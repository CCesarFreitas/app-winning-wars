"""Painel preparatorio de outubro. Nao ativa o motor nem altera o ranking."""
import re
import threading
from datetime import datetime
from zoneinfo import ZoneInfo

HEADERS = ['Temporada', 'ParticipanteID', 'Nome', 'PlayerTag', 'Status',
           'AtualizadoEm', 'AtualizadoPor']
TEMPORADA = '2026-10'
LOCK = threading.RLock()
# Vinculos confirmados pelo administrador nesta preparacao. Nao sao inscricoes.
SUGESTOES = {
    '1': ('JAMES JR', '#8L0YPGJYJ'),
    '2': ('Valdeir', '#QCRUU9G0'),
    '3': ('Rafael M', '#9YR2809R'),
    '4': ('Lusca', '#282LRJ8RU'),
    '5': ('Blitz', '#QL9UR0PQ'),
    '8': ('Victtor Silva', '#2JC8YYCQ9'),
    '10': ('William 77', '#QCYLC8G2V'),
    '11': ('Willian', '#LYPRYQU8R'),
    '12': ('I bzm', '#QU8J9GY29'),
    '13': ('CALAZANS', '#GJLPPPLLP'),
    '14': ('Pikachu', '#PY002PGJV'),
    '16': ('Hey_Wendel', '#UUJPRC9J'),
    '17': ('EDO-VIGARISTA', '#2QU2YGVUV'),
    '18': ('TTV Moura', '#LJQGRV9YV'),
    '19': ('Kill3rM4nch4', '#L0YYQGG99'),
    '22': ('IgorClash', '#2PVVVP8QV'),
    '25': ('Nato', '#9CUJGQJG'),
    '26': ('Mohamed', '#GV098C8LR'),
    '27': ('Soares', '#GVVG2JVPC'),
    '28': ('Sirius-Black', '#G9GGPC0CJ'),
    '29': ('Hawk', '#LJ0GJG29C'),
    '30': ('Zlatan', '#R080YGL0J'),
    '32': ('Eddy', '#PGJLRLVC0'),
    '34': ('lfmmsl', '#YLUVGP2G'),
    '36': ('KANON', '#GJV02QUJJ'),
    '37': ('LucasFazek', '#Q2C0QUUUJ'),
    '38': ('LuiZ', '#888V2C2J2'),
    '39': ('IBIZAI', '#Q2U0L9JQU'),
}


def ler_registros(valores):
    if not valores or valores[0] != HEADERS:
        raise ValueError('Cabecalhos de InscricoesTemporada diferentes do esperado.')
    registros = []
    participantes, tags = set(), set()
    for linha, valores_linha in enumerate(valores[1:], start=2):
        if not any(str(v).strip() for v in valores_linha):
            continue
        if len(valores_linha) > len(HEADERS):
            raise ValueError(f'Linha {linha}: colunas inesperadas.')
        valores_linha = valores_linha + [''] * (len(HEADERS) - len(valores_linha))
        r = dict(zip(HEADERS, (str(v).strip() for v in valores_linha)))
        r['PlayerTag'] = r['PlayerTag'].upper()
        r['Status'] = r['Status'].upper()
        if not re.fullmatch(r'[0-9]{4}-[0-9]{2}', r['Temporada']):
            raise ValueError(f'Linha {linha}: temporada invalida.')
        datetime.strptime(r['Temporada'], '%Y-%m')
        if not r['ParticipanteID'] or not r['Nome']:
            raise ValueError(f'Linha {linha}: participante sem ID ou nome.')
        if not re.fullmatch(r'#[0289PYLQGRJCUV]+', r['PlayerTag']):
            raise ValueError(f'Linha {linha}: tag invalida.')
        if r['Status'] not in {'RASCUNHO', 'ATIVO', 'INATIVO'}:
            raise ValueError(f'Linha {linha}: status invalido.')
        p = (r['Temporada'], r['ParticipanteID'])
        t = (r['Temporada'], r['PlayerTag'])
        if p in participantes or t in tags:
            raise ValueError(f'Linha {linha}: participante ou tag duplicado na temporada.')
        participantes.add(p)
        tags.add(t)
        r['_linha'] = linha
        registros.append(r)
    return registros


def planejar_rascunho(valores, participante, nome, tag, admin, agora=None):
    agora = agora or datetime.now(ZoneInfo('America/Sao_Paulo'))
    if agora.tzinfo is None:
        raise ValueError('Horario sem fuso.')
    if agora.astimezone(ZoneInfo('America/Sao_Paulo')).strftime('%Y-%m') >= TEMPORADA:
        raise ValueError('A preparacao encerrou. Use a futura gestao de temporada.')
    if not str(admin).strip():
        raise ValueError('Administrador nao identificado.')
    registros = ler_registros(valores)
    participante, nome, tag = str(participante).strip(), str(nome).strip(), str(tag).strip().upper()
    atual = next((r for r in registros if r['Temporada'] == TEMPORADA
                  and r['ParticipanteID'] == participante), None)
    if atual and atual['Status'] != 'RASCUNHO':
        raise ValueError('Este painel so altera rascunhos, nunca inscricoes ativas ou inativas.')
    registro = [TEMPORADA, participante, nome, tag, 'RASCUNHO',
                agora.isoformat(timespec='seconds'), str(admin).strip()]
    linha = atual['_linha'] if atual else max([r['_linha'] for r in registros], default=1) + 1
    candidato = [list(v) for v in valores]
    while len(candidato) < linha:
        candidato.append([])
    candidato[linha - 1] = registro
    ler_registros(candidato)
    return linha, registro


def salvar_rascunho(aba, estado_aba, esperado, participante, nome, tag, admin, agora=None):
    # Serializa sessoes deste processo. Nao e um bloqueio distribuido do Sheets.
    with LOCK:
        estado = {r[0]: r[1] for r in estado_aba.get_all_values() if len(r) >= 2}
        temporada = estado.get('temporada_atual_id', '')
        if not re.fullmatch(r'[0-9]{4}-[0-9]{2}', temporada):
            raise ValueError('Temporada atual ausente ou invalida; gravacao bloqueada.')
        datetime.strptime(temporada, '%Y-%m')
        if temporada >= TEMPORADA:
            raise ValueError('Outubro ja foi aberto; este painel preparatorio nao pode gravar.')
        atuais = aba.get_all_values()
        if atuais != esperado:
            raise ValueError('As inscricoes mudaram. Atualize a lista antes de salvar.')
        linha, registro = planejar_rascunho(atuais, participante, nome, tag, admin, agora)
        if linha > aba.row_count:
            raise ValueError('A aba esta sem linhas disponiveis.')
        # Sem retry automatico de escrita: uma resposta incerta exige nova leitura.
        aba.update(range_name=f'A{linha}:G{linha}', values=[registro], value_input_option='RAW')
        if aba.get(f'A{linha}:G{linha}') != [registro]:
            raise RuntimeError('Gravacao nao confirmada. Atualize a lista para conferir.')


def renderizar_painel(st, planilha, sheet_dados, sheet_estado):
    st.caption('Preparacao de outubro/2026. Salvar aqui nao ativa participantes nem altera pontos.')
    st.info('Use este painel com um administrador por vez. A ativacao do motor sera uma etapa separada.')
    if st.button('Carregar ou atualizar inscricoes', key='ww_inscricoes_carregar'):
        st.session_state.pop('ww_inscricoes_base', None)
    try:
        aba = planilha.worksheet('InscricoesTemporada')
        if 'ww_inscricoes_base' not in st.session_state:
            st.session_state['ww_inscricoes_base'] = aba.get_all_values()
        base = st.session_state['ww_inscricoes_base']
        registros = ler_registros(base)
        outubro = [{k: r[k] for k in HEADERS} for r in registros if r['Temporada'] == TEMPORADA]
        if outubro:
            st.dataframe(outubro, hide_index=True, use_container_width=True)
        else:
            st.info('Nenhum rascunho de outubro cadastrado.')

        # ID e nome vem do cadastro atual. Este painel nunca escreve nele.
        cadastro = sheet_dados.get_all_values()
        if not cadastro or 'ID' not in cadastro[0] or 'Nome' not in cadastro[0]:
            raise ValueError('Cadastro de jogadores sem ID ou Nome.')
        ids, nomes = cadastro[0].index('ID'), cadastro[0].index('Nome')
        opcoes = {}
        for linha in cadastro[1:]:
            if not any(linha):
                continue
            if len(linha) <= max(ids, nomes) or not linha[ids].strip() or not linha[nomes].strip():
                raise ValueError('Jogador sem ID ou nome no cadastro atual.')
            pid, nome = linha[ids].strip(), linha[nomes].strip()
            if pid in opcoes:
                raise ValueError('ID repetido no cadastro atual.')
            opcoes[pid] = nome
        if not opcoes:
            st.info('Nao ha jogadores cadastrados para selecionar.')
            return
        pid = st.selectbox('Participante', list(opcoes),
                           format_func=lambda p: f'{opcoes[p]} (ID {p})', key='ww_inscrito_id')
        existente = next((r for r in registros if r['Temporada'] == TEMPORADA and r['ParticipanteID'] == pid), None)
        confirmado = SUGESTOES.get(pid)
        sugestao = existente['PlayerTag'] if existente else (
            confirmado[1] if confirmado and confirmado[0] == opcoes[pid] else '')
        with st.form(f'ww_rascunho_{pid}'):
            tag = st.text_input('Tag da conta principal', value=sugestao,
                                help='Confira a conta no jogo. A sugestao nao inscreve automaticamente.')
            confirma = st.checkbox('Conferi a tag e quero preparar esta conta principal para outubro.')
            salvar = st.form_submit_button('Salvar rascunho de outubro')
        if salvar:
            if not confirma:
                st.warning('Confira a tag e marque a confirmacao.')
                return
            salvar_rascunho(aba, sheet_estado, base, pid, opcoes[pid], tag,
                            st.session_state.get('admin_logado', ''))
            st.session_state.pop('ww_inscricoes_base', None)
            st.success('Rascunho salvo. Nenhuma conta foi ativada no motor.')
    except ValueError as erro:
        st.error(str(erro))
    except Exception:
        st.error('Nao foi possivel concluir. Confira conexao, cabecalhos, duplicidades e se a preparacao ainda esta aberta. Atualize a lista antes de tentar novamente; uma gravacao pode ter sido recebida mesmo se a confirmacao falhar.')
