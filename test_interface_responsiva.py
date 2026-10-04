import unittest
from pathlib import Path

from ww_competicao.planejamento import filtrar_ataques, resumo_ataques, resumo_elenco


def guerra():
    return {
        'state': 'inWar', 'teamSize': 2, 'attacksPerMember': 1,
        'clan': {'tag': '#YVLGUJQY', 'name': 'Winning Wars', 'members': [
            {'tag': '#A', 'name': 'Alpha', 'townhallLevel': 17, 'mapPosition': 1,
             'attacks': [{'attackerTag': '#A', 'defenderTag': '#X', 'stars': 3,
                          'destructionPercentage': 100, 'order': 1}]},
            {'tag': '#B', 'name': 'Beta', 'townhallLevel': 16, 'mapPosition': 2},
        ]},
        'opponent': {'tag': '#OUTRO', 'name': 'Outro', 'members': [
            {'tag': '#X', 'name': 'Xray', 'townhallLevel': 18, 'mapPosition': 1},
            {'tag': '#Y', 'name': 'Yankee', 'townhallLevel': 17, 'mapPosition': 2},
        ]},
    }


class InterfaceResponsiva(unittest.TestCase):
    def test_resumo_elenco_compacto(self):
        resumo = resumo_elenco(guerra()['clan'])
        self.assertEqual(resumo['vilas'], 2)
        self.assertEqual(resumo['maior_cv'], 17)
        self.assertEqual(resumo['cv_medio'], 16.5)
        self.assertEqual(resumo['distribuicao'], [(17, 1), (16, 1)])

    def test_progresso_e_busca_de_ataques(self):
        resumo = resumo_ataques(guerra(), 'clan', 'liga')
        self.assertEqual((resumo['usados'], resumo['total'], resumo['restantes']), (1, 2, 1))
        self.assertEqual(resumo['taxa_triplos'], 100)
        self.assertEqual(len(filtrar_ataques(resumo['linhas'], 'xray')), 1)
        self.assertEqual(filtrar_ataques(resumo['linhas'], 'inexistente'), [])

    def test_app_remove_criacao_manual_e_oferece_cartoes_moveis(self):
        app = (Path(__file__).parent / 'app.py').read_text(encoding='utf-8')
        self.assertNotIn('Criar Guerra (', app)
        self.assertNotIn('Criar Liga (', app)
        self.assertNotIn('Criar Raide (', app)
        self.assertIn('class="mobile-list"', app)
        self.assertIn('cada jogador aparece em um cartão', app)


if __name__ == '__main__':
    unittest.main()
