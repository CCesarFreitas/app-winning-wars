import unittest
from copy import deepcopy
from ww_competicao.jogos_lote import preparar_lote,conferir_lote
from ww_competicao.manual import HEADER
from ww_competicao.planejar_inscricao_automatica import IA_HEADER
from ww_competicao.vinculos_competicao import VC_HEADER
from ww_competicao.participacao_competicao import PC_CABECALHO


def fontes():
    tabelas={'ranking':[['ID','Nome','JogosCla','Eventos']], 'inscricoes':[IA_HEADER],
        'vinculos':[VC_HEADER],'participacao':[PC_CABECALHO], 'manual':[HEADER],
        'admins':[['Usuario','Nivel'],['teste','Dono']],
        'estado':[['Chave','Valor'],['temporada_atual_id','2026-10'],['mes_finalizado','FALSE']]}
    f={n:{'valores':deepcopy(t),'formulas':deepcopy(t)} for n,t in tabelas.items()}
    m={n:{'id':i+1,'linhas':1,'colunas':len(t[0])} for i,(n,t) in enumerate(tabelas.items()) if n not in ('admins','estado')}
    m['manual']['nova']=True
    return f,m


def aplicar(f,m,p):
    f=deepcopy(f)
    nomes={v['id']:k for k,v in m.items()}
    for pedido in p['lote']['requests']:
        if 'updateCells' not in pedido:continue
        u=pedido['updateCells'];s=u['start'];n=nomes[s['sheetId']]
        for modo in ('valores','formulas'):
            t=f[n][modo]
            for i,linha in enumerate(u['rows'],s['rowIndex']):
                while len(t)<=i:t.append([])
                for j,c in enumerate(linha['values'],s['columnIndex']):
                    while len(t[i])<=j:t[i].append('')
                    t[i][j]=str(next(iter(c['userEnteredValue'].values())))
    return f


class Lote(unittest.TestCase):
    def test_interface_tabela_numerica_sem_consultas(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_string('''
import streamlit as st
from types import SimpleNamespace
from test_jogos_lote import fontes,aplicar
from ww_competicao.jogos_lote import preparar_lote,renderizar
f,m=fontes()
p=preparar_lote(f,m,'teste',[{'tag':'#222','nome':'A','valor':4000}])
f=aplicar(f,m,p)
st.session_state.setdefault('ww_jogos_lote_v1',dict(foto=f,metas=m,editor='teste'))
renderizar(st,None,SimpleNamespace(title='Ranking'),'teste',lambda:None,lambda:None)
''').run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe),1)
        self.assertEqual(app.dataframe[0].value.iloc[0]['Tag'],'#222')

    def test_bloqueio_admin_e_formula(self):
        f,m=fontes();e={'tag':'#222','nome':'A','valor':4000}
        p=preparar_lote(f,m,'teste',[e]);f=aplicar(f,m,p);m['manual']['nova']=False
        f['ranking']['formulas'][1][2]='=5'
        with self.assertRaises(ValueError):preparar_lote(f,m,'teste',[e])
        f['ranking']['formulas'][1][2]='5'
        import uuid
        for modo in ('valores','formulas'):
            f['participacao'][modo].append([str(uuid.uuid4()),'#222','A','FALSE','teste','bloqueio','2026-10-28T12:00:00+00:00','ADMIN'])
        with self.assertRaises(ValueError):preparar_lote(f,m,'teste',[e])

    def test_novatos_ids_distintos_auditoria_e_repeticao_sem_soma(self):
        f,m=fontes();antes=deepcopy(f)
        es=[{'tag':'#222','nome':'A ♤','valor':10000},{'tag':'#228','nome':'B','valor':4000}]
        p=preparar_lote(f,m,'teste',es)
        self.assertEqual(f,antes)
        self.assertEqual([r['id'] for r in p['propostas']],['1','2'])
        self.assertEqual(sum('addSheet' in r for r in p['lote']['requests']),1)
        final=aplicar(f,m,p);conferir_lote(final,p)
        m['manual']['nova']=False
        p2=preparar_lote(final,m,'teste',es)
        self.assertEqual([(r['antes'],r['pontos']) for r in p2['propostas']],[(10,10),(5,5)])

    def test_zero_novato_nao_cria_e_invalido_bloqueia(self):
        f,m=fontes()
        p=preparar_lote(f,m,'teste',[{'tag':'#222','nome':'A','valor':1500}])
        self.assertEqual(p['lote']['requests'],[])
        for v in (True,10001,-1,2.5):
            with self.assertRaises(ValueError):preparar_lote(f,m,'teste',[{'tag':'#222','nome':'A','valor':v}])

    def test_duplicado_e_sem_permissao(self):
        f,m=fontes();e={'tag':'#222','nome':'A','valor':4000}
        with self.assertRaises(ValueError):preparar_lote(f,m,'teste',[e,e])
        with self.assertRaises(PermissionError):preparar_lote(f,m,'intruso',[e])

    def test_zero_existente_gravado_e_correcao_detectada(self):
        f,m=fontes();e={'tag':'#222','nome':'A','valor':4000}
        p=preparar_lote(f,m,'teste',[e]);f=aplicar(f,m,p);m['manual']['nova']=False
        e['valor']=0;p=preparar_lote(f,m,'teste',[e]);f=aplicar(f,m,p);conferir_lote(f,p)
        f['ranking']['valores'][1][2]='5'
        with self.assertRaises(ValueError):conferir_lote(f,p)
