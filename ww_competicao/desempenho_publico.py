"""Consulta individual pública, sem controles administrativos ou visão coletiva."""
from datetime import datetime, timezone
import importlib
from .relatorio_desempenho import selecionar, construir, data_fim
from .desempenho_mensal import periodo, MESES
from .consultas import FUSO, horario


def renderizar(st,pd,documentos,carregar_manuais=None):
    st.markdown('### Desempenho individual')
    st.caption('Consulta livre, sem login. Escolha uma vila para consultar e baixar seu desempenho mensal em atividades encerradas.')
    atividades,invalidos=selecionar(documentos)
    if not atividades:
        st.info('Ainda não há atividades encerradas disponíveis.');return
    meses=sorted({data_fim(a).astimezone(FUSO).strftime('%Y-%m') for a in atividades},reverse=True)
    mes=st.selectbox('Mês do desempenho',meses,format_func=lambda m:MESES[int(m[5:])-1]+'/'+m[:4],key='dp_mes')
    modelo=construir(documentos,*periodo(mes),['guerra','liga','raide'])
    contas=modelo['contas']
    tags=sorted(contas,key=lambda t:(contas[t]['nome'].casefold(),t))
    tag=st.selectbox('Selecione uma vila pelo nome ou pela tag',['']+tags,
        format_func=lambda t:'Escolha uma vila' if not t else contas[t]['nome']+' · '+t,key='dp_vila')
    if not tag:return
    saude=documentos.get('saude',{})
    try:atraso=(datetime.now(timezone.utc)-datetime.fromisoformat(saude['verificado_em'])).total_seconds()>1200
    except (KeyError,ValueError,TypeError):atraso=True
    if atraso or invalidos or saude.get('falhas_historico') or saude.get('atividades_sem_detalhe'):
        st.warning('O histórico pode estar desatualizado ou incompleto. Ausência de registro não comprova falta de participação.')
    # Apenas a vila selecionada chega ao relatório/download. Auditoria bruta não é exibida.
    def jogos_selecionados():
        return [r for r in carregar_manuais() if r.get('PlayerTag')==tag and r.get('Temporada')==mes and r.get('Atividade')=='JogosCla']
    from . import desempenho_individual as individual
    if getattr(individual,'FEEDBACK_VERSAO',0)<3:
        individual=importlib.reload(individual)
    individual.renderizar(st,pd,contas[tag],mes,horario(saude.get('verificado_em'))+' (Brasília)',
        jogos_selecionados if carregar_manuais else None,chave='dp_individual',publico=True)
