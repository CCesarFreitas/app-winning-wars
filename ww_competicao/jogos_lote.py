"""Lançamento atômico de Jogos do Clã, reutilizando as regras individuais."""
from copy import deepcopy
from datetime import datetime, timezone
import uuid
import json
from .manual import preparar, conferir, fotografar, pontos_jogos
from .participacao_competicao import pc_validar_admin, pc_estado, pc_ler_eventos


def preparar_lote(foto, metas, usuario, entradas, agora=None):
    pc_validar_admin(foto['admins']['valores'],usuario)
    if not entradas:raise ValueError('Preencha pelo menos uma vila.')
    tags=[e['tag'] for e in entradas]
    if len(set(tags))!=len(tags):raise ValueError('Vila repetida no lote.')
    virtual=deepcopy(foto);capacidades=deepcopy(metas)
    propostas=[];ignorados=[];pedidos=[]
    agora=agora or datetime.now(timezone.utc).isoformat()
    for e in entradas:
        pontos_jogos(e['valor'])
        p=preparar(virtual,capacidades,usuario,e['tag'],e['nome'],'JogosCla',e['valor'],str(uuid.uuid4()),agora)
        if p['status']=='ZERO_SEM_INSCRICAO':
            ignorados.append(e);continue
        propostas.append(p);pedidos.extend(p['lote']['requests'])
        novas=json.loads(p['registro'][10])['novas_linhas']
        for n,linhas in novas.items():
            for modo in ('valores','formulas'):
                virtual[n][modo].extend([[str(v) for v in r] for r in linhas])
        for modo in ('valores','formulas'):
            ranking=virtual['ranking'][modo];col=ranking[0].index('JogosCla')
            linha=next(r for r in ranking[1:] if str(r[0])==p['id'])
            linha.extend(['']*max(0,col+1-len(linha)));linha[col]=str(p['pontos'])
            virtual['manual'][modo].append(p['registro'][:])
        for request in p['lote']['requests']:
            if 'addSheet' in request:capacidades['manual']['nova']=False
            if 'appendDimension' in request:
                a=request['appendDimension']
                for m in capacidades.values():
                    if m['id']==a['sheetId']:m['linhas']+=a['length']
    return {'propostas':propostas,'ignorados':ignorados,'lote':{'requests':pedidos}}


def conferir_lote(foto,lote):
    for p in lote['propostas']:conferir(foto,p)


def renderizar(st,planilha,ranking,usuario,backup,limpar):
    import pandas as pd
    st.markdown('### Jogos do Clã — lançamento em lote')
    st.caption('Preencha os pontos feitos no jogo. Campo vazio mantém o valor atual; zero é um lançamento explícito. O lote substitui os totais, sem somar novamente.')
    s=st.session_state.setdefault('ww_jogos_lote_v1',{})
    try:
        if s.get('pendente'):
            st.warning('Envio aguardando conferência. Não repita o lançamento.')
            if st.button('Conferir lote enviado',key='jl_reconferir'):
                f,_=fotografar(planilha,ranking.title);pc_validar_admin(f['admins']['valores'],usuario)
                conferir_lote(f,s['pendente']);s.clear();limpar();st.success('Lote conferido, sem novo envio.')
            return
        if st.button('Carregar / atualizar tabela',key='jl_carregar'):
            f,m=fotografar(planilha,ranking.title);pc_validar_admin(f['admins']['valores'],usuario)
            s.clear();s.update(foto=f,metas=m,editor=str(uuid.uuid4()))
        if 'foto' not in s:
            st.info('Carregue a tabela para preencher várias vilas de uma vez.');return
        f,m=s['foto'],s['metas'];pc_validar_admin(f['admins']['valores'],usuario)
        contas=pc_estado(pc_ler_eventos(f['participacao']['valores']))
        habilitadas={t:c for t,c in contas.items() if c['Habilitada']=='TRUE'}
        st.caption(f'{len(habilitadas)} contas habilitadas. Contas bloqueadas não aparecem para lançamento.')
        tabela=pd.DataFrame([{'Vila':c['Nome'],'Tag':t,'Pontos no jogo':float('nan')} for t,c in sorted(habilitadas.items(),key=lambda x:x[1]['Nome'].casefold())],columns=['Vila','Tag','Pontos no jogo'])
        tabela['Pontos no jogo']=tabela['Pontos no jogo'].astype(float)
        with st.form('jl_form'):
            editado=st.data_editor(tabela,hide_index=True,use_container_width=True,disabled=['Vila','Tag'],
                column_config={'Pontos no jogo':st.column_config.NumberColumn(min_value=0,max_value=10000,step=1,format='%d')},key='jl_editor_'+s['editor'])
            st.caption('Conversão: menos de 2.000 → 0 · 2.000–3.999 → 2 · 4.000–9.999 → 5 · 10.000 → 10 pontos na competição.')
            revisar=st.form_submit_button('Conferir lote')
        if revisar:
            s.pop('proposta',None)
            entradas=[]
            for r in editado.to_dict('records'):
                v=r['Pontos no jogo']
                if pd.isna(v):continue
                if isinstance(v,bool) or float(v)!=int(v):raise ValueError('Use somente pontos inteiros.')
                t=r['Tag']
                if t not in habilitadas:raise ValueError('Conta fora da lista habilitada.')
                entradas.append({'tag':t,'nome':habilitadas[t]['Nome'],'valor':int(v)})
            s['proposta']=preparar_lote(f,m,usuario,entradas)
        if s.get('proposta'):
            p=s['proposta']
            st.dataframe(pd.DataFrame([{'Vila':x['nome'],'Tag':x['tag'],'Pontos no jogo':x['valor'],'Competição antes':x['antes'],'Competição depois':x['pontos']} for x in p['propostas']]),hide_index=True,use_container_width=True)
            if p['ignorados']:st.info(f"{len(p['ignorados'])} contas sem inscrição e sem primeira pontuação positiva não serão criadas.")
            st.caption('O envio usa exclusivamente o resumo conferido acima. Se editar a tabela, clique novamente em Conferir lote.')
            if p['propostas'] and st.button('Confirmar e salvar lote',key='jl_salvar',type='primary'):
                for etapa in range(2):
                    atual,metas=fotografar(planilha,ranking.title);pc_validar_admin(atual['admins']['valores'],usuario)
                    if atual!=f or metas!=m:
                        s.clear();raise ValueError('Os dados mudaram. Carregue a tabela e confira novamente.')
                    if etapa==0:backup()
                s['pendente']=p
                planilha.batch_update(p['lote'])
                depois,_=fotografar(planilha,ranking.title);conferir_lote(depois,p)
                s.clear();limpar();st.success('Lote salvo e conferido: pontos, inscrições e auditoria. Atualize a página para ver o ranking.')
    except Exception as erro:st.error(str(erro))
