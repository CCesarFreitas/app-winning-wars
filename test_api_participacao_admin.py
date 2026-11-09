import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from plataforma_api.participacao_admin import montar_participacao_admin


class ParticipacaoAdmin(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "historico.sqlite3"
        with sqlite3.connect(self.db) as banco:
            banco.execute("""CREATE TABLE versoes (
                sequencia INTEGER PRIMARY KEY, tipo TEXT, chave TEXT,
                sha256 TEXT, conteudo TEXT, registrado_em TEXT)""")
        self.seq = 0

    def tearDown(self):
        self.tmp.cleanup()

    def guardar(self, tipo, chave, conteudo, em):
        self.seq += 1
        with sqlite3.connect(self.db) as banco:
            banco.execute(
                "INSERT INTO versoes VALUES(?,?,?,?,?,?)",
                (self.seq, tipo, chave, "hash", json.dumps(conteudo), em),
            )

    def fontes(self):
        em = "2026-11-09T12:00:00+00:00"
        self.guardar("fonte", "Página1", [
            ["ID", "Nome", "Guerra_1", "Total"],
            ["1", "Alpha", "3", "3"], ["2", "Beta", "2", "2"],
        ], em)
        self.guardar("fonte", "VinculosParticipantes", [
            ["EventoID", "ParticipanteID", "PlayerTag", "Administrador", "RegistradoEm"],
            ["v1", "1", "#AAA", "sistema", em], ["v2", "2", "#BBB", "sistema", em],
        ], em)
        self.guardar("fonte", "InscricoesTemporada", [
            ["Temporada", "ParticipanteID", "Nome", "PlayerTag", "Status"],
            ["2026-11", "1", "Alpha", "#AAA", "ATIVO"],
            ["2026-11", "2", "Beta", "#BBB", "ATIVO"],
        ], em)
        self.guardar("fonte", "ParticipacaoCompeticao", [
            ["EventoID", "PlayerTag", "Nome", "Habilitada", "Administrador", "Motivo", "RegistradoEm", "Origem"],
            ["p1", "#AAA", "Alpha", "TRUE", "sistema", "Primeira pontuacao", em, "CADASTRO"],
            ["p2", "#BBB", "Beta", "FALSE", "lider", "Conta secundaria", em, "ADMIN"],
        ], em)
        self.guardar("fonte", "EstadoMes", [
            ["Chave", "Valor"], ["temporada_atual_id", "2026-11"],
            ["temporada_atual_nome", "Novembro de 2026"],
        ], em)
        self.guardar("roster", "principal", {
            "consultado_em": "2026-11-08T12:00:00+00:00", "clan": "Vastaya",
            "contas": [{"tag": "#AAA", "nome": "Alpha", "cv": 18},
                       {"tag": "#BBB", "nome": "Beta", "cv": 17}],
        }, "2026-11-08T12:00:00+00:00")
        self.guardar("roster", "principal", {
            "consultado_em": em, "clan": "Vastaya",
            "contas": [{"tag": "#AAA", "nome": "Alpha", "cv": 18, "cargo": "member"}],
        }, em)

    def test_monta_presenca_vinculo_e_decisao(self):
        self.fontes()
        resultado = montar_participacao_admin(self.db)
        contas = {c["tag"]: c for c in resultado["contas"]}
        self.assertTrue(contas["#AAA"]["no_cla"])
        self.assertEqual(contas["#AAA"]["participante_id"], "1")
        self.assertEqual(contas["#AAA"]["cv"], 18)
        self.assertEqual(contas["#BBB"]["situacao"], "AUSENTE_AGORA")
        self.assertEqual(contas["#BBB"]["administrador"], "lider")
        self.assertEqual(contas["#BBB"]["motivo"], "Conta secundaria")
        self.assertEqual(resultado["contagens"]["bloqueadas"], 1)
        self.assertEqual(resultado["contagens"]["no_cla"], 1)

    def test_roster_ausente_falha_fechado(self):
        self.fontes()
        with sqlite3.connect(self.db) as banco:
            banco.execute("DELETE FROM versoes WHERE tipo='roster'")
        with self.assertRaisesRegex(ValueError, "Roster principal ausente"):
            montar_participacao_admin(self.db)


if __name__ == "__main__":
    unittest.main()
