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


# --- FUNÇÃO DE SEGURANÇA ---
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

  return sheet_dados, sheet_admins, sheet_estado


try:
  sheet_dados, sheet_admins, sheet_estado = conectar_banco()
except Exception as e:
  st.error(
      "⚠️ **Erro na Conexão:** Não foi possível acessar a planilha"
      " 'WinningWars_DB'. Verifique se as permissões e as chaves em Secrets"
      " estão corretas."
  )
  st.stop()

# --- CARREGAR DADOS ---
try:
  dados = sheet_dados.get_all_records()
  df = pd.DataFrame(dados)
except Exception as e:
  st.warning(
      "⚠️ **Atenção:** A planilha 'WinningWars_DB' precisa ter os cabeçalhos das"
      " colunas na primeira linha (Linha 1)."
  )
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

# ARMAZENAMENTO DE LAYOUTS (EM SESSÃO)
if "layouts_guerra" not in st.session_state:
  st.session_state["layouts_guerra"] = {
      f"CV {i}": [] for i in range(18, 11, -1)
  }

if "layouts_rankeada" not in st.session_state:
  st.session_state["layouts_rankeada"] = {
      f"CV {i}": [] for i in range(18, 11, -1)
  }

# --- ESTILIZAÇÃO CSS CUSTOMIZADA ---
st.markdown(
    """
    <style>
    .main { background-color: #0b0e14; }
    h1, h2, h3 { color: #facc15 !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    
    .main-title {
        text-align: center;
        margin-top: 10px;
        margin-bottom: 5px;
    }
    .main-subtitle {
        text-align: center;
        color: #94a3b8;
        margin-bottom: 25px;
    }
    
    /* PÓDIO */
    .podium-card {
        padding: 22px;
        border-radius: 16px;
        text-align: center;
        margin-bottom: 25px;
        color: #ffffff;
        box-shadow: 0 8px 25px rgba(0,0,0,0.4);
    }
    .gold { background: linear-gradient(135deg, #f59e0b 0%, #b45309 100%); border: 2px solid #facc15; }
    .silver { background: linear-gradient(135deg, #94a3b8 0%, #475569 100%); border: 2px solid #cbd5e1; }
    .bronze { background: linear-gradient(135deg, #d97706 0%, #78350f 100%); border: 2px solid #f97316; }
    
    .podium-title { font-size: 1.1rem; font-weight: bold; letter-spacing: 1px; }
    .podium-name { font-size: 1.8rem; font-weight: 800; text-shadow: 2px 2px 4px rgba(0,0,0,0.6); margin: 8px 0; }
    .podium-score { font-size: 1.5rem; color: #facc15; font-weight: bold; }

    /* SEÇÃO DE REGRAS E PREMIAÇÃO NO RODAPÉ */
    .info-box {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px;
        margin-top: 10px;
        color: #e6edf3;
    }
    .info-title {
        color: #facc15;
        font-size: 1.2rem;
        font-weight: bold;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .info-list {
        list-style-type: none;
        padding-left: 0;
        margin-bottom: 0;
    }
    .info-list li {
        margin-bottom: 8px;
        font-size: 0.95rem;
        line-height: 1.4;
    }
    .highlight-gold {
        color: #facc15;
        font-weight: bold;
    }

    /* BOTÃO DE LINK EXTERNO */
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
    .btn-external-link:hover {
        background-color: #15803d;
    }
    </style>
""",
    unsafe_allow_html=True,
)

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
# PÁGINA 1: LAYOUTS DE GUERRA
# ==============================================================================
if st.session_state["pagina_atual"] == "layouts_guerra":
  if st.button("⬅️ Voltar ao Início"):
    st.session_state["pagina_atual"] = "principal"
    st.rerun()

  st.markdown(
      "<h1 style='text-align: center;'>🛡️ Layouts Oficiais de Guerra</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='text-align: center; color: #94a3b8;'>Layouts defensivos"
      " oficiais selecionados pelos administradores para guerras e liga.</p>",
      unsafe_allow_html=True,
  )

  eh_admin = "admin_logado" in st.session_state

  if not eh_admin:
    st.info(
        "💡 **Apenas a administração do clã pode publicar novos layouts.**"
        " Selecione o seu CV abaixo para copiar a base."
    )

  cv_list = [f"CV {i}" for i in range(18, 11, -1)]
  tabs_cv = st.tabs(cv_list)

  for idx, cv_nome in enumerate(cv_list):
    with tabs_cv[idx]:
      st.subheader(f"Base de Guerra - {cv_nome}")

      # Form exclusivo para Administradores com keys únicas
      if eh_admin:
        with st.expander(
            f"➕ [ADMIN] Adicionar Novo Layout de Guerra ({cv_nome})"
        ):
          with st.form(key=f"form_guerra_{cv_nome}"):
            link_layout = st.text_input(
                "Link Oficial do Layout", key=f"input_link_guerra_{cv_nome}"
            )
            descricao = st.text_input(
                "Descrição / Foco (ex: Anti-3, Anti-2)",
                key=f"input_desc_guerra_{cv_nome}",
            )
            btn_enviar = st.form_submit_button("Publicar Layout")

            if btn_enviar:
              if link_layout.strip():
                st.session_state["layouts_guerra"][cv_nome].append({
                    "autor": st.session_state["admin_logado"],
                    "link": link_layout.strip(),
                    "descricao": (
                        descricao.strip()
                        if descricao.strip()
                        else "Layout Recomendado"
                    ),
                })
                st.success("Layout publicado com sucesso!")
                st.rerun()
              else:
                st.error("Insira um link de layout válido.")

      # Lista de Layouts disponíveis
      lista_l = st.session_state["layouts_guerra"][cv_nome]

      if lista_l:
        st.markdown("### 📋 Layouts Disponíveis")
        for item_idx, item in enumerate(lista_l):
          c_a, c_b, c_c, c_d = st.columns([2, 3, 2, 1])
          with c_a:
            st.write(f"👑 Admin: **{item['autor']}**")
          with c_b:
            st.write(f"📌 {item['descricao']}")
          with c_c:
            st.markdown(f"[📥 Copiar Layout]({item['link']})")
          with c_d:
            if eh_admin:
              if st.button(
                  "❌ Excluir", key=f"del_guerra_{cv_nome}_{item_idx}"
              ):
                st.session_state["layouts_guerra"][cv_nome].pop(item_idx)
                st.success("Layout removido!")
                st.rerun()
          st.divider()
      else:
        st.info(f"Nenhum layout oficial cadastrado ainda para o {cv_nome}.")

# ==============================================================================
# PÁGINA 2: LAYOUTS DE RANKEADA
# ==============================================================================
elif st.session_state["pagina_atual"] == "layouts_rankeada":
  if st.button("⬅️ Voltar ao Início"):
    st.session_state["pagina_atual"] = "principal"
    st.rerun()

  st.markdown(
      "<h1 style='text-align: center;'>🏆 Layouts Oficiais de Rankeada /"
      " Farm</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='text-align: center; color: #94a3b8;'>Layouts oficiais"
      " recomendados para subida de troféus, Vila Lendária e proteção de"
      " recursos.</p>",
      unsafe_allow_html=True,
  )

  eh_admin = "admin_logado" in st.session_state

  if not eh_admin:
    st.info(
        "💡 **Apenas a administração do clã pode publicar novos layouts.**"
        " Selecione o seu CV abaixo para copiar a base."
    )

  cv_list = [f"CV {i}" for i in range(18, 11, -1)]
  tabs_cv = st.tabs(cv_list)

  for idx, cv_nome in enumerate(cv_list):
    with tabs_cv[idx]:
      st.subheader(f"Base de Rankeada - {cv_nome}")

      # Form exclusivo para Administradores com keys únicas
      if eh_admin:
        with st.expander(
            f"➕ [ADMIN] Adicionar Novo Layout de Rankeada ({cv_nome})"
        ):
          with st.form(key=f"form_rankeada_{cv_nome}"):
            link_layout = st.text_input(
                "Link Oficial do Layout", key=f"input_link_rankeada_{cv_nome}"
            )
            descricao = st.text_input(
                "Descrição / Foco (ex: Push Lendária, Proteção de Dark)",
                key=f"input_desc_rankeada_{cv_nome}",
            )
            btn_enviar = st.form_submit_button("Publicar Layout")

            if btn_enviar:
              if link_layout.strip():
                st.session_state["layouts_rankeada"][cv_nome].append({
                    "autor": st.session_state["admin_logado"],
                    "link": link_layout.strip(),
                    "descricao": (
                        descricao.strip()
                        if descricao.strip()
                        else "Layout Recomendado"
                    ),
                })
                st.success("Layout publicado com sucesso!")
                st.rerun()
              else:
                st.error("Insira um link de layout válido.")

      # Lista de Layouts disponíveis
      lista_l = st.session_state["layouts_rankeada"][cv_nome]

      if lista_l:
        st.markdown("### 📋 Layouts Disponíveis")
        for item_idx, item in enumerate(lista_l):
          c_a, c_b, c_c, c_d = st.columns([2, 3, 2, 1])
          with c_a:
            st.write(f"👑 Admin: **{item['autor']}**")
          with c_b:
            st.write(f"📌 {item['descricao']}")
          with c_c:
            st.markdown(f"[📥 Copiar Layout]({item['link']})")
          with c_d:
            if eh_admin:
              if st.button(
                  "❌ Excluir", key=f"del_rankeada_{cv_nome}_{item_idx}"
              ):
                st.session_state["layouts_rankeada"][cv_nome].pop(item_idx)
                st.success("Layout removido!")
                st.rerun()
          st.divider()
      else:
        st.info(f"Nenhum layout oficial cadastrado ainda para o {cv_nome}.")

# ==============================================================================
# PÁGINA PRINCIPAL (RANKING & APLICAÇÃO)
# ==============================================================================
else:
  # TÍTULO CENTRALIZADO
  st.markdown(
      "<h1 class='main-title'>⚔️ Clã Winning Wars - Competição Mensal</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p class='main-subtitle'>Acompanhe o ranking em tempo real. Ao final do"
      " mês, os Top 3 garantem o Passe Dourado!</p>",
      unsafe_allow_html=True,
  )

  # --- TRATAMENTO DOS DADOS E SOMA DAS COLUNAS DINÂMICAS ---
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

    # Adiciona ícones aos 3 primeiros da lista
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

  # --- ABA 1: RANKING AO VIVO ---
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
                f"""
                        <div class="podium-card gold">
                            <div class="podium-title">🥇 1º LUGAR</div>
                            <div class="podium-name">{df_rank.iloc[0]['Nome']}</div>
                            <div class="podium-score">{int(df_rank.iloc[0]['Total'])} pts</div>
                            <small>Garantidor do Passe Dourado</small>
                        </div>
                    """,
                unsafe_allow_html=True,
            )

        if len(df_rank) >= 2:
          with col2:
            st.markdown(
                f"""
                        <div class="podium-card silver">
                            <div class="podium-title">🥈 2º LUGAR</div>
                            <div class="podium-name">{df_rank.iloc[1]['Nome']}</div>
                            <div class="podium-score">{int(df_rank.iloc[1]['Total'])} pts</div>
                            <small>Garantidor do Passe Dourado</small>
                        </div>
                    """,
                unsafe_allow_html=True,
            )

        if len(df_rank) >= 3:
          with col3:
            st.markdown(
                f"""
                        <div class="podium-card bronze">
                            <div class="podium-title">🥉 3º LUGAR</div>
                            <div class="podium-name">{df_rank.iloc[2]['Nome']}</div>
                            <div class="podium-score">{int(df_rank.iloc[2]['Total'])} pts</div>
                            <small>Garantidor do Passe Dourado</small>
                        </div>
                    """,
                unsafe_allow_html=True,
            )
        st.write("---")
      else:
        st.info(
            "⏳ **Mês em andamento.** A classificação abaixo é atualizada em"
            " tempo real. Os campeões do pódio serão revelados ao término do"
            " mês!"
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
              "background-color: #382403; color: #facc15; font-weight: bold;",
              "background-color: #382403; color: #facc15; font-weight: bold;",
              "background-color: #382403; color: #facc15; font-weight: bold;",
          ]
        elif "🥈" in pos:
          return [
              "background-color: #1e293b; color: #cbd5e1; font-weight: bold;",
              "background-color: #1e293b; color: #cbd5e1; font-weight: bold;",
              "background-color: #1e293b; color: #cbd5e1; font-weight: bold;",
          ]
        elif "🥉" in pos:
          return [
              "background-color: #2e1805; color: #f97316; font-weight: bold;",
              "background-color: #2e1805; color: #f97316; font-weight: bold;",
              "background-color: #2e1805; color: #f97316; font-weight: bold;",
          ]
        return ["", "", ""]

      st.dataframe(
          df_exibicao.style.apply(destacar_podio, axis=1).format(
              {"Pontuação Total": "{} pts"}
          ),
          use_container_width=True,
          hide_index=True,
          height=(len(df_exibicao) + 1) * 35 + 3,
      )

    else:
      st.info("Nenhum jogador cadastrado ainda ou dados ausentes na planilha.")

  # --- ABA 2: TABELA DETALHADA ---
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

  # --- ABA 3: ÁREA ADMINISTRAÇÃO ---
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
            st.success("Mês finalizado! O pódio agora está visível no ranking.")
            st.rerun()
        else:
          if st.button("🔓 Reabrir Mês para Edição"):
            sheet_estado.update_cell(2, 2, "FALSE")
            st.warning("Mês reaberto para lançamentos.")
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
                f" estão empatados com {int(p3_score)} pts na disputa pelas"
                " vagas do Top 3."
            )

            if st.button("🎲 Realizar Sorteio de Desempate"):
              ganhadores_sorteio = random.sample(
                  empatados_corte["Nome"].tolist(), len(empatados_corte)
              )
              st.balloons()
              st.success("Resultado do Sorteio:")
              for idx, nome_s in enumerate(ganhadores_sorteio, 1):
                st.write(f"**{idx}º Sorteado:** {nome_s}")
          else:
            st.info("Não há empates críticos que exijam sorteio no momento.")

      st.write("---")

      sub_tab1, sub_tab2, sub_tab3 = st.tabs([
          "➕ Cadastrar / Remover Player",
          "✏️ Lançar Pontuações Dinâmicas",
          "👥 Gerenciar Admins",
      ])

      # 1. JOGADORES
      with sub_tab1:
        c1, c2 = st.columns(2)
        with c1:
          st.markdown("#### Adicionar Jogador (Max 50)")
          novo_nome = st.text_input("Nome do Player")
          if st.button("Cadastrar Player"):
            if len(df) >= 50:
              st.error("Limite máximo de 50 jogadores atingido!")
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

      # 2. LANÇAMENTO DINÂMICO DE GUERRAS E RAIDES
      with sub_tab2:
        st.markdown("#### Criar Novas Rodadas de Eventos")
        col_add1, col_add2 = st.columns(2)

        cabecalho_real = sheet_dados.row_values(1)

        with col_add1:
          if st.button("⚔️ Adicionar Nova Coluna de Guerra"):
            nova_guerra_num = len(colunas_guerras) + 1
            nome_col_guerra = f"Guerra_{nova_guerra_num}"
            proxima_coluna = len(cabecalho_real) + 1
            sheet_dados.update_cell(1, proxima_coluna, nome_col_guerra)
            st.success(f"Coluna **{nome_col_guerra}** criada com sucesso!")
            st.rerun()

        with col_add2:
          if st.button("🛡️ Adicionar Nova Coluna de Raide"):
            nova_raide_num = len(colunas_raides) + 1
            nome_col_raide = f"Raide_FDS{nova_raide_num}"
            proxima_coluna = len(cabecalho_real) + 1
            sheet_dados.update_cell(1, proxima_coluna, nome_col_raide)
            st.success(f"Coluna **{nome_col_raide}** criada com sucesso!")
            st.rerun()

        st.write("---")
        st.markdown("#### Lançar / Corrigir Pontos de um Jogador")

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
                format_func=lambda x: f"{x} pts",
            )
            val_eventos = st.number_input(
                "Eventos Conjuntos",
                value=int(dados_p.get("Eventos", 0)),
                step=10,
            )

          with col_lan2:
            evento_tipo = st.radio(
                "Selecione o tipo de atividade para atualizar:",
                ["Guerras", "Raides"],
            )

            if evento_tipo == "Guerras" and colunas_guerras:
              guerra_sel = st.selectbox(
                  "Selecione a Guerra/Liga", colunas_guerras
              )
              val_guerra_item = st.number_input(
                  f"Estrelas na {guerra_sel} (0 a 3 pts)",
                  value=int(dados_p.get(guerra_sel, 0)),
                  min_value=0,
                  max_value=3,
              )
            elif evento_tipo == "Raides" and colunas_raides:
              raide_sel = st.selectbox(
                  "Selecione o FDS de Raide", colunas_raides
              )
              val_raide_item = st.selectbox(
                  f"Pontos no {raide_sel}",
                  options=[0, 10],
                  index=0 if int(dados_p.get(raide_sel, 0)) == 0 else 1,
                  format_func=lambda x: (
                      f"{x} pts (6 ataques)" if x == 10 else "0 pts"
                  ),
              )

          if st.button("Salvar Registro"):
            if "JogosCla" in cabecalho_real and "Eventos" in cabecalho_real:
              col_idx_jogos = cabecalho_real.index("JogosCla") + 1
              col_idx_eventos = cabecalho_real.index("Eventos") + 1
              sheet_dados.update_cell(linha_p, col_idx_jogos, val_jogos)
              sheet_dados.update_cell(linha_p, col_idx_eventos, val_eventos)

            if (
                evento_tipo == "Guerras"
                and colunas_guerras
                and guerra_sel in cabecalho_real
            ):
              col_idx_guerra = cabecalho_real.index(guerra_sel) + 1
              sheet_dados.update_cell(linha_p, col_idx_guerra, val_guerra_item)
            elif (
                evento_tipo == "Raides"
                and colunas_raides
                and raide_sel in cabecalho_real
            ):
              col_idx_raide = cabecalho_real.index(raide_sel) + 1
              sheet_dados.update_cell(linha_p, col_idx_raide, val_raide_item)

            st.success(f"Pontuações de {player_edit} atualizadas!")
            st.rerun()

      # 3. NOVO ADMIN
      sub_tab3 = sub_tab3
      with sub_tab3:
        st.markdown("#### Cadastrar Novo Administrador")
        u_novo = st.text_input("Novo Usuário")
        s_nova = st.text_input("Nova Senha", type="password")

        if st.button("Criar Admin"):
          if u_novo.strip() and s_nova.strip():
            if u_novo in df_admins["Usuario"].values:
              st.error("Usuário já existente!")
            else:
              sheet_admins.append_row([u_novo.strip(), gerar_hash(s_nova)])
              st.success(f"Admin {u_novo} criado com sucesso!")
              st.rerun()

  # --- SEÇÃO EXPLICATIVA DE REGRAS E PREMIAÇÃO (RODAPÉ) ---
  st.write("---")
  st.markdown("## 📜 Regulamento & Sistema de Premiação")
  st.markdown(
      "A ideia é simples: **valorizar quem joga bem, participa e ajuda o clã a"
      " crescer.**"
  )

  info_col1, info_col2, info_col3 = st.columns(3)

  with info_col1:
    st.markdown(
        """
          <div class="info-box">
              <div class="info-title">🏆 Prêmio Mensal</div>
              <ul class="info-list">
                  <li>Todo mês, os <b>3 principais destaques</b> do clã levam <span class="highlight-gold">1 Passe Dourado</span> cada um!</li>
              </ul>
          </div>
      """,
        unsafe_allow_html=True,
    )

  with info_col2:
    st.markdown(
        """
          <div class="info-box">
              <div class="info-title">📊 Como Pontuar</div>
              <ul class="info-list">
                  <li>⚔️ <b>Ataques em Guerras:</b> 1 ponto por estrela (⭐)</li>
                  <li>🎯 <b>Jogos do Clã e Eventos:</b> Meta = 5 pts / Completou = 10 pts</li>
                  <li>🛡️ <b>Raides de Fim de Semana:</b> 6 ataques realizados = 10 pts</li>
              </ul>
          </div>
      """,
        unsafe_allow_html=True,
    )

  with info_col3:
    st.markdown(
        """
          <div class="info-box">
              <div class="info-title">📜 Regras Rápidas</div>
              <ul class="info-list">
                  <li>👤 Vale apenas a <b>conta principal</b>.</li>
                  <li>🚫 Nada de trapaça ou conduta antidesportiva.</li>
                  <li>📱 É obrigatório estar no <b>grupo do WhatsApp</b>.</li>
                  <li>📊 Tudo será registrado em nossa tabela mensal.</li>
                  <li>🎲 Em caso de empate, teremos premiação/sorteio para 1º, 2º e 3º lugar.</li>
              </ul>
          </div>
      """,
        unsafe_allow_html=True,
    )

  st.markdown(
      """
      <br>
      <div style="text-align: center; background-color: #1e293b; padding: 15px; border-radius: 10px; border: 1px solid #334155;">
          <span style="font-size: 1.1rem; color: #facc15; font-weight: bold;">
              🔥 Resumindo: jogue bem, participe, ajude o clã, tenha esforço para melhorar e você pode levar o prêmio!
          </span>
          <br>
          <span style="font-size: 0.95rem; color: #cbd5e1;">Bora evoluir, fortalecer o clã e buscar o topo 💪</span>
      </div>
  """,
      unsafe_allow_html=True,
  )
