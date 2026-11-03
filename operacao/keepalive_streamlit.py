#!/usr/bin/env python3
"""Verifica e acessa o Streamlit a partir da Oracle.

Este monitor HTTP complementa a visita com navegador feita pelo GitHub Actions.
Ele falha explicitamente se o endereço terminar na autenticação do Community
Cloud, evitando que uma página de login seja confundida com o app ativo.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests


APP_URL = os.environ.get(
    "WW_STREAMLIT_URL",
    "https://app-winning-wars-jwjuzibnwyejvqmcwyvge8.streamlit.app/",
).strip()
TIMEOUT = int(os.environ.get("WW_STREAMLIT_TIMEOUT", "45"))


def _bloqueado_por_autenticacao(url: str) -> bool:
    destino = url.lower()
    return "share.streamlit.io/-/auth/" in destino or "/-/login" in destino


def verificar(url: str = APP_URL, session=None) -> dict:
    if not url.startswith("https://"):
        raise ValueError("WW_STREAMLIT_URL deve usar HTTPS")

    cliente = session or requests.Session()
    cliente.headers.update({
        "User-Agent": "WinningWars-Streamlit-KeepAlive/1.0",
        "Cache-Control": "no-cache",
    })

    alvos = {
        "pagina": url,
        "aplicacao": urljoin(url, "~/+/"),
        # O Community Cloud hospeda o processo real dentro de /~/+/.
        # O endereço /_stcore/health na raiz retorna apenas o shell externo.
        "saude": urljoin(url, "~/+/_stcore/health"),
    }
    resultados = {}
    for nome, alvo in alvos.items():
        resposta = cliente.get(alvo, timeout=TIMEOUT, allow_redirects=True)
        final = resposta.url
        cadeia_redirecionamentos = [
            item.url for item in getattr(resposta, "history", [])
        ] + [final]
        resultados[nome] = {
            "status": resposta.status_code,
            "url_final": final,
            # Não registrar URLs intermediárias: a sessão anônima do Streamlit
            # inclui um token temporário no endereço de retorno.
            "quantidade_redirecionamentos": len(cadeia_redirecionamentos) - 1,
        }
        # Apps públicos também passam por /auth/app para receber uma sessão
        # anônima. Só é bloqueio quando o destino final permanece em login.
        if _bloqueado_por_autenticacao(final):
            raise RuntimeError(
                f"{nome}: autenticação do Streamlit impediu o acesso ao app"
            )
        resposta.raise_for_status()

    corpo_saude = resposta.text.strip().lower()
    if corpo_saude not in {"ok", "healthy"}:
        raise RuntimeError(
            f"endpoint de saúde não confirmou o processo: {corpo_saude[:120]!r}"
        )

    return {
        "status": "STREAMLIT_ATIVO",
        "verificado_em": datetime.now(timezone.utc).isoformat(),
        "alvos": resultados,
    }


def main() -> int:
    try:
        resultado = verificar()
    except Exception as exc:
        print(json.dumps({
            "status": "FALHA_KEEPALIVE",
            "erro": str(exc),
            "verificado_em": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False))
        return 1
    print(json.dumps(resultado, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
