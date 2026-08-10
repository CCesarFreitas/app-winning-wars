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


# Obter senha inicial padrão via secrets
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


# --- CARREGAR DADOS COM CACHE DE DESEMPENHO ---
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


# --- FUNÇÃO PARA GERAR A TABELA COMPLETA EM HTML E DOWNLOAD EM HD ---
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
        font-size: 1rem;
        padding: 9px 18px;
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
        font-size: 1.1rem; 
        padding: 10px; 
        border-bottom: 2px solid #334155;
      }}

      .tabela-bilhete td {{
        border-bottom: 1px solid #334155; 
        padding: 10px 8px; 
        font-size: 1rem;
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
        padding-left: 12px !important;
      }}

      .tabela-pontos {{
        color: #38bdf8 !important;
        font-weight: 900;
      }}

      .emblema {{ 
        text-align: center; 
        margin-top: 16px; 
      }}

      .emblema img {{ 
        width: 85px; 
        filter: drop-shadow(0px 4px 8px rgba(0,0,0,0.5));
      }}

      @media (max-width: 768px) {{
        .bilhete-dourado-container {{ padding: 12px; }}
        .bilhete-dourado-title {{ font-size: 1.6rem !important; }}
        .tabela-bilhete th, .tabela-bilhete td {{ padding: 8px 6px; font-size: 0.95rem; }}
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
            <th style="width:55%; text-align: left; padding-left: 12px;">Membro</th>
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


# --- ESTILIZAÇÃO CSS CUSTOMIZADA MODERNA & RESPONSIVA MOBILE-FIRST ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Luckiest+Guy&family=Nunito:wght@600;700;800;900&display=swap');

    @keyframes fadeInPage {
        from { opacity: 0; transform: translateY(6px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .main .block-container {
        animation: fadeInPage 0.3s ease-in-out;
        padding-top: 1.2rem !important;
        padding-bottom: 2rem !important;
        max-width: 1200px;
    }

    .main { 
        background: radial-gradient(circle at top, #1e293b 0%, #0b0e14 100%); 
        font-size: 1rem;
        font-family: 'Nunito', sans-serif;
    }

    h1, h2, h3 { 
        font-family: 'Luckiest Guy', cursive !important; 
        color: #facc15 !important; 
        letter-spacing: 0.8px;
        text-shadow: 2px 2px 0px #000, -1px -1px 0px #000, 1px -1px 0px #000, -1px 1px 0px #000;
        word-break: break-word;
    }
    
    .main-title { 
        text-align: center; 
        margin-top: 4px; 
        margin-bottom: 4px; 
        font-size: 2.5rem !important; 
        line-height: 1.2;
    }

    .main-subtitle { 
        text-align: center; 
        color: #94a3b8; 
        font-family: 'Nunito', sans-serif; 
        font-weight: 700; 
        margin-bottom: 18px; 
        font-size: 1.05rem !important;
        padding: 0 8px;
    }
    
    /* BOTÕES GERAIS COM VISUAL GAMING MODERNO */
    div.stButton > button {
        background: linear-gradient(180deg, #22c55e 0%, #15803d 100%) !important;
        color: #ffffff !important;
        font-family: 'Luckiest Guy', cursive, sans-serif !important;
        font-size: 0.95rem !important;
        border: 1px solid #86efac !important;
        border-radius: 10px !important;
        box-shadow: 0px 3px 0px #14532d !important;
        transition: all 0.15s ease-in-out;
        text-shadow: 1px 1px 0px #000;
        white-space: nowrap !important;
        height: auto !important;
        padding: 8px 12px !important;
    }

    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0px 5px 0px #14532d !important;
        background: linear-gradient(180deg, #4ade80 0%, #16a34a 100%) !important;
    }

    div.stButton > button:active {
        transform: translateY(1px);
        box-shadow: 0px 1px 0px #14532d !important;
    }

    /* BOTÕES LINKS EXTERNOS REFINADOS */
    .btn-layout-copy {
        display: inline-block; width: 100%; max-width: 100%; text-align: center;
        background: linear-gradient(180deg, #3b82f6 0%, #1d4ed8 100%); color: white !important;
        padding: 10px 14px; border-radius: 10px; text-decoration: none; font-family: 'Luckiest Guy', cursive;
        border: 1px solid #93c5fd; box-shadow: 0px 3px 0px #1e3a8a; font-size: 1rem;
    }
    .btn-external-link, .btn-youtube-link, .btn-scid {
        display: flex; align-items: center; justify-content: center; gap: 6px;
        width: 100%; text-align: center;
        padding: 8px 10px; border-radius: 10px; text-decoration: none;
        font-family: 'Luckiest Guy', cursive; font-size: 0.9rem;
        transition: all 0.15s ease-in-out;
        box-shadow: 0px 3px 0px rgba(0,0,0,0.4);
        white-space: nowrap;
    }
    .btn-external-link {
        background: linear-gradient(180deg, #16a34a 0%, #15803d 100%); color: white !important;
        border: 1px solid #86efac;
    }
    .btn-youtube-link {
        background: linear-gradient(180deg, #dc2626 0%, #991b1b 100%); color: white !important;
        border: 1px solid #fca5a5;
    }
    .btn-scid {
        background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%); color: white !important;
        border: 1px solid #60a5fa;
    }
    .btn-external-link:hover, .btn-youtube-link:hover, .btn-scid:hover {
        transform: translateY(-2px);
        filter: brightness(1.1);
    }

    /* ABAS DE NAVEGAÇÃO */
    button[data-baseweb="tab"] {
        font-size: 1.05rem !important;
        font-weight: 800 !important;
        font-family: 'Nunito', sans-serif !important;
        padding: 10px 16px !important;
        background-color: #0f172a !important;
        border: 1px solid #334155 !important;
        border-radius: 10px 10px 0 0 !important;
        color: #94a3b8 !important;
        margin-right: 4px !important;
        transition: all 0.2s ease !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(180deg, #facc15 0%, #ca8a04 100%) !important;
        color: #000000 !important;
        border-color: #fef08a !important;
        box-shadow: 0px 4px 12px rgba(250, 204, 21, 0.25) !important;
    }

    /* CARDS E PODIUM */
    .podium-card { 
        padding: 16px; 
        border-radius: 14px; 
        text-align: center; 
        margin-bottom: 12px; 
        color: #ffffff; 
        box-shadow: 0 6px 20px rgba(0,0,0,0.5); 
        font-family: 'Nunito', sans-serif; 
    }
    .podium-title { font-family: 'Luckiest Guy', cursive; font-size: 1.25rem; margin-top: 4px; margin-bottom: 4px; }
    .podium-name { font-size: 1.15rem; font-weight: 800; word-break: break-word; }
    .podium-score { font-size: 1rem; margin-top: 2px; }
    .gold { background: linear-gradient(135deg, #f59e0b 0%, #78350f 100%); border: 2px solid #facc15; }
    .silver { background: linear-gradient(135deg, #64748b 0%, #1e293b 100%); border: 2px solid #cbd5e1; }
    .bronze { background: linear-gradient(135deg, #d97706 0%, #451a03 100%); border: 2px solid #f97316; }

    .mural-banner {
        background: #0f172a; border-radius: 12px; padding: 12px 16px; margin-bottom: 18px;
        border: 1px solid #334155; border-left: 5px solid #facc15;
        box-shadow: 0 4px 14px rgba(0,0,0,0.3); font-family: 'Nunito', sans-serif;
    }
    .mural-header { font-family: 'Luckiest Guy', cursive; color: #facc15; font-size: 1.1rem; margin-bottom: 4px; }

    .news-card {
        background: #0f172a; border: 1px solid #334155; border-top: 4px solid #38bdf8;
        border-radius: 12px; padding: 18px; margin-bottom: 16px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.4); font-family: 'Nunito', sans-serif;
    }
    .news-tag {
        display: inline-block; padding: 3px 8px; border-radius: 6px;
        font-weight: 800; font-size: 0.8rem; color: #fff; background: #2563eb; margin-bottom: 6px;
    }
    .news-title { font-family: 'Luckiest Guy', cursive; color: #facc15; font-size: 1.35rem; margin-bottom: 4px; }
    .news-meta { color: #94a3b8; font-size: 0.8rem; margin-bottom: 10px; }

    .info-card {
        background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 18px; margin-bottom: 12px;
        font-family: 'Nunito', sans-serif; color: #e2e8f0; box-shadow: 0 6px 18px rgba(0,0,0,0.4); height: 100%;
    }
    .info-card-header { font-family: 'Luckiest Guy', cursive; color: #facc15; font-size: 1.2rem; margin-bottom: 8px; }
    .info-card-list { padding-left: 16px; margin-bottom: 0px; }
    .info-card-list li { margin-bottom: 6px; line-height: 1.45; font-size: 0.98rem; }

    .rules-card {
        background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-top: 25px;
        font-family: 'Nunito', sans-serif; color: #e2e8f0; box-shadow: 0 6px 18px rgba(0,0,0,0.4);
    }
    .rules-title { font-family: 'Luckiest Guy', cursive; color: #facc15; font-size: 1.35rem; margin-bottom: 12px; }
    .rules-card ul { margin-bottom: 0px; padding-left: 18px; }
    .rules-card li { margin-bottom: 10px; line-height: 1.5; font-size: 0.98rem; }

    /* ROLAGEM HORIZONTAL SUAVE PARA SMARTPHONES (MOBILE) */
    @media (max-width: 768px) {
        .main-title { font-size: 1.8rem !important; }
        .main-subtitle { font-size: 0.88rem !important; margin-bottom: 12px; }

        div.stButton > button {
            font-size: 0.82rem !important;
            padding: 6px 8px !important;
            border-radius: 8px !important;
            box-shadow: 0px 2px 0px #14532d !important;
        }

        .btn-external-link, .btn-youtube-link, .btn-scid {
            font-size: 0.8rem !important;
            padding: 6px 6px !important;
            border-radius: 8px !important;
        }

        button[data-baseweb="tab"] {
            font-size: 0.88rem !important;
            padding: 8px 10px !important;
        }
        
        .main .block-container {
            padding-left: 0.6rem !important;
            padding-right: 0.6rem !important;
        }
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- TOPO DA PÁGINA: MENU DE NAVEGAÇÃO RESPONSIVO ---
with st.container():
  col_nav, col_admin_top = st.columns([8, 2])

  with col_nav:
    b1, b2, b3, b4, b5, b6, b7 = st.columns([1, 1, 1, 1, 1, 1, 1])
    with b1:
      if st.button("🛡️ Guerra", use_container_width=True):
        st.session_state["pagina_atual"] = "layouts_guerra"
        st.rerun()
    with b2:
      if st.button("🏆 Rankeada", use_container_width=True):
        st.session_state["pagina_atual"] = "layouts_rankeada"
        st.rerun()
    with b3:
      if st.button("📰 Novidades", use_container_width=True):
        st.session_state["pagina_atual"] = "novidades"
        st.rerun()
    with b4:
      if st.button("📜 Regras", use_container_width=True):
        st.session_state["pagina_atual"] = "regras_cla"
        st.rerun()
    with b5:
      st.markdown(
          '<a href="https://link.clashofclans.com/pt?action=OpenClanProfile&tag=2YPL9GU8Y"'
          ' target="_blank" class="btn-external-link">🏰 Clã ↗</a>',
          unsafe_allow_html=True,
      )
    with b6:
      st.markdown(
          '<a href="https://www.youtube.com/@winningwarscoc?sub_confirmation=1"'
          ' target="_blank" class="btn-youtube-link">📺 YouTube ↗</a>',
          unsafe_allow_html=True,
      )
    with b7:
      st.markdown(
          '<a href="https://link.clashofclans.com/?action=OpenSCID&p=25-1cb8481f-3a79-4681-90f9-8914acef2d63"'
          ' target="_blank" class="btn-scid">➕ Add ↗</a>',
          unsafe_allow_html=True,
      )

  with col_admin_top:
    if "admin_logado" in st.session_state:
      st.success(f"👤 {st.session_state['admin_logado']}")
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
                registrar_log(
                    u_top, "Logou pelo painel no canto superior direito"
                )
                st.success("Logado com sucesso!")
                st.rerun()
              else:
                st.error("Usuário ou senha inválidos.")

st.markdown("<hr style='margin: 10px 0; border-color: #334155;'>", unsafe_allow_html=True)


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
            <div style="display: flex; align-items: center; justify-content: center; gap: 12px; margin-top: 12px; margin-bottom: 18px;">
                <img src="{th_img_url}" width="75" style="filter: drop-shadow(0px 4px 8px rgba(0,0,0,0.5));">
                <h2 style="margin: 0; font-size: 1.8rem;">Bases de {tipo_layout} - {cv_nome}</h2>
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
                f"Publicou notícia '{noticia_titulo.strip()}' pela página Novidades",
            )
            st.cache_data.clear()
            st.success("✅ Notícia publicada com sucesso!")
            st.rerun()
          else:
            st.error("⚠️ Preencha o título e o conteúdo antes de publicar.")

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

      st.markdown(
          f"""
            <div class="news-card">
                <span class="news-tag">{escape(tag_nome)}</span>
                <div class="news-title">{escape(titulo)}</div>
                <div class="news-meta">🕒 Publicado em {escape(data_hora)} por <b>{escape(autor)}</b></div>
                <div style="color: #e2e8f0; font-size: 1.05rem; line-height: 1.6; white-space: pre-wrap;">{escape(conteudo)}</div>
            </div>
            """,
          unsafe_allow_html=True,
      )

      if img_url:
        st.markdown(
            f"""<div style="text-align:center; margin:8px 0 16px 0;">
                <img src="{escape(img_url, quote=True)}" alt="Imagem da novidade" style="max-width:100%; height:auto; border-radius:12px; border:2px solid #334155; box-shadow:0 6px 16px rgba(0,0,0,.45);" onerror="this.style.display='none';">
            </div>""",
            unsafe_allow_html=True,
        )

      if eh_admin:
        with st.expander(
            f"⚙️ [ADMIN] Gerenciar: {titulo or 'Sem título'}", expanded=False
        ):
          with st.form(f"form_editar_novidade_{item_idx}", clear_on_submit=False):
            edit_titulo = st.text_input(
                "Título", value=titulo, key=f"edit_titulo_{item_idx}"
            )
            tags_disponiveis = [
                "🎉 Evento",
                "⚔️ Torneio",
                "🚀 Atualização Game",
                "📢 Aviso Clã",
                "🏆 Premiação Extra",
            ]
            tag_index = (
                tags_disponiveis.index(tag_nome)
                if tag_nome in tags_disponiveis
                else 0
            )
            edit_tag = st.selectbox(
                "Categoria / Tag",
                tags_disponiveis,
                index=tag_index,
                key=f"edit_tag_{item_idx}",
            )
            edit_conteudo = st.text_area(
                "Conteúdo", value=conteudo, height=120, key=f"edit_conteudo_{item_idx}"
            )
            edit_img = st.text_input(
                "Link da Imagem", value=img_url, key=f"edit_img_{item_idx}"
            )

            col_salvar, col_excluir = st.columns([1, 1])
            with col_salvar:
              btn_salvar_edit = st.form_submit_button(
                  "💾 Salvar Alterações", use_container_width=True
              )
            with col_excluir:
              btn_excluir_edit = st.form_submit_button(
                  "❌ Excluir Publicação", use_container_width=True
              )

            if btn_salvar_edit:
              try:
                cell = sheet_novidades.find(titulo)
                if cell:
                  linha_planilha = cell.row
                  sheet_novidades.update_cell(linha_planilha, 2, edit_titulo)
                  sheet_novidades.update_cell(linha_planilha, 3, edit_conteudo)
                  sheet_novidades.update_cell(linha_planilha, 4, edit_img)
                  sheet_novidades.update_cell(linha_planilha, 5, edit_tag)
                  registrar_log(
                      st.session_state["admin_logado"],
                      f"Editou notícia '{edit_titulo}'",
                  )
                  st.cache_data.clear()
                  st.success("✅ Notícia atualizada!")
                  st.rerun()
              except Exception as e:
                st.error(f"Erro ao salvar edição: {e}")

            if btn_excluir_edit:
              try:
                cell = sheet_novidades.find(titulo)
                if cell:
                  sheet_novidades.delete_rows(cell.row)
                  registrar_log(
                      st.session_state["admin_logado"],
                      f"Excluiu notícia '{titulo}'",
                  )
                  st.cache_data.clear()
                  st.success("🗑️ Notícia excluída!")
                  st.rerun()
              except Exception as e:
                st.error(f"Erro ao excluir notícia: {e}")
  else:
    st.info("Nenhuma novidade publicada até o momento.")


# ==============================================================================
# PÁGINA EXCLUSIVA: REGRAS OFICIAIS DO CLÃ
# ==============================================================================
def renderizar_pagina_regras():
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
        <div class="rules-title">📌 Diretrizes Gerais do Clã</div>
        <ul>
            <li><b>Ataques na Guerra:</b> É obrigatório realizar ambos os ataques na guerra do clã respeitando o plano traçado pela liderança.</li>
            <li><b>Jogos do Clã:</b> A meta individual mínima é de 2.000 pontos para garantir a premiação máxima da equipe.</li>
            <li><b>Doações:</b> Mantenha a proporção de doações equilibrada e doe apenas o que for solicitado no pedido.</li>
            <li><b>Respeito e Convivência:</b> Promova um ambiente amigável e construtivo no chat do jogo e no grupo oficial.</li>
            <li><b>Inatividade:</b> Caso vá se ausentar, avise a liderança com antecedência para não ser removido por inatividade.</li>
        </ul>
    </div>
    """,
      unsafe_allow_html=True,
  )


# ROTEAMENTO DE PÁGINAS
if st.session_state["pagina_atual"] == "layouts_guerra":
  renderizar_pagina_layouts("Guerra", "🛡️ Layouts para Guerra de Clãs")
elif st.session_state["pagina_atual"] == "layouts_rankeada":
  renderizar_pagina_layouts("Rankeada", "🏆 Layouts para Vila Rankeada / CWL")
elif st.session_state["pagina_atual"] == "novidades":
  renderizar_pagina_novidades()
elif st.session_state["pagina_atual"] == "regras_cla":
  renderizar_pagina_regras()
else:
  # ==============================================================================
  # PÁGINA PRINCIPAL
  # ==============================================================================
  st.markdown(
      "<h1 class='main-title'>⚔️ WINNING WARS APP ⚔️</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<div class='main-subtitle'>Painel Oficial do Clã Vastaya / Winning"
      " Wars</div>",
      unsafe_allow_html=True,
  )

  if mural_recado:
    st.markdown(
        f"""
        <div class="mural-banner">
            <div class="mural-header">📢 COMUNICADO DA LIDERANÇA</div>
            <div style="color: #e2e8f0; font-size: 1.05rem;">{mural_recado}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

  # SEÇÃO DO RANKING BILHETE DOURADO
  if not df.empty:
    st.markdown(
        "<h2 style='text-align: center;'>🏆 Ranking do Bilhete Dourado</h2>",
        unsafe_allow_html=True,
    )

    df_rank = df.copy()
    if "Pontuação Total" in df_rank.columns:
      df_rank["Pontuação Total"] = pd.to_numeric(
          df_rank["Pontuação Total"], errors="coerce"
      ).fillna(0)
      df_rank = df_rank.sort_values(
          by="Pontuação Total", ascending=False
      ).reset_index(drop=True)
      df_rank.index = df_rank.index + 1
      df_rank["Posição"] = df_rank.index

      html_tabela = gerar_tabela_bilhete_dourado(df_rank)
      components.html(html_tabela, height=600, scrolling=True)

  # BOTÃO DE VER REGRAS COMPLETAS
  st.write("")
  c_btn_regras = st.columns([1, 2, 1])
  with c_btn_regras[1]:
    if st.button(
        "📖 CLIQUE AQUI PARA VER AS REGRAS OFICIAIS COMPLETAS DO CLÃ",
        use_container_width=True,
    ):
      st.session_state["pagina_atual"] = "regras_cla"
      st.rerun()

  # GALERIA DA FAMA
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

    st.dataframe(
        df_fama_exib,
        use_container_width=True,
        hide_index=True,
    )
  else:
    st.info("Nenhum histórico registrado na Galeria da Fama ainda.")
