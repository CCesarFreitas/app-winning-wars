"""Executado pelo observador, com tempo máximo controlado pelo processo pai."""
import sys
from pathlib import Path
from datetime import datetime, timezone

BASE = Path('/opt/winning-wars-api')
sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(BASE)]
from ww_competicao.armazenamento import Arquivo
from ww_competicao.planejamento_dados import coletar, validar_guerra
from supercell import supercell_get
import json


def executar():
    a = Arquivo(BASE / 'dados_consulta/historico.sqlite3')
    # Semeia o arquivo com capturas reais existentes, sem importar pontos nem executar motores.
    existentes = a.ultimos('planejamento_guerra')
    candidatos = {}
    for f in (BASE / 'oracle_producao_outubro/capturas_guerra').rglob('*.json'):
        try:
            d = json.loads(f.read_text())
            g = d.get('guerra', {})
            if g.get('state') != 'warEnded':
                continue
            validar_guerra(g)
            chave = 'comum:' + g['startTime'] + ':' + g['clan']['tag'] + ':' + g['opponent']['tag']
            if chave in existentes:
                continue
            stamp = d.get('arquivado_em') or datetime.fromtimestamp(f.stat().st_mtime, timezone.utc).isoformat()
            if chave not in candidatos or stamp > candidatos[chave]['consultado_em']:
                candidatos[chave] = {'dados': g, 'tipo': 'comum', 'consultado_em': stamp}
        except (ValueError, KeyError, TypeError):
            continue
    for chave, valor in candidatos.items():
        a.guardar('planejamento_guerra', chave, valor, valor['consultado_em'])
    try:
        d = coletar(a, supercell_get)
        print('Planejamento consultado:', len(d['guerras_liga']), 'guerras; pendências:', len(d['pendencias']))
    finally:
        a.close()


if __name__ == '__main__':
    executar()
