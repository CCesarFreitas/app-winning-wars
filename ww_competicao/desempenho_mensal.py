"""Painel mensal e imagens de apresentação, sem alteração de dados."""
import calendar
import io
import math
import zipfile
from datetime import date, datetime, timezone
from threading import Lock

CORES = {3: '#168775', 2: '#438ac4', 1: '#e8ad42', 0: '#c97170'}
NOMES = {'guerra': 'Guerras normais', 'liga': 'Liga', 'raide': 'Raides'}
MESES = ('janeiro','fevereiro','março','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro')
PLOT_LOCK = Lock()


def periodo(mes):
    ano, numero = map(int, mes.split('-'))
    return date(ano, numero, 1), date(ano, numero, calendar.monthrange(ano, numero)[1])


def linhas(contas, tipo):
    saida = []
    for c in contas:
        regs = [r for r in c['registros'] if r['tipo'] == tipo]
        if not regs: continue
        contagem = {n: 0 for n in range(4)}
        total = faltas = limites = saque = saque_ataques = 0
        completos = limites_ok = True
        for r in regs:
            j = r['jogador']
            n = j.get('quantidade_ataques') if tipo == 'raide' else len(j['ataques'])
            if type(n) is not int or n < 0:
                completos = limites_ok = False
                continue
            total += n
            limite = j.get('limite_ataques')
            if type(limite) is int and limite > 0 and n <= limite:
                faltas += limite-n; limites += limite
            else: limites_ok = False
            if tipo == 'raide':
                if type(j.get('saque')) is int and j['saque'] >= 0 and n > 0:
                    saque += j['saque']; saque_ataques += n
                elif n > 0: completos = False
            else:
                for a in j['ataques']:
                    e = a.get('Estrelas')
                    if type(e) is int and 0 <= e <= 3: contagem[e] += 1
                    else: completos = False
        saida.append({'nome': c['nome'], 'tag': c['tag'], 'atividades': len(regs),
            'ataques': total, 'estrelas': contagem,
            'taxa3': 100*contagem[3]/total if total and completos and tipo != 'raide' else None,
            'faltas': faltas if limites_ok else None,
            'uso': 100*total/limites if limites_ok and limites else None,
            'saque_medio': saque/saque_ataques if saque_ataques and completos else None,
            'completos': completos})
    return sorted(saida, key=lambda r: (-(r['saque_medio'] or 0) if tipo == 'raide' else -(r['taxa3'] if r['taxa3'] is not None else -1),
                                       -r['ataques'], r['nome'].casefold(), r['tag']))


def imagem(rows, tipo, mes, atualizado, pagina=1, paginas=1, escopo='Participantes no período'):
    # Figure isolada; lock evita concorrência nos caches de fontes do Matplotlib.
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.patches import Patch
    from matplotlib.font_manager import findfont
    from matplotlib.ft2font import FT2Font
    with PLOT_LOCK:
        h = 3.3 + max(3, len(rows)) * .50
        fig = Figure(figsize=(12, h), dpi=250, facecolor='#f6f8fb')
        FigureCanvasAgg(fig)
        fig.text(.04, 1-.43/h, 'WINNING WARS  /  DESEMPENHO MENSAL', fontsize=11, color='#53677a', weight='bold')
        mes_legivel=MESES[int(mes[5:])-1]+'/'+mes[:4]
        fig.text(.04, 1-.86/h, f'{NOMES[tipo]} · {mes_legivel}', fontsize=21, weight='bold', color='#153249')
        fig.text(.04, 1-1.17/h, f'{escopo}  |  Atividades encerradas no mês (Brasília)  |  Página {pagina}/{paginas}', fontsize=9, color='#53677a')
        bottom=1.12/h; top=1-1.98/h
        ax = fig.add_axes([.30,bottom,.36,top-bottom],facecolor='#f6f8fb')
        ax.set_ylim(len(rows)-.45,-.85)
        ax.set_xlim(0,100)
        ax.set_yticks([])
        ax.set_xticks([0,25,50,75,100],labels=['0%','25%','50%','75%','100%'])
        ax.tick_params(axis='x',labelsize=8,colors='#64778a',length=0)
        ax.grid(axis='x',color='#dce4eb',linewidth=.6,zorder=0)
        for spine in ax.spines.values():spine.set_visible(False)
        raid = tipo == 'raide'
        legend = ([Patch(color='#168775',label='Ataques usados'),Patch(color='#dce4eb',label='Não usados')]
                  if raid else [Patch(color=CORES[n],label=f'{n} estrela'+('s' if n!=1 else '')) for n in (3,2,1,0)])
        fig.legend(handles=legend,loc='upper left',bbox_to_anchor=(.30,1-1.39/h),ncol=len(legend),frameon=False,fontsize=9)
        ax.text(-.72,1.02,'VILA / TAG',transform=ax.transAxes,fontsize=8,weight='bold',color='#53677a')
        headers = [('Saque/ataque' if raid else 'Taxa 3★',1.20),('Atq. / ativ.',1.55),('Não usados',1.85)]
        for label,x in headers:ax.text(x,1.02,label,transform=ax.transAxes,ha='center',fontsize=8,weight='bold',color='#53677a')
        caracteres=FT2Font(findfont('DejaVu Sans')).get_charmap()
        for i,r in enumerate(rows):
            nome=r['nome'].replace('\n',' ').replace('\r',' ')
            nome=''.join(c for c in nome if ord(c) in caracteres).strip() or 'Vila'
            nome=nome if len(nome)<=28 else nome[:27]+'…'
            ax.text(-.72,i-.12,nome,transform=ax.get_yaxis_transform(),fontsize=10,weight='bold',color='#153249',clip_on=False,parse_math=False)
            ax.text(-.72,i+.23,r['tag'],transform=ax.get_yaxis_transform(),fontsize=7.8,color='#64778a',clip_on=False)
            if raid and r['uso'] is not None:
                ax.barh(i,100,height=.53,color='#dce4eb',zorder=2)
                ax.barh(i,r['uso'],height=.53,color='#168775',zorder=3)
                ax.text(50,i,f"{r['uso']:.0f}% utilizados",ha='center',va='center',fontsize=9,color='#153249',weight='bold',zorder=4)
            elif not raid and r['ataques'] and r['completos']:
                left=0
                for n in (3,2,1,0):
                    v=100*r['estrelas'][n]/r['ataques']
                    ax.barh(i,v,left=left,height=.53,color=CORES[n],zorder=3)
                    label=f"{r['estrelas'][n]} ({v:.0f}%)" if v>=25 else str(r['estrelas'][n])
                    if v>=7:ax.text(left+v/2,i,label,ha='center',va='center',fontsize=9,color='white' if n in (3,2,0) else '#153249',weight='bold')
                    left+=v
            else:
                ax.text(50,i,'Sem ataques' if not r['ataques'] else 'Dados incompletos',ha='center',va='center',fontsize=9,color='#64778a')
            valor=r['saque_medio'] if raid else r['taxa3']
            texto=('—' if valor is None else f'{valor:,.0f}'.replace(',','.') if raid else f'{valor:.1f}%'.replace('.',','))
            amostra=' *' if 0<r['ataques']<3 else ''
            for x,t in [(1.20,texto),(1.55,f"{r['ataques']} / {r['atividades']}"+amostra),(1.85,str(r['faltas']) if r['faltas'] is not None else '—')]:
                ax.text(x,i,t,transform=ax.get_yaxis_transform(),ha='center',va='center',fontsize=10,color='#153249',weight='bold' if x==1.20 else 'normal')
        nota = ('Raides: saque depende dos distritos e do papel de cada ataque; não é taxa de estrelas.' if raid else
                'Taxa 3★ = ataques de 3 estrelas ÷ ataques realizados. Barras: quantidade e proporção dos resultados.')
        fig.text(.04,.66/h,nota,fontsize=8.5,color='#53677a')
        fig.text(.04,.42/h,'* Menos de 3 ataques: amostra pequena. Não usados ≠ 0 estrelas. Compare CVs. Símbolos sem suporte são omitidos; confira a tag.',fontsize=8,color='#53677a')
        fig.text(.04,.18/h,f'Fonte: histórico do Winning Wars · atualizado em {atualizado} · leitura, sem alterações de pontos.',fontsize=7.5,color='#64778a')
        buffer=io.BytesIO();fig.savefig(buffer,format='png',dpi=250,facecolor=fig.get_facecolor())
        fig.clear()
        return buffer.getvalue()


def renderizar(st,pd,documentos,admins,usuario):
    from .participacao_competicao import pc_validar_admin
    from .relatorio_desempenho import selecionar, construir, data_fim, csv_seguro, faixas_cv
    from .consultas import FUSO, horario
    try:pc_validar_admin(admins,usuario)
    except (PermissionError,ValueError,KeyError,TypeError):
        st.info('Relatório disponível apenas para administradores autorizados.');return
    st.markdown('### Desempenho mensal dos membros')
    st.caption('Selecione o mês e a modalidade. Os gráficos podem ser baixados em PNG de alta resolução.')
    atividades, invalidos=selecionar(documentos)
    if not atividades:st.info('Ainda não há atividades encerradas disponíveis.');return
    meses=sorted({data_fim(a).astimezone(FUSO).strftime('%Y-%m') for a in atividades},reverse=True)
    c1,c2=st.columns([1,3])
    mes=c1.selectbox('Mês',meses,format_func=lambda m:MESES[int(m[5:])-1]+'/'+m[:4],key='dm_mes')
    tipo=c2.radio('Atividade',list(NOMES),format_func=NOMES.get,horizontal=True,key='dm_tipo')
    inicio,fim=periodo(mes)
    modelo=construir(documentos,inicio,fim,[tipo])
    contas=[c for c in modelo['contas'].values() if c['registros']]
    with st.expander('Filtrar membros'):
        atuais=st.checkbox('Somente membros da última consulta do clã',key='dm_atuais')
        if atuais:contas=[c for c in contas if c['atual']]
        por_tag={c['tag']:c for c in contas}
        escolhidos=st.multiselect('Selecionar vilas (vazio = todas)',list(por_tag),format_func=lambda t:por_tag[t]['nome']+' · '+t,key='dm_vilas')
        if escolhidos:contas=[por_tag[t] for t in escolhidos]
        st.caption('Lista do clã consultada em '+horario(documentos.get('membros',{}).get('consultado_em'))+'.')
    saude=documentos.get('saude',{})
    stamp=horario(saude.get('verificado_em'))+' (Brasília)'
    try:atraso=(datetime.now(timezone.utc)-datetime.fromisoformat(saude['verificado_em'])).total_seconds()>1200
    except (KeyError,TypeError,ValueError):atraso=True
    if atraso or invalidos or saude.get('falhas_historico') or saude.get('atividades_sem_detalhe'):
        st.warning('O histórico está desatualizado ou incompleto. Confira a integração antes de tomar decisões.')
    rows=linhas(contas,tipo)
    if not rows:st.info('Nenhuma participação nesta seleção. Ausência de registro não comprova inatividade.');return
    total=sum(r['ataques'] for r in rows)
    c1,c2,c3=st.columns(3)
    c1.metric('Vilas',len(rows));c2.metric('Ataques realizados',total)
    if tipo!='raide':
        taxa=100*sum(r['estrelas'][3] for r in rows)/total if total and all(r['completos'] for r in rows) else None
        c3.metric('Ataques com 3 estrelas',f'{taxa:.1f}%' if taxa is not None else 'Sem amostra')
    else:c3.metric('Raides encerrados',len(modelo['atividades']))
    escopo='Somente membros da última consulta' if atuais else 'Todas as vilas com participação no mês'
    if escolhidos:escopo+=' · seleção de vilas'
    paginas=math.ceil(len(rows)/10)
    pagina=st.selectbox('Página do gráfico',list(range(1,paginas+1)),key='dm_pagina') if paginas>1 else 1
    # Cache limitado a bytes de imagem; autorização é executada antes do acesso.
    gerar=st.cache_data(show_spinner=False,max_entries=24)(imagem)
    png=gerar(rows[(pagina-1)*10:pagina*10],tipo,mes,stamp,pagina,paginas,escopo)
    st.image(png,use_container_width=True)
    st.download_button('Baixar gráfico PNG — alta resolução',png,file_name=f'WinningWars_{mes}_{tipo}_{pagina}.png',mime='image/png',key='dm_png')
    if paginas>1 and st.button('Preparar imagens de todas as páginas',key='dm_preparar'):
        arquivo=io.BytesIO()
        with zipfile.ZipFile(arquivo,'w',zipfile.ZIP_DEFLATED) as z:
            for p in range(1,paginas+1):
                z.writestr(f'WinningWars_{mes}_{tipo}_{p}.png',gerar(rows[(p-1)*10:p*10],tipo,mes,stamp,p,paginas,escopo))
        st.download_button('Baixar todas as imagens (ZIP)',arquivo.getvalue(),file_name=f'WinningWars_{mes}_{tipo}.zip',mime='application/zip',key='dm_zip')
    st.caption('PNG com 3.000 pixels de largura. A mesma seleção é usada na tela e no arquivo. '+
               ('Nos raides, os dados atuais não trazem estrelas individuais.' if tipo=='raide' else 'Menos de três ataques: amostra pequena. A taxa não considera a dificuldade dos CVs; confira o detalhe individual.'))
    with st.expander('Conferir números e detalhes por membro'):
        tabela=[{'Vila':r['nome'],'Tag':r['tag'],'Atividades':r['atividades'],'Ataques':r['ataques'],
                 **({f'{n} estrelas':r['estrelas'][n] for n in (3,2,1,0)} if tipo!='raide' else {'Saque/ataque':r['saque_medio']}),
                 **({f'{n} estrelas (%)':100*r['estrelas'][n]/r['ataques'] if r['ataques'] and r['completos'] else None for n in (2,1,0)} if tipo!='raide' else {}),
                 **({'Taxa de 3 estrelas (%)':r['taxa3']} if tipo!='raide' else {}),
                 'Ataques não usados':r['faltas']} for r in rows]
        st.dataframe(pd.DataFrame(tabela).round(1),hide_index=True,use_container_width=True)
        st.download_button('Baixar números CSV',csv_seguro(tabela),file_name=f'desempenho_{mes}_{tipo}.csv',mime='text/csv',key='dm_csv')
        por_tag={c['tag']:c for c in contas}
        tag=st.selectbox('Vila para detalhar',list(por_tag),format_func=lambda t:por_tag[t]['nome']+' · '+t,key='dm_membro')
        regs=por_tag[tag]['registros']
        faixas=faixas_cv(regs)
        if faixas:st.dataframe(pd.DataFrame(faixas),hide_index=True,use_container_width=True)
        det=[{'Atividade':r['coluna'] or r['id'],'Fim (Brasília)':data_fim(r).astimezone(FUSO).strftime('%d/%m %H:%M'),
              'Ataques':r['jogador'].get('quantidade_ataques',len(r['jogador']['ataques'])),
              **({'Saque':r['jogador'].get('saque'),'Bônus':r['jogador'].get('bonus')} if tipo=='raide' else {}),
              'Pontos registrados':r['jogador'].get('pontos')} for r in regs]
        st.dataframe(pd.DataFrame(det),hide_index=True,use_container_width=True)
        ataques=[{'Atividade':r['coluna'] or r['id'],**a} for r in regs for a in r['jogador']['ataques']]
        if ataques:st.dataframe(pd.DataFrame(ataques),hide_index=True,use_container_width=True)
    with st.expander('Quem não atacou na última guerra comum?'):
        from .ultima_guerra_sem_ataques import renderizar as ultima
        ultima(st,pd,documentos,admins,usuario)
