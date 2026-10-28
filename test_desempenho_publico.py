import unittest
from unittest.mock import Mock,patch
from test_relatorio_desempenho import atividade,jogador
from ww_competicao.desempenho_publico import renderizar


class Publico(unittest.TestCase):
    def test_sem_selecao_sem_consulta_manual_nem_relatorio(self):
        st=Mock();st.selectbox.side_effect=['2026-10',''];manual=Mock()
        with patch('ww_competicao.desempenho_individual.renderizar') as individual:
            renderizar(st,None,{'atividade:1':atividade()},manual)
            individual.assert_not_called();manual.assert_not_called()

    def test_somente_selecionado_e_jogos_da_temporada(self):
        st=Mock();st.selectbox.side_effect=['2026-10','#222']
        registros=[{'PlayerTag':'#222','Temporada':'2026-10','Atividade':'JogosCla'},
                   {'PlayerTag':'#888','Temporada':'2026-10','Atividade':'JogosCla'},
                   {'PlayerTag':'#222','Temporada':'2026-09','Atividade':'JogosCla'}]
        with patch('ww_competicao.desempenho_individual.renderizar') as individual:
            renderizar(st,None,{'atividade:1':atividade(jogadores=[jogador(),jogador('#888')])},lambda:registros)
            args=individual.call_args.args
            self.assertEqual(args[2]['tag'],'#222')
            self.assertEqual(args[5](),registros[:1])
            self.assertTrue(individual.call_args.kwargs['publico'])
            self.assertNotIn('total_raides',individual.call_args.kwargs)

    def test_interface_publica_e_admin_sem_conflito(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_string('''
import streamlit as st
import pandas as pd
from test_relatorio_desempenho import atividade,jogador
from ww_competicao.desempenho_publico import renderizar
from ww_competicao.desempenho_mensal import renderizar as admin
d={'atividade:1':atividade(jogadores=[jogador(),jogador('#888')])}
renderizar(st,pd,d)
admin(st,pd,d,[['Usuario','Nivel'],['teste','Dono']],'teste')
''').run(timeout=60)
        self.assertFalse(app.exception)
        app.selectbox(key='dp_vila').set_value('#222').run(timeout=60)
        self.assertFalse(app.exception)
        app.multiselect(key='dm_vilas').set_value(['#888']).run(timeout=60)
        self.assertFalse(app.exception)
        keys=[b.key for b in app.get('download_button')]
        self.assertIn('dp_individual_png',keys);self.assertIn('di_png',keys)
