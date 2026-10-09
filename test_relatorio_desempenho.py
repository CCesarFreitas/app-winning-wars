import copy
import unittest
from datetime import datetime, timezone, date
from unittest.mock import Mock
from ww_competicao.relatorio_desempenho import construir, faixas_cv, selecionar, csv_seguro, renderizar

AGORA = datetime(2026, 10, 9, 12, tzinfo=timezone.utc)


def jogador(tag='#222', ataques=1, limite=1, pontos=3):
    return {'tag': tag, 'nome': 'Vila ♤', 'pontos': pontos, 'situacao': 'Pontuação registrada',
        'limite_ataques': limite, 'ataques': [{'Estrelas': 3, 'CV atacante': 16, 'CV alvo': 17,
            'Destruição (%)': 100, 'Regra aplicada': 'Estrelas convertidas'} for _ in range(ataques)]}


def atividade(ident='1', tipo='liga', jogadores=None):
    return {'id': ident, 'tipo': tipo, 'fim': '20261004T015538.000Z', 'temporada': '2026-10',
            'status': 'APLICADO', 'coluna': tipo+'_1', 'jogadores': jogadores or [jogador()]}


class Relatorio(unittest.TestCase):
    def modelo(self, documentos, **kwargs): return construir(documentos, agora=AGORA, **kwargs)

    def test_ausencia_de_escala_nao_e_falta(self):
        d = {'atividade:1': atividade(), 'membros': {'contas': [{'tag': '#888', 'nome': 'Novato'}]}}
        c = self.modelo(d)['contas']['#888']
        self.assertEqual(c['resumo']['escalacoes'], 0)
        self.assertEqual(c['resumo']['alertas'], [])

    def test_escalado_sem_ataque_e_taxa_sem_amostra(self):
        d = {'atividade:1': atividade(jogadores=[jogador(ataques=0, pontos=None)])}
        r = self.modelo(d)['contas']['#222']['resumo']
        self.assertEqual((r['sem_ataque'], r['perdidos_guerra']), (1, 1))
        self.assertIsNone(r['taxa_triplos']); self.assertIsNone(r['pontos'])

    def test_raide_limite_real_sem_inventar_sexto(self):
        j = jogador(ataques=0, limite=5, pontos=5)
        j.update(quantidade_ataques=5, saque=10000, bonus=0)
        r = self.modelo({'atividade:1': atividade(tipo='raide', jogadores=[j])})['contas']['#222']['resumo']
        self.assertEqual(r['perdidos_raide'], 0); self.assertEqual(r['uso_raide'], 100)
        self.assertEqual(r['saque_por_ataque'], 2000)
        j['limite_ataques'] = 6
        r = self.modelo({'atividade:1': atividade(tipo='raide', jogadores=[j])})['contas']['#222']['resumo']
        self.assertEqual(r['perdidos_raide'], 1)

    def test_limite_ausente_nao_inventa_falta(self):
        j = jogador(ataques=0, limite=None)
        r = self.modelo({'atividade:1': atividade(jogadores=[j])})['contas']['#222']['resumo']
        self.assertEqual(r['perdidos_guerra'], 0); self.assertEqual(r['sem_limite_guerra'], 1)

    def test_parcial_futura_e_filtro_fuso(self):
        d = {'atividade:1': atividade(), 'atividade:2': atividade('2')}
        d['atividade:2']['fim'] = '20261010T010000.000Z'
        self.assertEqual(len(selecionar(d, date(2026,10,3), date(2026,10,3), agora=AGORA)[0]), 1)
        d['atividade:1']['status'] = 'EM_ANDAMENTO'
        self.assertEqual(len(selecionar(d, agora=AGORA)[0]), 0)

    def test_duplicidade_nao_infla_resultado(self):
        d = {'atividade:1': atividade(), 'atividade:2': atividade()}
        self.assertEqual(selecionar(d, agora=AGORA), ([], 1))
        a = atividade(jogadores=[jogador(), jogador()])
        self.assertEqual(selecionar({'atividade:1': a}, agora=AGORA), ([], 1))

    def test_pontos_bloqueados_nao_apagam_desempenho(self):
        j = jogador(pontos=None); j['situacao'] = 'Participação desabilitada'
        r = self.modelo({'atividade:1': atividade(jogadores=[j])})['contas']['#222']['resumo']
        self.assertEqual(r['triplos'], 1); self.assertEqual(r['taxa_triplos'], 100)
        self.assertIsNone(r['pontos'])

    def test_taxa_ponderada_e_minimo_ajustavel(self):
        j1 = jogador(ataques=1, limite=2)
        j2 = jogador(ataques=2, limite=2)
        for a in j2['ataques']: a['Estrelas'] = 1
        d = {'atividade:1': atividade('1', 'guerra', [j1]), 'atividade:2': atividade('2', 'guerra', [j2])}
        r = self.modelo(d)['contas']['#222']['resumo']
        self.assertAlmostEqual(r['taxa_triplos'], 100/3)
        self.assertTrue(any('Taxa' in a for a in r['alertas']))
        r = self.modelo(d, minimo_amostra=4)['contas']['#222']['resumo']
        self.assertFalse(any('Taxa' in a for a in r['alertas']))

    def test_faixas_penalidade_e_dados_preservados(self):
        j = jogador(); j['ataques'][0].update({'CV alvo': 14, 'Regra aplicada': 'Desconto de uma estrela'})
        d = {'atividade:1': atividade(jogadores=[j])}; antes = copy.deepcopy(d)
        c = self.modelo(d)['contas']['#222']
        self.assertEqual(faixas_cv(c['registros'])[0]['CV do alvo'], '2 ou mais abaixo')
        self.assertEqual(c['resumo']['penalizados'], 1); self.assertEqual(d, antes)

    def test_nao_admin_bloqueado_antes_de_relatorio(self):
        st = Mock()
        renderizar(st, None, {}, [['Usuario','Nivel'],['visitante','membro']], 'visitante')
        st.info.assert_called_once(); st.markdown.assert_not_called()

    def test_csv_neutraliza_formulas_preserva_unicode(self):
        text = csv_seguro([{'Vila': '=HYPERLINK("x")', 'Tag': '#222', 'Nome': '♤'}]).decode('utf-8-sig')
        self.assertIn("'=HYPERLINK", text); self.assertIn('♤', text)


if __name__ == '__main__': unittest.main()
