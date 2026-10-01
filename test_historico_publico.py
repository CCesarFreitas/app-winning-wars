import unittest,json,hashlib,copy
from datetime import datetime,timezone
from ww_competicao.historico_publico import atividades_publicas,PLANILHA

class HistoricoPublico(unittest.TestCase):
    def setUp(self):
        self.agora=datetime(2026,10,7,tzinfo=timezone.utc)
        self.d={'ficticia':False,'planilha':PLANILHA,'pontos_por_participante':{'1':7},'tags':{'1':'#222'},
            'raide_por_participante':{'1':{'ataques':6,'saque':12000,'bonus_top3':1}},
            'administrador':'NAO_PUBLICAR','motivo':'NAO_PUBLICAR'}
        self.r={'AtividadeID':'ww1_raide_abc','Tipo':'raide','Status':'APLICADO','ClanTag':'#YVLGUJQY',
            'Inicio':'20261002T070000.000Z','Fim':'20261005T070000.000Z','AplicadoEm':'2026-10-05T08:00:00+00:00',
            'Temporada':'2026-10','ColunaDestino':'Raide_1'}
    def registro(self):
        r=copy.deepcopy(self.r);r['DetalhesJSON']=json.dumps(self.d)
        r['HashResultado']=hashlib.sha256(json.dumps(self.d,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        return r
    def test_raide_encerrado_e_sem_dados_privados(self):
        a=atividades_publicas([self.registro()],self.agora)
        self.assertEqual(a[0]['jogadores'][0]['Pontos lançados'],7)
        self.assertNotIn('NAO_PUBLICAR',str(a))
    def test_parcial_futuro_e_nao_aplicado_ocultos(self):
        for k,v in [('Fim','20261008T070000.000Z'),('Status','PENDENTE'),('Status','inWar'),('AplicadoEm','2026-10-04T08:00:00+00:00')]:
            r=self.registro();r[k]=v;self.assertEqual(atividades_publicas([r],self.agora),[])
    def test_fixture_hash_alterado_e_duplicado_ocultos(self):
        r=self.registro();r['HashResultado']='invalido'
        self.assertEqual(atividades_publicas([r],self.agora),[])
        r=self.registro();self.assertEqual(atividades_publicas([r,r],self.agora),[])
        self.d['ficticia']=True;self.assertEqual(atividades_publicas([self.registro()],self.agora),[])
    def test_raide_inconsistente_oculto(self):
        self.d['raide_por_participante']['1']['bonus_top3']=0
        self.assertEqual(atividades_publicas([self.registro()],self.agora),[])
    def test_guerra_liga_zero_e_persistencia_outra_temporada(self):
        self.d['pontos_por_participante']['1']=0
        for tipo in ('guerra','liga'):
            self.r['Tipo']=tipo
            a=atividades_publicas([self.registro()],datetime(2026,11,1,tzinfo=timezone.utc))
            self.assertEqual(a[0]['jogadores'][0]['Pontos lançados'],0)
            self.assertNotIn('Ataques',a[0]['jogadores'][0])

if __name__=='__main__':unittest.main()
