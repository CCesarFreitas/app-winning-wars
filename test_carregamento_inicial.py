import pathlib
import unittest


class CarregamentoInicial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.codigo = pathlib.Path("app.py").read_text(encoding="utf-8")

    def test_abas_principais_usam_execucao_preguicosa(self):
        self.assertIn('key="ww_abas_principais"', self.codigo)
        self.assertIn('on_change="rerun"', self.codigo)
        for aba in (
            "tab_ranking", "tab_tabela", "tab_historico_mes", "tab_perfil",
            "tab_agenda", "tab_atividades", "tab_planejamento", "tab_membros",
            "tab_admin",
        ):
            self.assertIn(f"if {aba}.open:", self.codigo)

    def test_dados_secundarios_nao_bloqueiam_ranking(self):
        trecho_inicial = self.codigo.split("# --- FUNÇÃO PARA GERAR A TABELA", 1)[0]
        self.assertNotIn(
            "df_historico_mensal = pd.DataFrame(obter_historico_mensal_cached())",
            trecho_inicial,
        )
        self.assertNotIn(
            "df_temporadas = pd.DataFrame(obter_temporadas_cached())",
            trecho_inicial,
        )
        self.assertIn("df_novidades = pd.DataFrame()", trecho_inicial)
        self.assertIn("df_eventos = pd.DataFrame()", trecho_inicial)


if __name__ == "__main__":
    unittest.main()
