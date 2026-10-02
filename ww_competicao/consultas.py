"""Consultas públicas leves, alimentadas pelo observador da Oracle."""
from datetime import datetime, timezone, timedelta
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
    busca = st.text_input('Buscar jogador no resultado', key='ww_detalhe_busca').strip().casefold()
    jogadores = [j for j in a['jogadores'] if not busca or busca in (j['nome']+' '+j['tag']).casefold()]
    st.dataframe(pd.DataFrame([{'Vila': j['nome'], 'Tag': j['tag'], 'Pontos originais': j['pontos'],
        'Situação': j['situacao'], **({'Ataques': j['quantidade_ataques'], 'Saque': j['saque'], 'Bônus': j['bonus']}
        if a['tipo'] == 'raide' else {'CV': j['cv'], 'Pontos calculados': j['pontos_calculados']})}
        for j in jogadores]), hide_index=True, use_container_width=True)
    for j in jogadores:
        with st.expander(j['nome'] + ' · ' + j['tag']):
            st.write(j['situacao'])
            if j['ataques']:
                st.dataframe(pd.DataFrame(j['ataques']), hide_index=True, use_container_width=True)
            elif a['tipo'] != 'raide':
                st.write('Nenhum ataque registrado.')
            revisoes = [r for r in documentos.get('revisoes', []) if r['Temporada'] == a['temporada']
                        and str(r['ParticipanteID']) == str(j['participante_id']) and r['Atividade'] == a['coluna']]
            if revisoes:
                st.write('Correções posteriores ao lançamento:')
                st.dataframe([{'Antes': r['Antes'], 'Depois': r['Depois'], 'Data': horario(r['RegistradoEm'])}
                              for r in sorted(revisoes, key=lambda r: r['RegistradoEm'])], hide_index=True)
    st.caption('Pontos calculados mostram o desempenho. Pontos originais são os do lançamento oficial; ausência de lançamento não significa zero. Correções posteriores ficam na trilha de revisões.')


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
    linhas = [{'Atividade': a['coluna'] or a['tipo'], 'Modalidade': a['tipo'], 'Pontos originais': j['pontos'],
               'Situação': j['situacao']} for a in lista if a['temporada'] == mes for j in a['jogadores'] if j['tag'] == tag]
    st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)
    st.caption('Este extrato mostra atividades automáticas encerradas. O total atualizado, incluindo Jogos, Eventos e correções, está no ranking.')
