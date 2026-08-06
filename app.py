import hashlib
import json
import random
from datetime import datetime
import gspread
import pandas as pd
import streamlit as st
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

  # Aba de Estado do Mês
  try:
    sheet_estado = spreadsheet.worksheet("EstadoMes")
  except gspread.WorksheetNotFound:
    sheet_estado = spreadsheet.add_worksheet(
        title="EstadoMes", rows="10", cols="2"
    )
    sheet_estado.append_row(["Chave", "Valor"])
    sheet_estado.append_row(["mes_finalizado", "FALSE"])
    sheet_estado.append_row(["sorteio_realizado", "FALSE"])

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

  # Aba de Logs de Alterações (Melhoria de Segurança)
  try:
    sheet_logs = spreadsheet.worksheet("Logs")
  except gspread.WorksheetNotFound:
    sheet_logs = spreadsheet.add_worksheet(title="Logs", rows="1000", cols="3")
    sheet_logs.append_row(["DataHora", "Admin", "Acao"])

  # Aba de Galeria da Fama (Histórico de Campeões)
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


# --- CARREGAR DADOS ---
try:
  dados = sheet_dados.get_all_records()
  df = pd.DataFrame(dados)
except Exception:
  df = pd.DataFrame()

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
except Exception:
  mes_finalizado = False

# ESTADO DE NAVEGAÇÃO
if "pagina_atual" not in st.session_state:
  st.session_state["pagina_atual"] = "principal"


# --- CARREGAR LAYOUTS E GALERIA DA FAMA ---
def carregar_layouts():
  try:
    registros = sheet_layouts.get_all_records()
    return pd.DataFrame(registros)
  except Exception:
    return pd.DataFrame(
        columns=["Tipo", "CV", "Autor", "Link", "Descricao", "ImagemUrl", "Tag"]
    )


def carregar_galeria():
  try:
    registros = sheet_fama.get_all_records()
    return pd.DataFrame(registros)
  except Exception:
    return pd.DataFrame(columns=["MesAno", "Primeiro", "Segundo", "Terceiro"])


df_layouts = carregar_layouts()
df_fama = carregar_galeria()

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
    }
    
    .main-title { text-align: center; margin-top: 5px; margin-bottom: 5px; font-size: 2.5rem; }
    .main-subtitle { text-align: center; color: #94a3b8; font-family: 'Nunito', sans-serif; font-weight: 600; margin-bottom: 25px; }
    
    div.stButton > button {
        background: linear-gradient(180deg, #22c55e 0%, #15803d 100%) !important;
        color: #ffffff !important;
        font-family: 'Luckiest Guy', cursive, sans-serif !important;
        font-size: 1.05rem !important;
        border: 2px solid #86efac !important;
        border-radius: 10px !important;
        box-shadow: 0px 4px 0px #14532d !important;
        transition: all 0.1s ease;
        text-shadow: 1px 1px 0px #000;
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0px 6px 0px #14532d !important;
        background: linear-gradient(180deg, #4ade80 0%, #16a34a 100%) !important;
    }

    .podium-card { padding: 22px; border-radius: 16px; text-align: center; margin-bottom: 25px; color: #ffffff; box-shadow: 0 8px 25px rgba(0,0,0,0.6); font-family: 'Nunito', sans-serif; }
    .podium-title { font-family: 'Luckiest Guy', cursive; font-size: 1.4rem; margin-top: 8px; margin-bottom: 8px; text-shadow: 1px 1px 0px #000; }
    .podium-name { font-size: 1.3rem; font-weight: 800; }
    .podium-score { font-size: 1.1rem; margin-top: 4px; }
    .gold { background: linear-gradient(135deg, #f59e0b 0%, #78350f 100%); border: 3px solid #facc15; }
    .silver { background: linear-gradient(135deg, #64748b 0%, #1e293b 100%); border: 3px solid #cbd5e1; }
    .bronze { background: linear-gradient(135deg, #d97706 0%, #451a03 100%); border: 3px solid #f97316; }

    .btn-layout-copy {
        display: inline-block; width: 100%; max-width: 380px; text-align: center;
        background: linear-gradient(180deg, #3b82f6 0%, #1d4ed8 100%); color: white !important;
        padding: 10px 18px; border-radius: 8px; text-decoration: none; font-family: 'Luckiest Guy', cursive;
        border: 2px solid #93c5fd; box-shadow: 0px 4px 0px #1e3a8a;
    }
    .btn-external-link {
        display: block; width: 100%; text-align: center;
        background: linear-gradient(180deg, #16a34a 0%, #15803d 100%); color: white !important;
        padding: 8px 16px; border-radius: 8px; text-decoration: none; font-family: 'Luckiest Guy', cursive;
        border: 2px solid #86efac; box-shadow: 0px 4px 0px #14532d;
    }

    .info-card { background: #1e293b; border-radius: 12px; padding: 20px; margin-bottom: 15px; border: 2px solid #334155; border-left: 5px solid #facc15; box-shadow: 0 4px 12px rgba(0,0,0,0.4); font-family: 'Nunito', sans-serif; }
    .info-card-header { font-size: 1.1rem; font-weight: bold; color: #facc15; margin-bottom: 10px; font-family: 'Luckiest Guy', cursive; }
    .info-card-list { color: #e2e8f0; margin: 0; padding-left: 20px; line-height: 1.6; }

    .badge-highlight {
        background: #0f172a; border: 2px solid #38bdf8; border-radius: 8px; padding: 8px 12px; margin: 4px; display: inline-block; font-family: 'Nunito', sans-serif; font-weight: bold; color: #e0f2fe;
    }
    </style>
""",
    unsafe_allow_html=True,
)


def renderizar_login_admin_layout(prefixo: str):
  if "admin_logado" not in st.session_state:
    with st.expander("🔐 É Administrador? Clique aqui para fazer Login"):
      with st.form(key=f"form_login_layout_{prefixo}"):
        u_in = st.text_input("Usuário Admin", key=f"u_lay_{prefixo}")
        s_in = st.text_input("Senha", type="password", key=f"s_lay_{prefixo}")
        btn_l = st.form_submit_button("Entrar")
        if btn_l:
          h_in = gerar_hash(s_in)
          val = df_admins[
              (df_admins["Usuario"] == u_in) & (df_admins["SenhaHash"] == h_in)
          ]
          if not val.empty:
            st.session_state["admin_logado"] = u_in
            registrar_log(u_in, "Fez Login pela área de layouts")
            st.success(f"Logado como {u_in}!")
            st.rerun()
          else:
            st.error("Credenciais inválidas.")


# --- BOTÕES SUPERIORES DE NAVEGAÇÃO ---
btn_col1, btn_col2, btn_col3, btn_col4, btn_col5 = st.columns(5)

with btn_col1:
  if st.button("🛡️ Layouts Guerra", use_container_width=True):
    st.session_state["pagina_atual"] = "layouts_guerra"
    st.rerun()

with btn_col2:
  if st.button("🏆 Layouts Rankeada", use_container_width=True):
    st.session_state["pagina_atual"] = "layouts_rankeada"
    st.rerun()

with btn_col3:
  if st.button("🌟 Galeria da Fama", use_container_width=True):
    st.session_state["pagina_atual"] = "galeria_fama"
    st.rerun()

with btn_col4:
  if st.button("📜 Regras Clã", use_container_width=True):
    st.session_state["pagina_atual"] = "regras_cla"
    st.rerun()

with btn_col5:
  st.markdown(
      '<a'
      ' href="https://link.clashofclans.com/pt?action=OpenClanProfile&tag=2YPL9GU8Y"'
      ' target="_blank" class="btn-external-link">🏰 Clã Vastaya ↗</a>',
      unsafe_allow_html=True,
  )

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
  renderizar_login_admin_layout(tipo_layout.lower())

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
      col_header1, col_header2 = st.columns([1, 8])
      with col_header1:
        st.image(th_img_url, width=60)
      with col_header2:
        st.subheader(f"Base de {tipo_layout} - {cv_nome}")

      if eh_admin:
        with st.expander(
            f"➕ [ADMIN] Adicionar Novo Layout de {tipo_layout} ({cv_nome})"
        ):
          with st.form(key=f"form_{tipo_layout}_{cv_nome}"):
            link_layout = st.text_input("Link Oficial do Layout (URL)")
            descricao = st.text_input(
                "Descrição (ex: Anti-3 Estrelas, Farm Ouro)"
            )
            tag_layout = st.selectbox(
                "Tag de Estilo",
                ["#Anti3Estrelas", "#Anti2Estrelas", "#Farm", "#PushTrofes"],
            )
            img_url = st.text_input("Link Direto da Foto (Opcional)")

            btn_enviar = st.form_submit_button("Publicar Layout")

            if btn_enviar:
              if link_layout.strip():
                sheet_layouts.append_row([
                    tipo_layout,
                    cv_nome,
                    st.session_state["admin_logado"],
                    link_layout.strip(),
                    descricao.strip() if descricao.strip() else "Recomendado",
                    img_url.strip(),
                    tag_layout,
                ])
                registrar_log(
                    st.session_state["admin_logado"],
                    f"Adicionou layout {tipo_layout} para {cv_nome}",
                )
                st.success("Layout publicado!")
                st.rerun()

      if not df_layouts.empty:
        layouts_filtrados = df_layouts[
            (df_layouts["Tipo"] == tipo_layout) & (df_layouts["CV"] == cv_nome)
        ]
      else:
        layouts_filtrados = pd.DataFrame()

      if not layouts_filtrados.empty:
        for item_idx, row in layouts_filtrados.iterrows():
          with st.container():
            tag_txt = (
                f" `{row.get('Tag', '#Clash')}`" if row.get("Tag") else ""
            )
            st.markdown(
                f"**👑 Admin:** {row['Autor']} | **📌 Foco:**"
                f" {row['Descricao']}{tag_txt}"
            )

            img_url_limpa = str(row["ImagemUrl"]).strip()
            if img_url_limpa:
              try:
                st.image(img_url_limpa, caption=f"Layout {cv_nome}", width=380)
              except Exception:
                pass

            c_btn, c_del = st.columns([3, 1])
            with c_btn:
              st.markdown(
                  f'<a href="{row["Link"]}" target="_blank"'
                  ' class="btn-layout-copy">📲 COPIAR LAYOUT NO CLASH</a>',
                  unsafe_allow_html=True,
              )
            with c_del:
              if eh_admin:
                if st.button(
                    "❌ Excluir", key=f"del_{tipo_layout}_{cv_nome}_{item_idx}"
                ):
                  cell = sheet_layouts.find(row["Link"])
                  if cell:
                    sheet_layouts.delete_rows(cell.row)
                    registrar_log(
                        st.session_state["admin_logado"],
                        f"Excluiu layout de {cv_nome}",
                    )
                    st.success("Removido!")
                    st.rerun()
            st.divider()
      else:
        st.info(f"Nenhum layout cadastrado para {cv_nome}.")


# ==============================================================================
# PÁGINA: GALERIA DA FAMA (HISTÓRICO)
# ==============================================================================
def renderizar_galeria_fama():
  if st.button("⬅️ Voltar ao Início"):
    st.session_state["pagina_atual"] = "principal"
    st.rerun()

  st.markdown(
      "<h1 style='text-align: center;'>🌟 Galeria da Fama - Campeões dos"
      " Meses Anteriores</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='text-align: center; color: #94a3b8;'>Eternizando os guerreiros"
      " que conquistaram o Passe Dourado na história do Clã!</p><br>",
      unsafe_allow_html=True,
  )

  if not df_fama.empty:
    st.dataframe(df_fama, use_container_width=True, hide_index=True)
  else:
    st.info("Nenhum histórico de meses anteriores registrado ainda.")


# ==============================================================================
# SELEÇÃO DE PÁGINAS
# ==============================================================================
if st.session_state["pagina_atual"] == "layouts_guerra":
  renderizar_pagina_layouts("Guerra", "🛡️ Layouts Oficiais de Guerra")
elif st.session_state["pagina_atual"] == "layouts_rankeada":
  renderizar_pagina_layouts("Rankeada", "🏆 Layouts Oficiais de Rankeada")
elif st.session_state["pagina_atual"] == "galeria_fama":
  renderizar_galeria_fama()

# ==============================================================================
# PÁGINA PRINCIPAL
# ==============================================================================
else:
  st.markdown(
      """
    <div style="text-align: center; margin-bottom: 10px;">
        <img src="https://i.ibb.co/yBShz18b/winning.png" width="130" style="filter: drop-shadow(0px 6px 12px rgba(0,0,0,0.6));">
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
        posicoes.append(f"  {i}º")
    df_rank["Posição"] = posicoes
  else:
    colunas_raides, colunas_guerras, colunas_liga = [], [], []

  # MÉTRICAS RESUMIDAS DO CLÃ
  if not df.empty and "Total" in df.columns:
    m1, m2, m3 = st.columns(3)
    m1.metric("👥 Jogadores Ativos", len(df))
    m2.metric("⭐ Média de Pontos", f"{int(df['Total'].mean())} pts")
    m3.metric("🔥 Total Acumulado", f"{int(df['Total'].sum())} pts")

  tab_ranking, tab_tabela, tab_admin = st.tabs(
      ["🏆 Ranking ao Vivo", "📋 Tabela Detalhada", "🔐 Área Admin"]
  )

  # ABA 1: RANKING AO VIVO
  with tab_ranking:
    if not df.empty and "Total" in df.columns:
      # DESTAQUES / BADGES AUTOMÁTICAS
      cols_war_all = colunas_guerras + colunas_liga
      if cols_war_all:
        df["WarTotal"] = df[cols_war_all].sum(axis=1)
        top_war = df.sort_values(by="WarTotal", ascending=False).iloc[0]
        if top_war["WarTotal"] > 0:
          st.markdown(
              f'<div class="badge-highlight">🗡️ O Rei da Guerra:'
              f' {top_war["Nome"]} ({int(top_war["WarTotal"])}⭐)</div>',
              unsafe_allow_html=True,
          )

      if "JogosCla" in df.columns:
        top_jogos = df.sort_values(by="JogosCla", ascending=False).iloc[0]
        if top_jogos["JogosCla"] > 0:
          st.markdown(
              f'<div class="badge-highlight">🎯 Mestre dos Jogos:'
              f' {top_jogos["Nome"]} ({int(top_jogos["JogosCla"])} pts)</div>',
              unsafe_allow_html=True,
          )

      st.write("")

      if mes_finalizado:
        st.success(
            "🔒 **O MÊS FOI FINALIZADO PELO ADMIN! CONFIRA OS CAMPEÕES:**"
        )
        col1, col2, col3 = st.columns(3)
        if len(df_rank) >= 1:
          with col1:
            st.markdown(
                f'<div class="podium-card gold"><img'
                ' src="https://i.ibb.co/mkC43vT/goldenpass.png" width="60"><div'
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
                ' src="https://i.ibb.co/mkC43vT/goldenpass.png" width="60"><div'
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
                ' src="https://i.ibb.co/mkC43vT/goldenpass.png" width="60"><div'
                ' class="podium-title">🥉 3º LUGAR</div><div'
                f' class="podium-name">{df_rank.iloc[2]["Nome"]}</div><div'
                ' class="podium-score">'
                f'{int(df_rank.iloc[2]["Total"])} pts</div><small>Garantidor do'
                " Passe Dourado 🎟️</small></div>",
                unsafe_allow_html=True,
            )

      st.subheader("📊 Classificação em Tempo Real")
      df_exibicao = df_rank[["Posição", "Nome", "Total"]].copy()
      df_exibicao["Total"] = df_exibicao["Total"].astype(int)
      df_exibicao.rename(
          columns={"Nome": "Jogador", "Total": "Pontuação Total"}, inplace=True
      )

      def destacar_podio(row):
        pos = str(row["Posição"])
        if "🥇" in pos:
          return [
              "background-color: #78350f; color: #facc15; font-weight: bold;"
          ] * 3
        elif "🥈" in pos:
          return [
              "background-color: #334155; color: #cbd5e1; font-weight: bold;"
          ] * 3
        elif "🥉" in pos:
          return [
              "background-color: #451a03; color: #f97316; font-weight: bold;"
          ] * 3
        return [""] * 3

      st.dataframe(
          df_exibicao.style.apply(destacar_podio, axis=1).format(
              {"Pontuação Total": "{} pts"}
          ),
          use_container_width=True,
          hide_index=True,
      )

  # ABA 2: TABELA DETALHADA
  with tab_tabela:
    if not df.empty and "Total" in df.columns:
      cols_exibicao = (
          ["Nome"]
          + [c for c in ["JogosCla", "Eventos"] if c in df.columns]
          + colunas_guerras
          + colunas_liga
          + colunas_raides
          + ["Total"]
      )
      st.dataframe(
          df[cols_exibicao].sort_values(by="Total", ascending=False),
          use_container_width=True,
          hide_index=True,
      )

  # ABA 3: ÁREA ADMIN
  with tab_admin:
    st.subheader("🔐 Painel de Controle e Administração")
    with st.form("form_login"):
      usuario_input = st.text_input("Usuário Admin")
      senha_input = st.text_input("Senha", type="password")
      btn_login = st.form_submit_button("Acessar Painel")

    if btn_login:
      hash_input = gerar_hash(senha_input)
      admin_valido = df_admins[
          (df_admins["Usuario"] == usuario_input)
          & (df_admins["SenhaHash"] == hash_input)
      ]
      if not admin_valido.empty:
        st.session_state["admin_logado"] = usuario_input
        registrar_log(usuario_input, "Logou no Painel Admin")
        st.success(f"Bem-vindo, {usuario_input}!")
        st.rerun()

    if "admin_logado" in st.session_state:
      st.write("---")
      st.success(f"Sessão Ativa: **{st.session_state['admin_logado']}**")

      sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
          "➕ Players",
          "✏️ Editar Pontos",
          "📜 Arquivar Mês (Galeria)",
          "📜 Logs do Sistema",
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
              st.success("Adicionado!")
              st.rerun()
        with c2:
          if not df.empty and "Nome" in df.columns:
            player_rem = st.selectbox("Remover", df["Nome"].tolist())
            if st.button("Remover Player", type="primary"):
              cell = sheet_dados.find(player_rem)
              sheet_dados.delete_rows(cell.row)
              registrar_log(
                  st.session_state["admin_logado"],
                  f"Removeu player {player_rem}",
              )
              st.success("Removido!")
              st.rerun()

      with sub_tab2:
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
            st.success("Salvo com sucesso!")
            st.rerun()

      with sub_tab3:
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
            st.success("Registrado na Galeria da Fama!")
            st.rerun()

      with sub_tab4:
        st.markdown("#### 🛡️ Registro de Atividades dos Admins")
        try:
          df_logs_exib = pd.DataFrame(sheet_logs.get_all_records())
          st.dataframe(
              df_logs_exib.tail(20), use_container_width=True, hide_index=True
          )
        except Exception:
          st.info("Nenhum log registrado ainda.")
