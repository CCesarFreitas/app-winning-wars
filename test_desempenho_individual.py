import io
import unittest
from PIL import Image
from ww_competicao.desempenho_individual import jogos_do_mes, exportar
from ww_competicao.manual import HEADER, hash_json

def registro(valor, depois, data='2026-10-27T12:00:00+00:00', tag='#222', mes='2026-10'):
    r=['evento',mes,tag,'1','JogosCla',str(valor),'0',str(depois),'admin',data,'{}']
    return dict(zip(HEADER,r+[hash_json(r)]))

class Individual(unittest.TestCase):
    def test_ausente_nao_e_zero(self):
        self.assertIsNone(jogos_do_mes([], '#222', '2026-10'))
        self.assertEqual(jogos_do_mes([registro(1000,0)], '#222', '2026-10')['competicao'],0)

    def test_revisao_substitui_e_isola_tag_mes(self):
        regs=[registro(4000,5),registro(10000,10,'2026-10-28T12:00:00+00:00'),
              registro(10000,10,tag='#333'),registro(10000,10,mes='2026-09')]
        self.assertEqual(jogos_do_mes(regs,'#222','2026-10')['jogo'],10000)
        self.assertEqual(jogos_do_mes(regs,'#222','2026-10')['competicao'],10)

    def test_adulteracao_bloqueada(self):
        r=registro(4000,5);r['ValorInformado']='10000'
        with self.assertRaises(ValueError):jogos_do_mes([r],'#222','2026-10')

    def test_exportacao_sem_modalidades(self):
        png=exportar({'nome':'Teste','tag':'#222','registros':[]},'2026-10','agora')
        img=Image.open(io.BytesIO(png))
        self.assertEqual(img.width,3000)
        self.assertGreater(img.height,3000)
