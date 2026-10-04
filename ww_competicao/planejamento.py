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
    agora_tab, adversario_tab, analise_tab, comum_tab = st.tabs([
        'Nossa guerra', 'Adversário', 'Análise', 'Guerras comuns'
    ])
    if grupo:
        dados_grupo = grupo['dados']
        opcoes = list(range(1, len(dados_grupo['rounds']) + 1))
        ativas = [r['rodada'] for r in guerras if r['dados']['state'] == 'inWar']
        preparadas = [r['rodada'] for r in guerras if r['dados']['state'] == 'preparation']
        padrao = max(ativas or preparadas or [1])
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
