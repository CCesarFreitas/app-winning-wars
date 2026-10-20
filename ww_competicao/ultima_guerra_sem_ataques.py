"""Indicador administrativo: apenas zero ataques na última guerra comum encerrada."""
from datetime import datetime, timezone
from .planejamento_dados import TAG, data, validar_guerra
from .consultas import FUSO, horario
from .participacao_competicao import pc_validar_admin


def analisar(documentos, agora=None):
    agora = agora or datetime.now(timezone.utc)
    p = documentos.get('planejamento') or {}
    candidatas = []
    for registro in [p.get('comum')] + list(p.get('historico_comum') or []):
        if not registro:
            continue
        g = registro.get('dados', {})
        if registro.get('tipo', 'comum') != 'comum' or g.get('state') != 'warEnded':
            continue
        # Não substitui uma captura encerrada inválida por uma guerra antiga.
        fim = data(g['endTime'])
        if fim > agora:
            raise ValueError('Encerramento futuro')
        candidatas.append((fim, registro.get('consultado_em', ''), g))
    if not candidatas:
        return None
    _, _, g = max(candidatas, key=lambda r: (r[0], r[1]))
    validar_guerra(g)
    if g.get('attacksPerMember') != 2:
        raise ValueError('Guerra sem confirmação de dois ataques por vila')
    lado = 'clan' if g['clan']['tag'] == TAG else 'opponent'
    nosso, outro = g[lado], g['opponent' if lado == 'clan' else 'clan']
    # A ausência do campo attacks é o formato normal da API para quem não atacou.
    # Exige total agregado para distinguir zero de uma captura incompleta.
    if type(nosso.get('attacks')) is not int:
        raise ValueError('Total de ataques ausente')
    atuais = documentos.get('membros', {})
    tags = {m['tag'] for m in atuais.get('contas', [])}
    rows = []
    for m in sorted(nosso['members'], key=lambda m: m['mapPosition']):
        if m.get('attacks', []):
            continue
        rows.append({'Posição na guerra': m['mapPosition'], 'Vila': m['name'],
                     'Tag': m['tag'], 'CV': m['townhallLevel'], 'Ataques realizados': 0,
                     'No clã na última consulta': ('Não informado' if not atuais.get('consultado_em')
                         else 'Sim' if m['tag'] in tags else 'Não consta')})
    return {'fim': data(g['endTime']).astimezone(FUSO), 'adversario': outro.get('name', outro['tag']),
            'adversario_tag': outro['tag'], 'escaladas': len(nosso['members']), 'vilas': rows,
            'membros_em': atuais.get('consultado_em'), 'publicado_em': p.get('publicado_em')}


def renderizar(st, pd, documentos, admins, usuario):
    try:
        pc_validar_admin(admins, usuario)
    except (PermissionError, ValueError, KeyError, TypeError):
        return
    st.markdown('#### Sem ataques na última guerra')
    try:
        resultado = analisar(documentos)
    except (KeyError, ValueError, TypeError, AttributeError):
        st.warning('Não foi possível conferir a última guerra. Nenhuma vila será marcada com dados incompletos.')
        return
    if resultado is None:
        st.info('Ainda não há uma guerra comum encerrada disponível para conferir os ataques.')
        return
    r = resultado
    st.caption(f"Última guerra comum encerrada disponível · contra {r['adversario']} ({r['adversario_tag']})"
               f" · fim em {r['fim']:%d/%m/%Y às %H:%M} (Brasília).")
    c1, c2 = st.columns(2)
    c1.metric('Vilas com zero ataques', len(r['vilas']))
    c2.metric('Entre as vilas escaladas', f"{len(r['vilas'])} de {r['escaladas']} · {100*len(r['vilas'])/r['escaladas']:.1f}%")
    if r['vilas']:
        st.dataframe(pd.DataFrame(r['vilas']), hide_index=True, use_container_width=True)
        from .relatorio_desempenho import csv_seguro
        st.download_button('Baixar lista de zero ataques', csv_seguro(r['vilas']),
                           file_name=f"sem_ataques_{r['fim']:%Y%m%d}.csv",
                           mime='text/csv', key='ultima_guerra_zero_csv')
    else:
        st.success('Todas as vilas escaladas fizeram pelo menos um ataque.')
    st.caption('Quem realizou um ou dois ataques não aparece. Esta lista independe da inscrição na competição '
               'e dos filtros abaixo. Nenhuma remoção ou bloqueio é feito automaticamente.')
    st.caption('Histórico atualizado: ' + horario(r['publicado_em']) + ' · Lista de membros: '
               + horario(r['membros_em']) + ' · Brasília.')
    try:
        recente = datetime.now(timezone.utc) - datetime.fromisoformat(r['publicado_em'])
        if recente.total_seconds() > 1200:
            st.warning('Histórico desatualizado: confirme a atualização antes de tomar providências.')
    except (TypeError, ValueError):
        st.warning('Horário de atualização indisponível; confira a integração.')

