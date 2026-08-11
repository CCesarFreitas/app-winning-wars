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
      " 'WinningWars_DB'. Verifique suas permissões no Google Sheets."
  )
  st.stop()


def registrar_log(admin: str, acao: str):
  try:
    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet_logs.append_row([data_hora, admin, acao])
  except Exception:
    pass


# --- CARREGAR DADOS COM CACHE ---
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
  dados_estado = dict(sheet_estado.get_all_values())
  mes_finalizado = dados_estado.get("mes_finalizado", "FALSE") == "TRUE"
  mural_recado = dados_estado.get("mural_recado", "")
except Exception:
  mes_finalizado = False
  mural_recado = ""

if "pagina_atual" not in st.session_state:
  st.session_state["pagina_atual"] = "principal"

df_layouts = pd.DataFrame(obter_layouts_cached())
df_fama = pd.DataFrame(obter_galeria_cached())
df_novidades = pd.DataFrame(obter_novidades_cached())


# --- ESTILIZAÇÃO CSS CUSTOMIZADA ---
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

    @keyframes fadeInPage {
        from { opacity: 0; transform: translateY(12px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .main .block-container { animation: fadeInPage 0.45s ease-in-out; }
    .main { background: radial-gradient(circle, #1e293b 0%, #0b0e14 100%); font-size: 1.05rem; }

    h1, h2, h3 { 
        font-family: 'Luckiest Guy', cursive !important; 
        color: #facc15 !important; 
        letter-spacing: 1px;
        text-shadow: 2px 2px 0px #000, -1px -1px 0px #000, 1px -1px 0px #000, -1px 1px 0px #000;
    }
    
    .main-title { text-align: center; margin-top: 8px; margin-bottom: 8px; font-size: 2.8rem !important; }
    .main-subtitle { text-align: center; color: #cbd5e1; font-family: 'Nunito', sans-serif; font-weight: 700; margin-bottom: 25px; }

    .mural-banner {
        background: #1e293b; border-radius: 14px; padding: 14px 18px; margin-bottom: 22px;
        border: 2px solid #334155; border-left: 6px solid #facc15;
        box-shadow: 0 4px 14px rgba(0,0,0,0.3); font-family: 'Nunito', sans-serif;
    }
    .mural-header { font-family: 'Luckiest Guy', cursive; color: #facc15; font-size: 1.15rem; margin-bottom: 4px; }
    </style>
""",
    unsafe_allow_html=True,
)

# --- CABEÇALHO ---
st.markdown(
    '<h1 class="main-title">⚔️ WINNING WARS ⚔️</h1>', unsafe_allow_html=True
)
st.markdown(
    '<p class="main-subtitle">Painel Oficial de Acompanhamento do Clã</p>',
    unsafe_allow_html=True,
)

# Mural de Recados
if mural_recado:
  st.markdown(
      f"""
    <div class="mural-banner">
        <div class="mural-header">📢 Mural de Recados</div>
        <div style="color: #e2e8f0; font-size: 1.05rem;">{mural_recado}</div>
    </div>
    """,
      unsafe_allow_html=True,
  )

# --- NAVEGAÇÃO PRINCIPAL ---
tab_ranking, tab_novidades, tab_layouts, tab_fama = st.tabs([
    "🏆 Ranking",
    "📰 Novidades",
    "🛡️ Layouts",
    "⭐ Galeria da Fama",
])

with tab_ranking:
  st.subheader("🏆 Ranking Atual")
  if not df.empty:
    st.dataframe(df, use_container_width=True)
  else:
    st.info("Nenhum dado encontrado no ranking no momento.")

with tab_novidades:
  st.subheader("📰 Últimas Novidades")
  if not df_novidades.empty:
    for _, row in df_novidades.iterrows():
      st.markdown(f"### {row.get('Titulo', 'Sem Título')}")
      st.write(row.get("Conteudo", ""))
      st.divider()
  else:
    st.info("Nenhuma novidade cadastrada.")

with tab_layouts:
  st.subheader("🛡️ Layouts de Vila")
  if not df_layouts.empty:
    st.dataframe(df_layouts, use_container_width=True)
  else:
    st.info("Nenhum layout cadastrado ainda.")

with tab_fama:
  st.subheader("⭐ Galeria da Fama")
  if not df_fama.empty:
    st.dataframe(df_fama, use_container_width=True)
  else:
    st.info("Galeria da fama vazia.")
