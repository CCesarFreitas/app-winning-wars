"""Compatibilidade com atualizações de arquivos sem reinício do Streamlit."""
import importlib
import inspect
from threading import RLock

_LOCK = RLock()


def obter_renderizador_feedback():
    with _LOCK:
        for nome in ('ww_competicao.desempenho_mensal', 'ww_competicao.desempenho_individual'):
            modulo=importlib.import_module(nome)
            if getattr(modulo,'FEEDBACK_VERSAO',0)<2:
                modulo=importlib.reload(modulo)
            if getattr(modulo,'FEEDBACK_VERSAO',0)<2:
                raise RuntimeError('Atualização da ficha incompleta; reinicie o aplicativo.')
        return obter_renderizador()


def obter_renderizador():
    # Atualizar primeiro a dependência. Não recarregar em cada rerun/sessão.
    with _LOCK:
        for nome in ('ww_competicao.desempenho_mensal',
                     'ww_competicao.relatorio_desempenho'):
            modulo = importlib.import_module(nome)
            if 'carregar_manuais' not in inspect.signature(modulo.renderizar).parameters:
                modulo = importlib.reload(modulo)
            if 'carregar_manuais' not in inspect.signature(modulo.renderizar).parameters:
                raise RuntimeError('Atualização do relatório incompleta; reinicie o aplicativo.')
        return modulo.renderizar
