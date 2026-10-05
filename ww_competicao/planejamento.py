"""Planejamento público responsivo; lê somente a projeção compartilhada."""
from collections import Counter
from datetime import datetime, timezone, timedelta
from html import escape

from .consultas import horario
from .planejamento_dados import TAG, ataques, data


ESTADOS = {
    'preparation': 'Preparação', 'inWar': 'Em andamento',
    'warEnded': 'Encerrada', 'ended': 'Encerrada',
    'notInWar': 'Sem guerra comum',
}


def hora_jogo(valor):
    return horario(data(valor).isoformat())


def distribuicao(membros):
    return Counter(m.get('townhallLevel', m.get('townHallLevel')) for m in membros)


def resumo_elenco(cla):
    dist = distribuicao(cla.get('members', []))
    total = sum(dist.values())
    return {
        'nome': cla.get('name', ''), 'tag': cla.get('tag', ''), 'vilas': total,
        'cv_medio': (sum(cv * quantidade for cv, quantidade in dist.items()) / total) if total else 0,
        'maior_cv': max(dist, default=0), 'distribuicao': sorted(dist.items(), reverse=True),
    }


def resumo_ataques(guerra, lado, tipo='liga'):
    linhas = ataques(guerra, lado)
    triplos = sum(linha['Estrelas'] == 3 for linha in linhas)
    limite = 1 if tipo == 'liga' else guerra.get('attacksPerMember', 2)
    total = guerra.get('teamSize', 0) * limite
    return {
        'linhas': linhas, 'usados': len(linhas), 'total': total,
        'restantes': max(0, total - len(linhas)), 'triplos': triplos,
        'taxa_triplos': (100 * triplos / len(linhas)) if linhas else 0,
    }


def composicao_clans(grupo, guerras, rodada):
    """Compara o elenco inscrito no grupo com a escalação real da rodada."""
    escalados = {}
    for registro in guerras:
        if registro.get('rodada') != rodada:
            continue
        guerra = registro.get('dados', {})
        for lado in ('clan', 'opponent'):
            cla = guerra.get(lado, {})
            if cla.get('tag'):
                escalados[cla['tag']] = distribuicao(cla.get('members', []))
    resultado = []
    for cla in grupo.get('clans', []):
        inscritos = Counter(m.get('townHallLevel') for m in cla.get('members', []))
        escala = escalados.get(cla['tag'])
        resultado.append({
            'nome': cla.get('name', cla['tag']), 'tag': cla['tag'],
            'inscritos': inscritos, 'total_inscritos': sum(inscritos.values()),
            'escalados': escala or Counter(),
            'total_escalados': sum(escala.values()) if escala is not None else None,
        })
    return sorted(resultado, key=lambda r: (r['tag'] != TAG, r['nome'].casefold()))


def perfil_ofensivo(guerras, clan_tag):
    """Resume ataques observados; a API não informa tropas ou feitiços usados."""
    linhas, rodadas = [], set()
    for registro in guerras:
        guerra = registro.get('dados', {})
        lado = next((lado for lado in ('clan', 'opponent')
                     if guerra.get(lado, {}).get('tag') == clan_tag), None)
        if lado is None:
            continue
        observados = ataques(guerra, lado)
        if observados:
            rodadas.add(registro.get('rodada'))
            linhas.extend(observados)
    relacoes = Counter()
    por_cv = {}
    for linha in linhas:
        diferenca = linha['CV alvo'] - linha['CV atacante']
        relacoes['CV superior' if diferenca > 0 else 'Mesmo CV' if diferenca == 0 else 'CV inferior'] += 1
        faixa = por_cv.setdefault(linha['CV atacante'], {'ataques': 0, 'triplos': 0, 'estrelas': 0})
        faixa['ataques'] += 1
        faixa['triplos'] += linha['Estrelas'] == 3
        faixa['estrelas'] += linha['Estrelas']
    total = len(linhas)
    duracoes = [l['Duração (s)'] for l in linhas if isinstance(l.get('Duração (s)'), (int, float))]
    return {
        'ataques': total, 'rodadas': len(rodadas),
        'triplos': sum(l['Estrelas'] == 3 for l in linhas),
        'taxa_triplos': 100 * sum(l['Estrelas'] == 3 for l in linhas) / total if total else 0,
        'estrelas_media': sum(l['Estrelas'] for l in linhas) / total if total else 0,
        'destruicao_media': sum(l['Destruição %'] for l in linhas) / total if total else 0,
        'duracao_media': sum(duracoes) / len(duracoes) if duracoes else None,
        'relacoes': relacoes, 'por_cv': por_cv, 'linhas': linhas,
    }


def filtrar_ataques(linhas, busca):
    termo = busca.strip().casefold()
    if not termo:
        return linhas
    return [linha for linha in linhas if termo in (
        linha['Atacante'] + ' ' + linha['Alvo'] + ' ' + linha['Tag'] + ' ' + linha['_alvo']
    ).casefold()]


def _css(st):
    st.markdown("""
    <style>
      .ww-plan-hero,.ww-plan-card,.ww-plan-attack{border:1px solid #334155;border-radius:16px;background:linear-gradient(145deg,#111827,#0f172a);padding:14px;margin:8px 0;color:#e2e8f0}
      .ww-plan-hero{border-color:#2563eb;background:linear-gradient(145deg,#172554,#0f172a)}
      .ww-plan-title{font-size:1.05rem;font-weight:850;color:#f8fafc;overflow-wrap:anywhere}
      .ww-plan-sub{font-size:.78rem;color:#94a3b8;margin-top:3px}
      .ww-plan-score{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:13px 0 8px}
      .ww-plan-side{width:42%;text-align:center}.ww-plan-side strong{display:block;font-size:1.7rem;color:#facc15}
      .ww-plan-vs{font-weight:900;color:#60a5fa}
      .ww-plan-bar{height:9px;border-radius:999px;background:#1e293b;overflow:hidden;margin:5px 0 3px}
      .ww-plan-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,#2563eb,#22d3ee)}
      .ww-plan-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin:8px 0}
      .ww-plan-chip{display:inline-block;padding:5px 9px;margin:3px;border:1px solid #475569;border-radius:999px;background:#1e293b;color:#e2e8f0;font-size:.78rem}
      .ww-plan-kpi{font-size:1.18rem;font-weight:850;color:#f8fafc}.ww-plan-label{font-size:.73rem;color:#94a3b8}
      .ww-plan-attack{padding:11px 12px}.ww-plan-attack strong{color:#f8fafc}.ww-plan-stars{color:#facc15;font-weight:900;white-space:nowrap}
      .ww-cwl-row{margin:12px 0 15px}.ww-cwl-head{display:flex;justify-content:space-between;gap:10px;font-size:.82rem;color:#e2e8f0;margin-bottom:5px}
      .ww-cwl-track{display:flex;height:27px;border-radius:9px;overflow:hidden;background:#1e293b;border:1px solid #334155}.ww-cwl-seg{display:flex;align-items:center;justify-content:center;min-width:0;font-size:.72rem;font-weight:850;color:#fff;text-shadow:0 1px 2px #000;overflow:hidden}
      .ww-cwl-empty{padding:5px 9px;border-radius:9px;background:#1e293b;color:#94a3b8;font-size:.76rem}.ww-plan-note{border-left:3px solid #38bdf8;background:#0c4a6e33;padding:10px 12px;border-radius:8px;color:#cbd5e1;font-size:.8rem;margin:10px 0}
      @media(max-width:600px){.ww-plan-hero,.ww-plan-card{padding:12px;border-radius:13px}.ww-plan-title{font-size:.96rem}.ww-plan-side strong{font-size:1.35rem}.ww-plan-grid{grid-template-columns:1fr 1fr}.ww-plan-sub{font-size:.72rem}}
    </style>
    """, unsafe_allow_html=True)


def aviso_leitura(st, registro, minutos=20):
    st.caption('Atualizado em ' + horario(registro['consultado_em']) + ' · Brasília')
    if datetime.now(timezone.utc) - datetime.fromisoformat(registro['consultado_em']) > timedelta(minutes=minutos):
        st.warning('Esta leitura está desatualizada. Confira o horário antes de planejar os ataques.')


def _barra(rotulo, valor, total):
    percentual = min(100, 100 * valor / total) if total else 0
    return (f'<div class="ww-plan-sub">{escape(rotulo)} · {valor}/{total}</div>'
            f'<div class="ww-plan-bar"><div class="ww-plan-fill" style="width:{percentual:.1f}%"></div></div>')


def resumo_guerra(st, guerra, tipo='liga'):
    nosso_lado = 'clan' if guerra['clan'].get('tag') == TAG else 'opponent'
    outro_lado = 'opponent' if nosso_lado == 'clan' else 'clan'
    nosso, outro = guerra[nosso_lado], guerra[outro_lado]
    nosso_ataques = resumo_ataques(guerra, nosso_lado, tipo)
    outro_ataques = resumo_ataques(guerra, outro_lado, tipo)
    st.markdown(f"""
      <div class="ww-plan-hero">
        <div class="ww-plan-title">{escape(ESTADOS.get(guerra['state'], guerra['state']))} · {guerra['teamSize']} × {guerra['teamSize']}</div>
        <div class="ww-plan-sub">Fim previsto: {escape(hora_jogo(guerra['endTime']))}</div>
        <div class="ww-plan-score">
          <div class="ww-plan-side">{escape(nosso['name'])}<strong>{nosso.get('stars',0)} ★</strong><span class="ww-plan-sub">{nosso.get('destructionPercentage',0):.1f}%</span></div>
          <div class="ww-plan-vs">×</div>
          <div class="ww-plan-side">{escape(outro['name'])}<strong>{outro.get('stars',0)} ★</strong><span class="ww-plan-sub">{outro.get('destructionPercentage',0):.1f}%</span></div>
        </div>
        {_barra('Nossos ataques', nosso_ataques['usados'], nosso_ataques['total'])}
        {_barra('Ataques do adversário', outro_ataques['usados'], outro_ataques['total'])}
      </div>
    """, unsafe_allow_html=True)


def _cartao_elenco(cla):
    resumo = resumo_elenco(cla)
    chips = ''.join(f'<span class="ww-plan-chip">CV {cv}: {qtd}</span>' for cv, qtd in resumo['distribuicao'])
    return f"""
      <div class="ww-plan-card">
        <div class="ww-plan-title">{escape(resumo['nome'])}</div>
        <div class="ww-plan-grid">
          <div><div class="ww-plan-kpi">{resumo['vilas']}</div><div class="ww-plan-label">vilas</div></div>
          <div><div class="ww-plan-kpi">{resumo['cv_medio']:.1f}</div><div class="ww-plan-label">CV médio</div></div>
          <div><div class="ww-plan-kpi">CV {resumo['maior_cv']}</div><div class="ww-plan-label">maior CV</div></div>
        </div>{chips}
      </div>
    """


def _cartao_vila(membro):
    defesa = membro.get('bestOpponentAttack')
    defesa_txt = f"{defesa['stars']} ★ · {defesa['destructionPercentage']}%" if defesa else 'Ainda sem ataque recebido'
    return f"""
      <div class="ww-plan-card">
        <div class="ww-plan-title">#{membro['mapPosition']} · {escape(membro['name'])}</div>
        <div class="ww-plan-sub">{escape(membro['tag'])} · CV {membro['townhallLevel']}</div>
        <div class="ww-plan-sub">Defesa: {escape(defesa_txt)}</div>
      </div>
    """


def _grafico_composicao(linhas, campo):
    totais = [sum(r[campo].values()) for r in linhas]
    maior = max(totais, default=1) or 1
    cvs = sorted({cv for r in linhas for cv in r[campo]}, reverse=True)
    paleta = ['#2563eb', '#0891b2', '#059669', '#65a30d', '#ca8a04', '#ea580c', '#dc2626', '#9333ea']
    cores = {cv: paleta[i % len(paleta)] for i, cv in enumerate(cvs)}
    legenda = ''.join(f'<span class="ww-plan-chip" style="border-color:{cores[cv]}">CV {cv}</span>' for cv in cvs)
    blocos = []
    for r in linhas:
        dist, total = r[campo], sum(r[campo].values())
        if total:
            segmentos = ''.join(
                f'<div class="ww-cwl-seg" title="CV {cv}: {qtd}" style="width:{100*qtd/total:.2f}%;background:{cores[cv]}">{qtd}</div>'
                for cv, qtd in sorted(dist.items(), reverse=True)
            )
            barra = f'<div class="ww-cwl-track" style="width:{100*total/maior:.2f}%">{segmentos}</div>'
        else:
            barra = '<div class="ww-cwl-empty">Escalação ainda indisponível</div>'
        destaque = ' · Winning Wars' if r['tag'] == TAG else ''
        blocos.append(f'<div class="ww-cwl-row"><div class="ww-cwl-head"><b>{escape(r["nome"])}</b><span>{total} vilas{destaque}</span></div>{barra}</div>')
    return legenda + ''.join(blocos)


def inteligencia_liga(st, grupo, guerras, rodada, adversario_padrao=None):
    linhas = composicao_clans(grupo, guerras, rodada)
    st.markdown('#### Composição dos oito clãs')
    st.caption('Compare o elenco inscrito na Liga com as vilas realmente escaladas na rodada selecionada.')
    visao = st.radio('Composição exibida', ['Inscritos na Liga', f'Escalados na rodada {rodada}'],
                     horizontal=True, key='ww_cwl_composicao')
    campo = 'inscritos' if visao == 'Inscritos na Liga' else 'escalados'
    st.markdown(_grafico_composicao(linhas, campo), unsafe_allow_html=True)
    st.caption('O comprimento da barra representa a quantidade total. Cada cor é um nível de CV; o número dentro da faixa é a quantidade de vilas.')

    adversarios = [r for r in linhas if r['tag'] != TAG]
    if not adversarios:
        return
    tags = [r['tag'] for r in adversarios]
    indice = tags.index(adversario_padrao) if adversario_padrao in tags else 0
    escolhido = st.selectbox('Analisar clã adversário', tags, index=indice,
        format_func=lambda tag: next(r['nome'] + ' · ' + tag for r in adversarios if r['tag'] == tag),
        key='ww_cwl_adversario')
    cla = next(r for r in adversarios if r['tag'] == escolhido)
    inscritos = ' · '.join(f'CV {cv}: {qtd}' for cv, qtd in sorted(cla['inscritos'].items(), reverse=True))
    escalados = (' · '.join(f'CV {cv}: {qtd}' for cv, qtd in sorted(cla['escalados'].items(), reverse=True))
                 or 'Ainda indisponível')
    st.markdown(f"""
      <div class="ww-plan-card">
        <div class="ww-plan-title">{escape(cla['nome'])}</div>
        <div class="ww-plan-sub"><b>Inscritos:</b> {escape(inscritos)}</div>
        <div class="ww-plan-sub"><b>Rodada {rodada}:</b> {escape(escalados)}</div>
      </div>
    """, unsafe_allow_html=True)

    perfil = perfil_ofensivo(guerras, escolhido)
    st.markdown('#### Padrão ofensivo observado')
    st.markdown('<div class="ww-plan-note"><b>Limite da API:</b> a Supercell não informa tropas, feitiços ou máquinas usados nos ataques. Estes indicadores usam somente ataques reais observados: CV, alvo, estrelas, destruição e duração.</div>', unsafe_allow_html=True)
    if not perfil['ataques']:
        st.info('Ainda não há ataques desse clã nas rodadas disponíveis.')
        return
    duracao = f"{perfil['duracao_media']:.0f}s" if perfil['duracao_media'] is not None else '—'
    st.markdown(f"""
      <div class="ww-plan-grid">
        <div class="ww-plan-card"><div class="ww-plan-kpi">{perfil['ataques']}</div><div class="ww-plan-label">ataques em {perfil['rodadas']} rodada(s)</div></div>
        <div class="ww-plan-card"><div class="ww-plan-kpi">{perfil['taxa_triplos']:.1f}%</div><div class="ww-plan-label">taxa de triplos</div></div>
        <div class="ww-plan-card"><div class="ww-plan-kpi">{perfil['destruicao_media']:.1f}%</div><div class="ww-plan-label">destruição média</div></div>
        <div class="ww-plan-card"><div class="ww-plan-kpi">{duracao}</div><div class="ww-plan-label">duração média</div></div>
      </div>
    """, unsafe_allow_html=True)
    relacoes = ''.join(f'<span class="ww-plan-chip">{escape(nome)}: {qtd}</span>'
                       for nome, qtd in perfil['relacoes'].items())
    por_cv = ''.join(
        f'<span class="ww-plan-chip">CV {cv}: {d["ataques"]} ataques · {d["triplos"]} triplos</span>'
        for cv, d in sorted(perfil['por_cv'].items(), reverse=True)
    )
    st.markdown('**Escolha de alvos observada**<br>' + relacoes, unsafe_allow_html=True)
    st.markdown('**Eficiência por CV atacante**<br>' + por_cv, unsafe_allow_html=True)
    if perfil['por_cv']:
        cv_mais_perigoso, dados = max(perfil['por_cv'].items(),
            key=lambda item: (item[1]['triplos'] / item[1]['ataques'], item[1]['ataques']))
        st.caption(f"Leitura defensiva: CV {cv_mais_perigoso} teve {dados['triplos']} triplos em {dados['ataques']} ataques observados. Priorize a revisão das bases que esse nível costuma enfrentar; a amostra aumenta a cada rodada.")


def desempenho(st, registro, chave):
    guerra = registro['dados']
    nomes = {lado: guerra[lado]['name'] for lado in ('clan', 'opponent')}
    padrao = 'clan' if guerra['clan'].get('tag') == TAG else 'opponent'
    lados = [padrao, 'opponent' if padrao == 'clan' else 'clan']
    lado = st.radio('Analisar', lados, format_func=nomes.get, horizontal=True, key=chave + '_lado')
    resumo = resumo_ataques(guerra, lado, registro.get('tipo', 'liga'))
    if not resumo['linhas']:
        st.info('Sem ataques nesta leitura. Os indicadores aparecerão após o primeiro ataque.')
        return
    st.markdown(f"""
      <div class="ww-plan-grid">
        <div class="ww-plan-card"><div class="ww-plan-kpi">{resumo['usados']}/{resumo['total']}</div><div class="ww-plan-label">ataques usados</div></div>
        <div class="ww-plan-card"><div class="ww-plan-kpi">{resumo['triplos']}</div><div class="ww-plan-label">ataques de 3 estrelas</div></div>
        <div class="ww-plan-card"><div class="ww-plan-kpi">{resumo['taxa_triplos']:.1f}%</div><div class="ww-plan-label">taxa de triplos</div></div>
        <div class="ww-plan-card"><div class="ww-plan-kpi">{resumo['restantes']}</div><div class="ww-plan-label">ataques restantes</div></div>
      </div>
    """, unsafe_allow_html=True)
    with st.expander('Ver ataques individuais'):
        busca = st.text_input('Buscar atacante, alvo ou tag', key=chave + '_busca').strip()
        linhas = filtrar_ataques(resumo['linhas'], busca)
        for linha in linhas:
            st.markdown(f"""
              <div class="ww-plan-attack">
                <strong>{escape(linha['Atacante'])}</strong> → {escape(linha['Alvo'])}
                <span class="ww-plan-stars"> · {linha['Estrelas']} ★</span>
                <div class="ww-plan-sub">CV {linha['CV atacante']} contra CV {linha['CV alvo']} · {linha['Destruição %']}% · estrelas novas: {linha['Estrelas novas']}</div>
              </div>
            """, unsafe_allow_html=True)
        if not linhas:
            st.info('Nenhum ataque encontrado para esta busca.')


def renderizar(st, documentos, pd=None):
    del pd
    _css(st)
    st.markdown('### Planejamento de guerras')
    st.caption('Primeiro, o confronto do Winning Wars. Detalhes ficam disponíveis sob demanda.')
    documento = documentos.get('planejamento')
    if not documento:
        st.info('O primeiro levantamento de guerras está sendo preparado. Tente novamente em alguns minutos.')
        return
    if datetime.now(timezone.utc) - datetime.fromisoformat(documento['publicado_em']) > timedelta(minutes=20):
        st.warning('Painel sem atualização recente. Os dados abaixo são da última leitura disponível.')
    if documento.get('pendencias') or documento.get('coleta_interrompida'):
        st.warning('Parte da consulta está pendente. As últimas leituras válidas foram preservadas.')

    grupo = documento.get('grupo')
    guerras = documento.get('guerras_liga', [])
    nossa_rodada, escolhidas = None, []
    agora_tab, liga_tab, adversario_tab, analise_tab, comum_tab = st.tabs([
        'Nossa guerra', 'Escalações da Liga', 'Adversário', 'Análise', 'Guerras comuns'
    ])
    if grupo:
        dados_grupo = grupo['dados']
        opcoes = list(range(1, len(dados_grupo['rounds']) + 1))
        ativas = [r['rodada'] for r in guerras if r['dados']['state'] == 'inWar']
        preparadas = [r['rodada'] for r in guerras if r['dados']['state'] == 'preparation']
        disponiveis = [r['rodada'] for r in guerras]
        padrao = max(ativas or preparadas or disponiveis or [1])
        rodada = st.selectbox('Rodada da Liga', opcoes, index=opcoes.index(padrao), key='ww_plan_rodada')
        escolhidas = [r for r in guerras if r['rodada'] == rodada]
        nossa_rodada = next((r for r in escolhidas if TAG in (r['dados']['clan']['tag'], r['dados']['opponent']['tag'])), None)

    with agora_tab:
        if not grupo:
            st.info('Grupo da Liga ainda indisponível.')
        elif not nossa_rodada:
            st.info('A guerra do Winning Wars ainda não está disponível nesta rodada.')
        else:
            aviso_leitura(st, nossa_rodada, 10**8 if nossa_rodada['dados']['state'] == 'warEnded' else 20)
            resumo_guerra(st, nossa_rodada['dados'], 'liga')
            with st.expander('Outros confrontos da rodada'):
                for registro in escolhidas:
                    guerra = registro['dados']
                    st.markdown(
                        f"**{escape(guerra['clan']['name'])}** {guerra['clan'].get('stars',0)} × "
                        f"{guerra['opponent'].get('stars',0)} **{escape(guerra['opponent']['name'])}**  "
                    )
                    st.caption(ESTADOS.get(guerra['state'], guerra['state']))

    with adversario_tab:
        if not nossa_rodada:
            st.info('Aguardando o confronto do Winning Wars nesta rodada.')
        else:
            guerra = nossa_rodada['dados']
            nosso_lado = 'clan' if guerra['clan']['tag'] == TAG else 'opponent'
            outro_lado = 'opponent' if nosso_lado == 'clan' else 'clan'
            st.markdown(_cartao_elenco(guerra[outro_lado]), unsafe_allow_html=True)
            busca = st.text_input('Buscar vila do adversário', key='ww_plan_vila').strip().casefold()
            membros = [m for m in sorted(guerra[outro_lado]['members'], key=lambda m: m['mapPosition'])
                       if not busca or busca in (m['name'] + ' ' + m['tag']).casefold()]
            for membro in membros:
                st.markdown(_cartao_vila(membro), unsafe_allow_html=True)

    with liga_tab:
        if not grupo:
            st.info('Aguardando o grupo da Liga para comparar os clãs.')
        else:
            adversario_padrao = None
            if nossa_rodada:
                g = nossa_rodada['dados']
                adversario_padrao = g['opponent']['tag'] if g['clan']['tag'] == TAG else g['clan']['tag']
            inteligencia_liga(st, dados_grupo, guerras, rodada, adversario_padrao)

    with analise_tab:
        if not nossa_rodada:
            st.info('Aguardando dados do confronto para calcular os indicadores.')
        else:
            aviso_leitura(st, nossa_rodada, 10**8 if nossa_rodada['dados']['state'] == 'warEnded' else 20)
            desempenho(st, {**nossa_rodada, 'tipo': 'liga'}, 'ww_plan_liga')

    with comum_tab:
        atual = documento.get('comum')
        if not atual or atual['dados']['state'] == 'notInWar':
            st.info('Sem guerra comum em andamento na última consulta.')
        else:
            aviso_leitura(st, atual)
            resumo_guerra(st, atual['dados'], 'comum')
            desempenho(st, {**atual, 'tipo': 'comum'}, 'ww_plan_comum')
        historico = documento.get('historico_comum', [])
        if historico:
            with st.expander('Guerras comuns encerradas'):
                indice = st.selectbox('Guerra arquivada', range(len(historico)), format_func=lambda i:
                    hora_jogo(historico[i]['dados']['endTime']) + ' · ' + historico[i]['dados']['clan']['name'] +
                    ' × ' + historico[i]['dados']['opponent']['name'], key='ww_plan_hist')
                resumo_guerra(st, historico[indice]['dados'], historico[indice].get('tipo', 'comum'))
