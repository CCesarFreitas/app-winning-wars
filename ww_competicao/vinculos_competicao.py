"""Vinculos explicitos, sem associacao automatica por nome."""
from datetime import datetime
from .participacao_competicao import pc_tag, pc_validar_admin, pc_ler_eventos, pc_estado

VC_ABA = "VinculosParticipantes"
VC_HEADER = ["EventoID", "ParticipanteID", "PlayerTag", "Administrador", "RegistradoEm"]


def vc_identidade(valor):
    """Sheets FORMULA pode devolver IDs numericos como int/float."""
    if type(valor) is int:
        if valor <= 0:
            raise ValueError("ID numerico invalido.")
        return str(valor)
    if type(valor) is float:
        if not valor.is_integer() or not 0 < valor <= 2**53 - 1:
            raise ValueError("ID numerico invalido.")
        return str(int(valor))
    if not isinstance(valor, str):
        raise ValueError("ID deve ser texto ou numero inteiro.")
    texto = valor.strip()
    if not texto or texto.startswith("=") or texto.upper() in {"TRUE", "FALSE"}:
        raise ValueError("ID vazio, calculado ou invalido.")
    return texto


def vc_registros(linhas, obrigatorios):
    if not linhas or len(set(linhas[0])) != len(linhas[0]) or not set(obrigatorios) <= set(linhas[0]):
        raise ValueError("Cabecalho de cadastro inesperado.")
    saida = []
    for linha in linhas[1:]:
        if not any(str(v).strip() for v in linha):
            continue
        if len(linha) > len(linhas[0]) and any(str(v).strip() for v in linha[len(linhas[0]):]):
            raise ValueError("Dados fora do cabecalho.")
        registro = dict(zip(linhas[0], linha + [""] * (len(linhas[0]) - len(linha))))
        for chave in ("ID", "ParticipanteID"):
            if chave in registro:
                registro[chave] = vc_identidade(registro[chave])
        saida.append(registro)
    return saida


def vc_estado(ranking, inscricoes, vinculos, controle):
    contas = pc_estado(pc_ler_eventos(controle))
    participantes = {}
    por_id, por_tag = {}, {}
    for r in vc_registros(ranking, ["ID", "Nome"]):
        identidade = r["ID"].strip()
        if not identidade or identidade in participantes or not isinstance(r["Nome"], str) or not r["Nome"].strip():
            raise ValueError("Participante sem ID/nome ou ID repetido.")
        participantes[identidade] = r["Nome"]

    def ligar(identidade, tag):
        if not identidade or pc_tag(tag) != tag:
            raise ValueError("Vinculo com ID ou tag invalido.")
        if identidade in por_id and por_id[identidade] != tag:
            raise ValueError("Um participante tem mais de uma tag; requer revisao.")
        if tag in por_tag and por_tag[tag] != identidade:
            raise ValueError("Uma conta foi vinculada a participantes diferentes; requer revisao.")
        por_id[identidade] = tag
        por_tag[tag] = identidade

    for r in vc_registros(inscricoes, ["ParticipanteID", "PlayerTag"]):
        # Todas as temporadas/status reservam o vinculo de identidade.
        ligar(r["ParticipanteID"].strip(), r["PlayerTag"])
    if not vinculos or vinculos[0] != VC_HEADER:
        raise ValueError("Cabecalho de vinculos inesperado.")
    eventos = {}
    for r in vc_registros(vinculos, VC_HEADER):
        if not all(isinstance(v, str) and v.strip() for v in r.values()):
            raise ValueError("Vinculo incompleto.")
        data = datetime.fromisoformat(r["RegistradoEm"])
        if data.tzinfo is None or data.utcoffset() is None:
            raise ValueError("Vinculo sem fuso horario.")
        if r["EventoID"] in eventos and eventos[r["EventoID"]] != r:
            raise ValueError("Identificador de vinculo reutilizado.")
        eventos[r["EventoID"]] = r
        ligar(r["ParticipanteID"], r["PlayerTag"])
    return dict(participantes=participantes, contas=contas, por_id=por_id, por_tag=por_tag, eventos=eventos)


def vc_preparar(ranking, inscricoes, vinculos, controle, admins, usuario, identidade, tag, evento_id, data):
    autor = pc_validar_admin(admins, usuario)
    estado = vc_estado(ranking, inscricoes, vinculos, controle)
    if identidade not in estado["participantes"] or tag not in estado["contas"]:
        raise ValueError("Participante ou conta nao encontrado. Atualize a lista.")
    if identidade in estado["por_id"] or tag in estado["por_tag"]:
        raise ValueError("Participante ou conta ja vinculado. Atualize a lista.")
    if evento_id in estado["eventos"]:
        raise ValueError("Identificador ja utilizado.")
    linha = [evento_id, identidade, tag, autor, data]
    vc_estado(ranking, inscricoes, vinculos + [linha], controle)
    return linha


def vc_confirmar(estado, linha):
    esperado = dict(zip(VC_HEADER, linha))
    encontrado = estado["eventos"].get(linha[0])
    if encontrado is not None and encontrado != esperado:
        raise ValueError("Vinculo registrado com dados divergentes.")
    return encontrado == esperado
