"""Gráficos administrativos a partir dos registros já conferidos."""
import html


def dados(contas, tipo):
    linhas = []
    for c in contas:
        regs = [r for r in c['registros'] if r['tipo'] == tipo]
        if not regs: continue
        usados = disponiveis = 0
        ataques = []
        saque = quantidade = 0
        limites_ausentes = 0
        for r in regs:
            j = r['jogador']
            n = j.get('quantidade_ataques') if tipo == 'raide' else len(j['ataques'])
            limite = j.get('limite_ataques')
            if type(n) is int and type(limite) is int and 0 <= n <= limite and limite > 0:
                usados += n; disponiveis += limite
            else: limites_ausentes += 1
            ataques.extend(j['ataques'])
            if tipo == 'raide' and type(n) is int and n > 0 and type(j.get('saque')) is int:
                saque += j['saque']; quantidade += n
        estrelas = [a['Estrelas'] for a in ataques if type(a.get('Estrelas')) is int and 0 <= a['Estrelas'] <= 3]
        linhas.append({'Vila': c['nome']+' · '+c['tag'], 'Nome': c['nome'], 'Tag': c['tag'],
            'Atividades': len(regs), 'Ataques': len(estrelas), 'Triplos': estrelas.count(3),
            'Triplos (%)': 100*estrelas.count(3)/len(estrelas) if estrelas else None,
            'Usados': usados, 'Disponíveis': disponiveis, 'Não usados': disponiveis-usados,
            'Uso (%)': 100*usados/disponiveis if disponiveis and not limites_ausentes else None,
            'Saque/ataque': saque/quantidade if quantidade else None,
            'Ataques de raide': quantidade, 'Limites ausentes': limites_ausentes})
    return linhas


def barras(st, pd, rows, eixo, titulo, maximo=None, altura=None):
    validas = [r for r in rows if r.get(eixo) is not None]
    if not validas:
        st.info('Sem amostra suficiente para este gráfico.'); return
    x = {'field': eixo, 'type': 'quantitative', 'title': titulo}
    if maximo: x['scale'] = {'domain': [0, maximo]}
    st.vega_lite_chart(pd.DataFrame(validas), {'height': altura or max(130, 30*len(validas)),
        'mark': {'type': 'bar', 'cornerRadiusEnd': 4, 'color': '#3299ce'},
        'encoding': {'y': {'field': 'Vila', 'type': 'nominal', 'sort': '-x', 'title': None,
                           'axis': {'labelLimit': 260}}, 'x': x,
                     'tooltip': [{'field': k, 'type': 'quantitative' if type(v) in (float,int) else 'nominal'}
                                 for k,v in validas[0].items()]}}, use_container_width=True)


def coletivo(st, pd, contas, tipos, minimo):
    from .relatorio_desempenho import TIPOS
    st.markdown('#### Visão visual da seleção')
    disponiveis = [t for t in tipos if any(r['tipo'] == t for c in contas for r in c['registros'])]
    if not disponiveis:
        st.info('Sem atividades nas modalidades selecionadas.'); return
    tipo = st.radio('Modalidade do gráfico', disponiveis, format_func=TIPOS.get, horizontal=True, key='rd_graf_tipo')
    metrica = st.radio('O que comparar', ['Uso dos ataques', 'Saque por ataque' if tipo == 'raide' else 'Ataques de três estrelas'],
                      horizontal=True, key='rd_graf_metrica_'+tipo)
    rows = dados(contas, tipo)
    if metrica == 'Uso dos ataques':
        completas = [r for r in rows if r['Uso (%)'] is not None]
        if completas:
            values = [{**r, 'Situação': situacao, 'Quantidade': r[chave],
                       'Percentual': 100*r[chave]/r['Disponíveis']} for r in completas
                      for situacao,chave in [('Utilizados','Usados'),('Não utilizados','Não usados')]]
            st.vega_lite_chart(pd.DataFrame(values), {'height': max(140, 29*len(completas)),
                'mark': 'bar', 'encoding': {
                    'y': {'field': 'Vila', 'type': 'nominal', 'title': None, 'sort': [r['Vila'] for r in sorted(completas,key=lambda r:r['Uso (%)'])], 'axis': {'labelLimit': 260}},
                    'x': {'field': 'Percentual', 'type': 'quantitative', 'stack': 'zero', 'title': 'Ataques disponíveis (%)', 'scale': {'domain':[0,100]}},
                    'color': {'field': 'Situação', 'scale': {'domain':['Utilizados','Não utilizados'],'range':['#218b86','#e1a13b']}, 'legend': {'orient':'top'}},
                    'tooltip': [{'field':k} for k in ['Vila','Situação','Quantidade','Disponíveis','Atividades']]}},use_container_width=True)
        else: st.info('Limites de ataques ainda não disponíveis para esta seleção.')
        st.caption('Verde: ataques utilizados. Amarelo: disponíveis e não utilizados. Apenas atividades em que a conta aparece; não mede presença em atividades fora do registro.')
        ausentes = sum(r['Limites ausentes'] > 0 for r in rows)
        if ausentes: st.caption(f'{ausentes} conta(s) sem limites completos ficaram fora deste gráfico.')
    elif tipo == 'raide':
        barras(st,pd,rows,'Saque/ataque','Saque médio por ataque')
        st.caption('Considere distritos e papel de cada ataque: limpar uma base pode render menos saque. Este gráfico não classifica colaboração sozinho.')
    else:
        validas = [r for r in rows if r['Ataques'] >= minimo]
        barras(st,pd,validas,'Triplos (%)','Ataques de três estrelas (%)',100)
        st.caption(f'Mínimo de {minimo} ataques por conta. {len(rows)-len(validas)} conta(s) abaixo desse mínimo não entram na comparação. Passe sobre as barras para ver triplos e tamanho da amostra; confira os CVs na ficha individual.')


def individual(st, pd, conta):
    from .relatorio_desempenho import TIPOS, faixas_cv, data_fim
    from .consultas import FUSO
    st.markdown('#### Painel visual do membro')
    for tipo in TIPOS:
        regs = [r for r in conta['registros'] if r['tipo'] == tipo]
        if not regs: continue
        st.markdown('**'+TIPOS[tipo]+'**')
        row = dados([conta],tipo)[0]
        c1,c2 = st.columns(2)
        c1.metric('Uso dos ataques',f"{row['Uso (%)']:.0f}%" if row['Uso (%)'] is not None else 'Sem limite completo')
        if tipo == 'raide':
            c2.metric('Saque por ataque', f"{row['Saque/ataque']:,.0f}" if row['Saque/ataque'] is not None else 'Sem amostra')
            linhas = [{'Vila': r['coluna'] or data_fim(r).astimezone(FUSO).strftime('%d/%m'),
                'Saque/ataque': r['jogador']['saque']/r['jogador']['quantidade_ataques'],
                'Ataques':r['jogador']['quantidade_ataques']} for r in regs if r['jogador'].get('quantidade_ataques',0)>0]
            barras(st,pd,linhas,'Saque/ataque','Saque por ataque em cada raide')
        else:
            c2.metric('Três estrelas',f"{row['Triplos']} de {row['Ataques']} ataques")
            distribuicao = [{'Estrelas':str(n)+' ★','Ataques':sum(a.get('Estrelas')==n for r in regs for a in r['jogador']['ataques'])} for n in range(4)]
            if row['Ataques']:
                st.vega_lite_chart(pd.DataFrame(distribuicao),{'height':180,'mark':{'type':'bar','color':'#3299ce'},'encoding':{
                    'x':{'field':'Estrelas','type':'ordinal','title':'Estrelas obtidas no jogo','axis':{'labelAngle':0}},
                    'y':{'field':'Ataques','type':'quantitative','axis':{'tickMinStep':1}},'tooltip':[{'field':'Estrelas'},{'field':'Ataques'}]}},use_container_width=True)
                faixas = [{'Vila':f['CV do alvo'],**f} for f in faixas_cv(regs)]
                barras(st,pd,faixas,'3 estrelas (%)','Triplos por faixa de CV do alvo (%)',100)
            else: st.info('Escalado, mas sem ataques registrados nestas atividades encerradas.')
        st.caption(f"{len(regs)} atividade(s) registrada(s). Ataques não utilizados não são ataques de zero estrela.")


def ficha_html(conta, inicio, fim):
    """Ficha portátil sem scripts, recursos externos ou nomes interpretados como HTML."""
    from .relatorio_desempenho import TIPOS, faixas_cv
    esc=lambda v:html.escape(str(v),quote=True)
    partes=[f'<h1>{esc(conta["nome"])}</h1><p>{esc(conta["tag"])} · {esc(inicio)} a {esc(fim)}</p>']
    def barra(label,valor,denom,texto):
        largura=100*valor/denom if denom else 0
        return f'<div class="linha"><b>{esc(label)}</b><span>{esc(texto)}</span><div class="trilho"><div style="width:{largura:.2f}%"></div></div></div>'
    for tipo in TIPOS:
        regs=[r for r in conta['registros'] if r['tipo']==tipo]
        if not regs:continue
        d=dados([conta],tipo)[0];partes.append(f'<section><h2>{TIPOS[tipo]}</h2><p>{len(regs)} atividade(s)</p>')
        if d['Uso (%)'] is not None:
            partes.append(barra('Ataques utilizados',d['Usados'],d['Disponíveis'],f"{d['Usados']} de {d['Disponíveis']} · {d['Uso (%)']:.1f}%"))
        else:partes.append('<p>Limite de ataques incompleto; uso não estimado.</p>')
        if tipo=='raide':
            if d['Saque/ataque'] is not None:partes.append(f"<p><b>{d['Saque/ataque']:,.0f}</b> de saque por ataque · {d['Ataques de raide']} ataques</p>")
            partes.append('<p>Saque depende dos distritos e do papel do ataque.</p>')
        elif d['Ataques']:
            partes.append(barra('Ataques de três estrelas',d['Triplos'],d['Ataques'],f"{d['Triplos']} de {d['Ataques']} · {d['Triplos (%)']:.1f}%"))
            for f in faixas_cv(regs):partes.append(barra('Alvo: CV '+f['CV do alvo'],f['Triplos'],f['Ataques'],f"{f['Triplos']} de {f['Ataques']} triplos"))
        else:partes.append('<p>Sem amostra de ataques para avaliar execução.</p>')
        partes.append('</section>')
    partes.append('<footer>Winning Wars · Atividades encerradas disponíveis no período. Indicadores de jogo, não pontos da competição. Amostras pequenas exigem cautela. Ausência de registro não comprova falta de colaboração. Ficha restrita à conta selecionada; revisão humana necessária.</footer>')
    return ('<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Desempenho Winning Wars</title><style>body{font:16px system-ui;color:#183347;max-width:820px;margin:32px auto;padding:20px}section{border:1px solid #dde5eb;border-radius:14px;padding:20px;margin:20px 0;break-inside:avoid}h1{margin-bottom:4px}h2{color:#187e80}.linha{margin:18px 0}.linha span{float:right}.trilho{height:16px;background:#f2ddb7;border-radius:8px;overflow:hidden;margin-top:8px}.trilho div{height:100%;background:#218b86}footer{font-size:13px;color:#526674}@media(max-width:500px){.linha span{float:none;display:block}}@media print{body{margin:0}.trilho{print-color-adjust:exact}}</style><body>'+''.join(partes)+'</body></html>').encode('utf-8')
