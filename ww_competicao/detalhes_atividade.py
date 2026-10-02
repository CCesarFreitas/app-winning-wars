"""Projeção pública de capturas encerradas; usa as regras instaladas no motor."""
import json
from datetime import datetime, timezone
from .historico_publico import atividades_publicas
from .participacao_competicao import pc_estado


def detalhar(captura, tipo, registro=None, eventos=()):
    aplicado = atividades_publicas([registro]) if registro else []
    if registro and not aplicado:
        raise ValueError('Lançamento sem integridade confirmada')
    if captura.get('temporada_origem', '') < '2026-10':
        raise ValueError('Histórico anterior à integração')
    if tipo == 'guerra':
        from preparar_calculo_guerra_auto import preparar_calculo
        from calculo_guerra_outubro import calcular_amostra
        preparar_calculo(captura, captura['temporada_origem'], False)
        bruto = calcular_amostra(captura['guerra'])['jogadores']
        dados = captura['guerra']
    elif tipo == 'liga':
        from validar_captura_liga import validar_captura
        if captura.get('origem') != 'api_liga':
            raise ValueError('Origem não oficial')
        resultado = validar_captura(captura)
        bruto = resultado['calculo']['jogadores']
        dados = captura['guerra']
    elif tipo == 'raide':
        from validar_captura_raide import validar_captura
        bruto = validar_captura(captura)['jogadores']
        dados = captura['raid']
    else:
        raise ValueError('Modalidade desconhecida')
    detalhes = json.loads(registro['DetalhesJSON']) if registro else {}
    if registro and (registro['AtividadeID'] != captura['atividade_id']
                     or registro['Tipo'] != tipo
                     or detalhes.get('captura_sha256') != captura['conteudo_sha256']):
        raise ValueError('Captura diferente da usada no lançamento')
    por_tag = {tag: pid for pid, tag in detalhes.get('tags', {}).items()}
    # A decisão de hoje não reescreve a elegibilidade de uma atividade passada.
    momento = datetime.fromisoformat(registro['AplicadoEm']) if registro else None
    historicos = [e for e in eventos if momento and datetime.fromisoformat(e['RegistradoEm']) <= momento]
    estado = pc_estado(historicos)
    jogadores = []
    for tag, j in sorted(bruto.items()):
        pid = por_tag.get(tag)
        pontos = detalhes.get('pontos_por_participante', {}).get(pid)
        if not registro:
            motivo = 'Encerrada no jogo; aguardando lançamento ou revisão'
        elif pid is not None:
            motivo = 'Pontuação registrada' if pontos else 'Sem pontos neste resultado'
        elif estado.get(tag, {}).get('Habilitada') == 'FALSE':
            motivo = 'Participação desabilitada no momento do lançamento'
        elif j.get('pontos_brutos', j.get('ataques', 0)) == 0:
            motivo = 'Sem pontuação válida para ingresso automático'
        else:
            motivo = 'Não incluída no lançamento; motivo requer conferência administrativa'
        item = {'tag': tag, 'nome': j['nome'], 'participante_id': pid,
                'pontos': pontos, 'situacao': motivo, 'ataques': []}
        if tipo == 'raide':
            raid = detalhes.get('raide_por_participante', {}).get(pid, {})
            item.update(quantidade_ataques=j['ataques'], saque=j['capital_resources_looted'],
                        bonus=raid.get('bonus_top3'))
            if pid is not None and (raid.get('ataques') != j['ataques']
                    or raid.get('saque') != j['capital_resources_looted']):
                raise ValueError('Raide lançado diverge da captura')
        else:
            item['cv'] = j['cv']
            item['pontos_calculados'] = j['pontos_brutos']
            if pid is not None and pontos != j['pontos_brutos']:
                raise ValueError('Cálculo diverge do lançamento original')
            ataques = j['ataques'] if tipo == 'guerra' else ([j['ataque']] if j['ataque'] else [])
            for a in ataques:
                valor = a.get('pontos', j['pontos_brutos'])
                if tipo == 'guerra' and j['cv'] - a['cv_alvo'] >= 2:
                    regra = ('Ataque sem pontuação: havia alternativa aberta na faixa permitida'
                             if a['alternativas_abertas'] else 'Desconto de uma estrela por diferença de CV')
                elif tipo == 'liga' and a['estrelas'] == 2 and a['cv_alvo'] > j['cv']:
                    regra = 'Duas estrelas contra CV superior: três pontos'
                else:
                    regra = 'Estrelas convertidas em pontos; alvo já fechado também vale'
                item['ataques'].append({'Ordem': a['ordem'], 'Alvo': a['alvo_tag'],
                    'CV atacante': j['cv'], 'CV alvo': a['cv_alvo'], 'Estrelas': a['estrelas'],
                    'Pontos do ataque': valor, 'Regra aplicada': regra})
        jogadores.append(item)
    return {'id': captura['atividade_id'], 'tipo': tipo,
            'temporada': captura['temporada_origem'], 'inicio': dados['startTime'],
            'fim': dados['endTime'], 'captura_sha256': captura['conteudo_sha256'],
            'status': 'APLICADO' if registro else 'AGUARDANDO_LANCAMENTO',
            'coluna': registro['ColunaDestino'] if registro else '',
            'aplicado_em': registro['AplicadoEm'] if registro else None,
            'regra': registro['VersaoRegra'] if registro else 'Prévia de desempenho; sem pontos atribuídos',
            'jogadores': jogadores}
