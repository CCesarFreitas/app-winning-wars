"""Coleta de planejamento: apenas GET, armazenamento separado dos pontos."""
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

TAG = '#YVLGUJQY'


def data(valor):
    return datetime.strptime(valor, '%Y%m%dT%H%M%S.%fZ').replace(tzinfo=timezone.utc)


def validar_grupo(g):
    if g.get('state') not in ('preparation', 'inWar', 'ended') or not g.get('season'):
        raise ValueError('Grupo indisponível')
    clans = g.get('clans', [])
    if len(clans) != 8 or len({c['tag'] for c in clans}) != 8 or TAG not in {c['tag'] for c in clans}:
        raise ValueError('Grupo incompleto')
    for c in clans:
        ms = c.get('members', [])
        if not ms or len({m['tag'] for m in ms}) != len(ms):
            raise ValueError('Elenco incompleto')
        if any(type(m.get('townHallLevel')) is not int or m['townHallLevel'] < 1 for m in ms):
            raise ValueError('CV ausente')
    if not isinstance(g.get('rounds'), list) or not g['rounds']:
        raise ValueError('Rodadas ausentes')
    tags = [t for r in g['rounds'] for t in r['warTags'] if t != '#0']
    if len(tags) != len(set(tags)):
        raise ValueError('Guerras duplicadas')
    return g


def validar_guerra(g, liga=False):
    if g.get('state') == 'notInWar' and not liga:
        return {'state': 'notInWar'}
    if g.get('state') not in ('preparation', 'inWar', 'warEnded'):
        raise ValueError('Estado desconhecido')
    if type(g.get('teamSize')) is not int or g['teamSize'] <= 0:
        raise ValueError('Tamanho inválido')
    if data(g['endTime']) <= data(g['startTime']):
        raise ValueError('Datas inválidas')
    if g['clan']['tag'] == g['opponent']['tag']:
        raise ValueError('Lados iguais')
    ordens = set()
    for lado, outro in (('clan', 'opponent'), ('opponent', 'clan')):
        ms = g[lado].get('members', [])
        if len(ms) != g['teamSize'] or len({m['tag'] for m in ms}) != len(ms):
            raise ValueError('Escalação incompleta')
        # Na preparação da CWL, a API pode manter posições do elenco inscrito:
        # uma escalação de 30 vilas pode incluir a posição 43, com lacunas.
        posicoes = [m.get('mapPosition') for m in ms]
        if any(type(p) is not int or p < 1 for p in posicoes) or len(set(posicoes)) != len(ms):
            raise ValueError('Posições inválidas ou repetidas')
        alvos = {m['tag'] for m in g[outro].get('members', [])}
        for m in ms:
            if type(m.get('townhallLevel')) is not int or m['townhallLevel'] < 1:
                raise ValueError('CV inválido')
            ataques = m.get('attacks', [])
            limite = 1 if liga else g.get('attacksPerMember', 2)
            if len(ataques) > limite:
                raise ValueError('Limite de ataques')
            for a in ataques:
                if a.get('attackerTag') != m['tag'] or a.get('defenderTag') not in alvos:
                    raise ValueError('Ataque sem vínculo')
                if type(a.get('stars')) is not int or not 0 <= a['stars'] <= 3:
                    raise ValueError('Estrelas inválidas')
                if type(a.get('order')) is not int or a['order'] < 1 or a['order'] in ordens:
                    raise ValueError('Ordem inválida')
                if not isinstance(a.get('destructionPercentage'), (float, int)) or not 0 <= a['destructionPercentage'] <= 100:
                    raise ValueError('Destruição inválida')
                ordens.add(a['order'])
        if 'attacks' in g[lado] and sum(len(m.get('attacks', [])) for m in ms) != g[lado]['attacks']:
            raise ValueError('Total incompleto')
    if not liga and TAG not in (g['clan']['tag'], g['opponent']['tag']):
        raise ValueError('Clã inesperado')
    return g


def coletar(arquivo, buscar, agora=None, max_consultas=10):
    agora = agora or datetime.now(timezone.utc)
    stamp = agora.isoformat()
    cache = arquivo.ultimos('planejamento_cache').get('atual', {})
    guerras = arquivo.ultimos('planejamento_guerra')
    erros, chamadas = [], 0

    def obter(chave, rota, minutos, validar):
        nonlocal chamadas
        anterior = cache.get(chave)
        if anterior and agora - datetime.fromisoformat(anterior['consultado_em']) < timedelta(minutes=minutos):
            return anterior
        if chamadas >= max_consultas:
            erros.append(chave)
            return anterior
        chamadas += 1
        try:
            valor = {'consultado_em': stamp, 'dados': validar(buscar(rota))}
            cache[chave] = valor
            return valor
        except Exception:
            # Nunca publica corpo de erro externo ou informação de autenticação.
            erros.append(chave)
            return anterior

    grupo = obter('grupo', '/clans/%23YVLGUJQY/currentwar/leaguegroup', 15, validar_grupo)
    comum = obter('comum', '/clans/%23YVLGUJQY/currentwar', 5, validar_guerra)
    if comum and comum['dados']['state'] != 'notInWar':
        g = comum['dados']
        identidade = 'comum:' + g['startTime'] + ':' + g['clan']['tag'] + ':' + g['opponent']['tag']
        registro = {**comum, 'tipo': 'comum'}
        arquivo.guardar('planejamento_guerra', identidade, registro, stamp)
        guerras[identidade] = registro
    rows = []
    if grupo:
        g = grupo['dados']
        clans = {c['tag'] for c in g['clans']}
        for rodada, r in enumerate(g['rounds'], 1):
            for tag in r['warTags']:
                if tag == '#0':
                    continue
                anterior = guerras.get(tag)
                if anterior and anterior['dados']['state'] == 'warEnded':
                    valor = anterior
                else:
                    def validar(w):
                        validar_guerra(w, liga=True)
                        if not {w['clan']['tag'], w['opponent']['tag']} <= clans:
                            raise ValueError('Guerra fora do grupo')
                        return w
                    valor = obter(tag, '/clanwarleagues/wars/' + quote(tag, safe=''), 5, validar)
                if valor:
                    registro = {**valor, 'tipo': 'liga', 'rodada': rodada, 'warTag': tag, 'temporada': g['season']}
                    arquivo.guardar('planejamento_guerra', tag, registro, stamp)
                    rows.append(registro)
        arquivo.guardar('planejamento_grupo', g['season'], grupo, stamp)
    historico = sorted((v for v in guerras.values() if v.get('tipo') == 'comum'
                        and v['dados']['state'] == 'warEnded'),
                       key=lambda v: v['dados']['endTime'], reverse=True)[:12]
    # Evita crescimento do cache operacional entre temporadas; o arquivo histórico é independente.
    manter = {'grupo', 'comum'} | {r['warTag'] for r in rows}
    cache = {k: v for k, v in cache.items() if k in manter}
    arquivo.guardar('planejamento_cache', 'atual', cache, stamp)
    documento = {'versao': 1, 'publicado_em': stamp, 'grupo': grupo, 'comum': comum,
                 'guerras_liga': rows, 'historico_comum': historico, 'pendencias': erros}
    arquivo.guardar('planejamento', 'atual', documento, stamp)
    return documento


def ataques(g, lado):
    alvos = {m['tag']: m for m in g['opponent' if lado == 'clan' else 'clan']['members']}
    rows = []
    for m in g[lado]['members']:
        for a in m.get('attacks', []):
            alvo = alvos[a['defenderTag']]
            rows.append({'Ordem': a['order'], 'Atacante': m['name'], 'Tag': m['tag'],
                         'CV atacante': m['townhallLevel'], 'Alvo': alvo['name'],
                         'CV alvo': alvo['townhallLevel'], 'Posição alvo': alvo['mapPosition'],
                         'Estrelas': a['stars'], 'Destruição %': a['destructionPercentage'],
                         'Duração (s)': a.get('duration'), '_alvo': a['defenderTag']})
    vistos, melhores = set(), {}
    for a in sorted(rows, key=lambda x: x['Ordem']):
        tag = a['_alvo']
        a['Primeiro ataque'] = tag not in vistos
        a['Estrelas novas'] = max(0, a['Estrelas'] - melhores.get(tag, 0))
        melhores[tag] = max(a['Estrelas'], melhores.get(tag, 0))
        vistos.add(tag)
    return sorted(rows, key=lambda x: x['Ordem'])
