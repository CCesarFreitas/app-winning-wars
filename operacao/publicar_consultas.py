"""Observador independente. Nunca altera ranking, inscrição ou participação."""
import fcntl
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path('/opt/winning-wars-api')
MOTOR = BASE / 'oracle_producao_outubro'
RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ), str(MOTOR), str(BASE)]
from ww_competicao.armazenamento import Arquivo, empacotar
from ww_competicao.detalhes_atividade import detalhar
from ww_competicao.participacao_competicao import pc_ler_eventos, pc_estado

SHEET = '1QTfVjrfSCVZ3JlqIDbhLHHBc2-anz8XhK9WzxU3v0oA'
TORNEIO_TAG = os.environ.get('WW_TORNEIO_CLAN_TAG', '#2YPL9GU8Y').strip().upper()


def linhas_registros(linhas):
    return [dict(zip(linhas[0], r)) for r in linhas[1:] if any(r)] if linhas else []


def saude(agora):
    unidades = ['winning-wars-outubro-guerra.service', 'winning-wars-outubro-ciclo.timer',
                'winning-wars-api.service']
    estados = {}
    for nome in unidades:
        r = subprocess.run(['systemctl', 'show', nome, '-p', 'ActiveState', '--value'],
                           capture_output=True, text=True, timeout=15, check=True)
        estados[nome] = r.stdout.strip()
    ciclo = json.loads((MOTOR / 'ultimo_ciclo_simulacao.json').read_text())
    guerra = {}
    r = subprocess.run(['journalctl', '-u', unidades[0], '-n', '300', '--no-pager', '-o', 'cat'],
                       capture_output=True, text=True, timeout=15, check=True)
    for linha in r.stdout.splitlines():
        if linha.startswith('{'):
            try:
                d = json.loads(linha)
                if 'registrado_em' in d and 'intervalo' in d:
                    guerra = {k: d[k] for k in ('status', 'registrado_em', 'intervalo')}
            except (ValueError, KeyError):
                pass
    return {'verificado_em': agora, 'servicos': estados, 'guerra': guerra,
            'ciclo': {k: ciclo.get(k) for k in ('inicio', 'fim', 'status', 'etapas')}}


def executar():
    agora = datetime.now(timezone.utc)
    dados_dir = BASE / 'dados_consulta'
    dados_dir.mkdir(mode=0o700, exist_ok=True)
    os.chmod(dados_dir, 0o700)
    trava = (dados_dir / 'publicacao.lock').open('a')
    fcntl.flock(trava, fcntl.LOCK_EX | fcntl.LOCK_NB)
    arquivo = Arquivo(dados_dir / 'historico.sqlite3')
    import gspread
    from google.oauth2.service_account import Credentials
    cred = Credentials.from_service_account_file(str(BASE / 'credentials/google_service_account.json'),
                scopes=['https://www.googleapis.com/auth/spreadsheets'])
    planilha = gspread.authorize(cred).open_by_key(SHEET)
    nomes = ['ControleAtividades', 'ParticipacaoCompeticao', 'InscricoesTemporada',
             'VinculosParticipantes', 'EstadoMes', 'Página1']
    # Uma leitura em lote; não acessa credenciais de administradores.
    resposta = planilha.values_batch_get(["'" + n + "'!A:ZZ" for n in nomes],
                                         params={'valueRenderOption': 'FORMATTED_VALUE'})
    fotos = {n: r.get('values', []) for n, r in zip(nomes, resposta['valueRanges'])}
    for nome, linhas in fotos.items():
        arquivo.guardar('fonte', nome, linhas, agora.isoformat())
    eventos = pc_ler_eventos(fotos['ParticipacaoCompeticao'])
    contas = pc_estado(eventos)
    vinculos = {r['PlayerTag']: r['ParticipanteID']
                for r in linhas_registros(fotos['VinculosParticipantes'])}
    registros = linhas_registros(fotos['ControleAtividades'])
    contagem = Counter(r['AtividadeID'] for r in registros)
    por_id = {r['AtividadeID']: r for r in registros if contagem[r['AtividadeID']] == 1}
    estado_mes = dict(r[:2] for r in fotos['EstadoMes'][1:] if len(r) >= 2)
    temporada = estado_mes.get('temporada_atual_id')
    inscritos = {r['PlayerTag'] for r in linhas_registros(fotos['InscricoesTemporada'])
                 if r.get('Temporada') == temporada and r.get('Status') == 'ATIVO'}
    # Consultas independentes da Supercell; nunca executam sincronização de cadastro.
    rosters = arquivo.ultimos('roster')
    erro_membros = False
    def obter_roster(chave, tag, validade):
        nonlocal erro_membros
        anterior = rosters.get(chave)
        if anterior and anterior.get('tag') != tag:
            anterior = None
        if anterior and agora - datetime.fromisoformat(anterior['consultado_em']) < validade:
            return anterior
        try:
            from supercell import supercell_get
            clan = supercell_get('/clans/' + tag.replace('#', '%23'))
            lista = clan.get('memberList')
            if (clan.get('tag') != tag or not isinstance(lista, list) or not lista
                    or clan.get('members') != len(lista)):
                raise ValueError('Lista de membros inválida')
            roster = {'consultado_em': agora.isoformat(), 'clan': clan.get('name', ''),
                      'tag': tag, 'contas': [
                {'tag': m['tag'], 'nome': m['name'], 'cv': m.get('townHallLevel'),
                 'cargo': m.get('role')} for m in lista]}
            if (len({m['tag'] for m in roster['contas']}) != len(roster['contas'])
                    or any(type(m['cv']) is not int or m['cv'] < 1 for m in roster['contas'])):
                raise ValueError('Membros duplicados ou incompletos')
            arquivo.guardar('roster', chave, roster, agora.isoformat())
            rosters[chave] = roster
            return roster
        except Exception:
            erro_membros = True
            return anterior

    # O elenco principal muda pouco para a consulta pública. O clã de torneios
    # é parametrizado no servidor e atualizado em intervalos curtos para lives.
    membros = obter_roster('principal', '#YVLGUJQY', timedelta(hours=8))
    roster_torneio = obter_roster('torneio_teste', TORNEIO_TAG, timedelta(minutes=2))
    documentos = {}
    if membros:
        documentos['membros'] = {'consultado_em': membros['consultado_em'], 'temporada': temporada,
            'contas': [{**m, 'competicao': 'Inscrito no mês' if m['tag'] in inscritos else 'Ainda não inscrito',
                       'permissao': ('Bloqueada' if contas.get(m['tag'], {}).get('Habilitada') == 'FALSE'
                                    else 'Habilitada' if m['tag'] in contas else 'Sem decisão registrada')}
                      for m in membros['contas']]}
    if roster_torneio:
        documentos['torneio_roster'] = {
            'modo': 'OFICIAL', 'consultado_em': roster_torneio['consultado_em'],
            'clan': roster_torneio['clan'], 'tag': roster_torneio['tag'],
            'contas': [{k: m[k] for k in ('tag', 'nome', 'cv')} for m in roster_torneio['contas']],
        }
    # Revisões entram também na reconstrução do detalhe: uma correção auditada
    # pode incluir uma conta que o lançamento original omitiu.
    try:
        revisoes_fonte = planilha.worksheet('RevisoesPontuacao').get_all_values()
    except gspread.WorksheetNotFound:
        revisoes_fonte = []
    revisoes_registros = linhas_registros(revisoes_fonte)
    falhas = []
    candidatas = {}
    for tipo in ('guerra', 'liga', 'raide'):
        for caminho in (MOTOR / ('capturas_' + tipo)).rglob('*.json'):
            try:
                captura = json.loads(caminho.read_text())
                if captura.get('temporada_origem', '') < '2026-10':
                    continue
                dados = captura.get('guerra', captura.get('raid', {}))
                if dados.get('state') not in ('warEnded', 'ended'):
                    continue
                identidade = captura['atividade_id']
                if contagem[identidade] > 1:
                    raise ValueError('Atividade duplicada')
                registro = por_id.get(identidade)
                if registro and json.loads(registro['DetalhesJSON']).get('captura_sha256') != captura.get('conteudo_sha256'):
                    continue
                detalhe = detalhar(captura, tipo, registro, eventos, vinculos, revisoes_registros)
                anterior = candidatas.get(identidade)
                # Uma mesma atividade pode ter várias fotografias encerradas. A de lançamento prevalece.
                if not anterior or captura.get('arquivado_em', '') > anterior[0]:
                    candidatas[identidade] = (captura.get('arquivado_em', ''), detalhe)
            except Exception as erro:
                falhas.append(type(erro).__name__)
    anteriores = arquivo.ultimos('atividade')
    for identidade, (_, detalhe) in candidatas.items():
        # Fechamento mensal pode limpar a aba operacional. Não rebaixa um resultado arquivado.
        if anteriores.get(identidade, {}).get('status') == 'APLICADO' and detalhe['status'] != 'APLICADO':
            continue
        arquivo.guardar('atividade', identidade, detalhe, agora.isoformat())
    for identidade, detalhe in arquivo.ultimos('atividade').items():
        documentos['atividade:' + identidade] = detalhe
    # Revisões são arquivadas somente se a aba já existe; não cria dados fictícios.
    if revisoes_fonte:
        arquivo.guardar('fonte', 'RevisoesPontuacao', revisoes_fonte, agora.isoformat())
        for r in revisoes_registros:
            arquivo.guardar('revisao', r['RevisaoID'], r, agora.isoformat())
    documentos['revisoes'] = [{k: r[k] for k in ('RevisaoID', 'Temporada', 'ParticipanteID', 'Atividade',
        'Antes', 'Depois', 'RegistradoEm')} for r in arquivo.ultimos('revisao').values()]
    health = saude(agora.isoformat())
    health.update(falhas_historico=len(falhas), falha_membros=erro_membros,
                  ultima_atividade=max((r.get('AplicadoEm', '') for r in registros), default=None),
                  ranking_conferido_em=agora.isoformat(), temporada=temporada,
                  atividades_aguardando=sum(d['status'] != 'APLICADO' for _, d in candidatas.values()),
                  atividades_sem_detalhe=sum(i not in candidatas for i in por_id),
                  armazenamento='SQLite na Oracle; ranking mantido na planilha')
    documentos['saude'] = health
    arquivo.guardar('saude', 'integracao', health, agora.isoformat())
    # Processo limitado: uma falha da Supercell não impede publicar as consultas existentes.
    planejamento_ok = False
    try:
        retorno = subprocess.run([sys.executable, '-B', str(RAIZ / 'operacao/coletar_planejamento.py')],
                                 capture_output=True, text=True, timeout=65)
        planejamento_ok = retorno.returncode == 0
    except subprocess.TimeoutExpired:
        pass
    planejamento = arquivo.ultimos('planejamento').get('atual')
    if planejamento:
        documentos['planejamento'] = {**planejamento, 'coleta_interrompida': not planejamento_ok}
    linhas = empacotar(documentos)
    try:
        destino = planilha.worksheet('ConsultaPublica')
    except gspread.WorksheetNotFound:
        destino = planilha.add_worksheet(title='ConsultaPublica', rows=max(1000, len(linhas)), cols=3)
    # Substitui apenas a projeção pública numa única operação atômica do Sheets.
    requisicoes = []
    if destino.row_count < len(linhas):
        requisicoes.append({'appendDimension': {'sheetId': destino.id, 'dimension': 'ROWS',
                                                'length': len(linhas)-destino.row_count}})
    requisicoes.append({'updateCells': {'range': {'sheetId': destino.id}, 'fields': 'userEnteredValue',
        'rows': [{'values': [{'userEnteredValue': {'stringValue': str(v)}} for v in linha]} for linha in linhas]}})
    planilha.batch_update({'requests': requisicoes})
    if destino.get_all_values() != linhas:
        raise ValueError('Publicação não conferida')
    backup = dados_dir / ('backup_' + agora.strftime('%Y%m%d') + '.sqlite3')
    if not backup.exists():
        arquivo.backup(backup)
    arquivo.close()
    print('Consultas publicadas; ranking, inscrições e permissões preservados.', flush=True)


if __name__ == '__main__':
    executar()
