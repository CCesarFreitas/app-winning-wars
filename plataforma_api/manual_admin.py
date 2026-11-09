"""Consulta e simulacao sem escrita para Jogos do Cla e eventos manuais."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .conteudo import _linhas_planilha
from .participacao_admin import montar_participacao_admin
from .ranking_atual import montar_ranking_atual


HEADER = [
    "EventoID", "Temporada", "PlayerTag", "ParticipanteID", "Atividade",
    "ValorInformado", "Antes", "Depois", "Administrador", "RegistradoEm",
    "DetalhesJSON", "Hash",
]


def pontos_jogos(valor: int) -> int:
    if type(valor) is not int or not 0 <= valor <= 10000:
        raise ValueError("Informe um inteiro entre 0 e 10.000 pontos dos Jogos do Cla")
    return 10 if valor == 10000 else 5 if valor >= 4000 else 2 if valor >= 2000 else 0


def _hash(dados: list[str]) -> str:
    texto = json.dumps(dados, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(texto.encode()).hexdigest()


def _historico(linhas: list[list[str]], limite: int = 200) -> list[dict[str, Any]]:
    if not linhas:
        return []
    if linhas[0] != HEADER:
        raise ValueError("Auditoria manual com cabecalho inesperado")
    resultado = []
    ids = set()
    for numero, linha in enumerate(linhas[1:], 2):
        if not any(str(v).strip() for v in linha):
            continue
        if len(linha) != len(HEADER):
            raise ValueError(f"Auditoria manual incompleta na linha {numero}")
        valores = [str(v) for v in linha]
        registro = dict(zip(HEADER, valores))
        if registro["EventoID"] in ids:
            raise ValueError("Auditoria manual com evento duplicado")
        ids.add(registro["EventoID"])
        if registro["Hash"] != _hash(valores[:-1]):
            raise ValueError("Auditoria manual com hash divergente")
        if registro["Atividade"] not in {"JogosCla", "Eventos"}:
            raise ValueError("Auditoria manual com atividade invalida")
        resultado.append({
            chave: registro[chave] for chave in (
                "EventoID", "Temporada", "PlayerTag", "ParticipanteID",
                "Atividade", "ValorInformado", "Antes", "Depois",
                "Administrador", "RegistradoEm",
            )
        })
    return list(reversed(resultado[-limite:]))


def montar_manual_admin(caminho_sqlite: str) -> dict[str, Any]:
    participacao = montar_participacao_admin(caminho_sqlite)
    ranking = montar_ranking_atual(caminho_sqlite)
    pontos_por_tag = {r["tag"]: r for r in ranking["ranking"] if r.get("tag")}
    contas = []
    for conta in participacao["contas"]:
        pontos = pontos_por_tag.get(conta["tag"], {})
        contas.append({
            "tag": conta["tag"], "nome": conta["nome"], "cv": conta.get("cv"),
            "participante_id": conta.get("participante_id"),
            "habilitada": conta.get("habilitada"), "inscrita": conta["inscrita"],
            "no_cla": conta["no_cla"], "jogos": pontos.get("jogos", 0),
            "eventos": pontos.get("eventos", 0),
        })
    contas.sort(key=lambda c: (c["habilitada"] != "TRUE", c["nome"].casefold(), c["tag"]))
    return {
        "temporada": participacao["temporada"],
        "temporada_nome": participacao["temporada_nome"],
        "regras": {
            "jogos": "menos de 2.000 = 0; 2.000-3.999 = 2; 4.000-9.999 = 5; 10.000 = 10",
            "operacao": "O lançamento substitui o total da conta na atividade; não soma novamente.",
        },
        "contas": contas,
        "historico": _historico(_linhas_planilha("LancamentosManuais", ttl=60)),
        "modo": "SOMENTE_LEITURA",
    }


def propor_lancamento(caminho_sqlite: str, tag: str, atividade: str, valor: int) -> dict[str, Any]:
    foto = montar_manual_admin(caminho_sqlite)
    tag = str(tag).strip().upper()
    encontrados = [c for c in foto["contas"] if c["tag"] == tag]
    if len(encontrados) != 1:
        raise ValueError("Conta ausente ou duplicada")
    conta = encontrados[0]
    if atividade not in {"JogosCla", "Eventos"}:
        raise ValueError("Atividade manual invalida")
    if type(valor) is not int or valor < 0 or valor > 1_000_000:
        raise ValueError("Valor informado invalido")
    pontos = pontos_jogos(valor) if atividade == "JogosCla" else valor
    antes = int(conta["jogos"] if atividade == "JogosCla" else conta["eventos"])
    if conta.get("habilitada") == "FALSE":
        return {"status": "BLOQUEADO", "motivo": "bloqueio_administrativo",
                "conta": conta, "atividade": atividade, "informado": valor,
                "antes": antes, "depois": antes, "inscreveria": False}
    if not conta["inscrita"] and pontos == 0:
        status = "ZERO_SEM_INSCRICAO"
    else:
        status = "PROPOSTA_SEM_ENVIO"
    return {
        "status": status, "conta": conta, "atividade": atividade,
        "informado": valor, "antes": antes, "depois": pontos,
        "inscreveria": bool(not conta["inscrita"] and pontos > 0),
    }
