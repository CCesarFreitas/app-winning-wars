"""Ficha mensal somente leitura, baseada nas projeções da integração atual."""
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path

from .ranking_atual import _fonte, _registros, _inteiro, montar_ranking_atual


def _mes(valor):
    return isinstance(valor, str) and re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", valor)


def _registro(atividade, jogador):
    tipo = atividade['tipo']
    ataques = [{
        'ordem': a.get('Ordem'), 'alvo_nome': a.get('Alvo'),
        'cv_alvo': a.get('CV alvo'), 'estrelas': a.get('Estrelas'),
        'cv_atacante': a.get('CV atacante', jogador.get('cv')),
        'percentual': a.get('Destruição (%)'), 'pontos': a.get('Pontos do ataque'),
        'tipo': a.get('Regra aplicada'),
    } for a in jogador.get('ataques', [])]
    return {
        'tipo': tipo, 'identificador': atividade['id'], 'data': atividade.get('fim'),
        'temporada': atividade['temporada'], 'rodada': atividade.get('rodada'),
        'adversario': atividade.get('adversario'), 'estado': atividade.get('status'),
        'jogador': {
            'tag': jogador['tag'], 'nome': jogador.get('nome'), 'cv': jogador.get('cv'),
            'pontos_competicao': jogador.get('pontos'),
            'pontos_calculados': jogador.get('pontos_calculados'),
            'motivo': jogador.get('situacao'),
            'limite_ataques': jogador.get('limite_ataques'),
            'ataques': jogador.get('quantidade_ataques', 0) if tipo == 'raide' else ataques,
            'capital_resources_looted': jogador.get('saque'),
            'bonus_top3': jogador.get('bonus'),
        },
    }


def _resumo_historico(db, tag, temporada):
    estados = []
    for seq, raw in db.execute("SELECT sequencia, conteudo FROM versoes WHERE tipo='fonte' AND chave='EstadoMes' ORDER BY sequencia"):
        estado = {r[0]: r[1] if len(r) > 1 else '' for r in json.loads(raw)[1:] if r}
        estados.append((seq, estado))
    do_mes = [(s, e) for s, e in estados if e.get('temporada_atual_id') == temporada]
    if not do_mes or not any(e.get('mes_finalizado', '').upper() == 'TRUE' for _, e in do_mes):
        return None
    primeiro = do_mes[0][0]
    proximo = next((s for s, e in estados if s > primeiro and e.get('temporada_atual_id') != temporada), None)
    if proximo is None:
        return None

    def fonte(chave):
        row = db.execute("SELECT conteudo FROM versoes WHERE tipo='fonte' AND chave=? AND sequencia<? ORDER BY sequencia DESC LIMIT 1", (chave, proximo)).fetchone()
        return _registros(json.loads(row[0])) if row else []

    ids = {str(r.get('ParticipanteID')) for r in fonte('InscricoesTemporada')
           if r.get('Temporada') == temporada and r.get('PlayerTag', '').strip().upper() == tag}
    if not ids:
        ids = {str(r.get('ParticipanteID')) for r in fonte('VinculosParticipantes')
               if r.get('PlayerTag', '').strip().upper() == tag}
    rows = [r for r in fonte('Página1') if str(r.get('ID')) in ids]
    if len(rows) != 1:
        return None
    row = rows[0]
    resumo = {
        'guerra': sum(_inteiro(v) for k, v in row.items() if k.startswith(('Guerra_', 'Liga_'))),
        'raides': sum(_inteiro(v) for k, v in row.items() if k.startswith('Raide_')),
        'jogos': _inteiro(row.get('JogosCla')), 'eventos': _inteiro(row.get('Eventos')),
        'posicao': None, 'origem': 'fotografia_fechamento',
    }
    resumo['total'] = sum(resumo[k] for k in ('guerra', 'raides', 'jogos', 'eventos'))
    return resumo


def montar_ficha_mensal(caminho, player_tag, temporada=None):
    tag = str(player_tag).strip().upper()
    if not re.fullmatch(r'#[A-Z0-9]+', tag):
        raise ValueError('Tag invalida')
    if temporada is not None and not _mes(temporada):
        raise ValueError('Temporada deve ter formato AAAA-MM')
    with closing(sqlite3.connect(f'file:{Path(caminho).resolve().as_posix()}?mode=ro', uri=True)) as db:
        db.execute('BEGIN')
        estado, _ = _fonte(db, 'EstadoMes')
        atual = dict((r[0], r[1]) for r in estado[1:] if len(r) >= 2).get('temporada_atual_id')
        if not _mes(atual):
            raise ValueError('Temporada atual indisponivel')
        mes = temporada or atual
        registros = []
        rodadas_liga = set()
        meses = {atual}
        # Uma única versão de cada atividade; filtro antes de qualquer limitação.
        for raw, in db.execute("SELECT conteudo FROM versoes WHERE tipo='atividade' AND sequencia IN (SELECT MAX(sequencia) FROM versoes WHERE tipo='atividade' GROUP BY chave)"):
            a = json.loads(raw)
            if a.get('status') != 'APLICADO' or a.get('tipo') not in {'guerra', 'liga', 'raide'} or not _mes(a.get('temporada')):
                continue
            if a['tipo'] == 'liga' and a['temporada'] == mes and type(a.get('rodada')) is int and 1 <= a['rodada'] <= 7:
                rodadas_liga.add(a['rodada'])
            jogador = next((j for j in a.get('jogadores', []) if j.get('tag', '').upper() == tag), None)
            if jogador is None:
                continue
            meses.add(a['temporada'])
            if a['temporada'] == mes:
                registros.append(_registro(a, jogador))
        # Meses com totais manuais, mesmo sem atividades automáticas da conta.
        inscricoes, _ = _fonte(db, 'InscricoesTemporada')
        meses.update(r['Temporada'] for r in _registros(inscricoes)
                     if r.get('PlayerTag', '').upper() == tag and _mes(r.get('Temporada')))
        resumo = _resumo_historico(db, tag, mes) if mes != atual else None

    if mes == atual:
        atual_ranking = montar_ranking_atual(caminho)
        if atual_ranking['temporada'] != atual:
            raise ValueError('Temporada mudou durante a consulta; atualize a pagina')
        jogador_atual = next((j for j in atual_ranking['ranking'] if j['tag'] == tag), None)
        if jogador_atual:
            resumo = {k: jogador_atual.get(k) for k in ('posicao', 'total', 'guerra', 'raides', 'jogos', 'eventos')}
            resumo['origem'] = 'ranking_atual'
    registros.sort(key=lambda r: (r.get('data') or '', r['identificador']), reverse=True)
    if resumo is None:
        resumo = {k: None for k in ('posicao', 'total', 'guerra', 'raides', 'jogos', 'eventos')}
        resumo['origem'] = 'indisponivel'
    return {
        'ok': True, 'player_tag': tag, 'temporada': mes, 'temporada_atual': atual,
        'temporadas': sorted(meses | {mes}, reverse=True), 'resumo': resumo,
        'total': len(registros), 'registros': registros,
        'liga_rodadas_disponiveis': sorted(rodadas_liga),
        'pontos_competicao': sum(r['jogador']['pontos_competicao'] or 0 for r in registros),
    }
