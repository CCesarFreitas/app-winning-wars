"""Projecao somente leitura do ranking da temporada ativa.

A fonte e a fotografia que o observador da Oracle ja guarda no SQLite. Este
modulo nao abre a planilha, nao recalcula regras dos motores e nao grava dados.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


COLUNAS_FIXAS = {"ID", "Nome", "Total", "Posicao", "Posição", "WarTotal"}


def _registros(linhas: list[list[str]]) -> list[dict[str, str]]:
    if not linhas:
        return []
    cabecalho = linhas[0]
    if not cabecalho or len(cabecalho) != len(set(cabecalho)):
        raise ValueError("Cabecalho ausente ou duplicado")
    return [dict(zip(cabecalho, linha)) for linha in linhas[1:] if any(linha)]


def _inteiro(valor: Any) -> int:
    try:
        return int(float(str(valor).replace(",", ".")))
    except (TypeError, ValueError):
        return 0


def _fonte(db: sqlite3.Connection, chave: str) -> tuple[list[list[str]], str]:
    linha = db.execute(
        """
        SELECT conteudo, registrado_em
        FROM versoes
        WHERE tipo = 'fonte' AND chave = ?
        ORDER BY sequencia DESC
        LIMIT 1
        """,
        (chave,),
    ).fetchone()
    if linha is None:
        raise ValueError(f"Fonte ausente: {chave}")
    conteudo, registrado_em = linha
    dados = json.loads(conteudo)
    if not isinstance(dados, list):
        raise ValueError(f"Fonte invalida: {chave}")
    return dados, str(registrado_em)


def _estado_participacao(linhas: list[list[str]]) -> dict[str, dict[str, str]]:
    """Reproduz a precedencia do controle oficial: ADMIN prevalece sobre cadastro."""
    contas: dict[str, dict[str, str]] = {}
    for evento in _registros(linhas):
        tag = evento.get("PlayerTag", "").strip().upper()
        if not tag:
            continue
        atual = contas.get(tag)
        if evento.get("Origem") == "ADMIN" or atual is None or atual.get("Origem") != "ADMIN":
            contas[tag] = evento
    return contas


def _cvs_roster(db: sqlite3.Connection) -> dict[str, int]:
    linha = db.execute(
        """SELECT conteudo FROM versoes
           WHERE tipo='roster' AND chave='principal'
           ORDER BY sequencia DESC LIMIT 1"""
    ).fetchone()
    if linha is None:
        return {}
    try:
        roster = json.loads(linha[0])
    except (TypeError, json.JSONDecodeError):
        return {}
    resultado: dict[str, int] = {}
    for conta in roster.get("contas", []) if isinstance(roster, dict) else []:
        if not isinstance(conta, dict):
            continue
        tag = str(conta.get("tag", "")).strip().upper()
        cv = conta.get("cv")
        if tag and type(cv) is int and 1 <= cv <= 18:
            resultado[tag] = cv
    return resultado


def montar_ranking_atual(caminho_sqlite: str | Path) -> dict[str, Any]:
    """Retorna a temporada e o ranking oficial sem modificar a fonte."""
    uri = f"file:{Path(caminho_sqlite).resolve().as_posix()}?mode=ro"
    db = sqlite3.connect(uri, uri=True, timeout=10)
    try:
        ranking_linhas, ranking_em = _fonte(db, "Página1")
        estado_linhas, estado_em = _fonte(db, "EstadoMes")
        vinculos_linhas, vinculos_em = _fonte(db, "VinculosParticipantes")
        participacao_linhas, participacao_em = _fonte(db, "ParticipacaoCompeticao")
        cvs_por_tag = _cvs_roster(db)
    finally:
        db.close()

    estado_mes = {
        linha[0]: linha[1] if len(linha) > 1 else ""
        for linha in estado_linhas[1:]
        if linha
    }
    temporada = estado_mes.get("temporada_atual_id", "").strip()
    if not temporada:
        raise ValueError("Temporada atual ausente")

    tag_por_id: dict[str, str] = {}
    for vinculo in _registros(vinculos_linhas):
        participante_id = vinculo.get("ParticipanteID", "").strip()
        tag = vinculo.get("PlayerTag", "").strip().upper()
        if participante_id and tag:
            anterior = tag_por_id.setdefault(participante_id, tag)
            if anterior != tag:
                raise ValueError("Participante com tags divergentes")

    participacao = _estado_participacao(participacao_linhas)
    cabecalho = ranking_linhas[0] if ranking_linhas else []
    colunas_guerra = [c for c in cabecalho if c.startswith(("Guerra_", "Liga_"))]
    colunas_raide = [c for c in cabecalho if c.startswith("Raide_")]

    resultado: list[dict[str, Any]] = []
    ids: set[str] = set()
    for linha in _registros(ranking_linhas):
        participante_id = str(linha.get("ID", linha.get("ParticipanteID", ""))).strip()
        if not participante_id or participante_id in ids:
            raise ValueError("Identificador de participante ausente ou duplicado")
        ids.add(participante_id)
        tag = tag_por_id.get(participante_id, "")
        if participacao.get(tag, {}).get("Habilitada") == "FALSE":
            continue

        guerra = sum(_inteiro(linha.get(c)) for c in colunas_guerra)
        raides = sum(_inteiro(linha.get(c)) for c in colunas_raide)
        jogos = _inteiro(linha.get("JogosCla"))
        eventos = _inteiro(linha.get("Eventos"))
        resultado.append(
            {
                "participante_id": participante_id,
                "tag": tag,
                "nome": str(linha.get("Nome", "")).strip(),
                "cv": cvs_por_tag.get(tag),
                "guerra": guerra,
                "raides": raides,
                "jogos": jogos,
                "eventos": eventos,
                "total": guerra + raides + jogos + eventos,
            }
        )

    resultado.sort(
        key=lambda r: (r["total"], r["guerra"], r["raides"], r["jogos"], r["nome"].casefold()),
        reverse=True,
    )
    for posicao, jogador in enumerate(resultado, 1):
        jogador["posicao"] = posicao
        jogador["temporada"] = temporada

    fontes = {
        "ranking": ranking_em,
        "estado": estado_em,
        "vinculos": vinculos_em,
        "participacao": participacao_em,
    }
    return {
        "temporada": temporada,
        "temporada_nome": estado_mes.get("temporada_atual_nome", ""),
        "mes_finalizado": estado_mes.get("mes_finalizado", "").upper() == "TRUE",
        "atualizado_em": max(fontes.values()),
        "fontes": fontes,
        "total": len(resultado),
        "ranking": resultado,
    }

