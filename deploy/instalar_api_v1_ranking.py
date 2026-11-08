"""Instala, com backup, as rotas GET da plataforma independente na API legada."""

from __future__ import annotations

import argparse
import ast
import json
import shutil
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


RAIZ = Path("/opt/winning-wars-api")
APP = RAIZ / "app.py"
DESTINO = RAIZ / "plataforma_api"
ORIGEM = Path(__file__).resolve().parent / "plataforma_api"
BACKUPS = RAIZ / "backups_plataforma_independente"
MARCADOR = "# Winning Wars plataforma independente: API v1 somente leitura"
GANCHO = (
    f"\n\n{MARCADOR}\n"
    "from plataforma_api.router import instalar_rotas as instalar_rotas_plataforma\n"
    "instalar_rotas_plataforma(app)\n"
)


def validar_fontes() -> None:
    if RAIZ.resolve() != Path("/opt/winning-wars-api"):
        raise RuntimeError("Destino inesperado")
    if not APP.is_file() or not ORIGEM.is_dir():
        raise FileNotFoundError("Aplicacao ou pacote de origem ausente")
    for nome in ("__init__.py", "ranking_atual.py", "router.py"):
        texto = (ORIGEM / nome).read_text(encoding="utf-8")
        ast.parse(texto, filename=nome)


def instalar() -> Path:
    validar_fontes()
    instante = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = BACKUPS / f"antes_api_v1_{instante}"
    backup.mkdir(parents=True, mode=0o700)
    shutil.copy2(APP, backup / "app.py")
    if DESTINO.exists():
        shutil.copytree(DESTINO, backup / "plataforma_api")

    temporario = RAIZ / ".plataforma_api.novo"
    if temporario.exists():
        shutil.rmtree(temporario)
    shutil.copytree(ORIGEM, temporario)
    if DESTINO.exists():
        shutil.rmtree(DESTINO)
    temporario.replace(DESTINO)

    texto = APP.read_text(encoding="utf-8")
    if MARCADOR not in texto:
        texto += GANCHO
        ast.parse(texto, filename=str(APP))
        app_novo = APP.with_suffix(".py.novo")
        app_novo.write_text(texto, encoding="utf-8")
        app_novo.replace(APP)
    return backup


def restaurar(backup: Path) -> None:
    shutil.copy2(backup / "app.py", APP)
    if DESTINO.exists():
        shutil.rmtree(DESTINO)
    pacote_anterior = backup / "plataforma_api"
    if pacote_anterior.exists():
        shutil.copytree(pacote_anterior, DESTINO)


def reiniciar_e_conferir() -> dict:
    subprocess.run(
        ["sudo", "systemctl", "restart", "winning-wars-api.service"],
        check=True,
        timeout=40,
    )
    ultimo_erro: Exception | None = None
    for _ in range(20):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=3) as resposta:
                saude = json.load(resposta)
            with urllib.request.urlopen("http://127.0.0.1:8000/v1/ranking", timeout=8) as resposta:
                ranking = json.load(resposta)
            if saude.get("status") != "ok" or not isinstance(ranking, list):
                raise ValueError("Resposta de conferencia invalida")
            if ranking and any(not r.get("temporada") or not r.get("tag") for r in ranking):
                raise ValueError("Ranking sem temporada ou tag")
            return {"jogadores": len(ranking), "temporada": ranking[0]["temporada"] if ranking else None}
        except Exception as erro:
            ultimo_erro = erro
            time.sleep(1)
    raise RuntimeError("API nao respondeu corretamente apos a instalacao") from ultimo_erro


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aplicar", action="store_true")
    args = parser.parse_args()
    validar_fontes()
    if not args.aplicar:
        print("OK: fontes validas; nenhuma alteracao realizada")
        return
    backup = instalar()
    try:
        conferencia = reiniciar_e_conferir()
    except Exception:
        restaurar(backup)
        subprocess.run(
            ["sudo", "systemctl", "restart", "winning-wars-api.service"],
            check=False,
            timeout=40,
        )
        raise
    print(f"INSTALADO_E_CONFERIDO: {backup} {json.dumps(conferencia, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
