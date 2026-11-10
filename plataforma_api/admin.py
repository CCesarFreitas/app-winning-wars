"""Autenticacao administrativa e resumo protegido da plataforma independente."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sqlite3
import threading
import time
import unicodedata
from collections import defaultdict, deque
from typing import Any

from fastapi import HTTPException, Request, Response
from pydantic import BaseModel, Field

from .conteudo import _linhas_planilha, obter_torneio
from .manual_admin import montar_manual_admin, propor_lancamento
from .operacoes_admin import (
    alterar_participacao, aplicar_lancamentos, avancar_torneio,
    encerrar_torneio, iniciar_torneio,
)
from .participacao_admin import montar_participacao_admin
from .ranking_atual import montar_ranking_atual


COOKIE = "ww_admin_session"
SESSAO_SEGUNDOS = 8 * 60 * 60
_TENTATIVAS: dict[str, deque[float]] = defaultdict(deque)
_LOCK = threading.Lock()


class Credenciais(BaseModel):
    usuario: str = Field(min_length=1, max_length=80)
    senha: str = Field(min_length=1, max_length=256)


class PropostaManual(BaseModel):
    tag: str = Field(min_length=4, max_length=20)
    atividade: str = Field(min_length=4, max_length=20)
    valor: int = Field(ge=0, le=1_000_000)


class AlteracaoParticipacao(BaseModel):
    tag: str = Field(min_length=4, max_length=20)
    habilitada: bool
    motivo: str = Field(min_length=3, max_length=500)
    evento_anterior: str = Field(min_length=1, max_length=100)


class EntradaManual(BaseModel):
    tag: str = Field(min_length=4, max_length=20)
    nome: str = Field(min_length=1, max_length=120)
    valor: int = Field(ge=0, le=1_000_000)


class LoteManual(BaseModel):
    atividade: str = Field(min_length=4, max_length=20)
    entradas: list[EntradaManual] = Field(min_length=1, max_length=50)


class NovoTorneio(BaseModel):
    nome: str = Field(min_length=3, max_length=80)
    modo: str = Field(min_length=3, max_length=80)
    cv: int | str
    tags: list[str] = Field(min_length=2, max_length=32)


class VencedorTorneio(BaseModel):
    rodada: int = Field(ge=0, le=10)
    partida: int = Field(ge=0, le=31)
    vencedor: str = Field(min_length=4, max_length=20)


def _segredo() -> bytes:
    valor = os.environ.get("WW_ADMIN_SESSION_SECRET", "").encode("utf-8")
    if len(valor) < 32:
        raise HTTPException(status_code=503, detail="autenticacao_nao_configurada")
    return valor


def _b64(dados: bytes) -> str:
    return base64.urlsafe_b64encode(dados).decode("ascii").rstrip("=")


def _desb64(valor: str) -> bytes:
    return base64.urlsafe_b64decode(valor + "=" * (-len(valor) % 4))


def _normalizar_nivel(valor: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", str(valor))
        if not unicodedata.combining(c)
    ).strip().casefold()


def _verificar_senha(senha: str, hash_armazenado: str) -> bool:
    valor = str(hash_armazenado or "")
    if valor.startswith("pbkdf2_sha256$"):
        try:
            _, iteracoes, salt_hex, digest_hex = valor.split("$", 3)
            teste = hashlib.pbkdf2_hmac(
                "sha256", senha.encode("utf-8"), bytes.fromhex(salt_hex),
                int(iteracoes),
            ).hex()
            return hmac.compare_digest(teste, digest_hex)
        except (TypeError, ValueError):
            return False
    legado = hashlib.sha256(senha.encode("utf-8")).hexdigest()
    return hmac.compare_digest(legado, valor)


def _administrador(usuario: str) -> dict[str, str] | None:
    linhas = _linhas_planilha("Admins", ttl=60)
    if not linhas or "Usuario" not in linhas[0] or "SenhaHash" not in linhas[0]:
        raise HTTPException(status_code=503, detail="cadastro_admin_indisponivel")
    encontrados = []
    for linha in linhas[1:]:
        registro = dict(zip(linhas[0], [str(v) for v in linha]))
        if registro.get("Usuario", "").strip().casefold() == usuario.strip().casefold():
            encontrados.append(registro)
    if len(encontrados) != 1:
        return None
    nivel = _normalizar_nivel(encontrados[0].get("Nivel", ""))
    if nivel not in {"dono", "lider", "co-lider", "colider"}:
        return None
    return encontrados[0]


def _ip(request: Request) -> str:
    encaminhado = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    return encaminhado or (request.client.host if request.client else "desconhecido")


def _limitar(ip: str, sucesso: bool = False) -> None:
    agora = time.monotonic()
    with _LOCK:
        fila = _TENTATIVAS[ip]
        while fila and agora - fila[0] > 15 * 60:
            fila.popleft()
        if sucesso:
            fila.clear()
            return
        if len(fila) >= 5:
            raise HTTPException(status_code=429, detail="muitas_tentativas")
        fila.append(agora)


def _criar_token(usuario: str, nivel: str) -> str:
    payload = {
        "usuario": usuario,
        "nivel": nivel,
        "exp": int(time.time()) + SESSAO_SEGUNDOS,
    }
    corpo = _b64(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode())
    assinatura = _b64(hmac.new(_segredo(), corpo.encode(), hashlib.sha256).digest())
    return f"{corpo}.{assinatura}"


def _ler_token(token: str | None) -> dict[str, Any] | None:
    if not token or "." not in token:
        return None
    try:
        corpo, assinatura = token.split(".", 1)
        esperada = _b64(hmac.new(_segredo(), corpo.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(assinatura, esperada):
            return None
        payload = json.loads(_desb64(corpo))
        if not isinstance(payload, dict) or int(payload.get("exp", 0)) <= int(time.time()):
            return None
        if not payload.get("usuario") or not payload.get("nivel"):
            return None
        return payload
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def _sessao(request: Request) -> dict[str, Any]:
    payload = _ler_token(request.cookies.get(COOKIE))
    if not payload:
        raise HTTPException(status_code=401, detail="sessao_admin_ausente")
    admin = _administrador(str(payload["usuario"]))
    if not admin:
        raise HTTPException(status_code=401, detail="administrador_revogado")
    return {
        "usuario": admin["Usuario"].strip(),
        "nivel": admin.get("Nivel", "").strip(),
    }


def _resumo_participacao() -> dict[str, int]:
    linhas = _linhas_planilha("ParticipacaoCompeticao", ttl=60)
    if not linhas or "PlayerTag" not in linhas[0] or "Habilitada" not in linhas[0]:
        return {"total": 0, "habilitadas": 0, "bloqueadas": 0}
    estado: dict[str, dict[str, str]] = {}
    for linha in linhas[1:]:
        registro = dict(zip(linhas[0], [str(v) for v in linha]))
        tag = registro.get("PlayerTag", "").strip().upper()
        origem = registro.get("Origem", "").strip().upper()
        if not tag:
            continue
        atual = estado.get(tag)
        if origem == "ADMIN" or atual is None or atual.get("Origem", "").upper() != "ADMIN":
            estado[tag] = registro
    habilitadas = sum(r.get("Habilitada", "").upper() == "TRUE" for r in estado.values())
    bloqueadas = sum(r.get("Habilitada", "").upper() == "FALSE" for r in estado.values())
    return {"total": len(estado), "habilitadas": habilitadas, "bloqueadas": bloqueadas}


def instalar_rotas_admin(app, caminho_sqlite: str) -> None:
    @app.post("/v1/admin/login")
    def login_admin(credenciais: Credenciais, request: Request, response: Response):
        ip = _ip(request)
        _limitar(ip)
        admin = _administrador(credenciais.usuario)
        if not admin or not _verificar_senha(credenciais.senha, admin.get("SenhaHash", "")):
            raise HTTPException(status_code=401, detail="credenciais_invalidas")
        _limitar(ip, sucesso=True)
        usuario = admin["Usuario"].strip()
        nivel = admin.get("Nivel", "").strip()
        response.set_cookie(
            COOKIE, _criar_token(usuario, nivel), max_age=SESSAO_SEGUNDOS,
            httponly=True, secure=os.environ.get("WW_ADMIN_COOKIE_SECURE", "1") != "0",
            samesite="strict", path="/api/v1/admin",
        )
        return {"autenticado": True, "usuario": usuario, "nivel": nivel}

    @app.get("/v1/admin/session")
    def sessao_admin(request: Request):
        try:
            sessao = _sessao(request)
        except HTTPException as erro:
            if erro.status_code == 401:
                return {"autenticado": False}
            raise
        return {"autenticado": True, **sessao}

    @app.post("/v1/admin/logout")
    def logout_admin(response: Response):
        response.delete_cookie(COOKIE, path="/api/v1/admin", samesite="strict")
        return {"autenticado": False}

    @app.get("/v1/admin/summary")
    def resumo_admin(request: Request):
        sessao = _sessao(request)
        ranking = montar_ranking_atual(caminho_sqlite)
        return {
            "admin": sessao,
            "temporada": ranking["temporada"],
            "temporada_nome": ranking["temporada_nome"],
            "ranking": {"jogadores": ranking["total"], "atualizado_em": ranking["atualizado_em"]},
            "participacao": _resumo_participacao(),
            "modo": "LEITURA_E_ESCRITA",
        }

    @app.get("/v1/admin/audit/activities")
    def atividades_auditoria_admin(request: Request, limite: int = 50):
        _sessao(request)
        from auditoria_historica import listar_atividades
        return listar_atividades(limite=max(1, min(limite, 200)))

    @app.get("/v1/admin/audit/player/{player_tag}")
    def jogador_auditoria_admin(player_tag: str, request: Request, limite: int = 100):
        _sessao(request)
        from auditoria_historica import auditoria_jogador
        return auditoria_jogador(player_tag, limite=max(1, min(limite, 200)))

    @app.get("/v1/admin/participation")
    def participacao_admin(request: Request):
        _sessao(request)
        try:
            return montar_participacao_admin(caminho_sqlite)
        except (OSError, ValueError, sqlite3.Error) as erro:
            raise HTTPException(status_code=503, detail="participacao_indisponivel") from erro

    @app.post("/v1/admin/participation/toggle")
    def alterar_participacao_admin(dados: AlteracaoParticipacao, request: Request):
        sessao = _sessao(request)
        try:
            return alterar_participacao(
                sessao["usuario"], dados.tag, dados.habilitada,
                dados.motivo, dados.evento_anterior,
            )
        except (ValueError, PermissionError) as erro:
            raise HTTPException(status_code=409, detail=str(erro)) from erro
        except (OSError, RuntimeError) as erro:
            raise HTTPException(status_code=503, detail=str(erro)) from erro

    @app.get("/v1/admin/manual")
    def manual_admin(request: Request):
        _sessao(request)
        try:
            return montar_manual_admin(caminho_sqlite)
        except (OSError, ValueError, sqlite3.Error) as erro:
            raise HTTPException(status_code=503, detail="manual_indisponivel") from erro

    @app.post("/v1/admin/manual/proposal")
    def proposta_manual(dados: PropostaManual, request: Request):
        _sessao(request)
        try:
            return propor_lancamento(caminho_sqlite, dados.tag, dados.atividade, dados.valor)
        except ValueError as erro:
            raise HTTPException(status_code=422, detail="proposta_manual_invalida") from erro

    @app.post("/v1/admin/manual/batch")
    def lancamentos_manuais_lote(dados: LoteManual, request: Request):
        sessao = _sessao(request)
        try:
            return aplicar_lancamentos(
                sessao["usuario"], dados.atividade,
                [entrada.dict() for entrada in dados.entradas],
            )
        except (ValueError, PermissionError) as erro:
            raise HTTPException(status_code=409, detail=str(erro)) from erro
        except (OSError, RuntimeError) as erro:
            raise HTTPException(status_code=503, detail=str(erro)) from erro

    @app.post("/v1/admin/tournament/start")
    def iniciar_torneio_admin(dados: NovoTorneio, request: Request):
        sessao = _sessao(request)
        estado = obter_torneio(caminho_sqlite)
        try:
            return iniciar_torneio(
                sessao["usuario"], estado.get("roster") or {}, dados.nome,
                dados.modo, dados.cv, dados.tags,
            )
        except (ValueError, PermissionError) as erro:
            raise HTTPException(status_code=409, detail=str(erro)) from erro

    @app.post("/v1/admin/tournament/winner")
    def vencedor_torneio_admin(dados: VencedorTorneio, request: Request):
        sessao = _sessao(request)
        estado = obter_torneio(caminho_sqlite)
        if not estado.get("torneio"):
            raise HTTPException(status_code=409, detail="Torneio ativo ausente")
        try:
            return avancar_torneio(
                sessao["usuario"], estado["torneio"], dados.rodada,
                dados.partida, dados.vencedor,
            )
        except ValueError as erro:
            raise HTTPException(status_code=409, detail=str(erro)) from erro

    @app.post("/v1/admin/tournament/reset")
    def encerrar_torneio_admin(request: Request):
        sessao = _sessao(request)
        return encerrar_torneio(sessao["usuario"])
