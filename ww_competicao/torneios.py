"""Torneios eliminatórios oficiais para transmissão ao vivo."""
from copy import deepcopy
from datetime import datetime, timezone
from html import escape
import json
import random
import re


CHAVE_SESSAO = "ww_torneio_oficial_v1"

IMAGENS_CV = {
    18: "https://i.ibb.co/fGLhwj76/Town-Hall18.webp",
    17: "https://i.ibb.co/yc4LCWmS/cv17.webp",
    16: "https://i.ibb.co/ym8MH1Q8/Giga-Inferno16.webp",
    15: "https://i.ibb.co/7dzVK5L7/Giga-Inferno15.webp",
    14: "https://i.ibb.co/x4LsVdM/Giga-Inferno14.webp",
    13: "https://i.ibb.co/HTPNQtyp/TH-13-4-Clash-GFX.png",
    12: "https://i.ibb.co/hFHnz1GW/TH-12-Clash-GFX.png",
    11: "https://www.clash.ninja/images/entities/1_11.png",
    10: "https://www.clash.ninja/images/entities/1_10.png",
    9: "https://www.clash.ninja/images/entities/1_9.png",
}


def validar_roster(documento):
    if not isinstance(documento, dict) or documento.get("modo") != "OFICIAL":
        raise ValueError("Elenco do torneio indisponível")
    if (not re.fullmatch(r"#[0289PYLQGRJCUV]+", str(documento.get("tag", "")))
            or not str(documento.get("clan", "")).strip()):
        raise ValueError("Clã do torneio inválido")
    contas, tags = [], set()
    for conta in documento.get("contas", []):
        tag = conta.get("tag")
        if (not isinstance(tag, str) or not re.fullmatch(r"#[0289PYLQGRJCUV]+", tag)
                or tag in tags or not str(conta.get("nome", "")).strip()
                or type(conta.get("cv")) is not int or conta["cv"] < 1):
            raise ValueError("Elenco do torneio inválido")
        tags.add(tag)
        contas.append({"tag": tag, "nome": str(conta["nome"]).strip(), "cv": conta["cv"]})
    if len(contas) < 2:
        raise ValueError("O clã do torneio precisa de pelo menos duas contas")
    return sorted(contas, key=lambda c: (-c["cv"], c["nome"].casefold(), c["tag"]))


def _potencia_seguinte(valor):
    tamanho = 2
    while tamanho < valor:
        tamanho *= 2
    return tamanho


def _rotulos(quantidade_rodadas, tamanho):
    especiais = {2: "Grande final", 4: "Semifinais", 8: "Quartas de final", 16: "Oitavas de final"}
    nomes = []
    participantes = tamanho
    for indice in range(quantidade_rodadas):
        nomes.append(especiais.get(participantes, f"Fase de {participantes}"))
        participantes //= 2
    return nomes


def _participante(conta):
    return None if conta is None else {"tag": conta["tag"], "nome": conta["nome"], "cv": conta["cv"]}


def _propagar_automaticos(torneio):
    mudou = True
    while mudou:
        mudou = False
        for ri, rodada in enumerate(torneio["rodadas"]):
            for mi, partida in enumerate(rodada):
                presentes = [p for p in partida["jogadores"] if p is not None]
                # Uma vaga vazia significa folga somente na primeira fase. Nas
                # rodadas seguintes ela também pode significar que o confronto
                # anterior do outro lado ainda não terminou.
                if ri == 0 and partida["vencedor"] is None and len(presentes) == 1:
                    partida["vencedor"] = deepcopy(presentes[0])
                    partida["automatico"] = True
                    mudou = True
                vencedor = partida["vencedor"]
                if vencedor is not None and ri + 1 < len(torneio["rodadas"]):
                    destino = torneio["rodadas"][ri + 1][mi // 2]
                    posicao = mi % 2
                    if destino["jogadores"][posicao] is None:
                        destino["jogadores"][posicao] = deepcopy(vencedor)
                        mudou = True
        final = torneio["rodadas"][-1][0]
        if final["vencedor"] is not None:
            torneio["campeao"] = deepcopy(final["vencedor"])
            torneio["status"] = "FINALIZADO"
    return torneio


def criar_torneio(nome, participantes, cv, sorteio=None, criado_em=None):
    if not isinstance(nome, str) or not 3 <= len(nome.strip()) <= 80:
        raise ValueError("Nome do torneio inválido")
    if not isinstance(participantes, list) or not 2 <= len(participantes) <= 32:
        raise ValueError("Selecione de 2 a 32 participantes")
    tags = [p.get("tag") for p in participantes]
    if len(tags) != len(set(tags)) or any(not isinstance(tag, str) or not re.fullmatch(r"#[0289PYLQGRJCUV]+", tag)
                                              for tag in tags):
        raise ValueError("Participante duplicado")
    for participante in participantes:
        _participante(participante)
        if not participante.get("nome") or type(participante.get("cv")) is not int:
            raise ValueError("Participante incompleto")
    if cv != "Todos" and (type(cv) is not int or any(p["cv"] != cv for p in participantes)):
        raise ValueError("Participante fora do CV escolhido")
    rng = sorteio or random.SystemRandom()
    jogadores = [_participante(p) for p in participantes]
    rng.shuffle(jogadores)
    tamanho = _potencia_seguinte(len(jogadores))
    folgas = tamanho - len(jogadores)
    partidas_iniciais, cursor = [], 0
    for _ in range(folgas):
        partidas_iniciais.append({"jogadores": [jogadores[cursor], None], "vencedor": None,
                                  "automatico": False})
        cursor += 1
    while cursor < len(jogadores):
        partidas_iniciais.append({"jogadores": jogadores[cursor:cursor + 2], "vencedor": None,
                                  "automatico": False})
        cursor += 2
    rng.shuffle(partidas_iniciais)
    rodadas = [partidas_iniciais]
    quantidade = tamanho // 2
    while quantidade > 1:
        quantidade //= 2
        rodadas.append([{"jogadores": [None, None], "vencedor": None, "automatico": False}
                        for _ in range(quantidade)])
    torneio = {
        "versao": 2, "nome": nome.strip(), "clan": participantes[0].get("clan", ""),
        "clan_tag": participantes[0].get("clan_tag", ""),
        "cv": cv, "status": "EM_ANDAMENTO", "criado_em": criado_em or datetime.now(timezone.utc).isoformat(),
        "participantes": jogadores, "tamanho_chave": tamanho, "rotulos": _rotulos(len(rodadas), tamanho),
        "rodadas": rodadas, "campeao": None, "ultima_transicao": None,
    }
    return _propagar_automaticos(torneio)


def partidas_pendentes(torneio):
    resultado = []
    for ri, rodada in enumerate(torneio["rodadas"]):
        for mi, partida in enumerate(rodada):
            if partida["vencedor"] is None and all(partida["jogadores"]):
                resultado.append((ri, mi, partida))
    return resultado


def selecionar_vencedor(torneio, rodada, partida, tag):
    copia = deepcopy(torneio)
    if copia.get("status") != "EM_ANDAMENTO":
        raise ValueError("Torneio encerrado")
    if type(rodada) is not int or type(partida) is not int:
        raise ValueError("Partida inválida")
    confronto = copia["rodadas"][rodada][partida]
    if confronto["vencedor"] is not None or not all(confronto["jogadores"]):
        raise ValueError("Partida indisponível")
    jogadores = {p["tag"]: p for p in confronto["jogadores"]}
    if tag not in jogadores:
        raise ValueError("Vencedor não participa desta partida")
    vencedor = jogadores[tag]
    perdedor = next(p for p in confronto["jogadores"] if p["tag"] != tag)
    confronto["vencedor"] = deepcopy(vencedor)
    confronto["automatico"] = False
    copia["ultima_transicao"] = {"rodada": rodada, "partida": partida,
                                  "vencedor": vencedor["tag"], "perdedor": perdedor["tag"]}
    return _propagar_automaticos(copia)


def _cartao_jogador(jogador, vencedor, perdedor):
    if jogador is None:
        return '<div class="wwt-player bye"><span>FOLGA</span></div>'
    classes = "wwt-player"
    if jogador["tag"] == vencedor:
        classes += " winner pulse"
    elif jogador["tag"] == perdedor:
        classes += " loser"
    imagem = IMAGENS_CV.get(jogador["cv"])
    avatar = (f'<span class="wwt-avatar"><img src="{escape(imagem)}" alt="CV {jogador["cv"]}"></span>'
              if imagem else f'<span class="wwt-avatar wwt-avatar-number">{jogador["cv"]}</span>')
    return (f'<div class="{classes}">{avatar}'
            f'<div><b>{escape(jogador["nome"])}</b><small>{escape(jogador["tag"])} · CV {jogador["cv"]}</small></div></div>')


def html_chaveamento(torneio):
    transicao = torneio.get("ultima_transicao") or {}
    vencedor, perdedor = transicao.get("vencedor"), transicao.get("perdedor")
    colunas = []
    for ri, rodada in enumerate(torneio["rodadas"]):
        partidas = []
        for mi, confronto in enumerate(rodada):
            titulo = "CLASSIFICADO" if confronto["vencedor"] else f"JOGO {mi + 1}"
            auto = '<em>avanço automático</em>' if confronto.get("automatico") else ''
            partidas.append(f'''<div class="wwt-match"><div class="wwt-match-title">{titulo}{auto}</div>
                {_cartao_jogador(confronto['jogadores'][0], vencedor, perdedor)}
                <div class="wwt-versus">VS</div>
                {_cartao_jogador(confronto['jogadores'][1], vencedor, perdedor)}</div>''')
        colunas.append(f'<section class="wwt-round"><h3>{escape(torneio["rotulos"][ri])}</h3><div class="wwt-round-body">{"".join(partidas)}</div></section>')
    campeao = torneio.get("campeao")
    trofeu = (f'<div class="wwt-champion"><span>🏆</span><div><small>CAMPEÃO</small><b>{escape(campeao["nome"])}</b><em>CV {campeao["cv"]}</em></div></div>'
              if campeao else '')
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
      *{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at 50% 0,#251046,#070910 52%);color:#f8fafc;font-family:Inter,Arial,sans-serif}}
      .wwt-stage{{padding:22px;min-height:560px;overflow-x:auto}}.wwt-brand{{display:flex;justify-content:space-between;align-items:end;gap:20px;margin-bottom:18px}}
      .wwt-brand small{{color:#fbbf24;font-weight:900;letter-spacing:.18em}}.wwt-brand h1{{margin:4px 0 0;font-size:clamp(1.5rem,3vw,2.7rem);text-transform:uppercase}}
      .wwt-badge{{border:1px solid #7c3aed;border-radius:999px;padding:8px 13px;color:#c4b5fd;white-space:nowrap}}
      .wwt-bracket{{display:flex;gap:20px;min-width:max-content;align-items:stretch}}.wwt-round{{width:260px;display:flex;flex-direction:column}}
      .wwt-round h3{{text-align:center;color:#fbbf24;text-transform:uppercase;font-size:.78rem;letter-spacing:.14em;margin:0 0 12px}}
      .wwt-round-body{{display:flex;flex-direction:column;justify-content:space-around;gap:16px;flex:1}}.wwt-match{{position:relative;background:linear-gradient(145deg,#151827,#0b0d16);border:1px solid #34384e;border-radius:16px;padding:10px;box-shadow:0 10px 25px #0007}}
      .wwt-match:after{{content:"";position:absolute;right:-21px;top:50%;width:20px;height:2px;background:#7c3aed}}.wwt-round:last-child .wwt-match:after{{display:none}}
      .wwt-match-title{{display:flex;justify-content:space-between;color:#818cf8;font-size:.62rem;font-weight:900;letter-spacing:.12em;margin:0 5px 6px}}.wwt-match-title em{{color:#64748b;letter-spacing:0;font-weight:600}}
      .wwt-player{{display:flex;align-items:center;gap:9px;border:1px solid #2d3143;border-radius:11px;padding:8px;background:#111522;min-height:53px}}.wwt-player b{{display:block;max-width:170px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:.86rem}}.wwt-player small{{display:block;color:#94a3b8;font-size:.61rem;margin-top:2px}}
      .wwt-avatar{{display:grid;place-items:center;min-width:46px;width:46px;height:46px}}.wwt-avatar img{{display:block;max-width:46px;max-height:46px;object-fit:contain;filter:drop-shadow(0 3px 4px #000a)}}
      .wwt-avatar-number{{border-radius:50%;background:linear-gradient(145deg,#f59e0b,#7c2d12);border:2px solid #fde68a;font-weight:950;font-size:.75rem}}
      .wwt-versus{{height:12px;text-align:center;color:#475569;font-size:.55rem;font-weight:950;line-height:12px}}.wwt-player.bye{{justify-content:center;color:#64748b;border-style:dashed;background:#0b0d15}}
      .wwt-player.winner{{border-color:#fbbf24;background:linear-gradient(100deg,#422006,#171625);box-shadow:0 0 18px #f59e0b55}}.wwt-player.loser{{filter:grayscale(1);opacity:.35;animation:wwtLose .7s ease both}}
      .pulse{{animation:wwtWin 1.1s ease both}}@keyframes wwtWin{{0%{{transform:scale(.92)}}45%{{transform:scale(1.06);box-shadow:0 0 34px #fbbf24}}100%{{transform:scale(1)}}}}@keyframes wwtLose{{to{{transform:scale(.96);opacity:.35}}}}
      .wwt-champion{{margin:22px auto 0;max-width:520px;display:flex;align-items:center;justify-content:center;gap:16px;border:2px solid #fbbf24;border-radius:22px;padding:15px;background:linear-gradient(120deg,#451a03,#23113f);box-shadow:0 0 45px #f59e0b55;animation:wwtWin 1.2s ease}}
      .wwt-champion>span{{font-size:3rem;animation:float 2s ease-in-out infinite}}.wwt-champion small,.wwt-champion b,.wwt-champion em{{display:block}}.wwt-champion small{{color:#fbbf24;letter-spacing:.2em}}.wwt-champion b{{font-size:1.35rem}}.wwt-champion em{{color:#c4b5fd}}@keyframes float{{50%{{transform:translateY(-6px)}}}}
      @media(max-width:600px){{.wwt-stage{{padding:13px}}.wwt-round{{width:225px}}.wwt-brand{{align-items:start;flex-direction:column;gap:8px}}}}
    </style></head><body><main class="wwt-stage"><header class="wwt-brand"><div><small>WINNING WARS APRESENTA</small><h1>{escape(torneio['nome'])}</h1></div><div class="wwt-badge">{len(torneio['participantes'])} competidores · CV {torneio['cv']}</div></header><div class="wwt-bracket">{"".join(colunas)}</div>{trofeu}</main></body></html>'''


def renderizar(st, documentos, admin_usuario=None, carregar_torneio=None, salvar_torneio=None):
    import streamlit.components.v1 as components
    st.markdown("""
      <style>
        .wwt-hero{border:1px solid #7c3aed;border-radius:22px;padding:22px;background:radial-gradient(circle at 85% 0,#4c1d9555,transparent 42%),linear-gradient(145deg,#111827,#090b12);margin:8px 0 18px;box-shadow:0 18px 45px #0007}
        .wwt-kicker{color:#fbbf24;font-weight:900;letter-spacing:.18em;font-size:.72rem}.wwt-hero h1{margin:.25rem 0;font-size:clamp(2rem,5vw,4rem);line-height:.95;text-transform:uppercase}.wwt-hero p{color:#cbd5e1;max-width:760px}
        .wwt-roster{display:flex;gap:7px;flex-wrap:wrap}.wwt-chip{border:1px solid #475569;border-radius:999px;padding:5px 9px;color:#e2e8f0;background:#1e293b;font-size:.76rem}
      </style>
      <div class="wwt-hero"><div class="wwt-kicker">LIVE ARENA</div><h1>⚔️ Torneios Winning Wars</h1><p>Confrontos eliminatórios 1 × 1, da primeira batalha à grande final.</p></div>
    """, unsafe_allow_html=True)
    documento = documentos.get("torneio_roster")
    try:
        roster = validar_roster(documento)
    except ValueError as erro:
        st.warning(str(erro) + ". A Oracle fará uma nova leitura automaticamente.")
        return
    for conta in roster:
        conta["clan"] = documento["clan"]
        conta["clan_tag"] = documento["tag"]
    st.caption(f"Elenco: {documento['clan']} · {len(roster)} contas · atualizado em {documento['consultado_em']}")
    dist = {}
    for conta in roster:
        dist[conta["cv"]] = dist.get(conta["cv"], 0) + 1
    st.markdown('<div class="wwt-roster">' + ''.join(
        f'<span class="wwt-chip">CV {cv}: {qtd}</span>' for cv, qtd in sorted(dist.items(), reverse=True)
    ) + '</div>', unsafe_allow_html=True)

    torneio = carregar_torneio() if carregar_torneio else st.session_state.get(CHAVE_SESSAO)
    if torneio is None:
        if not admin_usuario:
            st.info("Entre como administrador no app principal para criar um torneio.")
            return
        with st.container(border=True):
            st.markdown("### Console do organizador")
            nome = st.text_input("Nome do torneio", "Torneio Winning Wars", max_chars=80)
            cvs = ["Todos"] + sorted(dist, reverse=True)
            cv = st.selectbox("Centro de Vila do torneio", cvs,
                              format_func=lambda valor: "Todos os CVs" if valor == "Todos" else f"Somente CV {valor}")
            elegiveis = [c for c in roster if cv == "Todos" or c["cv"] == cv]
            mapa = {c["tag"]: c for c in elegiveis}
            selecionadas = st.multiselect("Participantes do sorteio", list(mapa), default=list(mapa),
                format_func=lambda tag: f"{mapa[tag]['nome']} · CV {mapa[tag]['cv']} · {tag}")
            st.caption("O sorteio aceita de 2 a 32 contas. Quando necessário, algumas recebem folga na primeira fase.")
            if st.button("🎲 Sortear chaveamento", type="primary", use_container_width=True):
                novo = criar_torneio(nome, [mapa[t] for t in selecionadas], cv)
                if salvar_torneio:
                    salvar_torneio(novo)
                else:
                    st.session_state[CHAVE_SESSAO] = novo
                st.rerun()
        return

    altura = max(620, len(torneio["rodadas"][0]) * 128 + 190)
    components.html(html_chaveamento(torneio), height=min(1400, altura), scrolling=True)
    if torneio.get("campeao"):
        st.success(f"🏆 Campeão: {torneio['campeao']['nome']} · CV {torneio['campeao']['cv']}")
        st.balloons()

    if admin_usuario:
        with st.expander("🎛️ Console do organizador", expanded=torneio["status"] == "EM_ANDAMENTO"):
            st.caption("Os controles não aparecem dentro do quadro transmitido. Nenhuma credencial é exibida.")
            pendentes = partidas_pendentes(torneio)
            if pendentes:
                opcoes = [(ri, mi) for ri, mi, _ in pendentes]
                mapa_partidas = {(ri, mi): p for ri, mi, p in pendentes}
                escolha = st.selectbox("Partida concluída", opcoes, format_func=lambda chave:
                    f"{torneio['rotulos'][chave[0]]} · Jogo {chave[1]+1} · " +
                    " × ".join(p["nome"] for p in mapa_partidas[chave]["jogadores"]))
                jogadores = mapa_partidas[escolha]["jogadores"]
                vencedor = st.radio("Vencedor", [p["tag"] for p in jogadores], horizontal=True,
                                     format_func=lambda tag: next(p["nome"] for p in jogadores if p["tag"] == tag))
                if st.button("⚡ Confirmar vencedor e avançar", type="primary", use_container_width=True):
                    atualizado = selecionar_vencedor(torneio, escolha[0], escolha[1], vencedor)
                    if salvar_torneio:
                        salvar_torneio(atualizado)
                    else:
                        st.session_state[CHAVE_SESSAO] = atualizado
                    st.rerun()
            else:
                st.info("Não há partidas pendentes.")
            if st.button("↻ Encerrar torneio e criar outro", use_container_width=True):
                if salvar_torneio:
                    salvar_torneio(None)
                else:
                    st.session_state.pop(CHAVE_SESSAO, None)
                st.rerun()
    else:
        st.caption("Modo transmissão: somente nomes, CVs e resultados do chaveamento são exibidos.")
