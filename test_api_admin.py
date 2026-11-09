import hashlib
import os
import time
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from plataforma_api import admin


def hash_pbkdf2(senha, salt=b"0123456789abcdef"):
    digest = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt, 210_000)
    return f"pbkdf2_sha256$210000${salt.hex()}${digest.hex()}"


class AdminApi(unittest.TestCase):
    def setUp(self):
        self.segredo = patch.dict(os.environ, {"WW_ADMIN_SESSION_SECRET": "s" * 48})
        self.segredo.start()
        admin._TENTATIVAS.clear()

    def tearDown(self):
        self.segredo.stop()
        admin._TENTATIVAS.clear()

    def test_senha_pbkdf2_e_legada(self):
        self.assertTrue(admin._verificar_senha("correta", hash_pbkdf2("correta")))
        self.assertFalse(admin._verificar_senha("errada", hash_pbkdf2("correta")))
        legado = hashlib.sha256(b"correta").hexdigest()
        self.assertTrue(admin._verificar_senha("correta", legado))

    def test_token_assinado_e_adulteracao(self):
        token = admin._criar_token("lider", "Dono")
        self.assertEqual(admin._ler_token(token)["usuario"], "lider")
        self.assertIsNone(admin._ler_token(token + "x"))

    def test_segredo_ausente_falha_fechado(self):
        with patch.dict(os.environ, {"WW_ADMIN_SESSION_SECRET": ""}):
            with self.assertRaises(HTTPException) as contexto:
                admin._criar_token("lider", "Dono")
        self.assertEqual(contexto.exception.status_code, 503)

    def test_limite_de_tentativas(self):
        for _ in range(5):
            admin._limitar("127.0.0.1")
        with self.assertRaises(HTTPException) as contexto:
            admin._limitar("127.0.0.1")
        self.assertEqual(contexto.exception.status_code, 429)

    def test_participacao_admin_prevalece(self):
        linhas = [
            ["EventoID", "PlayerTag", "Nome", "Habilitada", "Administrador", "Motivo", "RegistradoEm", "Origem"],
            ["1", "#AAA", "Alpha", "TRUE", "sistema", "cadastro", "2026-11-01T00:00:00+00:00", "CADASTRO"],
            ["2", "#AAA", "Alpha", "FALSE", "lider", "secundaria", "2026-11-02T00:00:00+00:00", "ADMIN"],
            ["3", "#AAA", "Alpha", "TRUE", "sistema", "retorno", "2026-11-03T00:00:00+00:00", "CADASTRO"],
            ["4", "#BBB", "Beta", "TRUE", "sistema", "cadastro", "2026-11-01T00:00:00+00:00", "CADASTRO"],
        ]
        with patch.object(admin, "_linhas_planilha", return_value=linhas):
            resumo = admin._resumo_participacao()
        self.assertEqual(resumo, {"total": 2, "habilitadas": 1, "bloqueadas": 1})


if __name__ == "__main__":
    unittest.main()
