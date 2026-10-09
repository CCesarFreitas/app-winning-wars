"""Relatório administrativo de leitura. Não consulta API nem escreve pontos."""
import csv
import io
from datetime import datetime, timezone
from .consultas import FUSO, horario
from .participacao_competicao import pc_validar_admin

TIPOS = {'guerra': 'Guerra', 'liga': 'Liga', 'raide': 'Raide'}


def inteiro(valor):
    return type(valor) is int and valor >= 0


def data_fim(a):
    return datetime.strptime(a['fim'], '%Y%m%dT%H%M%S.%fZ').replace(tzinfo=timezone.utc)


def selecionar(documentos, inicio=None, fim=None, tipos=tuple(TIPOS), agora=None):
    agora = agora or datetime.now(timezone.utc)
    por_id, invalidos, duplicados = {}, 0, set()
    for chave, a in documentos.items():
        if not chave.startswith('atividade:'):
            continue
        try:
            quando = data_fim(a)
            if (a['tipo'] not in tipos or a['status'] not in {'APLICADO', 'AGUARDANDO_LANCAMENTO'}
                    or quando > agora):
                continue
            dia = quando.astimezone(FUSO).date()
            if (inicio and dia < inicio) or (fim and dia > fim):
                continue
            if a['id'] in por_id or a['id'] in duplicados:
                duplicados.add(a['id']); por_id.pop(a['id'], None)
                raise ValueError('Atividade duplicada')
            tags = [j['tag'] for j in a['jogadores']]
            if len(tags) != len(set(tags)):
                raise ValueError('Conta repetida na atividade')
            por_id[a['id']] = a
        except (KeyError, TypeError, ValueError):
            invalidos += 1
    return sorted(por_id.values(), key=lambda a: a['fim']), invalidos


def resumo(registros, minimo_amostra=3, referencia_triplos=50):
    guerras = [r for r in registros if r['tipo'] != 'raide']
    raids = [r for r in registros if r['tipo'] == 'raide']
    ataques = [at for r in guerras for at in r['jogador']['ataques']]
    estrelas = [a['Estrelas'] for a in ataques if inteiro(a.get('Estrelas')) and a['Estrelas'] <= 3]
    destruicao = [a['Destruição (%)'] for a in ataques if type(a.get('Destruição (%)')) in (int, float)
                  and 0 <= a['Destruição (%)'] <= 100]
    usados_guerra, limites_guerra, perdidos_guerra, sem_limite_guerra = 0, 0, 0, 0
    usados_raide, limites_raide, perdidos_raide, sem_limite_raide = 0, 0, 0, 0
    for r in registros:
        j = r['jogador']; raide = r['tipo'] == 'raide'
        usados = j.get('quantidade_ataques') if raide else len(j['ataques'])
        limite = j.get('limite_ataques')
        if not inteiro(usados) or not inteiro(limite) or limite < usados or limite == 0:
            if raide: sem_limite_raide += 1
            else: sem_limite_guerra += 1
            continue
        if raide:
            usados_raide += usados; limites_raide += limite; perdidos_raide += limite-usados
        else:
            usados_guerra += usados; limites_guerra += limite; perdidos_guerra += limite-usados
    n = len(estrelas)
    taxa = 100 * estrelas.count(3)/n if n else None
    saque = sum(r['jogador'].get('saque', 0) for r in raids if inteiro(r['jogador'].get('saque')))
    ataques_raide = sum(r['jogador'].get('quantidade_ataques', 0) for r in raids
                       if inteiro(r['jogador'].get('quantidade_ataques')))
    penalizados = sum(('Desconto' in a.get('Regra aplicada', '') or
                       'sem pontuação: havia alternativa' in a.get('Regra aplicada', '')) for a in ataques)
    pontos = [r['jogador']['pontos'] for r in registros if r['status'] == 'APLICADO'
              and inteiro(r['jogador'].get('pontos'))]
    alertas = []
    if perdidos_guerra: alertas.append(f'{perdidos_guerra} ataque(s) não utilizado(s) em guerra/liga')
    if perdidos_raide: alertas.append(f'{perdidos_raide} ataque(s) disponível(is) não utilizado(s) em raide')
    if penalizados: alertas.append(f'{penalizados} ataque(s) com penalização pela regra de CV')
    if n >= minimo_amostra and taxa < referencia_triplos:
        alertas.append('Taxa de três estrelas abaixo da referência escolhida; conferir os CVs dos alvos')
    return {'atividades': len(registros), 'escalacoes': len(guerras), 'ataques': len(ataques),
        'sem_ataque': sum(not r['jogador']['ataques'] for r in guerras), 'triplos': estrelas.count(3),
        'amostra_estrelas': n, 'taxa_triplos': taxa, 'media_estrelas': sum(estrelas)/n if n else None,
        'media_destruicao': sum(destruicao)/len(destruicao) if destruicao else None,
        'amostra_destruicao': len(destruicao), 'perdidos_guerra': perdidos_guerra,
        'uso_guerra': 100*usados_guerra/limites_guerra if limites_guerra else None,
        'sem_limite_guerra': sem_limite_guerra, 'raides': len(raids), 'ataques_raide': ataques_raide,
        'saque': saque, 'saque_por_ataque': saque/ataques_raide if ataques_raide else None,
        'perdidos_raide': perdidos_raide, 'uso_raide': 100*usados_raide/limites_raide if limites_raide else None,
        'sem_limite_raide': sem_limite_raide, 'penalizados': penalizados,
        'bonus': sum(r['jogador']['bonus'] for r in raids if inteiro(r['jogador'].get('bonus'))),
        'pontos': sum(pontos) if pontos else None, 'lancamentos_com_pontos': len(pontos),
        'alertas': alertas, 'amostra_pequena': n < minimo_amostra}


def construir(documentos, inicio=None, fim=None, tipos=tuple(TIPOS), minimo_amostra=3,
              referencia_triplos=50, agora=None):
    lista, invalidos = selecionar(documentos, inicio, fim, tipos, agora)
    atuais = {m['tag']: m for m in documentos.get('membros', {}).get('contas', [])}
    contas = {tag: {'tag': tag, 'nome': m['nome'], 'atual': True, 'registros': []}
              for tag, m in atuais.items()}
    for a in lista:
        for j in a['jogadores']:
            c = contas.setdefault(j['tag'], {'tag': j['tag'], 'nome': j['nome'], 'atual': False, 'registros': []})
            if not c['atual']: c['nome'] = j['nome']
            c['registros'].append({**{k: a.get(k) for k in
                ('id', 'tipo', 'fim', 'coluna', 'status', 'rodada', 'adversario')}, 'jogador': j})
    for c in contas.values():
        c['resumo'] = resumo(c['registros'], minimo_amostra, referencia_triplos)
    return {'contas': contas, 'atividades': lista, 'invalidos': invalidos}


def faixas_cv(registros):
    grupos = {k: [] for k in ['Superior', 'Igual', '1 abaixo', '2 ou mais abaixo', 'Não informado']}
    for r in registros:
        if r['tipo'] == 'raide': continue
        for a in r['jogador']['ataques']:
            atacante, alvo = a.get('CV atacante'), a.get('CV alvo')
            if not inteiro(atacante) or not inteiro(alvo): faixa = 'Não informado'
            else:
                d = alvo-atacante
                faixa = 'Superior' if d > 0 else 'Igual' if d == 0 else '1 abaixo' if d == -1 else '2 ou mais abaixo'
            grupos[faixa].append(a)
    return [{'CV do alvo': k, 'Ataques': len(v), 'Triplos': sum(a.get('Estrelas') == 3 for a in v),
             '3 estrelas (%)': round(100*sum(a.get('Estrelas') == 3 for a in v)/len(v), 1)}
            for k, v in grupos.items() if v]


def linhas_contas(contas):
    rows = []
    for c in contas:
        r = c['resumo']
        rows.append({'Vila': c['nome'], 'Tag': c['tag'], 'No clã na última consulta': 'Sim' if c['atual'] else 'Não',
            'Escalações guerra/liga': r['escalacoes'], 'Ataques guerra/liga': r['ataques'],
            'Escalações sem ataque': r['sem_ataque'], 'Ataques não usados guerra/liga': r['perdidos_guerra'] if r['escalacoes'] and not r['sem_limite_guerra'] else None,
            'Triplos': r['triplos'], '3 estrelas (%)': r['taxa_triplos'], 'Estrelas/ataque': r['media_estrelas'],
            'Penalizações CV': r['penalizados'], 'Raides registrados': r['raides'], 'Ataques raide': r['ataques_raide'],
            'Ataques não usados raide': r['perdidos_raide'] if r['raides'] and not r['sem_limite_raide'] else None,
            'Saque': r['saque'] if r['raides'] else None, 'Saque/ataque': r['saque_por_ataque'],
            'Bônus registrado': r['bonus'] if r['raides'] else None, 'Pontos registrados nas atividades': r['pontos'],
            'Acompanhamento': '; '.join(r['alertas']) or ('Sem amostra' if not r['atividades'] else 'Sem alerta pelos critérios selecionados')})
    return rows


def csv_seguro(rows):
    if not rows: return b''
    s = io.StringIO(); w = csv.DictWriter(s, fieldnames=list(rows[0])); w.writeheader()
    for row in rows:
        w.writerow({k: ("'"+v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@')) else v)
                    for k, v in row.items()})
    return s.getvalue().encode('utf-8-sig')


def renderizar(st, pd, documentos, admins, usuario):
    try: pc_validar_admin(admins, usuario)
    except (PermissionError, ValueError, KeyError, TypeError):
        st.info('Relatório disponível apenas para administradores autorizados.')
        return
    st.markdown('### Desempenho e colaboração dos membros')
    st.caption('Somente atividades encerradas. Análise por conta/tag; nomes não agrupam contas de uma mesma pessoa.')
    lista, _ = selecionar(documentos)
    if not lista:
        st.info('Ainda não há atividades encerradas disponíveis para este relatório.')
        return
    saude = documentos.get('saude', {})
    st.caption('Dados atualizados em ' + horario(saude.get('verificado_em')) + ' · Brasília')
    try: desatualizado = datetime.now(timezone.utc)-datetime.fromisoformat(saude['verificado_em'])
    except (KeyError, ValueError, TypeError): desatualizado = None
    if desatualizado is None or desatualizado.total_seconds() > 1200:
        st.warning('A atualização do histórico não está recente. Confira Integração antes de tomar decisões.')
    if saude.get('falhas_historico') or saude.get('atividades_sem_detalhe'):
        st.warning('Há atividades sem detalhe conferido. Este relatório pode estar incompleto.')
    datas = [data_fim(a).astimezone(FUSO).date() for a in lista]
    c1, c2 = st.columns(2)
    inicio = c1.date_input('Encerramento a partir de', min(datas), key='rd_inicio')
    fim = c2.date_input('Encerramento até', max(datas), key='rd_fim')
    if inicio > fim:
        st.warning('A data inicial deve ser anterior ou igual à final.'); return
    tipos = st.multiselect('Modalidades', list(TIPOS), default=list(TIPOS), format_func=TIPOS.get, key='rd_tipos')
    with st.expander('Critérios de acompanhamento e limites da análise'):
        minimo = st.number_input('Mínimo de ataques para sinalizar taxa de três estrelas', 1, 50, 3, key='rd_minimo')
        referencia = st.slider('Referência de três estrelas (%)', 0, 100, 50, key='rd_referencia')
        st.caption('Referências de gestão, não regras de pontuação. Compare CVs e contexto antes de concluir que alguém precisa melhorar. '
                   'Raide considera o limite disponível da captura, incluindo bônus; não presume seis ataques para todos. '
                   'Quem não aparece em um raide não é automaticamente marcado como faltoso. Saque por ataque depende dos alvos e não mede sozinho colaboração. '
                   'Jogos, Eventos, doações, reservas de alvo e composição de tropas não estão cobertos por este relatório.')
    escopo = st.radio('Contas', ['Membros atuais', 'Todas com histórico e membros atuais'], horizontal=True, key='rd_escopo')
    busca = st.text_input('Buscar membro por nome ou tag', key='rd_busca').strip().casefold()
    apenas = st.checkbox('Mostrar apenas contas com alertas', key='rd_alertas')
    modelo = construir(documentos, inicio, fim, tipos, minimo, referencia)
    if modelo['invalidos']: st.warning('Há registros inconsistentes excluídos da análise; conferir a integração.')
    membros_data = documentos.get('membros', {}).get('consultado_em')
    st.caption('Lista de membros consultada em ' + horario(membros_data) + '. Entradas e saídas recentes podem não aparecer.')
    contas = [c for c in modelo['contas'].values() if (escopo != 'Membros atuais' or c['atual'])
              and (not busca or busca in (c['nome']+' '+c['tag']).casefold()) and (not apenas or c['resumo']['alertas'])]
    contas.sort(key=lambda c: (-len(c['resumo']['alertas']), c['nome'].casefold(), c['tag']))
    if not contas:
        st.info('Nenhuma conta nesta seleção.'); return
    cols = st.columns(3)
    cols[0].metric('Contas na seleção', len(contas))
    cols[1].metric('Com alertas', sum(bool(c['resumo']['alertas']) for c in contas))
    cols[2].metric('Sem amostra no período', sum(not c['registros'] for c in contas))
    st.caption('Atividades no período: ' + ' · '.join(f'{TIPOS[t]}: {sum(a["tipo"] == t for a in modelo["atividades"])}' for t in tipos))
    tabela = linhas_contas(contas)
    compacto = ['Vila', 'Tag', 'Escalações sem ataque', '3 estrelas (%)', 'Penalizações CV',
                'Ataques não usados raide', 'Saque/ataque', 'Acompanhamento']
    st.dataframe(pd.DataFrame(tabela)[compacto].round(1), hide_index=True, use_container_width=True)
    with st.expander('Ver todas as métricas da seleção'):
        st.dataframe(pd.DataFrame(tabela).round(1), hide_index=True, use_container_width=True)
    st.download_button('Baixar relatório CSV', csv_seguro(tabela), file_name=f'desempenho_{inicio}_{fim}.csv',
                       mime='text/csv', key='rd_exportar')
    st.markdown('#### Ficha individual')
    por_tag = {c['tag']: c for c in contas}
    tag = st.selectbox('Membro', list(por_tag), format_func=lambda t: por_tag[t]['nome']+' · '+t, key='rd_membro')
    c = por_tag[tag]; r = c['resumo']
    for alerta in r['alertas']: st.warning(alerta)
    if not c['registros']:
        st.info('Sem registros nas atividades selecionadas. Isso não comprova ausência ou falta de colaboração.'); return
    if r['amostra_pequena']:
        st.info(f'Amostra pequena para avaliar ataques de guerra/liga: {r["amostra_estrelas"]} ataque(s).')
    if r['sem_limite_guerra'] or r['sem_limite_raide']:
        st.info('Algumas capturas ainda não informam os limites de ataques. Não foram estimadas faltas nesses registros.')
    for tipo in TIPOS:
        regs = [reg for reg in c['registros'] if reg['tipo'] == tipo]
        if not regs: continue
        s = resumo(regs, minimo, referencia)
        with st.expander(TIPOS[tipo] + f' · {len(regs)} atividade(s)', expanded=True):
            if tipo == 'raide':
                st.write(f"{s['ataques_raide']} ataques · {s['saque']:,} de saque · {s['bonus']} bônus registrado(s)")
                st.caption('Uso dos ataques disponíveis: ' + (f"{s['uso_raide']:.1f}%" if s['uso_raide'] is not None else 'Não informado'))
            else:
                st.write(f"{s['ataques']} ataques · {s['triplos']} triplos · {s['sem_ataque']} escalação(ões) sem ataque")
                st.caption('Uso dos ataques disponíveis: ' + (f"{s['uso_guerra']:.1f}%" if s['uso_guerra'] is not None else 'Não informado'))
                faixas = faixas_cv(regs)
                if faixas: st.dataframe(pd.DataFrame(faixas), hide_index=True, use_container_width=True)
            linhas = []
            for reg in regs:
                j = reg['jogador']
                linha = {'Fim (Brasília)': data_fim(reg).astimezone(FUSO).strftime('%d/%m/%Y %H:%M'),
                    'Atividade': reg['coluna'] or reg['id'], 'Adversário': reg.get('adversario'), 'Rodada': reg.get('rodada'),
                    'Ataques': j.get('quantidade_ataques', len(j['ataques'])), 'Limite disponível': j.get('limite_ataques'),
                    'Pontos registrados': j.get('pontos'), 'Situação': j['situacao']}
                if tipo == 'raide': linha.update(Saque=j.get('saque'), Bônus=j.get('bonus'))
                linhas.append(linha)
            st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)
            detalhes = [{'Atividade': reg['coluna'] or reg['id'], **a} for reg in regs for a in reg['jogador']['ataques']]
            if detalhes:
                st.write('Ataques, CVs e regras aplicadas')
                st.dataframe(pd.DataFrame(detalhes), hide_index=True, use_container_width=True)
    st.caption('Pontos registrados são os das atividades disponíveis, incluindo correções auditadas conhecidas; não representam necessariamente o total do ranking. '
               'Pontuação ausente não é zero. Os alertas não bloqueiam contas nem alteram pontos.')
