"""Escritas administrativas pequenas, auditadas e conferidas na planilha oficial."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

# Os dominios usados pela plataforma independente ficam isolados dos motores
# de producao. Assim, uma atualizacao do painel nao muda o import dos servicos
# que processam guerras, Liga e raides.
_DOMINIOS = Path(os.environ.get(
    "WW_PLATAFORMA_DOMINIOS", "/opt/winning-wars-api/plataforma_dominios"
))
if _DOMINIOS.exists():
    sys.path.insert(0, str(_DOMINIOS))

from ww_competicao.manual import conferir, fotografar, preparar
from ww_competicao.participacao_competicao import (
    PC_ABA, pc_confirmar_evento, pc_preparar_alteracao,
)
from ww_competicao.torneios import criar_torneio, selecionar_vencedor

from .conteudo import CREDENCIAL_PADRAO, PLANILHA_PADRAO, invalidar_conteudo


_LOCK = threading.Lock()
_BACKUPS = Path(os.environ.get("WW_ADMIN_BACKUPS", "/opt/winning-wars-api/backups_admin_web"))
_LAYOUT_MAX_IMAGEM = 1_600_000
_LAYOUT_MAX_LOTE = 24_000_000


@lru_cache(maxsize=1)
def _planilha_escrita():
    import gspread
    from google.oauth2.service_account import Credentials

    creds = Credentials.from_service_account_file(
        os.environ.get("WW_GOOGLE_CREDENTIALS", CREDENCIAL_PADRAO),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return gspread.authorize(creds).open_by_key(
        os.environ.get("WW_GOOGLE_SHEET_ID", PLANILHA_PADRAO)
    )


def _backup(nome: str, dados: dict[str, Any]) -> str:
    _BACKUPS.mkdir(parents=True, exist_ok=True, mode=0o700)
    instante = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    destino = _BACKUPS / f"{nome}_{instante}.json"
    destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(destino, 0o600)
    return str(destino)


def _agendar_publicacao() -> None:
    programa = Path(os.environ.get(
        "WW_PUBLICADOR_CONSULTAS",
        "/opt/winning-wars-api/consultas_app_20261002/operacao/publicar_consultas.py",
    ))
    python = Path("/opt/winning-wars-api/venv/bin/python")
    if programa.exists() and python.exists():
        subprocess.Popen(
            [str(python), "-B", str(programa)], cwd="/opt/winning-wars-api",
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )


def _url_layout_oficial(valor: str) -> str:
    url = str(valor or "").strip()
    parsed = urlparse(url)
    parametros = parse_qs(parsed.query)
    if (parsed.scheme != "https" or parsed.netloc.casefold() != "link.clashofclans.com"
            or parametros.get("action", [""])[0].casefold() != "openlayout"):
        raise ValueError("Use um link oficial de layout do Clash of Clans")
    return url


def _url_imagem(valor: str) -> str:
    url = str(valor or "").strip()
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL de imagem invalida")
    return url


def _decodificar_webp(valor: str) -> bytes:
    texto = str(valor or "").strip()
    if not texto:
        return b""
    try:
        dados = base64.b64decode(texto, validate=True)
    except (ValueError, binascii.Error) as erro:
        raise ValueError("Imagem WEBP invalida") from erro
    if len(dados) > _LAYOUT_MAX_IMAGEM:
        raise ValueError("Imagem otimizada excede 1,6 MB")
    if len(dados) < 16 or dados[:4] != b"RIFF" or dados[8:12] != b"WEBP":
        raise ValueError("Imagem enviada nao e WEBP")
    return dados


def _credenciais_cloudinary() -> tuple[str, str, str]:
    valores = (
        os.environ.get("WW_CLOUDINARY_CLOUD_NAME") or os.environ.get("CLOUDINARY_CLOUD_NAME"),
        os.environ.get("WW_CLOUDINARY_API_KEY") or os.environ.get("CLOUDINARY_API_KEY"),
        os.environ.get("WW_CLOUDINARY_API_SECRET") or os.environ.get("CLOUDINARY_API_SECRET"),
    )
    if not all(str(valor or "").strip() for valor in valores):
        raise RuntimeError("Cloudinary ainda nao configurado na Oracle")
    return tuple(str(valor).strip() for valor in valores)


def _upload_cloudinary(dados: bytes, tipo: str, cv: int) -> str:
    import requests

    cloud_name, api_key, api_secret = _credenciais_cloudinary()
    folder = f"winning-wars/layouts/{tipo.casefold()}/cv-{cv}"
    timestamp = int(time.time())
    parametros = {"folder": folder, "timestamp": timestamp}
    assinatura_texto = "&".join(
        f"{chave}={parametros[chave]}" for chave in sorted(parametros)
    ) + api_secret
    assinatura = hashlib.sha1(assinatura_texto.encode("utf-8")).hexdigest()
    try:
        resposta = requests.post(
            f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload",
            data={"api_key": api_key, "timestamp": str(timestamp),
                  "folder": folder, "signature": assinatura},
            files={"file": (f"layout-{uuid.uuid4().hex}.webp", dados, "image/webp")},
            timeout=45,
        )
        resposta.raise_for_status()
        url = str(resposta.json().get("secure_url", "")).strip()
    except requests.RequestException as erro:
        detalhe = ""
        try:
            detalhe = str(erro.response.json().get("error", {}).get("message", "")) if erro.response else ""
        except Exception:
            pass
        raise RuntimeError(f"Falha no upload ao Cloudinary{': ' + detalhe if detalhe else ''}") from erro
    if not url:
        raise RuntimeError("Cloudinary nao retornou URL segura")
    return url


def preparar_layouts_lote(admin: str, tipo: str, cv: int,
                           itens: list[dict[str, Any]], agora: str) -> list[dict[str, Any]]:
    if tipo not in {"Guerra", "Rankeada"} or type(cv) is not int or not 9 <= cv <= 18:
        raise ValueError("Tipo ou Centro de Vila invalido")
    if not 1 <= len(itens) <= 20:
        raise ValueError("O lote deve conter de 1 a 20 layouts")
    resultado, links, tamanho_total = [], set(), 0
    for indice, item in enumerate(itens, 1):
        link = _url_layout_oficial(item.get("link", ""))
        if link in links:
            raise ValueError(f"Link repetido no item {indice}")
        links.add(link)
        imagem = _decodificar_webp(item.get("imagem_base64", ""))
        tamanho_total += len(imagem)
        if tamanho_total > _LAYOUT_MAX_LOTE:
            raise ValueError("As imagens do lote excedem 24 MB apos a otimizacao")
        imagem_url = _url_imagem(item.get("imagem_url", ""))
        if imagem and imagem_url:
            raise ValueError(f"Item {indice} possui arquivo e URL de imagem")
        descricao = str(item.get("descricao", "")).strip()
        if len(descricao) > 500:
            raise ValueError(f"Descricao muito longa no item {indice}")
        resultado.append({
            "Tipo": tipo, "CV": f"CV {cv}", "Autor": admin,
            "Link": link, "Descricao": descricao, "ImagemUrl": imagem_url,
            "DataHora": agora, "Tag": "", "imagem": imagem,
        })
    return resultado


def publicar_layouts(admin: str, tipo: str, cv: int,
                      itens: list[dict[str, Any]]) -> dict[str, Any]:
    agora = datetime.now(timezone.utc).isoformat()
    preparados = preparar_layouts_lote(admin, tipo, cv, itens, agora)
    with _LOCK:
        planilha = _planilha_escrita()
        aba = planilha.worksheet("Layouts")
        logs = planilha.worksheet("Logs")
        linhas_antes = aba.get_all_values(value_render_option="FORMULA")
        logs_antes = logs.get_all_values(value_render_option="FORMULA")
        if not linhas_antes:
            raise ValueError("Cabecalho de Layouts ausente")
        cabecalho = linhas_antes[0]
        # A aba oficial criada pelo app anterior termina em DataHora. Algumas
        # planilhas de homologacao possuem tambem Tag; quando existir ela sera
        # preenchida, mas nunca deve impedir a publicacao na estrutura oficial.
        obrigatorias = {"Tipo", "CV", "Autor", "Link", "Descricao", "ImagemUrl", "DataHora"}
        if not obrigatorias.issubset(set(cabecalho)):
            raise ValueError("Cabecalho de Layouts divergente")
        existentes = {
            linha[cabecalho.index("Link")].strip()
            for linha in linhas_antes[1:]
            if len(linha) > cabecalho.index("Link")
        }
        repetidos = [item["Link"] for item in preparados if item["Link"] in existentes]
        if repetidos:
            raise ValueError("Um ou mais layouts ja estao publicados")
        backup = _backup("layouts", {
            "aba": "Layouts", "linhas": linhas_antes,
            "logs": logs_antes, "tipo": tipo, "cv": cv,
        })
        for item in preparados:
            imagem = item.pop("imagem")
            if imagem:
                item["ImagemUrl"] = _upload_cloudinary(imagem, tipo, cv)
        linhas = [[item.get(coluna, "") for coluna in cabecalho] for item in preparados]
        aba.append_rows(linhas, value_input_option="RAW")
        if logs_antes:
            cabecalho_logs = logs_antes[0]
            registros_logs = []
            for item in preparados:
                registro = {
                    "DataHora": agora, "Admin": admin,
                    "Acao": f"Adicionou layout {tipo} para CV {cv}",
                }
                registros_logs.append([registro.get(coluna, "") for coluna in cabecalho_logs])
            logs.append_rows(registros_logs, value_input_option="RAW")
        finais = aba.get_all_values(value_render_option="FORMULA")
        registros_finais = {
            linha[cabecalho.index("Link")]: linha
            for linha in finais[1:]
            if len(linha) > cabecalho.index("Link")
        }
        if any(item["Link"] not in registros_finais for item in preparados):
            raise RuntimeError("Layouts enviados, mas a conferencia falhou; nao repetir automaticamente")
        invalidar_conteudo("Layouts")
        return {
            "status": "APLICADO_E_CONFERIDO", "aplicados": len(preparados),
            "tipo": tipo, "cv": cv, "backup": backup,
            "layouts": [{chave: valor for chave, valor in item.items() if chave != "imagem"}
                        for item in preparados],
        }


def alterar_participacao(admin: str, tag: str, habilitada: bool, motivo: str,
                         evento_anterior: str) -> dict[str, Any]:
    with _LOCK:
        planilha = _planilha_escrita()
        aba = planilha.worksheet(PC_ABA)
        linhas = aba.get_all_values(value_render_option="FORMULA")
        admins = planilha.worksheet("Admins").get_all_values(value_render_option="FORMULA")
        agora = datetime.now(timezone.utc).isoformat()
        evento_id = str(uuid.uuid4())
        linha = pc_preparar_alteracao(
            linhas, admins, admin, tag, habilitada, motivo, evento_anterior,
            evento_id, agora,
        )
        backup = _backup("participacao", {"aba": PC_ABA, "linhas": linhas})
        aba.append_row(linha, value_input_option="RAW")
        conferido = aba.get_all_values(value_render_option="FORMULA")
        if not pc_confirmar_evento(conferido, linha):
            raise RuntimeError("Alteracao enviada, mas ainda nao confirmada; nao repetir automaticamente")
        invalidar_conteudo("ParticipacaoCompeticao")
        _agendar_publicacao()
        return {
            "status": "APLICADO_E_CONFERIDO", "tag": linha[1],
            "habilitada": linha[3] == "TRUE", "evento_id": evento_id,
            "backup": backup,
        }


def _ranking_atual(planilha) -> str:
    # Página1 é o contrato estável usado também pelo publicador oficial. As
    # abas históricas nunca são selecionadas por semelhança de cabeçalho.
    aba = planilha.worksheet("Página1")
    cabecalho = aba.row_values(1)
    if not {"ID", "Nome", "JogosCla", "Eventos"}.issubset(set(cabecalho)):
        raise ValueError("Cabecalho do ranking atual divergente")
    return aba.title


def _aplicar_virtual(virtual: dict[str, Any], capacidades: dict[str, Any], proposta: dict[str, Any]) -> None:
    novas = json.loads(proposta["registro"][10])["novas_linhas"]
    for nome, linhas in novas.items():
        for modo in ("valores", "formulas"):
            virtual[nome][modo].extend([[str(valor) for valor in linha] for linha in linhas])
    for modo in ("valores", "formulas"):
        ranking = virtual["ranking"][modo]
        coluna = ranking[0].index(proposta["atividade"])
        linha = next(registro for registro in ranking[1:] if str(registro[0]) == proposta["id"])
        linha.extend([""] * max(0, coluna + 1 - len(linha)))
        linha[coluna] = str(proposta["pontos"])
        virtual["manual"][modo].append(proposta["registro"][:])
    for pedido in proposta["lote"]["requests"]:
        if "addSheet" in pedido:
            capacidades["manual"]["nova"] = False
        if "appendDimension" in pedido:
            dimensao = pedido["appendDimension"]
            for meta in capacidades.values():
                if meta["id"] == dimensao["sheetId"]:
                    meta["linhas"] += dimensao["length"]


def aplicar_lancamentos(admin: str, atividade: str,
                        entradas: list[dict[str, Any]]) -> dict[str, Any]:
    if atividade not in {"JogosCla", "Eventos"} or not 1 <= len(entradas) <= 50:
        raise ValueError("Lote manual invalido")
    tags = [str(item.get("tag", "")).strip().upper() for item in entradas]
    if len(tags) != len(set(tags)):
        raise ValueError("Conta repetida no lote")
    with _LOCK:
        planilha = _planilha_escrita()
        ranking_titulo = _ranking_atual(planilha)
        foto, metas = fotografar(planilha, ranking_titulo)
        virtual, capacidades = deepcopy(foto), deepcopy(metas)
        propostas, ignorados, pedidos = [], [], []
        agora = datetime.now(timezone.utc).isoformat()
        for entrada in entradas:
            valor = entrada.get("valor")
            if type(valor) is not int:
                raise ValueError("Use somente valores inteiros")
            proposta = preparar(
                virtual, capacidades, admin, str(entrada["tag"]),
                str(entrada["nome"]), atividade, valor, str(uuid.uuid4()), agora,
            )
            if proposta["status"] == "ZERO_SEM_INSCRICAO":
                ignorados.append(entrada)
                continue
            propostas.append(proposta)
            pedidos.extend(proposta["lote"]["requests"])
            _aplicar_virtual(virtual, capacidades, proposta)
        if not propostas:
            return {"status": "SEM_ALTERACOES", "aplicados": 0, "ignorados": len(ignorados)}
        backup = _backup("lancamentos_manuais", {
            "ranking": ranking_titulo, "atividade": atividade,
            "abas": {nome: dados["formulas"] for nome, dados in foto.items()},
        })
        planilha.batch_update({"requests": pedidos})
        foto_final, _ = fotografar(planilha, ranking_titulo)
        for proposta in propostas:
            conferir(foto_final, proposta)
        invalidar_conteudo()
        _agendar_publicacao()
        return {
            "status": "APLICADO_E_CONFERIDO", "atividade": atividade,
            "aplicados": len(propostas), "ignorados": len(ignorados),
            "backup": backup,
            "resultados": [{"tag": p["tag"], "antes": p["antes"], "depois": p["pontos"]} for p in propostas],
        }


def _salvar_torneio(admin: str, torneio: dict[str, Any] | None) -> dict[str, Any]:
    planilha = _planilha_escrita()
    aba = planilha.worksheet("Torneios")
    linhas = aba.get_all_values(value_render_option="FORMULA")
    backup = _backup("torneio", {"aba": "Torneios", "linhas": linhas})
    agora = datetime.now(timezone.utc).isoformat()
    if torneio is None:
        conteudo = {"status": "SEM_TORNEIO"}
        linha = ["", agora, admin, "SEM_TORNEIO", json.dumps(conteudo, separators=(",", ":"))]
    else:
        conteudo = torneio
        linha = [str(conteudo.get("criado_em", "")), agora, admin,
                 str(conteudo.get("status", "EM_ANDAMENTO")),
                 json.dumps(conteudo, ensure_ascii=False, separators=(",", ":"))]
    aba.append_row(linha, value_input_option="RAW")
    finais = aba.get_all_values(value_render_option="FORMULA")
    if not finais or finais[-1] != linha:
        raise RuntimeError("Torneio enviado, mas ainda nao confirmado; nao repetir automaticamente")
    invalidar_conteudo("Torneios")
    return {"status": "APLICADO_E_CONFERIDO", "torneio": torneio, "backup": backup}


def iniciar_torneio(admin: str, roster: dict[str, Any], nome: str, modo: str,
                     cv: int | str, tags: list[str]) -> dict[str, Any]:
    if roster.get("tag") != "#2CY88CCYU":
        raise ValueError("Elenco oficial do TorneiosWWars indisponivel")
    mapa = {conta["tag"]: conta for conta in roster.get("contas", [])}
    if len(tags) != len(set(tags)) or not 2 <= len(tags) <= 32 or any(tag not in mapa for tag in tags):
        raise ValueError("Selecao de participantes invalida")
    participantes = [{**mapa[tag], "clan": roster.get("clan", "TorneiosWWars"),
                      "clan_tag": roster["tag"]} for tag in tags]
    torneio = criar_torneio(nome, participantes, cv, modo=modo)
    with _LOCK:
        return _salvar_torneio(admin, torneio)


def avancar_torneio(admin: str, torneio: dict[str, Any], rodada: int,
                     partida: int, vencedor: str) -> dict[str, Any]:
    atualizado = selecionar_vencedor(torneio, rodada, partida, vencedor)
    with _LOCK:
        return _salvar_torneio(admin, atualizado)


def encerrar_torneio(admin: str) -> dict[str, Any]:
    with _LOCK:
        return _salvar_torneio(admin, None)
