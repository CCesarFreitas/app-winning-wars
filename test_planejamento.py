import copy
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from ww_competicao.armazenamento import Arquivo, empacotar, desempacotar
from ww_competicao.planejamento_dados import coletar, validar_guerra, ataques, TAG


def guerra(a=TAG, b='#ENEMY'):
    return {'state': 'inWar', 'teamSize': 1, 'startTime': '20261001T100000.000Z',
            'endTime': '20261002T100000.000Z', 'attacksPerMember': 2,
            'clan': {'tag': a, 'name': 'Nosso ♤', 'members': [{'tag': a+'P', 'name': 'A', 'townhallLevel': 17, 'mapPosition': 1}]},
            'opponent': {'tag': b, 'name': 'Outro', 'members': [{'tag': b+'P', 'name': 'B', 'townhallLevel': 18, 'mapPosition': 1}]}}


class Planejamento(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.arquivo = Arquivo(Path(self.temp.name) / 'dados.db')
        self.now = datetime(2026, 10, 2, tzinfo=timezone.utc)
        self.grupo = {'state': 'inWar', 'season': '2026-10-02', 'clans': [
            {'tag': tag, 'name': tag, 'members': [{'tag': tag+'P', 'name': tag, 'townHallLevel': 17}]}
            for tag in [TAG] + ['#C'+str(i) for i in range(7)]],
            'rounds': [{'warTags': ['#WAR']}, {'warTags': ['#0']}]}
        self.calls = []

    def tearDown(self):
        self.arquivo.close()
        self.temp.cleanup()

    def buscar(self, path):
        self.calls.append(path)
        if path.endswith('leaguegroup'):
            return copy.deepcopy(self.grupo)
        if path.endswith('currentwar'):
            return {'state': 'notInWar'}
        return guerra(TAG, '#C0')

    def test_cache_compartilhado_e_placeholder(self):
        d = coletar(self.arquivo, self.buscar, self.now)
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(d['grupo']['dados']['season'], '2026-10-02')
        coletar(self.arquivo, self.buscar, self.now+timedelta(minutes=1))
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(desempacotar(empacotar({'planejamento': d}))['planejamento'], d)

    def test_falha_preserva_ultima_leitura(self):
        original = coletar(self.arquivo, self.buscar, self.now)
        def falha(_):
            raise RuntimeError('não publicar dados do erro')
        d = coletar(self.arquivo, falha, self.now+timedelta(minutes=30))
        self.assertEqual(d['grupo'], original['grupo'])
        self.assertEqual(len(d['pendencias']), 3)
        self.assertNotIn('não publicar', str(d))

    def test_encerrada_nao_consulta_novamente(self):
        def buscar(p):
            d = self.buscar(p)
            if p.startswith('/clanwarleagues/'):
                d['state'] = 'warEnded'
            return d
        coletar(self.arquivo, buscar, self.now)
        self.calls.clear()
        coletar(self.arquivo, buscar, self.now+timedelta(minutes=20))
        self.assertEqual(len(self.calls), 2)

    def test_limite_de_chamadas(self):
        d = coletar(self.arquivo, self.buscar, self.now, max_consultas=1)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(d['guerras_liga'], [])
        self.assertTrue(d['pendencias'])

    def test_lista_incompleta_e_outro_cla(self):
        g = guerra()
        g['clan']['members'] = []
        with self.assertRaises(ValueError):
            validar_guerra(g)
        with self.assertRaises(ValueError):
            validar_guerra(guerra('#A', '#B'))
        validar_guerra(guerra('#ENEMY', TAG))

    def test_estrelas_novas_e_primeiro_ataque(self):
        g = guerra()
        g['clan']['members'][0]['attacks'] = [
            {'attackerTag': TAG+'P', 'defenderTag': '#ENEMYP', 'stars': 3, 'order': 3, 'destructionPercentage': 100},
            {'attackerTag': TAG+'P', 'defenderTag': '#ENEMYP', 'stars': 2, 'order': 1, 'destructionPercentage': 80}]
        r = ataques(g, 'clan')
        self.assertEqual([a['Estrelas novas'] for a in r], [2, 1])
        self.assertEqual([a['Primeiro ataque'] for a in r], [True, False])
        self.assertEqual(ataques(g, 'opponent'), [])

    def test_preparacao_com_posicoes_do_elenco(self):
        g = guerra()
        g['state'] = 'preparation'
        g['clan']['members'][0]['mapPosition'] = 43
        validar_guerra(g, liga=True)
        g['clan']['members'][0]['mapPosition'] = 0
        with self.assertRaises(ValueError):
            validar_guerra(g, liga=True)

    def test_rodada_ou_grupo_invalido_nao_substitui(self):
        d = coletar(self.arquivo, self.buscar, self.now)
        self.grupo['clans'].pop()
        novo = coletar(self.arquivo, self.buscar, self.now+timedelta(minutes=30))
        self.assertEqual(novo['grupo'], d['grupo'])
        self.assertIn('grupo', novo['pendencias'])


if __name__ == '__main__':
    unittest.main()
