"""Leituras publicas leves; Google Sheets continua sendo a fonte oficial."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from functools import lru_cache
from pathlib import Path
from typing import Any


PLANILHA_PADRAO = "1QTfVjrfSCVZ3JlqIDbhLHHBc2-anz8XhK9WzxU3v0oA"
CREDENCIAL_PADRAO = "/opt/winning-wars-api/credentials/google_service_account.json"
_CACHE: dict[str, tuple[float, list[list[str]]]] = {}
_LOCK = threading.Lock()


@lru_cache(maxsize=1)
def _planilha():
    import gspread
    from google.oauth2.service_account import Credentials

    credencial = os.environ.get("WW_GOOGLE_CREDENTIALS", CREDENCIAL_PADRAO)
    planilha_id = os.environ.get("WW_GOOGLE_SHEET_ID", PLANILHA_PADRAO)
    creds = Credentials.from_service_account_file(
        credencial,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    return gspread.authorize(creds).open_by_key(planilha_id)


def _linhas_planilha(nome: str, ttl: int) -> list[list[str]]:
    agora = time.monotonic()
    with _LOCK:
        anterior = _CACHE.get(nome)
        if anterior and agora - anterior[0] < ttl:
            return anterior[1]
    linhas = _planilha().worksheet(nome).get_all_values()
    with _LOCK:
        _CACHE[nome] = (agora, linhas)
    return linhas


def invalidar_conteudo(nome: str | None = None) -> None:
    """Invalida o cache depois de uma futura escrita administrativa conferida."""
    with _LOCK:
        if nome:
            _CACHE.pop(nome, None)
        else:
            _CACHE.clear()


def _registros(linhas: list[list[str]] | None) -> list[dict[str, str]]:
    if not linhas:
        return []
    cabecalho = [str(valor) for valor in linhas[0]]
    if not cabecalho or len(cabecalho) != len(set(cabecalho)):
        raise ValueError("Cabecalho publico invalido")
    return [
        dict(zip(cabecalho, [str(valor) for valor in linha]))
        for linha in linhas[1:]
        if any(linha)
    ]


def _projetar_layouts(
    linhas: list[list[str]], tipo: str | None = None, cv: str | None = None,
    limite: int = 24, deslocamento: int = 0,
) -> dict[str, Any]:
    tipo_normalizado = (tipo or "").strip().casefold()
    cv_normalizado = (cv or "").strip().casefold()
    resultado = []
    vistos = set()
    for item in reversed(_registros(linhas)):
        if tipo_normalizado and item.get("Tipo", "").strip().casefold() != tipo_normalizado:
            continue
        if cv_normalizado and item.get("CV", "").strip().casefold() != cv_normalizado:
            continue
        link = item.get("Link", "").strip()
        if not link or link in vistos:
            continue
        vistos.add(link)
        resultado.append(
            {
                "tipo": item.get("Tipo", "").strip(),
                "cv": item.get("CV", "").strip(),
                "autor": item.get("Autor", "").strip(),
                "link": link,
                "descricao": item.get("Descricao", "").strip(),
                "imagem_url": item.get("ImagemUrl", "").strip(),
                "publicado_em": item.get("DataHora", "").strip(),
                "tag": item.get("Tag", "").strip(),
            }
        )
    total = len(resultado)
    return {"total": total, "offset": deslocamento, "limit": limite,
            "layouts": resultado[deslocamento:deslocamento + limite]}


def listar_layouts(
    _caminho_sqlite: str | Path, tipo: str | None = None, cv: str | None = None,
    limite: int = 24, deslocamento: int = 0,
) -> dict[str, Any]:
    if not 1 <= limite <= 48 or deslocamento < 0:
        raise ValueError("Paginacao de layouts invalida")
    # Cinco minutos evitam leituras repetidas sem criar copia permanente na Oracle.
    return _projetar_layouts(_linhas_planilha("Layouts", ttl=300), tipo, cv,
                             limite, deslocamento)


def _ultimo_roster(caminho: str | Path) -> dict[str, Any] | None:
    uri = f"file:{Path(caminho).resolve().as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True, timeout=10) as db:
        linha = db.execute(
            """SELECT conteudo FROM versoes WHERE tipo='roster' AND chave='torneio_oficial'
               ORDER BY sequencia DESC LIMIT 1"""
        ).fetchone()
    return json.loads(linha[0]) if linha else None


def _projetar_torneio(linhas: list[list[str]]) -> dict[str, Any] | None:
    for item in reversed(_registros(linhas)):
        conteudo = item.get("ConteudoJSON", "").strip()
        status = item.get("Status", "").strip().upper()
        if not conteudo or status in {"ENCERRADO", "REMOVIDO", "SEM_TORNEIO"}:
            return None
        try:
            candidato = json.loads(conteudo)
        except json.JSONDecodeError as erro:
            raise ValueError("Torneio publico invalido") from erro
        if not isinstance(candidato, dict):
            raise ValueError("Torneio publico invalido")
        if candidato.get("status") == "SEM_TORNEIO":
            return None
        return candidato
    return None


def obter_torneio(caminho_sqlite: str | Path) -> dict[str, Any]:
    # Durante lives, o cache do estado dura apenas cinco segundos e vive na memoria.
    torneio = _projetar_torneio(_linhas_planilha("Torneios", ttl=5))
    roster = _ultimo_roster(caminho_sqlite)
    roster_publico = None
    if isinstance(roster, dict):
        roster_publico = {
            "clan": roster.get("clan", ""),
            "tag": roster.get("tag", ""),
            "consultado_em": roster.get("consultado_em", ""),
            "contas": [
                {chave: conta.get(chave) for chave in ("tag", "nome", "cv")}
                for conta in roster.get("contas", [])
                if isinstance(conta, dict)
            ],
        }
    return {"torneio": torneio, "roster": roster_publico}
