import unittest
import io
from PIL import Image
from ww_competicao.feedback_imagem import indicadores,exportar
from test_desempenho_mensal import conta

class Feedback(unittest.TestCase):
    def test_completas_zero_parcial_e_limite_desconhecido(self):
        c=conta([3,2]);c['registros']+=conta([])['registros']+conta([1])['registros']+conta([3],None)['registros']
        r=indicadores(c,'guerra')
        self.assertEqual((r['atividades'],r['completas'],r['zeradas'],r['conhecidas']),(4,1,1,3))
        self.assertIsNone(r['faltas'])
        self.assertIsNone(indicadores(c,'liga'))

    def test_raide_limite_real(self):
        c=conta([],5,'raide');c['registros'][0]['jogador'].update(quantidade_ataques=5,saque=10000)
        r=indicadores(c,'raide')
        self.assertEqual(r['completas'],1);self.assertEqual(r['faltas'],0)

    def test_png_completo_jogos_e_sem_registro(self):
        c=conta([3,2])
        png=exportar(c,'2026-10','27/10/2026',{'jogo':4000,'competicao':5,'data':'27/10/2026'},total_raides=4)
        im=Image.open(io.BytesIO(png));self.assertEqual(im.size,(3000,3750))
        self.assertAlmostEqual(im.info['dpi'][0],250,delta=1)
        self.assertTrue(exportar(c,'2026-10','agora',jogos_estado='erro'))
