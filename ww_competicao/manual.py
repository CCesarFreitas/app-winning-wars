"""Lancamentos manuais por tag, com inscricao, bloqueio e auditoria atomicos."""
import hashlib
import json
import re
from copy import deepcopy
from datetime import datetime
from .participacao_competicao import pc_validar_admin, pc_tag
from .planejar_inscricao_automatica import planejar_inscricoes
from .vinculos_competicao import vc_registros

PLANILHA_ID = "1QTfVjrfSCVZ3JlqIDbhLHHBc2-anz8XhK9WzxU3v0oA"
ABA = "LancamentosManuais"
HEADER = ["EventoID", "Temporada", "PlayerTag", "ParticipanteID", "Atividade", "ValorInformado",
          "Antes", "Depois", "Administrador", "RegistradoEm", "DetalhesJSON", "Hash"]


def pontos_jogos(valor):
    if type(valor) is not int or not 0 <= valor <= 10000:
        raise ValueError("Informe um inteiro entre 0 e 10.000 pontos dos Jogos do Cla.")
    return 10 if valor == 10000 else 5 if valor >= 4000 else 2 if valor >= 2000 else 0


def hash_json(dados):
    return hashlib.sha256(json.dumps(dados, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def preparar(fotos, metas, admin, tag, nome, atividade, valor, evento, agora):
    admin = pc_validar_admin(fotos["admins"]["valores"], admin)
    tag = pc_tag(tag)
    if not isinstance(evento, str) or not re.fullmatch(r"[0-9a-f-]{36}", evento):
        raise ValueError("Identificador do lancamento invalido")
    if datetime.fromisoformat(agora).utcoffset() is None:
        raise ValueError("Data sem fuso")
    estado_linhas = vc_registros(fotos["estado"]["valores"], ["Chave", "Valor"])
    estado = {r["Chave"]: r["Valor"] for r in estado_linhas}
    temporada = estado.get("temporada_atual_id", "")
    if (len(estado) != len(estado_linhas) or not re.fullmatch(r"\d{4}-\d{2}", temporada)
            or temporada < "2026-10" or estado.get("mes_finalizado", "").upper() != "FALSE"):
        raise ValueError("Este painel exige temporada aberta a partir de outubro/2026.")
    datetime.strptime(temporada, "%Y-%m")
    if atividade not in {"JogosCla", "Eventos"}:
        raise ValueError("Use este painel para Jogos do Cla ou Eventos.")
    if type(valor) is not int or valor < 0 or valor > 1000000:
        raise ValueError("Pontuacao invalida")
    pontos = pontos_jogos(valor) if atividade == "JogosCla" else valor
    fontes = ("ranking", "inscricoes", "vinculos", "participacao")
    plano = planejar_inscricoes(temporada, [{"player_tag": tag, "nome": nome, "pontos": int(pontos > 0)}],
        *(fotos[n]["valores"] for n in fontes), agora)
    if plano["excluidos"]:
        motivo = plano["excluidos"][0]["motivo"]
        if motivo == "sem_primeira_pontuacao_positiva":
            return {"status": "ZERO_SEM_INSCRICAO", "pontos": 0}
        raise ValueError("Lancamento bloqueado: " + motivo)
    identidade = plano["participantes"][0]["participante_id"]
    ranking = fotos["ranking"]["valores"]
    if atividade not in ranking[0]:
        raise ValueError("Coluna de pontuacao ausente: " + atividade)
    coluna = ranking[0].index(atividade)
    novas = dict(ranking=plano["novas_linhas_ranking"], inscricoes=plano["novas_inscricoes"],
        vinculos=plano["novos_vinculos"], participacao=plano["novos_eventos_participacao"])
    indices = [i for i, r in enumerate(plano["ranking_virtual"]) if i and r and str(r[0]) == identidade]
    if len(indices) != 1:
        raise ValueError("ID ausente ou duplicado")
    indice = indices[0]
    antes = 0
    if indice < len(ranking):
        for modo in ("valores", "formulas"):
            r = fotos["ranking"][modo][indice]
            v = str(r[coluna]) if len(r) > coluna else ""
            if v and not re.fullmatch(r"\d+", v):
                raise ValueError("Pontuacao atual invalida ou formula; revisar antes de alterar")
            if modo == "valores":
                antes = int(v or 0)
            elif int(v or 0) != antes:
                raise ValueError("Valor e formula divergem")
    ledger = fotos["manual"]["valores"]
    if ledger[0] != HEADER or ledger != fotos["manual"]["formulas"]:
        raise ValueError("Auditoria manual invalida ou contem formulas")
    eventos = vc_registros(ledger, HEADER)
    if any(r["EventoID"] == evento for r in eventos):
        raise ValueError("Evento ja registrado; conferir antes de reenviar")
    if len({r["EventoID"] for r in eventos}) != len(eventos):
        raise ValueError("Auditoria com evento duplicado")
    pedidos = []
    ids = [m["id"] for m in metas.values()]
    if len(ids) != len(set(ids)):
        raise ValueError("Abas com identificador repetido")
    for n in (*fontes, "manual"):
        f = fotos[n]
        if not f["valores"] or f["valores"][0] != f["formulas"][0]:
            raise ValueError("Cabecalho invalido: " + n)
        if n != "ranking" and f["valores"] != f["formulas"]:
            raise ValueError("Formula em cadastro: " + n)
        if any(any(str(v).strip() for v in r) for r in f["formulas"][len(f["valores"]):]):
            raise ValueError("Formula ou conteudo no destino: " + n)
        if any(any(str(v).strip() for v in r[len(f["valores"][0]):]) for modo in ("valores", "formulas") for r in f[modo]):
            raise ValueError("Conteudo fora do cabecalho: " + n)
    def escrever(n, linha, col, linhas):
        pedidos.append({"updateCells": {"start": {"sheetId": metas[n]["id"], "rowIndex": linha, "columnIndex": col},
            "rows": [{"values": [{"userEnteredValue": {"numberValue": v} if type(v) is int else {"stringValue": str(v)}} for v in r]} for r in linhas],
            "fields": "userEnteredValue"}})
    def expandir(n, final):
        if final > metas[n]["linhas"]:
            pedidos.append({"appendDimension": {"sheetId": metas[n]["id"], "dimension": "ROWS", "length": final - metas[n]["linhas"]}})
    if metas["manual"].get("nova"):
        pedidos.append({"addSheet": {"properties": {"sheetId": metas["manual"]["id"], "title": ABA,
            "gridProperties": {"rowCount": 1000, "columnCount": len(HEADER)}}}})
        escrever("manual", 0, 0, [HEADER])
    for n, linhas in novas.items():
        if linhas:
            if any(len(r) != len(fotos[n]["valores"][0]) for r in linhas):
                raise ValueError("Novo cadastro com tamanho divergente")
            expandir(n, len(fotos[n]["valores"]) + len(linhas))
            escrever(n, len(fotos[n]["valores"]), 0, linhas)
    escrever("ranking", indice, coluna, [[pontos]])
    detalhes = {"novas_linhas": novas, "nome": nome, "regra": "jogos-outubro-2026" if atividade == "JogosCla" else "evento-manual",
        "operacao": "substituir_total", "planilha_id": PLANILHA_ID}
    linha = [evento, temporada, tag, identidade, atividade, str(valor), str(antes), str(pontos), admin, agora,
        json.dumps(detalhes, ensure_ascii=False, separators=(",", ":")), ""]
    linha[-1] = hash_json(linha[:-1])
    expandir("manual", len(ledger) + 1)
    escrever("manual", len(ledger), 0, [linha])
    return {"status": "PREPARADO", "lote": {"requests": pedidos}, "registro": linha,
        "id": identidade, "tag": tag, "nome": nome, "atividade": atividade, "valor": valor,
        "antes": antes, "pontos": pontos, "temporada": temporada,
        "novos": {n: len(r) for n, r in novas.items()}}


def conferir(fotos, proposta):
    esperado = proposta["registro"]
    for modo in ("valores", "formulas"):
        tabela = fotos["manual"][modo]
        if tabela[0] != HEADER:
            raise ValueError("Cabecalho de auditoria divergente")
        encontrados = [r for r in tabela[1:] if r and r[0] == esperado[0]]
        if encontrados != [esperado] or hash_json(esperado[:-1]) != esperado[-1]:
            raise ValueError("Registro nao confirmado; nao reenviar automaticamente")
        ranking = fotos["ranking"][modo]
        col = ranking[0].index(proposta["atividade"])
        linhas = [r for r in ranking[1:] if r and str(r[0]) == proposta["id"]]
        if len(linhas) != 1 or len(linhas[0]) <= col or str(linhas[0][col]) != str(proposta["pontos"]):
            raise ValueError("Pontos divergentes; revisar sem sobrescrever")
        for n, novas in json.loads(esperado[10])["novas_linhas"].items():
            if n != "ranking" and any([str(v) for v in r] not in fotos[n][modo] for r in novas):
                raise ValueError("Cadastro nao confirmado: " + n)
    return True


def fotografar(planilha, ranking_titulo):
    if planilha.id != PLANILHA_ID or planilha.title != "WinningWars_DB":
        raise ValueError("Planilha diferente da base oficial configurada")
    titulos = {"ranking": ranking_titulo, "inscricoes": "InscricoesTemporada", "vinculos": "VinculosParticipantes",
        "participacao": "ParticipacaoCompeticao", "estado": "EstadoMes", "admins": "Admins", "manual": ABA}
    abas = {a.title: a for a in planilha.worksheets()}
    selecionadas = {n: t for n, t in titulos.items() if t in abas}
    if set(titulos) - set(selecionadas) - {"manual"}:
        raise ValueError("Abas de integracao ausentes")
    fotos = {n: {} for n in selecionadas}
    def texto(v):
        if type(v) is bool:
            return "TRUE" if v else "FALSE"
        return str(int(v)) if type(v) is float and v.is_integer() else str(v)
    for chave, modo in (("valores", "FORMATTED_VALUE"), ("formulas", "FORMULA")):
        ranges = ["'" + t.replace("'", "''") + "'" for t in selecionadas.values()]
        partes = planilha.values_batch_get(ranges, params={"valueRenderOption": modo}).get("valueRanges", [])
        if len(partes) != len(ranges):
            raise ValueError("Leitura incompleta")
        for n, p in zip(selecionadas, partes):
            fotos[n][chave] = [[texto(v) for v in r] for r in p.get("values", [])]
    metas = {n: {"id": abas[t].id, "linhas": abas[t].row_count, "colunas": abas[t].col_count}
        for n, t in selecionadas.items() if n not in ("estado", "admins")}
    if "manual" not in fotos:
        fotos["manual"] = {m: [HEADER[:]] for m in ("valores", "formulas")}
        metas["manual"] = {"id": max(a.id for a in abas.values()) + 1, "linhas": 1000, "colunas": len(HEADER), "nova": True}
    return fotos, metas
