"""Classificacao somente leitura da presenca das contas da competicao."""
from datetime import datetime


def visivel_no_ranking(participante_id, vinculos_por_id, participacao):
    """Oculta somente bloqueios explícitos, preservando falhas antigas de vínculo."""
    tag = vinculos_por_id.get(str(participante_id).strip())
    return participacao.get(tag, {}).get("Habilitada") != "FALSE"


def _registros(linhas):
    if not linhas:
        return []
    return [dict(zip(linhas[0], linha)) for linha in linhas[1:] if any(linha)]


def _inteiro(valor):
    try:
        return int(float(str(valor).replace(",", ".")))
    except (TypeError, ValueError):
        return 0


def _instante(foto, registrado_em):
    valor = foto.get("consultado_em") or registrado_em
    return datetime.fromisoformat(valor).isoformat()


def montar(temporada, ranking_linhas, vinculos, inscritos, participacao,
           roster_atual, versoes_roster, consultado_em):
    """Monta a fila administrativa sem decidir elegibilidade automaticamente.

    ``versoes_roster`` contem pares ``(conteudo, registrado_em)`` em ordem
    cronologica. A ausência atual é um alerta; somente uma decisão ADMIN pode
    bloquear a conta e preservar a regra de contas temporárias e secundárias.
    """
    fotos = []
    for foto, registrado_em in versoes_roster:
        contas = foto.get("contas", [])
        tags = {m.get("tag") for m in contas if m.get("tag")}
        fotos.append((_instante(foto, registrado_em), tags))

    primeira_foto = fotos[0][0] if fotos else None
    primeira_vista = {}
    ultima_vista = {}
    retornou = set()
    ja_vista = set()
    ausente_depois = set()
    for instante, tags in fotos:
        for tag in tags:
            primeira_vista.setdefault(tag, instante)
            ultima_vista[tag] = instante
            if tag in ausente_depois:
                retornou.add(tag)
            ja_vista.add(tag)
        ausente_depois.update(ja_vista - tags)

    membros = {m["tag"]: m for m in (roster_atual or {}).get("contas", [])}
    tag_por_id = {r.get("ParticipanteID", ""): r.get("PlayerTag", "")
                  for r in _registros(vinculos)}
    ranking_por_tag = {}
    if ranking_linhas:
        cabecalho = ranking_linhas[0]
        atividades = [c for c in cabecalho[2:]
                      if c not in {"Total", "Posição", "Posicao", "WarTotal"}]
        for r in _registros(ranking_linhas):
            pid = str(r.get("ID", r.get("ParticipanteID", ""))).strip()
            tag = tag_por_id.get(pid)
            if not tag:
                continue
            pontos = (_inteiro(r.get("Total")) if "Total" in r
                      else sum(_inteiro(r.get(c)) for c in atividades))
            ranking_por_tag[tag] = {"pontos": pontos, "nome_ranking": r.get("Nome", "")}

    tags = set(participacao) | set(ranking_por_tag)
    contas = []
    for tag in tags:
        decisao = participacao.get(tag, {})
        no_cla = tag in membros
        primeira = primeira_vista.get(tag)
        if no_cla and tag in retornou:
            situacao = "RETORNOU_AO_CLA"
        elif no_cla and primeira and primeira_foto and primeira > primeira_foto:
            situacao = "ENTROU_APOS_INICIO_DO_HISTORICO"
        elif no_cla:
            situacao = "MEMBRO_ATUAL"
        elif tag in primeira_vista:
            situacao = "AUSENTE_AGORA"
        else:
            situacao = "SEM_REGISTRO_NO_CLA"
        contas.append({
            "tag": tag,
            "nome": (decisao.get("Nome") or ranking_por_tag.get(tag, {}).get("nome_ranking")
                     or membros.get(tag, {}).get("nome") or ""),
            "pontos": ranking_por_tag.get(tag, {}).get("pontos", 0),
            "inscrita": tag in inscritos,
            "habilitada": decisao.get("Habilitada"),
            "origem_decisao": decisao.get("Origem"),
            "situacao": situacao,
            "no_cla": no_cla,
            "primeira_vista": primeira,
            "ultima_vista": ultima_vista.get(tag),
        })
    contas.sort(key=lambda c: (c["no_cla"], c["habilitada"] != "TRUE",
                               -c["pontos"], c["nome"].casefold(), c["tag"]))
    return {
        "consultado_em": consultado_em,
        "temporada": temporada,
        "historico_desde": primeira_foto,
        "criterio": "A ausência gera revisão; somente decisão administrativa bloqueia a conta.",
        "contas": contas,
    }
