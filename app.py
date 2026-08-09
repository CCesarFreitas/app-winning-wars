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
    page_title="Winning Wars - Competição Mensal", page_icon="⚔️", layout="wide"
)


# --- FUNÇÕES AUXILIARES ---
def gerar_hash(senha: str) -> str:
  return hashlib.sha256(senha.encode()).hexdigest()


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
    sheet_admins.append_row(["admin", gerar_hash("winning123")])

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

  return (
      sheet_dados,
      sheet_admins,
      sheet_estado,
      sheet_layouts,
      sheet_logs,
      sheet_fama,
  )


try:
  (
      sheet_dados,
      sheet_admins,
      sheet_estado,
      sheet_layouts,
      sheet_logs,
      sheet_fama,
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


dados = obter_dados_cached()
df = pd.DataFrame(dados) if dados else pd.DataFrame()

try:
  dados_admins = sheet_admins.get_all_records()
  df_admins = pd.DataFrame(dados_admins)
except Exception:
  df_admins = pd.DataFrame(
      [["admin", gerar_hash("winning123")]], columns=["Usuario", "SenhaHash"]
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


# --- FUNÇÃO PARA GERAR A TABELA COMPLETA EM HTML ---
def gerar_tabela_bilhete_dourado(df_exib):
  """Gera o HTML completo do ranking para renderização em iframe com visual padronizado ao app."""
  from html import escape

  linhas_html = []
  for _, row in df_exib.iterrows():
    posicao = escape(str(row.get("Posição", "")))
    jogador = escape(str(row.get("Jogador", "")))
    try:
      pontuacao = int(float(row.get("Pontuação Total", 0)))
    except (TypeError, ValueError):
      pontuacao = 0

    linhas_html.append(
        f'<tr><td class="tabela-posicao">{posicao}</td>'
        f'<td class="tabela-nome">{jogador}</td>'
        f'<td class="tabela-pontos">{pontuacao}</td></tr>'
    )

  return f"""
  <!DOCTYPE html>
  <html>
  <head>
    <meta charset="UTF-8">
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Luckiest+Guy&family=Nunito:wght@600;800&display=swap');

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
        font-size: 2rem !important;
        letter-spacing: 1px;
        text-shadow: 2px 2px 0px #000, -1px -1px 0px #000, 1px -1px 0px #000, -1px 1px 0px #000;
        margin: 0 !important;
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
        width: 90px; 
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
    <div class="bilhete-dourado-container">
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
        <img src="https://i.ibb.co/YFbsJ97x/Clash-of-Clans-emblem.png" alt="Emblema Clash of Clans">
      </div>
    </div>
  </body>
  </html>
  """


# --- ESTILIZAÇÃO CSS CUSTOMIZADA ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Luckiest+Guy&family=Nunito:wght@600;800&display=swap');

    .main { background: radial-gradient(circle, #1e293b 0%, #0b0e14 100%); }

    h1, h2, h3 { 
        font-family: 'Luckiest Guy', cursive !important; 
        color: #facc15 !important; 
        letter-spacing: 1px;
        text-shadow: 2px 2px 0px #000, -1px -1px 0px #000, 1px -1px 0px #000, -1px 1px 0px #000;
        word-break: break-word;
    }
    
    .main-title { 
        text-align: center; 
        margin-top: 5px; 
        margin-bottom: 5px; 
        font-size: 2.2rem; 
        line-height: 1.2;
    }

    .main-subtitle { 
        text-align: center; 
        color: #94a3b8; 
        font-family: 'Nunito', sans-serif; 
        font-weight: 600; 
        margin-bottom: 20px; 
        font-size: 1rem;
        padding: 0 10px;
    }
    
    /* BOTÕES GERAIS */
    div.stButton > button {
        background: linear-gradient(180deg, #22c55e 0%, #15803d 100%) !important;
        color: #ffffff !important;
        font-family: 'Luckiest Guy', cursive, sans-serif !important;
        font-size: 0.95rem !important;
        border: 2px solid #86efac !important;
        border-radius: 10px !important;
        box-shadow: 0px 4px 0px #14532d !important;
        transition: all 0.1s ease;
        text-shadow: 1px 1px 0px #000;
        white-space: normal !important;
        height: auto !important;
        padding: 8px 12px !important;
    }

    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0px 6px 0px #14532d !important;
        background: linear-gradient(180deg, #4ade80 0%, #16a34a 100%) !important;
    }

    /* ABAS */
    button[data-baseweb="tab"] {
        font-size: 1.25rem !important;
        font-weight: 800 !important;
        font-family: 'Nunito', sans-serif !important;
        padding: 12px 22px !important;
        background-color: #1e293b !important;
        border: 2px solid #334155 !important;
        border-radius: 10px 10px 0 0 !important;
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
        box-shadow: 0px 4px 12px rgba(250, 204, 21, 0.3) !important;
    }

    button[data-baseweb="tab"]:hover {
        border-color: #facc15 !important;
        color: #facc15 !important;
    }

    /* PODIUM E CARDS */
    .podium-card { 
        padding: 16px; 
        border-radius: 16px; 
        text-align: center; 
        margin-bottom: 15px; 
        color: #ffffff; 
        box-shadow: 0 8px 25px rgba(0,0,0,0.6); 
        font-family: 'Nunito', sans-serif; 
    }
    .podium-title { font-family: 'Luckiest Guy', cursive; font-size: 1.2rem; margin-top: 6px; margin-bottom: 6px; text-shadow: 1px 1px 0px #000; }
    .podium-name { font-size: 1.1rem; font-weight: 800; word-break: break-word; }
    .podium-score { font-size: 1rem; margin-top: 4px; }
    .gold { background: linear-gradient(135deg, #f59e0b 0%, #78350f 100%); border: 3px solid #facc15; }
    .silver { background: linear-gradient(135deg, #64748b 0%, #1e293b 100%); border: 3px solid #cbd5e1; }
    .bronze { background: linear-gradient(135deg, #d97706 0%, #451a03 100%); border: 3px solid #f97316; }

    .btn-layout-copy {
        display: inline-block; width: 100%; max-width: 100%; text-align: center;
        background: linear-gradient(180deg, #3b82f6 0%, #1d4ed8 100%); color: white !important;
        padding: 12px 16px; border-radius: 10px; text-decoration: none; font-family: 'Luckiest Guy', cursive;
        border: 2px solid #93c5fd; box-shadow: 0px 4px 0px #1e3a8a; font-size: 1.05rem;
    }
    .btn-external-link {
        display: flex; align-items: center; justify-content: center; gap: 6px; width: 100%; text-align: center;
        background: linear-gradient(180deg, #16a34a 0%, #15803d 100%); color: white !important;
        padding: 8px 10px; border-radius: 8px; text-decoration: none; font-family: 'Luckiest Guy', cursive;
        border: 2px solid #86efac; box-shadow: 0px 4px 0px #14532d; font-size: 0.88rem;
    }
    .btn-scid {
        display: flex; align-items: center; justify-content: center; gap: 6px; width: 100%; text-align: center;
        background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%); color: white !important;
        padding: 8px 10px; border-radius: 8px; text-decoration: none; font-family: 'Luckiest Guy', cursive;
        border: 2px solid #60a5fa; box-shadow: 0px 4px 0px #1e3a8a; font-size: 0.88rem;
    }

    .mural-banner {
        background: #1e293b; border-radius: 12px; padding: 12px 15px; margin-bottom: 20px;
        border: 2px solid #334155; border-left: 6px solid #facc15;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3); font-family: 'Nunito', sans-serif;
    }
    .mural-header { font-family: 'Luckiest Guy', cursive; color: #facc15; font-size: 1rem; margin-bottom: 4px; }

    .info-card {
        background: #0f172a; border: 2px solid #334155; border-radius: 14px; padding: 20px; margin-bottom: 15px;
        font-family: 'Nunito', sans-serif; color: #e2e8f0; box-shadow: 0 6px 18px rgba(0,0,0,0.4); height: 100%;
    }
    .info-card-header { font-family: 'Luckiest Guy', cursive; color: #facc15; font-size: 1.15rem; margin-bottom: 10px; }
    .info-card-list { padding-left: 18px; margin-bottom: 0px; }
    .info-card-list li { margin-bottom: 8px; line-height: 1.4; font-size: 0.95rem; }

    .rules-card {
        background: #0f172a; border: 2px solid #334155; border-radius: 14px; padding: 22px; margin-top: 35px;
        font-family: 'Nunito', sans-serif; color: #e2e8f0; box-shadow: 0 6px 18px rgba(0,0,0,0.4);
    }
    .rules-title { font-family: 'Luckiest Guy', cursive; color: #facc15; font-size: 1.3rem; margin-bottom: 12px; }
    .rules-card ul { margin-bottom: 0px; padding-left: 20px; }
    .rules-card li { margin-bottom: 10px; line-height: 1.5; }

    @media (max-width: 768px) {
        .main-title { font-size: 1.6rem !important; }
        .main-subtitle { font-size: 0.88rem !important; }
        .mural-banner { padding: 10px !important; }
        .podium-card { padding: 12px !important; }
        button[data-baseweb="tab"] { font-size: 1rem !important; padding: 8px 10px !important; }
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- TOPO DA PÁGINA: MENU DE NAVEGAÇÃO + LOGIN ADMIN ---
col_nav, col_admin_top = st.columns([5, 1])

with col_nav:
  b1, b2, b3, b4, b5 = st.columns(5)
  with b1:
    if st.button("🛡️ Layouts Guerra", use_container_width=True):
      st.session_state["pagina_atual"] = "layouts_guerra"
      st.rerun()
  with b2:
    if st.button("🏆 Layouts Rankeada", use_container_width=True):
      st.session_state["pagina_atual"] = "layouts_rankeada"
      st.rerun()
  with b3:
    if st.button("📜 Regras do Clã", use_container_width=True):
      st.session_state["pagina_atual"] = "regras_cla"
      st.rerun()
  with b4:
    st.markdown(
        '<a'
        ' href="https://link.clashofclans.com/pt?action=OpenClanProfile&tag=2YPL9GU8Y"'
        ' target="_blank" class="btn-external-link">🏰 Clã Vastaya ↗</a>',
        unsafe_allow_html=True,
    )
  with b5:
    st.markdown(
        '<a'
        ' href="https://link.clashofclans.com/?action=OpenSCID&p=25-1cb8481f-3a79-4681-90f9-8914acef2d63"'
        ' target="_blank" class="btn-scid"><img'
        ' src="https://i.ibb.co/fzPGy6fr/bg-hero-scid-landing-0.webp"'
        ' height="20" style="border-radius: 4px; object-fit:'
        ' cover;"> Add Godoy ↗</a>',
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
                <img src="{th_img_url}" width="80" style="filter: drop-shadow(0px 4px 8px rgba(0,0,0,0.5));">
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
        # Inverte os resultados para que os mais recentes apareçam no topo
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
                # Botão para baixar a imagem visível APENAS para Admins
                if eh_admin:
                  st.markdown(
                      f'<div style="text-align: center; margin-bottom: 10px;"><a href="{img_url_limpa}" target="_blank" download style="color: #38bdf8; text-decoration: underline; font-weight: bold; font-size: 0.9rem;">📥 Baixar Imagem (Admin)</a></div>',
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
  renderizar_pagina_layouts("Rankeada", "🏆 Layouts Oficiais de Rankeada")
elif st.session_state["pagina_atual"] == "regras_cla":
  renderizar_regras_cla()

# ==============================================================================
# PÁGINA PRINCIPAL
# ==============================================================================
else:
  st.markdown(
      """
    <div style="text-align: center; margin-bottom: 10px;">
        <img src="https://i.ibb.co/yBShz18b/winning.png" width="110" style="filter: drop-shadow(0px 6px 12px rgba(0,0,0,0.6));">
    </div>
    """,
      unsafe_allow_html=True,
  )

  st.markdown(
      "<h1 class='main-title'>⚔️ Clã Winning Wars - Competição Mensal</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p class='main-subtitle'>Acompanhe o ranking em tempo real. Ao final do"
      " mês, os Top 3 garantem o Passe Dourado!</p>",
      unsafe_allow_html=True,
  )

  # MURAL DE RECADOS
  if mural_recado.strip():
    st.markdown(
        f"""
        <div class="mural-banner">
            <div class="mural-header">📢 MURAL DA LIDERANÇA</div>
            <div style="color: #e2e8f0; font-size: 0.95rem;">{mural_recado}</div>
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
                f'<div class="podium-card gold"><img'
                ' src="https://i.ibb.co/mkC43vT/goldenpass.png" width="50"><div'
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
                ' src="https://i.ibb.co/mkC43vT/goldenpass.png" width="50"><div'
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
                ' src="https://i.ibb.co/mkC43vT/goldenpass.png" width="50"><div'
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

      # RENDERIZA A TABELA BILHETE DOURADO
      components.html(
          gerar_tabela_bilhete_dourado(df_exibicao),
          height=min(2200, max(300, 175 + len(df_exibicao) * 39)),
          scrolling=False,
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
      for _, row in df_tabela_mobile.iterrows():
        nome = str(row["Nome"])
        destaque = " jogador-destaque" if busca_detalhada and busca_detalhada in nome.lower() else ""
        cells = []
        for i, col in enumerate(cols_exibicao):
          valor = row[col]
          try:
            valor = int(float(valor))
          except (TypeError, ValueError):
            valor = str(valor)
          classe = "sticky-nome" if i == 0 else "sticky-total" if i == len(cols_exibicao) - 1 else ""
          cells.append(f'<td class="{classe}">{escape(str(valor))}</td>')
        linhas.append(f'<tr class="{destaque}">' + "".join(cells) + "</tr>")

      html_tabela = f"""
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
          * {{ box-sizing: border-box; }}
          body {{ margin: 0; background: transparent; font-family: Arial, sans-serif; }}
          .legenda {{ display:flex; flex-wrap:wrap; gap:6px; margin:0 0 8px; color:#cbd5e1; font-size:11px; line-height:1.3; }}
          .badge {{ padding:5px 8px; border-radius:999px; background:#1e293b; border:1px solid #475569; }}
          .viewport {{ width:100%; overflow:auto; max-height:68vh; border:1px solid #334155; border-radius:10px; -webkit-overflow-scrolling:touch; }}
          table {{ border-collapse:separate; border-spacing:0; min-width:760px; width:max-content; }}
          th,td {{ padding:8px 10px; border-right:1px solid #334155; border-bottom:1px solid #334155; text-align:center; white-space:nowrap; font-size:12px; color:#e2e8f0; background:#0f172a; }}
          thead th {{ background:#1e293b; font-weight:800; position:sticky; z-index:5; }}
          thead tr:first-child th {{ top:0; color:#facc15; font-size:10px; letter-spacing:.5px; height:28px; }}
          thead tr:nth-child(2) th {{ top:28px; color:#f8fafc; height:30px; }}
          tbody tr:nth-child(even) td {{ background:#111827; }}
          tbody tr:hover td {{ background:#1e293b; }}
          .sticky-nome {{ position:sticky !important; left:0; z-index:4; min-width:145px; max-width:145px; text-align:left; font-weight:800; box-shadow:5px 0 8px rgba(0,0,0,.25); }}
          thead .sticky-nome {{ z-index:8; background:#1e293b !important; }}
          .sticky-total {{ position:sticky !important; right:0; z-index:4; min-width:78px; font-weight:900; color:#facc15 !important; background:#172554 !important; box-shadow:-5px 0 8px rgba(0,0,0,.25); }}
          thead .sticky-total {{ z-index:8; background:#172554 !important; }}
          .grupo {{ text-align:center; background:#334155 !important; color:#facc15 !important; }}
          .grupo-canto-esq {{ min-width:145px; background:#334155 !important; position:sticky; left:0; z-index:9; }}
          .grupo-canto-dir {{ min-width:78px; background:#334155 !important; position:sticky; right:0; z-index:9; }}
          .jogador-destaque td {{ background:rgba(250,204,21,.18) !important; color:#fff !important; font-weight:900; }}
          .jogador-destaque .sticky-nome,.jogador-destaque .sticky-total {{ background:#713f12 !important; color:#fff !important; }}
          .vazio {{ padding:28px; text-align:center; color:#94a3b8; background:#0f172a; }}
          @media (max-width:600px) {{
            table {{ min-width:680px; }}
            th,td {{ padding:7px 8px; font-size:11px; }}
            .sticky-nome {{ min-width:125px; max-width:125px; }}
            .sticky-total {{ min-width:68px; }}
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
          <span class="badge">👈 Deslize horizontalmente</span>
          <span class="badge">📌 Nome e Total ficam fixos</span>
        </div>
        <div class="viewport">
          <table>
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
      </body>
      </html>
      """

      altura = min(900, max(300, 150 + len(df_tabela_mobile) * 38))
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

      sub_tab1, sub_tab2, sub_tab3, sub_tab4, sub_tab5, sub_tab6, sub_tab7 = st.tabs([
          "➕ Players",
          "👤 Novo Admin",
          "✏️ Gerenciar Pontos e Colunas",
          "📢 Recado / Arquivar Mês",
          "📜 Logs do Sistema",
          "💾 Backup de Dados",
          "🎲 Sorteio de Desempate",
      ])

      with sub_tab1:
        c1, c2 = st.columns(2)
        with c1:
          novo_nome = st.text_input("Nome do Player")
          if st.button("Cadastrar Player"):
            if novo_nome.strip() != "":
              novo_id = len(dados) + 1
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

      # === SUB TAB 3: GERENCIAR COLUNAS (GUERRA, LIGA, RAIDE) E PONTOS ===
      with sub_tab3:
        st.markdown("#### ➕ Criar Novas Colunas de Guerras, Liga ou Raides")
        st.markdown(
            "Clique nos botões abaixo para criar automaticamente as próximas"
            " colunas na sequência. Elas serão salvas no banco de dados e"
            " somadas ao total geral automaticamente!"
        )

        col_btn1, col_btn2, col_btn3 = st.columns(3)

        # BOTAO GUERRA
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

        # BOTAO LIGA
        with col_btn2:
          proxima_liga = obter_proxima_coluna_sequencial(
              "Liga", df.columns if not df.empty else []
          )
          if st.button(
              f"🏆 Criar Liga ({proxima_liga})",
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

        # BOTAO RAIDE
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
            novos_dados = [
                df_editado.columns.values.tolist()
            ] + df_editado.fillna(0).values.tolist()
            sheet_dados.clear()
            sheet_dados.update(novos_dados)
            registrar_log(
                st.session_state["admin_logado"],
                "Atualizou a planilha de pontos em lote",
            )
            st.cache_data.clear()
            st.success("Pontuações salvas e atualizadas com sucesso!")
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

        st.markdown("#### 🌟 Salvar Mês na Galeria da Fama")
        mes_ano_ref = st.text_input("Mês/Ano de Referência (Ex: Janeiro/2026)")
        if st.button("🏆 Arquivar Campeões do Mês"):
          if len(df_rank) >= 3 and mes_ano_ref.strip():
            sheet_fama.append_row([
                mes_ano_ref.strip(),
                df_rank.iloc[0]["Nome"],
                df_rank.iloc[1]["Nome"],
                df_rank.iloc[2]["Nome"],
            ])
            registrar_log(
                st.session_state["admin_logado"],
                f"Arquivou campeões de {mes_ano_ref}",
            )
            st.cache_data.clear()
            st.success("Registrado na Galeria da Fama!")
            st.rerun()

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
          # Identifica a maior pontuação da tabela
          maior_pontuacao = df_rank["Total"].max()

          # Filtra estritamente os jogadores empatados na pontuação máxima
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

            # Exibição dos Participantes
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

            # Configuração da quantidade de prêmios a sortear
            qtd_vagas = st.number_input(
                "Número de ganhadores a sortear entre os empatados:",
                min_value=1,
                max_value=qtd_empatados,
                value=1,
                step=1,
            )

            if st.button("🎰 INICIAR SORTEIO AO VIVO", type="primary"):
              # Animação de Contagem Regressiva para o Vídeo
              status_text = st.empty()
              bar = st.progress(0)

              for i in range(100):
                time.sleep(0.03)  # Delay dramático para a gravação
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

              # Realiza o sorteio
              vencedores = random.sample(lista_empatados, int(qtd_vagas))

              # Efeitos visuais
              st.balloons()

              # Registro de data/hora e Hash de verificação para auditoria
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

              # Registrar ação no Log
              registrar_log(
                  st.session_state["admin_logado"],
                  f"Realizou sorteio de desempate entre {lista_empatados}. Vencedor(es): {vencedores} (Hash: {hash_auditoria.upper()})",
              )
        else:
          st.info("Nenhum dado de ranking encontrado para realizar o sorteio.")

  # SEÇÃO EXPLICATIVA (RODAPÉ)
  st.write("---")
  st.markdown(
      "<h2 style='text-align: center;'>📜 Regulamento & Sistema de"
      " Premiação</h2>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='text-align: center; color: #94a3b8;'>A ideia é simples:"
      " valorizar quem joga bem, participa ativamente e ajuda o clã a"
      " crescer!</p><br>",
      unsafe_allow_html=True,
  )

  info_col1, info_col2, info_col3 = st.columns(3)

  with info_col1:
    st.markdown(
        """
        <div class="info-card" style="text-align: center;">
            <img src="https://i.ibb.co/mkC43vT/goldenpass.png" width="55" style="margin-bottom: 8px;">
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
            <img src="https://i.ibb.co/3PPkJD8/War-League-Main-Banner.webp" width="70" style="margin-bottom: 8px;">
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
            <img src="https://i.ibb.co/YFbsJ97x/Clash-of-Clans-emblem.png" width="55" style="margin-bottom: 8px;">
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
      "<p style='text-align: center; color: #94a3b8;'>Histórico dos grandes"
      " guerreiros do clã que conquistarão o Passe Dourado!</p><br>",
      unsafe_allow_html=True,
  )

  if not df_fama.empty:
    st.dataframe(df_fama, use_container_width=True, hide_index=True)
  else:
    st.info("Nenhum histórico de meses anteriores registrado ainda.")
