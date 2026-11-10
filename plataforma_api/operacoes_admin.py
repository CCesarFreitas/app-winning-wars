"""Escritas administrativas pequenas, auditadas e conferidas na planilha oficial."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

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
