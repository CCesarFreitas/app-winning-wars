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
        display: flex; align-items: center; justify-content: center; gap: 8px; width: 100%; text-align: center;
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
  b1, b2, b3 = st.columns(3)
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
        '<a'
        ' href="https://link.clashofclans.com/pt?action=OpenClanProfile&tag=2YPL9GU8Y"'
        ' target="_blank" class="btn-external-link">🏰 Clã Vastaya ↗</a>',
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

        if not layouts_filtrados.empty:
          for item_idx, row in layouts_filtrados.iterrows():
            if str(row["ImagemUrl"]).strip():
              st.image(str(row["ImagemUrl"]).strip(), use_container_width=True)

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
# COMPONENTE REUTILIZÁVEL: FEED DE NOVIDADES
# ==============================================================================
def renderizar_feed_novidades(limite=None, titulo="📰 Últimas Novidades"):
  """Renderiza o feed de notícias com opção de postar, editar e excluir para Admins diretamente no feed."""
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

  eh_admin = "admin_logado" in st.session_state

  # RECURSO ADMIN: CRIAR POST DIRETO NO FEED
  if eh_admin:
    with st.expander("➕ [ADMIN] Postar Novidade no Feed", expanded=False):
      with st.form("form_nova_noticia_feed", clear_on_submit=True):
        f_titulo = st.text_input("Título da Notícia")
        f_tag = st.selectbox(
            "Categoria / Tag",
            [
                "🎉 Evento",
                "⚔️ Torneio",
                "🚀 Atualização Game",
                "📢 Aviso Clã",
                "🏆 Premiação Extra",
            ],
            key="feed_tag_select",
        )
        f_conteudo = st.text_area("Conteúdo do Comunicado", height=120)
        f_img = st.text_input("Link Direto da Imagem / Banner (Opcional)")
        btn_feed_pub = st.form_submit_button(
            "📢 Publicar no Feed", use_container_width=True
        )

        if btn_feed_pub:
          if f_titulo.strip() and f_conteudo.strip():
            d_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
            sheet_novidades.append_row([
                d_hora,
                f_titulo.strip(),
                f_conteudo.strip(),
                f_img.strip(),
                f_tag,
                st.session_state["admin_logado"],
            ])
            registrar_log(
                st.session_state["admin_logado"],
                f"Publicou notícia '{f_titulo.strip()}' direto pelo Feed",
            )
            st.cache_data.clear()
            st.success("✅ Novidade publicada no feed!")
            st.rerun()
          else:
            st.error("⚠️ Preencha o título e o conteúdo antes de publicar.")

  if df_novidades.empty:
    st.info("Nenhuma novidade ou notícia publicada no momento.")
    return

  novidades_feed = df_novidades.iloc[::-1]
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
    conteudo_safe = escape(conteudo).replace("\n", "<br>")
    meta_safe = escape(
        f"Publicado em {data_hora} por {autor}"
        if data_hora
        else f"Por {autor}"
    )

    imagem_html = ""
    if img_url:
      imagem_html = f"""
      <div class="news-image-wrap">
          <img src="{escape(img_url, quote=True)}" alt="Imagem da novidade" class="news-image" loading="lazy" onerror="this.style.display='none'; this.parentElement.classList.add('news-image-error');">
          <div class="news-image-fallback">🖼️ Não foi possível carregar a imagem.</div>
      </div>
      """

    st.markdown(
        f"""
        <div class="news-card">
            <div class="news-card-top">
                <span class="news-tag">{tag_safe}</span>
                <span class="news-meta">{meta_safe}</span>
            </div>
            <div class="news-title">{titulo_safe}</div>
            {imagem_html}
            <div class="news-content">{conteudo_safe}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # RECURSO ADMIN: EDITAR E EXCLUIR POSTS DIRETO NO FEED
    if eh_admin:
      col_edit, col_del = st.columns([1, 1])

      with col_edit:
        with st.popover("✏️ Editar Post", use_container_width=True):
          st.markdown(f"#### ✏️ Editar: {titulo_item}")
          with st.form(f"form_edit_feed_{item_idx}"):
            e_titulo = st.text_input("Título", value=titulo_item)
            tags_opcoes = [
                "🎉 Evento",
                "⚔️ Torneio",
                "🚀 Atualização Game",
                "📢 Aviso Clã",
                "🏆 Premiação Extra",
            ]
            idx_tag = (
                tags_opcoes.index(tag_nome) if tag_nome in tags_opcoes else 0
            )
            e_tag = st.selectbox(
                "Tag", tags_opcoes, index=idx_tag, key=f"edit_tag_{item_idx}"
            )
            e_conteudo = st.text_area("Conteúdo", value=conteudo, height=120)
            e_img = st.text_input("Link da Imagem", value=img_url)
            btn_salvar_edit = st.form_submit_button(
                "💾 Salvar Alterações", use_container_width=True
            )

            if btn_salvar_edit:
              if e_titulo.strip() and e_conteudo.strip():
                # Encontrar e atualizar a linha na planilha (item_idx + 2 pois a linha 1 é o cabeçalho)
                row_num = item_idx + 2
                sheet_novidades.update(
                    f"A{row_num}:F{row_num}",
                    [[
                        data_hora,
                        e_titulo.strip(),
                        e_conteudo.strip(),
                        e_img.strip(),
                        e_tag,
                        autor,
                    ]],
                )
                registrar_log(
                    st.session_state["admin_logado"],
                    f"Editou notícia '{e_titulo.strip()}' via Feed",
                )
                st.cache_data.clear()
                st.success("✅ Publicação atualizada!")
                st.rerun()
              else:
                st.error("⚠️ Título e conteúdo não podem ser vazios.")

      with col_del:
        if st.button(
            "❌ Excluir Post",
            key=f"btn_del_feed_{item_idx}",
            use_container_width=True,
        ):
          row_num = item_idx + 2
          sheet_novidades.delete_rows(row_num)
          registrar_log(
              st.session_state["admin_logado"],
              f"Excluiu notícia '{titulo_item}' via Feed",
          )
          st.cache_data.clear()
          st.success("🗑️ Publicação excluída!")
          st.rerun()

    st.write("")


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
# SELEÇÃO DE PÁGINAS
# ==============================================================================
if st.session_state["pagina_atual"] == "layouts_guerra":
  renderizar_pagina_layouts("Guerra", "🛡️ Layouts Oficiais de Guerra")
elif st.session_state["pagina_atual"] == "layouts_rankeada":
  renderizar_pagina_layouts("Rankeada", "🏆 Layouts Oficiais para Rankeada")
elif st.session_state["pagina_atual"] == "regras_cla":
  renderizar_regras_cla()
else:
  # PÁGINA PRINCIPAL
  st.markdown(
      '<h1 class="main-title">⚔️ WINNING WARS ⚔️</h1>', unsafe_allow_html=True
  )
  st.markdown(
      '<div class="main-subtitle">ACOMPANHAMENTO DE PONTUAÇÃO E DESEMPENHO DO'
      " CLÃ</div>",
      unsafe_allow_html=True,
  )

  # BANNER DE RECADO / AVISO DO MURAL
  if mural_recado.strip():
    st.markdown(
        f"""
        <div class="mural-banner">
            <div class="mural-header">📌 COMUNICADO DA LIDERANÇA</div>
            <div>{mural_recado}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

  # PROCESSAR DADOS
  if not df.empty and "Jogador" in df.columns:
    df = df[df["Jogador"].astype(str).str.strip() != ""].copy()

    colunas_raides = [c for c in df.columns if c.startswith("Raides_")]
    colunas_guerras = [c for c in df.columns if c.startswith("Guerra_")]
    colunas_liga = [c for c in df.columns if c.startswith("Liga_")]

    cols_somar = [c for c in colunas_raides + colunas_guerras + colunas_liga if c in df.columns]

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
  tab_ranking, tab_tabela, tab_admin = st.tabs(
      ["🏆 Ranking ao Vivo", "📋 Tabela Detalhada", "🔐 Painel Admin"]
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
              '<div class="podium-card gold"><img'
              ' src="https://i.ibb.co/mkC43vT/goldenpass.png" width="55"><div'
              ' class="podium-title">🥇 1º LUGAR</div><div'
              f' class="podium-name">{df_rank.iloc[0]["Jogador"]}</div><div'
              ' class="podium-score">'
              f'{int(df_rank.iloc[0]["Total"])} Pontos</div></div>',
              unsafe_allow_html=True,
          )

      if len(df_rank) >= 2:
        with col2:
          st.markdown(
              '<div class="podium-card silver"><img'
              ' src="https://i.ibb.co/L5X4134/silverpass.png" width="55"><div'
              ' class="podium-title">🥈 2º LUGAR</div><div'
              f' class="podium-name">{df_rank.iloc[1]["Jogador"]}</div><div'
              ' class="podium-score">'
              f'{int(df_rank.iloc[1]["Total"])} Pontos</div></div>',
              unsafe_allow_html=True,
          )

      if len(df_rank) >= 3:
        with col3:
          st.markdown(
              '<div class="podium-card bronze"><img'
              ' src="https://i.ibb.co/L5X4134/silverpass.png" width="55"><div'
              ' class="podium-title">🥉 3º LUGAR</div><div'
              f' class="podium-name">{df_rank.iloc[2]["Jogador"]}</div><div'
              ' class="podium-score">'
              f'{int(df_rank.iloc[2]["Total"])} Pontos</div></div>',
              unsafe_allow_html=True,
          )

      st.markdown(
          "<h3 style='text-align: center; margin-top: 20px; margin-bottom:"
          " 15px;'>🏆 Ranking Geral</h3>",
          unsafe_allow_html=True,
      )

      df_exib = df_rank[["Posição", "Jogador", "Total"]].rename(
          columns={"Jogador": "Jogador", "Total": "Pontuação Total"}
      )

      html_tabela_hd = gerar_tabela_bilhete_dourado(df_exib)
      components.html(html_tabela_hd, height=750, scrolling=True)

    else:
      st.info("Nenhum dado cadastrado ainda na planilha.")

    st.markdown("---")

    # CARTÕES DE INFORMAÇÕES E REGRAS
    info_col1, info_col2, info_col3 = st.columns(3)

    with info_col1:
      st.markdown(
          """
            <div class="info-card">
                <img src="https://i.ibb.co/mkC43vT/goldenpass.png" width="60" style="margin-bottom: 8px;">
                <div class="info-card-header">🎁 Premiação Mensal</div>
                <ul class="info-card-list" style="text-align: left;">
                    <li><b>🥇 1º Lugar:</b> Bilhete Dourado (Pass) + Vaga na Liga Principal.</li>
                    <li><b>🥈 2º Lugar:</b> Destaque no Clã + Vaga na Liga Principal.</li>
                    <li><b>🥉 3º Lugar:</b> Destaque no Clã + Vaga na Liga Principal.</li>
                </ul>
            </div>
            """,
          unsafe_allow_html=True,
      )

    with info_col2:
      st.markdown(
          """
            <div class="info-card">
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
            <div class="info-card">
                <img src="https://i.ibb.co/YFbsJ97x/Clash-of-Clans-emblem.png" width="60" style="margin-bottom: 8px;">
                <div class="info-card-header">🛡️ Requisitos & Regras</div>
                <ul class="info-card-list" style="text-align: left;">
                    <li>Atacar na Guerra é <b>Obrigatório</b> se verde.</li>
                    <li>Respeitar as ordens no Chat / WhatsApp.</li>
                    <li>Manter doação ativa de tropas para a vila.</li>
                </ul>
            </div>
            """,
          unsafe_allow_html=True,
      )

    st.write("")

    # FEED DE NOVIDADES RENDERIZADO NO FINAL DO RANKING
    renderizar_feed_novidades(
        limite=3, titulo="📰 Novidades e Comunicados do Clã"
    )

  # ABA 2: TABELA DETALHADA
  with tab_tabela:
    if not df.empty:
      st.markdown(
          "<h3 style='text-align: center; margin-bottom: 15px;'>📋 Tabela"
          " Detalhada de Pontuações</h3>",
          unsafe_allow_html=True,
      )

      colunas_exibir = ["Jogador", "Total"] + [
          c
          for c in df.columns
          if c not in ["Jogador", "Total", "Posição", "Acoes"]
      ]

      df_tabela_mobile = df[colunas_exibir].sort_values(
          by="Total", ascending=False
      )

      # GERAR TABELA HTML ESTILIZADA PARA TABELA DETALHADA
      headers_html = "".join(
          [f"<th>{col}</th>" for col in df_tabela_mobile.columns]
      )
      rows_html = ""
      for idx_m, row_m in df_tabela_mobile.iterrows():
        cells_html = "".join([f"<td>{val}</td>" for val in row_m.values])
        rows_html += f"<tr>{cells_html}</tr>"

      html_tabela = f"""
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Luckiest+Guy&family=Nunito:wght@600;800;900&display=swap');
          body {{ margin: 0; background-color: transparent; font-family: 'Nunito', sans-serif; color: #e2e8f0; }}
          .table-container {{ overflow-x: auto; max-width: 100%; border-radius: 12px; border: 2px solid #334155; background: #0f172a; padding: 10px; }}
          table {{ width: 100%; border-collapse: collapse; min-width: 600px; }}
          th {{ background-color: #1e293b; color: #facc15; font-family: 'Luckiest Guy', cursive; font-size: 1.1rem; padding: 12px 10px; border: 1px solid #334155; text-align: center; }}
          td {{ padding: 10px; border: 1px solid #334155; text-align: center; font-weight: 700; font-size: 0.95rem; }}
          tr:nth-child(even) {{ background-color: #111827; }}
          tr:hover {{ background-color: #1e293b; }}
          .btn-download-tb {{ background: linear-gradient(180deg, #3b82f6 0%, #1d4ed8 100%); color: white; font-family: 'Luckiest Guy', cursive; border: 2px solid #93c5fd; padding: 8px 16px; border-radius: 8px; cursor: pointer; margin-bottom: 12px; }}
        </style>
      </head>
      <body>
        <div style="text-align: right;">
          <button class="btn-download-tb" id="btn-tb-dl" onclick="baixarTabelaHD()">🖼️ Baixar Tabela em HD</button>
        </div>
        <div class="table-container" id="tabela-completa-container">
          <table>
            <thead><tr>{headers_html}</tr></thead>
            <tbody>{rows_html}</tbody>
          </table>
        </div>
        <script>
          function baixarTabelaHD() {{
            const el = document.getElementById('tabela-completa-container');
            const btn = document.getElementById('btn-tb-dl');
            btn.innerText = "⏳ Gerando imagem...";
            btn.disabled = true;

            html2canvas(el, {{ scale: 2.5, useCORS: true, backgroundColor: '#0f172a' }}).then(canvas => {{
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

  # ABA 3: ÁREA ADMIN
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

      (
          sub_tab1,
          sub_tab2,
          sub_tab_pass,
          sub_tab3,
          sub_tab4,
          sub_tab_news,
          sub_tab5,
          sub_tab6,
          sub_tab7,
      ) = st.tabs([
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

      with sub_tab1:
        c1, c2 = st.columns(2)
        with c1:
          novo_nome = st.text_input("Nome do Player")
          if st.button("Cadastrar Player"):
            if novo_nome.strip():
              if not df.empty and novo_nome.strip() in df["Jogador"].values:
                st.error("⚠️ Este player já está cadastrado.")
              else:
                nova_linha = {"Jogador": novo_nome.strip()}
                sheet_dados.append_row([novo_nome.strip()])
                registrar_log(
                    st.session_state["admin_logado"],
                    f"Cadastrou player '{novo_nome.strip()}'",
                )
                st.cache_data.clear()
                st.success(f"Player **{novo_nome.strip()}** cadastrado!")
                st.rerun()

        with c2:
          if not df.empty and "Jogador" in df.columns:
            p_remover = st.selectbox(
                "Selecione o Player para Remover", df["Jogador"].values
            )
            if st.button("🗑️ Remover Player"):
              cell = sheet_dados.find(p_remover)
              if cell:
                sheet_dados.delete_rows(cell.row)
                registrar_log(
                    st.session_state["admin_logado"],
                    f"Removeu player '{p_remover}'",
                )
                st.cache_data.clear()
                st.success(f"Player **{p_remover}** removido!")
                st.rerun()

      with sub_tab2:
        st.markdown("#### 👤 Cadastrar Novo Administrador")
        with st.form("form_novo_admin_aba", clear_on_submit=True):
          novo_usr = st.text_input("Nome de Usuário")
          nova_pwd = st.text_input("Senha de Acesso", type="password")
          btn_cad_admin = st.form_submit_button("Criar Administrador")

          if btn_cad_admin:
            usr_limpo = novo_usr.strip()
            pwd_limpo = nova_pwd.strip()
            if usr_limpo and pwd_limpo:
              if not df_admins.empty and usr_limpo in df_admins["Usuario"].values:
                st.error("⚠️ Este usuário administrador já existe.")
              else:
                hash_senha = gerar_hash(pwd_limpo)
                sheet_admins.append_row([usr_limpo, hash_senha])
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
        st.markdown(
            f"#### 🔑 Alterar Senha de Admin (`{st.session_state['admin_logado']}`)"
        )
        with st.form("form_mudar_senha", clear_on_submit=True):
          senha_atual = st.text_input("Senha Atual", type="password")
          nova_senha = st.text_input("Nova Senha", type="password")
          conf_nova_senha = st.text_input("Confirmar Nova Senha", type="password")
          btn_trocar_senha = st.form_submit_button("Atualizar Senha")

          if btn_trocar_senha:
            if not senha_atual or not nova_senha:
              st.error("⚠️ Preencha todos os campos de senha.")
            elif nova_senha != conf_nova_senha:
              st.error("⚠️ A nova senha e a confirmação não coincidem.")
            else:
              cell_usr = sheet_admins.find(st.session_state["admin_logado"])
              if cell_usr:
                val_senha = sheet_admins.cell(cell_usr.row, 2).value
                if val_senha == gerar_hash(senha_atual):
                  sheet_admins.update_cell(
                      cell_usr.row, 2, gerar_hash(nova_senha)
                  )
                  registrar_log(
                      st.session_state["admin_logado"],
                      "Alterou a própria senha de administrador",
                  )
                  st.success("✅ Senha alterada com sucesso!")
                else:
                  st.error("⚠️ Senha atual incorreta.")

      with sub_tab3:
        st.markdown("#### ⚡ Adicionar Coluna Sequencial de Evento")
        ca1, ca2 = st.columns(2)
        with ca1:
          if st.button("⚔️ Criar Próxima Guerra"):
            nova_col = obter_proxima_coluna_sequencial("Guerra", df.columns)
            sheet_dados.update_cell(1, len(df.columns) + 1, nova_col)
            registrar_log(
                st.session_state["admin_logado"], f"Criou coluna {nova_col}"
            )
            st.cache_data.clear()
            st.success(f"Coluna **{nova_col}** criada!")
            st.rerun()

          if st.button("🛡️ Criar Próxima Raide"):
            nova_col = obter_proxima_coluna_sequencial("Raides", df.columns)
            sheet_dados.update_cell(1, len(df.columns) + 1, nova_col)
            registrar_log(
                st.session_state["admin_logado"], f"Criou coluna {nova_col}"
            )
            st.cache_data.clear()
            st.success(f"Coluna **{nova_col}** criada!")
            st.rerun()

        with ca2:
          if st.button("🏆 Criar Próxima Liga"):
            nova_col = obter_proxima_coluna_sequencial("Liga", df.columns)
            sheet_dados.update_cell(1, len(df.columns) + 1, nova_col)
            registrar_log(
                st.session_state["admin_logado"], f"Criou coluna {nova_col}"
            )
            st.cache_data.clear()
            st.success(f"Coluna **{nova_col}** criada!")
            st.rerun()

        st.divider()
        st.markdown("#### ✏️ Edição Direta de Pontuações")
        if not df.empty:
          df_editado = st.data_editor(
              df, num_rows="dynamic", use_container_width=True
          )
          if st.button("💾 Salvar Alterações na Planilha"):
            sheet_dados.clear()
            sheet_dados.update(
                [df_editado.columns.values.tolist()]
                + df_editado.values.tolist()
            )
            registrar_log(
                st.session_state["admin_logado"],
                "Salvou alterações de pontos diretamente na tabela",
            )
            st.cache_data.clear()
            st.success("Tabela atualizada com sucesso!")
            st.rerun()

      with sub_tab4:
        st.markdown("#### 📌 Mural de Recados")
        novo_recado_txt = st.text_area("Recado em Destaque", value=mural_recado)
        if st.button("Atualizar Recado do Mural"):
          cell_recado = sheet_estado.find("mural_recado")
          if cell_recado:
            sheet_estado.update_cell(cell_recado.row, 2, novo_recado_txt)
          else:
            sheet_estado.append_row(["mural_recado", novo_recado_txt])
          registrar_log(
              st.session_state["admin_logado"], "Atualizou recado do mural"
          )
          st.success("Mural atualizado!")
          st.rerun()

        st.divider()
        st.markdown("#### 🏆 Galeria da Fama (Lançamento Manual)")
        with st.form("form_galeria_fama_manual"):
          fama_titulo = st.text_input("Mês / Edição (Ex: Janeiro / 2026)")
          fama_1 = st.text_input("🥇 1º Lugar (Campeão)")
          fama_2 = st.text_input("🥈 2º Lugar")
          fama_3 = st.text_input("🥉 3º Lugar")
          btn_add_fama = st.form_submit_button("Adicionar à Galeria da Fama")

          if btn_add_fama:
            if fama_titulo.strip() and fama_1.strip():
              sheet_fama.append_row([
                  fama_titulo.strip(),
                  fama_1.strip(),
                  fama_2.strip(),
                  fama_3.strip(),
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

      # ABA DE GERENCIAMENTO DE NOTÍCIAS / NOVIDADES NO PAINEL ADMIN
      with sub_tab_news:
        st.markdown("#### 📰 Publicar Nova Notícia ou Evento")
        with st.form("form_nova_noticia", clear_on_submit=True):
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
            col_n1, col_n2 = st.columns([4, 1])
            with col_n1:
              st.write(
                  f"**{row_n.get('Titulo', '')}** ({row_n.get('Tag', '')}) -"
                  f" {row_n.get('DataHora', '')}"
              )
            with col_n2:
              if st.button("🗑️ Excluir", key=f"del_news_panel_{idx_n}"):
                row_num = idx_n + 2
                sheet_novidades.delete_rows(row_num)
                registrar_log(
                    st.session_state["admin_logado"],
                    f"Excluiu notícia '{row_n.get('Titulo', '')}'",
                )
                st.cache_data.clear()
                st.success("🗑️ Publicação excluída!")
                st.rerun()
        else:
          st.info("Nenhuma novidade ou notícia publicada no momento.")

      with sub_tab5:
        st.markdown("#### 📜 Histórico de Ações dos Administradores")
        try:
          logs_dados = sheet_logs.get_all_records()
          df_logs = pd.DataFrame(logs_dados)
          if not df_logs.empty:
            st.dataframe(
                df_logs.iloc[::-1], use_container_width=True, hide_index=True
            )
          else:
            st.info("Nenhum log registrado.")
        except Exception:
          st.info("Sem logs registrados ainda.")

      with sub_tab6:
        st.markdown("#### 💾 Backup dos Dados Atual")
        if not df.empty:
          csv = df.to_csv(index=False).encode("utf-8")
          st.download_button(
              label="📥 Baixar Backup em CSV",
              data=csv,
              file_name="winningwars_backup.csv",
              mime="text/csv",
          )

      with sub_tab7:
        st.markdown("#### 🎲 Sorteio de Desempate (Ao Vivo)")
        if not df.empty and "Total" in df.columns:
          maior_pontuacao = df_rank["Total"].max()
          empatados = df_rank[df_rank["Total"] == maior_pontuacao]
          lista_empatados = empatados["Jogador"].tolist()
          qtd_empatados = len(lista_empatados)

          if qtd_empatados > 1:
            st.warning(
                f"⚠️ Detectado um empate entre **{qtd_empatados} guerreiros** com"
                f" **{int(maior_pontuacao)} pontos**!"
            )
            cols_participantes = st.columns(min(4, qtd_empatados))
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

              data_hora_sorteio = datetime.now().strftime("%d/%m/%Y às %H:%M")
              vencedores_str = ", ".join(vencedores)

              st.success(
                  f"🎉 **SORTEIO CONCLUÍDO COM SUCESSO EM {data_hora_sorteio}!**"
              )
              st.markdown(
                  f"""
                <div style="background: linear-gradient(135deg, #15803d 0%, #166534 100%); border: 3px solid #86efac; border-radius: 14px; padding: 20px; text-align: center; margin-top: 15px;">
                    <h2 style="color: #ffffff !important; margin: 0 0 10px 0;">🏆 VENCEDOR(ES) DO SORTEIO 🏆</h2>
                    <h1 style="color: #facc15 !important; font-size: 2.5rem; margin: 0;">{vencedores_str}</h1>
                </div>
                """,
                  unsafe_allow_html=True,
              )
              registrar_log(
                  st.session_state["admin_logado"],
                  f"Realizou sorteio de desempate. Vencedor(es): {vencedores_str}",
              )
          else:
            st.info(
                "Não há empates na liderança no momento. O líder isolado é"
                f" **{df_rank.iloc[0]['Jogador']}** com"
                f" **{int(df_rank.iloc[0]['Total'])} pontos**."
            )

  # GALERIA DA FAMA NO FINAL DA PÁGINA
  st.write("---")
  st.markdown(
      "<h2 style='text-align: center;'>🏆 Galeria da Fama — Campeões"
      " Anteriores</h2>",
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

  # LINKS EXTERNOS / ATALHOS NO FINAL DA PÁGINA
  st.write("---")
  st.markdown(
      "<h3 style='text-align: center;'>🔗 Links Rápidos</h3>",
      unsafe_allow_html=True,
  )
  c_link1, c_link2, c_link3 = st.columns(3)

  with c_link1:
    st.markdown(
        '<a href="https://www.youtube.com/@winningwarscoc?sub_confirmation=1"'
        ' target="_blank" class="btn-youtube-link"><img'
        ' src="https://em-content.zobj.net/content/2020/04/05/yt.png"'
        ' width="22" height="22" style="vertical-align: middle;"> Canal Winning'
        ' Wars YT ↗</a>',
        unsafe_allow_html=True,
    )

  with c_link2:
    if st.button(
        "📜 Regras do Clã", use_container_width=True, key="bottom_regras_cla"
    ):
      st.session_state["pagina_atual"] = "regras_cla"
      st.rerun()

  with c_link3:
    st.markdown(
        '<a href="https://supercell.com/en/" target="_blank"'
        ' class="btn-scid">🌐 Supercell ID ↗</a>',
        unsafe_allow_html=True,
    )
