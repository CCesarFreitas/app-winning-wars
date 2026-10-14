import unittest, tempfile, json
from pathlib import Path
from datetime import date
from ww_competicao.armazenamento import Arquivo
from operacao.backup_historico import selecionar_reter

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

if __name__=='__main__':unittest.main()
