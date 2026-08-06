import hashlib
import json
import random
import re
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
        title="Layouts", rows="500", cols="6"
    )
    sheet_layouts.append_row(
        ["Tipo", "CV", "Autor", "Link", "Descricao", "ImagemUrl"]
    )

  return sheet_dados, sheet_admins, sheet_estado, sheet_layouts


try:
  sheet_dados, sheet_admins, sheet_estado, sheet_layouts = conectar_banco()
except Exception:
  st.error(
      "⚠️ **Erro na Conexão:** Não foi possível acessar a planilha"
      " 'WinningWars_DB'. Verifique suas permissões."
  )
  st.stop()

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

# ESTADO DE NAVEGAÇÃO ENTRE PÁGINAS
if "pagina_atual" not in st.session_state:
  st.session_state["pagina_atual"] = "principal"


# --- CARREGAR LAYOUTS DO BANCO DE DADOS ---
def carregar_layouts():
  try:
    registros = sheet_layouts.get_all_records()
    return pd.DataFrame(registros)
  except Exception:
    return pd.DataFrame(
        columns=["Tipo", "CV", "Autor", "Link", "Descricao", "ImagemUrl"]
    )


df_layouts = carregar_layouts()

# --- ESTILIZAÇÃO CSS CUSTOMIZADA (TEMA CLASH OF CLANS) ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Luckiest+Guy&family=Nunito:wght@600;800&display=swap');

    .main { 
        background: radial-gradient(circle, #1e293b 0%, #0b0e14 100%); 
    }

    /* TÍTULOS COM FONTE TEMÁTICA */
    h1, h2, h3 { 
        font-family: 'Luckiest Guy', cursive !important; 
        color: #facc15 !important; 
        letter-spacing: 1px;
        text-shadow: 2px 2px 0px #000, -1px -1px 0px #000, 1px -1px 0px #000, -1px 1px 0px #000;
    }
    
    .main-title { 
        text-align: center; 
        margin-top: 5px; 
        margin-bottom: 5px; 
        font-size: 2.5rem;
    }
    .main-subtitle { 
        text-align: center; 
        color: #94a3b8; 
        font-family: 'Nunito', sans-serif;
        font-weight: 600;
        margin-bottom: 25px; 
    }
    
    /* BOTÕES COM DESIGN ESTILO CLASH (3D/CARTOON) */
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
    div.stButton > button:active {
        transform: translateY(2px);
        box-shadow: 0px 1px 0px #14532d !important;
    }

    /* PÓDIO */
    .podium-card { 
        padding: 22px; 
        border-radius: 16px; 
        text-align: center; 
        margin-bottom: 25px; 
        color: #ffffff; 
        box-shadow: 0 8px 25px rgba(0,0,0,0.6); 
        font-family: 'Nunito', sans-serif;
    }
    .podium-title {
        font-family: 'Luckiest Guy', cursive;
        font-size: 1.4rem;
        margin-top: 8px;
        margin-bottom: 8px;
        text-shadow: 1px 1px 0px #000;
    }
    .podium-name {
        font-size: 1.3rem;
        font-weight: 800;
    }
    .podium-score {
        font-size: 1.1rem;
        margin-top: 4px;
    }
    .gold { background: linear-gradient(135deg, #f59e0b 0%, #78350f 100%); border: 3px solid #facc15; }
    .silver { background: linear-gradient(135deg, #64748b 0%, #1e293b 100%); border: 3px solid #cbd5e1; }
    .bronze { background: linear-gradient(135deg, #d97706 0%, #451a03 100%); border: 3px solid #f97316; }

    /* BOTÕES DE LINK E NAVEGAÇÃO EXTERNA */
    .btn-layout-copy {
        display: inline-block;
        width: 100%;
        max-width: 380px;
        text-align: center;
        background: linear-gradient(180deg, #3b82f6 0%, #1d4ed8 100%);
        color: white !important;
        padding: 10px 18px;
        border-radius: 8px;
        text-decoration: none;
        font-family: 'Luckiest Guy', cursive;
        border: 2px solid #93c5fd;
        box-shadow: 0px 4px 0px #1e3a8a;
    }
    .btn-layout-copy:hover { transform: translateY(-2px); }

    .btn-external-link {
        display: block;
        width: 100%;
        text-align: center;
        background: linear-gradient(180deg, #16a34a 0%, #15803d 100%);
        color: white !important;
        padding: 8px 16px;
        border-radius: 8px;
        text-decoration: none;
        font-family: 'Luckiest Guy', cursive;
        border: 2px solid #86efac;
        box-shadow: 0px 4px 0px #14532d;
    }

    /* CARDS DE INFORMAÇÃO E REGULAMENTO */
    .info-card {
        background: #1e293b;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        border: 2px solid #334155;
        border-left: 5px solid #facc15;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        font-family: 'Nunito', sans-serif;
    }
    .info-card-header {
        font-size: 1.1rem;
        font-weight: bold;
        color: #facc15;
        margin-bottom: 10px;
        font-family: 'Luckiest Guy', cursive;
    }
    .info-card-list {
        color: #e2e8f0;
        margin: 0;
        padding-left: 20px;
        line-height: 1.6;
    }

    /* CARDS DE REGRAS OFICIAIS */
    .rule-card {
        background: #1e293b;
        border: 2px solid #334155;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        font-family: 'Nunito', sans-serif;
    }
    .rule-number {
        font-family: 'Luckiest Guy', cursive;
        font-size: 1.3rem;
        color: #facc15;
        background: #0f172a;
        border: 2px solid #facc15;
        border-radius: 50%;
        width: 42px;
        height: 42px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-right: 15px;
        flex-shrink: 0;
    }
    .rule-text {
        color: #f8fafc;
        font-size: 1rem;
        line-height: 1.4;
        font-weight: 600;
    }
    </style>
""",
    unsafe_allow_html=True,
)


# --- LOGIN RÁPIDO DE ADMIN NAS PÁGINAS DE LAYOUT ---
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
            st.success(f"Logado como {u_in}!")
            st.rerun()
          else:
            st.error("Credenciais inválidas.")


# --- BOTÕES SUPERIORES DE NAVEGAÇÃO ---
btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)

with btn_col1:
  if st.button("🛡️ Layouts de Guerra", use_container_width=True):
    st.session_state["pagina_atual"] = "layouts_guerra"
    st.rerun()

with btn_col2:
  if st.button("🏆 Layouts de Rankeada", use_container_width=True):
    st.session_state["pagina_atual"] = "layouts_rankeada"
    st.rerun()

with btn_col3:
  if st.button("📜 Regras do Clã", use_container_width=True):
    st.session_state["pagina_atual"] = "regras_cla"
    st.rerun()

with btn_col4:
  st.markdown(
      '<a'
      ' href="https://link.clashofclans.com/pt?action=OpenClanProfile&tag=2YPL9GU8Y"'
      ' target="_blank" class="btn-external-link">🏰 Clã Farm Vastaya ↗</a>',
      unsafe_allow_html=True,
  )

st.write("---")


# ==============================================================================
# FUNÇÃO REUTILIZÁVEL PARA RENDERIZAR PÁGINAS DE LAYOUT
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

  # Mapeamento dos Centros de Vila com imagens oficiais
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

      # Form exclusivo para Administradores
      if eh_admin:
        with st.expander(
            f"➕ [ADMIN] Adicionar Novo Layout de {tipo_layout} ({cv_nome})"
        ):
          with st.form(key=f"form_{tipo_layout}_{cv_nome}"):
            link_layout = st.text_input(
                "Link Oficial do Layout (URL)",
                key=f"input_link_{tipo_layout}_{cv_nome}",
            )
            descricao = st.text_input(
                "Descrição / Foco (ex: Anti-3, Anti-2, Push)",
                key=f"input_desc_{tipo_layout}_{cv_nome}",
            )
            img_url = st.text_input(
                "Link Direto da Foto (ex: https://i.ibb.co/.../foto.png)",
                key=f"img_{tipo_layout}_{cv_nome}",
                help="Cole o link direto da imagem do layout.",
            )

            btn_enviar = st.form_submit_button("Publicar Layout")

            if btn_enviar:
              if link_layout.strip():
                sheet_layouts.append_row([
                    tipo_layout,
                    cv_nome,
                    st.session_state["admin_logado"],
                    link_layout.strip(),
                    (
                        descricao.strip()
                        if descricao.strip()
                        else "Layout Recomendado"
                    ),
                    img_url.strip(),
                ])
                st.success("Layout publicado no banco de dados!")
                st.rerun()
              else:
                st.error("Insira um link de layout válido.")

      # Filtrar layouts salvos da planilha
      if not df_layouts.empty:
        layouts_filtrados = df_layouts[
            (df_layouts["Tipo"] == tipo_layout) & (df_layouts["CV"] == cv_nome)
        ]
      else:
        layouts_filtrados = pd.DataFrame()

      if not layouts_filtrados.empty:
        st.markdown("### 📋 Layouts Disponíveis")
        for item_idx, row in layouts_filtrados.iterrows():
          with st.container():
            st.markdown(
                f"**👑 Admin:** {row['Autor']} | **📌 Foco:** {row['Descricao']}"
            )

            img_url_limpa = str(row["ImagemUrl"]).strip()

            if img_url_limpa:
              try:
                st.image(img_url_limpa, caption=f"Layout {cv_nome}", width=380)
              except Exception:
                st.caption("⚠️ *(Não foi possível carregar esta imagem)*")

            c_btn, c_del = st.columns([3, 1])
            with c_btn:
              st.markdown(
                  f'<a href="{row["Link"]}" target="_blank"'
                  ' class="btn-layout-copy">📲 COPIAR LAYOUT DIRETO NO CLASH</a>',
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
                    st.success("Removido com sucesso!")
                    st.rerun()

            st.divider()
      else:
        st.info(f"Nenhum layout oficial cadastrado ainda para o {cv_nome}.")


# ==============================================================================
# PÁGINA: REGRAS OFICIAIS DO CLÃ
# ==============================================================================
def renderizar_pagina_regras():
  if st.button("⬅️ Voltar ao Início"):
    st.session_state["pagina_atual"] = "principal"
    st.rerun()

  st.markdown(
      "<h1 style='text-align: center;'>📜 Regras Oficiais - Clã Winning"
      " Wars</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='text-align: center; color: #94a3b8;'>Leia com atenção para"
      " manter sua permanência no clã e garantir sua participação nos"
      " eventos e premiações.</p><br>",
      unsafe_allow_html=True,
  )

  regras = [
      "Novatos serão devidamente testados antes de serem inseridos nas Guerras.",
      (
          "Guerras: Ataque obrigatoriamente um CV do mesmo nível que o seu"
          " (NÃO se baseie na numeração de espelho)."
      ),
      "Inatividade por 3 dias sem aviso prévio resultará em remoção (kick).",
      (
          "Jogos dos Clãs: Meta mínima obrigatória de 2.000 pontos. O"
          " descumprimento causará kick."
      ),
      "Cargos e promoções (Ancião / Co-Líder) serão concedidos estritamente por mérito e engajamento.",
      (
          "Grupo do WhatsApp é OBRIGATÓRIO para participação na Liga e para"
          " disputar as premiações dos Passes Dourados."
      ),
      "Contas Rushadas com heróis em nível baixo não serão aceitas no clã.",
      (
          "Se tiver dúvidas, pergunte ou peça ajuda! Nossos membros e líderes"
          " estão aqui para nos ajudar mutually."
      ),
  ]

  for i, regra in enumerate(regras, 1):
    st.markdown(
        f"""
        <div class="rule-card">
            <div class="rule-number">{i}</div>
            <div class="rule-text">{regra}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

  st.write("---")
  c_voltar = st.columns([1, 2, 1])
  with c_voltar[1]:
    if st.button(
        "✅ Entendi as Regras e quero voltar ao Ranking", use_container_width=True
    ):
      st.session_state["pagina_atual"] = "principal"
      st.rerun()


# ==============================================================================
# SELEÇÃO DE PÁGINAS
# ==============================================================================
if st.session_state["pagina_atual"] == "layouts_guerra":
  renderizar_pagina_layouts("Guerra", "🛡️ Layouts Oficiais de Guerra")

elif st.session_state["pagina_atual"] == "layouts_rankeada":
  renderizar_pagina_layouts(
      "Rankeada", "🏆 Layouts Oficiais de Rankeada / Farm"
  )

elif st.session_state["pagina_atual"] == "regras_cla":
  renderizar_pagina_regras()

# ==============================================================================
# PÁGINA PRINCIPAL (RANKING & APLICAÇÃO)
# ==============================================================================
else:
  # LOGO OFICIAL DO CLÃ NO TOPO CENTRALIZADO
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

  tab_ranking, tab_tabela, tab_admin = st.tabs(
      ["🏆 Ranking ao Vivo", "📋 Tabela Detalhada", "🔐 Área Admin"]
  )

  # ABA 1: RANKING AO VIVO
  with tab_ranking:
    if not df.empty and "Total" in df.columns:
      if mes_finalizado:
        st.success(
            "🔒 **O MÊS FOI FINALIZADO PELO ADMIN! CONFIRA OS CAMPEÕES:**"
        )
        st.subheader("🥇 Pódio dos Premiados com Passe Dourado")

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
        st.write("---")
      else:
        st.info(
            "⏳ **Mês em andamento.** A classificação é atualizada em tempo"
            " real."
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
          height=(len(df_exibicao) + 1) * 35 + 3,
      )
    else:
      st.info("Nenhum jogador cadastrado ainda.")

  # ABA 2: TABELA DETALHADA
  with tab_tabela:
    st.subheader("📋 Pontuação Individual Detalhada por Evento")
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
    else:
      st.info("Sem registros no momento.")

  # ABA 3: ÁREA ADMINISTRAÇÃO
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
        st.success(f"Bem-vindo, {usuario_input}!")
        st.rerun()
      else:
        st.error("Usuário ou senha incorretos.")

    if "admin_logado" in st.session_state:
      st.write("---")
      st.success(f"Sessão Ativa: **{st.session_state['admin_logado']}**")

      st.markdown("### 🏁 Gestão de Encerramento do Mês")
      c_fin1, c_fin2 = st.columns(2)

      with c_fin1:
        if not mes_finalizado:
          if st.button("🔒 Finalizar Mês e Revelar Campeões", type="primary"):
            sheet_estado.update_cell(2, 2, "TRUE")
            st.success("Mês finalizado!")
            st.rerun()
        else:
          if st.button("🔓 Reabrir Mês para Edição"):
            sheet_estado.update_cell(2, 2, "FALSE")
            st.warning("Mês reaberto.")
            st.rerun()

      with c_fin2:
        st.markdown("#### 🎲 Verificação de Empate no Top 3")
        if not df.empty and "Total" in df.columns and len(df_rank) >= 3:
          p3_score = df_rank.iloc[2]["Total"]
          empatados_corte = df_rank[df_rank["Total"] == p3_score]

          if (
              len(empatados_corte) > 1
              and df_rank.iloc[0]["Total"] != df_rank.iloc[2]["Total"]
          ):
            st.warning(
                f"⚠️ **Empate detectado!** {len(empatados_corte)} jogadores"
                f" empatados com {int(p3_score)} pts."
            )
            if st.button("🎲 Realizar Sorteio de Desempate"):
              ganhadores_sorteio = random.sample(
                  empatados_corte["Nome"].tolist(), len(empatados_corte)
              )
              st.balloons()
              st.success("Resultado do Sorteio:")
              for idx_s, nome_s in enumerate(ganhadores_sorteio, 1):
                st.write(f"**{idx_s}º Sorteado:** {nome_s}")
          else:
            st.info("Não há empates críticos no momento.")

      st.write("---")
      sub_tab1, sub_tab2, sub_tab3 = st.tabs([
          "➕ Cadastrar / Remover Player",
          "✏️ Lançar Pontuações (Em Lote)",
          "👥 Gerenciar Admins",
      ])

      with sub_tab1:
        c1, c2 = st.columns(2)
        with c1:
          st.markdown("#### Adicionar Jogador")
          novo_nome = st.text_input("Nome do Player")
          if st.button("Cadastrar Player"):
            if len(df) >= 50:
              st.error("Limite máximo de 50 atingido!")
            elif novo_nome.strip() != "":
              novo_id = len(dados) + 1
              cols_atuais = len(sheet_dados.row_values(1))
              linha_nova = [novo_id, novo_nome.strip()] + [0] * (cols_atuais - 2)
              sheet_dados.append_row(linha_nova)
              st.success(f"{novo_nome} adicionado!")
              st.rerun()

        with c2:
          st.markdown("#### Remover Jogador")
          if not df.empty and "Nome" in df.columns:
            player_rem = st.selectbox(
                "Selecione para remover", df["Nome"].tolist()
            )
            if st.button("Remover Player", type="primary"):
              cell = sheet_dados.find(player_rem)
              sheet_dados.delete_rows(cell.row)
              st.success(f"{player_rem} removido!")
              st.rerun()

      # ABA 2: EDIÇÃO DE PONTUAÇÕES EM LOTE
      with sub_tab2:
        st.markdown("#### Criar Novas Rodadas / Colunas")
        col_add1, col_add2, col_add3 = st.columns(3)
        cabecalho_real = sheet_dados.row_values(1)

        with col_add1:
          if st.button("⚔️ Adicionar Guerra Normal"):
            nova_guerra_num = len(colunas_guerras) + 1
            sheet_dados.update_cell(
                1, len(cabecalho_real) + 1, f"Guerra_{nova_guerra_num}"
            )
            st.success("Coluna de Guerra Normal Criada!")
            st.rerun()

        with col_add2:
          if st.button("🏆 Adicionar Guerra de Liga (CWL)"):
            nova_liga_num = len(colunas_liga) + 1
            sheet_dados.update_cell(
                1, len(cabecalho_real) + 1, f"Liga_{nova_liga_num}"
            )
            st.success("Coluna de Guerra de Liga Criada!")
            st.rerun()

        with col_add3:
          if st.button("🛡️ Adicionar Coluna de Raide"):
            nova_raide_num = len(colunas_raides) + 1
            sheet_dados.update_cell(
                1, len(cabecalho_real) + 1, f"Raide_FDS{nova_raide_num}"
            )
            st.success("Coluna de Raide Criada!")
            st.rerun()

        st.write("---")
        st.markdown("#### 📝 Planilha de Edição Rápida (Em Lote)")
        st.info(
            "💡 **Como usar:** Altere os pontos de qualquer jogador"
            " diretamente nas células abaixo e clique em **💾 Salvar Todas as"
            " Alterações**."
        )

        if not df.empty:
          df_editavel = df.drop(columns=["Total"], errors="ignore").copy()

          df_editado = st.data_editor(
              df_editavel,
              use_container_width=True,
              hide_index=True,
              num_rows="fixed",
              disabled=["ID"],
              key="editor_pontos_lote",
          )

          if st.button(
              "💾 Salvar Todas as Alterações na Planilha", type="primary"
          ):
            try:
              df_editado = df_editado.fillna(0)
              novos_dados = [
                  df_editado.columns.values.tolist()
              ] + df_editado.values.tolist()
              sheet_dados.clear()
              sheet_dados.update(novos_dados)

              st.success("🎉 Todas as pontuações foram salvas com sucesso!")
              st.rerun()
            except Exception as e:
              st.error(
                  "Erro ao salvar na planilha. Verifique sua conexão e tente"
                  " novamente."
              )
        else:
          st.info("Nenhum jogador cadastrado na planilha ainda.")

      with sub_tab3:
        st.markdown("#### Cadastrar Administrador")
        u_novo = st.text_input("Usuário")
        s_nova = st.text_input("Senha", type="password")

        if st.button("Criar Admin"):
          if u_novo.strip() and s_nova.strip():
            if u_novo in df_admins["Usuario"].values:
              st.error("Usuário já existe!")
            else:
              sheet_admins.append_row([u_novo.strip(), gerar_hash(s_nova)])
              st.success(f"Admin {u_novo} criado!")
              st.rerun()

  # SEÇÃO EXPLICATIVA (RODAPÉ) - REGULAMENTO & PREMIAÇÃO COM ELEMENTOS OFICIAIS
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
                <li><b>Em caso de Empate:</b> Sorteio de desempate e/ou análise de engajamento pela liderança.</li>
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
