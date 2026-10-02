"""Correções explícitas: ponto e trilha no mesmo lote, sem alterar o lançamento original."""
import re
import uuid
from datetime import datetime, timezone
from .participacao_competicao import pc_validar_admin

ABA = 'RevisoesPontuacao'
HEADER = ['RevisaoID', 'Temporada', 'ParticipanteID', 'Nome', 'Atividade', 'Antes', 'Depois',
          'Administrador', 'Motivo', 'RegistradoEm']


def fotografar(planilha, ranking):
    abas = {k: planilha.worksheet(n) for k, n in {'ranking': ranking, 'estado': 'EstadoMes',
             'admins': 'Admins', 'revisoes': ABA}.items()}
    resposta = planilha.values_batch_get(["'" + w.title.replace("'", "''") + "'!A:ZZ" for w in abas.values()],
                                         params={'valueRenderOption': 'FORMULA'})
    foto = {k: r.get('values', []) for k, r in zip(abas, resposta['valueRanges'])}
    return foto, {k: w.id for k, w in abas.items()}


def preparar(foto, ids, usuario, pid, coluna, depois, motivo, revisao_id, agora):
    autor = pc_validar_admin(foto['admins'], usuario)
    if foto['revisoes'][:1] != [HEADER]:
        raise ValueError('Histórico de revisão indisponível')
    if any(str(r[0]) == revisao_id for r in foto['revisoes'][1:] if r):
        raise ValueError('Revisão já registrada; confira o resultado')
    pares = [r for r in foto['estado'][1:] if r]
    if any(len(r) < 2 for r in pares) or len({r[0] for r in pares}) != len(pares):
        raise ValueError('Estado do mês inconsistente')
    estado = dict((r[0], r[1]) for r in pares)
    if str(estado.get('mes_finalizado')).upper() != 'FALSE':
        raise ValueError('Mês fechado ou estado desconhecido')
    temporada = estado.get('temporada_atual_id', '')
    if not re.fullmatch(r'20\d{2}-(0[1-9]|1[0-2])', temporada):
        raise ValueError('Temporada inválida')
    limite = 3 if re.fullmatch(r'(Guerra|Liga)_\d+', coluna) else 7 if re.fullmatch(r'Raide_\d+', coluna) else None
    if limite is None:
        raise ValueError('Use o lançamento integrado para Jogos e Eventos')
    if type(depois) is not int or not 0 <= depois <= limite:
        raise ValueError('Pontuação fora do limite da modalidade')
    if not isinstance(motivo, str) or not 5 <= len(motivo.strip()) <= 500:
        raise ValueError('Informe uma justificativa de 5 a 500 caracteres')
    linhas = foto['ranking']
    if not linhas or len(set(linhas[0])) != len(linhas[0]):
        raise ValueError('Cabeçalhos inconsistentes')
    cab = linhas[0]
    idcol, nomecol, col = cab.index('ID'), cab.index('Nome'), cab.index(coluna)
    encontrados = [(i, r) for i, r in enumerate(linhas[1:], 1) if len(r) > idcol and str(r[idcol]) == str(pid)]
    if len(encontrados) != 1:
        raise ValueError('Participante ausente ou duplicado')
    linha, valores = encontrados[0]
    valor = valores[col] if len(valores) > col else ''
    if not re.fullmatch(r'\d+', str(valor)) or not 0 <= int(valor) <= limite:
        raise ValueError('Destino sem lançamento numérico válido; fórmulas não podem ser corrigidas aqui')
    antes = int(valor)
    if antes == depois:
        raise ValueError('A pontuação já tem esse valor')
    registro = [revisao_id, temporada, str(pid), str(valores[nomecol]), coluna, antes, depois,
                autor, motivo.strip(), agora]
    def celula(v):
        return {'userEnteredValue': {'numberValue': v} if type(v) is int else {'stringValue': str(v)}}
    lote = {'requests': [
        {'updateCells': {'range': {'sheetId': ids['ranking'], 'startRowIndex': linha, 'endRowIndex': linha+1,
                                  'startColumnIndex': col, 'endColumnIndex': col+1},
                         'rows': [{'values': [celula(depois)]}], 'fields': 'userEnteredValue'}},
        {'appendCells': {'sheetId': ids['revisoes'], 'rows': [{'values': [celula(v) for v in registro]}],
                         'fields': 'userEnteredValue'}}]}
    return {'registro': registro, 'lote': lote, 'pid': str(pid), 'coluna': coluna, 'depois': depois}


def conferir(foto, proposta):
    esperado = list(map(str, proposta['registro']))
    encontrados = [list(map(str, r)) for r in foto['revisoes'][1:] if r and str(r[0]) == esperado[0]]
    if encontrados != [esperado]:
        raise ValueError('Revisão não confirmada ou divergente. Não reenvie; peça conferência.')
    cab = foto['ranking'][0]
    linhas = [r for r in foto['ranking'][1:] if r and str(r[cab.index('ID')]) == proposta['pid']]
    if len(linhas) != 1 or str(linhas[0][cab.index(proposta['coluna'])]) != str(proposta['depois']):
        raise ValueError('Revisão registrada; o ranking mudou depois. Confira a trilha antes de outra correção.')


def renderizar(st, planilha, ranking, usuario, limpar):
    st.markdown('### Revisar pontos de uma atividade')
    st.caption('Guerra, Liga e Raide · preserva o lançamento original e registra valor anterior, novo valor, responsável e justificativa. Somente mês aberto.')
    sessao = st.session_state.setdefault('ww_revisao_v1', {})
    try:
        if sessao.get('pendente'):
            st.warning('Envio aguardando conferência. Não repita a correção.')
            if st.button('Conferir revisão enviada', key='ww_rev_conferir'):
                foto, _ = fotografar(planilha, ranking.title)
                pc_validar_admin(foto['admins'], usuario)
                conferir(foto, sessao['pendente'])
                sessao.clear()
                limpar()
                st.success('Revisão conferida sem novo envio.')
            return
        if st.button('Carregar pontos para revisão', key='ww_rev_carregar'):
            foto, ids = fotografar(planilha, ranking.title)
            pc_validar_admin(foto['admins'], usuario)
            sessao.clear()
            sessao.update(foto=foto, ids=ids)
        if 'foto' not in sessao:
            return
        foto, ids = sessao['foto'], sessao['ids']
        pc_validar_admin(foto['admins'], usuario)
        if len(foto['revisoes']) > 1:
            with st.expander('Histórico de revisões — responsáveis e justificativas'):
                st.dataframe([dict(zip(HEADER, r)) for r in foto['revisoes'][1:]], hide_index=True)
        cab = foto['ranking'][0]
        cols = [c for c in cab if re.fullmatch(r'(Guerra|Liga|Raide)_\d+', c)]
        if len(foto['ranking']) < 2 or not cols:
            st.info('Ainda não há pontuação de atividade disponível para revisão.')
            return
        pessoas = {str(r[cab.index('ID')]): str(r[cab.index('Nome')]) for r in foto['ranking'][1:] if r}
        with st.form('ww_rev_form'):
            pid = st.selectbox('Participante', list(pessoas), format_func=lambda p: pessoas[p]+' · ID '+p)
            coluna = st.selectbox('Atividade a corrigir', cols)
            valor = st.number_input('Pontuação correta', min_value=0, max_value=7, step=1)
            motivo = st.text_area('Justificativa da correção')
            revisar = st.form_submit_button('Revisar proposta')
        if revisar:
            sessao.pop('proposta', None)
            sessao['proposta'] = preparar(foto, ids, usuario, pid, coluna, int(valor), motivo,
                                         str(uuid.uuid4()), datetime.now(timezone.utc).isoformat())
        if sessao.get('proposta'):
            p = sessao['proposta']
            st.write(dict(zip(HEADER, p['registro'])))
            if st.button('Confirmar correção e registrar histórico', key='ww_rev_salvar'):
                atual, ids_atuais = fotografar(planilha, ranking.title)
                pc_validar_admin(atual['admins'], usuario)
                if atual != foto or ids_atuais != ids:
                    sessao.clear()
                    raise ValueError('Os dados mudaram. Carregue os pontos e revise novamente.')
                sessao['pendente'] = p
                planilha.batch_update(p['lote'])
                depois, _ = fotografar(planilha, ranking.title)
                conferir(depois, p)
                sessao.clear()
                limpar()
                st.success('Correção e histórico gravados e conferidos juntos.')
    except Exception as erro:
        st.error(str(erro))
