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
from google.oauth2.service_account import Credentials

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Winning Wars APP", page_icon="⚔️", layout="wide"
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
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_dict = json.loads(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
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

    # Aba de Logs
    try:
        sheet_logs = spreadsheet.worksheet("Logs")
    except gspread.WorksheetNotFound:
        sheet_logs = spreadsheet.add_worksheet(
            title="Logs", rows="1000", cols="3"
        )
        sheet_logs.append_row(["DataHora", "Usuario", "Acao"])

    # Aba de Layouts
    try:
        sheet_layouts = spreadsheet.worksheet("Layouts")
    except gspread.WorksheetNotFound:
        sheet_layouts = spreadsheet.add_worksheet(
            title="Layouts", rows="500", cols="4"
        )
        sheet_layouts.append_row(["CentroVila", "Link", "Criador", "Data"])

    # Aba de Estado das Inscrições
    try:
        sheet_estado = spreadsheet.worksheet("EstadoInscricoes")
    except gspread.WorksheetNotFound:
        sheet_estado = spreadsheet.add_worksheet(
            title="EstadoInscricoes", rows="10", cols="1"
        )
        sheet_estado.append_row(["Abertas"])

    return (
        sheet_dados,
        sheet_admins,
        sheet_logs,
        sheet_layouts,
        sheet_estado,
    )


# Conecta ao banco de dados
(
    sheet_dados,
    sheet_admins,
    sheet_logs,
    sheet_layouts,
    sheet_estado,
) = conectar_banco()


# --- OTIMIZAÇÃO DE LEITURA COM CACHE ---
@st.cache_data(ttl=60)
def carregar_dados_tabela(_sheet):
    return _sheet.get_all_records()


@st.cache_data(ttl=60)
def carregar_estado_inscricoes(_sheet):
    val = _sheet.get_all_values()
    return val[0][0] if val else "Abertas"


# --- CONTROLE DE ACESSO E REGRAS ---
def verificar_login_admin(usuario, senha):
    admins = carregar_dados_tabela(sheet_admins)
    if not admins:
        # Se nao houver admins cadastrados, valida pela senha padrao do secrets
        if usuario.lower() == "admin" and senha == SENHA_ADMIN_INICIAL:
            return True
        return False

    hash_digitado = gerar_hash(senha)
    for admin in admins:
        if (
            str(admin.get("Usuario", "")).strip().lower() == usuario.lower()
            and str(admin.get("SenhaHash", "")).strip() == hash_digitado
        ):
            return True
    return False


def registrar_log(usuario: str, acao: str):
    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet_logs.append_row([data_hora, usuario, acao])


# --- INICIALIZAÇÃO DE ESTADO ---
if "admin_logado" not in st.session_state:
    st.session_state["admin_logado"] = None
if "pagina_atual" not in st.session_state:
    st.session_state["pagina_atual"] = "inicio"


# --- ESTILIZAÇÃO CSS CUSTOMIZADA ---
st.markdown(
    """
    <style>
    .main-header {
        text-align: center;
        padding: 10px;
        background: linear-gradient(135deg, #1f1c2c, #928dab);
        color: white;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .info-card {
        background-color: #f8f9fa;
        border-left: 5px solid #ff4b4b;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 15px;
        color: #333333;
    }
    .info-card-header {
        font-weight: bold;
        font-size: 1.1rem;
        margin-bottom: 8px;
    }
    .info-card-list {
        margin: 0;
        padding-left: 20px;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        font-weight: bold;
    }
    </style>
""",
    unsafe_allow_html=True,
)


# --- NAVEGAÇÃO E HEADER ---
def renderizar_header():
    st.markdown(
        """
        <div class="main-header">
            <h1>⚔️ WINNING WARS APP ⚔️</h1>
            <p>Portal Oficial do Clã - Clash of Clans</p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    cols = st.columns(6)
    with cols[0]:
        if st.button("🏠 Início"):
            st.session_state["pagina_atual"] = "inicio"
            st.rerun()
    with cols[1]:
        if st.button("📝 Inscrição"):
            st.session_state["pagina_atual"] = "inscricao"
            st.rerun()
    with cols[2]:
        if st.button("🏰 Layouts CV"):
            st.session_state["pagina_atual"] = "layouts"
            st.rerun()
    with cols[3]:
        if st.button("📖 Regras"):
            st.session_state["pagina_atual"] = "regras_cla"
            st.rerun()
    with cols[4]:
        if st.button("📊 Ranking"):
            st.session_state["pagina_atual"] = "ranking"
            st.rerun()
    with cols[5]:
        if st.session_state["admin_logado"]:
            if st.button("🔐 Painel Admin"):
                st.session_state["pagina_atual"] = "admin"
                st.rerun()
        else:
            if st.button("🔑 Login"):
                st.session_state["pagina_atual"] = "login"
                st.rerun()


renderizar_header()


# --- PÁGINA: INÍCIO ---
def renderizar_pagina_inicio():
    st.markdown("### 👋 Bem-vindo ao Winning Wars!")
    st.write(
        "Utilize o menu acima para navegar pelas seções do aplicativo. Aqui você pode se inscrever nas guerras, consultar layouts para o seu Centro de Vila e visualizar as regras oficiais do clã."
    )

    st.write("")
    st.markdown(
        """
        <div class="info-card" style="text-align: center;">
            <img src="https://i.ibb.co/YFbsJ97x/Clash-of-Clans-emblem.png" width="60" style="margin-bottom: 8px;">
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


# --- PÁGINA: INSCRIÇÃO ---
def renderizar_pagina_inscricao():
    st.markdown("### 📝 Inscrição para a Guerra / CWL")

    estado_inscricoes = carregar_estado_inscricoes(sheet_estado)

    if estado_inscricoes == "Fechadas":
        st.error("🔒 As inscrições estão temporariamente **FECHADAS** pela administração.")
        return

    st.info("Preencha o formulário abaixo com os seus dados corretos do jogo.")

    with st.form("form_inscricao"):
        nome_jogador = st.text_input("Nome da Conta Principal (In-Game):")
        tag_jogador = st.text_input("Tag do Jogador (Ex: #PC9820URL):")
        cv_nivel = st.selectbox(
            "Nível do Centro de Vila (CV):",
            [f"CV {i}" for i in range(10, 18)],
        )
        confirma_whatsapp = st.checkbox("Estou no grupo do WhatsApp oficial do clã.")

        btn_enviar = st.form_submit_button("✅ Enviar Inscrição")

    if btn_enviar:
        if not nome_jogador.strip() or not tag_jogador.strip():
            st.warning("Preencha todos os campos obrigatórios!")
            return
        if not confirma_whatsapp:
            st.warning("É obrigatório estar no grupo do WhatsApp!")
            return

        tag_limpa = tag_jogador.strip().upper()
        if not tag_limpa.startswith("#"):
            tag_limpa = "#" + tag_limpa

        data_hoje = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        sheet_dados.append_row([data_hoje, nome_jogador.strip(), tag_limpa, cv_nivel])
        st.cache_data.clear()
        st.success("🎉 Inscrição realizada com sucesso! Boa sorte nas guerras.")


# --- PÁGINA: LAYOUTS ---
def renderizar_pagina_layouts():
    st.markdown("### 🏰 Compartilhamento de Layouts")

    tab1, tab2 = st.tabs(["🔍 Buscar Layouts", "➕ Adicionar Layout"])

    with tab1:
        cv_filtro = st.selectbox(
            "Selecione o Centro de Vila:",
            [f"CV {i}" for i in range(10, 18)],
            key="filtro_cv_layout",
        )

        dados_layouts = carregar_dados_tabela(sheet_layouts)
        df_layouts = pd.DataFrame(dados_layouts)

        if not df_layouts.empty and "CentroVila" in df_layouts.columns:
            df_filtrado = df_layouts[df_layouts["CentroVila"] == cv_filtro]
            if not df_filtrado.empty:
                for idx, row in df_filtrado.iterrows():
                    with st.container():
                        st.markdown(
                            f"**Layout postado por:** {row.get('Criador', 'Anônimo')} em {row.get('Data', '-')}"
                        )
                        st.link_button("🔗 Copiar Layout", row.get("Link", "#"))
                        if st.session_state["admin_logado"]:
                            if st.button(f"🗑️ Excluir Layout #{idx}", key=f"del_lay_{idx}"):
                                try:
                                    cell = sheet_layouts.find(row["Link"])
                                    if cell:
                                        sheet_layouts.delete_rows(cell.row)
                                        registrar_log(
                                            st.session_state["admin_logado"],
                                            f"Excluiu layout de {cv_filtro}",
                                        )
                                        st.cache_data.clear()
                                        st.success("Layout removido!")
                                        st.rerun()
                                except gspread.CellNotFound:
                                    st.error("Erro: O layout não foi localizado na planilha.")
                        st.divider()
            else:
                st.info("Nenhum layout cadastrado para este nível de CV ainda.")
        else:
            st.info("Nenhum layout cadastrado.")

    with tab2:
        with st.form("form_add_layout"):
            cv_select = st.selectbox(
                "Centro de Vila:", [f"CV {i}" for i in range(10, 18)]
            )
            link_layout = st.text_input("Link do Layout (Oficial do Clash of Clans):")
            nome_criador = st.text_input("Seu Nome / Nick:")
            btn_salvar_layout = st.form_submit_button("💾 Salvar Layout")

        if btn_salvar_layout:
            if not link_layout.strip() or not nome_criador.strip():
                st.warning("Preencha o link e seu nome!")
                return
            if "clashofclans.com" not in link_layout:
                st.warning("Insira um link válido do Clash of Clans!")
                return

            data_hoje = datetime.now().strftime("%Y-%m-%d")
            sheet_layouts.append_row(
                [cv_select, link_layout.strip(), nome_criador.strip(), data_hoje]
            )
            st.cache_data.clear()
            st.success("Layout cadastrado com sucesso!")


# --- PÁGINA: REGRAS ---
def renderizar_pagina_regras():
    st.markdown("### 📖 Regras Oficiais do Clã")
    st.write(
        """
        1. **Respeito:** Mantenha um ambiente saudável no chat do jogo e no WhatsApp.
        2. **Ataques na Guerra:** É obrigatório realizar todos os ataques. Quem não atacar será advertido ou removido.
        3. **Doações:** Mantenha um equilíbrio razoável entre doações feitas e recebidas.
        4. **Vila / Layout:** Mantenha um layout de guerra atualizado e defensivo.
        5. **Inatividade:** Avise a liderança caso vá ficar ausente por alguns dias.
    """
    )


# --- PÁGINA: RANKING ---
def renderizar_pagina_ranking():
    st.markdown("### 📊 Inscrições Realizadas")
    dados = carregar_dados_tabela(sheet_dados)
    if dados:
        df = pd.DataFrame(dados)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nenhuma inscrição cadastrada até o momento.")


# --- PÁGINA: LOGIN ADMIN ---
def renderizar_pagina_login():
    st.markdown("### 🔑 Área Administrativa")
    with st.form("form_login"):
        user = st.text_input("Usuário:")
        senha = st.text_input("Senha:", type="password")
        btn_entrar = st.form_submit_button("Entrar")

    if btn_entrar:
        if verificar_login_admin(user, senha):
            st.session_state["admin_logado"] = user
            st.session_state["pagina_atual"] = "admin"
            registrar_log(user, "Fez login no sistema")
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")


# --- PÁGINA: PAINEL ADMIN ---
def renderizar_pagina_admin():
    if not st.session_state["admin_logado"]:
        st.warning("Você precisa estar logado como administrador.")
        return

    st.markdown(f"### 🔐 Painel Administrativo (`{st.session_state['admin_logado']}`)")

    if st.button("🚪 Sair (Logout)"):
        registrar_log(st.session_state["admin_logado"], "Fez logout")
        st.session_state["admin_logado"] = None
        st.session_state["pagina_atual"] = "inicio"
        st.rerun()

    tab1, tab2, tab3 = st.tabs(
        ["⚙️ Configurações de Guerra", "👥 Gerenciar Admins", "📜 Logs de Atividade"]
    )

    with tab1:
        st.markdown("#### Estado das Inscrições")
        estado_atual = carregar_estado_inscricoes(sheet_estado)

        col_st1, col_st2 = st.columns(2)
        with col_st1:
            if st.button("🟢 Abrir Inscrições"):
                sheet_estado.update("A1", [["Abertas"]])
                registrar_log(st.session_state["admin_logado"], "Abriu as inscrições")
                st.cache_data.clear()
                st.success("Inscrições ABERTAS!")
                st.rerun()
        with col_st2:
            if st.button("🔴 Fechar Inscrições"):
                sheet_estado.update("A1", [["Fechadas"]])
                registrar_log(st.session_state["admin_logado"], "Fechou as inscrições")
                st.cache_data.clear()
                st.success("Inscrições FECHADAS!")
                st.rerun()

        st.info(f"Status atual das inscrições: **{estado_atual}**")

    with tab2:
        st.markdown("#### Cadastrar Novo Administrador")
        with st.form("form_novo_admin"):
            novo_user = st.text_input("Novo Usuário Admin:")
            nova_senha = st.text_input("Nova Senha:", type="password")
            btn_add_admin = st.form_submit_button("Cadastrar Admin")

        if btn_add_admin:
            if novo_user.strip() and nova_senha.strip():
                hash_s = gerar_hash(nova_senha.strip())
                sheet_admins.append_row([novo_user.strip(), hash_s])
                registrar_log(
                    st.session_state["admin_logado"],
                    f"Cadastrou admin: {novo_user.strip()}",
                )
                st.cache_data.clear()
                st.success(f"Administrador `{novo_user}` cadastrado com sucesso!")
            else:
                st.warning("Preencha usuário e senha!")

    with tab3:
        st.markdown("#### Histórico de Atividades")
        logs = carregar_dados_tabela(sheet_logs)
        if logs:
            st.dataframe(pd.DataFrame(logs), use_container_width=True)
        else:
            st.info("Nenhum log registrado.")


# --- ROTEAMENTO DE PÁGINAS ---
p = st.session_state["pagina_atual"]

if p == "inicio":
    renderizar_pagina_inicio()
elif p == "inscricao":
    renderizar_pagina_inscricao()
elif p == "layouts":
    renderizar_pagina_layouts()
elif p == "regras_cla":
    renderizar_pagina_regras()
elif p == "ranking":
    renderizar_pagina_ranking()
elif p == "login":
    renderizar_pagina_login()
elif p == "admin":
    renderizar_pagina_admin()
