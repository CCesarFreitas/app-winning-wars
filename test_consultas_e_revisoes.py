import copy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from ww_competicao.armazenamento import Arquivo, empacotar, desempacotar
from ww_competicao.revisoes import preparar, conferir, renderizar, HEADER


class ArquivoTest(unittest.TestCase):
    def test_versoes_repeticao_reversao_e_restauracao(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            a = Arquivo(Path(d)/'a.db')
            for valor in (1, 1, 2, 1):
                a.guardar('atividade', 'x', {'pontos': valor}, '2026-10-02')
            self.assertEqual(a.db.execute('SELECT count(*) FROM versoes').fetchone()[0], 3)
            a.backup(Path(d)/'b.db')
            b = Arquivo(Path(d)/'b.db')
            self.assertEqual(b.ultimos('atividade'), {'x': {'pontos': 1}})
            a.close(); b.close()

    def test_publicacao_unicode_e_partes(self):
        dados = {'atividade:x': {'nome': '♤漢字'*30000}, 'saude': {'ok': True}}
        linhas = empacotar(dados)
        self.assertEqual(desempacotar(linhas), dados)
        with self.assertRaises(ValueError):
            desempacotar(linhas + [linhas[1]])
        with self.assertRaises(ValueError):
            desempacotar(linhas[:1] + linhas[2:])


class RevisoesTest(unittest.TestCase):
    def setUp(self):
        self.f = {'admins': [['Usuario', 'Nivel'], ['caio', 'Líder']],
                  'estado': [['Chave', 'Valor'], ['mes_finalizado', 'FALSE'], ['temporada_atual_id', '2026-10']],
                  'ranking': [['ID', 'Nome', 'Guerra_1'], ['2', '♤ Nome', '3']], 'revisoes': [HEADER]}
        self.ids = {'ranking': 1, 'revisoes': 2}

    def proposta(self, **kwargs):
        args = dict(foto=self.f, ids=self.ids, usuario='caio', pid='2', coluna='Guerra_1', depois=2,
                    motivo='Revisão do ataque', revisao_id='revisao-1', agora='2026-10-02T12:00:00+00:00')
        args.update(kwargs)
        return preparar(**args)

    def test_ponto_e_auditoria_atomicos_identidade_por_id(self):
        p = self.proposta()
        self.assertEqual(len(p['lote']['requests']), 2)
        self.assertEqual(p['registro'][5:7], [3, 2])
        self.f['ranking'][1][2] = '2'
        self.f['revisoes'].append(p['registro'])
        conferir(self.f, p)
        with self.assertRaises(ValueError):
            self.proposta(depois=1)

    def test_sem_autorizacao_sem_correcao(self):
        self.f['admins'][1][1] = 'Membro'
        with self.assertRaises(PermissionError):
            self.proposta()

    def test_formula_mes_fechado_limite_e_justificativa(self):
        for valor in ('=3', '', 'nan', '-1'):
            self.f['ranking'][1][2] = valor
            with self.assertRaises(ValueError):
                self.proposta()
        self.f['ranking'][1][2] = '3'
        for kwargs in ({'depois': 4}, {'depois': True}, {'motivo': ''}, {'coluna': 'Nome'}):
            with self.assertRaises(ValueError):
                self.proposta(**kwargs)
        self.f['estado'][1][1] = 'TRUE'
        with self.assertRaises(ValueError):
            self.proposta()

    def test_resposta_perdida_e_alteracao_posterior(self):
        p = self.proposta()
        with self.assertRaises(ValueError):
            conferir(self.f, p)
        self.f['revisoes'].append(p['registro'])
        self.f['ranking'][1][2] = '1'
        with self.assertRaisesRegex(ValueError, 'mudou depois'):
            conferir(self.f, p)

    def test_tela_releitura_e_resposta_perdida_nao_reenvia(self):
        p = self.proposta()
        st = MagicMock()
        st.session_state = {'ww_revisao_v1': {'foto': copy.deepcopy(self.f), 'ids': self.ids, 'proposta': p}}
        st.form_submit_button.return_value = False
        st.button.side_effect = lambda label, **kw: label == 'Confirmar correção e registrar histórico'
        planilha = MagicMock()
        def gravar(lote):
            self.f['ranking'][1][2] = '2'
            self.f['revisoes'].append(p['registro'])
            raise TimeoutError('Resposta perdida')
        planilha.batch_update.side_effect = gravar
        with patch('ww_competicao.revisoes.fotografar', side_effect=lambda *args: (copy.deepcopy(self.f), self.ids)):
            renderizar(st, planilha, SimpleNamespace(title='Página1'), 'caio', MagicMock())
            self.assertIn('pendente', st.session_state['ww_revisao_v1'])
            st.button.side_effect = lambda label, **kw: label == 'Conferir revisão enviada'
            renderizar(st, planilha, SimpleNamespace(title='Página1'), 'caio', MagicMock())
        planilha.batch_update.assert_called_once()
        self.assertEqual(st.session_state['ww_revisao_v1'], {})

    def test_tela_dados_mudaram_sem_escrita(self):
        st = MagicMock()
        st.session_state = {'ww_revisao_v1': {'foto': copy.deepcopy(self.f), 'ids': self.ids, 'proposta': self.proposta()}}
        st.form_submit_button.return_value = False
        st.button.side_effect = lambda label, **kw: label == 'Confirmar correção e registrar histórico'
        self.f['ranking'][1][2] = '1'
        planilha = MagicMock()
        with patch('ww_competicao.revisoes.fotografar', return_value=(self.f, self.ids)):
            renderizar(st, planilha, SimpleNamespace(title='Página1'), 'caio', MagicMock())
        planilha.batch_update.assert_not_called()
        st.error.assert_called_once()


if __name__ == '__main__':
    unittest.main()
