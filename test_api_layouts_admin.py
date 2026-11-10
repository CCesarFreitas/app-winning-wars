import base64
import unittest
from unittest.mock import patch

from plataforma_api.operacoes_admin import (
    LayoutDuplicadoError, excluir_layout, preparar_layouts_lote, publicar_layouts,
)


class _Aba:
    def __init__(self, linhas):
        self.linhas = [list(linha) for linha in linhas]

    def get_all_values(self, **_kwargs):
        return [list(linha) for linha in self.linhas]

    def append_rows(self, linhas, **_kwargs):
        self.linhas.extend([list(linha) for linha in linhas])

    def delete_rows(self, numero_linha):
        del self.linhas[numero_linha - 1]


class _Planilha:
    def __init__(self):
        self.abas = {
            "Layouts": _Aba([["Tipo", "CV", "Autor", "Link", "Descricao", "ImagemUrl", "DataHora"]]),
            "Logs": _Aba([["DataHora", "Admin", "Acao"]]),
        }

    def worksheet(self, nome):
        return self.abas[nome]


class LayoutsAdmin(unittest.TestCase):
    def test_prepara_lote_mantendo_ordem_e_webp(self):
        webp = b"RIFF" + (8).to_bytes(4, "little") + b"WEBP" + b"1234"
        itens = preparar_layouts_lote("Caio", "Guerra", 18, [{
            "link": "https://link.clashofclans.com/pt?action=OpenLayout&id=TH18-ABC",
            "descricao": "Anti-3", "imagem_base64": base64.b64encode(webp).decode(),
            "imagem_url": "",
        }], "2026-11-10T00:00:00+00:00")
        self.assertEqual(itens[0]["CV"], "CV 18")
        self.assertEqual(itens[0]["Autor"], "Caio")
        self.assertEqual(itens[0]["imagem"], webp)

    def test_rejeita_link_nao_oficial(self):
        with self.assertRaisesRegex(ValueError, "link oficial"):
            preparar_layouts_lote("Caio", "Guerra", 18, [{
                "link": "https://exemplo.com/layout", "descricao": "",
                "imagem_base64": "", "imagem_url": "",
            }], "2026-11-10T00:00:00+00:00")

    def test_rejeita_duplicado_no_lote(self):
        link = "https://link.clashofclans.com/pt?action=OpenLayout&id=TH18-ABC"
        with self.assertRaisesRegex(ValueError, "repetido"):
            preparar_layouts_lote("Caio", "Rankeada", 17, [
                {"link": link}, {"link": link},
            ], "2026-11-10T00:00:00+00:00")

    def test_rejeita_lote_de_imagens_acima_do_limite(self):
        webp = b"RIFF" + (8).to_bytes(4, "little") + b"WEBP" + (b"x" * 1_300_000)
        imagem = base64.b64encode(webp).decode()
        with self.assertRaisesRegex(ValueError, "excedem 24 MB"):
            preparar_layouts_lote("Caio", "Guerra", 18, [{
                "link": f"https://link.clashofclans.com/pt?action=OpenLayout&id=TH18-{indice}",
                "imagem_base64": imagem,
            } for indice in range(19)], "2026-11-10T00:00:00+00:00")

    def test_publica_no_cabecalho_oficial_sem_tag(self):
        planilha = _Planilha()
        with patch("plataforma_api.operacoes_admin._planilha_escrita", return_value=planilha), \
             patch("plataforma_api.operacoes_admin._backup", return_value="backup.json"), \
             patch("plataforma_api.operacoes_admin.invalidar_conteudo"):
            resultado = publicar_layouts("Caio", "Guerra", 18, [{
                "link": "https://link.clashofclans.com/pt?action=OpenLayout&id=TH18-OFICIAL",
                "descricao": "Teste",
            }])
        self.assertEqual(resultado["status"], "APLICADO_E_CONFERIDO")
        self.assertEqual(len(planilha.abas["Layouts"].linhas), 2)
        self.assertEqual(len(planilha.abas["Layouts"].linhas[1]), 7)

    def test_informa_todos_os_layouts_ja_publicados(self):
        primeiro = "https://link.clashofclans.com/pt?action=OpenLayout&id=TH18-PRIMEIRO"
        terceiro = "https://link.clashofclans.com/pt?action=OpenLayout&id=TH18-TERCEIRO"
        planilha = _Planilha()
        planilha.abas["Layouts"].linhas.extend([
            ["Guerra", "CV 18", "Godoy", primeiro, "", "https://img/1", "2026-11-01"],
            ["Rankeada", "CV 17", "Caio", terceiro, "", "https://img/3", "2026-11-02"],
        ])
        with patch("plataforma_api.operacoes_admin._planilha_escrita", return_value=planilha):
            with self.assertRaises(LayoutDuplicadoError) as contexto:
                publicar_layouts("Caio", "Guerra", 18, [
                    {"link": primeiro},
                    {"link": "https://link.clashofclans.com/pt?action=OpenLayout&id=TH18-NOVO"},
                    {"link": terceiro},
                ])
        self.assertEqual([item["linha_lote"] for item in contexto.exception.duplicados], [1, 3])
        self.assertEqual(contexto.exception.duplicados[0]["autor"], "Godoy")
        self.assertEqual(contexto.exception.duplicados[1]["cv"], "CV 17")

    def test_exclusao_remove_todas_as_linhas_do_link_e_confere(self):
        link = "https://link.clashofclans.com/pt?action=OpenLayout&id=TH18-REPETIDO"
        planilha = _Planilha()
        linha = ["Guerra", "CV 18", "Godoy", link, "", "https://img/1", "2026-11-01"]
        planilha.abas["Layouts"].linhas.extend([linha, list(linha)])
        with patch("plataforma_api.operacoes_admin._planilha_escrita", return_value=planilha), \
             patch("plataforma_api.operacoes_admin._backup", return_value="backup.json"), \
             patch("plataforma_api.operacoes_admin.invalidar_conteudo"):
            resultado = excluir_layout("Caio", link, "Guerra", 18)
        self.assertEqual(resultado["status"], "REMOVIDO_E_CONFERIDO")
        self.assertEqual(resultado["removidos"], 2)
        self.assertTrue(resultado["imagem_externa_preservada"])
        self.assertEqual(len(planilha.abas["Layouts"].linhas), 1)
        self.assertEqual(len(planilha.abas["Logs"].linhas), 2)


if __name__ == "__main__":
    unittest.main()
