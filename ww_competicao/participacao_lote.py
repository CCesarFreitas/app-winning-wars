"""Decisoes em lote, mantendo um evento auditavel por conta."""
from uuid import UUID, uuid5
from .participacao_competicao import pc_preparar_alteracao, pc_confirmar_evento, pc_ler_eventos


def preparar_lote(linhas, admins, usuario, selecoes, habilitada, motivo, lote_id, data):
    if not isinstance(selecoes, dict) or not selecoes:
        raise ValueError("Selecione pelo menos uma conta.")
    namespace = UUID(lote_id)
    novas = []
    for tag, evento_anterior in sorted(selecoes.items()):
        novas.append(pc_preparar_alteracao(
            linhas, admins, usuario, tag, habilitada, motivo, evento_anterior,
            str(uuid5(namespace, tag)), data))
    pc_ler_eventos(linhas + novas)
    return novas


def conferir_lote(linhas, esperado):
    if not esperado:
        raise ValueError("Lote vazio.")
    return all(pc_confirmar_evento(linhas, linha) for linha in esperado)
