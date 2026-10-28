"""Ícones empacotados com o app: sem dependência de hospedagem externa."""
import base64
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=10)
def imagem_cv(cv):
    if type(cv) is not int or cv not in range(9,19):
        raise ValueError('Centro de Vila sem imagem cadastrada')
    arquivo=Path(__file__).resolve().parent.parent/'static'/'centros_vila'/f'cv{cv}.webp'
    return 'data:image/webp;base64,'+base64.b64encode(arquivo.read_bytes()).decode('ascii')
