"""Rotas publicas somente leitura para a plataforma independente."""

from __future__ import annotations

import os

from fastapi import HTTPException

from .admin import instalar_rotas_admin
from .conteudo import listar_layouts, obter_torneio
from .ranking_atual import montar_ranking_atual, montar_tabela_detalhada


CAMINHO_PADRAO = "/opt/winning-wars-api/dados_consulta/historico.sqlite3"


def instalar_rotas(app, caminho_sqlite: str | None = None) -> None:
    caminho = caminho_sqlite or os.environ.get("WW_CONSULTA_SQLITE", CAMINHO_PADRAO)
    instalar_rotas_admin(app, caminho)

    @app.get("/v1/ranking")
    def ranking_v1():
        try:
            return montar_ranking_atual(caminho)["ranking"]
        except (OSError, ValueError) as erro:
            raise HTTPException(status_code=503, detail="ranking_atual_indisponivel") from erro

    @app.get("/v1/season")
    def temporada_v1():
        try:
            resultado = montar_ranking_atual(caminho)
        except (OSError, ValueError) as erro:
            raise HTTPException(status_code=503, detail="temporada_atual_indisponivel") from erro
        return {chave: resultado[chave] for chave in (
            "temporada", "temporada_nome", "mes_finalizado", "atualizado_em", "total"
        )}

    @app.get("/v1/ranking/details")
    def tabela_detalhada_v1():
        try:
            return montar_tabela_detalhada(caminho)
        except (OSError, ValueError) as erro:
            raise HTTPException(status_code=503, detail="tabela_detalhada_indisponivel") from erro

    @app.get("/v1/layouts")
    def layouts_v1(tipo: str | None = None, cv: str | None = None,
                   limit: int = 24, offset: int = 0):
        try:
            return listar_layouts(caminho, tipo=tipo, cv=cv,
                                  limite=limit, deslocamento=offset)
        except (OSError, ValueError) as erro:
            raise HTTPException(status_code=503, detail="layouts_indisponiveis") from erro

    @app.get("/v1/tournament")
    def torneio_v1():
        try:
            return obter_torneio(caminho)
        except (OSError, ValueError) as erro:
            raise HTTPException(status_code=503, detail="torneio_indisponivel") from erro

