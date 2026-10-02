"""Página pública de planejamento; lê somente a projeção compartilhada."""
from collections import Counter
from datetime import datetime, timezone, timedelta
from .consultas import horario
from .planejamento_dados import TAG, ataques, data

ESTADOS = {'preparation': 'Preparação', 'inWar': 'Em andamento', 'warEnded': 'Encerrada',
           'ended': 'Encerrada', 'notInWar': 'Sem guerra comum'}


def hora_jogo(s):
    return horario(data(s).isoformat())


def distribuicao(membros):
    return Counter(m.get('townhallLevel', m.get('townHallLevel')) for m in membros)


def grafico(st, pd, elencos):
    rows = []
    for c in elencos:
        for cv, n in sorted(distribuicao(c['members']).items(), reverse=True):
            rows.append({'Clã': c['name'], 'CV': 'CV' + str(cv), 'Vilas': n, 'Nível': cv})
    if not rows:
        return
    st.vega_lite_chart(pd.DataFrame(rows), {
        'mark': 'bar', 'height': max(90, len(elencos) * 38),
        'encoding': {'y': {'field': 'Clã', 'type': 'nominal', 'sort': [c['name'] for c in elencos]},
                     'x': {'field': 'Vilas', 'type': 'quantitative', 'aggregate': 'sum', 'stack': 'zero'},
                     'color': {'field': 'CV', 'type': 'nominal', 'sort': 'descending',
                               'scale': {'scheme': 'tableau10'}},
                     'order': {'field': 'Nível', 'sort': 'descending'},
                     'tooltip': [{'field': 'Clã'}, {'field': 'CV'}, {'field': 'Vilas'}]},
    }, use_container_width=True)


def aviso_leitura(st, registro, minutos=20):
    st.caption('Consulta à Supercell: ' + horario(registro['consultado_em']) + ' · Brasília')
    if datetime.now(timezone.utc) - datetime.fromisoformat(registro['consultado_em']) > timedelta(minutes=minutos):
        st.warning('Esta leitura está desatualizada. Confira o horário antes de planejar os ataques.')


def resumo_guerra(st, g):
    cols = st.columns(2)
    for col, lado in zip(cols, ('clan', 'opponent')):
        c = g[lado]
        col.metric(c['name'], f"{c.get('stars', 0)} ★")
        col.caption(f"{c.get('attacks', 0)} ataques · {c.get('destructionPercentage', 0):.1f}% de destruição final")
    st.caption(f"{ESTADOS.get(g['state'], g['state'])} · {g['teamSize']} × {g['teamSize']} · "
               f"Início: {hora_jogo(g['startTime'])} · Fim previsto: {hora_jogo(g['endTime'])}")


def desempenho(st, pd, registro, chave):
    g = registro['dados']
    nomes = {s: g[s]['name'] for s in ('clan', 'opponent')}
    lado = st.radio('Clã analisado', list(nomes), format_func=nomes.get, horizontal=True, key=chave+'_lado')
    rows = ataques(g, lado)
    if not rows:
        st.info('Sem amostra de ataques nesta leitura. A taxa de sucesso aparecerá após os primeiros ataques.')
        return
    triplos = sum(r['Estrelas'] == 3 for r in rows)
    primeiros = [r for r in rows if r['Primeiro ataque']]
    cols = st.columns(3)
    cols[0].metric('Ataques de 3 estrelas', f'{100*triplos/len(rows):.1f}%')
    cols[0].caption(f'{triplos} de {len(rows)} ataques')
    cols[1].metric('Triplos no primeiro ataque', f"{100*sum(r['Estrelas']==3 for r in primeiros)/len(primeiros):.1f}%")
    cols[1].caption(f'{len(primeiros)} bases atacadas')
    limite = 1 if registro.get('tipo') == 'liga' else g.get('attacksPerMember', 2)
    cols[2].metric('Ataques não usados' if g['state'] == 'warEnded' else 'Ataques restantes',
                   max(0, g['teamSize'] * limite - len(rows)))
    recortes = []
    for nome, sinal in [('superior', 1), ('igual', 0), ('inferior', -1)]:
        amostra = [r for r in rows if ((r['CV alvo'] > r['CV atacante']) - (r['CV alvo'] < r['CV atacante'])) == sinal]
        n = sum(r['Estrelas'] == 3 for r in amostra)
        recortes.append({'Alvo': 'CV '+nome, 'Triplos / ataques': f'{n} / {len(amostra)}',
                         'Taxa': f'{100*n/len(amostra):.1f}%' if amostra else 'Sem amostra'})
    st.dataframe(pd.DataFrame(recortes), hide_index=True, use_container_width=True)
    busca = st.text_input('Buscar atacante, alvo ou tag', key=chave+'_busca').strip().casefold()
    visiveis = [{k: v for k, v in r.items() if not k.startswith('_')} for r in rows
                if not busca or busca in (r['Atacante']+' '+r['Alvo']+' '+r['Tag']+' '+r['_alvo']).casefold()]
    st.dataframe(pd.DataFrame(visiveis), hide_index=True, use_container_width=True)


def renderizar(st, documentos, pd):
    st.markdown('### Planejamento de guerras')
    st.caption('Compare os adversários e acompanhe os ataques. Estrelas do jogo não são pontos da competição dos passes.')
    d = documentos.get('planejamento')
    if not d:
        st.info('O primeiro levantamento de guerras está sendo preparado. Tente novamente em alguns minutos.')
        return
    if datetime.now(timezone.utc) - datetime.fromisoformat(d['publicado_em']) > timedelta(minutes=20):
        st.warning('Painel sem atualização recente. Os dados abaixo são da última leitura disponível.')
    if d.get('pendencias') or d.get('coleta_interrompida'):
        st.warning('Parte da consulta à Supercell está pendente. As últimas leituras válidas foram preservadas.')
    st.caption('Atualização compartilhada em aproximadamente cinco minutos; abrir a página não dispara novas consultas ao jogo.')
    tgrupo, tconfronto, tcomum, tdesempenho = st.tabs(['Liga · os 8 clãs', 'Confronto e vilas', 'Guerras comuns', 'Desempenho'])
    grupo = d.get('grupo')
    wars = d.get('guerras_liga', [])
    rodada = None
    with tgrupo:
        if not grupo:
            st.info('Grupo da liga ainda indisponível. As guerras comuns podem ser consultadas nas outras abas.')
        else:
            g = grupo['dados']
            aviso_leitura(st, grupo, 35)
            st.write('Temporada da liga: ' + g['season'] + ' · ' + ESTADOS.get(g['state'], g['state']))
            opcoes = list(range(1, len(g['rounds']) + 1))
            ativas = [r['rodada'] for r in wars if r['dados']['state'] == 'inWar']
            preparadas = [r['rodada'] for r in wars if r['dados']['state'] == 'preparation']
            padrao = max(ativas or preparadas or [1])
            rodada = st.selectbox('Rodada da liga', opcoes, index=opcoes.index(padrao), key='ww_plan_rodada')
            fonte = st.radio('Comparar', ['Escalação da rodada', 'Elenco inscrito'], horizontal=True, key='ww_plan_fonte')
            escolhidas = [r for r in wars if r['rodada'] == rodada]
            nossa_rodada = next((r for r in escolhidas if TAG in (r['dados']['clan']['tag'], r['dados']['opponent']['tag'])), None)
            if nossa_rodada:
                w = nossa_rodada['dados']
                nos = w['clan'] if w['clan']['tag'] == TAG else w['opponent']
                adversario = w['opponent'] if w['clan']['tag'] == TAG else w['clan']
                cols = st.columns(3)
                cols[0].metric('Situação da rodada', ESTADOS[w['state']])
                cols[1].metric('Adversário', adversario['name'])
                cols[2].metric('Formato', f"{w['teamSize']} × {w['teamSize']}")
                st.caption('Início: '+hora_jogo(w['startTime'])+' · fim previsto: '+hora_jogo(w['endTime']))
            elencos = g['clans'] if fonte == 'Elenco inscrito' else [r['dados'][s] for r in escolhidas for s in ('clan', 'opponent')]
            if not elencos:
                st.info('A API ainda não disponibilizou as escalações desta rodada.')
            else:
                if len(elencos) != 8:
                    st.warning(f'Cobertura parcial: {len(elencos)} de 8 clãs disponíveis nesta rodada.')
                if fonte != 'Elenco inscrito':
                    for r in escolhidas:
                        if datetime.now(timezone.utc)-datetime.fromisoformat(r['consultado_em']) > timedelta(minutes=20) and r['dados']['state'] != 'warEnded':
                            st.warning('Há escalações com leitura atrasada nesta comparação.')
                            break
                    st.caption('A escalação ainda pode mudar durante a preparação. Reservas não entram nesta comparação.')
                else:
                    st.caption('Inclui reservas; não representa necessariamente os jogadores da rodada nem os membros atuais do clã.')
                elencos = sorted(elencos, key=lambda c: sum(k*v for k,v in distribuicao(c['members']).items())/len(c['members']), reverse=True)
                grafico(st, pd, elencos)
                cvs = sorted({cv for c in elencos for cv in distribuicao(c['members'])}, reverse=True)
                tabela = []
                for c in elencos:
                    n = distribuicao(c['members'])
                    tabela.append({'Clã': c['name'] + (' · nós' if c['tag'] == TAG else ''), 'Tag': c['tag'],
                                   'Vilas': len(c['members']), **{'CV'+str(cv): n[cv] for cv in cvs}})
                st.dataframe(pd.DataFrame(tabela), hide_index=True, use_container_width=True)
                st.caption('Ordem por CV médio, não pela classificação da liga. CV não determina sozinho o vencedor.')
                with st.expander('Confrontos da rodada'):
                    for r in escolhidas:
                        w = r['dados']
                        st.text(f"{w['clan']['name']} × {w['opponent']['name']} · {ESTADOS[w['state']]}")
                        st.caption('Início: '+hora_jogo(w['startTime'])+' · leitura: '+horario(r['consultado_em']))
    with tconfronto:
        escolhidas = [r for r in wars if r['rodada'] == rodada]
        lados = {r['dados'][s]['tag']: (r, s) for r in escolhidas for s in ('clan', 'opponent')}
        nossa = lados.get(TAG)
        if not nossa:
            st.info('Selecione uma rodada disponível na aba Liga para comparar as vilas.')
        else:
            r, s = nossa
            inimigo = r['dados']['opponent' if s == 'clan' else 'clan']
            st.text('Adversário desta rodada: '+inimigo['name'])
            tags = list(lados)
            tag = st.selectbox('Clã para comparar', tags, index=tags.index(inimigo['tag']),
                               format_func=lambda t: lados[t][0]['dados'][lados[t][1]]['name'], key='ww_plan_inimigo')
            outro_r, outro_s = lados[tag]
            alvo = outro_r['dados'][outro_s]
            aviso_leitura(st, outro_r, 10**8 if outro_r['dados']['state']=='warEnded' else 20)
            st.caption('Rodada '+str(rodada)+' · '+ESTADOS[outro_r['dados']['state']])
            grafico(st, pd, [r['dados'][s], alvo] if tag != TAG else [alvo])
            busca = st.text_input('Buscar vila por nome ou tag', key='ww_plan_vila').strip().casefold()
            filtro = st.selectbox('Centro de vila', ['Todos'] + sorted(distribuicao(alvo['members']), reverse=True), key='ww_plan_cv')
            linhas = []
            for m in sorted(alvo['members'], key=lambda m:m['mapPosition']):
                if (filtro != 'Todos' and m['townhallLevel'] != filtro) or (busca and busca not in (m['name']+' '+m['tag']).casefold()):
                    continue
                defesa = m.get('bestOpponentAttack')
                linhas.append({'Posição': m['mapPosition'], 'Vila': m['name'], 'Tag': m['tag'], 'CV': m['townhallLevel'],
                               'Ataques usados': len(m.get('attacks', [])),
                               'Melhor ataque recebido': f"{defesa['stars']} ★ / {defesa['destructionPercentage']}%" if defesa else 'Sem ataque registrado'})
            st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)
            st.caption('Consulta de vilas; não reserva alvos nem altera a escalação no jogo.')
            if outro_r['dados']['state'] == 'preparation':
                st.caption('Durante a preparação, a API pode trazer posições não consecutivas do elenco. Os números são preservados como recebidos e podem mudar até o início da batalha.')
    with tcomum:
        atual = d.get('comum')
        if atual:
            aviso_leitura(st, atual)
            if atual['dados']['state'] == 'notInWar':
                st.info('Sem guerra comum em andamento na última consulta.')
            else:
                resumo_guerra(st, atual['dados'])
                desempenho(st, pd, {**atual, 'tipo': 'comum'}, 'ww_plan_comum_atual')
        else:
            st.info('Guerra comum ainda indisponível.')
        historico = d.get('historico_comum', [])
        if historico:
            with st.expander('Guerras comuns encerradas · últimas capturas disponíveis'):
                idx = st.selectbox('Guerra arquivada', range(len(historico)), format_func=lambda i:
                    hora_jogo(historico[i]['dados']['endTime'])+' · '+historico[i]['dados']['clan']['name']+' × '+historico[i]['dados']['opponent']['name'], key='ww_plan_hist')
                resumo_guerra(st, historico[idx]['dados'])
                st.caption('Histórico de planejamento. Não gera pontos retroativos nem substitui a auditoria da competição.')
                desempenho(st, pd, historico[idx], 'ww_plan_hist_perf')
    with tdesempenho:
        escolhidas = [r for r in wars if r['rodada'] == rodada]
        if escolhidas:
            indice = st.selectbox('Confronto para analisar', range(len(escolhidas)), format_func=lambda i:
                escolhidas[i]['dados']['clan']['name']+' × '+escolhidas[i]['dados']['opponent']['name'], key='ww_plan_perf_war')
            r = escolhidas[indice]
            aviso_leitura(st, r, 10**8 if r['dados']['state']=='warEnded' else 20)
            resumo_guerra(st, r['dados'])
            desempenho(st, pd, r, 'ww_plan_perf')
        else:
            st.info('Aguardando uma rodada disponível para analisar os ataques da liga.')
        with st.expander('Como interpretar as estatísticas'):
            st.write('Três estrelas: ataques com 3 estrelas divididos pelos ataques registrados. Primeiro ataque: primeira tentativa contra cada base, pela ordem do jogo. Estrelas novas: apenas o incremento sobre o melhor ataque anterior àquela base.')
            st.write('Resultados em andamento são parciais. Poucos ataques não permitem concluir a força de um jogador. A soma das estrelas de todos os ataques não é o placar final da guerra.')
        with st.expander('E as tropas mais usadas?'):
            st.write('O histórico recente de batalhas do jogador pode trazer códigos de exército, mas os ataques de guerra consultados não trazem essa composição. Por isso, este painel não atribui exércitos de batalhas comuns ou ranqueadas à liga. Essa análise depende de uma integração específica, ainda não publicada.')
