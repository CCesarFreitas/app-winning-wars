import unittest, tempfile, json, sqlite3, gc
from pathlib import Path
from datetime import date
from ww_competicao.armazenamento import Arquivo
from operacao.backup_historico import selecionar_reter
from operacao.manutencao_historico import verificar, aplicar

class Testes(unittest.TestCase):
    def test_estado_nao_acumula_e_historico_permanece(self):
        with tempfile.TemporaryDirectory() as td:
            a=Arquivo(Path(td)/'a.sqlite3')
            a.db.execute("INSERT INTO versoes(tipo,chave,sha256,conteudo,registrado_em) VALUES('planejamento','atual','antigo','{}','2026-10-01')")
            a.db.commit()
            for i in range(100):
                a.guardar('planejamento','atual',{'publicado_em':str(i)},str(i))
                a.guardar('planejamento_cache','atual',{'d':i},str(i))
                a.guardar('saude','integracao',{'d':i},str(i))
            self.assertEqual(a.db.execute('SELECT count(*) FROM versoes').fetchone()[0],1)
            self.assertEqual(a.db.execute('SELECT count(*) FROM estados_operacionais').fetchone()[0],3)
            self.assertEqual(a.ultimos('planejamento')['atual'],{'publicado_em':'99'})
            a.guardar('atividade','guerra1',{'pontos':2},'1')
            a.guardar('atividade','guerra1',{'pontos':3},'2')
            a.guardar('atividade','guerra1',{'pontos':3},'3')
            self.assertEqual(a.db.execute("SELECT count(*) FROM versoes WHERE tipo='atividade'").fetchone()[0],2)
            a.backup(Path(td)/'copia.sqlite3')
            a.close()
            b=Arquivo(Path(td)/'copia.sqlite3')
            self.assertEqual(b.ultimos('atividade')['guerra1'],{'pontos':3})
            self.assertEqual(b.ultimos('planejamento')['atual'],{'publicado_em':'99'})
            b.close()

    def test_retencao_janelas_e_tres_mais_recentes(self):
        files=[Path(f'backup_202610{d:02d}.sqlite3.gz') for d in range(14,1,-1)]
        keep=selecionar_reter(files,date(2026,10,14))
        self.assertTrue(set(files[:7])<=keep)
        self.assertIn(Path('backup_20261004.sqlite3.gz'),keep)
        self.assertNotIn(Path('backup_20261002.sqlite3.gz'),keep)
        antigos=[Path('backup_20260103.sqlite3.gz'),Path('backup_20260102.sqlite3.gz'),Path('backup_20260101.sqlite3.gz')]
        self.assertEqual(selecionar_reter(antigos,date(2026,10,14)),set(antigos))

    def test_fotografia_igual_com_novo_horario_nao_cria_versao(self):
        with tempfile.TemporaryDirectory() as td:
            a = Arquivo(Path(td) / 'a.sqlite3')
            a.guardar('roster', 'principal', {'consultado_em': '2026-11-01T00:00:00+00:00', 'contas': []}, '2026-11-01T00:00:00+00:00')
            a.guardar('roster', 'principal', {'consultado_em': '2026-11-01T00:05:00+00:00', 'contas': []}, '2026-11-01T00:05:00+00:00')
            self.assertEqual(a.db.execute("SELECT count(*) FROM versoes WHERE tipo='roster'").fetchone()[0], 1)
            a.guardar('roster', 'principal', {'consultado_em': '2026-11-01T00:10:00+00:00', 'contas': [{'tag': '#A'}]}, '2026-11-01T00:10:00+00:00')
            self.assertEqual(a.db.execute("SELECT count(*) FROM versoes WHERE tipo='roster'").fetchone()[0], 2)
            a.close()

    def test_manutencao_preserva_atividade_fonte_revisao_e_retem_fotografia_recente(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td); banco = base / 'a.sqlite3'; backups = base / 'backups'
            a = Arquivo(banco)
            for tipo in ('planejamento', 'planejamento_cache', 'saude'):
                a.db.execute("INSERT INTO versoes(tipo,chave,sha256,conteudo,registrado_em) VALUES(?,?,?,?,?)", (tipo, 'atual', 'x', '{}', '2026-10-01T00:00:00+00:00'))
                a.guardar(tipo, 'atual', {'novo': True}, '2026-11-14T00:00:00+00:00')
            for momento in ('2026-09-01T00:00:00+00:00', '2026-11-13T00:00:00+00:00', '2026-11-13T00:05:00+00:00'):
                a.db.execute("INSERT INTO versoes(tipo,chave,sha256,conteudo,registrado_em) VALUES(?,?,?,?,?)", ('roster', 'principal', momento, '{}', momento))
            for tipo in ('atividade', 'fonte', 'revisao'):
                a.db.execute("INSERT INTO versoes(tipo,chave,sha256,conteudo,registrado_em) VALUES(?,?,?,?,?)", (tipo, tipo, 'x', '{}', '2026-09-01T00:00:00+00:00'))
            a.db.commit(); a.close(); del a
            plano = verificar(banco, 30)
            self.assertEqual(plano['exclusoes_planejadas']['estados_operacionais_antigos'], 3)
            resultado = aplicar(banco, backups, 30)
            self.assertTrue(Path(resultado['backup']).exists())
            with sqlite3.connect(banco) as db:
                self.assertEqual(db.execute("SELECT count(*) FROM versoes WHERE tipo IN ('atividade','fonte','revisao')").fetchone()[0], 3)
                self.assertEqual(db.execute("SELECT count(*) FROM versoes WHERE tipo='roster'").fetchone()[0], 1)
                self.assertEqual(db.execute("SELECT count(*) FROM versoes WHERE tipo='planejamento'").fetchone()[0], 0)
            del db
            gc.collect()  # SQLite no Windows pode manter o handle até a coleta final.

if __name__=='__main__':unittest.main()
