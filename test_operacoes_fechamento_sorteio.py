import unittest

from plataforma_api.operacoes_admin import (
    _hash_sorteio, _proxima_temporada, _ranking_planilha, _temporada_nome,
)


class FechamentoESorteio(unittest.TestCase):
    def test_ranking_soma_atividades_e_preserva_ordem_no_empate(self):
        linhas = [
            ["ID", "Nome", "JogosCla", "Eventos", "Guerra_1", "Liga_1", "Raide_1"],
            ["1", "Alpha", "2", "0", "3", "1", "0"],
            ["2", "Beta", "0", "0", "0", "0", "6"],
            ["3", "Gamma", "5", "0", "0", "0", "0"],
        ]
        ranking = _ranking_planilha(linhas)
        self.assertEqual([item["nome"] for item in ranking], ["Alpha", "Beta", "Gamma"])
        self.assertEqual([item["total"] for item in ranking], [6, 6, 5])
        self.assertEqual([item["posicao"] for item in ranking], [1, 2, 3])

    def test_proxima_temporada_e_nome(self):
        self.assertEqual(_proxima_temporada("2026-11"), "2026-12")
        self.assertEqual(_proxima_temporada("2026-12"), "2027-01")
        self.assertEqual(_temporada_nome("2027-01"), "janeiro/2027")

    def test_hash_de_auditoria_e_deterministico(self):
        valores = ["id", "2026-11", "sem_liga", "7", "[]", "[]", "1", "admin", "data", "nonce"]
        self.assertEqual(_hash_sorteio(valores), _hash_sorteio(valores))
        self.assertNotEqual(_hash_sorteio(valores), _hash_sorteio([*valores[:-1], "outro"]))


if __name__ == "__main__":
    unittest.main()
