"""Visao administrativa somente leitura de participacao, vinculos e presenca."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .ranking_atual import (
    _atividades, _colunas_atividade, _contribuicoes_atividades,
    _estado_participacao, _fonte, _registros,
)


def _inteiro(valor: Any) -> int:
    try:
        return int(float(str(valor).replace(",", ".")))
    except (TypeError, ValueError):
        return 0


def _instante(foto: dict[str, Any], registrado_em: str) -> str:
    return datetime.fromisoformat(str(foto.get("consultado_em") or registrado_em)).isoformat()


def _montar_situacao(temporada: str, ranking: list[list[str]],
                     vinculos: list[list[str]], inscritos: set[str],
                     participacao: dict[str, dict[str, str]], roster: dict[str, Any],
                     versoes_roster: list[tuple[dict[str, Any], str]],
                     consultado_em: str,
                     contribuicoes: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    fotos = []
    for foto, registrado_em in versoes_roster:
        tags = {m.get("tag") for m in foto.get("contas", []) if m.get("tag")}
        fotos.append((_instante(foto, registrado_em), tags))
    primeira_foto = fotos[0][0] if fotos else None
    primeira_vista: dict[str, str] = {}
    ultima_vista: dict[str, str] = {}
    retornou: set[str] = set()
    ja_vista: set[str] = set()
    ausente_depois: set[str] = set()
    for instante, tags in fotos:
        for tag in tags:
            primeira_vista.setdefault(tag, instante)
            ultima_vista[tag] = instante
            if tag in ausente_depois:
                retornou.add(tag)
            ja_vista.add(tag)
        ausente_depois.update(ja_vista - tags)

    membros = {m["tag"]: m for m in roster.get("contas", [])}
    tag_por_id = {r.get("ParticipanteID", ""): r.get("PlayerTag", "")
                  for r in _registros(vinculos)}
    ranking_por_tag = {}
    cabecalho = ranking[0] if ranking else []
    atividades = [c for c in cabecalho[2:]
                  if c not in {"Total", "Posição", "Posicao", "WarTotal"}]
    for registro in _registros(ranking):
        participante_id = str(registro.get("ID", registro.get("ParticipanteID", ""))).strip()
        tag = tag_por_id.get(participante_id)
        if not tag:
            continue
        pontos = (_inteiro(registro.get("Total")) if "Total" in registro
                  else sum(_inteiro(registro.get(c)) for c in atividades))
        ranking_por_tag[tag] = {"pontos": pontos, "nome_ranking": registro.get("Nome", "")}

    contas = []
    contribuicoes = contribuicoes or {}
    for tag in set(participacao) | set(ranking_por_tag) | set(contribuicoes):
        decisao = participacao.get(tag, {})
        no_cla = tag in membros
        primeira = primeira_vista.get(tag)
        if no_cla and tag in retornou:
            situacao = "RETORNOU_AO_CLA"
        elif no_cla and primeira and primeira_foto and primeira > primeira_foto:
            situacao = "ENTROU_APOS_INICIO_DO_HISTORICO"
        elif no_cla:
            situacao = "MEMBRO_ATUAL"
        elif tag in primeira_vista:
            situacao = "AUSENTE_AGORA"
        else:
            situacao = "SEM_REGISTRO_NO_CLA"
        contas.append({
            "tag": tag,
            "nome": (decisao.get("Nome") or ranking_por_tag.get(tag, {}).get("nome_ranking")
                     or membros.get(tag, {}).get("nome")
                     or contribuicoes.get(tag, {}).get("nome") or ""),
            "pontos": ranking_por_tag.get(tag, {}).get("pontos", 0),
            "inscrita": tag in inscritos,
            "habilitada": decisao.get("Habilitada"),
            "origem_decisao": decisao.get("Origem"),
            "situacao": situacao,
            "no_cla": no_cla,
            "primeira_vista": primeira,
            "ultima_vista": ultima_vista.get(tag),
        })
    contas.sort(key=lambda c: (c["no_cla"], c["habilitada"] != "TRUE",
                               -c["pontos"], c["nome"].casefold(), c["tag"]))
    return {"consultado_em": consultado_em, "temporada": temporada,
            "criterio": "A ausência gera revisão; somente decisão administrativa bloqueia a conta.",
            "contas": contas}


def _ultimo_roster(db: sqlite3.Connection) -> tuple[dict[str, Any], list[tuple[dict[str, Any], str]]]:
    linhas = db.execute(
        """SELECT conteudo, registrado_em FROM versoes
           WHERE tipo='roster' AND chave='principal' ORDER BY sequencia"""
    ).fetchall()
    if not linhas:
        raise ValueError("Roster principal ausente")
    historico = []
    for conteudo, registrado_em in linhas:
        foto = json.loads(conteudo)
        if not isinstance(foto, dict) or not isinstance(foto.get("contas"), list):
            raise ValueError("Roster principal invalido")
        historico.append((foto, str(registrado_em)))
    return historico[-1][0], historico


def montar_participacao_admin(caminho_sqlite: str | Path) -> dict[str, Any]:
    uri = f"file:{Path(caminho_sqlite).resolve().as_posix()}?mode=ro"
    db = sqlite3.connect(uri, uri=True, timeout=10)
    try:
        ranking, ranking_em = _fonte(db, "Página1")
        vinculos, vinculos_em = _fonte(db, "VinculosParticipantes")
        inscricoes, inscricoes_em = _fonte(db, "InscricoesTemporada")
        participacao_linhas, participacao_em = _fonte(db, "ParticipacaoCompeticao")
        estado_linhas, estado_em = _fonte(db, "EstadoMes")
        roster, versoes_roster = _ultimo_roster(db)
        atividades = _atividades(db)
    finally:
        db.close()

    estado_mes = {
        linha[0]: linha[1] if len(linha) > 1 else ""
        for linha in estado_linhas[1:] if linha
    }
    temporada = estado_mes.get("temporada_atual_id", "").strip()
    if not temporada:
        raise ValueError("Temporada atual ausente")

    participacao = _estado_participacao(participacao_linhas)
    contribuicoes = _contribuicoes_atividades(atividades, temporada)
    inscritos = {
        r.get("PlayerTag", "").strip().upper()
        for r in _registros(inscricoes)
        if r.get("Temporada", "").strip() == temporada
        and r.get("Status", "").strip().upper() == "ATIVO"
    }
    resultado = _montar_situacao(
        temporada, ranking, vinculos, inscritos, participacao, roster,
        versoes_roster, max(ranking_em, vinculos_em, inscricoes_em,
                            participacao_em, estado_em), contribuicoes,
    )

    vinculo_por_tag = {
        r.get("PlayerTag", "").strip().upper(): r.get("ParticipanteID", "").strip()
        for r in _registros(vinculos)
        if r.get("PlayerTag") and r.get("ParticipanteID")
    }
    tag_por_id = {participante_id: tag for tag, participante_id in vinculo_por_tag.items()}
    cabecalho_ranking = ranking[0] if ranking else []
    colunas = _colunas_atividade(cabecalho_ranking)
    ranking_por_tag = {}
    for registro in _registros(ranking):
        participante_id = str(registro.get("ID", registro.get("ParticipanteID", ""))).strip()
        tag = tag_por_id.get(participante_id)
        if tag:
            ranking_por_tag[tag] = registro
    membro_por_tag = {}
    for foto, _ in versoes_roster:
        for membro in foto.get("contas", []):
            if isinstance(membro, dict) and membro.get("tag"):
                membro_por_tag[str(membro["tag"]).strip().upper()] = membro
    contas = []
    for conta in resultado["contas"]:
        tag = conta["tag"]
        decisao = participacao.get(tag, {})
        membro = membro_por_tag.get(tag, {})
        linha_ranking = ranking_por_tag.get(tag, {})
        contribuicao = contribuicoes.get(tag, {})
        pontos_colunas = {
            coluna: (
                _inteiro(contribuicao.get("colunas", {}).get(coluna))
                if coluna in contribuicao.get("colunas", {})
                else _inteiro(linha_ranking.get(coluna))
            )
            for coluna in colunas
        }
        guerra = sum(valor for coluna, valor in pontos_colunas.items()
                     if coluna.startswith(("Guerra_", "Liga_")))
        raides = sum(valor for coluna, valor in pontos_colunas.items()
                     if coluna.startswith("Raide_"))
        jogos = _inteiro(linha_ranking.get("JogosCla"))
        eventos = _inteiro(linha_ranking.get("Eventos"))
        total_contribuicao = guerra + raides + jogos + eventos
        contas.append({
            **conta,
            "pontos": total_contribuicao,
            "contribuicao": {
                "guerra": guerra, "raides": raides, "jogos": jogos,
                "eventos": eventos, "total": total_contribuicao,
                "atividades": _inteiro(contribuicao.get("atividades")),
            },
            "participante_id": vinculo_por_tag.get(tag),
            "cv": membro.get("cv"),
            "cargo": membro.get("cargo"),
            "administrador": decisao.get("Administrador", ""),
            "motivo": decisao.get("Motivo", ""),
            "decidido_em": decisao.get("RegistradoEm", ""),
            "evento_id": decisao.get("EventoID", ""),
        })

    contagens = {
        "total": len(contas),
        "no_cla": sum(c["no_cla"] for c in contas),
        "ausentes": sum(not c["no_cla"] for c in contas),
        "habilitadas": sum(c.get("habilitada") == "TRUE" for c in contas),
        "bloqueadas": sum(c.get("habilitada") == "FALSE" for c in contas),
        "sem_decisao": sum(not c.get("habilitada") for c in contas),
        "inscritas": sum(c["inscrita"] for c in contas),
        "com_pontos": sum(c["pontos"] > 0 for c in contas),
    }
    return {
        "temporada": temporada,
        "temporada_nome": estado_mes.get("temporada_atual_nome", ""),
        "consultado_em": resultado["consultado_em"],
        "roster_em": roster.get("consultado_em", ""),
        "criterio": resultado["criterio"],
        "contagens": contagens,
        "contas": contas,
    }
