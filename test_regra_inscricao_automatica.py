import unittest

from ww_competicao.participacao_competicao import PC_CABECALHO, pc_estado, pc_ler_eventos
from ww_competicao.planejar_inscricao_automatica import IA_HEADER, planejar_inscricoes
from ww_competicao.vinculos_competicao import VC_HEADER


DATA = "2026-10-04T18:00:00-03:00"
TAG = "#Q2UCGPGY"


class RegraParticipacaoAutomatica(unittest.TestCase):
    def fontes(self, eventos=()):
        return (
            [["ID", "Nome", "Liga_1"]],
            [IA_HEADER],
            [VC_HEADER],
            [PC_CABECALHO, *eventos],
        )

    def planejar(self, eventos=(), pontos=3):
        return planejar_inscricoes(
            "2026-10",
            [{"player_tag": TAG, "nome": "GODOY", "pontos": pontos}],
            *self.fontes(eventos),
            DATA,
        )

    def test_false_de_cadastro_nao_bloqueia_primeira_pontuacao(self):
        antigo = ["migracao", TAG, "GODOY", "FALSE", "migracao_oracle",
                  "Cadastro inicial", "2026-09-27T00:00:00-03:00", "CADASTRO"]
        plano = self.planejar([antigo])
        self.assertEqual([p["player_tag"] for p in plano["participantes"]], [TAG])
        self.assertEqual(len(plano["novos_eventos_participacao"]), 1)
        self.assertEqual(plano["novos_eventos_participacao"][0][3:4], ["TRUE"])
        estado = pc_estado(pc_ler_eventos(plano["controle_virtual"]))
        self.assertEqual(estado[TAG]["Habilitada"], "TRUE")
        self.assertEqual(estado[TAG]["Origem"], "CADASTRO")

    def test_false_do_admin_continua_bloqueando(self):
        antigo = ["migracao", TAG, "GODOY", "FALSE", "migracao_oracle",
                  "Cadastro inicial", "2026-09-27T00:00:00-03:00", "CADASTRO"]
        bloqueio = ["admin", TAG, "GODOY", "FALSE", "dono",
                    "Conta secundaria", "2026-10-01T00:00:00-03:00", "ADMIN"]
        plano = self.planejar([antigo, bloqueio])
        self.assertEqual(plano["participantes"], [])
        self.assertEqual(plano["excluidos"], [{"tag": TAG, "motivo": "bloqueio_administrativo"}])

    def test_admin_nao_e_sobrescrito_por_cadastro_posterior(self):
        admin = ["admin", TAG, "GODOY", "TRUE", "dono",
                 "Habilitada", "2026-10-01T00:00:00-03:00", "ADMIN"]
        cadastro = ["cadastro", TAG, "GODOY", "FALSE", "importacao",
                    "Carga tardia", "2026-10-02T00:00:00-03:00", "CADASTRO"]
        estado = pc_estado(pc_ler_eventos([PC_CABECALHO, admin, cadastro]))
        self.assertEqual(estado[TAG]["EventoID"], "admin")
        self.assertEqual(estado[TAG]["Habilitada"], "TRUE")


if __name__ == "__main__":
    unittest.main()
