import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from plataforma_api.ranking_atual import montar_ranking_atual, montar_tabela_detalhada


class RankingAtual(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.banco = Path(self.tmp.name) / "historico.sqlite3"
        db = sqlite3.connect(self.banco)
        db.execute(
            """CREATE TABLE versoes (
            sequencia INTEGER PRIMARY KEY, tipo TEXT, chave TEXT,
            sha256 TEXT, conteudo TEXT, registrado_em TEXT)"""
        )
        fontes = {
            "Página1": [
                ["ID", "Nome", "JogosCla", "Eventos", "Guerra_1", "Raide_1", "Liga_1"],
                ["1", "Alpha", "5", "1", "3", "7", "2"],
                ["2", "Beta", "10", "0", "0", "6", "3"],
                ["3", "Sem vinculo", "2", "0", "0", "0", "0"],
            ],
            "EstadoMes": [
                ["Chave", "Valor"],
                ["temporada_atual_id", "2026-11"],
                ["temporada_atual_nome", "novembro/2026"],
                ["mes_finalizado", "FALSE"],
            ],
            "VinculosParticipantes": [
                ["EventoID", "ParticipanteID", "PlayerTag", "Administrador", "RegistradoEm"],
                ["v1", "1", "#AAA", "motor", "2026-11-01T00:00:00+00:00"],
                ["v2", "2", "#BBB", "motor", "2026-11-01T00:00:00+00:00"],
            ],
            "ParticipacaoCompeticao": [
                ["EventoID", "PlayerTag", "Nome", "Habilitada", "Administrador", "Motivo", "RegistradoEm", "Origem"],
                ["p1", "#AAA", "Alpha", "TRUE", "motor", "cadastro", "2026-11-01T00:00:00+00:00", "CADASTRO"],
                ["p2", "#BBB", "Beta", "TRUE", "motor", "cadastro", "2026-11-01T00:00:00+00:00", "CADASTRO"],
                ["p3", "#BBB", "Beta", "FALSE", "admin", "secundaria", "2026-11-02T00:00:00+00:00", "ADMIN"],
                ["p4", "#BBB", "Beta", "TRUE", "motor", "novo cadastro", "2026-11-03T00:00:00+00:00", "CADASTRO"],
            ],
        }
        for indice, (chave, valor) in enumerate(fontes.items(), 1):
            db.execute(
                "INSERT INTO versoes VALUES(?,?,?,?,?,?)",
                (indice, "fonte", chave, "sha", json.dumps(valor), f"2026-11-08T00:0{indice}:00+00:00"),
            )
        db.execute(
            "INSERT INTO versoes VALUES(?,?,?,?,?,?)",
            (10, "roster", "principal", "sha", json.dumps({
                "contas": [{"tag": "#AAA", "nome": "Alpha", "cv": 16}]
            }), "2026-11-08T01:00:00+00:00"),
        )
        db.commit()
        db.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_soma_modalidades_e_oculta_bloqueio_admin(self):
        saida = montar_ranking_atual(self.banco)
        self.assertEqual(saida["temporada"], "2026-11")
        self.assertEqual(saida["total"], 2)
        self.assertEqual([r["nome"] for r in saida["ranking"]], ["Alpha", "Sem vinculo"])
        self.assertEqual(saida["ranking"][0]["guerra"], 5)
        self.assertEqual(saida["ranking"][0]["raides"], 7)
        self.assertEqual(saida["ranking"][0]["total"], 18)
        self.assertEqual(saida["ranking"][0]["cv"], 16)
        self.assertIsNone(saida["ranking"][1]["cv"])

    def test_fonte_inexistente_falha_fechado(self):
        db = sqlite3.connect(self.banco)
        db.execute("DELETE FROM versoes WHERE chave='Página1'")
        db.commit()
        db.close()
        with self.assertRaisesRegex(ValueError, "Fonte ausente"):
            montar_ranking_atual(self.banco)

    def test_tabela_detalhada_preserva_colunas_e_bloqueios(self):
        saida = montar_tabela_detalhada(self.banco)
        self.assertEqual(
            [coluna["chave"] for coluna in saida["colunas"]],
            ["JogosCla", "Eventos", "Guerra_1", "Raide_1", "Liga_1"],
        )
        self.assertEqual([jogador["nome"] for jogador in saida["jogadores"]], ["Alpha", "Sem vinculo"])
        alpha = saida["jogadores"][0]
        self.assertEqual(alpha["pontos"]["Guerra_1"], 3)
        self.assertEqual(alpha["pontos"]["Liga_1"], 2)
        self.assertEqual(alpha["total"], 18)
        self.assertEqual(saida["total"], 2)


if __name__ == "__main__":
    unittest.main()
