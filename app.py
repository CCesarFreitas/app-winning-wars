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
    page_title="Winning Wars APP",
    page_icon="https://i.ibb.co/YFV3LGy5/winningwars-ico.png",
    layout="wide",
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
    sheet_estado.append_row([
        "mural_recado",
        "Bem-vindos ao aplicativo oficial do clã Winning Wars!",
    ])

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


# --- ESTILIZAÇÃO CSS CUSTOMIZADA COM ANIMAÇÃO, FONTES MAIORES E ÍCONE DO APP NA TELA INICIAL DO CELULAR ---
st.markdown(
    """
    <link rel="icon" type="image/png" href="https://i.ibb.co/YFV3LGy5/winningwars-ico.png">
    <link rel="apple-touch-icon" href="https://i.ibb.co/YFV3LGy5/winningwars-ico.png">
    <link rel="apple-touch-icon" sizes="180x180" href="https://i.ibb.co/YFV3LGy5/winningwars-ico.png">
    <link rel="shortcut icon" href="https://i.ibb.co/YFV3LGy5/winningwars-ico.png">
    <meta name="apple-mobile-web-app-title" content="Winning Wars">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">

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
