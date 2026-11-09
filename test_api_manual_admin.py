import unittest
from unittest.mock import patch

from plataforma_api import manual_admin


class ManualAdmin(unittest.TestCase):
    def test_limites_jogos(self):
        casos = {0: 0, 1999: 0, 2000: 2, 3999: 2, 4000: 5, 9999: 5, 10000: 10}
        for informado, esperado in casos.items():
            self.assertEqual(manual_admin.pontos_jogos(informado), esperado)
        for invalido in (-1, 10001, 2000.5, True):
            with self.assertRaises(ValueError):
                manual_admin.pontos_jogos(invalido)

    def test_historico_valida_hash(self):
        base = ["evento", "2026-11", "#AAA", "1", "JogosCla", "4000", "2", "5", "lider",
                "2026-11-09T12:00:00+00:00", "{}"]
        linhas = [manual_admin.HEADER, base + [manual_admin._hash(base)]]
        historico = manual_admin._historico(linhas)
        self.assertEqual(historico[0]["Depois"], "5")
        linhas[1][-1] = "adulterado"
        with self.assertRaisesRegex(ValueError, "hash divergente"):
            manual_admin._historico(linhas)

    def test_proposta_substitui_sem_somar(self):
        foto = {"contas": [{"tag": "#AAA", "nome": "Alpha", "habilitada": "TRUE",
                              "inscrita": True, "jogos": 5, "eventos": 0}]}
        with patch.object(manual_admin, "montar_manual_admin", return_value=foto):
            proposta = manual_admin.propor_lancamento("ignorado", "#AAA", "JogosCla", 2000)
        self.assertEqual(proposta["antes"], 5)
        self.assertEqual(proposta["depois"], 2)
        self.assertFalse(proposta["inscreveria"])

    def test_bloqueio_e_primeira_pontuacao(self):
        bloqueada = {"contas": [{"tag": "#AAA", "nome": "Alpha", "habilitada": "FALSE",
                                   "inscrita": False, "jogos": 0, "eventos": 0}]}
        with patch.object(manual_admin, "montar_manual_admin", return_value=bloqueada):
            proposta = manual_admin.propor_lancamento("ignorado", "#AAA", "Eventos", 10)
        self.assertEqual(proposta["status"], "BLOQUEADO")

        nova = {"contas": [{"tag": "#BBB", "nome": "Beta", "habilitada": "TRUE",
                              "inscrita": False, "jogos": 0, "eventos": 0}]}
        with patch.object(manual_admin, "montar_manual_admin", return_value=nova):
            zero = manual_admin.propor_lancamento("ignorado", "#BBB", "JogosCla", 1999)
            positiva = manual_admin.propor_lancamento("ignorado", "#BBB", "JogosCla", 2000)
        self.assertEqual(zero["status"], "ZERO_SEM_INSCRICAO")
        self.assertFalse(zero["inscreveria"])
        self.assertTrue(positiva["inscreveria"])


if __name__ == "__main__":
    unittest.main()
