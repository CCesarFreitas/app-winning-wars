"""Visao publica restrita a lancamentos oficiais encerrados e integro s."""
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

PLANILHA = '1QTfVjrfSCVZ3JlqIDbhLHHBc2-anz8XhK9WzxU3v0oA'
TIPOS = {'guerra': 'Guerra', 'liga': 'Liga', 'raide': 'Raide'}

def atividades_publicas(registros, agora=None):
    agora = agora or datetime.now(timezone.utc)
    ids = Counter(str(r.get('AtividadeID','')) for r in registros)
    saida = []
    for r in registros:
        try:
            tipo = r['Tipo']
            if tipo not in TIPOS or r['Status'] != 'APLICADO' or r['ClanTag'] != '#YVLGUJQY':
                continue
            identidade = r['AtividadeID']
            if not identidade or ids[identidade] != 1:
                continue
            inicio = datetime.strptime(r['Inicio'], '%Y%m%dT%H%M%S.%fZ').replace(tzinfo=timezone.utc)
            fim = datetime.strptime(r['Fim'], '%Y%m%dT%H%M%S.%fZ').replace(tzinfo=timezone.utc)
            aplicado = datetime.fromisoformat(r['AplicadoEm'])
            if aplicado.utcoffset() is None or not inicio < fim <= aplicado <= agora:
                continue
            temporada = inicio.astimezone(ZoneInfo('America/Sao_Paulo')).strftime('%Y-%m')
            if temporada < '2026-10' or temporada != r['Temporada']:
                continue
            d = json.loads(r['DetalhesJSON'])
            resumo = hashlib.sha256(json.dumps(d,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            if d.get('ficticia') is not False or d.get('planilha') != PLANILHA or resumo != r['HashResultado']:
                continue
            pontos, tags = d['pontos_por_participante'], d['tags']
            if not pontos or set(pontos) != set(tags) or len(set(tags.values())) != len(tags):
                continue
            nomes = {}
            for linha in d.get('inscricao_automatica',{}).get('linhas_acrescentadas',{}).get('inscricoes',[]):
                if len(linha) >= 4: nomes[str(linha[1])] = str(linha[2])
            jogadores = []
            for pid, valor in pontos.items():
                if type(valor) is not int or not 0 <= valor <= (7 if tipo=='raide' else 3):
                    raise ValueError('Pontos invalidos')
                if not re.fullmatch(r'#[0289PYLQGRJCUV]+',tags[pid]):
                    raise ValueError('Tag invalida')
                jogador = {'Nome registrado':nomes.get(pid,tags[pid]),'Tag':tags[pid],
                    'Pontos lançados':valor,'Participação':'Elegível neste lançamento'}
                if tipo=='raide':
                    raid=d['raide_por_participante'][pid]
                    a,s,b=(raid[k] for k in ('ataques','saque','bonus_top3'))
                    if (any(type(v) is not int for v in (a,s,b)) or not 0<=a<=6 or s<0
                            or b not in (0,1) or valor!=a+b or (a==0 and (s or b))):
                        raise ValueError('Raide inconsistente')
                    jogador.update({'Ataques':a,'Saque':s,'Bônus Top 3':b})
                jogadores.append(jogador)
            # Lista explicita: nao repassar JSON de administracao, cadastro ou eventos.
            saida.append({'id':identidade,'temporada':temporada,'tipo':tipo,
                'coluna':str(r['ColunaDestino']),'fim':fim,'inicio':inicio,
                'aplicado':aplicado,'jogadores':jogadores})
        except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
            continue
    return sorted(saida,key=lambda a:a['fim'],reverse=True)

def renderizar(st, registros, pd):
    st.markdown('### 📚 Atividades encerradas')
    st.caption('Consulta pública de guerras, raides e rodadas da Liga encerrados e com pontos oficialmente lançados. Horários de Brasília.')
    atividades=atividades_publicas(registros)
    if not atividades:
        st.info('Ainda não há atividades encerradas com lançamento oficial disponível. Atividades em andamento não aparecem aqui.')
    else:
        temporada=st.selectbox('Temporada da atividade',sorted({a['temporada'] for a in atividades},reverse=True),key='ww_pub_temporada')
        tipo=st.selectbox('Modalidade',['Todas','Guerra','Liga','Raide'],key='ww_pub_tipo')
        filtradas=[a for a in atividades if a['temporada']==temporada and (tipo=='Todas' or TIPOS[a['tipo']]==tipo)]
        if not filtradas:
            st.info('Nenhuma atividade nesta modalidade e temporada.')
        else:
            por_id={a['id']:a for a in filtradas}
            def rotulo(i):
                a=por_id[i]
                return f"{TIPOS[a['tipo']]} · {a['coluna']} · encerrada em {a['fim'].astimezone(ZoneInfo('America/Sao_Paulo')):%d/%m/%Y %H:%M}"
            escolha=st.selectbox('Escolha a atividade',list(por_id),format_func=rotulo,key='ww_pub_atividade')
            a=por_id[escolha]
            st.success('Atividade encerrada · pontuação lançada')
            st.caption(f"Lançamento em {a['aplicado'].astimezone(ZoneInfo('America/Sao_Paulo')):%d/%m/%Y %H:%M}. Identificação: {a['id']}")
            busca=st.text_input('Buscar participante por nome ou tag',key='ww_pub_busca').strip().casefold()
            jogadores=[j for j in a['jogadores'] if not busca or busca in j['Nome registrado'].casefold() or busca in j['Tag'].casefold()]
            st.dataframe(pd.DataFrame(jogadores),hide_index=True,use_container_width=True)
            st.caption('Pontos do lançamento original desta atividade. Correções posteriores devem ser conferidas com a administração. Quando o nome não foi guardado neste registro, mostramos a tag.')
    with st.expander('O que este histórico mostra?'):
        st.markdown('Os registros permanecem consultáveis nas temporadas seguintes. Nos raides, aparecem ataques, saque, bônus e pontos. Em guerras e Liga, aparecem os pontos lançados por conta; o detalhamento de cada ataque ainda não consta neste histórico público. Contas excluídas e atividades aguardando revisão não estão incluídas nos registros de lançamento. Ausência na lista não significa zero pontos. A auditoria administrativa continua disponível para revisão.')
