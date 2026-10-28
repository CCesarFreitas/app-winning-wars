"""Feedback individual mensal, apenas leitura e atividades encerradas."""
import io
from datetime import datetime
from .desempenho_mensal import NOMES, linhas, imagem, grafico_interativo


def jogos_do_mes(registros, tag, mes):
    candidatos = [r for r in registros if r.get('PlayerTag') == tag
                  and r.get('Temporada') == mes and r.get('Atividade') == 'JogosCla']
    if not candidatos:
        return None
    # O painel manual substitui o total: nunca somar revisões do mesmo lançamento.
    from .manual import HEADER, hash_json, pontos_jogos
    for r in candidatos:
        if hash_json([str(r.get(k, '')) for k in HEADER[:-1]]) != r.get('Hash'):
            raise ValueError('Assinatura do lançamento divergente')
        data = datetime.fromisoformat(r['RegistradoEm'])
        if data.utcoffset() is None:
            raise ValueError('Data sem fuso')
        if pontos_jogos(int(r['ValorInformado'])) != int(r['Depois']):
            raise ValueError('Pontuação divergente')
    candidatos.sort(key=lambda r: datetime.fromisoformat(r['RegistradoEm']))
    if len(candidatos)>1 and candidatos[-1]['RegistradoEm']==candidatos[-2]['RegistradoEm']:
        raise ValueError('Lançamentos simultâneos; conferir auditoria')
    r = candidatos[-1]
    return {'jogo': int(r['ValorInformado']), 'competicao': int(r['Depois']), 'data': r['RegistradoEm']}


def exportar(conta, mes, stamp):
    """Une os mesmos gráficos das três modalidades em uma imagem de feedback."""
    from PIL import Image
    partes=[]
    for tipo in NOMES:
        rows=linhas([conta],tipo)
        partes.append(Image.open(io.BytesIO(imagem(rows,tipo,mes,stamp,escopo='Feedback individual · '+conta['tag']))).convert('RGB'))
    final=Image.new('RGB',(3000,sum(p.height for p in partes)), '#f6f8fb')
    y=0
    for p in partes:
        final.paste(p,(0,y));y+=p.height
    saida=io.BytesIO();final.save(saida,format='PNG',dpi=(250,250))
    return saida.getvalue()


FEEDBACK_VERSAO = 3

def renderizar(st,pd,conta,mes,stamp,carregar_manuais=None,total_raides=None,chave='di',publico=False):
    from .relatorio_desempenho import data_fim, faixas_cv, csv_seguro
    from .consultas import FUSO
    st.subheader(conta['nome'])
    st.caption(conta['tag']+' · Análise completa de '+mes+' · Atualização: '+stamp)
    if not publico:st.caption('A seleção de uma única vila reúne todas as modalidades, independentemente do filtro Atividade.')
    for tipo,titulo in NOMES.items():
        st.markdown('#### '+titulo)
        regs=[r for r in conta['registros'] if r['tipo']==tipo]
        rows=linhas([conta],tipo)
        if not rows:
            st.info('Sem participação registrada nesta modalidade no mês. Isso não comprova inatividade.')
            continue
        r=rows[0]
        c1,c2,c3,c4=st.columns(4)
        c1.metric('Raides com registro' if tipo=='raide' else ('Rodadas com registro' if tipo=='liga' else 'Guerras com registro'),r['atividades'])
        c2.metric('Ataques feitos',r['ataques'])
        c3.metric('Ataques não usados',r['faltas'] if r['faltas'] is not None else 'Não informado')
        c4.metric('Uso dos ataques' if tipo=='raide' else 'Taxa de 3 estrelas',
                  f"{r['uso'] if tipo=='raide' else r['taxa3']:.1f}%" if (r['uso'] if tipo=='raide' else r['taxa3']) is not None else 'Sem amostra')
        grafico_interativo(st,pd,rows,tipo)
        if tipo!='raide':
            st.caption(' · '.join(f"{n} estrelas: {r['estrelas'][n]}" for n in (3,2,1,0)))
            if r['ataques']<3:st.caption('Amostra pequena: menos de três ataques.')
        else:
            st.caption('Saque médio por ataque: '+(f"{r['saque_medio']:,.0f}" if r['saque_medio'] is not None else 'não informado')+'. Estrelas individuais de raides não estão disponíveis neste histórico.')
        with st.expander('Ver atividades e ataques — '+titulo):
            tabela=[{'Atividade':x['coluna'] or x['id'],
                'Fim':data_fim(x).astimezone(FUSO).strftime('%d/%m %H:%M'),
                'Ataques':x['jogador'].get('quantidade_ataques',len(x['jogador']['ataques'])),
                'Pontos registrados':x['jogador'].get('pontos'),
                **({'Saque':x['jogador'].get('saque'),'Bônus':x['jogador'].get('bonus')} if tipo=='raide' else {})} for x in regs]
            st.dataframe(pd.DataFrame(tabela),hide_index=True,use_container_width=True)
            faixas=faixas_cv(regs)
            if faixas:st.dataframe(pd.DataFrame(faixas),hide_index=True,use_container_width=True)
            ataques=[{'Atividade':x['coluna'] or x['id'],**a} for x in regs for a in x['jogador']['ataques']]
            if ataques:st.dataframe(pd.DataFrame(ataques),hide_index=True,use_container_width=True)
            st.download_button('Baixar detalhes CSV',csv_seguro(tabela),file_name=f'{mes}_{tipo}_individual.csv',key=chave+'_csv_'+tipo)
    st.markdown('#### Jogos do Clã')
    jogos=None
    jogos_estado='pendente'
    try:
        jogos=jogos_do_mes(carregar_manuais(),conta['tag'],mes) if carregar_manuais else None
        if jogos is None:st.info('Sem lançamento confirmado neste mês. O resultado aparecerá após o registro no painel de Jogos do Clã.')
        else:
            c1,c2=st.columns(2)
            c1.metric('Pontos feitos nos Jogos',jogos['jogo']);c2.metric('Pontos na competição',jogos['competicao'])
            st.caption('Último lançamento auditado: '+jogos['data'])
    except Exception:
        jogos_estado='erro'
        st.warning('Não foi possível conferir o lançamento dos Jogos do Clã. Isso não significa zero pontos.')
    from .feedback_imagem import exportar as ficha
    gerar=st.cache_data(show_spinner=False,max_entries=16)(ficha)
    st.download_button('Baixar feedback completo — guerras, liga, raides e jogos (PNG)',gerar(conta,mes,stamp,jogos,jogos_estado,total_raides),
        file_name=f"WinningWars_{mes}_{conta['tag'].lstrip('#')}_individual.png",mime='image/png',key=chave+'_png')
    st.caption('Imagem com 3.000 pixels de largura. Participações e faltas consideram apenas atividades com registro individual; ausência no histórico não é falta de ataque. Compare também os níveis dos CVs antes do feedback.')
