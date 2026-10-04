"""Execute com PYTHONPATH apontando para os módulos oficiais do motor."""
import copy
import hashlib
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from ww_competicao.detalhes_atividade import detalhar
from ww_competicao.historico_publico import PLANILHA
from identidade_atividades import identificar_atividade


def sha(d):
    return hashlib.sha256(json.dumps(d, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        d = datetime(2026, 10, 8, tzinfo=timezone.utc)
        return d.astimezone(tz) if tz else d.replace(tzinfo=None)


class DetalhesMotor(unittest.TestCase):
    def setUp(self):
        for modulo in ('preparar_calculo_guerra_auto', 'validar_captura_liga', 'validar_captura_raide',
                       'ww_competicao.historico_publico'):
            p = patch(modulo+'.datetime', Clock)
            p.start(); self.addCleanup(p.stop)
        rede = patch('socket.socket', side_effect=AssertionError('Rede proibida'))
        rede.start(); self.addCleanup(rede.stop)
        self.g = {'state': 'warEnded', 'teamSize': 1, 'attacksPerMember': 2,
            'startTime': '20261001T070000.000Z', 'endTime': '20261002T070000.000Z',
            'clan': {'tag': '#YVLGUJQY', 'attacks': 1, 'members': [{'tag': '#222', 'name': 'Vila ♤',
                'townhallLevel': 16, 'mapPosition': 1, 'attacks': [{'attackerTag': '#222',
                    'defenderTag': '#888', 'stars': 3, 'order': 1}]}]},
            'opponent': {'tag': '#2YPL9GU8Y', 'attacks': 0, 'members': [{'tag': '#888', 'name': 'Alvo',
                'townhallLevel': 14, 'mapPosition': 1}]}}

    def guerra(self):
        return {'versao': 1, 'origem': 'api_guerra_atual', 'guerra': self.g, 'conteudo_sha256': sha(self.g),
            'temporada_origem': '2026-10', 'atividade_id': identificar_atividade('guerra', '#YVLGUJQY',
                self.g['startTime'], oponente='#2YPL9GU8Y')}

    def registro(self, c, tipo, pontos=2):
        d = {'ficticia': False, 'planilha': PLANILHA, 'captura_sha256': c['conteudo_sha256'],
             'pontos_por_participante': {'1': pontos}, 'tags': {'1': '#222'}}
        if tipo == 'raide':
            d['raide_por_participante'] = {'1': {'ataques': 6, 'saque': 100, 'bonus_top3': 1}}
        return {'AtividadeID': c['atividade_id'], 'Temporada': '2026-10', 'Tipo': tipo, 'ClanTag': '#YVLGUJQY',
            'Inicio': self.g['startTime'], 'Fim': self.g['endTime'], 'ColunaDestino': 'Atividade_1',
            'Status': 'APLICADO', 'VersaoRegra': 'v1', 'AplicadoEm': '2026-10-02T08:00:00+00:00',
            'DetalhesJSON': json.dumps(d), 'HashResultado': sha(d)}

    def test_guerra_desconto_e_pendente_sem_pontos_oficiais(self):
        c = self.guerra()
        j = detalhar(c, 'guerra')['jogadores'][0]
        self.assertIsNone(j['pontos'])
        self.assertEqual(j['pontos_calculados'], 2)
        self.assertIn('Desconto', j['ataques'][0]['Regra aplicada'])
        self.assertEqual(detalhar(c, 'guerra', self.registro(c, 'guerra'))['jogadores'][0]['pontos'], 2)

    def test_parcial_adulterada_e_resultado_divergente(self):
        c = self.guerra()
        c['guerra']['state'] = 'inWar'; c['conteudo_sha256'] = sha(c['guerra'])
        with self.assertRaises(ValueError): detalhar(c, 'guerra')
        c['guerra']['state'] = 'warEnded'
        with self.assertRaises(ValueError): detalhar(c, 'guerra')
        c = self.guerra()
        with self.assertRaises(ValueError): detalhar(c, 'guerra', self.registro(c, 'guerra', 3))

    def test_liga_dois_contra_superior(self):
        self.g['attacksPerMember'] = 1
        self.g['opponent']['members'][0]['townhallLevel'] = 17
        self.g['clan']['members'][0]['attacks'][0]['stars'] = 2
        c = {'versao': 1, 'origem': 'api_liga', 'clan_tag': '#YVLGUJQY', 'temporada_liga': '2026-10',
             'rodada': 1, 'war_tag': '#PPP', 'guerra': self.g, 'temporada_origem': '2026-10'}
        c['conteudo_sha256'] = sha({k: c[k] for k in ('clan_tag', 'temporada_liga', 'rodada', 'war_tag', 'guerra')})
        c['atividade_id'] = identificar_atividade('liga', '#YVLGUJQY', self.g['startTime'], oponente='#2YPL9GU8Y', war_tag='#PPP')
        j = detalhar(c, 'liga', self.registro(c, 'liga', 3))['jogadores'][0]
        self.assertEqual(j['pontos'], 3)
        self.assertIn('Duas estrelas', j['ataques'][0]['Regra aplicada'])

    def test_correcao_auditada_inclui_conta_omitida(self):
        self.g['attacksPerMember'] = 1
        c = {'versao': 1, 'origem': 'api_liga', 'clan_tag': '#YVLGUJQY', 'temporada_liga': '2026-10',
             'rodada': 1, 'war_tag': '#PPP', 'guerra': self.g, 'temporada_origem': '2026-10'}
        c['conteudo_sha256'] = sha({k: c[k] for k in ('clan_tag', 'temporada_liga', 'rodada', 'war_tag', 'guerra')})
        c['atividade_id'] = identificar_atividade('liga', '#YVLGUJQY', self.g['startTime'], oponente='#2YPL9GU8Y', war_tag='#PPP')
        registro = self.registro(c, 'liga', 3)
        detalhes = json.loads(registro['DetalhesJSON'])
        detalhes['pontos_por_participante'] = {'99': 1}
        detalhes['tags'] = {'99': '#888'}
        registro['DetalhesJSON'] = json.dumps(detalhes)
        registro['HashResultado'] = sha(detalhes)
        revisao = {'Temporada': '2026-10', 'ParticipanteID': '30', 'Atividade': 'Atividade_1',
                   'Depois': '3', 'RegistradoEm': '2026-10-04T18:00:00+00:00'}
        j = detalhar(c, 'liga', registro, (), {'#222': '30'}, [revisao])['jogadores'][0]
        self.assertEqual(j['participante_id'], '30')
        self.assertEqual(j['pontos'], 3)
        self.assertIn('correção auditada', j['situacao'])

    def test_raide_saque_bonus_e_sem_dados_admin(self):
        raid = {'state': 'ended', 'startTime': self.g['startTime'], 'endTime': self.g['endTime'],
            'totalAttacks': 6, 'capitalTotalLoot': 100, 'members': [{'tag': '#222', 'name': 'Vila ♤',
                'attacks': 6, 'attackLimit': 5, 'bonusAttackLimit': 1, 'capitalResourcesLooted': 100}]}
        c = {'versao': 1, 'origem': 'api_capitalraidseasons', 'clan_tag': '#YVLGUJQY', 'raid': raid,
            'conteudo_sha256': sha({'clan_tag': '#YVLGUJQY', 'raid': raid}), 'temporada_origem': '2026-10',
            'atividade_id': identificar_atividade('raide', '#YVLGUJQY', raid['startTime'])}
        d = detalhar(c, 'raide', self.registro(c, 'raide', 7))
        self.assertEqual(d['jogadores'][0]['bonus'], 1)
        self.assertEqual(d['jogadores'][0]['saque'], 100)


if __name__ == '__main__': unittest.main()
