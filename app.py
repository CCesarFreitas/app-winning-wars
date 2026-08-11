import hashlib
import hmac
import os
import json
import random
import re
import time
from datetime import datetime
import gspread
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Winning Wars APP", page_icon="https://i.ibb.co/YFV3LGy5/winningwars-ico.png", layout="wide"
)

# --- ÍCONE PARA IPHONE / IPAD (ADICIONAR À TELA DE INÍCIO) ---
# O iOS/Safari usa apple-touch-icon, que é diferente do favicon/page_icon.
_APP_ICON_URL = "https://i.ibb.co/YFV3LGy5/winningwars-ico.png"

st.markdown(
    f'<link rel="apple-touch-icon" sizes="180x180" href="{_APP_ICON_URL}">',
    unsafe_allow_html=True,
)

# Injeta o Apple Touch Icon também no <head> da página principal do Streamlit.
# Isso melhora a compatibilidade do atalho criado pelo Safari no iPhone/iPad.
components.html(
    f"""
    <script>
    (function() {{
        try {{
            const doc = window.parent.document;
            const iconUrl = {repr('https://i.ibb.co/YFV3LGy5/winningwars-ico.png')};

            let touchIcon = doc.querySelector('link[rel="apple-touch-icon"]');
            if (!touchIcon) {{
                touchIcon = doc.createElement('link');
                touchIcon.rel = 'apple-touch-icon';
                touchIcon.sizes = '180x180';
                doc.head.appendChild(touchIcon);
            }}
            touchIcon.href = iconUrl;

            let favicon = doc.querySelector('link[rel="icon"]');
            if (!favicon) {{
                favicon = doc.createElement('link');
                favicon.rel = 'icon';
                doc.head.appendChild(favicon);
            }}
            favicon.href = iconUrl;
        }} catch (e) {{
            console.debug('Não foi possível aplicar o ícone do iOS:', e);
        }}
    }})();
    </script>
    """,
    height=0,
    width=0,
)


# --- FUNÇÕES AUXILIARES ---
def gerar_hash(senha: str) -> str:
  """Hash legado mantido para compatibilidade com admins existentes."""
  return hashlib.sha256(senha.encode()).hexdigest()


def gerar_hash_seguro(senha: str) -> str:
  """PBKDF2 com salt; usado em novos cadastros e trocas de senha."""
  salt = os.urandom(16)
  digest = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt, 210_000)
  return f"pbkdf2_sha256$210000${salt.hex()}${digest.hex()}"


def verificar_senha(senha: str, hash_armazenado: str) -> bool:
  """Aceita hashes novos e o SHA-256 antigo sem quebrar a base atual."""
  valor = str(hash_armazenado or "")
  if valor.startswith("pbkdf2_sha256$"):
    try:
      _, iteracoes, salt_hex, digest_hex = valor.split("$", 3)
      teste = hashlib.pbkdf2_hmac(
          "sha256", senha.encode(), bytes.fromhex(salt_hex), int(iteracoes)
      ).hex()
      return hmac.compare_digest(teste, digest_hex)
    except Exception:
      return False
  return hmac.compare_digest(gerar_hash(senha), valor)


# Obter senha inicial padrao via secrets para evitar exposicao no GitHub
SENHA_ADMIN_INICIAL = st.secrets.get("admin_default_password", "winning123")


# --- CONEXÃO COM O GOOGLE SHEETS ---
@st.cache_resource
def conectar_banco():
  scope = [
      "https://spreadsheets.google.com/feeds",
      "https://www.googleapis.com/auth/drive",
  ]
  creds_dict = json.loads(st.secrets["gcp_service_account"])
  creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
  client = gspread.authorize(creds)

  spreadsheet = client.open("WinningWars_DB")
  sheet_dados = spreadsheet.sheet1

  # Aba de Admins
  try:
    sheet_admins = spreadsheet.worksheet("Admins")
  except gspread.WorksheetNotFound:
    sheet_admins = spreadsheet.add_worksheet(
        title="Admins", rows="100", cols="3"
    )
    sheet_admins.append_row(["Usuario", "SenhaHash", "Nivel"])
    sheet_admins.append_row(["admin", gerar_hash_seguro(SENHA_ADMIN_INICIAL), "Dono"])

  # Aba de Estado e Recados
  try:
    sheet_estado = spreadsheet.worksheet("EstadoMes")
  except gspread.WorksheetNotFound:
    sheet_estado = spreadsheet.add_worksheet(
        title="EstadoMes", rows="10", cols="2"
    )
    sheet_estado.append_row(["Chave", "Valor"])
    sheet_estado.append_row(["mes_finalizado", "FALSE"])
    sheet_estado.append_row(
        ["mural_recado", "Bem-vindos ao aplicativo oficial do clã Winning Wars!"]
    )

  # Aba de Layouts
  try:
    sheet_layouts = spreadsheet.worksheet("Layouts")
  except gspread.WorksheetNotFound:
    sheet_layouts = spreadsheet.add_worksheet(
        title="Layouts", rows="500", cols="7"
    )
    sheet_layouts.append_row(
        ["Tipo", "CV", "Autor", "Link", "Descricao", "ImagemUrl", "Tag"]
    )

  # Aba de Logs
  try:
    sheet_logs = spreadsheet.worksheet("Logs")
  except gspread.WorksheetNotFound:
    sheet_logs = spreadsheet.add_worksheet(title="Logs", rows="1000", cols="3")
    sheet_logs.append_row(["DataHora", "Admin", "Acao"])

  # Aba de Galeria da Fama
  try:
    sheet_fama = spreadsheet.worksheet("GaleriaFama")
  except gspread.WorksheetNotFound:
    sheet_fama = spreadsheet.add_worksheet(
        title="GaleriaFama", rows="100", cols="4"
    )
    sheet_fama.append_row(["MesAno", "Primeiro", "Segundo", "Terceiro"])

  # Aba de Novidades e Notícias
  try:
    sheet_novidades = spreadsheet.worksheet("Novidades")
  except gspread.WorksheetNotFound:
    sheet_novidades = spreadsheet.add_worksheet(
        title="Novidades", rows="200", cols="6"
    )
    sheet_novidades.append_row(
        ["DataHora", "Titulo", "Conteudo", "ImagemUrl", "Tag", "Autor"]
    )

  # Migração suave das notícias: campos extras da Central de Comunicação.
  try:
    headers_news = sheet_novidades.row_values(1)
    extras_news = ["Fixada", "ExpiraEm", "Status", "LinkBotao"]
    if len(headers_news) < 10:
      sheet_novidades.resize(cols=10)
    for extra in extras_news:
      if extra not in headers_news:
        sheet_novidades.update_cell(1, len(headers_news) + 1, extra)
        headers_news.append(extra)
  except Exception:
    pass

  # Winning Wars 2.0 - histórico de temporadas e evolução
  try:
    sheet_historico = spreadsheet.worksheet("Historico")
  except gspread.WorksheetNotFound:
    sheet_historico = spreadsheet.add_worksheet(title="Historico", rows="3000", cols="7")
    sheet_historico.append_row(["DataHora", "Temporada", "Jogador", "Pontos", "Posicao", "Tipo", "Detalhe"])

  # Winning Wars 2.0 - agenda/eventos do clã
  try:
    sheet_eventos = spreadsheet.worksheet("EventosCla")
  except gspread.WorksheetNotFound:
    sheet_eventos = spreadsheet.add_worksheet(title="EventosCla", rows="500", cols="7")
    sheet_eventos.append_row(["ID", "Data", "Tipo", "Titulo", "Descricao", "Status", "Autor"])

  # Winning Wars 2.0 - auditoria detalhada de pontuações
  try:
    sheet_auditoria = spreadsheet.worksheet("AuditoriaPontos")
  except gspread.WorksheetNotFound:
    sheet_auditoria = spreadsheet.add_worksheet(title="AuditoriaPontos", rows="5000", cols="7")
    sheet_auditoria.append_row(["DataHora", "Admin", "Jogador", "Atividade", "Antes", "Depois", "Motivo"])

  # Migração suave: adiciona nível de permissão aos admins antigos.
  try:
    headers_admin = sheet_admins.row_values(1)
    if len(headers_admin) < 3:
      sheet_admins.resize(cols=3)
    if "Nivel" not in headers_admin:
      sheet_admins.update_cell(1, len(headers_admin) + 1, "Nivel")
      for row_i in range(2, len(sheet_admins.get_all_values()) + 1):
        sheet_admins.update_cell(row_i, len(headers_admin) + 1, "Dono" if row_i == 2 else "Lider")
  except Exception:
    pass

  return (
      sheet_dados,
      sheet_admins,
      sheet_estado,
      sheet_layouts,
      sheet_logs,
      sheet_fama,
      sheet_novidades,
      sheet_historico,
      sheet_eventos,
      sheet_auditoria,
  )


try:
  (
      sheet_dados,
      sheet_admins,
      sheet_estado,
      sheet_layouts,
      sheet_logs,
      sheet_fama,
      sheet_novidades,
      sheet_historico,
      sheet_eventos,
      sheet_auditoria,
  ) = conectar_banco()
except Exception:
  st.error(
      "⚠️ **Erro na Conexão:** Não foi possível acessar a planilha"
      " 'WinningWars_DB'. Verifique suas permissões."
  )
  st.stop()


def registrar_log(admin: str, acao: str):
  try:
    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet_logs.append_row([data_hora, admin, acao])
  except Exception:
    pass


# --- CARREGAR DADOS COM CACHE DE DESEMPENHO (120 SEGUNDOS) ---
@st.cache_data(ttl=120)
def obter_dados_cached():
  try:
    return sheet_dados.get_all_records()
  except Exception:
    return []


@st.cache_data(ttl=120)
def obter_layouts_cached():
  try:
    return sheet_layouts.get_all_records()
  except Exception:
    return []


@st.cache_data(ttl=120)
def obter_galeria_cached():
  try:
    return sheet_fama.get_all_records()
  except Exception:
    return []


@st.cache_data(ttl=120)
def obter_novidades_cached():
  try:
    return sheet_novidades.get_all_records()
  except Exception:
    return []


@st.cache_data(ttl=60)
def obter_historico_cached():
  try:
    return sheet_historico.get_all_records()
  except Exception:
    return []


@st.cache_data(ttl=60)
def obter_eventos_cached():
  try:
    return sheet_eventos.get_all_records()
  except Exception:
    return []


def nivel_admin_atual() -> str:
  if "admin_logado" not in st.session_state:
    return "Membro"
  usuario = st.session_state["admin_logado"]
  try:
    atual = pd.DataFrame(sheet_admins.get_all_records())
    if not atual.empty and "Nivel" in atual.columns:
      linha = atual[atual["Usuario"] == usuario]
      if not linha.empty:
        return str(linha.iloc[0].get("Nivel", "Lider") or "Lider")
  except Exception:
    pass
  return "Lider"


def tem_permissao(*niveis) -> bool:
  return nivel_admin_atual() in niveis


def registrar_auditoria_ponto(jogador, atividade, antes, depois, motivo=""):
  try:
    admin = st.session_state.get("admin_logado", "sistema")
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet_auditoria.append_row([agora, admin, jogador, atividade, antes, depois, motivo])
  except Exception:
    pass


def salvar_snapshot_historico(df_rank_snapshot, temporada, tipo="snapshot", detalhe=""):
  if df_rank_snapshot is None or df_rank_snapshot.empty:
    return
  agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  linhas = []
  for pos, (_, row) in enumerate(df_rank_snapshot.reset_index(drop=True).iterrows(), start=1):
    linhas.append([agora, temporada, str(row.get("Nome", "")), int(row.get("Total", 0)), pos, tipo, detalhe])
  try:
    sheet_historico.append_rows(linhas, value_input_option="USER_ENTERED")
  except Exception:
    for linha in linhas:
      sheet_historico.append_row(linha)


def snapshot_ranking_atual(tipo="alteracao", detalhe=""):
  try:
    atual = pd.DataFrame(sheet_dados.get_all_records())
    if atual.empty or "Nome" not in atual.columns:
      return
    cols = [c for c in atual.columns if c in ["JogosCla", "Eventos"] or c.startswith(("Guerra_", "Liga_", "Raide_"))]
    for c in cols:
      atual[c] = pd.to_numeric(atual[c], errors="coerce").fillna(0)
    atual["Total"] = atual[cols].sum(axis=1) if cols else 0
    rank = atual.sort_values("Total", ascending=False).reset_index(drop=True)
    salvar_snapshot_historico(rank, temporada_atual_texto(), tipo, detalhe)
  except Exception:
    pass


def temporada_atual_texto():
  meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
  agora = datetime.now()
  return f"{meses[agora.month-1]}/{agora.year}"


dados = obter_dados_cached()
df = pd.DataFrame(dados) if dados else pd.DataFrame()

try:
  dados_admins = sheet_admins.get_all_records()
  df_admins = pd.DataFrame(dados_admins)
except Exception:
  df_admins = pd.DataFrame(
      [["admin", gerar_hash_seguro(SENHA_ADMIN_INICIAL), "Dono"]], columns=["Usuario", "SenhaHash", "Nivel"]
  )

try:
  dados_estado = dict(sheet_estado.get_all_values())
  mes_finalizado = dados_estado.get("mes_finalizado", "FALSE") == "TRUE"
  mural_recado = dados_estado.get("mural_recado", "")
except Exception:
  mes_finalizado = False
  mural_recado = ""

# ESTADO DE NAVEGAÇÃO
if "pagina_atual" not in st.session_state:
  st.session_state["pagina_atual"] = "principal"

df_layouts = pd.DataFrame(obter_layouts_cached())
df_fama = pd.DataFrame(obter_galeria_cached())
df_novidades = pd.DataFrame(obter_novidades_cached())
df_historico = pd.DataFrame(obter_historico_cached())
df_eventos = pd.DataFrame(obter_eventos_cached())


# --- FUNÇÃO AUXILIAR PARA DETERMINAR A PRÓXIMA COLUNA SEQUENCIAL ---
def obter_proxima_coluna_sequencial(col_prefixo: str, df_cols) -> str:
  max_num = 0
  pattern = re.compile(rf"^{col_prefixo}_(\d+)$", re.IGNORECASE)
  for col in df_cols:
    match = pattern.match(str(col).strip())
    if match:
      num = int(match.group(1))
      if num > max_num:
        max_num = num
  return f"{col_prefixo}_{max_num + 1}"


# --- FUNÇÃO PARA GERAR A TABELA COMPLETA EM HTML E DOWNLOAD EM HD COM DESTAQUE NO TOP 3 ---
def gerar_tabela_bilhete_dourado(df_exib):
  """Gera o HTML do ranking com destaque de cores e medalhas para o Top 3."""
  from html import escape

  linhas_html = []
  for idx, row in df_exib.iterrows():
    posicao = escape(str(row.get("Posição", "")))
    jogador = escape(str(row.get("Jogador", "")))
    try:
      pontuacao = int(float(row.get("Pontuação Total", 0)))
    except (TypeError, ValueError):
      pontuacao = 0

    # Aplicação de estilo e medalhas para o Top 3
    classe_top = ""
    prefixo_medalha = ""
    if idx == 1:
      classe_top = "top1-row"
      prefixo_medalha = "🥇 "
    elif idx == 2:
      classe_top = "top2-row"
      prefixo_medalha = "🥈 "
    elif idx == 3:
      classe_top = "top3-row"
      prefixo_medalha = "🥉 "

    linhas_html.append(
        f'<tr class="{classe_top}">'
        f'<td class="tabela-posicao">{posicao}</td>'
        f'<td class="tabela-nome">{prefixo_medalha}{jogador}</td>'
        f'<td class="tabela-pontos">{pontuacao}</td></tr>'
    )

  return f"""
  <!DOCTYPE html>
  <html>
  <head>
    <meta charset="UTF-8">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Luckiest+Guy&family=Nunito:wght@600;800;900&display=swap');

      * {{ box-sizing: border-box; }}
      body {{ 
        margin: 0; 
        background: transparent; 
        font-family: 'Nunito', sans-serif; 
      }}

      .bilhete-dourado-container {{
        background-color: #0f172a; 
        border: 2px solid #334155;
        border-top: 4px solid #facc15;
        border-radius: 14px; 
        padding: 20px;
        max-width: 550px; 
        margin: 10px auto 25px auto;
        box-shadow: 0 8px 25px rgba(0,0,0,0.6);
      }}

      .bilhete-dourado-header {{
        text-align: center;
        margin-bottom: 16px;
      }}

      .bilhete-dourado-title {{
        font-family: 'Luckiest Guy', cursive !important;
        color: #facc15 !important;
        font-size: 2.2rem !important;
        letter-spacing: 1px;
        text-shadow: 2px 2px 0px #000, -1px -1px 0px #000, 1px -1px 0px #000, -1px 1px 0px #000;
        margin: 0 0 10px 0 !important;
      }}

      .btn-download-img {{
        background: linear-gradient(180deg, #3b82f6 0%, #1d4ed8 100%);
        color: #ffffff !important;
        font-family: 'Luckiest Guy', cursive;
        font-size: 1.05rem;
        padding: 10px 20px;
        border: 2px solid #93c5fd;
        border-radius: 10px;
        box-shadow: 0px 4px 0px #1e3a8a;
        cursor: pointer;
        transition: all 0.2s ease;
        text-shadow: 1px 1px 0px #000;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        margin-top: 5px;
      }}

      .btn-download-img:hover {{
        transform: translateY(-2px);
        box-shadow: 0px 6px 0px #1e3a8a;
        background: linear-gradient(180deg, #60a5fa 0%, #2563eb 100%);
      }}

      .tabela-bilhete {{ 
        width: 100%; 
        border-collapse: collapse; 
        text-align: center; 
      }}

      .tabela-bilhete th {{
        background-color: #1e293b; 
        color: #facc15; 
        font-weight: 800;
        font-size: 1.2rem; 
        padding: 12px; 
        border-bottom: 2px solid #334155;
      }}

      .tabela-bilhete td {{
        border-bottom: 1px solid #334155; 
        padding: 12px 10px; 
        font-size: 1.05rem;
        font-weight: 800; 
        color: #e2e8f0;
      }}

      .tabela-bilhete tr:nth-child(even) {{ 
        background-color: #111827; 
      }}

      /* ESTILOS ESPECIAIS PARA O TOP 3 */
      .top1-row {{
        background: linear-gradient(90deg, rgba(250, 204, 21, 0.28) 0%, rgba(202, 138, 4, 0.15) 100%) !important;
        border-left: 4px solid #facc15;
      }}
      .top1-row .tabela-nome, .top1-row .tabela-posicao {{
        color: #fef08a !important;
        font-weight: 900 !important;
      }}
      .top2-row {{
        background: linear-gradient(90deg, rgba(203, 213, 225, 0.22) 0%, rgba(100, 116, 139, 0.12) 100%) !important;
        border-left: 4px solid #cbd5e1;
      }}
      .top2-row .tabela-nome, .top2-row .tabela-posicao {{
        color: #f1f5f9 !important;
        font-weight: 900 !important;
      }}
      .top3-row {{
        background: linear-gradient(90deg, rgba(249, 115, 22, 0.22) 0%, rgba(194, 65, 12, 0.12) 100%) !important;
        border-left: 4px solid #f97316;
      }}
      .top3-row .tabela-nome, .top3-row .tabela-posicao {{
        color: #ffedd5 !important;
        font-weight: 900 !important;
      }}

      .tabela-bilhete tr:hover {{ 
        background-color: #1e293b; 
      }}

      .tabela-posicao {{ 
        color: #facc15 !important; 
        font-weight: 800; 
      }}

      .tabela-nome {{
        text-align: left;
        padding-left: 15px !important;
      }}

      .tabela-pontos {{
        color: #38bdf8 !important;
        font-weight: 900;
      }}

      .emblema {{ 
        text-align: center; 
        margin-top: 18px; 
      }}

      .emblema img {{ 
        width: 100px; 
        filter: drop-shadow(0px 4px 8px rgba(0,0,0,0.5));
      }}

      @media (max-width: 768px) {{
        .bilhete-dourado-container {{ padding: 14px; }}
        .bilhete-dourado-title {{ font-size: 1.8rem !important; }}
        .tabela-bilhete th, .tabela-bilhete td {{ padding: 9px 7px; font-size: 1rem; }}
      }}
    </style>
  </head>
  <body>
    <div style="text-align: center; margin-bottom: 12px;">
      <button class="btn-download-img" id="btn-download-card" onclick="baixarTabelaHD()">
        📸 Baixar Imagem do Ranking (HD)
      </button>
    </div>

    <div class="bilhete-dourado-container" id="card-bilhete-dourado">
      <div class="bilhete-dourado-header">
        <h2 class="bilhete-dourado-title">🏆 Bilhete Dourado</h2>
      </div>
      <table class="tabela-bilhete">
        <thead>
          <tr>
            <th style="width:20%">Pos.</th>
            <th style="width:55%; text-align: left; padding-left: 15px;">Membro</th>
            <th style="width:25%">Pontos</th>
          </tr>
        </thead>
        <tbody>{''.join(linhas_html)}</tbody>
      </table>
      <div class="emblema">
        <img src="https://i.ibb.co/YFbsJ97x/Clash-of-Clans-emblem.png" alt="Emblema Clash of Clans" crossorigin="anonymous">
      </div>
    </div>

    <script>
      function baixarTabelaHD() {{
        const element = document.getElementById('card-bilhete-dourado');
        const btn = document.getElementById('btn-download-card');
        btn.innerText = "⏳ Gerando imagem em HD...";
        btn.disabled = true;

        html2canvas(element, {{
          scale: 3,
          useCORS: true,
          backgroundColor: null,
          logging: false
        }}).then(canvas => {{
          const link = document.createElement('a');
          link.download = 'ranking_bilhete_dourado.png';
          link.href = canvas.toDataURL('image/png', 1.0);
          link.click();
          
          btn.innerText = "📸 Baixar Imagem do Ranking (HD)";
          btn.disabled = false;
        }}).catch(err => {{
          console.error("Erro ao gerar imagem:", err);
          alert("Não foi possível gerar a imagem.");
          btn.innerText = "📸 Baixar Imagem do Ranking (HD)";
          btn.disabled = false;
        }});
      }}
    </script>
  </body>
  </html>
  """


# --- ESTILIZAÇÃO CSS CUSTOMIZADA COM ANIMAÇÃO E FONTES MAIORES ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Luckiest+Guy&family=Nunito:wght@600;800;900&display=swap');

    /* ANIMAÇÃO DE TRANSIÇÃO SUAVE ENTRE PÁGINAS */
    @keyframes fadeInPage {
        from {
            opacity: 0;
            transform: translateY(12px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .main .block-container {
        animation: fadeInPage 0.45s ease-in-out;
    }

    .main { 
        background: radial-gradient(circle, #1e293b 0%, #0b0e14 100%); 
        font-size: 1.05rem;
    }

    h1, h2, h3 { 
        font-family: 'Luckiest Guy', cursive !important; 
        color: #facc15 !important; 
        letter-spacing: 1px;
        text-shadow: 2px 2px 0px #000, -1px -1px 0px #000, 1px -1px 0px #000, -1px 1px 0px #000;
        word-break: break-word;
    }
    
    .main-title { 
        text-align: center; 
        margin-top: 8px; 
        margin-bottom: 8px; 
        font-size: 2.8rem !important; 
        line-height: 1.2;
    }

    .main-subtitle { 
        text-align: center; 
        color: #cbd5e1; 
        font-family: 'Nunito', sans-serif; 
        font-weight: 700; 
        margin-bottom: 25px; 
        font-size: 1.15rem !important;
        padding: 0 10px;
    }
    
    /* BOTÕES GERAIS */
    div.stButton > button {
        background: linear-gradient(180deg, #22c55e 0%, #15803d 100%) !important;
        color: #ffffff !important;
        font-family: 'Luckiest Guy', cursive, sans-serif !important;
        font-size: 1.05rem !important;
        border: 2px solid #86efac !important;
        border-radius: 12px !important;
        box-shadow: 0px 4px 0px #14532d !important;
        transition: all 0.2s ease;
        text-shadow: 1px 1px 0px #000;
        white-space: normal !important;
        height: auto !important;
        padding: 10px 14px !important;
    }

    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0px 6px 0px #14532d !important;
        background: linear-gradient(180deg, #4ade80 0%, #16a34a 100%) !important;
    }

    /* ==========================================================
       PORTAIS DE NAVEGAÇÃO - DESTAQUE VISUAL / CTA
       ========================================================== */
    @keyframes portalAuraGold {
        0%,100% { box-shadow: 0 10px 28px rgba(245,158,11,.22), inset 0 1px 0 rgba(255,255,255,.20); }
        50%     { box-shadow: 0 14px 42px rgba(250,204,21,.46), inset 0 1px 0 rgba(255,255,255,.30); }
    }
    @keyframes portalAuraBlue {
        0%,100% { box-shadow: 0 10px 28px rgba(59,130,246,.22), inset 0 1px 0 rgba(255,255,255,.18); }
        50%     { box-shadow: 0 14px 42px rgba(96,165,250,.46), inset 0 1px 0 rgba(255,255,255,.28); }
    }
    @keyframes portalAuraGreen {
        0%,100% { box-shadow: 0 10px 28px rgba(34,197,94,.18), inset 0 1px 0 rgba(255,255,255,.18); }
        50%     { box-shadow: 0 14px 40px rgba(74,222,128,.38), inset 0 1px 0 rgba(255,255,255,.26); }
    }
    @keyframes portalSweep {
        0% { transform: translateX(-180%) skewX(-22deg); opacity:0; }
        18% { opacity:.8; }
        48%,100% { transform: translateX(320%) skewX(-22deg); opacity:0; }
    }
    @keyframes portalFloat {
        0%,100% { transform: translateY(0); }
        50% { transform: translateY(-3px); }
    }

    .st-key-top_nav_menu {
        padding: 6px 2px 12px;
    }

    /* Base comum dos três portais */
    .st-key-top_nav_menu div.stButton > button,
    .top-nav-link {
        position: relative !important;
        overflow: hidden !important;
        isolation: isolate;
        width: 100%;
        min-height: 68px !important;
        padding: 10px 14px !important;
        border-radius: 18px !important;
        border: 1px solid rgba(255,255,255,.28) !important;
        font-family: 'Luckiest Guy', cursive, sans-serif !important;
        font-size: 1.04rem !important;
        font-weight: 900 !important;
        line-height: 1.15 !important;
        letter-spacing: .15px !important;
        text-decoration: none !important;
        transition: transform .22s cubic-bezier(.2,.85,.25,1),
                    filter .22s ease,
                    box-shadow .22s ease,
                    border-color .22s ease !important;
        -webkit-tap-highlight-color: transparent;
    }

    /* Guerra: fogo/dourado */
    .st-key-top_nav_menu div[data-testid="stColumn"]:nth-child(1) div.stButton > button {
        color: #fff7d6 !important;
        background:
          radial-gradient(circle at 15% 10%, rgba(255,255,255,.24), transparent 25%),
          linear-gradient(135deg, #7c2d12 0%, #b45309 36%, #f59e0b 72%, #facc15 100%) !important;
        text-shadow: 0 2px 3px rgba(0,0,0,.65) !important;
        animation: portalAuraGold 2.8s ease-in-out infinite, portalFloat 4.4s ease-in-out infinite;
    }

    /* Rankeada: arena azul/roxa */
    .st-key-top_nav_menu div[data-testid="stColumn"]:nth-child(2) div.stButton > button {
        color: #eef6ff !important;
        background:
          radial-gradient(circle at 15% 10%, rgba(255,255,255,.22), transparent 25%),
          linear-gradient(135deg, #312e81 0%, #4338ca 34%, #2563eb 68%, #38bdf8 100%) !important;
        text-shadow: 0 2px 3px rgba(0,0,0,.62) !important;
        animation: portalAuraBlue 3.1s ease-in-out infinite, portalFloat 4.8s ease-in-out infinite .3s;
    }

    /* Vastaya: portal esmeralda */
    .top-nav-link.nav-clan {
        display:flex;
        align-items:center;
        justify-content:center;
        color:#ecfdf5 !important;
        background:
          radial-gradient(circle at 15% 10%, rgba(255,255,255,.20), transparent 25%),
          linear-gradient(135deg, #064e3b 0%, #047857 40%, #16a34a 72%, #4ade80 100%) !important;
        text-shadow: 0 2px 3px rgba(0,0,0,.62) !important;
        animation: portalAuraGreen 3.3s ease-in-out infinite, portalFloat 5s ease-in-out infinite .5s;
    }

    /* Reflexo cinematográfico */
    .st-key-top_nav_menu div.stButton > button::before,
    .top-nav-link::before {
        content:"";
        position:absolute;
        z-index:-1;
        top:-35%;
        left:-35%;
        width:30%;
        height:175%;
        pointer-events:none;
        background:linear-gradient(90deg, transparent, rgba(255,255,255,.62), transparent);
        animation:portalSweep 5.2s ease-in-out infinite;
    }

    /* Moldura interna */
    .st-key-top_nav_menu div.stButton > button::after,
    .top-nav-link::after {
        content:"";
        position:absolute;
        inset:4px;
        border-radius:13px;
        border:1px solid rgba(255,255,255,.14);
        pointer-events:none;
        z-index:-1;
    }

    .st-key-top_nav_menu div.stButton > button:hover,
    .top-nav-link:hover {
        transform: translateY(-6px) scale(1.035) !important;
        filter: brightness(1.12) saturate(1.13);
        border-color: rgba(255,255,255,.70) !important;
    }
    .st-key-top_nav_menu div.stButton > button:active,
    .top-nav-link:active {
        transform: translateY(1px) scale(.98) !important;
        filter: brightness(.96);
        transition-duration:.07s !important;
    }

    /* Texto auxiliar embaixo dos portais */
    .portal-caption {
        margin-top: -3px;
        text-align:center;
        font-size:.72rem;
        font-weight:700;
        letter-spacing:.35px;
        color:#94a3b8;
        opacity:.95;
    }
    .portal-caption.gold { color:#fcd34d; }
    .portal-caption.blue { color:#93c5fd; }
    .portal-caption.green { color:#86efac; }

    @media (max-width:700px) {
        .st-key-top_nav_menu div.stButton > button,
        .top-nav-link {
            min-height:62px !important;
            padding:9px 7px !important;
            font-size:.92rem !important;
            border-radius:15px !important;
        }
        .portal-caption {
            font-size:.62rem;
            line-height:1.15;
        }
    }

    @media (prefers-reduced-motion: reduce) {
        .st-key-top_nav_menu div.stButton > button,
        .top-nav-link,
        .st-key-top_nav_menu div.stButton > button::before,
        .top-nav-link::before {
            animation:none !important;
            transition-duration:.01ms !important;
        }
    }

    /* ABAS */
    button[data-baseweb="tab"] {
        font-size: 1.35rem !important;
        font-weight: 800 !important;
        font-family: 'Nunito', sans-serif !important;
        padding: 14px 24px !important;
        background-color: #1e293b !important;
        border: 2px solid #334155 !important;
        border-radius: 12px 12px 0 0 !important;
        color: #cbd5e1 !important;
        margin-right: 6px !important;
        transition: all 0.2s ease !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(180deg, #facc15 0%, #ca8a04 100%) !important;
        color: #000000 !important;
        border-color: #fef08a !important;
        text-shadow: none !important;
        transform: translateY(-2px);
        box-shadow: 0px 4px 14px rgba(250, 204, 21, 0.35) !important;
    }

    button[data-baseweb="tab"]:hover {
        border-color: #facc15 !important;
        color: #facc15 !important;
    }

    /* PODIUM E CARDS */
    .podium-card { 
        padding: 18px; 
        border-radius: 16px; 
        text-align: center; 
        margin-bottom: 15px; 
        color: #ffffff; 
        box-shadow: 0 8px 25px rgba(0,0,0,0.6); 
        font-family: 'Nunito', sans-serif; 
    }
    .podium-title { font-family: 'Luckiest Guy', cursive; font-size: 1.35rem; margin-top: 6px; margin-bottom: 6px; text-shadow: 1px 1px 0px #000; }
    .podium-name { font-size: 1.2rem; font-weight: 800; word-break: break-word; }
    .podium-score { font-size: 1.1rem; margin-top: 4px; }
    .gold { background: linear-gradient(135deg, #f59e0b 0%, #78350f 100%); border: 3px solid #facc15; }
    .silver { background: linear-gradient(135deg, #64748b 0%, #1e293b 100%); border: 3px solid #cbd5e1; }
    .bronze { background: linear-gradient(135deg, #d97706 0%, #451a03 100%); border: 3px solid #f97316; }

    .btn-layout-copy {
        display: inline-block; width: 100%; max-width: 100%; text-align: center;
        background: linear-gradient(180deg, #3b82f6 0%, #1d4ed8 100%); color: white !important;
        padding: 12px 16px; border-radius: 10px; text-decoration: none; font-family: 'Luckiest Guy', cursive;
        border: 2px solid #93c5fd; box-shadow: 0px 4px 0px #1e3a8a; font-size: 1.1rem;
    }
    .btn-external-link {
        display: flex; align-items: center; justify-content: center; gap: 6px; width: 100%; text-align: center;
        background: linear-gradient(180deg, #16a34a 0%, #15803d 100%); color: white !important;
        padding: 10px 12px; border-radius: 10px; text-decoration: none; font-family: 'Luckiest Guy', cursive;
        border: 2px solid #86efac; box-shadow: 0px 4px 0px #14532d; font-size: 0.95rem;
    }
    .btn-youtube-link {
        display: flex; align-items: center; justify-content: center; gap: 6px; width: 100%; text-align: center;
        background: linear-gradient(180deg, #dc2626 0%, #991b1b 100%); color: white !important;
        padding: 10px 12px; border-radius: 10px; text-decoration: none; font-family: 'Luckiest Guy', cursive;
        border: 2px solid #fca5a5; box-shadow: 0px 4px 0px #7f1d1d; font-size: 0.95rem;
    }
    .btn-scid {
        display: flex; align-items: center; justify-content: center; gap: 6px; width: 100%; text-align: center;
        background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%); color: white !important;
        padding: 10px 12px; border-radius: 10px; text-decoration: none; font-family: 'Luckiest Guy', cursive;
        border: 2px solid #60a5fa; box-shadow: 0px 4px 0px #1e3a8a; font-size: 0.95rem;
    }
    .btn-whatsapp-link {
        display: flex; align-items: center; justify-content: center; gap: 6px; width: 100%; text-align: center;
        background: linear-gradient(180deg, #22c55e 0%, #15803d 100%); color: white !important;
        padding: 10px 12px; border-radius: 10px; text-decoration: none; font-family: 'Luckiest Guy', cursive;
        border: 2px solid #86efac; box-shadow: 0px 4px 0px #14532d; font-size: 0.95rem;
    }

    .mural-banner {
        background: #1e293b; border-radius: 14px; padding: 14px 18px; margin-bottom: 22px;
        border: 2px solid #334155; border-left: 6px solid #facc15;
        box-shadow: 0 4px 14px rgba(0,0,0,0.3); font-family: 'Nunito', sans-serif;
    }
    .mural-header { font-family: 'Luckiest Guy', cursive; color: #facc15; font-size: 1.15rem; margin-bottom: 4px; }

    .news-card {
        background: #0f172a; border: 2px solid #334155; border-top: 4px solid #38bdf8;
        border-radius: 14px; padding: 20px; margin-bottom: 20px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.4); font-family: 'Nunito', sans-serif;
    }
    .news-tag {
        display: inline-block; padding: 4px 10px; border-radius: 6px;
        font-weight: 800; font-size: 0.85rem; color: #fff; background: #2563eb; margin-bottom: 8px;
    }
    .news-title { font-family: 'Luckiest Guy', cursive; color: #facc15; font-size: 1.5rem; margin-bottom: 6px; }
    .news-meta { color: #94a3b8; font-size: 0.85rem; margin-bottom: 12px; }
    .news-card-top { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
    .news-content { color: #e2e8f0; font-size: 1.05rem; line-height: 1.6; }
    .news-image-wrap { position: relative; margin: 12px 0 16px 0; text-align: center; }
    .news-image { display: block; width: 100%; max-width: 100%; max-height: 520px; object-fit: contain; margin: 0 auto; border-radius: 12px; border: 2px solid #334155; box-shadow: 0 6px 16px rgba(0,0,0,.45); background: #111827; }
    .news-image-fallback { display: none; color: #94a3b8; background: #111827; border: 2px dashed #334155; border-radius: 12px; padding: 22px; font-weight: 800; }
    .news-image-error .news-image { display: none; }
    .news-image-error .news-image-fallback { display: block; }

    .info-card {
        background: #0f172a; border: 2px solid #334155; border-radius: 14px; padding: 22px; margin-bottom: 15px;
        font-family: 'Nunito', sans-serif; color: #e2e8f0; box-shadow: 0 6px 18px rgba(0,0,0,0.4); height: 100%;
    }
    .info-card-header { font-family: 'Luckiest Guy', cursive; color: #facc15; font-size: 1.25rem; margin-bottom: 10px; }
    .info-card-list { padding-left: 18px; margin-bottom: 0px; }
    .info-card-list li { margin-bottom: 8px; line-height: 1.5; font-size: 1.05rem; }

    .rules-card {
        background: #0f172a; border: 2px solid #334155; border-radius: 14px; padding: 25px; margin-top: 35px;
        font-family: 'Nunito', sans-serif; color: #e2e8f0; box-shadow: 0 6px 18px rgba(0,0,0,0.4);
    }
    .rules-title { font-family: 'Luckiest Guy', cursive; color: #facc15; font-size: 1.45rem; margin-bottom: 14px; }
    .rules-card ul { margin-bottom: 0px; padding-left: 20px; }
    .rules-card li { margin-bottom: 12px; line-height: 1.55; font-size: 1.05rem; }

    @media (max-width: 768px) {
        .main-title { font-size: 2rem !important; }
        .main-subtitle { font-size: 0.95rem !important; }
        .mural-banner { padding: 12px !important; }
        .podium-card { padding: 14px !important; }
        button[data-baseweb="tab"] { font-size: 1.05rem !important; padding: 10px 12px !important; }
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- TOPO DA PÁGINA: MENU DE NAVEGAÇÃO + LOGIN ADMIN ---
col_nav, col_admin_top = st.columns([6, 1])

with col_nav:
  # Container com chave própria para que as animações atinjam somente
  # os botões de direcionamento do topo da página.
  with st.container(key="top_nav_menu"):
    b1, b2, b3 = st.columns(3)
    with b1:
      if st.button("⚔️ LAYOUTS PARA GUERRA", use_container_width=True):
        st.session_state["pagina_atual"] = "layouts_guerra"
        st.rerun()
    with b2:
      if st.button("🏆 LAYOUTS PARA RANKEADAS", use_container_width=True):
        st.session_state["pagina_atual"] = "layouts_rankeada"
        st.rerun()
    with b3:
      st.markdown(
          '<a'
          ' href="https://link.clashofclans.com/pt?action=OpenClanProfile&tag=2YPL9GU8Y"'
          ' target="_blank" rel="noopener noreferrer"'
          ' class="top-nav-link nav-clan">🏰 VISITAR CLÃ VASTAYA ↗</a>',
          unsafe_allow_html=True,
      )

with col_admin_top:
  if "admin_logado" in st.session_state:
    st.success(f"👤 **{st.session_state['admin_logado']}**")
    if st.button("🚪 Sair", key="top_logout", use_container_width=True):
      del st.session_state["admin_logado"]
      st.rerun()
  else:
    with st.popover("🔐 Admin", use_container_width=True):
      st.markdown("### 🔐 Acesso Restrito Admin")
      with st.form("form_login_topo"):
        u_top = st.text_input("Usuário Admin")
        s_top = st.text_input("Senha", type="password")
        btn_top_login = st.form_submit_button(
            "Entrar", use_container_width=True
        )

        if btn_top_login:
          if not df_admins.empty:
            val = df_admins[
                (df_admins["Usuario"] == u_top)
                & (df_admins["SenhaHash"] == gerar_hash(s_top))
            ]
            if not val.empty:
              st.session_state["admin_logado"] = u_top
              registrar_log(u_top, "Logou pelo painel no canto superior direito")
              st.success("Logado com sucesso!")
              st.rerun()
            else:
              st.error("Usuário ou senha inválidos.")

st.write("---")


# ==============================================================================
# FUNÇÃO PARA RENDERIZAR PÁGINAS DE LAYOUT
# ==============================================================================
def renderizar_pagina_layouts(tipo_layout: str, titulo: str):
  if st.button("⬅️ Voltar ao Início"):
    st.session_state["pagina_atual"] = "principal"
    st.rerun()

  st.markdown(
      f"<h1 style='text-align: center;'>{titulo}</h1>", unsafe_allow_html=True
  )
  eh_admin = "admin_logado" in st.session_state

  cv_map = {
      "CV 18": "https://i.ibb.co/fGLhwj76/Town-Hall18.webp",
      "CV 17": "https://i.ibb.co/yc4LCWmS/cv17.webp",
      "CV 16": "https://i.ibb.co/ym8MH1Q8/Giga-Inferno16.webp",
      "CV 15": "https://i.ibb.co/7dzVK5L7/Giga-Inferno15.webp",
      "CV 14": "https://i.ibb.co/x4LsVdM/Giga-Inferno14.webp",
      "CV 13": "https://i.ibb.co/HTPNQtyp/TH-13-4-Clash-GFX.png",
      "CV 12": "https://i.ibb.co/hFHnz1GW/TH-12-Clash-GFX.png",
  }

  cv_list = list(cv_map.keys())
  tabs_cv = st.tabs(cv_list)

  for idx, cv_nome in enumerate(cv_list):
    with tabs_cv[idx]:
      th_img_url = cv_map[cv_nome]

      st.markdown(
          f"""
            <div style="display: flex; align-items: center; justify-content: center; gap: 15px; margin-top: 15px; margin-bottom: 20px;">
                <img src="{th_img_url}" width="90" style="filter: drop-shadow(0px 4px 8px rgba(0,0,0,0.5));">
                <h2 style="margin: 0; font-size: 2rem;">Bases de {tipo_layout} - {cv_nome}</h2>
            </div>
            """,
          unsafe_allow_html=True,
      )

      if eh_admin:
        with st.expander(
            f"➕ [ADMIN] Adicionar Novo Layout de {tipo_layout} ({cv_nome})"
        ):
          with st.form(
              key=f"form_{tipo_layout}_{cv_nome}", clear_on_submit=True
          ):
            link_layout = st.text_input("Link Oficial do Layout (URL)")
            img_url = st.text_input("Link Direto da Foto (Opcional)")

            btn_enviar = st.form_submit_button("Publicar Layout")

            if btn_enviar:
              if link_layout.strip():
                sheet_layouts.append_row([
                    tipo_layout,
                    cv_nome,
                    st.session_state["admin_logado"],
                    link_layout.strip(),
                    "",
                    img_url.strip(),
                    "",
                ])
                registrar_log(
                    st.session_state["admin_logado"],
                    f"Adicionou layout {tipo_layout} para {cv_nome}",
                )
                st.cache_data.clear()
                st.success("Layout publicado com sucesso!")
                st.rerun()
              else:
                st.error("⚠️ Insira o link do layout antes de publicar.")

      if not df_layouts.empty:
        layouts_filtrados = df_layouts[
            (df_layouts["Tipo"] == tipo_layout) & (df_layouts["CV"] == cv_nome)
        ]
      else:
        layouts_filtrados = pd.DataFrame()

      if not layouts_filtrados.empty:
        layouts_filtrados = layouts_filtrados.iloc[::-1]

        for item_idx, row in layouts_filtrados.iterrows():
          _, col_cent, _ = st.columns([1, 2, 1])
          with col_cent:
            st.markdown(
                f"<div style='text-align: center; margin-bottom: 8px;'><b>👑"
                f" Enviado por:</b> {row['Autor']}</div>",
                unsafe_allow_html=True,
            )

            img_url_limpa = str(row["ImagemUrl"]).strip()
            if img_url_limpa:
              try:
                st.markdown(
                    f"""
                                    <div style="text-align: center; margin-bottom: 12px;">
                                        <img src="{img_url_limpa}" style="max-width: 100%; border-radius: 12px; border: 2px solid #334155; box-shadow: 0 6px 16px rgba(0,0,0,0.5);">
                                    </div>
                                    """,
                    unsafe_allow_html=True,
                )
                if eh_admin:
                  st.markdown(
                      f'<div style="text-align: center; margin-bottom: 10px;"><a href="{img_url_limpa}" target="_blank" download style="color: #38bdf8; text-decoration: underline; font-weight: bold; font-size: 0.95rem;">📥 Baixar Imagem (Admin)</a></div>',
                      unsafe_allow_html=True,
                  )
              except Exception:
                pass

            st.markdown(
                f'<a href="{row["Link"]}" target="_blank"'
                ' class="btn-layout-copy">📲 COPIAR LAYOUT NO CLASH</a>',
                unsafe_allow_html=True,
            )

            if eh_admin:
              st.write("")
              if st.button(
                  "❌ Excluir Layout (Admin)",
                  key=f"del_{tipo_layout}_{cv_nome}_{item_idx}",
                  use_container_width=True,
              ):
                cell = sheet_layouts.find(row["Link"])
                if cell:
                  sheet_layouts.delete_rows(cell.row)
                  registrar_log(
                      st.session_state["admin_logado"],
                      f"Excluiu layout de {cv_nome}",
                  )
                  st.cache_data.clear()
                  st.success("Removido!")
                  st.rerun()

            st.divider()
      else:
        st.info(f"Nenhum layout cadastrado para {cv_nome}.")


# ==============================================================================
# COMPONENTE AUXILIAR: LINKS CLICÁVEIS NO FEED
# ==============================================================================
def tornar_links_clicaveis(texto: str) -> str:
  """Converte URLs HTTP/HTTPS em links que abrem em nova guia."""
  from html import escape

  texto_safe = escape(str(texto), quote=False)
  url_pattern = re.compile(r"https?://[^\s<]+", re.IGNORECASE)

  def substituir(match):
    url = match.group(0)
    pontuacao_final = ""
    while url and url[-1] in ".,;:!?)]}":
      pontuacao_final = url[-1] + pontuacao_final
      url = url[:-1]
    url_attr = escape(url, quote=True)
    return (
      f'<a href="{url_attr}" target="_blank" rel="noopener noreferrer" '
      f'style="color:#38bdf8; text-decoration:underline; font-weight:800;">'
      f'{escape(url)}</a>{escape(pontuacao_final)}'
    )

  return url_pattern.sub(substituir, texto_safe).replace("\n", "<br>")

# ==============================================================================
# COMPONENTE REUTILIZÁVEL: FEED DE NOVIDADES
# ==============================================================================
def renderizar_feed_novidades(limite=None, titulo="📰 Últimas Novidades"):
  """Renderiza o feed de notícias mantendo texto e imagem no mesmo card."""
  from html import escape

  st.markdown(
      f"<h2 style='text-align: center;'>{titulo}</h2>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='text-align: center; color: #cbd5e1;'>"
      "Atualizações, eventos e comunicados do clã em um só lugar.</p>",
      unsafe_allow_html=True,
  )

  if df_novidades.empty:
    st.info("Nenhuma novidade ou notícia publicada no momento.")
    return

  novidades_feed = df_novidades.copy()
  if "Status" in novidades_feed.columns:
    novidades_feed = novidades_feed[~novidades_feed["Status"].astype(str).str.lower().isin(["encerrada", "encerrado", "inativa"])]
  if "ExpiraEm" in novidades_feed.columns:
    def _valida_expira(v):
      txt = str(v or "").strip()
      if not txt: return True
      try: return datetime.strptime(txt, "%d/%m/%Y").date() >= datetime.now().date()
      except Exception: return True
    novidades_feed = novidades_feed[novidades_feed["ExpiraEm"].apply(_valida_expira)]
  if "Fixada" in novidades_feed.columns:
    novidades_feed["_fix"] = novidades_feed["Fixada"].astype(str).str.upper().isin(["SIM","TRUE","1"]).astype(int)
    novidades_feed = novidades_feed.sort_values("_fix", ascending=False, kind="stable")
  novidades_feed = novidades_feed.iloc[::-1] if "Fixada" not in novidades_feed.columns else pd.concat([novidades_feed[novidades_feed.get("_fix",0)==1], novidades_feed[novidades_feed.get("_fix",0)==0].iloc[::-1]])
  if limite is not None:
    novidades_feed = novidades_feed.head(limite)

  for item_idx, item in novidades_feed.iterrows():
    tag_nome = str(item.get("Tag", "Aviso")).strip()
    titulo_item = str(item.get("Titulo", "")).strip()
    conteudo = str(item.get("Conteudo", "")).strip()
    img_url = str(item.get("ImagemUrl", "")).strip()
    data_hora = str(item.get("DataHora", "")).strip()
    autor = str(item.get("Autor", "Liderança")).strip()

    tag_safe = escape(tag_nome)
    titulo_safe = escape(titulo_item)
    conteudo_safe = tornar_links_clicaveis(conteudo)
    data_safe = escape(data_hora)
    autor_safe = escape(autor)
    img_safe = escape(img_url, quote=True)

    # A imagem fica dentro do próprio card. O fallback evita ícone de imagem
    # quebrada caso a URL cadastrada esteja indisponível.
    imagem_html = ""
    if img_url:
      imagem_html = f"""
        <div class="news-image-wrap">
          <img src="{img_safe}"
               alt="Imagem da novidade"
               class="news-image"
               loading="lazy"
               onerror="this.style.display='none'; this.parentElement.classList.add('news-image-error');">
          <div class="news-image-fallback">🖼️ Imagem indisponível</div>
        </div>
      """

    link_botao = str(item.get("LinkBotao", "")).strip()
    link_html = f'<div style="margin-top:14px;"><a class="btn-external-link" href="{escape(link_botao, quote=True)}" target="_blank" rel="noopener noreferrer">🔗 ABRIR LINK ↗</a></div>' if link_botao else ""

    st.markdown(
        f"""
        <article class="news-card">
          <div class="news-card-top">
            <span class="news-tag">{tag_safe}</span>
            <div class="news-meta">🕒 Publicado em {data_safe} por <b>{autor_safe}</b></div>
          </div>
          <div class="news-title">{titulo_safe}</div>
          {imagem_html}
          <div class="news-content">{conteudo_safe}</div>
          {link_html}
        </article>
        """,
        unsafe_allow_html=True,
    )

    # Winning Wars 2.3 - gerenciamento do próprio post diretamente no feed.
    if "admin_logado" in st.session_state:
      with st.expander(
          f"⚙️ [ADMIN] Editar / excluir: {titulo_item or 'Publicação sem título'}",
          expanded=False,
      ):
        tags_news = [
            "🎉 Evento", "⚔️ Torneio", "🚀 Atualização Game",
            "📢 Aviso Clã", "🏆 Premiação Extra"
        ]
        tag_idx_news = tags_news.index(tag_nome) if tag_nome in tags_news else 0
        fixada_atual = str(item.get("Fixada", "")).strip().upper() in ["SIM", "TRUE", "1"]
        expira_atual = str(item.get("ExpiraEm", "")).strip()
        status_atual_news = str(item.get("Status", "Ativa")).strip() or "Ativa"
        status_news_opcoes = ["Ativa", "Encerrada", "Inativa"]
        status_idx_news = (
            status_news_opcoes.index(status_atual_news)
            if status_atual_news in status_news_opcoes else 0
        )

        with st.form(f"form_feed_news_admin_{item_idx}", clear_on_submit=False):
          edit_feed_titulo = st.text_input(
              "Título", value=titulo_item, key=f"feed_news_titulo_{item_idx}"
          )
          edit_feed_tag = st.selectbox(
              "Categoria / Tag", tags_news, index=tag_idx_news,
              key=f"feed_news_tag_{item_idx}",
          )
          edit_feed_conteudo = st.text_area(
              "Conteúdo", value=conteudo, height=150,
              key=f"feed_news_conteudo_{item_idx}",
          )
          edit_feed_img = st.text_input(
              "Link da imagem / banner", value=img_url,
              key=f"feed_news_img_{item_idx}",
          )
          edit_feed_link = st.text_input(
              "Link do botão (opcional)", value=str(item.get("LinkBotao", "")).strip(),
              key=f"feed_news_link_{item_idx}",
          )

          nf1, nf2, nf3 = st.columns(3)
          with nf1:
            edit_feed_fixada = st.checkbox(
                "📌 Fixar no topo", value=fixada_atual,
                key=f"feed_news_fixada_{item_idx}",
            )
          with nf2:
            edit_feed_expira = st.text_input(
                "Expira em", value=expira_atual, placeholder="DD/MM/AAAA",
                key=f"feed_news_expira_{item_idx}",
            )
          with nf3:
            edit_feed_status = st.selectbox(
                "Status", status_news_opcoes, index=status_idx_news,
                key=f"feed_news_status_{item_idx}",
            )

          confirmar_feed_delete = st.checkbox(
              "⚠️ Confirmo a exclusão permanente deste post",
              key=f"feed_news_confirm_delete_{item_idx}",
          )
          bf1, bf2 = st.columns(2)
          with bf1:
            salvar_feed_news = st.form_submit_button(
                "💾 Salvar alterações", use_container_width=True, type="primary"
            )
          with bf2:
            excluir_feed_news = st.form_submit_button(
                "🗑️ Excluir publicação", use_container_width=True
            )

          linha_news = int(item_idx) + 2

          if salvar_feed_news:
            if not edit_feed_titulo.strip() or not edit_feed_conteudo.strip():
              st.error("⚠️ Título e conteúdo são obrigatórios.")
            else:
              expira_limpa = edit_feed_expira.strip()
              data_expira_valida = True
              if expira_limpa:
                try:
                  datetime.strptime(expira_limpa, "%d/%m/%Y")
                except ValueError:
                  data_expira_valida = False

              if not data_expira_valida:
                st.error("⚠️ Use DD/MM/AAAA no campo de expiração ou deixe-o vazio.")
              else:
                headers_news = sheet_novidades.row_values(1)
                atualizacoes_news = {{
                    "Titulo": edit_feed_titulo.strip(),
                    "Conteudo": edit_feed_conteudo.strip(),
                    "ImagemUrl": edit_feed_img.strip(),
                    "Tag": edit_feed_tag,
                    "Autor": st.session_state["admin_logado"],
                    "Fixada": "SIM" if edit_feed_fixada else "NAO",
                    "ExpiraEm": expira_limpa,
                    "Status": edit_feed_status,
                    "LinkBotao": edit_feed_link.strip(),
                }}
                for coluna_news, valor_news in atualizacoes_news.items():
                  if coluna_news in headers_news:
                    sheet_novidades.update_cell(
                        linha_news, headers_news.index(coluna_news) + 1, valor_news
                    )
                registrar_log(
                    st.session_state["admin_logado"],
                    f"Editou publicação '{titulo_item}' diretamente no feed Últimas Novidades",
                )
                st.cache_data.clear()
                st.success("✅ Publicação atualizada com sucesso!")
                st.rerun()

          if excluir_feed_news:
            if not confirmar_feed_delete:
              st.warning("⚠️ Marque a confirmação antes de excluir a publicação.")
            else:
              sheet_novidades.delete_rows(linha_news)
              registrar_log(
                  st.session_state["admin_logado"],
                  f"Excluiu publicação '{titulo_item}' diretamente no feed Últimas Novidades",
              )
              st.cache_data.clear()
              st.success("🗑️ Publicação excluída com sucesso!")
              st.rerun()


# ==============================================================================
# PÁGINA EXCLUSIVA: NOVIDADES E PAINEL DE NOTÍCIAS
# ==============================================================================
def renderizar_pagina_novidades():
  if st.button("⬅️ Voltar ao Início"):
    st.session_state["pagina_atual"] = "principal"
    st.rerun()

  st.markdown(
      "<h1 style='text-align: center;'>📰 Novidades, Torneios & Eventos</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='text-align: center; color: #cbd5e1;'>Fique por dentro das"
      " atualizações do Clash of Clans, eventos internos e comunicados da"
      " liderança do clã!</p><br>",
      unsafe_allow_html=True,
  )

  eh_admin = "admin_logado" in st.session_state

  # PAINEL ADMINISTRATIVO DIRETO NA ABA NOVIDADES
  if eh_admin:
    with st.expander("🔐 [ADMIN] Publicar Nova Novidade", expanded=False):
      with st.form("form_nova_novidade_pagina", clear_on_submit=True):
        noticia_titulo = st.text_input("Título da Notícia")
        noticia_tag = st.selectbox(
            "Categoria / Tag",
            ["🎉 Evento", "⚔️ Torneio", "🚀 Atualização Game", "📢 Aviso Clã", "🏆 Premiação Extra"],
        )
        noticia_conteudo = st.text_area("Conteúdo do Comunicado", height=140)
        noticia_img = st.text_input(
            "Link Direto da Imagem / Banner (Opcional)",
            placeholder="https://exemplo.com/imagem.jpg",
        )
        btn_pub = st.form_submit_button("📢 Publicar Notícia", use_container_width=True)

        if btn_pub:
          if noticia_titulo.strip() and noticia_conteudo.strip():
            d_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
            sheet_novidades.append_row([
                d_hora,
                noticia_titulo.strip(),
                noticia_conteudo.strip(),
                noticia_img.strip(),
                noticia_tag,
                st.session_state["admin_logado"],
            ])
            registrar_log(
                st.session_state["admin_logado"],
                f"Publicou notícia '{noticia_titulo.strip()}' pela página Novidades",
            )
            st.cache_data.clear()
            st.success("✅ Notícia publicada com sucesso!")
            st.rerun()
          else:
            st.error("⚠️ Preencha o título e o conteúdo antes de publicar.")

    st.caption("Como administrador, você pode editar ou excluir cada publicação diretamente abaixo.")

  # LISTAGEM DAS NOVIDADES
  if not df_novidades.empty:
    novidades_inv = df_novidades.iloc[::-1]

    for item_idx, item in novidades_inv.iterrows():
      tag_nome = str(item.get("Tag", "Aviso")).strip()
      titulo = str(item.get("Titulo", "")).strip()
      conteudo = str(item.get("Conteudo", "")).strip()
      img_url = str(item.get("ImagemUrl", "")).strip()
      data_hora = str(item.get("DataHora", "")).strip()
      autor = str(item.get("Autor", "Liderança")).strip()

      from html import escape

      imagem_html_admin = ""
      if img_url:
        imagem_html_admin = f"""
          <div class="news-image-wrap">
            <img src="{escape(img_url, quote=True)}"
                 alt="Imagem da novidade"
                 class="news-image"
                 loading="lazy"
                 onerror="this.style.display='none'; this.parentElement.classList.add('news-image-error');">
            <div class="news-image-fallback">🖼️ Imagem indisponível</div>
          </div>
        """

      st.markdown(
          f"""
            <article class="news-card">
                <div class="news-card-top">
                    <span class="news-tag">{escape(tag_nome)}</span>
                    <div class="news-meta">🕒 Publicado em {escape(data_hora)} por <b>{escape(autor)}</b></div>
                </div>
                <div class="news-title">{escape(titulo)}</div>
                {imagem_html_admin}
                <div class="news-content">{tornar_links_clicaveis(conteudo)}</div>
            </article>
            """,
          unsafe_allow_html=True,
      )

      # EDIÇÃO/EXCLUSÃO DIRETAMENTE NO CARD PARA ADMINS
      if eh_admin:
        with st.expander(f"⚙️ [ADMIN] Gerenciar: {titulo or 'Sem título'}", expanded=False):
          with st.form(f"form_editar_novidade_{item_idx}", clear_on_submit=False):
            edit_titulo = st.text_input(
                "Título", value=titulo, key=f"edit_titulo_{item_idx}"
            )

            tags_disponiveis = [
                "🎉 Evento", "⚔️ Torneio", "🚀 Atualização Game",
                "📢 Aviso Clã", "🏆 Premiação Extra"
            ]
            tag_index = tags_disponiveis.index(tag_nome) if tag_nome in tags_disponiveis else 0

            edit_tag = st.selectbox(
                "Categoria / Tag",
                tags_disponiveis,
                index=tag_index,
                key=f"edit_tag_{item_idx}",
            )
            edit_conteudo = st.text_area(
                "Conteúdo", value=conteudo, height=140,
                key=f"edit_conteudo_{item_idx}",
            )
            edit_img = st.text_input(
                "Link da Imagem / Banner", value=img_url,
                key=f"edit_img_{item_idx}",
            )

            c_edit, c_del = st.columns(2)
            with c_edit:
              btn_editar = st.form_submit_button(
                  "💾 Salvar Alterações", use_container_width=True
              )
            with c_del:
              btn_excluir = st.form_submit_button(
                  "🗑️ Excluir Publicação", use_container_width=True
              )

            if btn_editar:
              if not edit_titulo.strip() or not edit_conteudo.strip():
                st.error("⚠️ O título e o conteúdo são obrigatórios.")
              else:
                # O índice do DataFrame corresponde à linha da planilha - 1,
                # pois a primeira linha da planilha é o cabeçalho.
                linha_planilha = int(item_idx) + 2
                sheet_novidades.update(
                    f"A{linha_planilha}:F{linha_planilha}",
                    [[
                        data_hora,
                        edit_titulo.strip(),
                        edit_conteudo.strip(),
                        edit_img.strip(),
                        edit_tag,
                        st.session_state["admin_logado"],
                    ]],
                )
                registrar_log(
                    st.session_state["admin_logado"],
                    f"Editou notícia '{titulo}' pela página Novidades",
                )
                st.cache_data.clear()
                st.success("✅ Publicação atualizada!")
                st.rerun()

            if btn_excluir:
              linha_planilha = int(item_idx) + 2
              sheet_novidades.delete_rows(linha_planilha)
              registrar_log(
                  st.session_state["admin_logado"],
                  f"Excluiu notícia '{titulo}' pela página Novidades",
              )
              st.cache_data.clear()
              st.success("🗑️ Publicação excluída!")
              st.rerun()

      st.divider()
  else:
    st.info("Nenhuma novidade ou notícia publicada no momento.")


# PÁGINA EXCLUSIVA: REGRAS DO CLÃ
# ==============================================================================
def renderizar_regras_cla():
  if st.button("⬅️ Voltar ao Início"):
    st.session_state["pagina_atual"] = "principal"
    st.rerun()

  st.markdown(
      "<h1 style='text-align: center;'>📜 Regras Oficiais do Clã Winning"
      " Wars</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      """
    <div class="rules-card">
        <div class="rules-title">🛡️ Regras Oficiais do Clã</div>
        <ul>
            <li>1 - Novatos serão testados antes de ir para as guerras.</li>
            <li>2 - Guerras: Ataque o CV do mesmo nível que o seu. (<b>NÃO</b> é espelho).</li>
            <li>3 - Inatividade por 3 dias sem aviso prévio = kick.</li>
            <li>4 - Jogos dos Clãs: Mínimo de 2.000 pontos. O descumprimento = kick.</li>
            <li>5 - Cargos e promoções serão por mérito.</li>
            <li>6 - WhatsApp obrigatório para participar da Liga / para disputar a premiação dos passes.</li>
            <li>7 - Contas rushadas com heróis em nível baixo não serão aceitas.</li>
            <li>8 - Se tem dúvida, pergunte / peça ajuda! Estamos aqui para nos ajudar.</li>
        </ul>
    </div>
    """,
      unsafe_allow_html=True,
  )


# ==============================================================================
# WINNING WARS 2.0 - COMPONENTES DE EXPERIÊNCIA / GESTÃO
# ==============================================================================
def renderizar_dashboard_temporada(df_rank):
  if df_rank is None or df_rank.empty:
    return
  total_membros = len(df_rank)
  lider = str(df_rank.iloc[0].get("Nome", "-"))
  pontos_lider = int(df_rank.iloc[0].get("Total", 0))
  col1, col2, col3, col4 = st.columns(4)
  col1.metric("👥 Membros", total_membros)
  col2.metric("🏆 Líder", lider)
  col3.metric("⭐ Pontos do líder", pontos_lider)
  col4.metric("🎟️ Temporada", temporada_atual_texto())

  if len(df_rank) >= 3:
    terceiro = int(df_rank.iloc[2].get("Total", 0))
    quarto = int(df_rank.iloc[3].get("Total", 0)) if len(df_rank) > 3 else None
    texto = (
        f"🥇 **{df_rank.iloc[0]['Nome']}** · {int(df_rank.iloc[0]['Total'])} pts   "
        f"🥈 **{df_rank.iloc[1]['Nome']}** · {int(df_rank.iloc[1]['Total'])} pts   "
        f"🥉 **{df_rank.iloc[2]['Nome']}** · {terceiro} pts"
    )
    st.markdown(texto)
    if quarto is not None:
      st.caption(f"🔥 Disputa pelo Top 3: {df_rank.iloc[3]['Nome']} está a {max(0, terceiro-quarto+1)} ponto(s) de ultrapassar o 3º colocado.")


def calcular_medalhas(row, colunas_guerras, colunas_liga, colunas_raides, df_rank):
  medalhas = []
  total = int(row.get("Total", 0))
  nome = str(row.get("Nome", ""))
  if total >= 100: medalhas.append("💯 Centurião")
  if total >= 50: medalhas.append("🔥 Em Chamas")
  if colunas_guerras and sum(float(row.get(c, 0) or 0) for c in colunas_guerras) >= 20: medalhas.append("⚔️ Senhor da Guerra")
  if colunas_raides and sum(float(row.get(c, 0) or 0) for c in colunas_raides) >= 20: medalhas.append("🏰 Mestre dos Raides")
  if colunas_liga and all(float(row.get(c, 0) or 0) > 0 for c in colunas_liga): medalhas.append("🏆 Veterano da Liga")
  if not df_rank.empty and str(df_rank.iloc[0].get("Nome")) == nome: medalhas.append("👑 Líder Atual")
  if not df_fama.empty and any(nome in [str(r.get("Primeiro","")), str(r.get("Segundo","")), str(r.get("Terceiro",""))] for _, r in df_fama.iterrows()):
    medalhas.append("🎟️ Hall da Fama")
  return medalhas


def renderizar_perfil_membro(df_rank, colunas_guerras, colunas_liga, colunas_raides):
  st.markdown("### 👤 Perfil do Guerreiro")
  if df_rank is None or df_rank.empty:
    st.info("Ainda não existem dados para montar perfis.")
    return
  nomes = df_rank["Nome"].astype(str).tolist()
  nome = st.selectbox("Escolha seu nome", nomes, key="perfil_membro_nome")
  pos = nomes.index(nome)
  row = df_rank.iloc[pos]
  total = int(row.get("Total", 0))
  acima = df_rank.iloc[pos-1] if pos > 0 else None
  terceiro = df_rank.iloc[2] if len(df_rank) >= 3 else None

  c1,c2,c3,c4 = st.columns(4)
  c1.metric("🏆 Posição", f"{pos+1}º")
  c2.metric("⭐ Pontos", total)
  if acima is not None:
    falta = max(0, int(acima.get("Total",0)) - total + 1)
    c3.metric("⬆️ Próxima posição", f"{falta} pts")
  else:
    c3.metric("👑 Status", "Líder")
  if terceiro is not None and pos >= 3:
    c4.metric("🥉 Para o Top 3", f"{max(0, int(terceiro.get('Total',0))-total+1)} pts")
  else:
    c4.metric("🎟️ Top 3", "Dentro" if pos < 3 else "-")

  guerra = int(sum(float(row.get(c,0) or 0) for c in colunas_guerras))
  liga = int(sum(float(row.get(c,0) or 0) for c in colunas_liga))
  raide = int(sum(float(row.get(c,0) or 0) for c in colunas_raides))
  jogos = int(float(row.get("JogosCla",0) or 0))
  eventos = int(float(row.get("Eventos",0) or 0))
  st.markdown(f"**⚔️ Guerras:** {guerra}    **🏆 Liga:** {liga}    **🏰 Raides:** {raide}    **🎮 Jogos:** {jogos}    **🎉 Eventos:** {eventos}")

  medals = calcular_medalhas(row, colunas_guerras, colunas_liga, colunas_raides, df_rank)
  if medals:
    st.markdown("**Conquistas:** " + " · ".join(medals))

  if not df_historico.empty and "Jogador" in df_historico.columns:
    hist = df_historico[df_historico["Jogador"].astype(str) == nome].copy()
    if not hist.empty:
      hist["Pontos"] = pd.to_numeric(hist["Pontos"], errors="coerce")
      hist["DataHora"] = pd.to_datetime(hist["DataHora"], errors="coerce")
      hist = hist.dropna(subset=["DataHora"]).sort_values("DataHora")
      if not hist.empty:
        st.markdown("#### 📈 Evolução")
        st.line_chart(hist.set_index("DataHora")[["Pontos"]])


def renderizar_agenda_membros():
  st.markdown("### 📅 Agenda Winning Wars")
  if df_eventos.empty:
    st.info("Nenhum evento cadastrado no momento.")
    return
  agenda = df_eventos.copy()
  if "Status" in agenda.columns:
    agenda = agenda[agenda["Status"].astype(str).str.lower() != "encerrado"]
  for _, ev in agenda.sort_values("Data", ascending=True).iterrows():
    st.markdown(f"**{ev.get('Data','')} · {ev.get('Tipo','📅')} {ev.get('Titulo','Evento')}**  \n{ev.get('Descricao','')}")
    st.divider()


def renderizar_gestao_20(df_rank, colunas_guerras, colunas_liga, colunas_raides):
  st.markdown("### 🚀 Central de Gestão 2.0")
  st.caption(f"Nível de acesso: **{nivel_admin_atual()}**")
  if not tem_permissao("Dono", "Lider", "Co-lider"):
    st.warning("Seu nível permite comunicação, mas não alteração de pontuações.")
    return

  quick, eventos_tab, comunicacao_tab, temporada_tab, auditoria_tab, permissoes_tab = st.tabs([
      "⚡ Lançamento rápido", "📅 Eventos", "📢 Comunicação", "🏆 Temporada", "↩️ Auditoria", "🛡️ Permissões"
  ])

  with quick:
    atividades = [c for c in df.columns if c in ["JogosCla", "Eventos"] or c.startswith(("Guerra_", "Liga_", "Raide_"))]
    if df.empty or not atividades:
      st.info("Cadastre jogadores e atividades antes de lançar pontos.")
    else:
      atividade = st.selectbox("Atividade", atividades, key="ww20_atividade")
      base = df[["Nome", atividade]].copy()
      base[atividade] = pd.to_numeric(base[atividade], errors="coerce").fillna(0).astype(int)
      edit = st.data_editor(base, hide_index=True, use_container_width=True, disabled=["Nome"], key=f"quick_{atividade}")
      motivo = st.text_input("Motivo/observação (opcional)", key="quick_motivo")
      if st.button("💾 Salvar somente alterações", type="primary", use_container_width=True):
        alteracoes = 0
        headers = sheet_dados.row_values(1)
        col_num = headers.index(atividade) + 1
        for idx, row_edit in edit.iterrows():
          antes = int(base.iloc[idx][atividade])
          depois = int(row_edit[atividade])
          if antes != depois:
            nome_j = str(row_edit["Nome"])
            cell_nome = sheet_dados.find(nome_j)
            if cell_nome:
              sheet_dados.update_cell(cell_nome.row, col_num, depois)
              registrar_auditoria_ponto(nome_j, atividade, antes, depois, motivo)
              registrar_log(st.session_state["admin_logado"], f"Alterou {nome_j} - {atividade}: {antes} → {depois}")
              alteracoes += 1
        if alteracoes:
          snapshot_ranking_atual("alteracao", f"Lançamento rápido: {atividade}")
          st.cache_data.clear(); st.success(f"✅ {alteracoes} alteração(ões) salva(s)."); st.rerun()
        else:
          st.info("Nenhuma pontuação foi alterada.")

  with eventos_tab:
    with st.form("novo_evento_20", clear_on_submit=True):
      c1,c2 = st.columns(2)
      data_ev = c1.date_input("Data")
      tipo_ev = c2.selectbox("Tipo", ["⚔️ Guerra", "🏆 Liga", "🏰 Raide", "🎮 Jogos do Clã", "🎉 Evento", "📢 Aviso"] )
      titulo_ev = st.text_input("Título")
      desc_ev = st.text_area("Descrição")
      if st.form_submit_button("➕ Adicionar à agenda"):
        if titulo_ev.strip():
          valores = sheet_eventos.get_all_values()
          ids=[]
          for r in valores[1:]:
            try: ids.append(int(r[0]))
            except: pass
          novo_id = max(ids, default=0)+1
          sheet_eventos.append_row([novo_id, data_ev.strftime("%d/%m/%Y"), tipo_ev, titulo_ev.strip(), desc_ev.strip(), "Ativo", st.session_state["admin_logado"]])
          st.cache_data.clear(); st.success("Evento cadastrado!"); st.rerun()
    if not df_eventos.empty:
      st.dataframe(df_eventos, hide_index=True, use_container_width=True)
      ids_ev = df_eventos.get("ID", pd.Series(dtype=str)).astype(str).tolist()
      if ids_ev:
        id_manage = st.selectbox("Gerenciar evento ID", ids_ev, key="ev_manage_id")

        # Localiza a linha pelo ID exclusivamente na primeira coluna.
        valores_eventos = sheet_eventos.get_all_values()
        linha_evento = None
        for numero_linha, valores_linha in enumerate(valores_eventos[1:], start=2):
          if valores_linha and str(valores_linha[0]).strip() == str(id_manage).strip():
            linha_evento = numero_linha
            break

        evento_sel = df_eventos[
            df_eventos["ID"].astype(str).str.strip() == str(id_manage).strip()
        ]
        evento_atual = evento_sel.iloc[0] if not evento_sel.empty else None

        if evento_atual is not None:
          st.markdown("#### ✏️ Editar evento publicado")

          tipos_evento = [
              "⚔️ Guerra", "🏆 Liga", "🏰 Raide",
              "🎮 Jogos do Clã", "🎉 Evento", "📢 Aviso"
          ]
          tipo_atual = str(evento_atual.get("Tipo", "🎉 Evento")).strip()
          indice_tipo = tipos_evento.index(tipo_atual) if tipo_atual in tipos_evento else 4

          try:
            data_atual_evento = datetime.strptime(
                str(evento_atual.get("Data", "")).strip(), "%d/%m/%Y"
            ).date()
          except (ValueError, TypeError):
            data_atual_evento = datetime.now().date()

          status_atual = str(evento_atual.get("Status", "Ativo")).strip()
          status_opcoes = ["Ativo", "Encerrado"]
          indice_status = (
              status_opcoes.index(status_atual)
              if status_atual in status_opcoes else 0
          )

          with st.form(f"editar_evento_{id_manage}", clear_on_submit=False):
            ce1, ce2 = st.columns(2)
            edit_data_ev = ce1.date_input(
                "Data do evento",
                value=data_atual_evento,
                key=f"edit_data_ev_{id_manage}",
            )
            edit_tipo_ev = ce2.selectbox(
                "Tipo do evento",
                tipos_evento,
                index=indice_tipo,
                key=f"edit_tipo_ev_{id_manage}",
            )
            edit_titulo_ev = st.text_input(
                "Título do evento",
                value=str(evento_atual.get("Titulo", "")),
                key=f"edit_titulo_ev_{id_manage}",
            )
            edit_desc_ev = st.text_area(
                "Descrição do evento",
                value=str(evento_atual.get("Descricao", "")),
                key=f"edit_desc_ev_{id_manage}",
            )
            edit_status_ev = st.selectbox(
                "Status",
                status_opcoes,
                index=indice_status,
                key=f"edit_status_ev_{id_manage}",
            )

            if st.form_submit_button(
                "💾 Salvar alterações do evento",
                use_container_width=True,
                type="primary",
            ):
              if not edit_titulo_ev.strip():
                st.error("⚠️ O título do evento é obrigatório.")
              elif linha_evento is None:
                st.error("⚠️ Não foi possível localizar o evento na planilha.")
              else:
                headers_ev = sheet_eventos.row_values(1)
                dados_atualizados = {
                    "Data": edit_data_ev.strftime("%d/%m/%Y"),
                    "Tipo": edit_tipo_ev,
                    "Titulo": edit_titulo_ev.strip(),
                    "Descricao": edit_desc_ev.strip(),
                    "Status": edit_status_ev,
                    "Autor": st.session_state["admin_logado"],
                }

                for coluna, valor in dados_atualizados.items():
                  if coluna in headers_ev:
                    sheet_eventos.update_cell(
                        linha_evento, headers_ev.index(coluna) + 1, valor
                    )

                registrar_log(
                    st.session_state["admin_logado"],
                    f"Editou evento ID {id_manage}: '{edit_titulo_ev.strip()}'",
                )
                st.cache_data.clear()
                st.success("✅ Evento atualizado com sucesso!")
                st.rerun()

        st.markdown("#### ⚙️ Outras ações")
        cenc, cdel = st.columns(2)

        if cenc.button(
            "✅ Marcar encerrado",
            use_container_width=True,
            key=f"encerrar_evento_{id_manage}",
        ):
          headers_ev = sheet_eventos.row_values(1)
          if linha_evento and "Status" in headers_ev:
            sheet_eventos.update_cell(
                linha_evento, headers_ev.index("Status") + 1, "Encerrado"
            )
            registrar_log(
                st.session_state["admin_logado"],
                f"Encerrou evento ID {id_manage}",
            )
            st.cache_data.clear()
            st.success("✅ Evento marcado como encerrado.")
            st.rerun()

        with cdel:
          confirmar_exclusao_evento = st.checkbox(
              "Confirmar exclusão",
              key=f"confirmar_exclusao_evento_{id_manage}",
          )
          if st.button(
              "🗑️ Excluir evento",
              use_container_width=True,
              key=f"excluir_evento_{id_manage}",
          ):
            if not confirmar_exclusao_evento:
              st.warning("⚠️ Marque 'Confirmar exclusão' antes de excluir.")
            elif linha_evento is None:
              st.error("⚠️ Não foi possível localizar o evento na planilha.")
            else:
              titulo_excluido = (
                  str(evento_atual.get("Titulo", ""))
                  if evento_atual is not None else ""
              )
              sheet_eventos.delete_rows(linha_evento)
              registrar_log(
                  st.session_state["admin_logado"],
                  f"Excluiu evento ID {id_manage}: '{titulo_excluido}'",
              )
              st.cache_data.clear()
              st.success("🗑️ Evento excluído com sucesso!")
              st.rerun()

  with comunicacao_tab:
    st.markdown("#### 📢 Publicação avançada")
    with st.form("comunicacao_20", clear_on_submit=True):
      titulo_c = st.text_input("Título do comunicado")
      tag_c = st.selectbox("Categoria", ["📢 Aviso Clã", "⚔️ Torneio", "🎉 Evento", "🏆 Premiação Extra", "🚨 Urgente"] )
      conteudo_c = st.text_area("Conteúdo")
      img_c = st.text_input("Imagem (URL, opcional)")
      link_c = st.text_input("Link do botão (opcional)")
      fixada_c = st.checkbox("📌 Fixar no topo")
      usar_exp = st.checkbox("Definir data de expiração")
      exp_c = st.date_input("Expira em", value=datetime.now().date())
      if st.form_submit_button("📣 Publicar comunicado"):
        if titulo_c.strip() and conteudo_c.strip():
          exp_txt = exp_c.strftime("%d/%m/%Y") if usar_exp else ""
          sheet_novidades.append_row([datetime.now().strftime("%d/%m/%Y %H:%M"), titulo_c.strip(), conteudo_c.strip(), img_c.strip(), tag_c, st.session_state["admin_logado"], "SIM" if fixada_c else "NAO", exp_txt, "Ativa", link_c.strip()])
          registrar_log(st.session_state["admin_logado"], f"Publicou comunicado avançado '{titulo_c.strip()}'")
          st.cache_data.clear(); st.success("Comunicado publicado!"); st.rerun()

  with temporada_tab:
    st.markdown("#### 🏆 Encerramento seguro da temporada")
    st.write(f"Temporada sugerida: **{temporada_atual_texto()}**")
    if not df_rank.empty:
      st.write("Top 3 atual:")
      st.write(" · ".join([f"{i+1}º {df_rank.iloc[i]['Nome']} ({int(df_rank.iloc[i]['Total'])} pts)" for i in range(min(3,len(df_rank)))]))
    confirm = st.checkbox("Confirmo que revisei as pontuações e quero finalizar a temporada", key="confirm_finaliza_20")
    c1,c2 = st.columns(2)
    if c1.button("🔒 FINALIZAR TEMPORADA", type="primary", use_container_width=True, disabled=not confirm):
      if not df_rank.empty:
        temporada = temporada_atual_texto()
        salvar_snapshot_historico(df_rank, temporada, "fechamento", "Ranking final")
        if len(df_rank) >= 3:
          sheet_fama.append_row([temporada, df_rank.iloc[0]["Nome"], df_rank.iloc[1]["Nome"], df_rank.iloc[2]["Nome"]])
        cell = sheet_estado.find("mes_finalizado")
        if cell: sheet_estado.update_cell(cell.row, 2, "TRUE")
        else: sheet_estado.append_row(["mes_finalizado", "TRUE"])
        registrar_log(st.session_state["admin_logado"], f"Finalizou temporada {temporada} e arquivou ranking")
        st.cache_data.clear(); st.success("🏆 Temporada finalizada e arquivada!"); st.rerun()
    if c2.button("🔓 REABRIR TEMPORADA", use_container_width=True):
      cell = sheet_estado.find("mes_finalizado")
      if cell: sheet_estado.update_cell(cell.row, 2, "FALSE")
      registrar_log(st.session_state["admin_logado"], "Reabriu a temporada para edição")
      st.cache_data.clear(); st.success("Temporada aberta."); st.rerun()

    st.divider()
    st.markdown("#### 🌅 Iniciar nova temporada")
    confirma_reset = st.checkbox("Confirmo que quero zerar as pontuações das atividades após arquivar o ranking atual", key="reset_temporada_20")
    if st.button("🌅 ARQUIVAR E ZERAR PONTUAÇÕES", disabled=not confirma_reset, use_container_width=True):
      snapshot_ranking_atual("pre_reset", "Snapshot antes de zerar pontuações")
      headers = sheet_dados.row_values(1)
      atividades = [c for c in headers if c in ["JogosCla", "Eventos"] or c.startswith(("Guerra_", "Liga_", "Raide_"))]
      total_linhas = len(sheet_dados.get_all_values())
      for atividade in atividades:
        col_n = headers.index(atividade)+1
        if total_linhas >= 2:
          inicio = gspread.utils.rowcol_to_a1(2, col_n)
          fim = gspread.utils.rowcol_to_a1(total_linhas, col_n)
          sheet_dados.update(f"{inicio}:{fim}", [[0] for _ in range(total_linhas-1)])
      cell = sheet_estado.find("mes_finalizado")
      if cell: sheet_estado.update_cell(cell.row, 2, "FALSE")
      registrar_log(st.session_state["admin_logado"], "Iniciou nova temporada e zerou pontuações")
      st.cache_data.clear(); st.success("🌅 Nova temporada iniciada com pontuações zeradas."); st.rerun()

  with auditoria_tab:
    try:
      aud = pd.DataFrame(sheet_auditoria.get_all_records())
    except Exception:
      aud = pd.DataFrame()
    if aud.empty:
      st.info("Nenhuma alteração detalhada registrada ainda.")
    else:
      aud_rev = aud.iloc[::-1].head(100)
      st.dataframe(aud_rev, hide_index=True, use_container_width=True)
      st.caption("A auditoria registra quem alterou, jogador, atividade e valor antes/depois.")
      ultima = aud.iloc[-1]
      st.warning(f"Última alteração: {ultima.get('Jogador')} / {ultima.get('Atividade')} — {ultima.get('Antes')} → {ultima.get('Depois')}")
      if st.button("↩️ Desfazer última alteração", use_container_width=True):
        jogador = str(ultima.get("Jogador", "")); atividade = str(ultima.get("Atividade", "")); antes = ultima.get("Antes", 0)
        headers = sheet_dados.row_values(1); cell_nome = sheet_dados.find(jogador) if jogador else None
        if cell_nome and atividade in headers:
          atual_val = sheet_dados.cell(cell_nome.row, headers.index(atividade)+1).value
          sheet_dados.update_cell(cell_nome.row, headers.index(atividade)+1, antes)
          registrar_auditoria_ponto(jogador, atividade, atual_val, antes, "DESFAZER última alteração")
          registrar_log(st.session_state["admin_logado"], f"Desfez alteração de {jogador}/{atividade}")
          snapshot_ranking_atual("desfazer", f"Reversão {jogador}/{atividade}")
          st.cache_data.clear(); st.success("Alteração desfeita."); st.rerun()

  with permissoes_tab:
    if not tem_permissao("Dono"):
      st.warning("Somente o nível Dono pode alterar permissões.")
    else:
      admins = pd.DataFrame(sheet_admins.get_all_records())
      if not admins.empty:
        usuario_p = st.selectbox("Administrador", admins["Usuario"].astype(str).tolist())
        nivel_p = st.selectbox("Novo nível", ["Dono", "Lider", "Co-lider", "Editor"])
        if st.button("🛡️ Atualizar permissão"):
          cell = sheet_admins.find(usuario_p)
          headers = sheet_admins.row_values(1)
          if cell and "Nivel" in headers:
            sheet_admins.update_cell(cell.row, headers.index("Nivel")+1, nivel_p)
            registrar_log(st.session_state["admin_logado"], f"Alterou permissão de {usuario_p} para {nivel_p}")
            st.success("Permissão atualizada."); st.rerun()

# ==============================================================================
# SELEÇÃO DE PÁGINAS
# ==============================================================================
if st.session_state["pagina_atual"] == "layouts_guerra":
  renderizar_pagina_layouts("Guerra", "🛡️ Layouts Oficiais de Guerra")
elif st.session_state["pagina_atual"] == "layouts_rankeada":
  renderizar_pagina_layouts("Rankeada", "🏆 Layouts Oficiais de Rankeada")
elif st.session_state["pagina_atual"] == "novidades":
  renderizar_pagina_novidades()
elif st.session_state["pagina_atual"] == "regras_cla":
  renderizar_regras_cla()

# ==============================================================================
# PÁGINA PRINCIPAL
# ==============================================================================
else:
  # LOGO COM TAMANHO AUMENTADO (180px)
  st.markdown(
      """
    <div style="text-align: center; margin-top: 10px; margin-bottom: 12px;">
        <img src="https://i.ibb.co/yBShz18b/winning.png" width="180" style="filter: drop-shadow(0px 8px 16px rgba(0,0,0,0.7)); transition: transform 0.3s ease;">
    </div>
    """,
      unsafe_allow_html=True,
  )

  # TÍTULO PRINCIPAL
  st.markdown(
      "<h1 class='main-title'>⚔️ Winning Wars APP</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p class='main-subtitle'>Acompanhe o ranking em tempo real. Ao final do"
      " mês, os Top 3 garantem o Passe Dourado!</p>",
      unsafe_allow_html=True,
  )

  # BANNER DA TEMPORADA ATUAL - destaque temático sem repetir dados do ranking
  temporada_topo = temporada_atual_texto()
  status_temporada_topo = "TEMPORADA FINALIZADA" if mes_finalizado else "TEMPORADA EM DISPUTA"
  icone_status_temporada = "🏆" if mes_finalizado else "⚔️"
  st.markdown(
      f"""
      <style>
        @keyframes wwSeasonGlow {{
          0%, 100% {{ box-shadow: 0 0 12px rgba(250,204,21,.28), inset 0 0 18px rgba(250,204,21,.05); }}
          50% {{ box-shadow: 0 0 28px rgba(250,204,21,.52), inset 0 0 30px rgba(250,204,21,.10); }}
        }}
        @keyframes wwSeasonShine {{
          0% {{ transform: translateX(-150%) skewX(-20deg); }}
          55%, 100% {{ transform: translateX(260%) skewX(-20deg); }}
        }}
        @keyframes wwSeasonFloat {{
          0%, 100% {{ transform: translateY(0); }}
          50% {{ transform: translateY(-3px); }}
        }}
        .ww-season-banner {{
          position: relative;
          overflow: hidden;
          max-width: 760px;
          margin: 2px auto 24px auto;
          padding: 15px 22px 16px;
          text-align: center;
          border: 2px solid #facc15;
          border-radius: 18px;
          background:
            radial-gradient(circle at 50% -30%, rgba(250,204,21,.25), transparent 52%),
            linear-gradient(135deg, #111827 0%, #1e293b 50%, #111827 100%);
          animation: wwSeasonGlow 2.8s ease-in-out infinite;
        }}
        .ww-season-banner::before {{
          content: '';
          position: absolute;
          top: -50%;
          left: -30%;
          width: 25%;
          height: 200%;
          background: linear-gradient(90deg, transparent, rgba(255,255,255,.22), transparent);
          animation: wwSeasonShine 4.8s ease-in-out infinite;
          pointer-events: none;
        }}
        .ww-season-kicker {{
          color: #cbd5e1;
          font-family: 'Nunito', sans-serif;
          font-weight: 900;
          font-size: .82rem;
          letter-spacing: 2px;
          text-transform: uppercase;
        }}
        .ww-season-name {{
          margin: 3px 0 2px;
          color: #facc15;
          font-family: 'Luckiest Guy', cursive;
          font-size: clamp(1.7rem, 5vw, 2.45rem);
          letter-spacing: 1px;
          text-shadow: 2px 2px 0 #000, 0 0 16px rgba(250,204,21,.38);
          animation: wwSeasonFloat 2.2s ease-in-out infinite;
        }}
        .ww-season-status {{
          display: inline-block;
          margin-top: 4px;
          padding: 5px 12px;
          border-radius: 999px;
          background: rgba(15,23,42,.72);
          border: 1px solid rgba(250,204,21,.42);
          color: #f8fafc;
          font-family: 'Nunito', sans-serif;
          font-weight: 900;
          font-size: .78rem;
          letter-spacing: .7px;
        }}
        @media (max-width: 600px) {{
          .ww-season-banner {{ margin-bottom: 18px; padding: 13px 14px 14px; border-radius: 15px; }}
          .ww-season-kicker {{ font-size: .72rem; letter-spacing: 1.4px; }}
        }}
      </style>
      <div class="ww-season-banner">
        <div class="ww-season-kicker">🎟️ Competição Winning Wars</div>
        <div class="ww-season-name">{temporada_topo}</div>
        <div class="ww-season-status">{icone_status_temporada} {status_temporada_topo}</div>
      </div>
      """,
      unsafe_allow_html=True,
  )

  # MURAL DE RECADOS
  if mural_recado.strip():
    st.markdown(
        f"""
        <div class="mural-banner">
            <div class="mural-header">📢 MURAL DA LIDERANÇA</div>
            <div style="color: #e2e8f0; font-size: 1.05rem;">{mural_recado}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

  if not df.empty:
    colunas_raides = [c for c in df.columns if c.startswith("Raide_")]
    colunas_guerras = [c for c in df.columns if c.startswith("Guerra_")]
    colunas_liga = [c for c in df.columns if c.startswith("Liga_")]
    colunas_pontos = (
        ["JogosCla", "Eventos"] + colunas_raides + colunas_guerras + colunas_liga
    )

    for col in colunas_pontos:
      if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    cols_somar = [c for c in colunas_pontos if c in df.columns]
    df["Total"] = df[cols_somar].sum(axis=1) if cols_somar else 0
    df_rank = df.sort_values(by="Total", ascending=False).reset_index(drop=True)
    df_rank.index = df_rank.index + 1

    posicoes = []
    for i in df_rank.index:
      if i == 1:
        posicoes.append("🥇 1º")
      elif i == 2:
        posicoes.append("🥈 2º")
      elif i == 3:
        posicoes.append("🥉 3º")
      else:
        posicoes.append(f"{i}º")
    df_rank["Posição"] = posicoes
  else:
    colunas_raides, colunas_guerras, colunas_liga = [], [], []
    df_rank = pd.DataFrame()

  # ABAS DESTACADAS DA PÁGINA PRINCIPAL
  st.write("")

  tab_ranking, tab_tabela, tab_perfil, tab_agenda, tab_admin = st.tabs(
      ["🏆 Ranking ao Vivo", "📋 Tabela Detalhada", "👤 Meu Perfil", "📅 Agenda", "🔐 Painel Admin"]
  )

  # ABA 1: RANKING AO VIVO
  with tab_ranking:
    if not df.empty and "Total" in df.columns:
      if mes_finalizado:
        st.success(
            "🔒 **O MÊS FOI FINALIZADO PELO ADMIN! CONFIRA OS CAMPEÕES:**"
        )
        col1, col2, col3 = st.columns(3)
        if len(df_rank) >= 1:
          with col1:
            st.markdown(
                f'<div class="podium-card gold"><img'
                ' src="https://i.ibb.co/mkC43vT/goldenpass.png" width="55"><div'
                ' class="podium-title">🥇 1º LUGAR</div><div'
                f' class="podium-name">{df_rank.iloc[0]["Nome"]}</div><div'
                ' class="podium-score">'
                f'{int(df_rank.iloc[0]["Total"])} pts</div><small>Garantidor do'
                " Passe Dourado 🎟️</small></div>",
                unsafe_allow_html=True,
            )
        if len(df_rank) >= 2:
          with col2:
            st.markdown(
                f'<div class="podium-card silver"><img'
                ' src="https://i.ibb.co/mkC43vT/goldenpass.png" width="55"><div'
                ' class="podium-title">🥈 2º LUGAR</div><div'
                f' class="podium-name">{df_rank.iloc[1]["Nome"]}</div><div'
                ' class="podium-score">'
                f'{int(df_rank.iloc[1]["Total"])} pts</div><small>Garantidor do'
                " Passe Dourado 🎟️</small></div>",
                unsafe_allow_html=True,
            )
        if len(df_rank) >= 3:
          with col3:
            st.markdown(
                f'<div class="podium-card bronze"><img'
                ' src="https://i.ibb.co/mkC43vT/goldenpass.png" width="55"><div'
                ' class="podium-title">🥉 3º LUGAR</div><div'
                f' class="podium-name">{df_rank.iloc[2]["Nome"]}</div><div'
                ' class="podium-score">'
                f'{int(df_rank.iloc[2]["Total"])} pts</div><small>Garantidor do'
                " Passe Dourado 🎟️</small></div>",
                unsafe_allow_html=True,
            )

      # BARRA DE BUSCA
      _, col_busca, _ = st.columns([1, 2, 1])
      with col_busca:
        busca_player = st.text_input(
            "🔍 Buscar Jogador no Ranking:",
            placeholder="Digite o nome do membro...",
        )

      df_exibicao = df_rank[["Posição", "Nome", "Total"]].copy()
      df_exibicao["Total"] = df_exibicao["Total"].astype(int)
      df_exibicao.rename(
          columns={"Nome": "Jogador", "Total": "Pontuação Total"}, inplace=True
      )

      if busca_player.strip():
        df_exibicao = df_exibicao[
            df_exibicao["Jogador"]
            .str.lower()
            .str.contains(busca_player.strip().lower())
        ]

      altura_dinamica = max(450, len(df_exibicao) * 48 + 250)

      # RENDERIZA A TABELA COM BOTÃO DE DOWNLOAD HD E DESTAQUE NO TOP 3
      components.html(
          gerar_tabela_bilhete_dourado(df_exibicao),
          height=altura_dinamica,
          scrolling=True,
      )

  # ABA 2: TABELA DETALHADA GERAL
  with tab_tabela:
    if not df.empty and "Total" in df.columns:
      st.markdown("### 📋 Tabela Detalhada Geral de Pontuações")
      st.markdown(
          "Acompanhe os pontos por atividade. No celular, **Nome** e **Total** "
          "permanecem fixos enquanto você desliza para visualizar as atividades."
      )

      cols_exibicao = (
          ["Nome"]
          + [c for c in ["JogosCla", "Eventos"] if c in df.columns]
          + colunas_guerras
          + colunas_liga
          + colunas_raides
          + ["Total"]
      )
      df_detalhada = df[cols_exibicao].sort_values(
          by="Total", ascending=False
      ).reset_index(drop=True)

      _, col_busca, _ = st.columns([1, 2, 1])
      with col_busca:
        busca_detalhada = st.text_input(
            "🔎 Localizar jogador",
            placeholder="Digite parte do nome para localizar...",
            key="busca_tabela_detalhada",
        ).strip().lower()

      if busca_detalhada:
        mascara = df_detalhada["Nome"].astype(str).str.lower().str.contains(
            busca_detalhada, regex=False, na=False
        )
        df_tabela_mobile = df_detalhada[mascara].copy()
      else:
        df_tabela_mobile = df_detalhada.copy()

      from html import escape

      def rotulo_coluna(col):
        if col == "JogosCla":
          return "Jogos"
        if col == "Eventos":
          return "Eventos"
        if col == "Total":
          return "TOTAL"
        prefixos = {
            "Guerra_": "Guerra ",
            "Liga_": "Liga ",
            "Raide_": "Raide ",
        }
        for prefixo, rotulo in prefixos.items():
          if col.startswith(prefixo):
            identificador = col[len(prefixo):].replace("_", " ")
            return f"{rotulo}{identificador}".strip()
        return col

      headers = [rotulo_coluna(c) for c in cols_exibicao]
      header_html = "".join(
          f'<th class="{"sticky-nome" if i == 0 else "sticky-total" if i == len(cols_exibicao)-1 else ""}">{escape(str(h))}</th>'
          for i, h in enumerate(headers)
      )

      linhas = []
      for idx_m, row in df_tabela_mobile.iterrows():
        nome = str(row["Nome"])
        destaque = " jogador-destaque" if busca_detalhada and busca_detalhada in nome.lower() else ""

        # Destaque para o Top 3 na Tabela Detalhada
        top_class = ""
        prefixo_m = ""
        if idx_m == 0:
          top_class = " top1-detalhada"
          prefixo_m = "🥇 "
        elif idx_m == 1:
          top_class = " top2-detalhada"
          prefixo_m = "🥈 "
        elif idx_m == 2:
          top_class = " top3-detalhada"
          prefixo_m = "🥉 "

        cells = []
        for i, col in enumerate(cols_exibicao):
          valor = row[col]
          try:
            valor = int(float(valor))
          except (TypeError, ValueError):
            valor = str(valor)

          if i == 0:
            str_display = f"{prefixo_m}{escape(str(valor))}"
          else:
            str_display = escape(str(valor))

          classe = "sticky-nome" if i == 0 else "sticky-total" if i == len(cols_exibicao) - 1 else ""
          cells.append(f'<td class="{classe}">{str_display}</td>')
        linhas.append(f'<tr class="{destaque}{top_class}">' + "".join(cells) + "</tr>")

      html_tabela = f"""
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <style>
          * {{ box-sizing: border-box; }}
          body {{ margin: 0; background: transparent; font-family: Arial, sans-serif; }}
          .legenda {{ display:flex; flex-wrap:wrap; gap:6px; margin:0 0 10px; color:#cbd5e1; font-size:12px; line-height:1.3; align-items: center; }}
          .badge {{ padding:5px 9px; border-radius:999px; background:#1e293b; border:1px solid #475569; }}
          .btn-download-img {{
            background: linear-gradient(180deg, #3b82f6 0%, #1d4ed8 100%);
            color: #ffffff;
            border: 1px solid #93c5fd;
            border-radius: 8px;
            padding: 6px 12px;
            font-size: 11px;
            font-weight: bold;
            cursor: pointer;
            box-shadow: 0px 2px 4px rgba(0,0,0,0.3);
            transition: all 0.2s ease;
          }}
          .btn-download-img:hover {{ background: linear-gradient(180deg, #60a5fa 0%, #2563eb 100%); }}
          .viewport {{ width:100%; overflow:auto; max-height:68vh; border:1px solid #334155; border-radius:10px; -webkit-overflow-scrolling:touch; background:#0f172a; }}
          table {{ border-collapse:separate; border-spacing:0; min-width:760px; width:max-content; background:#0f172a; }}
          th,td {{ padding:9px 11px; border-right:1px solid #334155; border-bottom:1px solid #334155; text-align:center; white-space:nowrap; font-size:13px; color:#e2e8f0; background:#0f172a; }}
          thead th {{ background:#1e293b; font-weight:800; position:sticky; z-index:5; }}
          thead tr:first-child th {{ top:0; color:#facc15; font-size:11px; letter-spacing:.5px; height:28px; }}
          thead tr:nth-child(2) th {{ top:28px; color:#f8fafc; height:30px; }}
          tbody tr:nth-child(even) td {{ background:#111827; }}
          tbody tr:hover td {{ background:#1e293b; }}
          .sticky-nome {{ position:sticky !important; left:0; z-index:4; min-width:150px; max-width:150px; text-align:left; font-weight:800; box-shadow:5px 0 8px rgba(0,0,0,.25); background:#0f172a; }}
          thead .sticky-nome {{ z-index:8; background:#1e293b !important; }}
          .sticky-total {{ position:sticky !important; right:0; z-index:4; min-width:85px; font-weight:900; color:#facc15 !important; background:#172554 !important; box-shadow:-5px 0 8px rgba(0,0,0,.25); }}
          thead .sticky-total {{ z-index:8; background:#172554 !important; }}
          .grupo {{ text-align:center; background:#334155 !important; color:#facc15 !important; }}
          .grupo-canto-esq {{ min-width:150px; background:#334155 !important; position:sticky; left:0; z-index:9; }}
          .grupo-canto-dir {{ min-width:85px; background:#334155 !important; position:sticky; right:0; z-index:9; }}
          .jogador-destaque td {{ background:rgba(250,204,21,.18) !important; color:#fff !important; font-weight:900; }}
          .jogador-destaque .sticky-nome,.jogador-destaque .sticky-total {{ background:#713f12 !important; color:#fff !important; }}
          
          /* CORES TOP 3 DETALHADA */
          .top1-detalhada td {{ background: rgba(250, 204, 21, 0.15) !important; font-weight: 800; }}
          .top1-detalhada .sticky-nome {{ color: #fef08a !important; background: #3a2e05 !important; }}
          .top2-detalhada td {{ background: rgba(203, 213, 225, 0.12) !important; font-weight: 800; }}
          .top2-detalhada .sticky-nome {{ color: #f1f5f9 !important; background: #27303f !important; }}
          .top3-detalhada td {{ background: rgba(249, 115, 22, 0.12) !important; font-weight: 800; }}
          .top3-detalhada .sticky-nome {{ color: #ffedd5 !important; background: #431d05 !important; }}

          .vazio {{ padding:28px; text-align:center; color:#94a3b8; background:#0f172a; }}
          @media (max-width:600px) {{
            table {{ min-width:680px; }}
            th,td {{ padding:8px 9px; font-size:12px; }}
            .sticky-nome {{ min-width:130px; max-width:130px; }}
            .sticky-total {{ min-width:75px; }}
          }}
        </style>
      </head>
      <body>
        <div class="legenda">
          <span class="badge"><b>🎮 Jogos</b> = Jogos do Clã</span>
          <span class="badge"><b>🎉 Eventos</b> = Eventos especiais</span>
          <span class="badge"><b>⚔️ Guerra</b> = Pontos de guerras</span>
          <span class="badge"><b>🏆 Liga</b> = Pontos de ligas</span>
          <span class="badge"><b>⚡ Raide</b> = Pontos de Raides</span>
          <button class="btn-download-img" onclick="baixarImagemTabela()">🖼️ Baixar Tabela em HD</button>
        </div>
        <div class="viewport" id="area-tabela">
          <table id="tabela-render">
            <thead>
              <tr>
                <th class="grupo-canto-esq">JOGADOR</th>
                <th colspan="{len(cols_exibicao)-2}" class="grupo">PONTUAÇÃO POR ATIVIDADE</th>
                <th class="grupo-canto-dir">TOTAL</th>
              </tr>
              <tr>{header_html}</tr>
            </thead>
            <tbody>
              {''.join(linhas) if linhas else f'<tr><td colspan="{len(cols_exibicao)}" class="vazio">Nenhum jogador encontrado.</td></tr>'}
            </tbody>
          </table>
        </div>

        <script>
          function baixarImagemTabela() {{
            const btn = document.querySelector('.btn-download-img');
            btn.innerText = "⏳ Gerando imagem...";
            btn.disabled = true;

            const elemento = document.getElementById('tabela-render');

            html2canvas(elemento, {{
              scale: 2,
              useCORS: true,
              backgroundColor: '#0f172a'
            }}).then(canvas => {{
              const link = document.createElement('a');
              link.download = 'tabela_detalhada_winningwars.png';
              link.href = canvas.toDataURL('image/png');
              link.click();

              btn.innerText = "🖼️ Baixar Tabela em HD";
              btn.disabled = false;
            }}).catch(err => {{
              alert('Erro ao gerar imagem: ' + err);
              btn.innerText = "🖼️ Baixar Tabela em HD";
              btn.disabled = false;
            }});
          }}
        </script>
      </body>
      </html>
      """

      altura = min(900, max(300, 150 + len(df_tabela_mobile) * 40))
      components.html(html_tabela, height=altura, scrolling=False)

  # ABA 3: PERFIL INDIVIDUAL / CONQUISTAS
  with tab_perfil:
    renderizar_perfil_membro(df_rank, colunas_guerras, colunas_liga, colunas_raides)

  # ABA 4: AGENDA DO CLÃ
  with tab_agenda:
    renderizar_agenda_membros()

  # ABA 5: ÁREA ADMIN
  with tab_admin:
    st.subheader("🔐 Painel de Controle e Administração")

    if "admin_logado" not in st.session_state:
      st.info(
          "👉 Faça o login clicando no botão **'🔐 Admin'** no canto superior"
          " direito da página para acessar os controles de gestão."
      )
    else:
      st.success(
          f"Sessão Ativa: **{st.session_state['admin_logado']}** (Gerenciamento"
          " Liberado)"
      )

      sub_tab20, sub_tab1, sub_tab2, sub_tab_pass, sub_tab3, sub_tab4, sub_tab_news, sub_tab5, sub_tab6, sub_tab7 = st.tabs([
          "🚀 Gestão 2.0",
          "➕ Players",
          "👤 Novo Admin",
          "🔑 Alterar Senha",
          "✏️ Gerenciar Pontos e Colunas",
          "📢 Recado e Galeria",
          "📰 Gerenciar Novidades",
          "📜 Logs do Sistema",
          "💾 Backup de Dados",
          "🎲 Sorteio de Desempate",
      ])

      with sub_tab20:
        renderizar_gestao_20(df_rank, colunas_guerras, colunas_liga, colunas_raides)

      with sub_tab1:
        c1, c2 = st.columns(2)
        with c1:
          novo_nome = st.text_input("Nome do Player")
          if st.button("Cadastrar Player"):
            if novo_nome.strip() != "":
              ids_existentes = pd.to_numeric(df.get("ID", pd.Series(dtype=float)), errors="coerce").dropna() if not df.empty else pd.Series(dtype=float)
              novo_id = int(ids_existentes.max()) + 1 if not ids_existentes.empty else 1
              cols_atuais = len(sheet_dados.row_values(1))
              sheet_dados.append_row(
                  [novo_id, novo_nome.strip()] + [0] * (cols_atuais - 2)
              )
              registrar_log(
                  st.session_state["admin_logado"],
                  f"Cadastrou player {novo_nome}",
              )
              st.cache_data.clear()
              st.success("Adicionado!")
              st.rerun()
        with c2:
          if not df.empty and "Nome" in df.columns:
            player_rem = st.selectbox("Remover Player", df["Nome"].tolist())
            confirmar_rem = st.checkbox(
                "⚠️ Confirmar exclusão permanente deste jogador"
            )
            if st.button("Remover Player", type="primary"):
              if confirmar_rem:
                cell = sheet_dados.find(player_rem)
                sheet_dados.delete_rows(cell.row)
                registrar_log(
                    st.session_state["admin_logado"],
                    f"Removeu player {player_rem}",
                )
                st.cache_data.clear()
                st.success("Removido com sucesso!")
                st.rerun()
              else:
                st.warning(
                    "Marque a caixa de confirmação para poder remover."
                )

      with sub_tab2:
        st.markdown("#### 👤 Cadastrar Novo Administrador")
        with st.form("form_novo_admin", clear_on_submit=True):
          c_adm1, c_adm2 = st.columns(2)
          with c_adm1:
            novo_admin_usr = st.text_input("Nome do Usuário Admin")
            novo_admin_pwd = st.text_input("Senha", type="password")
          with c_adm2:
            novo_admin_pwd_conf = st.text_input(
                "Confirmar Senha", type="password"
            )

          btn_cadastrar_admin = st.form_submit_button("Criar Usuário Admin")

          if btn_cadastrar_admin:
            usr_limpo = novo_admin_usr.strip()
            pwd_limpo = novo_admin_pwd.strip()

            if not usr_limpo or not pwd_limpo:
              st.error("⚠️ Preencha o nome de usuário e a senha.")
            elif pwd_limpo != novo_admin_pwd_conf.strip():
              st.error("⚠️ As senhas informadas não coincidem.")
            else:
              df_admins_atual = pd.DataFrame(sheet_admins.get_all_records())
              if (
                  not df_admins_atual.empty
                  and usr_limpo.lower()
                  in df_admins_atual["Usuario"].str.lower().values
              ):
                st.error("⚠️ Já existe um administrador com esse usuário!")
              else:
                hash_senha = gerar_hash_seguro(pwd_limpo)
                nivel_novo = "Lider"
                sheet_admins.append_row([usr_limpo, hash_senha, nivel_novo])
                registrar_log(
                    st.session_state["admin_logado"],
                    f"Cadastrou o novo admin '{usr_limpo}'",
                )
                st.cache_data.clear()
                st.success(
                    f"✅ Administrador **{usr_limpo}** cadastrado com sucesso!"
                )
                st.rerun()

      with sub_tab_pass:
        st.markdown(f"#### 🔑 Alterar Senha de Admin (`{st.session_state['admin_logado']}`)")
        with st.form("form_mudar_senha", clear_on_submit=True):
          senha_atual = st.text_input("Senha Atual", type="password")
          nova_senha = st.text_input("Nova Senha", type="password")
          conf_nova_senha = st.text_input("Confirmar Nova Senha", type="password")
          btn_trocar_senha = st.form_submit_button("Atualizar Senha")

          if btn_trocar_senha:
            if not senha_atual or not nova_senha:
              st.error("⚠️ Preencha todos os campos do formulário.")
            elif nova_senha != conf_nova_senha:
              st.error("⚠️ A nova senha e a confirmação não coincidem.")
            else:
              admin_atual = st.session_state["admin_logado"]
              df_admins_atual = pd.DataFrame(sheet_admins.get_all_records())
              
              if not df_admins_atual.empty:
                candidatos = df_admins_atual[df_admins_atual["Usuario"] == admin_atual]
                validacao = candidatos[
                    candidatos["SenhaHash"].apply(lambda h: verificar_senha(senha_atual, h))
                ] if not candidatos.empty else candidatos
                if validacao.empty:
                  st.error("⚠️ Senha atual incorreta!")
                else:
                  cell = sheet_admins.find(admin_atual)
                  if cell:
                    sheet_admins.update_cell(cell.row, 2, gerar_hash_seguro(nova_senha))
                    registrar_log(admin_atual, "Alterou a própria senha de acesso")
                    st.cache_data.clear()
                    st.success("✅ Senha alterada com sucesso!")
                    st.rerun()

      sub_tab3_col1, sub_tab3_col2 = sub_tab3.columns([1, 1])
      with sub_tab3:
        st.markdown("#### ➕ Criar Novas Colunas de Guerras, Liga ou Raides")
        st.markdown(
            "Clique nos botões abaixo para criar automaticamente as próximas"
            " colunas na sequência."
        )

        col_btn1, col_btn2, col_btn3 = st.columns(3)

        with col_btn1:
          proxima_guerra = obter_proxima_coluna_sequencial(
              "Guerra", df.columns if not df.empty else []
          )
          if st.button(
              f"⚔️ Criar Guerra ({proxima_guerra})",
              use_container_width=True,
          ):
            headers = sheet_dados.row_values(1)
            if proxima_guerra in headers:
              st.error(f"⚠️ A coluna {proxima_guerra} já existe!")
            else:
              proxima_col_num = len(headers) + 1
              sheet_dados.update_cell(1, proxima_col_num, proxima_guerra)

              if not df.empty:
                num_linhas = len(df)
                sheet_dados.update(
                    f"{gspread.utils.rowcol_to_a1(2, proxima_col_num)}:{gspread.utils.rowcol_to_a1(num_linhas + 1, proxima_col_num)}",
                    [[0]] * num_linhas,
                )

              registrar_log(
                  st.session_state["admin_logado"],
                  f"Criou a coluna de Guerra Normal '{proxima_guerra}'",
              )
              st.cache_data.clear()
              st.success(
                  f"✅ Coluna **{proxima_guerra}** adicionada com sucesso!"
              )
              st.rerun()

        with col_btn2:
          colunas_liga_existentes = [c for c in (df.columns if not df.empty else []) if c.startswith("Liga_")]
          qtd_liga = len(colunas_liga_existentes)
          
          if qtd_liga >= 7:
            st.info("🔒 **Limite de 7 Guerras de Liga atingido.**")
          else:
            proxima_liga = f"Liga_{qtd_liga + 1}"
            if st.button(
                f"🏆 Criar Liga ({proxima_liga}) [{qtd_liga + 1}/7]",
                use_container_width=True,
            ):
              headers = sheet_dados.row_values(1)
              if proxima_liga in headers:
                st.error(f"⚠️ A coluna {proxima_liga} já existe!")
              else:
                proxima_col_num = len(headers) + 1
                sheet_dados.update_cell(1, proxima_col_num, proxima_liga)

                if not df.empty:
                  num_linhas = len(df)
                  sheet_dados.update(
                      f"{gspread.utils.rowcol_to_a1(2, proxima_col_num)}:{gspread.utils.rowcol_to_a1(num_linhas + 1, proxima_col_num)}",
                      [[0]] * num_linhas,
                  )

                registrar_log(
                    st.session_state["admin_logado"],
                    f"Criou a coluna de Guerra de Liga '{proxima_liga}'",
                )
                st.cache_data.clear()
                st.success(
                    f"✅ Coluna **{proxima_liga}** adicionada com sucesso!"
                )
                st.rerun()

        with col_btn3:
          proxima_raide = obter_proxima_coluna_sequencial(
              "Raide", df.columns if not df.empty else []
          )
          if st.button(
              f"🏰 Criar Raide ({proxima_raide})",
              use_container_width=True,
          ):
            headers = sheet_dados.row_values(1)
            if proxima_raide in headers:
              st.error(f"⚠️ A coluna {proxima_raide} já existe!")
            else:
              proxima_col_num = len(headers) + 1
              sheet_dados.update_cell(1, proxima_col_num, proxima_raide)

              if not df.empty:
                num_linhas = len(df)
                sheet_dados.update(
                    f"{gspread.utils.rowcol_to_a1(2, proxima_col_num)}:{gspread.utils.rowcol_to_a1(num_linhas + 1, proxima_col_num)}",
                    [[0]] * num_linhas,
                )

              registrar_log(
                  st.session_state["admin_logado"],
                  f"Criou a coluna de Raide '{proxima_raide}'",
              )
              st.cache_data.clear()
              st.success(
                  f"✅ Coluna **{proxima_raide}** adicionada com sucesso!"
              )
              st.rerun()

        st.divider()

        st.markdown("#### ✏️ Edição de Pontos dos Jogadores")
        if not df.empty:
          df_editavel = df.drop(
              columns=["Total", "WarTotal"], errors="ignore"
          ).copy()
          df_editado = st.data_editor(
              df_editavel, use_container_width=True, hide_index=True
          )
          if st.button("💾 Salvar Alterações em Lote", type="primary"):
            alteracoes = []
            headers = sheet_dados.row_values(1)
            for idx_row in range(len(df_editado)):
              nome_j = str(df_editado.iloc[idx_row].get("Nome", ""))
              for col in df_editado.columns:
                antes = df_editavel.iloc[idx_row].get(col)
                depois = df_editado.iloc[idx_row].get(col)
                if str(antes) != str(depois):
                  try:
                    cell_nome = sheet_dados.find(nome_j)
                    if cell_nome and col in headers:
                      sheet_dados.update_cell(cell_nome.row, headers.index(col)+1, depois)
                      if col != "Nome": registrar_auditoria_ponto(nome_j, col, antes, depois, "Edição em lote")
                      alteracoes.append(f"{nome_j}/{col}: {antes}→{depois}")
                  except Exception:
                    pass
            registrar_log(st.session_state["admin_logado"], f"Atualizou {len(alteracoes)} campo(s) em lote")
            if alteracoes: snapshot_ranking_atual("alteracao", "Edição em lote")
            st.cache_data.clear()
            st.success(f"✅ {len(alteracoes)} alteração(ões) salva(s) sem apagar a planilha.")
            st.rerun()

      with sub_tab4:
        st.markdown("#### 📢 Atualizar / Excluir Mural de Recados")
        novo_recado = st.text_area("Recado para o topo da tela:", mural_recado)
        col_rec1, col_rec2 = st.columns(2)
        with col_rec1:
          if st.button("Publicar Recado"):
            cell_recado = sheet_estado.find("mural_recado")
            if cell_recado:
              sheet_estado.update_cell(cell_recado.row, 2, novo_recado.strip())
            else:
              sheet_estado.append_row(["mural_recado", novo_recado.strip()])
            registrar_log(
                st.session_state["admin_logado"], "Atualizou mural de recados"
            )
            st.cache_data.clear()
            st.success("Recado publicado!")
            st.rerun()
        with col_rec2:
          if st.button("🗑️ Excluir Recado Atual"):
            cell_recado = sheet_estado.find("mural_recado")
            if cell_recado:
              sheet_estado.update_cell(cell_recado.row, 2, "")
            registrar_log(
                st.session_state["admin_logado"], "Excluiu mural de recados"
            )
            st.cache_data.clear()
            st.success("Recado removido do mural!")
            st.rerun()

        st.divider()

        st.markdown("#### 🌟 Adicionar / Arquivar na Galeria da Fama")
        st.markdown("Você pode **arquivar os campeões do mês atual** ou **incluir manualmente pessoas/premiações extras**!")

        # OPÇÃO A: ARQUIVAR MÊS ATUAL
        with st.expander("🏆 Arquivar Campeões do Mês Atual (Ranking Automático)"):
          mes_ano_ref = st.text_input("Mês/Ano de Referência (Ex: Março/2026)")
          if st.button("🏆 Arquivar Mês Atual na Galeria"):
            if len(df_rank) >= 3 and mes_ano_ref.strip():
              sheet_fama.append_row([
                  mes_ano_ref.strip(),
                  df_rank.iloc[0]["Nome"],
                  df_rank.iloc[1]["Nome"],
                  df_rank.iloc[2]["Nome"],
              ])
              registrar_log(
                  st.session_state["admin_logado"],
                  f"Arquivou campeões do mês {mes_ano_ref}",
              )
              st.cache_data.clear()
              st.success("Registrado na Galeria da Fama com sucesso!")
              st.rerun()

        # OPÇÃO B: INCLUIR MANUALMENTE
        with st.expander("➕ Adicionar Vencedores / Premiação Extra Manualmente"):
          with st.form("form_fama_manual", clear_on_submit=True):
            fama_titulo = st.text_input("Título/Mês (Ex: Torneio Extra - Fev/2026)")
            fama_p1 = st.text_input("🥇 1º Lugar (Ganhador Principal)")
            fama_p2 = st.text_input("🥈 2º Lugar (Opcional)")
            fama_p3 = st.text_input("🥉 3º Lugar (Opcional)")

            btn_fama_manual = st.form_submit_button("Salvar na Galeria da Fama")

            if btn_fama_manual:
              if fama_titulo.strip() and fama_p1.strip():
                sheet_fama.append_row([
                    fama_titulo.strip(),
                    fama_p1.strip(),
                    fama_p2.strip() if fama_p2.strip() else "-",
                    fama_p3.strip() if fama_p3.strip() else "-",
                ])
                registrar_log(
                    st.session_state["admin_logado"],
                    f"Adicionou manual na Galeria da Fama: {fama_titulo}",
                )
                st.cache_data.clear()
                st.success("Adicionado à Galeria da Fama!")
                st.rerun()
              else:
                st.error("⚠️ Preencha pelo menos o Título e o 1º Lugar.")

      # ABA DE GERENCIAMENTO DE NOTÍCIAS / NOVIDADES
      with sub_tab_news:
        st.markdown("#### 📰 Publicar Nova Notícia ou Evento")
        with st.form("form_nova_noticia", clear_on_submit=True):
          noticia_titulo = st.text_input("Título da Notícia")
          noticia_tag = st.selectbox(
              "Categoria / Tag",
              ["🎉 Evento", "⚔️ Torneio", "🚀 Atualização Game", "📢 Aviso Clã", "🏆 Premiação Extra"]
          )
          noticia_conteudo = st.text_area("Conteúdo do Comunicado", height=120)
          noticia_img = st.text_input("Link Direto da Imagem / Banner (Opcional)")

          btn_pub_noticia = st.form_submit_button("Publicar Notícia")

          if btn_pub_noticia:
            if noticia_titulo.strip() and noticia_conteudo.strip():
              d_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
              sheet_novidades.append_row([
                  d_hora,
                  noticia_titulo.strip(),
                  noticia_conteudo.strip(),
                  noticia_img.strip(),
                  noticia_tag,
                  st.session_state["admin_logado"],
              ])
              registrar_log(
                  st.session_state["admin_logado"],
                  f"Publicou notícia '{noticia_titulo}'",
              )
              st.cache_data.clear()
              st.success("✅ Notícia publicada no painel de Novidades!")
              st.rerun()
            else:
              st.error("⚠️ Insira o título e o conteúdo antes de publicar.")

        st.divider()
        st.markdown("#### 🗑️ Gerenciar / Excluir Notícias")
        if not df_novidades.empty:
          for idx_n, row_n in df_novidades.iterrows():
            st.write(f"📌 **{row_n.get('Titulo')}** ({row_n.get('DataHora')})")
            if st.button(
                f"❌ Excluir Notícia #{idx_n + 1}",
                key=f"del_news_{idx_n}",
            ):
              cell_n = sheet_novidades.find(row_n["Titulo"])
              if cell_n:
                sheet_novidades.delete_rows(cell_n.row)
                registrar_log(
                    st.session_state["admin_logado"],
                    f"Excluiu notícia '{row_n['Titulo']}'",
                )
                st.cache_data.clear()
                st.success("Notícia removida!")
                st.rerun()
        else:
          st.info("Nenhuma notícia cadastrada para exclusão.")

      with sub_tab5:
        st.markdown("#### 🛡️ Registro de Atividades dos Admins")
        try:
          df_logs_exib = pd.DataFrame(sheet_logs.get_all_records())
          st.dataframe(
              df_logs_exib.tail(20), use_container_width=True, hide_index=True
          )
        except Exception:
          st.info("Nenhum log registrado ainda.")

      with sub_tab6:
        st.markdown("#### 💾 Exportar Backup do Banco de Dados")
        if not df.empty:
          csv_backup = df.to_csv(index=False).encode("utf-8")
          st.download_button(
              label="📥 Baixar Backup Atual em CSV",
              data=csv_backup,
              file_name=(
                  f"winningwars_backup_{datetime.now().strftime('%Y%m%d')}.csv"
              ),
              mime="text/csv",
          )
        else:
          st.info("Nenhum dado disponível para backup.")

      with sub_tab7:
        st.markdown("#### 🎲 Sorteio de Desempate Transparente (Gravação de Tela)")
        st.info(
            "🎥 **Dica para Gravação:** Inicie a gravação da sua tela antes de"
            " clicar no botão de sorteio para enviar o vídeo ao grupo do WhatsApp"
            " do clã."
        )

        if not df_rank.empty and "Total" in df_rank.columns:
          maior_pontuacao = df_rank["Total"].max()

          df_empatados = df_rank[df_rank["Total"] == maior_pontuacao]
          lista_empatados = df_empatados["Nome"].tolist()
          qtd_empatados = len(lista_empatados)

          st.markdown(f"**Pontuação do Topo:** `{int(maior_pontuacao)} pts`")

          if qtd_empatados <= 1:
            st.success(
                "✅ **Não há empate no 1º lugar!** O líder isolado é:"
                f" **{df_rank.iloc[0]['Nome']}**."
            )
          else:
            st.warning(
                f"⚠️ **Empate Detectado!** Existem **{qtd_empatados} jogadores**"
                f" empatados no topo com {int(maior_pontuacao)} pontos."
            )

            st.markdown("### 👥 Jogadores Participantes do Sorteio:")
            cols_participantes = st.columns(min(qtd_empatados, 4))
            for idx, nome_p in enumerate(lista_empatados):
              with cols_participantes[idx % 4]:
                st.markdown(
                    f"""
                    <div style="background-color: #1e293b; border: 2px solid #facc15; border-radius: 10px; padding: 12px; text-align: center; margin-bottom: 10px;">
                        <span style="font-size: 1.5rem;">⚔️</span><br>
                        <strong style="color: #facc15; font-size: 1.1rem;">{nome_p}</strong><br>
                        <small style="color: #94a3b8;">{int(maior_pontuacao)} pts</small>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.divider()

            qtd_vagas = st.number_input(
                "Número de ganhadores a sortear entre os empatados:",
                min_value=1,
                max_value=qtd_empatados,
                value=1,
                step=1,
            )

            if st.button("🎰 INICIAR SORTEIO AO VIVO", type="primary"):
              status_text = st.empty()
              bar = st.progress(0)

              for i in range(100):
                time.sleep(0.03)
                bar.progress(i + 1)
                if i < 30:
                  status_text.markdown(
                      "### 🎲 Embaralhando nomes dos guerreiros..."
                  )
                elif i < 70:
                  status_text.markdown(
                      "### ⚡ Auditando pontuações e validando..."
                  )
                else:
                  status_text.markdown(
                      "### 🏆 Selecionando o(s) vencedor(es)..."
                  )

              status_text.empty()
              bar.empty()

              vencedores = random.sample(lista_empatados, int(qtd_vagas))

              st.balloons()

              data_hora_sorteio = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
              hash_auditoria = hashlib.sha256(
                  f"{vencedores}{data_hora_sorteio}".encode()
              ).hexdigest()[:12]

              st.markdown(
                  f"""
                  <div style="background: linear-gradient(135deg, #15803d 0%, #166534 100%); border: 3px solid #86efac; border-radius: 15px; padding: 25px; text-align: center; margin-top: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
                      <h2 style="color: #facc15; font-family: 'Luckiest Guy', cursive; margin-bottom: 5px;">🎉 GANHADOR(ES) DO SORTEIO 🎉</h2>
                      <h1 style="color: #ffffff; font-size: 2.5rem; margin: 10px 0;">{", ".join(vencedores)}</h1>
                      <p style="color: #dcfce7; font-size: 1.1rem;">Parabéns! Vencedor(es) do desempate pelo Passe Dourado 🎟️</p>
                      <hr style="border-color: #22c55e; margin: 15px 0;">
                      <small style="color: #93c5fd;">🕒 <b>Data/Hora do Sorteio:</b> {data_hora_sorteio}<br>🔑 <b>Código de Verificação:</b> {hash_auditoria.upper()}</small>
                  </div>
                  """,
                  unsafe_allow_html=True,
              )

              registrar_log(
                  st.session_state["admin_logado"],
                  f"Realizou sorteio de desempate entre {lista_empatados}. Vencedor(es): {vencedores} (Hash: {hash_auditoria.upper()})",
              )
        else:
          st.info("Nenhum dado de ranking encontrado para realizar o sorteio.")

  # FEED DE NOVIDADES NA PÁGINA PRINCIPAL
  # Fica abaixo do ranking/tabela e concentra os comunicados sem exigir
  # navegação para outra página.
  st.write("---")
  renderizar_feed_novidades()

  # SEÇÃO EXPLICATIVA (RODAPÉ)
  st.write("---")
  st.markdown(
      "<h2 style='text-align: center;'>📜 Regulamento & Sistema de"
      " Premiação</h2>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='text-align: center; color: #cbd5e1;'>A ideia é simples:"
      " valorizar quem joga bem, participa ativamente e ajuda o clã a"
      " crescer!</p><br>",
      unsafe_allow_html=True,
  )

  info_col1, info_col2, info_col3 = st.columns(3)

  with info_col1:
    st.markdown(
        """
        <div class="info-card" style="text-align: center;">
            <img src="https://i.ibb.co/mkC43vT/goldenpass.png" width="60" style="margin-bottom: 8px;">
            <div class="info-card-header">🏆 Premiação Mensal</div>
            <ul class="info-card-list" style="text-align: left;">
                <li><b>Top 3 Destaques:</b> Garantem <b>1 Passe Dourado 🎟️</b> cada um no final do mês.</li>
                <li><b>Em caso de Empate:</b> Sorteio de desempate.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

  with info_col2:
    st.markdown(
        """
        <div class="info-card" style="text-align: center;">
            <img src="https://i.ibb.co/3PPkJD8/War-League-Main-Banner.webp" width="75" style="margin-bottom: 8px;">
            <div class="info-card-header">📊 Sistema de Pontuação</div>
            <ul class="info-card-list" style="text-align: left;">
                <li><b>⚔️ Guerras & Liga (CWL):</b> 1 Ponto por ⭐ conquistada.</li>
                <li><b>🎯 Jogos do Clã:</b> Meta = <b>5 pts</b> | Bateu limite total = <b>10 pts</b>.</li>
                <li><b>🛡️ Raides (FDS):</b> Concluiu os 6 ataques = <b>10 pts</b>.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

  with info_col3:
    st.markdown(
        """
        <div class="info-card" style="text-align: center;">
            <img src="https://i.ibb.co/YFbsJ97x/Clash-of-Clans-emblem.png" width="60" style="margin-bottom: 8px;">
            <div class="info-card-header">📜 Diretrizes Básicas</div>
            <ul class="info-card-list" style="text-align: left;">
                <li><b>Conta Principal:</b> Válido estritamente para a conta principal.</li>
                <li><b>Zero Trapaça 🚫:</b> Qualquer ato antidesportivo anula a pontuação.</li>
                <li><b>WhatsApp Obrigatório 📱:</b> Indispensável estar no grupo do clã.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

  # GALERIA DA FAMA FORMATADA COM DESTAQUE
  st.write("---")
  st.markdown(
      "<h2 style='text-align: center;'>🌟 Galeria da Fama</h2>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='text-align: center; color: #cbd5e1;'>Histórico dos grandes"
      " guerreiros do clã que conquistaram o Passe Dourado!</p><br>",
      unsafe_allow_html=True,
  )

  if not df_fama.empty:
    df_fama_exib = df_fama.copy()
    if "Primeiro" in df_fama_exib.columns:
      df_fama_exib["Primeiro"] = "🥇 " + df_fama_exib["Primeiro"].astype(str)
    if "Segundo" in df_fama_exib.columns:
      df_fama_exib["Segundo"] = "🥈 " + df_fama_exib["Segundo"].astype(str)
    if "Terceiro" in df_fama_exib.columns:
      df_fama_exib["Terceiro"] = "🥉 " + df_fama_exib["Terceiro"].astype(str)

    df_fama_exib.rename(
        columns={
            "MesAno": "Mês / Edição",
            "Primeiro": "1º Lugar (Campeão)",
            "Segundo": "2º Lugar",
            "Terceiro": "3º Lugar",
        },
        inplace=True,
    )
    st.dataframe(df_fama_exib, use_container_width=True, hide_index=True)
  else:
    st.info("Nenhum histórico de meses anteriores registrado ainda.")

  # LINKS EXTERNOS / ATALHOS — MANTIDOS NO FINAL DA PÁGINA
  st.write("---")
  st.markdown(
      "<h3 style='text-align: center;'>🔗 Links Rápidos</h3>",
      unsafe_allow_html=True,
  )
  c_link1, c_link2, c_link3, c_link4 = st.columns(4)

  with c_link1:
    st.markdown(
        '<a href="https://www.youtube.com/@winningwarscoc?sub_confirmation=1" '
        'target="_blank" rel="noopener noreferrer" class="btn-youtube-link"><img '
        'src="https://img.cdndsgni.com/preview/10000151.jpg" '
        'height="20" style="border-radius: 4px; object-fit: cover;"> Canal Winning Wars YT ↗</a>',
        unsafe_allow_html=True,
    )

  with c_link2:
    if st.button("📜 Regras do Clã", use_container_width=True, key="bottom_regras_cla"):
      st.session_state["pagina_atual"] = "regras_cla"
      st.rerun()

  with c_link3:
    st.markdown(
        '<a href="https://link.clashofclans.com/?action=OpenSCID&p=25-1cb8481f-3a79-4681-90f9-8914acef2d63" '
        'target="_blank" rel="noopener noreferrer" class="btn-scid"><img '
        'src="https://i.ibb.co/fzPGy6fr/bg-hero-scid-landing-0.webp" '
        'height="20" style="border-radius: 4px; object-fit: cover;"> Add no Supercell ID ↗</a>',
        unsafe_allow_html=True,
    )

  with c_link4:
    st.markdown(
        '<a href="https://chat.whatsapp.com/FKFc5y323PCBnTFdsjhv64" '
        'target="_blank" rel="noopener noreferrer" class="btn-whatsapp-link"><img '
        'src="https://img.cdndsgni.com/preview/10000484.jpg" '
        'height="20" style="border-radius: 4px; object-fit: cover;"> Grupo do Clã no Whats ↗</a>',
        unsafe_allow_html=True,
    )
