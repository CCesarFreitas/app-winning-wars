import hashlib
import json
import gspread
import pandas as pd
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Winning Wars - Competição Mensal", page_icon="⚔️", layout="wide"
)

# --- FUNÇÃO DE SEGURANÇA (HASH DE SENHA) ---
def gerar_hash(senha: str) -> str:
  """Cria uma camada de proteção gerando um hash SHA-256 para as senhas."""
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

  # Abre a planilha principal
  spreadsheet = client.open("WinningWars_DB")

  # Garante/Acessa as abas necessárias
  sheet_dados = spreadsheet.sheet1  # Aba 1: Jogadores e Pontos

  try:
    sheet_admins = spreadsheet.worksheet("Admins")
  except gspread.WorksheetNotFound:
    # Cria a aba de admins caso não exista e insere o Admin Padrão
    sheet_admins = spreadsheet.add_worksheet(
        title="Admins", rows="100", cols="2"
    )
    sheet_admins.append_row(["Usuario", "SenhaHash"])
    # Usuário Padrão: admin | Senha Padrão: winning123
    sheet_admins.append_row(["admin", gerar_hash("winning123")])

  return sheet_dados, sheet_admins


try:
  sheet_dados, sheet_admins = conectar_banco()
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

# --- ESTILIZAÇÃO CUSTOMIZADA (CSS) ---
st.markdown(
    """
    <style>
    .main { background-color: #0b0e14; }
    h1, h2, h3 { color: #facc15 !important; }
    
    /* PÓDIO PERSONALIZADO */
    .podium-card {
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 20px;
        color: #ffffff;
    }
    .gold { background: linear-gradient(135deg, #f59e0b 0%, #b45309 100%); border: 2px solid #facc15; }
    .silver { background: linear-gradient(135deg, #94a3b8 0%, #475569 100%); border: 2px solid #cbd5e1; }
    .bronze { background: linear-gradient(135deg, #d97706 0%, #78350f 100%); border: 2px solid #f97316; }
    
    .podium-title { font-size: 1.2rem; font-weight: bold; margin-bottom: 5px; }
    .podium-name { font-size: 1.6rem; font-weight: bold; text-shadow: 1px 1px 2px #000; }
    .podium-score { font-size: 1.4rem; color: #facc15; font-weight: bold; }
    </style>
""",
    unsafe_allow_html=True,
)

# --- CABEÇALHO ---
st.title("⚔️ Clã Winning Wars - Competição Mensal")
st.write("Acompanhe o ranking em tempo real e dispute o Passe Dourado!")

tab_ranking, tab_tabela, tab_admin = st.tabs(
    ["🏆 Ranking ao Vivo", "📋 Tabela Detalhada", "🔐 Área Admin"]
)

# --- ABA 1: RANKING AO VIVO ---
with tab_ranking:
  if not df.empty:
    for col in ["JogosCla", "Raides", "Guerras", "Eventos"]:
      df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["Total"] = df["JogosCla"] + df["Raides"] + df["Guerras"] + df["Eventos"]

    # Ordenação do Ranking
    df_rank = df.sort_values(by="Total", ascending=False).reset_index(
        drop=True
    )

    # Adiciona a numeração da classificação (1º, 2º, 3º...)
    df_rank.index = df_rank.index + 1
    df_rank["Posição"] = [f"{i}º" for i in df_rank.index]

    st.subheader("🥇 Pódio dos Campeões")
    col1, col2, col3 = st.columns(3)

    # Cartões do Pódio Personalizado
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
    st.subheader("📊 Classificação Geral Completa")

    # Exibe a tabela numerada com a posição de todos os jogadores
    st.dataframe(
        df_rank[["Posição", "Nome", "Total"]],
        use_container_width=True,
        hide_index=True,
    )
  else:
    st.info("Nenhum jogador cadastrado ainda.")

# --- ABA 2: TABELA DETALHADA ---
with tab_tabela:
  st.subheader("📊 Histórico Completo de Pontuações")
  if not df.empty:
    df_detalhado = df.sort_values(
        by=["JogosCla", "Raides", "Guerras", "Eventos"], ascending=False
    ).reset_index(drop=True)
    df_detalhado.index = df_detalhado.index + 1
    df_detalhado["Posição"] = [f"{i}º" for i in df_detalhado.index]

    st.dataframe(
        df_detalhado[
            ["Posição", "Nome", "JogosCla", "Raides", "Guerras", "Eventos"]
        ],
        use_container_width=True,
        hide_index=True,
    )
  else:
    st.info("Sem registros no momento.")

# --- ABA 3: ÁREA ADMINISTRAÇÃO E SEGURANÇA ---
with tab_admin:
  st.subheader("🔐 Autenticação de Administrador")

  # Formulário de Login com camada de proteção por Hash
  with st.form("form_login"):
    usuario_input = st.text_input("Usuário Admin")
    senha_input = st.text_input("Senha", type="password")
    btn_login = st.form_submit_button("Acessar Painel")

  autenticado = False
  if btn_login:
    hash_input = gerar_hash(senha_input)
    # Proteção: Validação no banco de dados de Admins
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
    st.success(f"Sessão ativa: **{st.session_state['admin_logado']}**")

    sub_tab1, sub_tab2, sub_tab3 = st.tabs([
        "➕ Cadastrar / Remover Player",
        "✏️ Lançar Pontuações",
        "👥 Gerenciar Admins",
    ])

    # 1. GERENCIAR JOGADORES (LIMITE MAX: 50)
    with sub_tab1:
      c1, c2 = st.columns(2)
      with c1:
        st.markdown("### Adicionar Jogador")
        novo_nome = st.text_input("Nome do Player")
        if st.button("Cadastrar Player"):
          if len(df) >= 50:
            st.error(
                " Camada de Proteção: Limite máximo de 50 jogadores atingido!"
            )
          elif novo_nome.strip() != "":
            novo_id = len(dados) + 1
            sheet_dados.append_row([novo_id, novo_nome.strip(), 0, 0, 0, 0])
            st.success(f"{novo_nome} adicionado com sucesso!")
            st.rerun()
          else:
            st.warning("Insira um nome válido.")

      with c2:
        st.markdown("### Remover Jogador")
        if not df.empty:
          player_rem = st.selectbox(
              "Selecione para remover", df["Nome"].tolist(), key="rem_box"
          )
          if st.button("Remover Player", type="primary"):
            cell = sheet_dados.find(player_rem)
            sheet_dados.delete_rows(cell.row)
            st.success(f"{player_rem} removido do sistema!")
            st.rerun()

    # 2. LANÇAR E CORRIGIR PONTOS
    with sub_tab2:
      st.markdown("### Atualizar / Corrigir Pontuação")
      if not df.empty:
        player_edit = st.selectbox(
            "Selecione o Player", df["Nome"].tolist(), key="edit_box"
        )
        dados_player = df[df["Nome"] == player_edit].iloc[0]
        linha = df[df["Nome"] == player_edit].index[0] + 2

        col1, col2 = st.columns(2)

        with col1:
          jogos_opcoes = {
              "Manter atual": int(dados_player["JogosCla"]),
              "0 pontos": 0,
              "5 pontos (2.000~9.000 pts)": 5,
              "10 pontos (10.000 pts)": 10,
          }
          sel_jogos = st.selectbox(
              "Jogos do Clã", list(jogos_opcoes.keys())
          )
          val_jogos = jogos_opcoes[sel_jogos]

          val_raides = st.number_input(
              "Pontos de Raides",
              value=int(dados_player["Raides"]),
              step=10,
          )

        with col2:
          val_guerras = st.number_input(
              "Pontos de Guerras (Estrelas)",
              value=int(dados_player["Guerras"]),
              step=1,
          )

          val_eventos = st.number_input(
              "Pontos de Eventos Conjuntos",
              value=int(dados_player["Eventos"]),
              step=10,
          )

        if st.button("Salvar Alterações"):
          sheet_dados.update_cell(linha, 3, val_jogos)
          sheet_dados.update_cell(linha, 4, val_raides)
          sheet_dados.update_cell(linha, 5, val_guerras)
          sheet_dados.update_cell(linha, 6, val_eventos)
          st.success(f"Dados de {player_edit} atualizados com sucesso!")
          st.rerun()

    # 3. CRIAR NOVOS USUÁRIOS ADMIN
    with sub_tab3:
      st.markdown("### Criar Novo Usuário Admin")
      novo_admin_user = st.text_input("Novo Usuário Admin")
      novo_admin_pass = st.text_input("Senha do Novo Admin", type="password")

      if st.button("Criar Usuário Admin"):
        if novo_admin_user.strip() != "" and novo_admin_pass.strip() != "":
          # Proteção: Verifica se usuário já existe
          if novo_admin_user in df_admins["Usuario"].values:
            st.error("Este nome de usuário já existe!")
          else:
            senha_encriptada = gerar_hash(novo_admin_pass)
            sheet_admins.append_row([novo_admin_user.strip(), senha_encriptada])
            st.success(
                f"Administrador **{novo_admin_user}** criado com sucesso!"
            )
            st.rerun()
        else:
          st.warning("Preencha o usuário e a senha.")
