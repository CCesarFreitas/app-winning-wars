"""Consultas públicas leves, alimentadas pelo observador da Oracle."""
from datetime import datetime, timezone, timedelta
from html import escape
from zoneinfo import ZoneInfo
from .armazenamento import desempacotar

FUSO = ZoneInfo('America/Sao_Paulo')


def horario(valor):
    if not valor:
        return 'Ainda não registrado'
    try:
        return datetime.fromisoformat(valor).astimezone(FUSO).strftime('%d/%m/%Y %H:%M')
    except ValueError:
        return str(valor)


def ler(planilha):
    return desempacotar(planilha.worksheet('ConsultaPublica').get_all_values())


def renderizar_saude(st, documentos):
    st.markdown('### Saúde da integração')
    d = documentos.get('saude')
    if not d:
        st.info('Aguardando a primeira atualização do painel de integração.')
        return
    atrasada = datetime.now(timezone.utc) - datetime.fromisoformat(d['verificado_em']) > timedelta(minutes=20)
    if atrasada:
        st.warning('Painel sem atualização recente. Os estados abaixo podem estar desatualizados.')
    st.caption('Conferência do painel: ' + horario(d['verificado_em']) + ' · horários de Brasília')
    nomes = {'winning-wars-outubro-guerra.service': 'Monitor de guerras',
             'winning-wars-outubro-ciclo.timer': 'Agendamento de raides e Liga',
             'winning-wars-api.service': 'API do clã'}
    for nome, estado in d['servicos'].items():
        st.write(f"{'✅' if estado == 'active' else '⚠️'} {nomes.get(nome, nome)}: {'ativo' if estado == 'active' else estado}")
    guerra = d.get('guerra', {})
    st.write('Última consulta de guerra: ' + horario(guerra.get('registrado_em')))
    if guerra.get('registrado_em'):
        proxima = datetime.fromisoformat(guerra['registrado_em']) + timedelta(seconds=guerra['intervalo'])
        st.caption('Próxima consulta estimada de guerra: ' + horario(proxima.isoformat()))
        if datetime.now(timezone.utc) > proxima + timedelta(minutes=10) or guerra.get('status') != 'CONSULTA_CONCLUIDA':
            st.warning('A consulta de guerra precisa de conferência administrativa.')
    else:
        st.warning('Ainda não foi possível confirmar a última consulta de guerra.')
    ciclo = d.get('ciclo', {})
    st.write('Último ciclo de raides e Liga: ' + horario(ciclo.get('fim')))
    if ciclo.get('status') != 'CONCLUIDO' or (ciclo.get('fim') and
            datetime.now(timezone.utc) - datetime.fromisoformat(ciclo['fim']) > timedelta(hours=3)):
        st.warning('Ciclo de raides e Liga pendente, atrasado ou em revisão.')
    if any(e.get('status') == 'GRUPO_INDISPONIVEL_RECUPERADO_PELO_INDICE' for e in ciclo.get('etapas', [])):
        st.info('Grupo da Liga indisponível; consultadas as rodadas já conhecidas. Novas rodadas dependem da API do jogo.')
    st.write('Último lançamento automático: ' + horario(d.get('ultima_atividade')))
    st.caption('Ranking consultado em ' + horario(d.get('ranking_conferido_em')) + '. Consulta não significa alteração dos pontos.')
    if d.get('atividades_aguardando'):
        st.warning(f"{d['atividades_aguardando']} atividade(s) encerrada(s) aguardando lançamento ou revisão.")
    if d.get('falhas_historico') or d.get('atividades_sem_detalhe'):
        st.warning('Há detalhes de histórico que ainda não puderam ser conferidos. Os lançamentos originais continuam disponíveis.')
    if d.get('falha_membros'):
        st.warning('A última tentativa de atualizar os membros falhou. A lista anterior foi preservada.')


def renderizar_membros(st, documentos, pd):
    st.markdown('### Membros do clã principal')
    d = documentos.get('membros')
    if not d:
        st.info('Lista atual de membros ainda não disponível.')
        return
    st.caption('Consulta à Supercell: ' + horario(d['consultado_em']) + ' · atualização a cada oito horas.')
    if datetime.now(timezone.utc) - datetime.fromisoformat(d['consultado_em']) > timedelta(hours=9):
        st.warning('A lista de membros está desatualizada; uma entrada ou saída recente pode não aparecer.')
    st.caption('Estar no clã, estar habilitado e estar inscrito na competição são situações diferentes.')
    busca = st.text_input('Buscar vila por nome ou tag', key='ww_membros_busca').strip().casefold()
    filtro = st.selectbox('Participação na competição', ['Todas', 'Inscrito no mês', 'Ainda não inscrito', 'Bloqueada'], key='ww_membros_filtro')
    contas = [m for m in d['contas'] if (not busca or busca in (m['nome']+' '+m['tag']).casefold())
              and (filtro == 'Todas' or filtro in (m['competicao'], m['permissao']))]
    cargos = {'leader': 'Líder', 'coLeader': 'Colíder', 'admin': 'Ancião', 'member': 'Membro'}
    st.write(f"{len(d['contas'])} membros · {len(contas)} nesta seleção")
    st.dataframe(pd.DataFrame([{'Vila': m['nome'], 'Tag': m['tag'], 'CV': m['cv'],
        'Cargo': cargos.get(m['cargo'], m['cargo']), 'Competição': m['competicao'],
        'Permissão': m['permissao']} for m in contas]), hide_index=True, use_container_width=True)
    st.caption('Líder e colíderes podem habilitar ou bloquear contas em lote no Painel Admin → Participação. Bloqueios não apagam pontos anteriores.')


def atividades(documentos):
    agora = datetime.now(timezone.utc)
    resultado = []
    for chave, d in documentos.items():
        if not chave.startswith('atividade:'):
            continue
        try:
            fim = datetime.strptime(d['fim'], '%Y%m%dT%H%M%S.%fZ').replace(tzinfo=timezone.utc)
            if fim <= agora and d['status'] in ('APLICADO', 'AGUARDANDO_LANCAMENTO'):
                resultado.append(d)
        except (ValueError, KeyError, TypeError):
            continue
    return sorted(resultado, key=lambda d: d['fim'], reverse=True)


def _revisoes_do_jogador(documentos, atividade, jogador):
    return sorted([
        revisao for revisao in documentos.get('revisoes', [])
        if revisao['Temporada'] == atividade['temporada']
        and str(revisao['ParticipanteID']) == str(jogador['participante_id'])
        and revisao['Atividade'] == atividade['coluna']
    ], key=lambda revisao: revisao['RegistradoEm'])


def renderizar_explicacao(st, documentos, atividade, jogador, chave):
    pontos = jogador['pontos']
    pontos_texto = ('Pendente' if pontos is None else
                    f"{pontos} ponto{'s' if pontos != 1 else ''}")
    st.markdown(f"""
      <div style="border:1px solid #334155;border-radius:16px;padding:15px;background:linear-gradient(145deg,#172554,#0f172a);margin:8px 0">
        <div style="font-size:.78rem;color:#93c5fd">{escape(atividade['coluna'] or atividade['tipo'].capitalize())}</div>
        <div style="font-size:1.08rem;font-weight:850;color:#f8fafc;overflow-wrap:anywhere">{escape(jogador['nome'])}</div>
        <div style="font-size:2rem;font-weight:900;color:#facc15">{escape(pontos_texto)}</div>
        <div style="font-size:.82rem;color:#cbd5e1">{escape(jogador['situacao'])}</div>
      </div>
    """, unsafe_allow_html=True)
    if atividade['tipo'] == 'raide':
        colunas = st.columns(3)
        colunas[0].metric('Ataques', jogador['quantidade_ataques'])
        colunas[1].metric('Saque', jogador['saque'])
        colunas[2].metric('Bônus Top 3', 'Sim' if jogador['bonus'] else 'Não')
        st.caption('No raide, a pontuação considera os ataques usados e o bônus de saque previsto na regra da temporada.')
    elif jogador['ataques']:
        st.markdown('**Como os pontos foram calculados**')
        for numero, ataque in enumerate(jogador['ataques'], start=1):
            st.markdown(f"""
              <div style="border:1px solid #334155;border-radius:13px;padding:12px;margin:7px 0;background:#111827;color:#e2e8f0">
                <b>Ataque {numero}</b> · <span style="color:#facc15;font-weight:900">{ataque['Estrelas']} ★ → {ataque['Pontos do ataque']} ponto{'s' if ataque['Pontos do ataque'] != 1 else ''}</span><br>
                <small>Alvo {escape(ataque['Alvo'])} · CV {ataque['CV atacante']} contra CV {ataque['CV alvo']}</small><br>
                <small style="color:#93c5fd">{escape(ataque['Regra aplicada'])}</small>
              </div>
            """, unsafe_allow_html=True)
    elif atividade['tipo'] != 'raide':
        st.info('Nenhum ataque válido foi registrado para esta vila nesta atividade.')
    revisoes = _revisoes_do_jogador(documentos, atividade, jogador)
    if revisoes:
        with st.expander('Correções posteriores ao lançamento', expanded=True):
            for revisao in revisoes:
                st.write(f"{revisao['Antes']} → {revisao['Depois']} · {horario(revisao['RegistradoEm'])}")
    st.caption('A explicação usa a captura final conferida pelo motor. Motivos administrativos restritos não são publicados.')


def renderizar_detalhes(st, documentos, pd):
    st.markdown('### Desempenho das atividades encerradas')
    lista = atividades(documentos)
    if not lista:
        st.info('Ainda não há capturas encerradas de outubro disponíveis para detalhamento.')
        return
    meses = sorted({a['temporada'] for a in lista}, reverse=True)
    mes = st.selectbox('Mês', meses, key='ww_detalhe_mes')
    tipo = st.selectbox('Tipo de atividade', ['Todas', 'guerra', 'liga', 'raide'], key='ww_detalhe_tipo')
    lista = [a for a in lista if a['temporada'] == mes and (tipo == 'Todas' or a['tipo'] == tipo)]
    if not lista:
        st.info('Nenhuma atividade nesta seleção.')
        return
    indice = st.selectbox('Atividade encerrada', range(len(lista)), key='ww_detalhe_atividade',
        format_func=lambda i: f"{lista[i]['tipo'].capitalize()} · {lista[i]['coluna'] or 'Aguardando lançamento'} · {lista[i]['fim'][:8]}")
    a = lista[indice]
    if a['status'] == 'APLICADO':
        st.success('Resultado lançado e conferido com a captura usada pelo motor.')
    else:
        st.warning('Encerrada no jogo, aguardando lançamento ou revisão. Pontos ainda não atribuídos.')
    st.caption('Regra: ' + a['regra'])
    if not a['jogadores']:
        st.info('Nenhum jogador disponível nesta atividade.')
        return
    jogador = st.selectbox(
        'Escolha a vila para entender a pontuação', a['jogadores'],
        format_func=lambda j: j['nome'] + ' · ' + j['tag'], key='ww_detalhe_jogador'
    )
    renderizar_explicacao(st, documentos, a, jogador, 'ww_detalhe')


def renderizar_trajetoria(st, documentos, pd):
    st.markdown('### Meu desempenho por atividade')
    lista = atividades(documentos)
    pessoas = {j['tag']: j['nome'] for a in reversed(lista) for j in a['jogadores']}
    if not pessoas:
        st.info('Seu desempenho aparecerá aqui após o encerramento das primeiras atividades.')
        return
    tag = st.selectbox('Escolha sua vila (busque pelo nome ou tag)', sorted(pessoas),
                      format_func=lambda t: pessoas[t]+' · '+t, key='ww_trajetoria_vila')
    mes = st.selectbox('Temporada do desempenho', sorted({a['temporada'] for a in lista}, reverse=True), key='ww_trajetoria_mes')
    opcoes = [(a, j) for a in lista if a['temporada'] == mes for j in a['jogadores'] if j['tag'] == tag]
    if not opcoes:
        st.info('Nenhuma atividade automática encerrada para esta vila na temporada escolhida.')
        return
    escolha = st.selectbox(
        'Atividade para explicar', opcoes,
        format_func=lambda item: (f"{item[0]['coluna'] or item[0]['tipo']} · " +
                                  ('Pendente' if item[1]['pontos'] is None else
                                   f"{item[1]['pontos']} ponto(s)")),
        key='ww_trajetoria_atividade'
    )
    renderizar_explicacao(st, documentos, escolha[0], escolha[1], 'ww_trajetoria')
    st.caption('Jogos do Clã e Eventos aparecem no total do ranking e possuem auditoria própria de lançamento manual.')
