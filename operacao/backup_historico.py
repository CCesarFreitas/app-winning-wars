"""Backup diário verificado, comprimido e com retenção; não altera dados do app."""
import gzip, hashlib, json, os, sqlite3
from contextlib import closing
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path('/var/oled/winning-wars-backups')
SOURCE = Path('/opt/winning-wars-api/dados_consulta/historico.sqlite3')

def hash_arquivo(path, compactado=False):
    h=hashlib.sha256()
    with (gzip.open(path,'rb') if compactado else path.open('rb')) as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def selecionar_reter(files, hoje):
    # Sete dias, quatro semanas e seis meses; o mais recente de cada janela.
    manter=set(files[:3]); semanas=set(); meses=set()
    for p in files:
        data=datetime.strptime(p.name[7:15],'%Y%m%d').date()
        if data >= hoje-timedelta(days=6): manter.add(p)
        semana=data.isocalendar()[:2]
        if semana not in semanas and len(semanas)<4:
            semanas.add(semana); manter.add(p)
        mes=(data.year,data.month)
        if mes not in meses and len(meses)<6:
            meses.add(mes); manter.add(p)
    return manter

def executar():
    import fcntl
    assert ROOT.is_dir() and ROOT.stat().st_dev != SOURCE.parent.stat().st_dev
    lock=(ROOT/'backup.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    hoje=datetime.now(timezone.utc).date()
    destino=ROOT/('backup_'+hoje.strftime('%Y%m%d')+'.sqlite3.gz')
    if not destino.exists():
        temporario=ROOT/'backup_em_andamento.sqlite3'
        compactado=ROOT/'backup_em_andamento.gz'
        # Arquivos temporários pertencem exclusivamente a esta rotina e trava.
        for p in (temporario,compactado):
            if p.exists(): p.unlink()
        with closing(sqlite3.connect(SOURCE.as_uri()+'?mode=ro',uri=True)) as origem:
            with closing(sqlite3.connect(temporario)) as copia:
                origem.backup(copia,pages=256,sleep=0.05)
                assert copia.execute('PRAGMA integrity_check').fetchone()==('ok',)
        sha=hash_arquivo(temporario)
        with compactado.open('xb') as raw:
            with gzip.GzipFile(fileobj=raw,mode='wb',compresslevel=1,mtime=0) as gz, temporario.open('rb') as inp:
                for b in iter(lambda:inp.read(1024*1024),b''): gz.write(b)
            raw.flush(); os.fsync(raw.fileno())
        assert hash_arquivo(compactado,True)==sha
        os.replace(compactado,destino)
        destino.with_suffix('.gz.sha256').write_text(sha+'\n')
        temporario.unlink()
        print('Backup criado e conferido:',destino,flush=True)
    else:
        # Verifica CRC/estrutura antes de permitir retenção; hash quando disponível.
        sha=hash_arquivo(destino,True)
        assinatura=destino.with_suffix('.gz.sha256')
        if assinatura.exists(): assert assinatura.read_text().strip()==sha
        print('Backup diário existente conferido:',destino,flush=True)
    files=sorted(ROOT.glob('backup_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].sqlite3.gz'),reverse=True)
    manter=selecionar_reter(files,hoje)
    # Teto adicional de 8 GiB; preserva ao menos as três cópias mais recentes.
    for p in reversed(files):
        if sum(x.stat().st_size for x in manter)>8*1024**3 and p not in files[:3]: manter.discard(p)
    for p in files:
        if p not in manter:
            assert p.resolve().parent==ROOT.resolve() and not p.is_symlink()
            with (ROOT/'retencao.jsonl').open('a') as log:
                log.write(json.dumps({'arquivo':p.name,'bytes':p.stat().st_size,'data':str(hoje)})+'\n')
                log.flush(); os.fsync(log.fileno())
            p.unlink()
            p.with_suffix('.gz.sha256').unlink(missing_ok=True)
            print('Expirado pela retenção:',p.name,flush=True)
    print('Rotina concluída.',flush=True)

if __name__=='__main__': executar()
