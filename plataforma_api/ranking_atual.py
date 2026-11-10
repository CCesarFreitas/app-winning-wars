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


def _colunas_atividade(cabecalho: list[str]) -> list[str]:
    return [
        coluna for coluna in cabecalho
        if coluna in {"JogosCla", "Eventos"}
        or coluna.startswith(("Guerra_", "Liga_", "Raide_"))
    ]


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
    linhas = db.execute(
        """SELECT conteudo FROM versoes
           WHERE tipo='roster' AND chave='principal'
           ORDER BY sequencia DESC"""
    ).fetchall()
    resultado: dict[str, int] = {}
    for linha in linhas:
        try:
            roster = json.loads(linha[0])
        except (TypeError, json.JSONDecodeError):
            continue
        for conta in roster.get("contas", []) if isinstance(roster, dict) else []:
            if not isinstance(conta, dict):
                continue
            tag = str(conta.get("tag", "")).strip().upper()
            cv = conta.get("cv")
            if tag and type(cv) is int and 1 <= cv <= 18:
                # As versoes estao da mais nova para a mais antiga.
                resultado.setdefault(tag, cv)
    return resultado


def _atividades(db: sqlite3.Connection) -> list[dict[str, Any]]:
    linhas = db.execute(
        """SELECT conteudo FROM versoes WHERE sequencia IN
           (SELECT MAX(sequencia) FROM versoes WHERE tipo='atividade' GROUP BY chave)"""
    ).fetchall()
    documentos = []
    for linha in linhas:
        try:
            documento = json.loads(linha[0])
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(documento, dict):
            documentos.append(documento)
    return documentos


def _contribuicoes_atividades(
    documentos: list[dict[str, Any]], temporada: str,
) -> dict[str, dict[str, Any]]:
    """Preserva desempenho de todos, sem transformar bloqueio em elegibilidade."""
    resultado: dict[str, dict[str, Any]] = {}
    for atividade in documentos:
        if (atividade.get("temporada") != temporada
                or atividade.get("status") != "APLICADO"
                or atividade.get("tipo") not in {"guerra", "liga", "raide"}):
            continue
        coluna = str(atividade.get("coluna", "")).strip()
        if not coluna:
            continue
        for jogador in atividade.get("jogadores", []):
            if not isinstance(jogador, dict):
                continue
            tag = str(jogador.get("tag", "")).strip().upper()
            if not tag:
                continue
            pontos = jogador.get("pontos")
            if pontos is None:
                if atividade["tipo"] == "raide":
                    pontos = (_inteiro(jogador.get("quantidade_ataques"))
                              + _inteiro(jogador.get("bonus")))
                else:
                    pontos = _inteiro(jogador.get("pontos_calculados"))
            pontos = max(0, _inteiro(pontos))
            conta = resultado.setdefault(tag, {
                "tag": tag, "nome": str(jogador.get("nome", "")).strip(),
                "colunas": {}, "guerra": 0, "raides": 0,
                "jogos": 0, "eventos": 0, "total": 0,
                "atividades": 0,
            })
            # Uma atividade possui uma coluna única. max evita duplicar versões.
            anterior = _inteiro(conta["colunas"].get(coluna))
            conta["colunas"][coluna] = max(anterior, pontos)
            conta["atividades"] += 1
    for conta in resultado.values():
        conta["guerra"] = sum(
            _inteiro(valor) for coluna, valor in conta["colunas"].items()
            if coluna.startswith(("Guerra_", "Liga_"))
        )
        conta["raides"] = sum(
            _inteiro(valor) for coluna, valor in conta["colunas"].items()
            if coluna.startswith("Raide_")
        )
        conta["total"] = conta["guerra"] + conta["raides"]
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
        atividades = _atividades(db)
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
    contribuicoes = _contribuicoes_atividades(atividades, temporada)
    cabecalho = ranking_linhas[0] if ranking_linhas else []
    colunas_atividade = _colunas_atividade(cabecalho)
    colunas_guerra = [c for c in colunas_atividade if c.startswith(("Guerra_", "Liga_"))]
    colunas_raide = [c for c in colunas_atividade if c.startswith("Raide_")]

    resultado: list[dict[str, Any]] = []
    detalhes_por_id: dict[str, dict[str, int]] = {}
    ids: set[str] = set()
    tags_incluidas: set[str] = set()
    for linha in _registros(ranking_linhas):
        participante_id = str(linha.get("ID", linha.get("ParticipanteID", ""))).strip()
        if not participante_id or participante_id in ids:
            raise ValueError("Identificador de participante ausente ou duplicado")
        ids.add(participante_id)
        tag = tag_por_id.get(participante_id, "")
        if participacao.get(tag, {}).get("Habilitada") == "FALSE":
            continue

        contribuicao = contribuicoes.get(tag, {})
        pontos_por_coluna = {
            coluna: (
                _inteiro(contribuicao.get("colunas", {}).get(coluna))
                if coluna in contribuicao.get("colunas", {})
                else _inteiro(linha.get(coluna))
            )
            for coluna in colunas_atividade
        }

        guerra = sum(pontos_por_coluna[c] for c in colunas_guerra)
        raides = sum(pontos_por_coluna[c] for c in colunas_raide)
        jogos = _inteiro(linha.get("JogosCla"))
        eventos = _inteiro(linha.get("Eventos"))
        detalhes_por_id[participante_id] = pontos_por_coluna
        if tag:
            tags_incluidas.add(tag)
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

    # Contas que contribuíram enquanto estavam bloqueadas não possuíam linha no
    # ranking. Quando o administrador as habilita, a projeção passa a exibir o
    # desempenho já preservado no SQLite, sem reescrever a planilha nem duplicar
    # lançamentos futuros.
    for tag, contribuicao in contribuicoes.items():
        if (tag in tags_incluidas
                or participacao.get(tag, {}).get("Habilitada") != "TRUE"
                or _inteiro(contribuicao.get("total")) <= 0):
            continue
        participante_id = f"desempenho:{tag}"
        nome = (participacao.get(tag, {}).get("Nome")
                or contribuicao.get("nome") or tag)
        pontos_por_coluna = {
            coluna: _inteiro(contribuicao.get("colunas", {}).get(coluna))
            for coluna in colunas_atividade
        }
        detalhes_por_id[participante_id] = pontos_por_coluna
        guerra = sum(pontos_por_coluna[c] for c in colunas_guerra)
        raides = sum(pontos_por_coluna[c] for c in colunas_raide)
        resultado.append({
            "participante_id": participante_id, "tag": tag,
            "nome": str(nome).strip(), "cv": cvs_por_tag.get(tag),
            "guerra": guerra, "raides": raides, "jogos": 0,
            "eventos": 0, "total": guerra + raides,
            "origem": "desempenho_preservado",
        })

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
        "colunas_atividade": colunas_atividade,
        "detalhes_por_id": detalhes_por_id,
        "contribuicoes_por_tag": contribuicoes,
    }


def montar_tabela_detalhada(caminho_sqlite: str | Path) -> dict[str, Any]:
    """Projeta cada coluna da temporada sem expor linhas administrativas."""
    resultado = montar_ranking_atual(caminho_sqlite)
    colunas = resultado["colunas_atividade"]
    detalhes = resultado["detalhes_por_id"]
    jogadores = []
    for jogador in resultado["ranking"]:
        jogadores.append({
            **jogador,
            "pontos": detalhes.get(jogador["participante_id"], {}),
        })
    return {
        "temporada": resultado["temporada"],
        "temporada_nome": resultado["temporada_nome"],
        "atualizado_em": resultado["atualizado_em"],
        "total": resultado["total"],
        "colunas": [
            {
                "chave": coluna,
                "rotulo": coluna.replace("_", " ").replace("JogosCla", "Jogos do Clã"),
                "tipo": (
                    "guerra" if coluna.startswith("Guerra_")
                    else "liga" if coluna.startswith("Liga_")
                    else "raide" if coluna.startswith("Raide_")
                    else "jogos" if coluna == "JogosCla"
                    else "eventos"
                ),
            }
            for coluna in colunas
        ],
        "jogadores": jogadores,
    }


def montar_ranking_contribuicao_sem_liga(caminho_sqlite: str | Path) -> dict[str, Any]:
    """Classifica contribuintes habilitados que nao participaram da Liga.

    A presenca em uma atividade de Liga e verificada pelo documento aplicado,
    inclusive quando o jogador recebeu zero ponto. A classificacao nao grava
    premio nem altera o ranking oficial.
    """
    resultado = montar_ranking_atual(caminho_sqlite)
    colunas = resultado["colunas_atividade"]
    detalhes = resultado["detalhes_por_id"]
    contribuicoes = resultado["contribuicoes_por_tag"]
    colunas_guerra = [c for c in colunas if c.startswith("Guerra_")]
    colunas_liga = [c for c in colunas if c.startswith("Liga_")]
    colunas_raide = [c for c in colunas if c.startswith("Raide_")]

    elegiveis: list[dict[str, Any]] = []
    excluidos_liga = 0
    sem_contribuicao = 0
    for jogador in resultado["ranking"]:
        pontos = detalhes.get(jogador["participante_id"], {})
        colunas_observadas = contribuicoes.get(jogador.get("tag", ""), {}).get("colunas", {})
        participou_liga = any(
            coluna in colunas_observadas or _inteiro(pontos.get(coluna)) > 0
            for coluna in colunas_liga
        )
        if participou_liga:
            excluidos_liga += 1
            continue

        guerra = sum(_inteiro(pontos.get(c)) for c in colunas_guerra)
        raides = sum(_inteiro(pontos.get(c)) for c in colunas_raide)
        jogos = _inteiro(pontos.get("JogosCla"))
        eventos = _inteiro(pontos.get("Eventos"))
        total = guerra + raides + jogos + eventos
        if total <= 0:
            sem_contribuicao += 1
            continue
        atividades_positivas = sum(
            _inteiro(pontos.get(coluna)) > 0
            for coluna in [*colunas_guerra, *colunas_raide, "JogosCla", "Eventos"]
        )
        elegiveis.append({
            "participante_id": jogador["participante_id"],
            "tag": jogador.get("tag", ""),
            "nome": jogador["nome"],
            "cv": jogador.get("cv"),
            "guerra": guerra,
            "raides": raides,
            "jogos": jogos,
            "eventos": eventos,
            "total": total,
            "atividades_positivas": atividades_positivas,
        })

    elegiveis.sort(key=lambda item: (
        item["total"], item["atividades_positivas"], item["guerra"],
        item["raides"], item["jogos"], item["eventos"],
        item["nome"].casefold(),
    ), reverse=True)
    for posicao, jogador in enumerate(elegiveis, 1):
        jogador["posicao"] = posicao
        jogador["temporada"] = resultado["temporada"]

    return {
        "temporada": resultado["temporada"],
        "temporada_nome": resultado["temporada_nome"],
        "atualizado_em": resultado["atualizado_em"],
        "total": len(elegiveis),
        "excluidos_liga": excluidos_liga,
        "sem_contribuicao": sem_contribuicao,
        "criterio": (
            "Contas habilitadas com contribuição positiva em guerras comuns, "
            "raides, Jogos do Clã ou eventos e sem participação em nenhuma "
            "rodada da Liga na temporada."
        ),
        "desempate": (
            "Maior total; mais atividades com pontuação; guerras; raides; "
            "Jogos do Clã; eventos."
        ),
        "jogadores": elegiveis,
    }

