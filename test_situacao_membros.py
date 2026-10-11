import unittest

from ww_competicao.situacao_membros import montar, visivel_no_ranking


class SituacaoMembros(unittest.TestCase):
    def setUp(self):
        self.ranking = [
            ["ID", "Nome", "Raide_1", "Total"],
            ["1", "Titular", "6", "6"],
            ["2", "Visitante", "6", "6"],
        ]
        self.vinculos = [
            ["EventoID", "ParticipanteID", "PlayerTag", "Administrador", "RegistradoEm"],
            ["v1", "1", "#AAA", "auto", "2026-10-01T00:00:00+00:00"],
            ["v2", "2", "#BBB", "auto", "2026-10-01T00:00:00+00:00"],
        ]
        self.participacao = {
            "#AAA": {"Nome": "Titular", "Habilitada": "TRUE", "Origem": "CADASTRO"},
            "#BBB": {"Nome": "Visitante", "Habilitada": "TRUE", "Origem": "CADASTRO"},
        }

    def test_ausencia_apenas_sinaliza_revisao(self):
        versoes = [
            ({"consultado_em": "2026-10-01T00:00:00+00:00", "contas": [{"tag": "#AAA"}, {"tag": "#BBB"}]}, ""),
            ({"consultado_em": "2026-10-02T00:00:00+00:00", "contas": [{"tag": "#AAA"}]}, ""),
        ]
        relatorio = montar("2026-10", self.ranking, self.vinculos, {"#AAA", "#BBB"},
                          self.participacao, {"contas": [{"tag": "#AAA", "nome": "Titular"}]},
                          versoes, "2026-10-02T00:00:00+00:00")
        por_tag = {c["tag"]: c for c in relatorio["contas"]}
        self.assertEqual(por_tag["#BBB"]["situacao"], "AUSENTE_AGORA")
        self.assertEqual(por_tag["#BBB"]["habilitada"], "TRUE")
        self.assertEqual(por_tag["#BBB"]["pontos"], 6)

    def test_retorno_e_nova_entrada_sao_identificados(self):
        versoes = [
            ({"consultado_em": "2026-10-01T00:00:00+00:00", "contas": [{"tag": "#AAA"}]}, ""),
            ({"consultado_em": "2026-10-02T00:00:00+00:00", "contas": [{"tag": "#BBB"}]}, ""),
            ({"consultado_em": "2026-10-03T00:00:00+00:00", "contas": [{"tag": "#AAA"}, {"tag": "#BBB"}]}, ""),
        ]
        roster = {"contas": [{"tag": "#AAA", "nome": "Titular"}, {"tag": "#BBB", "nome": "Visitante"}]}
        relatorio = montar("2026-10", self.ranking, self.vinculos, {"#AAA", "#BBB"},
                          self.participacao, roster, versoes, "2026-10-03T00:00:00+00:00")
        por_tag = {c["tag"]: c for c in relatorio["contas"]}
        self.assertEqual(por_tag["#AAA"]["situacao"], "RETORNOU_AO_CLA")
        self.assertEqual(por_tag["#BBB"]["situacao"], "ENTROU_APOS_INICIO_DO_HISTORICO")

    def test_bloqueio_oculta_sem_apagar_identidade(self):
        vinculos = {"1": "#AAA", "2": "#BBB"}
        participacao = {
            "#AAA": {"Habilitada": "TRUE"},
            "#BBB": {"Habilitada": "FALSE"},
        }
        self.assertTrue(visivel_no_ranking("1", vinculos, participacao))
        self.assertFalse(visivel_no_ranking("2", vinculos, participacao))
        self.assertTrue(visivel_no_ranking("3", vinculos, participacao))


if __name__ == "__main__":
    unittest.main()
