import copy,io,unittest
from PIL import Image
from unittest.mock import Mock
from ww_competicao.desempenho_mensal import linhas,periodo,imagem,renderizar,grafico_interativo

def conta(estrelas,limite=2,tipo='guerra'):
    return {'nome':'Vila ♤ $x','tag':'#222','registros':[{'tipo':tipo,'jogador':{
        'ataques':[{'Estrelas':e} for e in estrelas], 'limite_ataques':limite}}]}

class Mensal(unittest.TestCase):
    def test_estrelas_nao_sao_pontos_e_taxa_ponderada(self):
        c=conta([3,2]);c['registros']+=conta([1,0])['registros']
        antes=copy.deepcopy(c);r=linhas([c],'guerra')[0]
        self.assertEqual(r['estrelas'],{0:1,1:1,2:1,3:1})
        self.assertEqual(r['taxa3'],25);self.assertEqual(r['atividades'],2)
        self.assertEqual(c,antes)

    def test_sem_ataque_nao_se_torna_zero_estrela(self):
        r=linhas([conta([])],'guerra')[0]
        self.assertEqual(r['faltas'],2);self.assertEqual(r['estrelas'][0],0)
        self.assertIsNone(r['taxa3'])
        r=linhas([conta([0])],'guerra')[0]
        self.assertEqual(r['taxa3'],0);self.assertEqual(r['faltas'],1)

    def test_modalidade_isolada_e_limite_desconhecido(self):
        c=conta([3],None);c['registros']+=conta([0],1,'liga')['registros']
        r=linhas([c],'guerra')[0]
        self.assertEqual(r['taxa3'],100);self.assertIsNone(r['faltas'])
        self.assertIsNone(r['uso'])

    def test_estrelas_invalidas_nao_geram_taxa_falsa(self):
        r=linhas([conta([True,3])],'guerra')[0]
        self.assertFalse(r['completos']);self.assertIsNone(r['taxa3'])

    def test_raide_media_ponderada_limite_real_e_sem_estrelas(self):
        c=conta([],5,'raide');j=c['registros'][0]['jogador']
        j.update(quantidade_ataques=5,saque=10000)
        segundo=copy.deepcopy(c['registros'][0]);segundo['jogador'].update(quantidade_ataques=1,saque=4000,limite_ataques=6)
        c['registros'].append(segundo)
        r=linhas([c],'raide')[0]
        self.assertAlmostEqual(r['saque_medio'],14000/6)
        self.assertEqual(r['faltas'],5);self.assertIsNone(r['taxa3'])

    def test_meses(self):
        self.assertEqual(periodo('2028-02')[1].day,29)
        self.assertEqual(periodo('2026-10')[0].day,1)

    def test_png_real_alta_resolucao(self):
        b=imagem(linhas([conta([3,1])],'guerra'),'guerra','2026-10','27/10/2026')
        with Image.open(io.BytesIO(b)) as im:
            self.assertEqual(im.format,'PNG');self.assertEqual(im.width,3000)
            self.assertGreaterEqual(im.height,1000);self.assertGreaterEqual(im.info['dpi'][0],249)

    def test_autorizacao_antes_dos_dados(self):
        st=Mock();renderizar(st,None,{},[['Usuario','Nivel']],'visitante')
        st.info.assert_called_once();st.image.assert_not_called()

    def test_grafico_interativo_preserva_contagens_e_nao_exibe_imagem(self):
        import pandas as pd
        st=Mock()
        grafico_interativo(st,pd,linhas([conta([3,1])],'guerra'),'guerra')
        frame=st.vega_lite_chart.call_args.args[0]
        self.assertEqual(frame['Percentual'].sum(),100)
        self.assertEqual(frame['Quantidade'].sum(),2)
        self.assertEqual(frame.loc[frame['Resultado']=='3 estrelas','Percentual'].iloc[0],50)
        st.image.assert_not_called()

    def test_grafico_sem_ataques_nao_fabrica_fatia_zero_estrelas(self):
        import pandas as pd
        st=Mock()
        grafico_interativo(st,pd,linhas([conta([])],'guerra'),'guerra')
        frame=st.vega_lite_chart.call_args.args[0]
        self.assertEqual(frame['Aviso'].iloc[0],'Sem ataques')
        self.assertNotIn('0 estrelas',frame['Resultado'].tolist())

if __name__=='__main__':unittest.main()
