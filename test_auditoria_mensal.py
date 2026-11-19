import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from contextlib import closing

from plataforma_api.auditoria_mensal import montar_ficha_mensal


class FichaMensal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / 'hist.sqlite3'
        with closing(sqlite3.connect(self.db)) as c:
            c.execute('CREATE TABLE versoes (sequencia INTEGER PRIMARY KEY, tipo TEXT, chave TEXT, sha256 TEXT, conteudo TEXT, registrado_em TEXT)')
        self.seq = 0
        self.estado('2026-10', 'TRUE')
        self.put('fonte', 'VinculosParticipantes', [['ParticipanteID', 'PlayerTag'], ['1', '#AAA']])
        self.put('fonte', 'ParticipacaoCompeticao', [['EventoID', 'PlayerTag', 'Habilitada', 'Origem'], ['p1', '#AAA', 'TRUE', 'CADASTRO']])
        self.put('fonte', 'InscricoesTemporada', [['Temporada', 'ParticipanteID', 'PlayerTag'], ['2026-10', '1', '#AAA'], ['2026-11', '1', '#AAA']])
        self.ranking(10, 3)
        self.estado('2026-11', 'FALSE')
        self.ranking(0, 2)
        self.atividade('antiga', '2026-10', 3)
        self.atividade('nova', '2026-11', 2)

    def put(self, tipo, chave, valor):
        self.seq += 1
        with closing(sqlite3.connect(self.db)) as c, c:
            c.execute('INSERT INTO versoes VALUES(?,?,?,?,?,?)', (self.seq, tipo, chave, 'hash', json.dumps(valor), '2026-11-18T00:00:00Z'))

    def estado(self, mes, fechado):
        self.put('fonte', 'EstadoMes', [['Chave', 'Valor'], ['temporada_atual_id', mes], ['mes_finalizado', fechado]])

    def ranking(self, jogos, guerra):
        self.put('fonte', 'Página1', [['ID', 'Nome', 'JogosCla', 'Eventos', 'Guerra_1'], ['1', 'Jogador', str(jogos), '0', str(guerra)]])

    def atividade(self, chave, mes, pontos, status='APLICADO', tipo='guerra'):
        self.put('atividade', chave, {'id': chave, 'temporada': mes, 'tipo': tipo,
            'status': status, 'fim': '20261101T010000.000Z', 'coluna': 'Guerra_1',
            'jogadores': [{'tag': '#AAA', 'nome': 'Jogador', 'pontos': pontos,
                'situacao': 'Pontuação registrada', 'ataques': [{'Estrelas': 3, 'CV alvo': 19, 'Destruição (%)': 100}],
                'quantidade_ataques': 6, 'saque': 30000, 'bonus': 1}]})

    def test_rodadas_disponiveis_nao_exigem_escalacao_do_jogador(self):
        self.put('atividade', 'liga-reserva', {'id': 'liga-reserva', 'tipo': 'liga',
            'temporada': '2026-11', 'status': 'APLICADO', 'rodada': 3,
            'jogadores': [{'tag': '#BBB', 'ataques': []}]})
        self.put('atividade', 'liga-pendente', {'id': 'liga-pendente', 'tipo': 'liga',
            'temporada': '2026-11', 'status': 'AGUARDANDO_LANCAMENTO', 'rodada': 4, 'jogadores': []})
        r = montar_ficha_mensal(self.db, '#AAA')
        self.assertEqual(r['liga_rodadas_disponiveis'], [3])
        self.assertFalse(any(x['tipo'] == 'liga' for x in r['registros']))
        self.assertEqual(montar_ficha_mensal(self.db, '#AAA', '2026-10')['liga_rodadas_disponiveis'], [])

    def test_padrao_temporada_vigente_sem_mesclar_registros(self):
        r = montar_ficha_mensal(self.db, '#AAA')
        self.assertEqual(r['temporada'], '2026-11')
        self.assertEqual([x['identificador'] for x in r['registros']], ['nova'])
        self.assertEqual(r['resumo']['jogos'], 0)
        self.assertEqual(r['temporadas'], ['2026-11', '2026-10'])

    def test_historico_usa_temporada_registrada_e_fechamento(self):
        r = montar_ficha_mensal(self.db, '#AAA', '2026-10')
        self.assertEqual([x['identificador'] for x in r['registros']], ['antiga'])
        self.assertEqual(r['resumo']['jogos'], 10)
        self.assertEqual(r['resumo']['total'], 13)
        self.assertIsNone(r['resumo']['posicao'])
        self.assertEqual(r['registros'][0]['jogador']['ataques'][0]['estrelas'], 3)

    def test_mes_vazio_nao_retorna_outro_mes(self):
        r = montar_ficha_mensal(self.db, '#AAA', '2026-12')
        self.assertEqual(r['total'], 0)
        self.assertIsNone(r['resumo']['total'])

    def test_deduplica_versoes_e_exclui_pendente(self):
        self.atividade('nova', '2026-11', 1)
        self.atividade('pendente', '2026-11', 3, status='AGUARDANDO_LANCAMENTO')
        r = montar_ficha_mensal(self.db, '#AAA')
        self.assertEqual(r['total'], 1)
        self.assertEqual(r['pontos_competicao'], 1)

    def test_mais_de_cem_atividades_nao_ocultam_mes_antigo(self):
        for i in range(105):
            self.atividade(f'nova{i}', '2026-11', 3)
        self.assertEqual(montar_ficha_mensal(self.db, '#AAA', '2026-10')['total'], 1)
        self.assertEqual(montar_ficha_mensal(self.db, '#AAA')['total'], 106)

    def test_raide_normaliza_saque_ataques_e_bonus(self):
        self.atividade('raide', '2026-11', 7, tipo='raide')
        r = montar_ficha_mensal(self.db, '#AAA')
        j = next(x['jogador'] for x in r['registros'] if x['tipo'] == 'raide')
        self.assertEqual((j['ataques'], j['capital_resources_looted'], j['bonus_top3']), (6, 30000, 1))

    def test_periodo_invalido(self):
        for mes in ('2026-13', '2026-1', 'todos', '2026-10-01'):
            with self.assertRaises(ValueError):
                montar_ficha_mensal(self.db, '#AAA', mes)

    def test_virada_muda_padrao_sem_alterar_historico(self):
        self.estado('2026-12', 'FALSE')
        r = montar_ficha_mensal(self.db, '#AAA')
        self.assertEqual((r['temporada'], r['total']), ('2026-12', 0))
        self.assertEqual(montar_ficha_mensal(self.db, '#AAA', '2026-10')['total'], 1)


if __name__ == '__main__':
    unittest.main()
