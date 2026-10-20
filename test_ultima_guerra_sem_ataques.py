import copy
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock
from test_planejamento import guerra
from ww_competicao.ultima_guerra_sem_ataques import analisar, renderizar

NOW = datetime(2026,10,20,tzinfo=timezone.utc)

def documento(n=0):
    g=guerra();g['state']='warEnded';g['clan']['attacks']=n
    m=g['clan']['members'][0]
    if n:
        m['attacks']=[dict(attackerTag=m['tag'],defenderTag=g['opponent']['members'][0]['tag'],
                           stars=0,order=i+1,destructionPercentage=0) for i in range(n)]
    return {'planejamento':{'historico_comum':[{'dados':g,'tipo':'comum'}]}}

class UltimaGuerra(unittest.TestCase):
    def test_zero_sim_um_e_dois_nao_mesmo_sem_estrelas(self):
        self.assertEqual(len(analisar(documento(),NOW)['vilas']),1)
        for n in (1,2):self.assertEqual(analisar(documento(n),NOW)['vilas'],[])

    def test_ignora_atual_e_pega_mais_recente(self):
        d=documento()
        anterior=copy.deepcopy(d['planejamento']['historico_comum'][0])
        anterior['dados']['endTime']='20261003T100000.000Z'
        anterior['dados']['clan']['members'][0]['name']='Mais recente'
        d['planejamento']['historico_comum'].append(anterior)
        d['planejamento']['comum']={'dados':guerra()}
        self.assertEqual(analisar(d,NOW)['vilas'][0]['Vila'],'Mais recente')

    def test_exclui_liga(self):
        d=documento();d['planejamento']['historico_comum'][0]['tipo']='liga'
        self.assertIsNone(analisar(d,NOW))

    def test_incompleto_nao_vira_falta(self):
        for campo in ('members','attacks'):
            d=documento();del d['planejamento']['historico_comum'][0]['dados']['clan'][campo]
            with self.assertRaises((ValueError,KeyError)):analisar(d,NOW)

    def test_total_divergente_bloqueia(self):
        d=documento();d['planejamento']['historico_comum'][0]['dados']['clan']['attacks']=1
        with self.assertRaises(ValueError):analisar(d,NOW)

    def test_opponent_e_nao_inscrito_incluidos(self):
        d=documento();g=d['planejamento']['historico_comum'][0]['dados']
        g['clan'],g['opponent']=g['opponent'],g['clan']
        self.assertEqual(len(analisar(d,NOW)['vilas']),1)

    def test_futuro_bloqueado(self):
        d=documento();d['planejamento']['historico_comum'][0]['dados']['endTime']='20261021T100000.000Z'
        with self.assertRaises(ValueError):analisar(d,NOW)

    def test_sem_permissao_nao_exibe(self):
        st=Mock();renderizar(st,None,documento(),[['Usuario','Nivel']],'visitante')
        self.assertEqual(st.mock_calls,[])

    def test_membros_nao_escalados_nao_incluidos_e_fontes_preservadas(self):
        d=documento();d['membros']={'consultado_em':'2026-10-20T00:00:00+00:00',
                                  'contas':[{'tag':'#NOVO','nome':'Novo'}]}
        antes=copy.deepcopy(d)
        r=analisar(d,NOW)
        self.assertEqual(len(r['vilas']),1)
        self.assertEqual(r['vilas'][0]['No clã na última consulta'],'Não consta')
        self.assertEqual(d,antes)

if __name__=='__main__':unittest.main()
