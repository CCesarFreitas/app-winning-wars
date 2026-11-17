"""Retenção segura do histórico local de consultas.

Não toca na planilha, não recalcula pontos e nunca remove ``atividade``,
``revisao`` ou ``fonte``. Remove apenas projeções técnicas redundantes, depois
de criar uma cópia SQLite consistente no volume secundário.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:  # A Oracle usa flock; o fallback permite validar a regra no Windows.
    import fcntl
except ModuleNotFoundError:  # pragma: no cover - ambiente local de desenvolvimento
    fcntl = None


BANCO = Path('/opt/winning-wars-api/dados_consulta/historico.sqlite3')
BACKUPS = Path('/var/oled/winning-wars-backups')
TIPOS_ESTADO = ('planejamento', 'planejamento_cache', 'saude')
TIPOS_FOTOGRAFIA = ('planejamento_guerra', 'planejamento_grupo', 'roster')


def _bytes_banco(caminho: Path) -> int:
    return sum(p.stat().st_size for p in (caminho, Path(str(caminho) + '-wal'), Path(str(caminho) + '-shm')) if p.exists())


def _hash(caminho: Path, compactado: bool = False) -> str:
    digest = hashlib.sha256()
    abertura = gzip.open if compactado else Path.open
    with abertura(caminho, 'rb') as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b''):
            digest.update(bloco)
    return digest.hexdigest()


def _resumo(db: sqlite3.Connection) -> dict[str, int]:
    return {tipo: quantidade for tipo, quantidade in db.execute(
        'SELECT tipo,COUNT(*) FROM versoes GROUP BY tipo ORDER BY tipo'
    )}


def _prever_exclusoes(db: sqlite3.Connection, corte: str) -> dict[str, int]:
    estado = db.execute(
        """SELECT COUNT(*) FROM versoes AS v
           WHERE v.tipo IN ('planejamento','planejamento_cache','saude')
             AND EXISTS (SELECT 1 FROM estados_operacionais e
                         WHERE e.tipo=v.tipo AND e.chave=v.chave)"""
    ).fetchone()[0]
    fotografia = db.execute(
        """WITH classificadas AS (
             SELECT sequencia,registrado_em,
               ROW_NUMBER() OVER (PARTITION BY tipo,chave ORDER BY sequencia DESC) AS ultima,
               ROW_NUMBER() OVER (PARTITION BY tipo,chave,substr(registrado_em,1,10)
                                  ORDER BY sequencia DESC) AS diaria
             FROM versoes
             WHERE tipo IN ('planejamento_guerra','planejamento_grupo','roster')
           )
           SELECT COUNT(*) FROM classificadas
           WHERE ultima > 1 AND (registrado_em < ? OR diaria > 1)""",
        (corte,),
    ).fetchone()[0]
    return {'estados_operacionais_antigos': estado, 'fotografias_redundantes': fotografia,
            'total': estado + fotografia}


def verificar(caminho: Path = BANCO, dias: int = 30) -> dict[str, object]:
    agora = datetime.now(timezone.utc)
    corte = (agora - timedelta(days=dias)).isoformat()
    with closing(sqlite3.connect(caminho)) as db:
        return {
            'banco': str(caminho),
            'bytes_ativos': _bytes_banco(caminho),
            'integridade': db.execute('PRAGMA integrity_check').fetchone()[0],
            'versoes_por_tipo': _resumo(db),
            'corte_fotografias': corte,
            'exclusoes_planejadas': _prever_exclusoes(db, corte),
        }


def _backup_previo(origem: Path, destino: Path) -> tuple[Path, str]:
    destino.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporario = destino.with_suffix('.sqlite3')
    compactado = destino.with_suffix('.sqlite3.gz')
    with closing(sqlite3.connect(origem.as_uri() + '?mode=ro', uri=True)) as leitura:
        with closing(sqlite3.connect(temporario)) as copia:
            # A trava de publicação já garante que não há escritor concorrente.
            # Blocos grandes evitam manter uma manutenção de alguns GiB ativa
            # por dezenas de minutos em uma VM Always Free.
            leitura.backup(copia, pages=8192, sleep=.005)
            if copia.execute('PRAGMA integrity_check').fetchone() != ('ok',):
                raise RuntimeError('Backup SQLite inconsistente')
    assinatura = _hash(temporario)
    with compactado.open('xb') as bruto:
        with gzip.GzipFile(fileobj=bruto, mode='wb', compresslevel=1, mtime=0) as saida, temporario.open('rb') as entrada:
            shutil.copyfileobj(entrada, saida, length=1024 * 1024)
        bruto.flush()
        os.fsync(bruto.fileno())
    temporario.unlink()
    if _hash(compactado, compactado=True) != assinatura:
        compactado.unlink(missing_ok=True)
        raise RuntimeError('Hash do backup prévio divergente')
    compactado.with_suffix('.gz.sha256').write_text(assinatura + '\n', encoding='ascii')
    return compactado, assinatura


def aplicar(caminho: Path = BANCO, backups: Path = BACKUPS, dias: int = 30) -> dict[str, object]:
    if dias < 7:
        raise ValueError('A retenção de fotografias não pode ser menor que sete dias')
    if shutil.disk_usage(caminho.parent).free < 5 * 1024 ** 3:
        raise RuntimeError('Espaço livre insuficiente para compactar o banco com segurança')
    agora = datetime.now(timezone.utc)
    corte = (agora - timedelta(days=dias)).isoformat()
    lock_path = caminho.parent / 'publicacao.lock'
    with lock_path.open('a') as trava:
        if fcntl is not None:
            fcntl.flock(trava, fcntl.LOCK_EX)
        antes = verificar(caminho, dias)
        if antes['integridade'] != 'ok':
            raise RuntimeError('Banco inconsistente; retenção cancelada')
        selo = agora.strftime('%Y%m%dT%H%M%SZ')
        copia, assinatura = _backup_previo(caminho, backups / f'pre_retencao_{selo}')
        with closing(sqlite3.connect(caminho, timeout=60)) as db:
            db.execute('PRAGMA busy_timeout=60000')
            db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            with db:
                db.execute("""DELETE FROM versoes AS v
                    WHERE v.tipo IN ('planejamento','planejamento_cache','saude')
                      AND EXISTS (SELECT 1 FROM estados_operacionais e
                                  WHERE e.tipo=v.tipo AND e.chave=v.chave)""")
                db.execute("""WITH classificadas AS (
                    SELECT sequencia,registrado_em,
                      ROW_NUMBER() OVER (PARTITION BY tipo,chave ORDER BY sequencia DESC) AS ultima,
                      ROW_NUMBER() OVER (PARTITION BY tipo,chave,substr(registrado_em,1,10)
                                         ORDER BY sequencia DESC) AS diaria
                    FROM versoes
                    WHERE tipo IN ('planejamento_guerra','planejamento_grupo','roster')
                  )
                  DELETE FROM versoes WHERE sequencia IN (
                    SELECT sequencia FROM classificadas
                    WHERE ultima > 1 AND (registrado_em < ? OR diaria > 1)
                  )""", (corte,))
            db.execute('VACUUM')
            if db.execute('PRAGMA integrity_check').fetchone() != ('ok',):
                raise RuntimeError('Compactação inconsistente; backup prévio preservado')
        depois = verificar(caminho, dias)
        registro = {
            'executado_em': agora.isoformat(), 'dias_fotografias': dias,
            'antes_bytes': antes['bytes_ativos'], 'depois_bytes': depois['bytes_ativos'],
            'removidos': antes['exclusoes_planejadas'],
            'backup': str(copia), 'backup_sha256': assinatura,
        }
        with (backups / 'retencao_historico.jsonl').open('a', encoding='utf-8') as log:
            log.write(json.dumps(registro, ensure_ascii=False) + '\n')
            log.flush(); os.fsync(log.fileno())
        return registro


def main() -> None:
    parser = argparse.ArgumentParser(description='Retenção segura do SQLite de consultas Winning Wars')
    parser.add_argument('--aplicar', action='store_true', help='executa após backup e conferência')
    parser.add_argument('--dias', type=int, default=30, help='dias de fotografias diárias a preservar')
    parser.add_argument('--banco', type=Path, default=BANCO)
    parser.add_argument('--backups', type=Path, default=BACKUPS)
    args = parser.parse_args()
    resposta = aplicar(args.banco, args.backups, args.dias) if args.aplicar else verificar(args.banco, args.dias)
    print(json.dumps(resposta, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
