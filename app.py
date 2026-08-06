import hashlib
import json
import random
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

  # Aba de Layouts (Persistência Global para todos os membros)
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
except Exception as e:
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

# --- ESTILIZAÇÃO CSS CUSTOMIZADA ---
st.markdown(
    """
    <style>
    .main { background-color: #0b0e14; }
    h1, h2, h3 { color: #facc15 !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    
    .main-title { text-align: center; margin-top: 10px; margin-bottom: 5px; }
    .main-subtitle { text-align: center; color: #94a3b8; margin-bottom: 25px; }
    
    /* PÓDIO */
    .podium-card { padding: 22px; border-radius: 16px; text-align: center; margin-bottom: 25px; color: #ffffff; box-shadow: 0 8px 25px rgba(0,0,0,0.4); }
    .gold { background: linear-gradient(135deg, #f59e0b 0%, #b45309 100%); border: 2px solid #facc15; }
    .silver { background: linear-gradient(135deg, #94a3b8 0%, #475569 100%); border: 2px solid #cbd5e1; }
    .bronze { background: linear-gradient(135deg, #d97706 0%, #78350f 100%); border: 2px solid #f97316; }

    /* BOTÃO DE LINK DO LAYOUT E CLÃ FARM */
    .btn-layout-copy {
        display: inline-block;
        width: 100%;
        max-width: 380px;
        text-align: center;
        background-color: #2563eb;
        color: white !important;
        padding: 10px 18px;
        border-radius: 8px;
        text-decoration: none;
        font-weight: bold;
        border: 1px solid #3b82f6;
    }
    .btn-layout-copy:hover { background-color: #1d4ed8; }

    .btn-external-link {
        display: block;
        width: 100%;
        text-align: center;
        background-color: #16a34a;
        color: white !important;
        padding: 8px 16px;
        border-radius: 8px;
        text-decoration: none;
        font-weight: bold;
        border: 1px solid #22c55e;
    }
    .btn-external-link:hover { background-color: #15803d; }

    /* LIMITAÇÃO DO TAMANHO DE IMAGENS */
    stImage > img {
        max-width: 380px !important;
        border-radius: 10px;
        border: 1px solid #334155;
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
btn_col1, btn_col2, btn_col3 = st.columns(3)

with btn_col1:
  if st.button("🛡️ Layouts de Guerra", use_container_width=True):
    st.session_state["pagina_atual"] = "layouts_guerra"
    st.rerun()

with btn_col2:
  if st.button("🏆 Layouts de Rankeada", use_container_width=True):
    st.session_state["pagina_atual"] = "layouts_rankeada"
    st.rerun()

with btn_col3:
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

  cv_list = [f"CV {i}" for i in range(18, 11, -1)]
  tabs_cv = st.tabs(cv_list)

  for idx, cv_nome in enumerate(cv_list):
    with tabs_cv[idx]:
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
                "URL da Imagem da Base (Link direto da foto)",
                key=f"img_{tipo_layout}_{cv_nome}",
                help=(
                    "Cole o link da imagem hospedada (ex: Imgur, Discord, etc.)"
                ),
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

            # Exibe Imagem com TAMANHO CONTROLADO (width=380)
            if str(row["ImagemUrl"]).strip():
              try:
                st.image(
                    str(row["ImagemUrl"]).strip(),
                    caption=f"Layout {cv_nome}",
                    width=380,
                )
              except Exception:
                pass

            # Botão Direto para copiar
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
                  # Remove a linha no Google Sheets (+2 devido ao cabeçalho/index 1)
                  cell = sheet_layouts.find(row["Link"])
                  if cell:
                    sheet_layouts.delete_rows(cell.row)
                    st.success("Removido com sucesso!")
                    st.rerun()

            st.divider()
      else:
        st.info(f"Nenhum layout oficial cadastrado ainda para o {cv_nome}.")


# ==============================================================================
# PÁGINAS DE LAYOUT
# ==============================================================================
if st.session_state["pagina_atual"] == "layouts_guerra":
  renderizar_pagina_layouts("Guerra", "🛡️ Layouts Oficiais de Guerra")

elif st.session_state["pagina_atual"] == "layouts_rankeada":
  renderizar_pagina_layouts(
      "Rankeada", "🏆 Layouts Oficiais de Rankeada / Farm"
  )

# ==============================================================================
# PÁGINA PRINCIPAL (RANKING & APLICAÇÃO)
# ==============================================================================
else:
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
    colunas_pontos = ["JogosCla", "Eventos"] + colunas_raides + colunas_guerras

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
                f'<div class="podium-card gold"><div'
                ' class="podium-title">🥇 1º LUGAR</div><div'
                f' class="podium-name">{df_rank.iloc[0]["Nome"]}</div><div'
                ' class="podium-score">'
                f'{int(df_rank.iloc[0]["Total"])} pts</div><small>Garantidor do'
                " Passe Dourado</small></div>",
                unsafe_allow_html=True,
            )
        if len(df_rank) >= 2:
          with col2:
            st.markdown(
                f'<div class="podium-card silver"><div'
                ' class="podium-title">🥈 2º LUGAR</div><div'
                f' class="podium-name">{df_rank.iloc[1]["Nome"]}</div><div'
                ' class="podium-score">'
                f'{int(df_rank.iloc[1]["Total"])} pts</div><small>Garantidor do'
                " Passe Dourado</small></div>",
                unsafe_allow_html=True,
            )
        if len(df_rank) >= 3:
          with col3:
            st.markdown(
                f'<div class="podium-card bronze"><div'
                ' class="podium-title">🥉 3º LUGAR</div><div'
                f' class="podium-name">{df_rank.iloc[2]["Nome"]}</div><div'
                ' class="podium-score">'
                f'{int(df_rank.iloc[2]["Total"])} pts</div><small>Garantidor do'
                " Passe Dourado</small></div>",
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
              "background-color: #382403; color: #facc15; font-weight: bold;"
          ] * 3
        elif "🥈" in pos:
          return [
              "background-color: #1e293b; color: #cbd5e1; font-weight: bold;"
          ] * 3
        elif "🥉" in pos:
          return [
              "background-color: #2e1805; color: #f97316; font-weight: bold;"
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
          + colunas_raides
          + colunas_guerras
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
          "✏️ Lançar Pontuações Dinâmicas",
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

      with sub_tab2:
        st.markdown("#### Criar Novas Rodadas")
        col_add1, col_add2 = st.columns(2)
        cabecalho_real = sheet_dados.row_values(1)

        with col_add1:
          if st.button("⚔️ Adicionar Coluna de Guerra"):
            nova_guerra_num = len(colunas_guerras) + 1
            sheet_dados.update_cell(
                1, len(cabecalho_real) + 1, f"Guerra_{nova_guerra_num}"
            )
            st.success("Coluna de Guerra Criada!")
            st.rerun()

        with col_add2:
          if st.button("🛡️ Adicionar Coluna de Raide"):
            nova_raide_num = len(colunas_raides) + 1
            sheet_dados.update_cell(
                1, len(cabecalho_real) + 1, f"Raide_FDS{nova_raide_num}"
            )
            st.success("Coluna de Raide Criada!")
            st.rerun()

        st.write("---")
        st.markdown("#### Lançar Pontos")
        if not df.empty and "Nome" in df.columns:
          player_edit = st.selectbox("Selecione o Player", df["Nome"].tolist())
          dados_p = df[df["Nome"] == player_edit].iloc[0]
          linha_p = df[df["Nome"] == player_edit].index[0] + 2

          col_lan1, col_lan2 = st.columns(2)

          with col_lan1:
            val_jogos_atual = int(dados_p.get("JogosCla", 0))
            val_jogos = st.selectbox(
                "Jogos do Clã",
                options=[0, 5, 10],
                index=(
                    [0, 5, 10].index(val_jogos_atual)
                    if val_jogos_atual in [0, 5, 10]
                    else 0
                ),
            )
            val_eventos = st.number_input(
                "Eventos", value=int(dados_p.get("Eventos", 0)), step=10
            )

          with col_lan2:
            evento_tipo = st.radio("Atividade:", ["Guerras", "Raides"])
            if evento_tipo == "Guerras" and colunas_guerras:
              guerra_sel = st.selectbox("Guerra", colunas_guerras)
              val_guerra_item = st.number_input(
                  f"Estrelas ({guerra_sel})",
                  value=int(dados_p.get(guerra_sel, 0)),
                  min_value=0,
                  max_value=3,
              )
            elif evento_tipo == "Raides" and colunas_raides:
              raide_sel = st.selectbox("Raide", colunas_raides)
              val_raide_item = st.selectbox(
                  f"Pontos ({raide_sel})",
                  options=[0, 10],
                  index=0 if int(dados_p.get(raide_sel, 0)) == 0 else 1,
              )

          if st.button("Salvar Registro"):
            if "JogosCla" in cabecalho_real and "Eventos" in cabecalho_real:
              sheet_dados.update_cell(
                  linha_p, cabecalho_real.index("JogosCla") + 1, val_jogos
              )
              sheet_dados.update_cell(
                  linha_p, cabecalho_real.index("Eventos") + 1, val_eventos
              )

            if (
                evento_tipo == "Guerras"
                and colunas_guerras
                and guerra_sel in cabecalho_real
            ):
              sheet_dados.update_cell(
                  linha_p,
                  cabecalho_real.index(guerra_sel) + 1,
                  val_guerra_item,
              )
            elif (
                evento_tipo == "Raides"
                and colunas_raides
                and raide_sel in cabecalho_real
            ):
              sheet_dados.update_cell(
                  linha_p, cabecalho_real.index(raide_sel) + 1, val_raide_item
              )

            st.success("Pontuações salvas!")
            st.rerun()

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

  # SEÇÃO EXPLICATIVA (RODAPÉ)
  st.write("---")
  st.markdown("## 📜 Regulamento & Premiação")
  info_col1, info_col2, info_col3 = st.columns(3)

  with info_col1:
    st.markdown(
        '<div class="info-box"><div class="info-title">🏆 Prêmio'
        " Mensal</div><ul class=\"info-list\"><li>Os <b>3 principais</b> levam"
        ' <span class="highlight-gold">1 Passe Dourado</span></li></ul></div>',
        unsafe_allow_html=True,
    )

  with info_col2:
    st.markdown(
        '<div class="info-box"><div class="info-title">📊 Como Pontuar</div><ul'
        ' class="info-list"><li>⚔️ <b>Guerras:</b> 1 pt por estrela</li><li>🎯'
        " <b>Jogos/Eventos:</b> 5 ou 10 pts</li><li>🛡️ <b>Raides:</b> 10"
        " pts</li></ul></div>",
        unsafe_allow_html=True,
    )

  with info_col3:
    st.markdown(
        '<div class="info-box"><div class="info-title">📜 Regras</div><ul'
        " class=\"info-list\"><li>👤 Conta principal</li><li>📱 Estar no"
        " WhatsApp</li></ul></div>",
        unsafe_allow_html=True,
    )
