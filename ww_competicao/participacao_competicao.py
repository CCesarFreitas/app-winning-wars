"""Contrato compartilhado entre o app e a futura integracao do motor.

A aba e um historico de eventos acrescentados ao final, nunca uma tabela
reescrita pela sincronizacao. CADASTRO cria o padrao; ADMIN sempre prevalece.
A ordem das linhas define a ordem das decisoes administrativas.
"""
import re
import unicodedata
from datetime import datetime

PC_ABA = "ParticipacaoCompeticao"
PC_CABECALHO = [
    "EventoID", "PlayerTag", "Nome", "Habilitada", "Administrador",
    "Motivo", "RegistradoEm", "Origem",
]


def pc_tag(valor):
    if not isinstance(valor, str):
        raise ValueError("Tag ausente.")
    tag = valor.strip().upper()
    if not re.fullmatch(r"#[0289PYLQGRJCUV]+", tag):
        raise ValueError("Tag invalida.")
    return tag


def pc_validar_admin(linhas, usuario):
    if not isinstance(usuario, str) or not usuario.strip():
        raise PermissionError("Entre com uma conta administrativa autorizada.")
    if not linhas or len(set(linhas[0])) != len(linhas[0]):
        raise PermissionError("Nao foi possivel confirmar as permissoes.")
    cabecalho = linhas[0]
    if "Usuario" not in cabecalho or "Nivel" not in cabecalho:
        raise PermissionError("Cadastro de administradores incompleto.")
    encontrados = []
    for linha in linhas[1:]:
        dados = dict(zip(cabecalho, linha))
        if str(dados.get("Usuario", "")).strip().casefold() == usuario.strip().casefold():
            encontrados.append(dados)
    if len(encontrados) != 1:
        raise PermissionError("Administrador ausente ou cadastro duplicado.")
    nivel = str(encontrados[0].get("Nivel", "")).strip()
    nivel = "".join(
        c for c in unicodedata.normalize("NFKD", nivel)
        if not unicodedata.combining(c)
    ).casefold()
    if nivel not in {"dono", "lider", "co-lider", "colider"}:
        raise PermissionError("Somente dono, lider e colider podem gerir a participacao.")
    return str(encontrados[0]["Usuario"]).strip()


def pc_ler_eventos(linhas):
    if not linhas or linhas[0] != PC_CABECALHO:
        raise ValueError("Controle de participacao ausente ou com cabecalho diferente.")
    eventos = []
    ids = {}
    for numero, linha in enumerate(linhas[1:], 2):
        if not any(str(v).strip() for v in linha):
            continue
        if len(linha) != len(PC_CABECALHO) or not all(isinstance(v, str) for v in linha):
            raise ValueError(f"Linha {numero}: registro de participacao incompleto.")
        registro = dict(zip(PC_CABECALHO, linha))
        if any(not valor.strip() for valor in registro.values()):
            raise ValueError(f"Linha {numero}: campos obrigatorios ausentes.")
        if registro["PlayerTag"] != pc_tag(registro["PlayerTag"]):
            raise ValueError(f"Linha {numero}: tag fora do formato padrao.")
        if registro["Habilitada"] not in {"TRUE", "FALSE"}:
            raise ValueError(f"Linha {numero}: permissao invalida.")
        if registro["Origem"] not in {"CADASTRO", "ADMIN"}:
            raise ValueError(f"Linha {numero}: origem invalida.")
        data = datetime.fromisoformat(registro["RegistradoEm"])
        if data.tzinfo is None or data.utcoffset() is None:
            raise ValueError(f"Linha {numero}: data sem fuso.")
        identidade = registro["EventoID"]
        if identidade in ids:
            if ids[identidade] != registro:
                raise ValueError(f"Linha {numero}: identificador reutilizado com dados diferentes.")
            continue
        ids[identidade] = registro
        eventos.append(registro)
    return eventos


def pc_estado(eventos):
    contas = {}
    for evento in eventos:
        tag = evento["PlayerTag"]
        atual = contas.get(tag)
        if evento["Origem"] == "ADMIN" or atual is None or atual["Origem"] != "ADMIN":
            contas[tag] = dict(evento)
        # Um novo CADASTRO pode corrigir outro cadastro automatico/importado.
        # Depois da primeira decisao ADMIN, somente outro ADMIN pode altera-la.
    return contas


def pc_habilitada(linhas, tag):
    """Ausencia de cadastro nao significa permissao implicita para pontuar."""
    conta = pc_estado(pc_ler_eventos(linhas)).get(pc_tag(tag))
    if conta is None:
        raise ValueError("Conta ainda nao registrada no controle de participacao.")
    return conta["Habilitada"] == "TRUE"


def pc_preparar_alteracao(linhas, admins, usuario, tag, habilitada,
                         motivo, evento_anterior, evento_id, registrado_em):
    autor = pc_validar_admin(admins, usuario)
    if type(habilitada) is not bool:
        raise ValueError("A participacao deve ser habilitada ou desabilitada.")
    if not isinstance(motivo, str) or not 3 <= len(motivo.strip()) <= 500:
        raise ValueError("Informe um motivo de 3 a 500 caracteres.")
    tag = pc_tag(tag)
    eventos = pc_ler_eventos(linhas)
    atual = pc_estado(eventos).get(tag)
    if atual is None:
        raise ValueError("Conta nao encontrada no controle de participacao.")
    if atual["EventoID"] != evento_anterior:
        raise ValueError("Esta conta foi alterada por outro administrador. Atualize o painel.")
    if any(evento["EventoID"] == evento_id for evento in eventos):
        raise ValueError("Identificador de alteracao ja utilizado.")
    valor = "TRUE" if habilitada else "FALSE"
    if atual["Habilitada"] == valor:
        raise ValueError("A conta ja possui a participacao selecionada.")
    linha = [evento_id, tag, atual["Nome"], valor, autor, motivo.strip(), registrado_em, "ADMIN"]
    pc_ler_eventos([PC_CABECALHO, linha])
    return linha


def pc_confirmar_evento(linhas, linha_enviada):
    esperado = dict(zip(PC_CABECALHO, linha_enviada))
    for evento in pc_ler_eventos(linhas):
        if evento["EventoID"] == esperado["EventoID"]:
            if evento != esperado:
                raise ValueError("Alteracao registrada com dados divergentes.")
            return True
    return False
