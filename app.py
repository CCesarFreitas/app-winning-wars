import json
import gspread
import pandas as pd
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURAÇÃO DA PÁGINA (ESTILO VISUAL) ---
st.set_page_config(
    page_title="Winning Wars - Competição Mensal", page_icon="⚔️", layout="wide"
)

# Estilo visual personalizado (Tema Clash de Cores)
st.markdown(
    """
    <style>
    .main { background-color: #0b0e14; }
    h1, h2, h3 { color: #facc15 !important; font-family: 'sans-serif'; }
    .stButton>button { background-color: #8b5cf6; color: white; font-weight: bold; border-radius: 8px; }
    </style>
""",
    unsafe_allow_html=True,
)


# --- CONEXÃO COM O GOOGLE SHEETS ---
@st.cache_resource
def conectar_banco():
  scope = [
      "https://spreadsheets.google.com/feeds",
      "https://www.googleapis.com/auth/drive",
  ]
  # Busca as credenciais salvas com segurança no servidor
  creds_dict = json.loads(st.secrets["gcp_service_account"])
  creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
  client = gspread.authorize(creds)
  # Nome da planilha criada no Google Drive
  sheet = client.open("WinningWars_DB").sheet1
  return sheet


try:
  sheet = conectar_banco()
except Exception as e:
  st.error(
      "Aguardando configuração das chaves de segurança (Secrets) no Streamlit."
  )
  st.stop()

# Carregar dados atuais
dados = sheet.get_all_records()
df = pd.DataFrame(dados)

# --- CABEÇALHO DO CLÃ ---
st.title("⚔️ Clã Winning Wars - Competição Mensal")
st.write("Acompanhe o ranking em tempo real e dispute o Passe Dourado!")

tab_ranking, tab_tabela, tab_admin = st.tabs(
    ["🏆 Ranking ao Vivo", "📋 Tabela Detalhada", "🔐 Área Admin"]
)

# --- ABA 1: RANKING AO VIVO (PÚBLICO) ---
with tab_ranking:
  if not df.empty:
    # Garante que os valores sejam numéricos para soma
    for col in ["JogosCla", "Raides", "Guerras", "Eventos"]:
      df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["Total"] = df["JogosCla"] + df["Raides"] + df["Guerras"] + df["Eventos"]
    df_rank = df.sort_values(by="Total", ascending=False).reset_index(
        drop=True
    )

    st.subheader("🥇 Top 3 Premiados do Mês")
    cols = st.columns(3)
    if len(df_rank) >= 1:
      cols[0].metric(
          "🥇 1º Lugar (Passe Dourado)",
          f"{int(df_rank.iloc[0]['Total'])} pts",
          df_rank.iloc[0]["Nome"],
      )
    if len(df_rank) >= 2:
      cols[1].metric(
          "🥈 2º Lugar (Passe Dourado)",
          f"{int(df_rank.iloc[1]['Total'])} pts",
          df_rank.iloc[1]["Nome"],
      )
    if len(df_rank) >= 3:
      cols[2].metric(
          "🥉 3º Lugar (Passe Dourado)",
          f"{int(df_rank.iloc[2]['Total'])} pts",
          df_rank.iloc[2]["Nome"],
      )

    st.write("---")
    st.subheader("Classificação Geral")
    st.dataframe(
        df_rank[["Nome", "Total"]], use_container_width=True, hide_index=True
    )
  else:
    st.info("Nenhum jogador cadastrado ainda.")

# --- ABA 2: TABELA DETALHADA (PÚBLICO - SOMENTE LEITURA) ---
with tab_tabela:
  st.subheader("📊 Histórico de Pontos por Categoria")
  if not df.empty:
    st.dataframe(
        df[["Nome", "JogosCla", "Raides", "Guerras", "Eventos"]],
        use_container_width=True,
        hide_index=True,
    )
  else:
    st.info("Sem registros no momento.")

# --- ABA 3: PAINEL DE ADMINISTRAÇÃO ---
with tab_admin:
  senha = st.text_input("Digite a senha de Admin para editar", type="password")

  if senha == "winning123":  # VOCÊ PODE ALTERAR ESSA SENHA AQUI
    st.success("Acesso Admin Concedido!")

    sub_tab1, sub_tab2 = st.tabs(
        ["➕ Cadastrar / Remover Player", "✏️ Lançar Pontuações"]
    )

    # 1. GERENCIAR JOGADORES
    with sub_tab1:
      c1, c2 = st.columns(2)
      with c1:
        st.markdown("### Adicionar Jogador")
        novo_nome = st.text_input("Nome do Player")
        if st.button("Cadastrar Player"):
          if novo_nome:
            novo_id = len(dados) + 1
            sheet.append_row([novo_id, novo_nome, 0, 0, 0, 0])
            st.success(f"{novo_nome} adicionado!")
            st.rerun()

      with c2:
        st.markdown("### Remover Jogador")
        if not df.empty:
          player_rem = st.selectbox(
              "Selecione para remover", df["Nome"].tolist(), key="rem_box"
          )
          if st.button("Remover Player", type="primary"):
            cell = sheet.find(player_rem)
            sheet.delete_rows(cell.row)
            st.success(f"{player_rem} removido!")
            st.rerun()

    # 2. LANÇAR E CORRIGIR PONTOS
    with sub_tab2:
      st.markdown("### Atribuir Pontos aos Eventos")
      if not df.empty:
        player_edit = st.selectbox(
            "Selecione o Player", df["Nome"].tolist(), key="edit_box"
        )

        # Localiza o jogador selecionado
        dados_player = df[df["Nome"] == player_edit].iloc[0]
        linha = (
            df[df["Nome"] == player_edit].index[0] + 2
        )  # +2 compõe o cabeçalho no Sheets

        st.info(f"Editando registros de: **{player_edit}**")

        col1, col2 = st.columns(2)

        with col1:
          # Jogos do Clã
          jogos_opcoes = {
              "Manter atual": int(dados_player["JogosCla"]),
              "0 pontos": 0,
              "5 pontos (2.000~9.000 pts)": 5,
              "10 pontos (10.000 pts)": 10,
          }
          sel_jogos = st.selectbox(
              "Jogos do Clã (Ocorre 1x no mês)", list(jogos_opcoes.keys())
          )
          val_jogos = jogos_opcoes[sel_jogos]

          # Raides (Acumulativo de fim de semana)
          val_raides = st.number_input(
              "Pontos de Raides (Acumulado do mês)",
              value=int(dados_player["Raides"]),
              step=10,
              help="Soma 10 pts para cada fim de semana em que o player fez 6 ataques.",
          )

        with col2:
          # Guerras (Acumulativo)
          val_guerras = st.number_input(
              "Pontos de Guerras (Estrelas acumuladas)",
              value=int(dados_player["Guerras"]),
              step=1,
              help="Some as estrelas obtidas nas guerras normais e de liga.",
          )

          # Eventos Conjuntos
          val_eventos = st.number_input(
              "Pontos de Eventos Conjuntos",
              value=int(dados_player["Eventos"]),
              step=10,
          )

        if st.button("Salvar / Corrigir Pontuação"):
          sheet.update_cell(linha, 3, val_jogos)
          sheet.update_cell(linha, 4, val_raides)
          sheet.update_cell(linha, 5, val_guerras)
          sheet.update_cell(linha, 6, val_eventos)
          st.success(f"Pontuações de {player_edit} salvas com sucesso!")
          st.rerun()

  elif senha != "":
    st.error("Senha incorreta!")
