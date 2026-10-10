import random
import unittest

from ww_competicao.torneios import (criar_torneio, partidas_pendentes,
                                    selecionar_vencedor, validar_roster, html_chaveamento)


def jogadores(qtd, cv=16):
    return [{"tag": "#P" + "Y" * indice + "2", "nome": f"Jogador {indice}", "cv": cv}
            for indice in range(1, qtd + 1)]


class Torneios(unittest.TestCase):
    def test_roster_publico_validado(self):
        doc = {"modo": "PROVA_DE_CONCEITO", "tag": "#2YPL9GU8Y", "clan": "Vastaya",
               "contas": [{"tag": "#P2Y", "nome": "A", "cv": 16},
                           {"tag": "#P8Y", "nome": "B", "cv": 16}]}
        self.assertEqual(len(validar_roster(doc)), 2)
        doc["contas"][1]["tag"] = "#P2Y"
        with self.assertRaises(ValueError):
            validar_roster(doc)

    def test_sorteio_folga_e_avanco_ate_final(self):
        torneio = criar_torneio("Copa teste", jogadores(5), 16, random.Random(7),
                                "2026-10-10T12:00:00+00:00")
        self.assertEqual(torneio["tamanho_chave"], 8)
        self.assertEqual(len(torneio["rodadas"]), 3)
        self.assertEqual(sum(p["automatico"] for p in torneio["rodadas"][0]), 3)
        while torneio["status"] == "EM_ANDAMENTO":
            ri, mi, partida = partidas_pendentes(torneio)[0]
            torneio = selecionar_vencedor(torneio, ri, mi, partida["jogadores"][0]["tag"])
        self.assertIsNotNone(torneio["campeao"])
        self.assertIn("CAMPEÃO", html_chaveamento(torneio))

    def test_vencedor_invalido_e_cv_divergente(self):
        with self.assertRaises(ValueError):
            criar_torneio("Teste", jogadores(2, 15), 16, random.Random(1))
        torneio = criar_torneio("Teste", jogadores(2), 16, random.Random(1))
        with self.assertRaises(ValueError):
            selecionar_vencedor(torneio, 0, 0, "#Q2Y")


if __name__ == "__main__":
    unittest.main()
