import unittest
from unittest.mock import Mock

from operacao.keepalive_streamlit import verificar


class KeepAliveStreamlit(unittest.TestCase):
    @staticmethod
    def sessao(*respostas):
        sessao = Mock()
        sessao.headers = {}
        sessao.get.side_effect = respostas
        return sessao

    @staticmethod
    def resposta(url, texto="", status=200):
        resposta = Mock()
        resposta.url = url
        resposta.text = texto
        resposta.status_code = status
        resposta.history = []
        resposta.raise_for_status.side_effect = None
        return resposta

    def test_confirma_pagina_aplicacao_e_saude(self):
        base = "https://exemplo.streamlit.app/"
        sessao = self.sessao(
            self.resposta(base),
            self.resposta(base + "~/+/"),
            self.resposta(base + "_stcore/health", "ok"),
        )
        resultado = verificar(base, sessao)
        self.assertEqual(resultado["status"], "STREAMLIT_ATIVO")
        self.assertEqual(sessao.get.call_count, 3)

    def test_login_nao_e_sucesso(self):
        sessao = self.sessao(self.resposta(
            "https://share.streamlit.io/-/auth/app?redirect_uri=x"
        ))
        with self.assertRaisesRegex(RuntimeError, "autenticação"):
            verificar("https://exemplo.streamlit.app/", sessao)

    def test_login_intermediario_nao_e_sucesso(self):
        base = "https://exemplo.streamlit.app/"
        resposta = self.resposta(base)
        resposta.history = [self.resposta(
            "https://share.streamlit.io/-/auth/app?redirect_uri=x"
        )]
        with self.assertRaisesRegex(RuntimeError, "autenticação"):
            verificar(base, self.sessao(resposta))

    def test_saude_precisa_confirmar_processo(self):
        base = "https://exemplo.streamlit.app/"
        sessao = self.sessao(
            self.resposta(base),
            self.resposta(base + "~/+/"),
            self.resposta(base + "_stcore/health", "pagina inesperada"),
        )
        with self.assertRaisesRegex(RuntimeError, "não confirmou"):
            verificar(base, sessao)

    def test_exige_https(self):
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            verificar("http://exemplo.test/", self.sessao())


if __name__ == "__main__":
    unittest.main()
