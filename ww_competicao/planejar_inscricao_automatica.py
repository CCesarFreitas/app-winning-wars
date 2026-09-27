"""Plano puro de inscricao: nao consulta servicos nem grava dados.

O chamador deve validar captura, modalidade, encerramento e temporada aberta
ANTES de chamar esta funcao. O plano nao autoriza um envio por si so.
"""
from copy import deepcopy
from datetime import datetime
import re
import uuid
from .participacao_competicao import PC_CABECALHO, pc_estado, pc_ler_eventos, pc_tag
from .vinculos_competicao import VC_HEADER, vc_estado, vc_registros

IA_HEADER = ["Temporada", "ParticipanteID", "Nome", "PlayerTag", "Status", "AtualizadoEm", "AtualizadoPor"]

def planejar_inscricoes(temporada, jogadores, ranking, inscricoes, vinculos, controle, registrado_em):
    if not isinstance(temporada, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}", temporada):
        raise ValueError("Temporada invalida")
    datetime.strptime(temporada, "%Y-%m")
    if temporada < "2026-10":
        raise ValueError("Temporada anterior a integracao")
    data = datetime.fromisoformat(registrado_em)
    if data.utcoffset() is None:
        raise ValueError("Data sem fuso")
    if not inscricoes or inscricoes[0] != IA_HEADER:
        raise ValueError("Cabecalho de inscricoes inesperado")
    estado = vc_estado(ranking, inscricoes, vinculos, controle)
    registros = vc_registros(inscricoes, IA_HEADER)
    vistos_ids, vistos_tags, atuais = set(), set(), {}
    for registro in registros:
        mes = registro["Temporada"]
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}", mes):
            raise ValueError("Temporada de inscricao invalida")
        datetime.strptime(mes, "%Y-%m")
        tag, identidade = registro["PlayerTag"], registro["ParticipanteID"]
        if not registro["Nome"].strip() or registro["Status"] not in {"ATIVO", "INATIVO", "RASCUNHO"}:
            raise ValueError("Inscricao incompleta ou status invalido")
        if (mes, identidade) in vistos_ids or (mes, tag) in vistos_tags:
            raise ValueError("Inscricao duplicada na temporada")
        vistos_ids.add((mes, identidade))
        vistos_tags.add((mes, tag))
        if mes == temporada:
            atuais[tag] = registro
    if not isinstance(jogadores, list):
        raise ValueError("Jogadores devem ser uma lista")
    por_tag = {}
    for jogador in jogadores:
        tag = pc_tag(jogador["player_tag"])
        pontos = jogador["pontos"]
        if tag != jogador["player_tag"] or tag in por_tag:
            raise ValueError("Tag duplicada ou nao normalizada")
        if type(pontos) is not int or not 0 <= pontos <= 3:
            raise ValueError("Pontuacao de guerra invalida")
        if not isinstance(jogador.get("nome"), str) or not jogador["nome"].strip():
            raise ValueError("Nome da API ausente")
        por_tag[tag] = jogador
    ids_reservados = set(estado["participantes"]) | set(estado["por_id"])
    if any(not re.fullmatch(r"[1-9][0-9]*", identidade) for identidade in ids_reservados):
        raise ValueError("ID existente fora do formato numerico previsto")
    proximo_id = max((int(i) for i in ids_reservados), default=0) + 1
    sem_vinculo = sorted(set(estado["participantes"]) - set(estado["por_id"]))
    cabecalho = ranking[0]
    if cabecalho[:2] != ["ID", "Nome"]:
        raise ValueError("Ranking deve iniciar por ID e Nome")
    novas_linhas, novas_inscricoes, novos_vinculos, novas_contas = [], [], [], []
    participantes, excluidos = [], []
    contas = estado["contas"]
    for tag, jogador in sorted(por_tag.items()):
        pontos, nome = jogador["pontos"], jogador["nome"]
        if tag in contas and contas[tag]["Habilitada"] == "FALSE":
            excluidos.append({"tag": tag, "motivo": "bloqueio_administrativo"})
            continue
        inscricao = atuais.get(tag)
        if inscricao and inscricao["Status"] != "ATIVO":
            excluidos.append({"tag": tag, "motivo": "inscricao_nao_ativa_requer_revisao"})
            continue
        if not inscricao and pontos == 0:
            excluidos.append({"tag": tag, "motivo": "sem_primeira_pontuacao_positiva"})
            continue
        identidade = estado["por_tag"].get(tag)
        if identidade is None:
            # Sem tag nos cadastros legados, nao e possivel distinguir um novato
            # de um dos participantes que ainda aguardam migracao.
            if sem_vinculo:
                raise ValueError("MIGRACAO_PENDENTE: IDs sem tag: " + ", ".join(sem_vinculo))
            identidade = str(proximo_id)
            proximo_id += 1
        if identidade not in estado["participantes"]:
            novas_linhas.append([identidade, nome] + [0] * (len(cabecalho) - 2))
        if tag not in contas:
            eid = str(uuid.uuid5(uuid.NAMESPACE_URL, "winning-wars:participacao:cadastro:" + tag))
            novas_contas.append([eid, tag, nome, "TRUE", "integracao_automatica", "Primeira pontuacao valida", registrado_em, "CADASTRO"])
        if tag not in estado["por_tag"]:
            eid = str(uuid.uuid5(uuid.NAMESPACE_URL, "winning-wars:vinculo:auto:" + identidade + ":" + tag))
            novos_vinculos.append([eid, identidade, tag, "integracao_automatica", registrado_em])
        if not inscricao:
            novas_inscricoes.append([temporada, identidade, nome, tag, "ATIVO", registrado_em, "integracao_automatica"])
        participantes.append({"participante_id": identidade, "player_tag": tag, "nome": nome, "pontos": pontos})
    virtual = [deepcopy(ranking) + novas_linhas, deepcopy(inscricoes) + novas_inscricoes,
               deepcopy(vinculos) + novos_vinculos, deepcopy(controle) + novas_contas]
    vc_estado(*virtual)
    return {
        "status": "PLANO_INSCRICOES_SEM_GRAVACAO", "temporada": temporada,
        "participantes": participantes, "excluidos": excluidos,
        "novas_linhas_ranking": novas_linhas, "novas_inscricoes": novas_inscricoes,
        "novos_vinculos": novos_vinculos, "novos_eventos_participacao": novas_contas,
        "ranking_virtual": virtual[0], "inscricoes_virtuais": virtual[1],
        "vinculos_virtuais": virtual[2], "controle_virtual": virtual[3],
    }
