import hashlib
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
    page_title="Winning Wars APP", page_icon="⚔️", layout="wide"
)


# --- FUNÇÕES AUXILIARES ---
def gerar_hash(senha: str) -> str:
  return hashlib.sha256(senha.encode()).hexdigest()


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
        title="Admins", rows="100", cols="2"
    )
    sheet_admins.append_row(["Usuario", "SenhaHash"])
    sheet_admins.append_row(["admin", gerar_hash(SENHA_ADMIN_INICIAL)])

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
        ["mural_recado", "Bem-vindos ao aplicativo oficial!"]
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

  return (
      sheet_dados,
      sheet_admins,
      sheet_estado,
      sheet_layouts,
      sheet_logs,
      sheet_fama,
      sheet_novidades,
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


dados = obter_dados_cached()
df = pd.DataFrame(dados) if dados else pd.DataFrame()

try:
  dados_admins = sheet_admins.get_all_records()
  df_admins = pd.DataFrame(dados_admins)
except Exception:
  df_admins = pd.DataFrame(
      [["admin", gerar_hash(SENHA_ADMIN_INICIAL)]], columns=["Usuario", "SenhaHash"]
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


# --- ESTILIZAÇÃO CSS CUSTOMIZADA ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Luckiest+Guy&family=Nunito:wght@600;800;900&display=swap');

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

# --- TOPO DA PÁGINA: MENU SIMPLIFICADO ---
col_nav, col_admin_top = st.columns([6, 1])

with col_nav:
  b1, b2, b3 = st.columns([1, 1, 1])
  with b1:
    if st.button("🛡️ Layouts Guerra", use_container_width=True):
      st.session_state["pagina_atual"] = "layouts_guerra"
      st.rerun()
  with b2:
    if st.button("🏆 Layouts Rankeada", use_container_width=True):
      st.session_state["pagina_atual"] = "layouts_rankeada"
      st.rerun()
  with b3:
    st.markdown(
        '<a href="https://link.clashofclans.com/pt?action=OpenClanProfile&tag=2YPL9GU8Y" target="_blank" class="btn-external-link">🏰 Clã Vastaya ↗</a>',
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
                f"<div style='text-align: center; margin-bottom: 8px;'><b>👑 Enviado por:</b> {row['Autor']}</div>",
                unsafe_allow_html=True,
            )

            img_url_limpa = str(row["ImagemUrl"]).strip()
            if img_url_limpa:
              try:
                st.markdown(
                    f"""
                    <div style="text-align: center; margin-bottom: 12px;">
                        <img src="{img_url_limpa}" style="max-width: 100%; border-radius: 12px; border: 2px solid #334155; box-shadow: 0 4px 12px rgba(0,0,0,0.5);">
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
              except Exception:
                pass

            st.markdown(
                f"""
                <a href="{row['Link']}" target="_blank" class="btn-layout-copy">
                    📋 COPIAR ESTE LAYOUT PARA O JOGO ↗
                </a>
                <br><br>
                """,
                unsafe_allow_html=True,
            )

            if eh_admin:
              if st.button(
                  f"🗑️ Excluir Layout #{item_idx}",
                  key=f"del_{tipo_layout}_{cv_nome}_{item_idx}",
              ):
                df_atualizado = df_layouts.drop(item_idx)
                sheet_layouts.clear()
                sheet_layouts.append_row([
                    "Tipo",
                    "CV",
                    "Autor",
                    "Link",
                    "Descricao",
                    "ImagemUrl",
                    "Tag",
                ])
                if not df_atualizado.empty:
                  sheet_layouts.append_rows(df_atualizado.values.tolist())
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
# COMPONENTE DE NOVIDADES / FEED DE NOTÍCIAS
# ==============================================================================
def renderizar_feed_novidades():
  st.write("---")
  st.markdown(
      "<h2 style='text-align: center;'>📰 Novidades, Torneios & Eventos</h2>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='text-align: center; color: #cbd5e1;'>Fique por dentro das atualizações do Clash of Clans, eventos internos e comunicados da liderança do clã!</p><br>",
      unsafe_allow_html=True,
  )

  eh_admin = "admin_logado" in st.session_state

  # PAINEL ADMINISTRATIVO DIRETO NO FEED
  if eh_admin:
    with st.expander("🔐 [ADMIN] Publicar Nova Novidade", expanded=False):
      with st.form("form_nova_novidade_pagina", clear_on_submit=True):
        noticia_titulo = st.text_input("Título da Notícia")
        noticia_tag = st.selectbox(
            "Categoria / Tag",
            [
                "🎉 Evento",
                "⚔️ Torneio",
                "🚀 Atualização Game",
                "📢 Aviso Clã",
                "🏆 Premiação Extra",
            ],
        )
        noticia_conteudo = st.text_area("Conteúdo do Comunicado", height=140)
        noticia_img = st.text_input(
            "Link Direto da Imagem / Banner (Opcional)",
            placeholder="https://exemplo.com/imagem.jpg",
        )

        btn_pub = st.form_submit_button(
            "📢 Publicar Notícia", use_container_width=True
        )

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
                f"Publicou notícia: {noticia_titulo.strip()}",
            )
            st.cache_data.clear()
            st.success("Notícia publicada com sucesso!")
            st.rerun()
          else:
            st.error("⚠️ Título e conteúdo são obrigatórios.")

  if not df_novidades.empty:
    novidades_exib = df_novidades.iloc[::-1]

    for item_idx, row in novidades_exib.iterrows():
      titulo = str(row.get("Titulo", "")).strip()
      conteudo = str(row.get("Conteudo", "")).strip()
      img_url = str(row.get("ImagemUrl", "")).strip()
      tag = str(row.get("Tag", "📢 Aviso Clã")).strip()
      data_hora = str(row.get("DataHora", "")).strip()
      autor = str(row.get("Autor", "Liderança")).strip()

      img_html = ""
      if img_url:
        img_html = f'<div style="margin-top: 15px; text-align: center;"><img src="{img_url}" style="max-width: 100%; border-radius: 10px; border: 1px solid #334155;"></div>'

      st.markdown(
          f"""
          <div class="news-card">
              <span class="news-tag">{tag}</span>
              <div class="news-title">{titulo}</div>
              <div class="news-meta">📅 {data_hora} | ✍️ {autor}</div>
              <div style="color: #e2e8f0; font-size: 1.05rem; white-space: pre-line;">{conteudo}</div>
              {img_html}
          </div>
          """,
          unsafe_allow_html=True,
      )

      if eh_admin:
        with st.expander(
            f"🛠️ [ADMIN] Gerenciar Postagem #{item_idx} - {titulo[:20]}..."
        ):
          with st.form(key=f"form_edit_post_{item_idx}"):
            edit_titulo = st.text_input(
                "Título", value=titulo, key=f"edit_tit_{item_idx}"
            )
            tags_disponiveis = [
                "🎉 Evento",
                "⚔️ Torneio",
                "🚀 Atualização Game",
                "📢 Aviso Clã",
                "🏆 Premiação Extra",
            ]
            tag_index = (
                tags_disponiveis.index(tag) if tag in tags_disponiveis else 0
            )
            edit_tag = st.selectbox(
                "Categoria / Tag",
                tags_disponiveis,
                index=tag_index,
                key=f"edit_tag_{item_idx}",
            )
            edit_conteudo = st.text_area(
                "Conteúdo",
                value=conteudo,
                height=140,
                key=f"edit_conteudo_{item_idx}",
            )
            edit_img = st.text_input(
                "Link da Imagem / Banner",
                value=img_url,
                key=f"edit_img_{item_idx}",
            )

            c_edit, c_del = st.columns(2)
            with c_edit:
              btn_editar = st.form_submit_button(
                  "💾 Salvar Alterações", use_container_width=True
              )
            with c_del:
              btn_excluir = st.form_submit_button(
                  "🗑️ Excluir Postagem", use_container_width=True
              )

            if btn_editar:
              df_novidades.loc[
                  item_idx,
                  ["Titulo", "Tag", "Conteudo", "ImagemUrl"],
              ] = [
                  edit_titulo.strip(),
                  edit_tag,
                  edit_conteudo.strip(),
                  edit_img.strip(),
              ]
              sheet_novidades.clear()
              sheet_novidades.append_row([
                  "DataHora",
                  "Titulo",
                  "Conteudo",
                  "ImagemUrl",
                  "Tag",
                  "Autor",
              ])
              sheet_novidades.append_rows(df_novidades.values.tolist())
              registrar_log(
                  st.session_state["admin_logado"],
                  f"Editou notícia: {edit_titulo.strip()}",
              )
              st.cache_data.clear()
              st.success("Alterações salvas!")
              st.rerun()

            if btn_excluir:
              df_atualizado = df_novidades.drop(item_idx)
              sheet_novidades.clear()
              sheet_novidades.append_row([
                  "DataHora",
                  "Titulo",
                  "Conteudo",
                  "ImagemUrl",
                  "Tag",
                  "Autor",
              ])
              if not df_atualizado.empty:
                sheet_novidades.append_rows(df_atualizado.values.tolist())
              registrar_log(
                  st.session_state["admin_logado"],
                  f"Excluiu notícia: {titulo}",
              )
              st.cache_data.clear()
              st.success("Postagem excluída!")
              st.rerun()
  else:
    st.info("Nenhuma novidade publicada no momento. Volte em breve!")


# ==============================================================================
# PÁGINA EXCLUSIVA: REGRAS DO CLÃ
# ==============================================================================
def renderizar_pagina_regras():
  if st.button("⬅️ Voltar ao Início"):
    st.session_state["pagina_atual"] = "principal"
    st.rerun()

  st.markdown(
      "<h1 style='text-align: center;'>📜 Regras Oficiais do Clã Vastaya</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='text-align: center; color: #cbd5e1;'>Guia de convivência e"
      " diretrizes para garantir a ordem, respeito e excelência no clã!</p>",
      unsafe_allow_html=True,
  )

  st.markdown(
      """
      <div class="rules-card">
          <div class="rules-title">📌 Diretrizes do Clã</div>
          <ul>
              <li><b>1. Respeito Acima de Tudo:</b> É estritamente proibido insultar, ofender ou desrespeitar qualquer membro do clã, independente da situação.</li>
              <li><b>2. Participação nas Guerras:</b> Se marcou o escudo como VERDE, o uso dos 2 ataques é OBRIGATÓRIO. Caso prefira não participar, mantenha o escudo VERMELHO.</li>
              <li><b>3. Ataques Estratégicos:</b> Respeite a ordem e estratégia definidas pela Liderança/Co-líderes nas Guerras e CWL. Ataques por vila/espelho devem seguir os alvos definidos.</li>
              <li><b>4. Doações Conscientes:</b> Apenas doe tropas no nível ou especificação pedida. Respeite as requisições de Castelo do Clã.</li>
              <li><b>5. Jogos do Clã:</b> A meta individual mínima é de 1.000 pontos em todas as edições dos Jogos do Clã para ajudar no baú máximo.</li>
              <li><b>6. Inatividade sem Aviso:</b> Ausências não justificadas à liderança por mais de 5 dias podem resultar em rebaixamento ou remoção do clã.</li>
          </ul>
      </div>
      """,
      unsafe_allow_html=True,
  )


# --- ROTEAMENTO DE PÁGINAS ---
if st.session_state["pagina_atual"] == "layouts_guerra":
  renderizar_pagina_layouts("Guerra", "🛡️ Layouts de Guerra")
  st.stop()
elif st.session_state["pagina_atual"] == "layouts_rankeada":
  renderizar_pagina_layouts("Rankeada", "🏆 Layouts Rankeada")
  st.stop()
elif st.session_state["pagina_atual"] == "regras_cla":
  renderizar_pagina_regras()
  st.stop()

# ==============================================================================
# PÁGINA PRINCIPAL
# ==============================================================================
st.markdown(
    "<h1 class='main-title'>🏆 Winning Wars APP</h1>", unsafe_allow_html=True
)
st.markdown(
    "<p class='main-subtitle'>Acompanhe a pontuação dos guerreiros no Passe"
    " Dourado de Clash of Clans!</p>",
    unsafe_allow_html=True,
)

eh_admin = "admin_logado" in st.session_state

# --- MURAL DE RECADOS DA LIDERANÇA ---
if mural_recado:
  st.markdown(
      f"""
        <div class="mural-banner">
            <div class="mural-header">📢 Mural da Liderança:</div>
            <div style="color: #e2e8f0; font-size: 1.05rem;">{mural_recado}</div>
        </div>
        """,
      unsafe_allow_html=True,
  )

# --- PAINEL DE CONTROLE ADMINISTRATIVO NO TOPO ---
if eh_admin:
  with st.expander("🛠️ Painel de Controle Administrativo (Aba Principal)"):
    st.markdown("### 📢 Atualizar Mural de Recados")
    with st.form("form_mural"):
      novo_mural = st.text_area("Mensagem para o clã", value=mural_recado)
      if st.form_submit_button("Salvar Mural"):
        try:
          cell = sheet_estado.find("mural_recado")
          sheet_estado.update_cell(cell.row, cell.col + 1, novo_mural.strip())
        except Exception:
          sheet_estado.append_row(["mural_recado", novo_mural.strip()])
        registrar_log(
            st.session_state["admin_logado"], "Atualizou o mural de recados"
        )
        st.cache_data.clear()
        st.success("Mural atualizado!")
        st.rerun()

    st.write("---")
    st.markdown("### 👥 Gerenciar Jogadores")
    col_cad1, col_cad2 = st.columns(2)
    with col_cad1:
      with st.form("form_add_jogador"):
        novo_nome = st.text_input("Nome do Novo Jogador")
        if st.form_submit_button("➕ Adicionar Jogador"):
          if novo_nome.strip():
            nova_linha = [novo_nome.strip()] + [0] * (
                len(df.columns) - 1 if not df.empty else 0
            )
            sheet_dados.append_row(nova_linha)
            registrar_log(
                st.session_state["admin_logado"],
                f"Adicionou o jogador {novo_nome.strip()}",
            )
            st.cache_data.clear()
            st.success("Jogador adicionado!")
            st.rerun()

    with col_cad2:
      if not df.empty and "Jogador" in df.columns:
        with st.form("form_rem_jogador"):
          jogador_remover = st.selectbox(
              "Remover Jogador", df["Jogador"].tolist()
          )
          if st.form_submit_button("🗑️ Remover Jogador"):
            try:
              cell = sheet_dados.find(jogador_remover)
              sheet_dados.delete_rows(cell.row)
              registrar_log(
                  st.session_state["admin_logado"],
                  f"Removeu o jogador {jogador_remover}",
              )
              st.cache_data.clear()
              st.success("Jogador removido!")
              st.rerun()
            except Exception:
              st.error("Erro ao remover.")

    st.write("---")
    st.markdown("### ⚔️ Adicionar Novas Colunas de Evento")
    col_btn1, col_btn2, col_btn3 = st.columns(3)

    with col_btn1:
      colunas_guerra_existentes = [
          c
          for c in (df.columns if not df.empty else [])
          if c.startswith("Guerra_")
      ]
      proxima_guerra = obter_proxima_coluna_sequencial(
          "Guerra", colunas_guerra_existentes
      )
      if st.button(f"➕ Criar {proxima_guerra}", use_container_width=True):
        headers = sheet_dados.row_values(1)
        if proxima_guerra in headers:
          st.error(f"A coluna {proxima_guerra} já existe!")
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
          st.success(f"✅ Coluna **{proxima_guerra}** adicionada com sucesso!")
          st.rerun()

    with col_btn2:
      colunas_liga_existentes = [
          c for c in (df.columns if not df.empty else []) if c.startswith("Liga_")
      ]
      qtd_liga = len(colunas_liga_existentes)
      if qtd_liga >= 7:
        st.warning("⚠️ Limite de 7 rodadas de Liga atingido!")
      else:
        proxima_liga = obter_proxima_coluna_sequencial(
            "Liga", colunas_liga_existentes
        )
        if st.button(f"➕ Criar {proxima_liga}", use_container_width=True):
          headers = sheet_dados.row_values(1)
          if proxima_liga in headers:
            st.error(f"A coluna {proxima_liga} já existe!")
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
                f"Criou a coluna de Liga '{proxima_liga}'",
            )
            st.cache_data.clear()
            st.success(f"✅ Coluna **{proxima_liga}** adicionada com sucesso!")
            st.rerun()

    with col_btn3:
      colunas_extra_existentes = [
          c
          for c in (df.columns if not df.empty else [])
          if c.startswith("Extra_")
      ]
      proxima_extra = obter_proxima_coluna_sequencial(
          "Extra", colunas_extra_existentes
      )
      if st.button(f"➕ Criar {proxima_extra}", use_container_width=True):
        headers = sheet_dados.row_values(1)
        if proxima_extra in headers:
          st.error(f"A coluna {proxima_extra} já existe!")
        else:
          proxima_col_num = len(headers) + 1
          sheet_dados.update_cell(1, proxima_col_num, proxima_extra)
          if not df.empty:
            num_linhas = len(df)
            sheet_dados.update(
                f"{gspread.utils.rowcol_to_a1(2, proxima_col_num)}:{gspread.utils.rowcol_to_a1(num_linhas + 1, proxima_col_num)}",
                [[0]] * num_linhas,
            )
          registrar_log(
              st.session_state["admin_logado"],
              f"Criou a coluna Extra '{proxima_extra}'",
          )
          st.cache_data.clear()
          st.success(f"✅ Coluna **{proxima_extra}** adicionada com sucesso!")
          st.rerun()

    st.write("---")
    st.markdown("### 🗑️ Excluir Colunas de Evento")
    if not df.empty:
      colunas_excluiveis = [
          c
          for c in df.columns
          if c.startswith(("Guerra_", "Liga_", "Extra_")) or c == "Doacoes"
      ]
      if colunas_excluiveis:
        with st.form("form_deletar_coluna"):
          col_para_deletar = st.selectbox(
              "Selecione a coluna para remover", colunas_excluiveis
          )
          btn_del_col = st.form_submit_button("🗑️ Confirmar Exclusão de Coluna")
          if btn_del_col:
            try:
              headers = sheet_dados.row_values(1)
              if col_para_deletar in headers:
                col_idx = headers.index(col_para_deletar) + 1
                sheet_dados.delete_columns(col_idx)
                registrar_log(
                    st.session_state["admin_logado"],
                    f"Excluiu a coluna '{col_para_deletar}'",
                )
                st.cache_data.clear()
                st.success(
                    f"✅ Coluna **{col_para_deletar}** excluída com sucesso!"
                )
                st.rerun()
              else:
                st.error("Coluna não encontrada no banco.")
            except Exception as err:
              st.error(f"Erro ao excluir coluna: {err}")
      else:
        st.info("Nenhuma coluna customizada disponível para exclusão.")

    st.write("---")
    st.markdown("### 🔒 Finalização do Mês")
    if mes_finalizado:
      st.warning(
          "⚠️ **O mês atual está FINALIZADO.** Apenas leitura ativada para"
          " membros."
      )
      if st.button("🔓 Reabrir Mês Atual"):
        try:
          cell = sheet_estado.find("mes_finalizado")
          sheet_estado.update_cell(cell.row, cell.col + 1, "FALSE")
        except Exception:
          sheet_estado.append_row(["mes_finalizado", "FALSE"])
        registrar_log(st.session_state["admin_logado"], "Reabriu o mês atual")
        st.cache_data.clear()
        st.rerun()
    else:
      if st.button("🔒 Finalizar Mês Atual (Travar Edição)"):
        try:
          cell = sheet_estado.find("mes_finalizado")
          sheet_estado.update_cell(cell.row, cell.col + 1, "TRUE")
        except Exception:
          sheet_estado.append_row(["mes_finalizado", "TRUE"])

        if not df.empty and "Pontuação Total" in df.columns:
          df_rank = df.sort_values(by="Pontuação Total", ascending=False)
          nomes = df_rank["Jogador"].tolist()
          p1 = nomes[0] if len(nomes) > 0 else "-"
          p2 = nomes[1] if len(nomes) > 1 else "-"
          p3 = nomes[2] if len(nomes) > 2 else "-"
          mes_ano = datetime.now().strftime("%m/%Y")
          sheet_fama.append_row([mes_ano, p1, p2, p3])

        registrar_log(
            st.session_state["admin_logado"],
            "Finalizou o mês atual e salvou no histórico",
        )
        st.cache_data.clear()
        st.success("Mês finalizado e gravado na Galeria da Fama!")
        st.rerun()

# --- PROCESSAMENTO DOS DADOS DO RANKING ---
if not df.empty and "Jogador" in df.columns:
  colunas_guerra = [c for c in df.columns if c.startswith("Guerra_")]
  colunas_liga = [c for c in df.columns if c.startswith("Liga_")]
  colunas_extra = [c for c in df.columns if c.startswith("Extra_")]

  has_doacoes = "Doacoes" in df.columns
  has_doacoes_flag = "Doacoes_flag" in df.columns

  for col in colunas_guerra + colunas_liga + colunas_extra:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

  if has_doacoes:
    df["Doacoes"] = pd.to_numeric(df["Doacoes"], errors="coerce").fillna(0)

  df["Pontos_Guerra"] = (
      df[colunas_guerra].sum(axis=1) if colunas_guerra else 0
  )
  df["Pontos_Liga"] = df[colunas_liga].sum(axis=1) if colunas_liga else 0
  df["Pontos_Extra"] = df[colunas_extra].sum(axis=1) if colunas_extra else 0
  df["Pontos_Doacoes"] = df["Doacoes"] if has_doacoes else 0

  df["Pontuação Total"] = (
      df["Pontos_Guerra"]
      + df["Pontos_Liga"]
      + df["Pontos_Extra"]
      + df["Pontos_Doacoes"]
  )

  df_sorted = df.sort_values(
      by=["Pontuação Total", "Jogador"], ascending=[False, True]
  ).reset_index(drop=True)
  df_sorted["Posição"] = [f"{i+1}º" for i in range(len(df_sorted))]

  # TABELA RESUMIDA
  cols_resumida = ["Posição", "Jogador", "Pontuação Total"]
  df_resumida = df_sorted[cols_resumida].copy()

  # TABELA DETALHADA
  cols_detalhada = (
      ["Posição", "Jogador"]
      + colunas_guerra
      + colunas_liga
      + (["Doacoes"] if has_doacoes else [])
      + colunas_extra
      + ["Pontuação Total"]
  )
  df_detalhada = df_sorted[cols_detalhada].copy()

  # MODO DE EDIÇÃO PARA ADMIN
  if eh_admin and not mes_finalizado:
    st.markdown("### ✏️ Edição Rápida de Pontuação (Modo Admin)")
    cols_editaveis = (
        colunas_guerra
        + colunas_liga
        + (["Doacoes"] if has_doacoes else [])
        + colunas_extra
    )

    if cols_editaveis:
      edited_df = st.data_editor(
          df_sorted[["Jogador"] + cols_editaveis],
          use_container_width=True,
          hide_index=True,
      )

      if st.button("💾 Salvar Alterações na Planilha", type="primary"):
        try:
          all_records = sheet_dados.get_all_records()
          df_banco = pd.DataFrame(all_records)

          for _, row_edited in edited_df.iterrows():
            nome = row_edited["Jogador"]
            idx_banco = df_banco[df_banco["Jogador"] == nome].index
            if not idx_banco.empty:
              r_idx = idx_banco[0] + 2
              for col_name in cols_editaveis:
                c_idx = df_banco.columns.get_loc(col_name) + 1
                val = row_edited[col_name]
                sheet_dados.update_cell(r_idx, c_idx, int(val))

          registrar_log(
              st.session_state["admin_logado"],
              "Editou pontuações diretamente na tabela",
          )
          st.cache_data.clear()
          st.success("Salvo com sucesso!")
          st.rerun()
        except Exception as e:
          st.error(f"Erro ao salvar: {e}")

  # --- EXIBIÇÃO DA TABELA DO RANKING ---
  st.write("---")
  st.markdown(
      "<h2 style='text-align: center;'>📊 Tabela Completa do Ranking</h2>",
      unsafe_allow_html=True,
  )

  from html import escape

  def montar_tabela_detalhada_html(df_det):
    linhas = []
    cols_exibicao = [c for c in df_det.columns if c != "Posição"]

    for idx, row in df_det.iterrows():
      pos = idx + 1
      top_class = ""
      prefixo_m = ""

      if pos == 1:
        top_class = " top1-detalhada"
        prefixo_m = "🥇 "
      elif pos == 2:
        top_class = " top2-detalhada"
        prefixo_m = "🥈 "
      elif pos == 3:
        top_class = " top3-detalhada"
        prefixo_m = "🥉 "

      destaque = "linha-par" if pos % 2 == 0 else "linha-impar"
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

        classe = (
            "sticky-nome"
            if i == 0
            else "sticky-total"
            if i == len(cols_exibicao) - 1
            else ""
        )
        cells.append(f'<td class="{classe}">{str_display}</td>')

      linhas.append(
          f'<tr class="{destaque}{top_class}">' + "".join(cells) + "</tr>"
      )

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
          margin-left: auto;
        }}
        .table-container {{
          width: 100%;
          max-height: 580px;
          overflow: auto;
          border-radius: 12px;
          border: 1px solid #334155;
          box-shadow: 0 4px 14px rgba(0,0,0,0.35);
          background: #0f172a;
        }}
        table {{
          width: 100%;
          border-collapse: separate;
          border-spacing: 0;
          min-width: 720px;
          font-size: 13px;
        }}
        th, td {{
          padding: 10px 11px;
          text-align: center;
          border-bottom: 1px solid #1e293b;
          border-right: 1px solid #1e293b;
          white-space: nowrap;
        }}
        th {{
          background: #1e293b;
          color: #facc15;
          font-weight: 800;
          position: sticky;
          top: 0;
          z-index: 3;
        }}
        .sticky-nome {{
          position: sticky;
          left: 0;
          z-index: 2;
          text-align: left;
          font-weight: 700;
          min-width: 150px;
          max-width: 150px;
          overflow: hidden;
          text-overflow: ellipsis;
        }}
        th.sticky-nome {{ z-index: 5; background: #1e293b; color: #facc15; }}
        .sticky-total {{
          position: sticky;
          right: 0;
          z-index: 2;
          font-weight: 900;
          color: #facc15 !important;
          background: #0f172a;
          min-width: 85px;
        }}
        th.sticky-total {{ z-index: 5; background: #1e293b; color: #facc15; }}
        .linha-impar td {{ background: #0f172a; color: #e2e8f0; }}
        .linha-par td {{ background: #162032; color: #e2e8f0; }}
        .linha-impar .sticky-nome {{ background: #0f172a; color: #ffffff; }}
        .linha-par .sticky-nome {{ background: #162032; color: #ffffff; }}
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
        <span class="badge">🛡️ Guerra: <b>+3 pts</b> / ataque</span>
        <span class="badge">⚔️ Liga: <b>+3 pts</b> / estrela</span>
        <span class="badge">📦 Doações: <b>+10 pts</b> (1º lugar)</span>
        <button class="btn-download-img" id="btn-download-detalhada" onclick="baixarDetalhadaHD()">
          📸 Baixar Tabela Completa (HD)
        </button>
      </div>
      <div class="table-container" id="card-tabela-detalhada">
        <table>
          <thead>
            <tr>
              {"".join([f'<th class="{"sticky-nome" if i==0 else "sticky-total" if i==len(cols_exibicao)-1 else ""}">{escape(str(c))}</th>' for i, c in enumerate(cols_exibicao)])}
            </tr>
          </thead>
          <tbody>{"".join(linhas)}</tbody>
        </table>
      </div>

      <script>
        function baixarDetalhadaHD() {{
          const element = document.getElementById('card-tabela-detalhada');
          const btn = document.getElementById('btn-download-detalhada');
          btn.innerText = "⏳ Gerando imagem...";
          btn.disabled = true;

          html2canvas(element, {{
            scale: 2.5,
            useCORS: true,
            backgroundColor: "#0f172a",
            logging: false
          }}).then(canvas => {{
            const link = document.createElement('a');
            link.download = 'tabela_completa_ranking.png';
            link.href = canvas.toDataURL('image/png', 1.0);
            link.click();
            btn.innerText = "📸 Baixar Tabela Completa (HD)";
            btn.disabled = false;
          }}).catch(err => {{
            console.error("Erro ao gerar imagem:", err);
            alert("Não foi possível gerar a imagem da tabela completa.");
            btn.innerText = "📸 Baixar Tabela Completa (HD)";
            btn.disabled = false;
          }});
        }}
      </script>
    </body>
    </html>
    """
    return html_tabela

  tab_res, tab_det = st.tabs(
      ["🏆 Visualização Bilhete Dourado", "📋 Tabela Detalhada Geral"]
  )

  with tab_res:
    html_resumido = gerar_tabela_bilhete_dourado(df_resumida)
    components.html(html_resumido, height=680, scrolling=True)

  with tab_det:
    html_detalhado = montar_tabela_detalhada_html(df_detalhada)
    components.html(html_detalhado, height=620, scrolling=False)

  # AUDITORIA E DESEMPATE
  if eh_admin:
    st.write("---")
    st.markdown("### 🎲 Ferramenta de Sorteio de Desempate (Admin)")
    contagem_pontos = df_sorted["Pontuação Total"].value_counts()
    pontos_empatados = contagem_pontos[contagem_pontos > 1].index.tolist()

    if pontos_empatados:
      opcoes_empate = {}
      for p in pontos_empatados:
        jogadores_emp = df_sorted[df_sorted["Pontuação Total"] == p][
            "Jogador"
        ].tolist()
        opcoes_empate[f"{p} Pontos ({', '.join(jogadores_emp)})"] = (
            p,
            jogadores_emp,
        )

      escolha = st.selectbox(
          "Selecione o grupo empatado:", list(opcoes_empate.keys())
      )

      if escolha:
        p_val, lista_empatados = opcoes_empate[escolha]
        qtd_vencedores = st.number_input(
            "Quantidade de Vencedores no Sorteio",
            min_value=1,
            max_value=len(lista_empatados),
            value=1,
        )

        if st.button("🎲 Realizar Sorteio Auditado"):
          vencedores = random.sample(lista_empatados, int(qtd_vencedores))
          data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
          semente = f"{data_hora}-{p_val}-{'-'.join(lista_empatados)}"
          hash_auditoria = hashlib.sha256(semente.encode()).hexdigest()[:12]

          st.balloons()
          st.success(
              f"🎉 **Vencedor(es) do Sorteio:** {', '.join(vencedores)}"
          )
          st.markdown(
              f"""
              <div style="background:#1e293b; padding:12px; border-radius:8px; border:1px solid #334155; margin-top:8px;">
                  <small style="color:#cbd5e1;"><b>Comprovante de Auditoria:</b><br>
                  <b>Data/Hora:</b> {data_hora}<br>
                  <b>Participantes:</b> {', '.join(lista_empatados)}<br>
                  <b>Código de Verificação:</b> {hash_auditoria.upper()}</small>
              </div>
              """,
              unsafe_allow_html=True,
          )
          registrar_log(
              st.session_state["admin_logado"],
              f"Realizou sorteio de desempate entre {lista_empatados}."
              f" Vencedor(es): {vencedores} (Hash: {hash_auditoria.upper()})",
          )
    else:
      st.info("Nenhum empate detectado no momento.")

# --- FEED DE NOVIDADES INTEGRADO LOGO ABAIXO DO RANKING ---
renderizar_feed_novidades()

# SEÇÃO EXPLICATIVA (RODAPÉ)
st.write("---")
st.markdown(
    "<h2 style='text-align: center;'>📜 Regulamento & Sistema de Premiação</h2>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align: center; color: #cbd5e1;'>A ideia é simples: valorizar quem joga bem, participa ativamente e ajuda o clã a crescer!</p><br>",
    unsafe_allow_html=True,
)

col_info1, col_info2, col_info3 = st.columns(3)

with col_info1:
  st.markdown(
      """
      <div class="info-card">
          <div class="info-card-header">⚔️ Como Pontuar?</div>
          <ul class="info-card-list">
              <li><b>Guerras Normais:</b> Ganhe <b>+3 pontos</b> por cada ataque realizado.</li>
              <li><b>Liga de Guerras (CWL):</b> Ganhe <b>+3 pontos</b> por cada estrela conquistada.</li>
              <li><b>Doações do Clã:</b> O maior doador do mês garante <b>+10 pontos</b> extras.</li>
          </ul>
      </div>
      """,
      unsafe_allow_html=True,
  )

with col_info2:
  st.markdown(
      """
      <div class="info-card">
          <div class="info-card-header">🎁 Qual é o Prêmio?</div>
          <ul class="info-card-list">
              <li><b>1º Lugar no Ranking:</b> Recebe o <b>Passe Dourado</b> do mês seguinte!</li>
              <li><b>Regra de Transparência:</b> O prêmio é entregue via doação oficial de gift card ou ativação na conta do jogador.</li>
          </ul>
      </div>
      """,
      unsafe_allow_html=True,
  )

with col_info3:
  st.markdown(
      """
      <div class="info-card">
          <div class="info-card-header">🤝 Empates & Regras</div>
          <ul class="info-card-list">
              <li>Em caso de empate na liderança, será feito um <b>sorteio ao vivo/auditado</b> via algoritmo público no app.</li>
              <li>Pontuações são atualizadas continuamente durante a temporada.</li>
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
    "<p style='text-align: center; color: #cbd5e1;'>Histórico dos grandes guerreiros do clã que conquistaram o Passe Dourado!</p><br>",
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

  st.dataframe(df_fama_exib, use_container_width=True, hide_index=True)
else:
  st.info(
      "A Galeria da Fama será inaugurada na finalização da primeira temporada!"
  )

# --- BOTÕES DE NAVEGAÇÃO E LINKS ÚTEIS NO FINAL DA PÁGINA ---
st.write("---")
f_col1, f_col2, f_col3 = st.columns(3)

with f_col1:
  if st.button(
      "📖 CLIQUE AQUI PARA VER AS REGRAS OFICIAIS COMPLETAS DO CLÃ",
      use_container_width=True,
  ):
    st.session_state["pagina_atual"] = "regras_cla"
    st.rerun()

with f_col2:
  st.markdown(
      '<a href="https://www.youtube.com/@winningwarscoc?sub_confirmation=1" target="_blank" class="btn-youtube-link">📺 Canal Oficial no YouTube ↗</a>',
      unsafe_allow_html=True,
  )

with f_col3:
  st.markdown(
      '<a href="https://link.clashofclans.com/?action=OpenSCID&p=25-1cb8481f-3a79-4681-90f9-8914acef2d63" target="_blank" class="btn-scid"><img src="https://i.ibb.co/fzPGy6fr/bg-hero-scid-landing-0.webp" height="20" style="border-radius: 4px; object-fit: cover;"> Add Godoy no Supercell ID ↗</a>',
      unsafe_allow_html=True,
  )
