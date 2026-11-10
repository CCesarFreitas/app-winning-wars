"""Escritas administrativas pequenas, auditadas e conferidas na planilha oficial."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import secrets
import subprocess
import sys
import threading
import time
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

# Os dominios usados pela plataforma independente ficam isolados dos motores
# de producao. Assim, uma atualizacao do painel nao muda o import dos servicos
# que processam guerras, Liga e raides.
_DOMINIOS = Path(os.environ.get(
    "WW_PLATAFORMA_DOMINIOS", "/opt/winning-wars-api/plataforma_dominios"
))
if _DOMINIOS.exists():
    sys.path.insert(0, str(_DOMINIOS))

from ww_competicao.manual import conferir, fotografar, preparar
from ww_competicao.participacao_competicao import (
    PC_ABA, pc_confirmar_evento, pc_preparar_alteracao,
)
from ww_competicao.torneios import criar_torneio, selecionar_vencedor

from .conteudo import CREDENCIAL_PADRAO, PLANILHA_PADRAO, invalidar_conteudo


_LOCK = threading.Lock()
_BACKUPS = Path(os.environ.get("WW_ADMIN_BACKUPS", "/opt/winning-wars-api/backups_admin_web"))
_LAYOUT_MAX_IMAGEM = 1_600_000
_LAYOUT_MAX_LOTE = 24_000_000
_SORTEIO_ABA = "SorteiosDesempate"
_SORTEIO_HEADER = [
    "SorteioID", "Temporada", "Ranking", "PontosEmpate",
    "ParticipantesJSON", "VencedoresJSON", "QuantidadeVencedores",
    "Administrador", "RealizadoEm", "Nonce", "Hash",
]
_MESES_PT = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


class LayoutDuplicadoError(ValueError):
    """Informa todos os itens do lote que ja constam na planilha."""

    def __init__(self, duplicados: list[dict[str, Any]]):
        super().__init__("Um ou mais layouts ja estao publicados")
        self.duplicados = duplicados


@lru_cache(maxsize=1)
def _planilha_escrita():
    import gspread
    from google.oauth2.service_account import Credentials

    creds = Credentials.from_service_account_file(
        os.environ.get("WW_GOOGLE_CREDENTIALS", CREDENCIAL_PADRAO),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return gspread.authorize(creds).open_by_key(
        os.environ.get("WW_GOOGLE_SHEET_ID", PLANILHA_PADRAO)
    )


def _backup(nome: str, dados: dict[str, Any]) -> str:
    _BACKUPS.mkdir(parents=True, exist_ok=True, mode=0o700)
    instante = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    destino = _BACKUPS / f"{nome}_{instante}.json"
    destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(destino, 0o600)
    return str(destino)


def _agendar_publicacao() -> None:
    programa = Path(os.environ.get(
        "WW_PUBLICADOR_CONSULTAS",
        "/opt/winning-wars-api/consultas_app_20261002/operacao/publicar_consultas.py",
    ))
    python = Path("/opt/winning-wars-api/venv/bin/python")
    if programa.exists() and python.exists():
        subprocess.Popen(
            [str(python), "-B", str(programa)], cwd="/opt/winning-wars-api",
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )


def _inteiro(valor: Any) -> int:
    try:
        return int(float(str(valor or 0).replace(",", ".")))
    except (TypeError, ValueError):
        return 0


def _registros(linhas: list[list[str]]) -> list[dict[str, str]]:
    if not linhas:
        return []
    cabecalho = [str(valor) for valor in linhas[0]]
    if not cabecalho or len(cabecalho) != len(set(cabecalho)):
        raise ValueError("Cabecalho ausente ou duplicado")
    return [dict(zip(cabecalho, [str(v) for v in linha]))
            for linha in linhas[1:] if any(str(v).strip() for v in linha)]


def _registrar_log(planilha, admin: str, acao: str, agora: str | None = None) -> None:
    aba = planilha.worksheet("Logs")
    linhas = aba.get_all_values(value_render_option="FORMULA")
    if not linhas or linhas[0] != ["DataHora", "Admin", "Acao"]:
        raise ValueError("Cabecalho de Logs divergente")
    aba.append_row([agora or datetime.now(timezone.utc).isoformat(), admin, acao],
                   value_input_option="RAW")


def _temporada_nome(temporada: str) -> str:
    try:
        ano, mes = [int(parte) for parte in temporada.split("-", 1)]
        if 1 <= mes <= 12:
            return f"{_MESES_PT[mes - 1]}/{ano}"
    except (TypeError, ValueError):
        pass
    raise ValueError("Temporada invalida")


def _proxima_temporada(temporada: str) -> str:
    ano, mes = [int(parte) for parte in temporada.split("-", 1)]
    return f"{ano + 1:04d}-01" if mes == 12 else f"{ano:04d}-{mes + 1:02d}"


def _estado(linhas: list[list[str]]) -> dict[str, str]:
    if not linhas or linhas[0] != ["Chave", "Valor"]:
        raise ValueError("Cabecalho de EstadoMes divergente")
    return {str(linha[0]).strip(): str(linha[1]).strip() if len(linha) > 1 else ""
            for linha in linhas[1:] if linha}


def _definir_estado(aba, chave: str, valor: str) -> None:
    linhas = aba.get_all_values(value_render_option="FORMULA")
    for numero, linha in enumerate(linhas[1:], 2):
        if linha and str(linha[0]).strip() == chave:
            aba.update_cell(numero, 2, str(valor))
            return
    aba.append_row([chave, str(valor)], value_input_option="RAW")


def _ranking_planilha(linhas: list[list[str]]) -> list[dict[str, Any]]:
    if not linhas or linhas[0][:2] != ["ID", "Nome"]:
        raise ValueError("Cabecalho do ranking atual divergente")
    cabecalho = linhas[0]
    atividades = [coluna for coluna in cabecalho if coluna in {"JogosCla", "Eventos"}
                  or coluna.startswith(("Guerra_", "Liga_", "Raide_"))]
    ranking = []
    for ordem, registro in enumerate(_registros(linhas)):
        if not str(registro.get("Nome", "")).strip():
            continue
        pontos = {coluna: _inteiro(registro.get(coluna)) for coluna in atividades}
        ranking.append({
            "id": str(registro.get("ID", "")).strip(),
            "nome": str(registro.get("Nome", "")).strip(),
            "total": sum(pontos.values()), "pontos": pontos,
            "ordem": ordem,
        })
    ranking.sort(key=lambda item: (-item["total"], item["ordem"]))
    for posicao, item in enumerate(ranking, 1):
        item["posicao"] = posicao
    return ranking


def _backup_planilha(planilha, admin: str, acao: str,
                     abas: list[tuple[str, Any]]) -> str:
    destino = planilha.worksheet("BackupsSeguranca")
    cabecalho = destino.row_values(1)
    esperado = ["BackupID", "DataHora", "Admin", "Acao", "Aba", "Parte", "ConteudoJSON"]
    if cabecalho != esperado:
        raise ValueError("Cabecalho de BackupsSeguranca divergente")
    agora = datetime.now(timezone.utc)
    backup_id = agora.strftime("BKP-WEB-%Y%m%d-%H%M%S-%f")
    linhas = []
    for nome, aba in abas:
        conteudo = json.dumps(
            aba.get_all_values(value_render_option="FORMULA"),
            ensure_ascii=False, separators=(",", ":"),
        )
        partes = [conteudo[i:i + 35000] for i in range(0, len(conteudo), 35000)] or ["[]"]
        linhas.extend([
            backup_id, agora.isoformat(), admin, acao, nome,
            f"{indice}/{len(partes)}", parte,
        ] for indice, parte in enumerate(partes, 1))
    destino.append_rows(linhas, value_input_option="RAW")
    finais = destino.get_all_values(value_render_option="FORMULA")
    gravadas = sum(len(linha) > 0 and linha[0] == backup_id for linha in finais[1:])
    if gravadas != len(linhas):
        raise RuntimeError("Backup de seguranca nao confirmado; operacao cancelada")
    return backup_id


def _url_layout_oficial(valor: str) -> str:
    url = str(valor or "").strip()
    parsed = urlparse(url)
    parametros = parse_qs(parsed.query)
    if (parsed.scheme != "https" or parsed.netloc.casefold() != "link.clashofclans.com"
            or parametros.get("action", [""])[0].casefold() != "openlayout"):
        raise ValueError("Use um link oficial de layout do Clash of Clans")
    return url


def _url_imagem(valor: str) -> str:
    url = str(valor or "").strip()
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL de imagem invalida")
    return url


def _decodificar_webp(valor: str) -> bytes:
    texto = str(valor or "").strip()
    if not texto:
        return b""
    try:
        dados = base64.b64decode(texto, validate=True)
    except (ValueError, binascii.Error) as erro:
        raise ValueError("Imagem WEBP invalida") from erro
    if len(dados) > _LAYOUT_MAX_IMAGEM:
        raise ValueError("Imagem otimizada excede 1,6 MB")
    if len(dados) < 16 or dados[:4] != b"RIFF" or dados[8:12] != b"WEBP":
        raise ValueError("Imagem enviada nao e WEBP")
    return dados


def _credenciais_cloudinary() -> tuple[str, str, str]:
    valores = (
        os.environ.get("WW_CLOUDINARY_CLOUD_NAME") or os.environ.get("CLOUDINARY_CLOUD_NAME"),
        os.environ.get("WW_CLOUDINARY_API_KEY") or os.environ.get("CLOUDINARY_API_KEY"),
        os.environ.get("WW_CLOUDINARY_API_SECRET") or os.environ.get("CLOUDINARY_API_SECRET"),
    )
    if not all(str(valor or "").strip() for valor in valores):
        raise RuntimeError("Cloudinary ainda nao configurado na Oracle")
    return tuple(str(valor).strip() for valor in valores)


def _upload_cloudinary(dados: bytes, tipo: str, cv: int) -> str:
    import requests

    cloud_name, api_key, api_secret = _credenciais_cloudinary()
    folder = f"winning-wars/layouts/{tipo.casefold()}/cv-{cv}"
    timestamp = int(time.time())
    parametros = {"folder": folder, "timestamp": timestamp}
    assinatura_texto = "&".join(
        f"{chave}={parametros[chave]}" for chave in sorted(parametros)
    ) + api_secret
    assinatura = hashlib.sha1(assinatura_texto.encode("utf-8")).hexdigest()
    try:
        resposta = requests.post(
            f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload",
            data={"api_key": api_key, "timestamp": str(timestamp),
                  "folder": folder, "signature": assinatura},
            files={"file": (f"layout-{uuid.uuid4().hex}.webp", dados, "image/webp")},
            timeout=45,
        )
        resposta.raise_for_status()
        url = str(resposta.json().get("secure_url", "")).strip()
    except requests.RequestException as erro:
        detalhe = ""
        try:
            detalhe = str(erro.response.json().get("error", {}).get("message", "")) if erro.response else ""
        except Exception:
            pass
        raise RuntimeError(f"Falha no upload ao Cloudinary{': ' + detalhe if detalhe else ''}") from erro
    if not url:
        raise RuntimeError("Cloudinary nao retornou URL segura")
    return url


def preparar_layouts_lote(admin: str, tipo: str, cv: int,
                           itens: list[dict[str, Any]], agora: str) -> list[dict[str, Any]]:
    if tipo not in {"Guerra", "Rankeada"} or type(cv) is not int or not 9 <= cv <= 18:
        raise ValueError("Tipo ou Centro de Vila invalido")
    if not 1 <= len(itens) <= 20:
        raise ValueError("O lote deve conter de 1 a 20 layouts")
    resultado, links, tamanho_total = [], set(), 0
    for indice, item in enumerate(itens, 1):
        link = _url_layout_oficial(item.get("link", ""))
        if link in links:
            raise ValueError(f"Link repetido no item {indice}")
        links.add(link)
        imagem = _decodificar_webp(item.get("imagem_base64", ""))
        tamanho_total += len(imagem)
        if tamanho_total > _LAYOUT_MAX_LOTE:
            raise ValueError("As imagens do lote excedem 24 MB apos a otimizacao")
        imagem_url = _url_imagem(item.get("imagem_url", ""))
        if imagem and imagem_url:
            raise ValueError(f"Item {indice} possui arquivo e URL de imagem")
        descricao = str(item.get("descricao", "")).strip()
        if len(descricao) > 500:
            raise ValueError(f"Descricao muito longa no item {indice}")
        resultado.append({
            "Tipo": tipo, "CV": f"CV {cv}", "Autor": admin,
            "Link": link, "Descricao": descricao, "ImagemUrl": imagem_url,
            "DataHora": agora, "Tag": "", "imagem": imagem,
        })
    return resultado


def publicar_layouts(admin: str, tipo: str, cv: int,
                      itens: list[dict[str, Any]]) -> dict[str, Any]:
    agora = datetime.now(timezone.utc).isoformat()
    preparados = preparar_layouts_lote(admin, tipo, cv, itens, agora)
    with _LOCK:
        planilha = _planilha_escrita()
        aba = planilha.worksheet("Layouts")
        logs = planilha.worksheet("Logs")
        linhas_antes = aba.get_all_values(value_render_option="FORMULA")
        logs_antes = logs.get_all_values(value_render_option="FORMULA")
        if not linhas_antes:
            raise ValueError("Cabecalho de Layouts ausente")
        cabecalho = linhas_antes[0]
        # A aba oficial criada pelo app anterior termina em DataHora. Algumas
        # planilhas de homologacao possuem tambem Tag; quando existir ela sera
        # preenchida, mas nunca deve impedir a publicacao na estrutura oficial.
        obrigatorias = {"Tipo", "CV", "Autor", "Link", "Descricao", "ImagemUrl", "DataHora"}
        if not obrigatorias.issubset(set(cabecalho)):
            raise ValueError("Cabecalho de Layouts divergente")
        indice_link = cabecalho.index("Link")
        existentes = {
            linha[indice_link].strip(): linha
            for linha in linhas_antes[1:]
            if len(linha) > indice_link and linha[indice_link].strip()
        }
        duplicados = []
        for indice_lote, item in enumerate(preparados, 1):
            linha = existentes.get(item["Link"])
            if not linha:
                continue
            registro = dict(zip(cabecalho, linha))
            duplicados.append({
                "linha_lote": indice_lote,
                "link": item["Link"],
                "tipo": registro.get("Tipo", ""),
                "cv": registro.get("CV", ""),
                "autor": registro.get("Autor", ""),
                "publicado_em": registro.get("DataHora", ""),
            })
        if duplicados:
            raise LayoutDuplicadoError(duplicados)
        backup = _backup("layouts", {
            "aba": "Layouts", "linhas": linhas_antes,
            "logs": logs_antes, "tipo": tipo, "cv": cv,
        })
        for item in preparados:
            imagem = item.pop("imagem")
            if imagem:
                item["ImagemUrl"] = _upload_cloudinary(imagem, tipo, cv)
        linhas = [[item.get(coluna, "") for coluna in cabecalho] for item in preparados]
        aba.append_rows(linhas, value_input_option="RAW")
        if logs_antes:
            cabecalho_logs = logs_antes[0]
            registros_logs = []
            for item in preparados:
                registro = {
                    "DataHora": agora, "Admin": admin,
                    "Acao": f"Adicionou layout {tipo} para CV {cv}",
                }
                registros_logs.append([registro.get(coluna, "") for coluna in cabecalho_logs])
            logs.append_rows(registros_logs, value_input_option="RAW")
        finais = aba.get_all_values(value_render_option="FORMULA")
        registros_finais = {
            linha[cabecalho.index("Link")]: linha
            for linha in finais[1:]
            if len(linha) > cabecalho.index("Link")
        }
        if any(item["Link"] not in registros_finais for item in preparados):
            raise RuntimeError("Layouts enviados, mas a conferencia falhou; nao repetir automaticamente")
        invalidar_conteudo("Layouts")
        return {
            "status": "APLICADO_E_CONFERIDO", "aplicados": len(preparados),
            "tipo": tipo, "cv": cv, "backup": backup,
            "layouts": [{chave: valor for chave, valor in item.items() if chave != "imagem"}
                        for item in preparados],
        }


def excluir_layout(admin: str, link: str, tipo: str, cv: int) -> dict[str, Any]:
    """Remove da planilha todas as linhas do link, preservando a imagem externa."""
    link_validado = _url_layout_oficial(link)
    if tipo not in {"Guerra", "Rankeada"} or type(cv) is not int or not 9 <= cv <= 18:
        raise ValueError("Tipo ou Centro de Vila invalido")
    with _LOCK:
        planilha = _planilha_escrita()
        aba = planilha.worksheet("Layouts")
        logs = planilha.worksheet("Logs")
        linhas_antes = aba.get_all_values(value_render_option="FORMULA")
        logs_antes = logs.get_all_values(value_render_option="FORMULA")
        if not linhas_antes or "Link" not in linhas_antes[0]:
            raise ValueError("Cabecalho de Layouts divergente")
        cabecalho = linhas_antes[0]
        indice_link = cabecalho.index("Link")
        correspondencias = []
        for numero_linha, linha in enumerate(linhas_antes[1:], 2):
            if len(linha) <= indice_link or linha[indice_link].strip() != link_validado:
                continue
            registro = dict(zip(cabecalho, linha))
            if registro.get("Tipo", "").strip() != tipo or registro.get("CV", "").strip() != f"CV {cv}":
                raise ValueError("Layout localizado em outra categoria ou Centro de Vila")
            correspondencias.append((numero_linha, registro))
        if not correspondencias:
            raise ValueError("Layout nao encontrado ou ja removido")
        backup = _backup("excluir_layout", {
            "aba": "Layouts", "linhas": linhas_antes, "logs": logs_antes,
            "link": link_validado, "tipo": tipo, "cv": cv,
        })
        for numero_linha, _registro in reversed(correspondencias):
            aba.delete_rows(numero_linha)
        agora = datetime.now(timezone.utc).isoformat()
        if logs_antes:
            cabecalho_logs = logs_antes[0]
            registro_log = {
                "DataHora": agora, "Admin": admin,
                "Acao": f"Excluiu layout {tipo} de CV {cv} ({len(correspondencias)} linha(s))",
            }
            logs.append_rows([[registro_log.get(coluna, "") for coluna in cabecalho_logs]], value_input_option="RAW")
        finais = aba.get_all_values(value_render_option="FORMULA")
        if any(len(linha) > indice_link and linha[indice_link].strip() == link_validado for linha in finais[1:]):
            raise RuntimeError("Layout removido parcialmente; confira a planilha antes de repetir")
        invalidar_conteudo("Layouts")
        return {
            "status": "REMOVIDO_E_CONFERIDO", "removidos": len(correspondencias),
            "link": link_validado, "tipo": tipo, "cv": cv, "backup": backup,
            "imagem_externa_preservada": True,
        }


def alterar_participacao(admin: str, tag: str, habilitada: bool, motivo: str,
                         evento_anterior: str) -> dict[str, Any]:
    with _LOCK:
        planilha = _planilha_escrita()
        aba = planilha.worksheet(PC_ABA)
        linhas = aba.get_all_values(value_render_option="FORMULA")
        admins = planilha.worksheet("Admins").get_all_values(value_render_option="FORMULA")
        agora = datetime.now(timezone.utc).isoformat()
        evento_id = str(uuid.uuid4())
        linha = pc_preparar_alteracao(
            linhas, admins, admin, tag, habilitada, motivo, evento_anterior,
            evento_id, agora,
        )
        backup = _backup("participacao", {"aba": PC_ABA, "linhas": linhas})
        aba.append_row(linha, value_input_option="RAW")
        conferido = aba.get_all_values(value_render_option="FORMULA")
        if not pc_confirmar_evento(conferido, linha):
            raise RuntimeError("Alteracao enviada, mas ainda nao confirmada; nao repetir automaticamente")
        invalidar_conteudo("ParticipacaoCompeticao")
        _agendar_publicacao()
        return {
            "status": "APLICADO_E_CONFERIDO", "tag": linha[1],
            "habilitada": linha[3] == "TRUE", "evento_id": evento_id,
            "backup": backup,
        }


def _ranking_atual(planilha) -> str:
    # Página1 é o contrato estável usado também pelo publicador oficial. As
    # abas históricas nunca são selecionadas por semelhança de cabeçalho.
    aba = planilha.worksheet("Página1")
    cabecalho = aba.row_values(1)
    if not {"ID", "Nome", "JogosCla", "Eventos"}.issubset(set(cabecalho)):
        raise ValueError("Cabecalho do ranking atual divergente")
    return aba.title


def _aplicar_virtual(virtual: dict[str, Any], capacidades: dict[str, Any], proposta: dict[str, Any]) -> None:
    novas = json.loads(proposta["registro"][10])["novas_linhas"]
    for nome, linhas in novas.items():
        for modo in ("valores", "formulas"):
            virtual[nome][modo].extend([[str(valor) for valor in linha] for linha in linhas])
    for modo in ("valores", "formulas"):
        ranking = virtual["ranking"][modo]
        coluna = ranking[0].index(proposta["atividade"])
        linha = next(registro for registro in ranking[1:] if str(registro[0]) == proposta["id"])
        linha.extend([""] * max(0, coluna + 1 - len(linha)))
        linha[coluna] = str(proposta["pontos"])
        virtual["manual"][modo].append(proposta["registro"][:])
    for pedido in proposta["lote"]["requests"]:
        if "addSheet" in pedido:
            capacidades["manual"]["nova"] = False
        if "appendDimension" in pedido:
            dimensao = pedido["appendDimension"]
            for meta in capacidades.values():
                if meta["id"] == dimensao["sheetId"]:
                    meta["linhas"] += dimensao["length"]


def aplicar_lancamentos(admin: str, atividade: str,
                        entradas: list[dict[str, Any]]) -> dict[str, Any]:
    if atividade not in {"JogosCla", "Eventos"} or not 1 <= len(entradas) <= 50:
        raise ValueError("Lote manual invalido")
    tags = [str(item.get("tag", "")).strip().upper() for item in entradas]
    if len(tags) != len(set(tags)):
        raise ValueError("Conta repetida no lote")
    with _LOCK:
        planilha = _planilha_escrita()
        ranking_titulo = _ranking_atual(planilha)
        foto, metas = fotografar(planilha, ranking_titulo)
        virtual, capacidades = deepcopy(foto), deepcopy(metas)
        propostas, ignorados, pedidos = [], [], []
        agora = datetime.now(timezone.utc).isoformat()
        for entrada in entradas:
            valor = entrada.get("valor")
            if type(valor) is not int:
                raise ValueError("Use somente valores inteiros")
            proposta = preparar(
                virtual, capacidades, admin, str(entrada["tag"]),
                str(entrada["nome"]), atividade, valor, str(uuid.uuid4()), agora,
            )
            if proposta["status"] == "ZERO_SEM_INSCRICAO":
                ignorados.append(entrada)
                continue
            propostas.append(proposta)
            pedidos.extend(proposta["lote"]["requests"])
            _aplicar_virtual(virtual, capacidades, proposta)
        if not propostas:
            return {"status": "SEM_ALTERACOES", "aplicados": 0, "ignorados": len(ignorados)}
        backup = _backup("lancamentos_manuais", {
            "ranking": ranking_titulo, "atividade": atividade,
            "abas": {nome: dados["formulas"] for nome, dados in foto.items()},
        })
        planilha.batch_update({"requests": pedidos})
        foto_final, _ = fotografar(planilha, ranking_titulo)
        for proposta in propostas:
            conferir(foto_final, proposta)
        invalidar_conteudo()
        _agendar_publicacao()
        return {
            "status": "APLICADO_E_CONFERIDO", "atividade": atividade,
            "aplicados": len(propostas), "ignorados": len(ignorados),
            "backup": backup,
            "resultados": [{"tag": p["tag"], "antes": p["antes"], "depois": p["pontos"]} for p in propostas],
        }


def _salvar_torneio(admin: str, torneio: dict[str, Any] | None) -> dict[str, Any]:
    planilha = _planilha_escrita()
    aba = planilha.worksheet("Torneios")
    linhas = aba.get_all_values(value_render_option="FORMULA")
    backup = _backup("torneio", {"aba": "Torneios", "linhas": linhas})
    agora = datetime.now(timezone.utc).isoformat()
    if torneio is None:
        conteudo = {"status": "SEM_TORNEIO"}
        linha = ["", agora, admin, "SEM_TORNEIO", json.dumps(conteudo, separators=(",", ":"))]
    else:
        conteudo = torneio
        linha = [str(conteudo.get("criado_em", "")), agora, admin,
                 str(conteudo.get("status", "EM_ANDAMENTO")),
                 json.dumps(conteudo, ensure_ascii=False, separators=(",", ":"))]
    aba.append_row(linha, value_input_option="RAW")
    finais = aba.get_all_values(value_render_option="FORMULA")
    if not finais or finais[-1] != linha:
        raise RuntimeError("Torneio enviado, mas ainda nao confirmado; nao repetir automaticamente")
    invalidar_conteudo("Torneios")
    return {"status": "APLICADO_E_CONFERIDO", "torneio": torneio, "backup": backup}


def iniciar_torneio(admin: str, roster: dict[str, Any], nome: str, modo: str,
                     cv: int | str, tags: list[str]) -> dict[str, Any]:
    if roster.get("tag") != "#2CY88CCYU":
        raise ValueError("Elenco oficial do TorneiosWWars indisponivel")
    mapa = {conta["tag"]: conta for conta in roster.get("contas", [])}
    if len(tags) != len(set(tags)) or not 2 <= len(tags) <= 32 or any(tag not in mapa for tag in tags):
        raise ValueError("Selecao de participantes invalida")
    participantes = [{**mapa[tag], "clan": roster.get("clan", "TorneiosWWars"),
                      "clan_tag": roster["tag"]} for tag in tags]
    torneio = criar_torneio(nome, participantes, cv, modo=modo)
    with _LOCK:
        return _salvar_torneio(admin, torneio)


def avancar_torneio(admin: str, torneio: dict[str, Any], rodada: int,
                     partida: int, vencedor: str) -> dict[str, Any]:
    atualizado = selecionar_vencedor(torneio, rodada, partida, vencedor)
    with _LOCK:
        return _salvar_torneio(admin, atualizado)


def encerrar_torneio(admin: str) -> dict[str, Any]:
    with _LOCK:
        return _salvar_torneio(admin, None)


def _hash_sorteio(valores: list[str]) -> str:
    texto = json.dumps(valores, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _aba_sorteios(planilha, criar: bool = False):
    try:
        aba = planilha.worksheet(_SORTEIO_ABA)
    except Exception as erro:
        if not criar or erro.__class__.__name__ != "WorksheetNotFound":
            if not criar and erro.__class__.__name__ == "WorksheetNotFound":
                return None
            raise
        aba = planilha.add_worksheet(title=_SORTEIO_ABA, rows=500, cols=len(_SORTEIO_HEADER))
        aba.append_row(_SORTEIO_HEADER, value_input_option="RAW")
    linhas = aba.get_all_values(value_render_option="FORMULA")
    if not linhas or linhas[0] != _SORTEIO_HEADER:
        raise ValueError("Cabecalho de SorteiosDesempate divergente")
    return aba


def listar_sorteios_desempate(temporada: str | None = None,
                              ranking: str | None = None) -> list[dict[str, Any]]:
    planilha = _planilha_escrita()
    aba = _aba_sorteios(planilha, criar=False)
    if aba is None:
        return []
    resultado = []
    for registro in _registros(aba.get_all_values(value_render_option="FORMULA")):
        valores = [registro.get(coluna, "") for coluna in _SORTEIO_HEADER[:-1]]
        if registro.get("Hash") != _hash_sorteio(valores):
            raise ValueError("Auditoria de sorteio com hash divergente")
        if temporada and registro.get("Temporada") != temporada:
            continue
        if ranking and registro.get("Ranking") != ranking:
            continue
        try:
            participantes = json.loads(registro["ParticipantesJSON"])
            vencedores = json.loads(registro["VencedoresJSON"])
        except json.JSONDecodeError as erro:
            raise ValueError("Auditoria de sorteio invalida") from erro
        resultado.append({
            "sorteio_id": registro["SorteioID"],
            "temporada": registro["Temporada"], "ranking": registro["Ranking"],
            "pontos": _inteiro(registro["PontosEmpate"]),
            "participantes": participantes, "vencedores": vencedores,
            "quantidade_vencedores": _inteiro(registro["QuantidadeVencedores"]),
            "administrador": registro["Administrador"],
            "realizado_em": registro["RealizadoEm"], "hash": registro["Hash"],
        })
    return list(reversed(resultado[-50:]))


def sortear_desempate(admin: str, temporada: str, ranking_tipo: str,
                      pontos: int, participantes_esperados: list[str],
                      quantidade: int, sorteio_id: str,
                      ranking_atual: list[dict[str, Any]]) -> dict[str, Any]:
    if ranking_tipo not in {"oficial", "sem_liga"}:
        raise ValueError("Ranking de sorteio invalido")
    if not sorteio_id or len(sorteio_id) > 100:
        raise ValueError("Identificador de sorteio invalido")
    grupo = [jogador for jogador in ranking_atual if _inteiro(jogador.get("total")) == pontos]
    tags = sorted(str(jogador.get("tag", "")).strip().upper() for jogador in grupo)
    esperadas = sorted(str(tag).strip().upper() for tag in participantes_esperados)
    if len(grupo) < 2 or tags != esperadas or len(tags) != len(set(tags)):
        raise ValueError("O empate mudou; atualize a pagina antes do sorteio")
    if type(quantidade) is not int or not 1 <= quantidade < len(grupo):
        raise ValueError("Quantidade de vencedores invalida")
    participantes = [{
        "tag": str(jogador.get("tag", "")).strip().upper(),
        "nome": str(jogador.get("nome", "")).strip(),
        "pontos": pontos,
    } for jogador in grupo]

    with _LOCK:
        planilha = _planilha_escrita()
        aba = _aba_sorteios(planilha, criar=True)
        existentes = listar_sorteios_desempate(temporada, ranking_tipo)
        repetido = next((item for item in existentes if item["sorteio_id"] == sorteio_id), None)
        if repetido:
            return {"status": "JA_REALIZADO", **repetido}
        anterior = next((item for item in existentes if item["pontos"] == pontos), None)
        if anterior:
            return {"status": "JA_REALIZADO", **anterior}

        linhas_antes = aba.get_all_values(value_render_option="FORMULA")
        logs = planilha.worksheet("Logs")
        logs_antes = logs.get_all_values(value_render_option="FORMULA")
        backup = _backup("sorteio_desempate", {
            "aba": _SORTEIO_ABA, "linhas": linhas_antes,
            "logs": logs_antes, "temporada": temporada,
            "ranking": ranking_tipo, "pontos": pontos,
        })
        vencedores = secrets.SystemRandom().sample(participantes, quantidade)
        realizado_em = datetime.now(timezone.utc).isoformat()
        nonce = secrets.token_hex(16)
        valores = [
            sorteio_id, temporada, ranking_tipo, str(pontos),
            json.dumps(participantes, ensure_ascii=False, separators=(",", ":")),
            json.dumps(vencedores, ensure_ascii=False, separators=(",", ":")),
            str(quantidade), admin, realizado_em, nonce,
        ]
        hash_auditoria = _hash_sorteio(valores)
        linha = valores + [hash_auditoria]
        aba.append_row(linha, value_input_option="RAW")
        _registrar_log(
            planilha, admin,
            f"Sorteio {ranking_tipo} {temporada} entre {', '.join(j['nome'] for j in participantes)}; "
            f"vencedor(es): {', '.join(j['nome'] for j in vencedores)}; hash {hash_auditoria[:12].upper()}",
            realizado_em,
        )
        finais = aba.get_all_values(value_render_option="FORMULA")
        if not any(linha_final and linha_final[0] == sorteio_id
                   and len(linha_final) >= len(_SORTEIO_HEADER)
                   and linha_final[-1] == hash_auditoria for linha_final in finais[1:]):
            raise RuntimeError("Sorteio registrado, mas a auditoria nao foi confirmada; nao repetir")
        return {
            "status": "SORTEADO_E_AUDITADO", "sorteio_id": sorteio_id,
            "temporada": temporada, "ranking": ranking_tipo, "pontos": pontos,
            "participantes": participantes, "vencedores": vencedores,
            "quantidade_vencedores": quantidade, "administrador": admin,
            "realizado_em": realizado_em, "hash": hash_auditoria,
            "backup": backup,
        }


def _upsert_temporada(aba, temporada: str, nome: str, status: str, *,
                      aberta_em: str = "", fechada_em: str = "", admin: str = "",
                      ranking: list[dict[str, Any]] | None = None,
                      observacao: str = "") -> None:
    # IDs como 2026-11 foram historicamente gravados com USER_ENTERED e o
    # Sheets os armazena como datas. O valor formatado preserva o contrato.
    linhas = aba.get_all_values()
    esperado = [
        "TemporadaID", "MesAno", "Status", "AbertaEm", "FechadaEm",
        "AdminFechamento", "Primeiro", "Segundo", "Terceiro",
        "QtdJogadores", "Observacao",
    ]
    if not linhas or linhas[0] != esperado:
        raise ValueError("Cabecalho de Temporadas divergente")
    ranking = ranking or []
    nomes = [ranking[i]["nome"] if i < len(ranking) else "-" for i in range(3)]
    novo = [temporada, nome, status, aberta_em, fechada_em, admin,
            *nomes, str(len(ranking)), observacao]
    for numero, linha in enumerate(linhas[1:], 2):
        if linha and linha[0] == temporada:
            atual = linha + [""] * (len(esperado) - len(linha))
            for indice in (3, 4, 5):
                if not novo[indice]:
                    novo[indice] = atual[indice]
            aba.update(f"A{numero}:K{numero}", [novo], value_input_option="RAW")
            return
    aba.append_row(novo, value_input_option="RAW")


def obter_fechamento_mensal() -> dict[str, Any]:
    planilha = _planilha_escrita()
    ranking_aba = planilha.worksheet("Página1")
    estado_aba = planilha.worksheet("EstadoMes")
    historico = planilha.worksheet("HistoricoMensal").get_all_values()
    estado = _estado(estado_aba.get_all_values())
    temporada = estado.get("temporada_atual_id", "")
    nome = estado.get("temporada_atual_nome", "") or _temporada_nome(temporada)
    ranking = _ranking_planilha(ranking_aba.get_all_values(value_render_option="FORMULA"))
    arquivado = any(registro.get("TemporadaID") == temporada for registro in _registros(historico))
    return {
        "temporada": temporada, "temporada_nome": nome,
        "mes_finalizado": estado.get("mes_finalizado", "").upper() == "TRUE",
        "ultimo_fechamento": estado.get("ultimo_fechamento", ""),
        "arquivo_confirmado": arquivado, "total_jogadores": len(ranking),
        "podio": ranking[:3], "proxima_temporada": _proxima_temporada(temporada),
        "proxima_temporada_nome": _temporada_nome(_proxima_temporada(temporada)),
    }


def finalizar_mes(admin: str, temporada_esperada: str, confirmacao: str) -> dict[str, Any]:
    if confirmacao != f"FINALIZAR {temporada_esperada}":
        raise ValueError("Confirmacao de fechamento invalida")
    with _LOCK:
        planilha = _planilha_escrita()
        ranking_aba = planilha.worksheet("Página1")
        estado_aba = planilha.worksheet("EstadoMes")
        fama = planilha.worksheet("GaleriaFama")
        mensal = planilha.worksheet("HistoricoMensal")
        temporadas = planilha.worksheet("Temporadas")
        historico = planilha.worksheet("Historico")
        logs = planilha.worksheet("Logs")
        estado = _estado(estado_aba.get_all_values())
        temporada = estado.get("temporada_atual_id", "")
        nome = estado.get("temporada_atual_nome", "") or _temporada_nome(temporada)
        if temporada != temporada_esperada:
            raise ValueError("A temporada mudou; atualize a pagina")
        if estado.get("mes_finalizado", "").upper() == "TRUE":
            return {"status": "JA_FINALIZADO", **obter_fechamento_mensal()}
        ranking_linhas = ranking_aba.get_all_values(value_render_option="FORMULA")
        ranking = _ranking_planilha(ranking_linhas)
        if not ranking:
            raise ValueError("Nao ha ranking para finalizar")
        abas_backup = [(aba.title, aba) for aba in (
            ranking_aba, estado_aba, fama, mensal, temporadas, historico, logs,
        )]
        backup_local = _backup("fechamento_mensal", {
            nome_aba: aba.get_all_values(value_render_option="FORMULA")
            for nome_aba, aba in abas_backup
        })
        backup_planilha = _backup_planilha(
            planilha, admin, f"Fechamento mensal {nome}", abas_backup,
        )
        agora = datetime.now(timezone.utc).isoformat()
        atividades = [coluna for coluna in ranking_linhas[0]
                      if coluna in {"JogosCla", "Eventos"}
                      or coluna.startswith(("Guerra_", "Liga_", "Raide_"))]
        existentes_mensal = _registros(mensal.get_all_values())
        if not any(registro.get("TemporadaID") == temporada for registro in existentes_mensal):
            linhas_mensais = []
            for jogador in ranking:
                pontos = jogador["pontos"]
                detalhes = {"ID": jogador["id"], "Nome": jogador["nome"],
                            **{coluna: pontos.get(coluna, 0) for coluna in atividades}}
                linhas_mensais.append([
                    temporada, nome, agora, jogador["id"], jogador["nome"],
                    jogador["posicao"], pontos.get("JogosCla", 0), pontos.get("Eventos", 0),
                    sum(valor for coluna, valor in pontos.items() if coluna.startswith("Guerra_")),
                    sum(valor for coluna, valor in pontos.items() if coluna.startswith("Liga_")),
                    sum(valor for coluna, valor in pontos.items() if coluna.startswith("Raide_")),
                    jogador["total"], json.dumps(detalhes, ensure_ascii=False, separators=(",", ":")),
                ])
            mensal.append_rows(linhas_mensais, value_input_option="RAW")
        existentes_historico = _registros(historico.get_all_values())
        if not any(registro.get("Temporada") == nome and registro.get("Tipo") == "fechamento"
                   for registro in existentes_historico):
            historico.append_rows([
                [agora, nome, jogador["nome"], jogador["total"], jogador["posicao"],
                 "fechamento", "Ranking final mensal"] for jogador in ranking
            ], value_input_option="RAW")
        registros_fama = _registros(fama.get_all_values())
        if not any(registro.get("MesAno") == nome for registro in registros_fama):
            vencedores = [ranking[i]["nome"] if i < len(ranking) else "-" for i in range(3)]
            fama.append_row([nome, *vencedores], value_input_option="RAW")
        _upsert_temporada(
            temporadas, temporada, nome, "Fechada", fechada_em=agora,
            admin=admin, ranking=ranking,
            observacao="Fechamento mensal pelo painel web administrativo",
        )
        _definir_estado(estado_aba, "mes_finalizado", "TRUE")
        _definir_estado(estado_aba, "ultima_temporada_fechada_id", temporada)
        _definir_estado(estado_aba, "ultima_temporada_fechada_nome", nome)
        _definir_estado(estado_aba, "ultimo_fechamento", agora)
        _registrar_log(planilha, admin, f"Finalizou o mes {nome}, arquivou dados e registrou campeoes", agora)
        estado_final = _estado(estado_aba.get_all_values())
        arquivo_final = _registros(mensal.get_all_values())
        if (estado_final.get("mes_finalizado") != "TRUE"
                or not any(item.get("TemporadaID") == temporada for item in arquivo_final)):
            raise RuntimeError("Fechamento parcialmente aplicado; confira a planilha antes de repetir")
        invalidar_conteudo()
        _agendar_publicacao()
        return {
            "status": "FINALIZADO_E_CONFERIDO", "temporada": temporada,
            "temporada_nome": nome, "fechado_em": agora,
            "backup": backup_local, "backup_planilha": backup_planilha,
        }


def iniciar_proximo_mes(admin: str, temporada_esperada: str,
                        confirmacao: str) -> dict[str, Any]:
    proxima = _proxima_temporada(temporada_esperada)
    if confirmacao != f"ABRIR {proxima}":
        raise ValueError("Confirmacao da nova temporada invalida")
    with _LOCK:
        planilha = _planilha_escrita()
        ranking_aba = planilha.worksheet("Página1")
        estado_aba = planilha.worksheet("EstadoMes")
        mensal = planilha.worksheet("HistoricoMensal")
        temporadas = planilha.worksheet("Temporadas")
        logs = planilha.worksheet("Logs")
        estado = _estado(estado_aba.get_all_values())
        temporada = estado.get("temporada_atual_id", "")
        if temporada != temporada_esperada:
            raise ValueError("A temporada mudou; atualize a pagina")
        if estado.get("mes_finalizado", "").upper() != "TRUE":
            raise ValueError("Finalize e arquive o mes atual antes de abrir o proximo")
        if not any(item.get("TemporadaID") == temporada
                   for item in _registros(mensal.get_all_values())):
            raise ValueError("Arquivo historico nao confirmado; abertura bloqueada")
        abas_backup = [(aba.title, aba) for aba in (ranking_aba, estado_aba, temporadas, logs)]
        backup_local = _backup("iniciar_temporada", {
            nome: aba.get_all_values(value_render_option="FORMULA") for nome, aba in abas_backup
        })
        backup_planilha = _backup_planilha(
            planilha, admin, f"Iniciar temporada {proxima}", abas_backup,
        )
        ranking_aba.clear()
        ranking_aba.resize(rows=100, cols=4)
        ranking_aba.update("A1:D1", [["ID", "Nome", "JogosCla", "Eventos"]],
                           value_input_option="RAW")
        agora = datetime.now(timezone.utc).isoformat()
        nome_novo = _temporada_nome(proxima)
        _definir_estado(estado_aba, "temporada_atual_id", proxima)
        _definir_estado(estado_aba, "temporada_atual_nome", nome_novo)
        _definir_estado(estado_aba, "mes_finalizado", "FALSE")
        _upsert_temporada(
            temporadas, proxima, nome_novo, "Aberta", aberta_em=agora,
            observacao=f"Iniciada apos o fechamento de {temporada_esperada}",
        )
        _registrar_log(planilha, admin, f"Iniciou a nova temporada {nome_novo}; area de pontuacao renovada", agora)
        estado_final = _estado(estado_aba.get_all_values())
        cabecalho_final = ranking_aba.row_values(1)
        if (estado_final.get("temporada_atual_id") != proxima
                or estado_final.get("mes_finalizado") != "FALSE"
                or cabecalho_final != ["ID", "Nome", "JogosCla", "Eventos"]):
            raise RuntimeError("Nova temporada parcialmente aplicada; confira a planilha antes de repetir")
        invalidar_conteudo()
        _agendar_publicacao()
        return {
            "status": "NOVA_TEMPORADA_ABERTA_E_CONFERIDA",
            "temporada": proxima, "temporada_nome": nome_novo,
            "aberta_em": agora, "backup": backup_local,
            "backup_planilha": backup_planilha,
        }
