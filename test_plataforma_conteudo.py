import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from plataforma_api.conteudo import listar_layouts, obter_torneio


class ConteudoPublico(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "consulta.sqlite3"
        con = sqlite3.connect(self.db)
        con.execute("""CREATE TABLE versoes (
          sequencia INTEGER PRIMARY KEY, tipo TEXT, chave TEXT,
          sha256 TEXT, conteudo TEXT, registrado_em TEXT)""")
        roster = {"clan": "TorneiosWWars", "tag": "#2CY88CCYU", "consultado_em": "2026-11-01",
                  "contas": [{"tag": "#ABC", "nome": "Jogador", "cv": 16, "cargo": "member"}]}
        con.execute("INSERT INTO versoes VALUES(?,?,?,?,?,?)",
                    (1, "roster", "torneio_oficial", "x", json.dumps(roster), "2026-11-01"))
        con.commit()
        con.close()
        self.layouts = [
            ["Tipo", "CV", "Autor", "Link", "Descricao", "ImagemUrl", "DataHora", "Tag"],
            ["Guerra", "CV 16", "admin", "https://layout/1", "", "https://img/1", "2026-11-01", ""],
            ["Rankeada", "CV 15", "admin", "https://layout/2", "", "", "2026-11-02", ""],
        ]
        torneio = {"nome": "Copa", "status": "EM_ANDAMENTO", "rodadas": []}
        self.torneios = [["TorneioID", "AtualizadoEm", "Admin", "Status", "ConteudoJSON"],
                          ["1", "2026-11-01", "admin", "EM_ANDAMENTO", json.dumps(torneio)]]

    def tearDown(self):
        self.tmp.cleanup()

    def test_filtra_layouts_sem_copia_local(self):
        with patch("plataforma_api.conteudo._linhas_planilha", return_value=self.layouts):
            resposta = listar_layouts(self.db, tipo="Guerra", cv="CV 16")
        self.assertEqual(resposta["total"], 1)
        self.assertEqual(resposta["layouts"][0]["link"], "https://layout/1")

    def test_torneio_da_planilha_e_roster_operacional(self):
        with patch("plataforma_api.conteudo._linhas_planilha", return_value=self.torneios):
            resposta = obter_torneio(self.db)
        self.assertEqual(resposta["torneio"]["nome"], "Copa")
        self.assertEqual(resposta["roster"]["contas"][0],
                         {"tag": "#ABC", "nome": "Jogador", "cv": 16})

    def test_paginacao_e_deduplicacao(self):
        repetidos = self.layouts + [self.layouts[1]]
        with patch("plataforma_api.conteudo._linhas_planilha", return_value=repetidos):
            resposta = listar_layouts(self.db, tipo="Guerra", limite=1, deslocamento=0)
        self.assertEqual(resposta["total"], 1)
        self.assertEqual(len(resposta["layouts"]), 1)


if __name__ == "__main__":
    unittest.main()
