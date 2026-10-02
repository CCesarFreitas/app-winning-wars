"""Arquivo SQLite de consulta: versões imutáveis, sem escrever no ranking."""
import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path


def serializar(valor):
    return json.dumps(valor, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


class Arquivo:
    def __init__(self, caminho):
        self.caminho = Path(caminho)
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.caminho, timeout=30)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS versoes (
                sequencia INTEGER PRIMARY KEY, tipo TEXT NOT NULL,
                chave TEXT NOT NULL, sha256 TEXT NOT NULL, conteudo TEXT NOT NULL,
                registrado_em TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS por_chave ON versoes(tipo,chave,sequencia);
        ''')

    def guardar(self, tipo, chave, valor, agora):
        texto = serializar(valor)
        resumo = hashlib.sha256(texto.encode()).hexdigest()
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            ultimo = self.db.execute('SELECT sha256 FROM versoes WHERE tipo=? AND chave=? ORDER BY sequencia DESC LIMIT 1',
                                     (tipo, chave)).fetchone()
            if ultimo != (resumo,):
                self.db.execute('INSERT INTO versoes(tipo,chave,sha256,conteudo,registrado_em) VALUES(?,?,?,?,?)',
                                (tipo, chave, resumo, texto, agora))
        return resumo

    def ultimos(self, tipo):
        return {k: json.loads(v) for k, v in self.db.execute('''
            SELECT chave,conteudo FROM versoes WHERE sequencia IN
            (SELECT MAX(sequencia) FROM versoes WHERE tipo=? GROUP BY chave)
        ''', (tipo,))}

    def backup(self, destino):
        with closing(sqlite3.connect(destino)) as copia:
            self.db.backup(copia)
            if copia.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Backup do histórico inconsistente')

    def close(self):
        self.db.close()


def empacotar(documentos):
    linhas = [['Chave', 'Parte', 'JSON']]
    for chave, valor in sorted(documentos.items()):
        texto = serializar(valor)
        for indice, inicio in enumerate(range(0, len(texto), 15000)):
            linhas.append([chave, str(indice), texto[inicio:inicio+15000]])
    return linhas


def desempacotar(linhas):
    if not linhas or linhas[0] != ['Chave', 'Parte', 'JSON']:
        raise ValueError('Publicação indisponível')
    grupos = {}
    for linha in linhas[1:]:
        if not any(linha):
            continue
        if len(linha) != 3:
            raise ValueError('Publicação incompleta')
        chave, indice, texto = linha
        grupo = grupos.setdefault(chave, {})
        indice = int(indice)
        if indice in grupo or indice < 0:
            raise ValueError('Publicação duplicada')
        grupo[indice] = texto
    saida = {}
    for chave, partes in grupos.items():
        if sorted(partes) != list(range(len(partes))):
            raise ValueError('Parte ausente')
        saida[chave] = json.loads(''.join(partes[i] for i in range(len(partes))))
    return saida
