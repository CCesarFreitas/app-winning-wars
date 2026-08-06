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

  # Aba de Estado do Mês (Para controlar o encerramento)
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
      "Aguardando configuração das chaves de segurança (Secrets) no Streamlit."
  )
  st.stop()

# --- CARREGAR DADOS ---
dados = sheet_dados.get_all_records()
df = pd.DataFrame(dados)

dados_admins = sheet_admins.get_all_records()
df_admins = pd.DataFrame(dados_admins)

dados_estado = dict(sheet_estado.get_all_values())
mes_finalizado = dados_estado.get("mes_finalizado", "FALSE") == "TRUE"

# --- ESTILIZAÇÃO CSS CUSTOMIZADA (DESIGN MODERNO) ---
st.markdown(
    """
    <style>
    .main { background-color: #0b0e14; }
    h1, h2, h3 { color: #facc15 !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    
    /* CARTÕES E PÓDIO */
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

    /* TABELA DE RANKING MODERNA */
    .modern-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0 10px;
        margin-top: 15px;
    }
    .modern-table th {
        background-color: #1e293b;
        color: #facc15;
        padding: 14px 18px;
        text-align: left;
        font-size: 1rem;
        text-transform: uppercase;
        border-bottom: 2px solid #334155;
    }
    .modern-table td {
        background-color: #161e2e;
        color: #f1f5f9;
        padding: 14px 18px;
        font-size: 1.05rem;
        border-top: 1px solid #273549;
        border-bottom: 1px solid #273549;
    }
    .modern-table tr td:first-child { border-top-left-radius: 10px; border-bottom-left-radius: 10px; font-weight: bold; color: #facc15; }
    .modern-table tr td:last-child { border-top-right-radius: 10px; border-bottom-right-radius: 10px; font-weight: bold; text-align: right; }
    
    .badge-pos {
        background: #334155;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.9rem;
    }
    .badge-top1 { background: #b45309; color: #facc15; }
    .badge-top2 { background: #475569; color: #ffffff; }
    .badge-top3 { background: #78350f; color: #fdba74; }
    </style>
""",
    unsafe_allow_html=True,
)

# --- TRATAMENTO DOS DADOS E SOMA DAS COLUNAS DINÂMICAS ---
if not df.empty:
  # Identifica colunas de Raides e Guerras
  colunas_raides = [c for c in df.columns if c.startswith("Raide_")]
  colunas_guerras = [c for c in df.columns if c.startswith("Guerra_")]
  colunas_pontos = ["JogosCla", "Eventos"] + colunas_raides + colunas_guerras

  for col in colunas_pontos:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

  df["Total"] = df[colunas_pontos].sum(axis=1)
  df_rank = df.sort_values(by="Total", ascending=False).reset_index(drop=True)
  df_rank.index = df_rank.index + 1
  df_rank["Posição"] = [f"{i}º" for i in df_rank.index]

# --- CABEÇALHO ---
st.title("⚔️ Clã Winning Wars - Competição Mensal")
st.write(
    "Acompanhe o ranking em tempo real. Ao final do mês, os Top 3 garantem o"
    " Passe Dourado!"
)

tab_ranking, tab_tabela, tab_admin = st.tabs(
    ["🏆 Ranking ao Vivo", "📋 Tabela Detalhada", "🔐 Área Admin"]
)

# --- ABA 1: RANKING AO VIVO ---
with tab_ranking:
  if not df.empty:
    # EXIBIÇÃO DO PÓDIO APENAS SE O MÊS FOR FINALIZADO
    if mes_finalizado:
      st.success("🔒 **O MÊS FOI FINALIZADO PELO ADMIN! CONFIRA OS CAMPEÕES:**")
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
          "⏳ **Mês em andamento.** A classificação abaixo é atualizada em tempo"
          " real. Os campeões do pódio serão revelados ao término do mês!"
      )

st.subheader("📊 Classificação em Tempo Real")

    # TABELA COM DESIGN MODERNO EM HTML E ENVOLTÓRIO RESPONSIVO
    html_table = """
    <div style="overflow-x: auto;">
        <table class="modern-table">
            <thead>
                <tr>
                    <th>Posição</th>
                    <th>Jogador</th>
                    <th>Pontuação Total</th>
                </tr>
            </thead>
            <tbody>
    """

    for _, row in df_rank.iterrows():
      pos_str = row["Posição"]
      badge_class = (
          "badge-top1"
          if pos_str == "1º"
          else (
              "badge-top2"
              if pos_str == "2º"
              else "badge-top3" if pos_str == "3º" else "badge-pos"
          )
      )

      html_table += f"""
            <tr>
                <td><span class="{badge_class}">{pos_str}</span></td>
                <td><strong>{row['Nome']}</strong></td>
                <td>{int(row['Total'])} pts</td>
            </tr>
            """

    html_table += """
            </tbody>
        </table>
    </div>
    """

    # O PARÂMETRO unsafe_allow_html=True É O QUE INTERPRETA O HTML CORRETAMENTE
    st.markdown(html_table, unsafe_allow_html=True)

  else:
    st.info("Nenhum jogador cadastrado ainda.")

# --- ABA 2: TABELA DETALHADA ---
with tab_tabela:
  st.subheader("📋 Pontuação Individual Detalhada por Evento")
  if not df.empty:
    cols_exibicao = ["Nome", "JogosCla", "Eventos"] + colunas_raides + colunas_guerras + ["Total"]
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

    # GERENCIAMENTO DE CICLO DO MÊS, SORTEIO E FINALIZAÇÃO
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

    # SISTEMA DE DESEMPATE E SORTEIO
    with c_fin2:
      st.markdown("#### 🎲 Verificação de Empate no Top 3")
      if not df_rank.empty and len(df_rank) >= 3:
        p3_score = df_rank.iloc[2]["Total"]  # Nota do 3º colocado
        # Busca jogadores empatados na linha de corte do Top 3
        empatados_corte = df_rank[df_rank["Total"] == p3_score]

        if len(empatados_corte) > 1 and df_rank.iloc[0]["Total"] != df_rank.iloc[2]["Total"]:
          st.warning(
              f"⚠️ **Empate detectado!** {len(empatados_corte)} jogadores estão"
              f" empatados com {int(p3_score)} pts na disputa pelas vagas do"
              " Top 3."
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
            # Cria linha preenchendo zeros para as colunas existentes
            linha_nova = [novo_id, novo_nome.strip()] + [0] * (len(df.columns) - 2)
            sheet_dados.append_row(linha_nova)
            st.success(f"{novo_nome} adicionado!")
            st.rerun()

      with c2:
        st.markdown("#### Remover Jogador")
        if not df.empty:
          player_rem = st.selectbox("Selecione para remover", df["Nome"].tolist())
          if st.button("Remover Player", type="primary"):
            cell = sheet_dados.find(player_rem)
            sheet_dados.delete_rows(cell.row)
            st.success(f"{player_rem} removido!")
            st.rerun()

    # 2. LANÇAMENTO DINÂMICO DE GUERRAS E RAIDES
    with sub_tab2:
      st.markdown("#### Criar Novas Rodadas de Eventos")
      col_add1, col_add2 = st.columns(2)

      with col_add1:
        if st.button("⚔️ Adicionar Nova Coluna de Guerra"):
          nova_guerra_num = len(colunas_guerras) + 1
          nome_col_guerra = f"Guerra_{nova_guerra_num}"
          sheet_dados.update_cell(1, len(df.columns) + 1, nome_col_guerra)
          st.success(f"Coluna **{nome_col_guerra}** criada com sucesso!")
          st.rerun()

      with col_add2:
        if st.button("🛡️ Adicionar Nova Coluna de Raide"):
          nova_raide_num = len(colunas_raides) + 1
          nome_col_raide = f"Raide_FDS{nova_raide_num}"
          sheet_dados.update_cell(1, len(df.columns) + 1, nome_col_raide)
          st.success(f"Coluna **{nome_col_raide}** criada com sucesso!")
          st.rerun()

      st.write("---")
      st.markdown("#### Lançar / Corrigir Pontos de um Jogador")

      if not df.empty:
        player_edit = st.selectbox("Selecione o Player", df["Nome"].tolist())
        dados_p = df[df["Nome"] == player_edit].iloc[0]
        linha_p = df[df["Nome"] == player_edit].index[0] + 2

        col_lan1, col_lan2 = st.columns(2)

        with col_lan1:
          # Jogos do Clã
          val_jogos = st.selectbox(
              "Jogos do Clã",
              options=[0, 5, 10],
              index=[0, 5, 10].index(int(dados_p["JogosCla"])),
              format_func=lambda x: f"{x} pts",
          )
          # Eventos Conjuntos
          val_eventos = st.number_input(
              "Eventos Conjuntos", value=int(dados_p["Eventos"]), step=10
          )

        with col_lan2:
          # Seletor dinâmico para Raides e Guerras
          evento_tipo = st.radio(
              "Selecione o tipo de atividade para atualizar:",
              ["Guerras", "Raides"],
          )

          if evento_tipo == "Guerras" and colunas_guerras:
            guerra_sel = st.selectbox("Selecione a Guerra/Liga", colunas_guerras)
            val_guerra_item = st.number_input(
                f"Estrelas na {guerra_sel} (0 a 3 pts)",
                value=int(dados_p[guerra_sel]),
                min_value=0,
                max_value=3,
            )
          elif evento_tipo == "Raides" and colunas_raides:
            raide_sel = st.selectbox("Selecione o FDS de Raide", colunas_raides)
            val_raide_item = st.selectbox(
                f"Pontos no {raide_sel}",
                options=[0, 10],
                index=0 if int(dados_p[raide_sel]) == 0 else 1,
                format_func=lambda x: f"{x} pts (6 ataques)" if x == 10 else "0 pts",
            )

        if st.button("Salvar Registro"):
          # Atualiza Jogos e Eventos
          col_idx_jogos = df.columns.get_loc("JogosCla") + 1
          col_idx_eventos = df.columns.get_loc("Eventos") + 1
          sheet_dados.update_cell(linha_p, col_idx_jogos, val_jogos)
          sheet_dados.update_cell(linha_p, col_idx_eventos, val_eventos)

          # Atualiza Guerra ou Raide selecionada
          if evento_tipo == "Guerras" and colunas_guerras:
            col_idx_guerra = df.columns.get_loc(guerra_sel) + 1
            sheet_dados.update_cell(linha_p, col_idx_guerra, val_guerra_item)
          elif evento_tipo == "Raides" and colunas_raides:
            col_idx_raide = df.columns.get_loc(raide_sel) + 1
            sheet_dados.update_cell(linha_p, col_idx_raide, val_raide_item)

          st.success(f"Pontuações de {player_edit} atualizadas!")
          st.rerun()

    # 3. NOVO ADMIN
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
