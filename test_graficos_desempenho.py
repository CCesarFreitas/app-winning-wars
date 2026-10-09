import copy
import unittest
from ww_competicao.graficos_desempenho import dados, ficha_html


def conta(tipo='liga', nome='Vila ♤'):
    return {'nome': nome, 'tag': '#222', 'registros': [
        {'tipo': tipo, 'jogador': {'ataques': [{'Estrelas': 3, 'CV atacante': 16, 'CV alvo': 17}],
         'limite_ataques': 1, 'quantidade_ataques': 1, 'saque': 1000}}]}


class Graficos(unittest.TestCase):
    def test_taxas_ponderadas_e_fontes_preservadas(self):
        c = conta()
        c['registros'].append({'tipo': 'liga', 'jogador': {'ataques': [], 'limite_ataques': 1}})
        original = copy.deepcopy(c)
        d = dados([c], 'liga')[0]
        self.assertEqual(d['Uso (%)'], 50)
        self.assertEqual(d['Triplos (%)'], 100)
        self.assertEqual(d['Ataques'], 1)
        self.assertEqual(c, original)

    def test_limite_desconhecido_nao_estima_uso(self):
        c = conta(); c['registros'][0]['jogador']['limite_ataques'] = None
        self.assertIsNone(dados([c], 'liga')[0]['Uso (%)'])

    def test_zero_ataques_nao_e_zero_estrelas(self):
        c = conta(); c['registros'][0]['jogador']['ataques'] = []
        d = dados([c], 'liga')[0]
        self.assertEqual(d['Uso (%)'], 0)
        self.assertIsNone(d['Triplos (%)'])

    def test_saque_por_ataque_ponderado(self):
        c = conta('raide')
        c['registros'].append({'tipo': 'raide', 'jogador': {'ataques': [], 'limite_ataques': 6,
            'quantidade_ataques': 6, 'saque': 18000}})
        self.assertAlmostEqual(dados([c], 'raide')[0]['Saque/ataque'], 19000/7)

    def test_ficha_escapa_nome_e_nao_inclui_outras_contas(self):
        c = conta(nome='<script>alert(1)</script> ♤')
        ficha = ficha_html(c, '2026-10-01', '2026-10-09').decode('utf-8')
        self.assertNotIn('<script>', ficha)
        self.assertIn('&lt;script&gt;', ficha)
        self.assertIn('1 de 1', ficha)
        self.assertIn('♤', ficha)
        self.assertNotIn('https://', ficha)


if __name__ == '__main__':
    unittest.main()
