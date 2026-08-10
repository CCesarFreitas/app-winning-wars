import hashlib
import json
import random
import re
import time
from datetime import datetime, timedelta
import gspread
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Winning Wars APP - v15", page_icon="⚔️", layout="wide"
)

# --- FUNÇÕES AUXILIARES E SEGURANÇA ---
def gerar_hash(senha: str) -> str:
    return hashlib.sha256(senha.encode()).hexdigest()

SENHA_ADMIN_INICIAL = st.secrets.get("admin_default_password", "winning123")

# Proteção contra Bruteforce
if "tentativas_login" not in st.session_state:
    st.session_state["tentativas_login"] = 0
if "bloqueio_login_ate" not in st.session_state:
    st.session_state["bloqueio_login_ate"] = None

# --- CONEXÃO COM O GOOGLE SHEETS (BANCO DE DADOS COMPLETO) ---
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

    # Aba Admins (com Nível de Permissão: Super Admin, Admin, Editor)
    try:
        sheet_admins = spreadsheet.worksheet("Admins")
    except gspread.WorksheetNotFound:
        sheet_admins = spreadsheet.add_worksheet(title="Admins", rows="100", cols="3")
        sheet_admins.append_row(["Usuario", "SenhaHash", "Nivel"])
        sheet_admins.append_row(["admin", gerar_hash(SENHA_ADMIN_INICIAL), "Super Admin"])

    # Aba EstadoMes
    try:
        sheet_estado = spreadsheet.worksheet("EstadoMes")
    except gspread.WorksheetNotFound:
        sheet_estado = spreadsheet.add_worksheet(title="EstadoMes", rows="10", cols="2")
        sheet_estado.append_row(["Chave", "Valor"])
        sheet_estado.append_row(["mes_finalizado", "FALSE"])
        sheet_estado.append_row(["mural_recado", "Bem-vindos ao aplicativo oficial!"])

    # Aba Layouts
    try:
        sheet_layouts = spreadsheet.worksheet("Layouts")
    except gspread.WorksheetNotFound:
        sheet_layouts = spreadsheet.add_worksheet(title="Layouts", rows="500", cols="7")
        sheet_layouts.append_row(["Tipo", "CV", "Autor", "Link", "Descricao", "ImagemUrl", "Tag"])

    # Aba Logs de Auditoria
    try:
        sheet_logs = spreadsheet.worksheet("Logs")
    except gspread.WorksheetNotFound:
        sheet_logs = spreadsheet.add_worksheet(title="Logs", rows="2000", cols="3")
        sheet_logs.append_row(["DataHora", "Admin", "Acao"])

    # Aba Galeria da Fama
    try:
        sheet_fama = spreadsheet.worksheet("GaleriaFama")
    except gspread.WorksheetNotFound:
        sheet_fama = spreadsheet.add_worksheet(title="GaleriaFama", rows="100", cols="4")
        sheet_fama.append_row(["MesAno", "Primeiro", "Segundo", "Terceiro"])

    # Aba Novidades Expandida
    try:
        sheet_novidades = spreadsheet.worksheet("Novidades")
    except gspread.WorksheetNotFound:
        sheet_novidades = spreadsheet.add_worksheet(title="Novidades", rows="300", cols="9")
        sheet_novidades.append_row([
            "ID", "DataHora", "Titulo", "Conteudo", "ImagemUrl", "Tag", "Autor", "Fixado", "Ativo"
        ])

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
    st.error("⚠️ **Erro na Conexão:** Não foi possível acessar a planilha 'WinningWars_DB'.")
    st.stop()

def registrar_log(admin: str, acao: str):
    try:
        data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        sheet_logs.append_row([data_hora, admin, acao])
    except Exception:
        pass

# --- CACHE DE DADOS (120 SEGUNDOS) ---
@st.cache_data(ttl=120)
def obter_dados_cached():
    try: return sheet_dados.get_all_records()
    except Exception: return []

@st.cache_data(ttl=120)
def obter_layouts_cached():
    try: return sheet_layouts.get_all_records()
    except Exception: return []

@st.cache_data(ttl=120)
def obter_galeria_cached():
    try: return sheet_fama.get_all_records()
    except Exception: return []

@st.cache_data(ttl=120)
def obter_novidades_cached():
    try: return sheet_novidades.get_all_records()
    except Exception: return []

dados = obter_dados_cached()
df = pd.DataFrame(dados) if dados else pd.DataFrame()

try:
    df_admins = pd.DataFrame(sheet_admins.get_all_records())
    if "Nivel" not in df_admins.columns:
        df_admins["Nivel"] = "Admin"
except Exception:
    df_admins = pd.DataFrame([["admin", gerar_hash(SENHA_ADMIN_INICIAL), "Super Admin"]], columns=["Usuario", "SenhaHash", "Nivel"])

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

# EXPIRAÇÃO DE SESSÃO AUTOMÁTICA (10. SEGURANÇA)
SESSAO_EXPIRACAO_MINUTOS = 30
if "ultimo_acesso" in st.session_state and "admin_logado" in st.session_state:
    tempo_decorrido = datetime.now() - st.session_state["ultimo_acesso"]
    if tempo_decorrido > timedelta(minutes=SESSAO_EXPIRACAO_MINUTOS):
        registrar_log(st.session_state["admin_logado"], "Sessão expirada por inatividade")
        del st.session_state["admin_logado"]
        del st.session_state["admin_nivel"]
        st.warning("⏱️ Sua sessão expirou. Faça login novamente.")
        st.rerun()

st.session_state["ultimo_acesso"] = datetime.now()

# HELPER DE PERMISSÕES (4. SISTEMA DE PERMISSÕES)
def verificar_permissao(niveis_permitidos):
    nivel_atual = st.session_state.get("admin_nivel", "Editor")
    return nivel_atual in niveis_permitidos or nivel_atual == "Super Admin"

# --- ESTILIZAÇÃO CSS CUSTOMIZADA ---
st.markdown("""
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
        text-shadow: 2px 2px 0px #000;
    }
    .main-title { text-align: center; margin-top: 8px; font-size: 2.8rem !important; }
    
    /* CARDS DO PAINEL ADMIN E MÉTRICAS */
    .kpi-card {
        background: #0f172a; border: 2px solid #334155; border-radius: 12px;
        padding: 15px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }
    .kpi-title { color: #94a3b8; font-size: 0.9rem; font-weight: 700; margin-bottom: 4px; }
    .kpi-value { font-family: 'Luckiest Guy', cursive; color: #38bdf8; font-size: 1.8rem; }
    
    .news-card {
        background: #0f172a; border: 2px solid #334155; border-top: 4px solid #38bdf8;
        border-radius: 14px; padding: 20px; margin-bottom: 20px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.4); font-family: 'Nunito', sans-serif;
    }
    .news-tag {
        display: inline-block; padding: 4px 10px; border-radius: 6px;
        font-weight: 800; font-size: 0.85rem; color: #fff; background: #2563eb; margin-bottom: 8px;
    }
    .news-tag-fixado { background: #eab308 !important; color: #000 !important; font-weight: 900; }
    .news-tag-evento { background: #ec4899 !important; }
    .news-tag-torneio { background: #8b5cf6 !important; }
    .news-tag-aviso { background: #f97316 !important; }

    .btn-external-link, .btn-youtube-link, .btn-scid {
        display: flex; align-items: center; justify-content: center; gap: 6px; width: 100%;
        text-align: center; padding: 10px 12px; border-radius: 10px; text-decoration: none;
        font-family: 'Luckiest Guy', cursive; font-size: 0.95rem; color: white !important;
    }
    .btn-external-link { background: linear-gradient(180deg, #16a34a 0%, #15803d 100%); border: 2px solid #86efac; }
    .btn-youtube-link { background: linear-gradient(180deg, #dc2626 0%, #991b1b 100%); border: 2px solid #fca5a5; }
    .btn-scid { background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%); border: 2px solid #60a5fa; }
    </style>
""", unsafe_allow_html=True)

# --- TOPO DA PÁGINA & LOGIN ---
col_nav, col_admin_top = st.columns([6, 1.5])

with col_nav:
    b1, b2, b3, b4, b5, b6, b7 = st.columns(7)
    with b1:
        if st.button("🛡️ Layouts Guerra", use_container_width=True):
            st.session_state["pagina_atual"] = "layouts_guerra"
            st.rerun()
    with b2:
        if st.button("🏆 Layouts Rankeada", use_container_width=True):
            st.session_state["pagina_atual"] = "layouts_rankeada"
            st.rerun()
    with b3:
        if st.button("📰 Novidades", use_container_width=True):
            st.session_state["pagina_atual"] = "novidades"
            st.rerun()
    with b4:
        if st.button("📜 Regras do Clã", use_container_width=True):
            st.session_state["pagina_atual"] = "regras_cla"
            st.rerun()
    with b5:
        st.markdown('<a href="https://link.clashofclans.com/pt?action=OpenClanProfile&tag=2YPL9GU8Y" target="_blank" class="btn-external-link">🏰 Clã Vastaya ↗</a>', unsafe_allow_html=True)
    with b6:
        st.markdown('<a href="https://www.youtube.com/@winningwarscoc?sub_confirmation=1" target="_blank" class="btn-youtube-link">📺 YouTube ↗</a>', unsafe_allow_html=True)
    with b7:
        st.markdown('<a href="https://link.clashofclans.com/?action=OpenSCID&p=25-1cb8481f-3a79-4681-90f9-8914acef2d63" target="_blank" class="btn-scid">Add Godoy ↗</a>', unsafe_allow_html=True)

with col_admin_top:
    if "admin_logado" in st.session_state:
        st.success(f"👤 **{st.session_state['admin_logado']}** ({st.session_state.get('admin_nivel', 'Admin')})")
        c_p, c_l = st.columns(2)
        with c_p:
            if st.button("🛡️ Painel", use_container_width=True):
                st.session_state["pagina_atual"] = "painel_admin"
                st.rerun()
        with c_l:
            if st.button("🚪 Sair", key="top_logout", use_container_width=True):
                registrar_log(st.session_state["admin_logado"], "Fez logout do sistema")
                del st.session_state["admin_logado"]
                del st.session_state["admin_nivel"]
                st.rerun()
    else:
        with st.popover("🔐 Admin", use_container_width=True):
            st.markdown("### 🔐 Acesso Restrito Admin")
            if st.session_state["bloqueio_login_ate"] and datetime.now() < st.session_state["bloqueio_login_ate"]:
                st.error("⚠️ Muitas tentativas incorretas. Login bloqueado temporariamente por 5 minutos.")
            else:
                with st.form("form_login_topo"):
                    u_top = st.text_input("Usuário Admin")
                    s_top = st.text_input("Senha", type="password")
                    btn_top_login = st.form_submit_button("Entrar", use_container_width=True)

                    if btn_top_login:
                        if not df_admins.empty:
                            val = df_admins[
                                (df_admins["Usuario"] == u_top) & 
                                (df_admins["SenhaHash"] == gerar_hash(s_top))
                            ]
                            if not val.empty:
                                st.session_state["admin_logado"] = u_top
                                st.session_state["admin_nivel"] = val.iloc[0].get("Nivel", "Admin")
                                st.session_state["tentativas_login"] = 0
                                registrar_log(u_top, "Logou no sistema com sucesso")
                                st.success("Logado com sucesso!")
                                st.rerun()
                            else:
                                st.session_state["tentativas_login"] += 1
                                if st.session_state["tentativas_login"] >= 5:
                                    st.session_state["bloqueio_login_ate"] = datetime.now() + timedelta(minutes=5)
                                    st.error("❌ 5 tentativas falhas. Bloqueado por 5 min.")
                                else:
                                    st.error(f"Usuário ou senha inválidos. Tentativa {st.session_state['tentativas_login']}/5.")

st.write("---")

# ==============================================================================
# 1. & 9. DASHBOARD E CENTRAL DE COMANDO ADMINISTRATIVA
# ==============================================================================
def renderizar_painel_admin():
    if "admin_logado" not in st.session_state:
        st.error("⛔ Acesso restrito a administradores.")
        return

    st.markdown("<h1>🛡️ CENTRAL DE COMANDO — WINNING WARS</h1>", unsafe_allow_html=True)
    st.write(f"Bem-vindo, **{st.session_state['admin_logado']}** | Nível de permissão: `{st.session_state.get('admin_nivel', 'Admin')}`")

    # MÉTICAS RESUMIDAS (KPIs)
    k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
    
    total_membros = len(df) if not df.empty else 0
    membros_ativos = len(df[df["Status"] == "Ativo"]) if not df.empty and "Status" in df.columns else total_membros
    total_novidades = len(df_novidades) if not df_novidades.empty else 0
    total_layouts = len(df_layouts) if not df_layouts.empty else 0
    lider_atual = "N/A"
    media_pontos = 0
    if not df.empty and "Pontuação Total" in df.columns:
        df_temp = df.copy()
        df_temp["Pontos_Num"] = pd.to_numeric(df_temp["Pontuação Total"], errors="coerce").fillna(0)
        if not df_temp.empty:
            df_temp_sorted = df_temp.sort_values(by="Pontos_Num", ascending=False)
            if not df_temp_sorted.empty and "Jogador" in df_temp_sorted.columns:
                lider_atual = df_temp_sorted.iloc[0]["Jogador"]
            media_pontos = round(df_temp["Pontos_Num"].mean(), 1)

    total_admins = len(df_admins) if not df_admins.empty else 1

    with k1: st.markdown(f'<div class="kpi-card"><div class="kpi-title">👥 TOTAL MEMBERS</div><div class="kpi-value">{total_membros}</div></div>', unsafe_allow_html=True)
    with k2: st.markdown(f'<div class="kpi-card"><div class="kpi-title">🟢 ATIVOS</div><div class="kpi-value">{membros_ativos}</div></div>', unsafe_allow_html=True)
    with k3: st.markdown(f'<div class="kpi-card"><div class="kpi-title">📰 NOVIDADES</div><div class="kpi-value">{total_novidades}</div></div>', unsafe_allow_html=True)
    with k4: st.markdown(f'<div class="kpi-card"><div class="kpi-title">🧱 LAYOUTS</div><div class="kpi-value">{total_layouts}</div></div>', unsafe_allow_html=True)
    with k5: st.markdown(f'<div class="kpi-card"><div class="kpi-title">🏆 LÍDER RANKING</div><div class="kpi-value" style="font-size:1.2rem;">{lider_atual}</div></div>', unsafe_allow_html=True)
    with k6: st.markdown(f'<div class="kpi-card"><div class="kpi-title">📊 MÉDIA PONTOS</div><div class="kpi-value">{media_pontos}</div></div>', unsafe_allow_html=True)
    with k7: st.markdown(f'<div class="kpi-card"><div class="kpi-title">🔐 ADMINS</div><div class="kpi-value">{total_admins}</div></div>', unsafe_allow_html=True)

    st.write("<br>", unsafe_allow_html=True)

    # ABAS DE GESTÃO DO PAINEL
    t_membros, t_novidades, t_ranking, t_auditoria, t_backup = st.tabs([
        "👥 Gerenciar Membros", "📰 Gerenciar Novidades", "📊 Ranking & Pontos", "📜 Auditoria de Logs", "💾 Backup e Segurança"
    ])

    # --------------------------------------------------------------------------
    # 6. GESTÃO DE MEMBROS (MUITO COMPLETA E IMPORTAÇÃO EM MASSA)
    # --------------------------------------------------------------------------
    with t_membros:
        if not verificar_permissao(["Admin", "Super Admin"]):
            st.warning("⚠️ Seu perfil (Editor) não possui permissão para gerenciar membros.")
        else:
            st.subheader("👥 Gestão Integrada de Membros")
            
            c_mem_a, c_mem_b = st.columns([2, 1])
            with c_mem_a:
                if not df.empty:
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("Nenhum membro cadastrado.")
            
            with c_mem_b:
                st.markdown("#### 🔄 Importar / Atualizar Vários Jogadores")
                texto_import = st.text_area("Cole os dados no formato: NOME, GUERRA, JOGOS, RAID, EVENTOS, ATIVIDADE (um por linha)", height=150, placeholder="Jogador1, 48, 10, 10, 20, 54\nJogador2, 30, 10, 5, 10, 20")
                if st.button("📥 Importar Lista em Massa"):
                    linhas = texto_import.strip().split("\n")
                    sucesso_count = 0
                    for l in linhas:
                        partes = [p.strip() for p in l.split(",")]
                        if len(partes) >= 1 and partes[0]:
                            nome = partes[0]
                            gw = partes[1] if len(partes) > 1 else "0"
                            jg = partes[2] if len(partes) > 2 else "0"
                            rd = partes[3] if len(partes) > 3 else "0"
                            ev = partes[4] if len(partes) > 4 else "0"
                            at = partes[5] if len(partes) > 5 else "0"
                            total = sum([float(x) for x in [gw, jg, rd, ev, at] if x.isdigit()])
                            sheet_dados.append_row([nome, total, gw, jg, rd, ev, at, "Ativo"])
                            sucesso_count += 1
                    
                    registrar_log(st.session_state["admin_logado"], f"Importou {sucesso_count} jogadores em massa.")
                    st.cache_data.clear()
                    st.success(f"✅ {sucesso_count} membros importados com sucesso!")
                    st.rerun()

            st.write("---")
            c_add, c_edit = st.columns(2)
            with c_add:
                with st.form("form_add_membro"):
                    st.markdown("#### ➕ Adicionar Membro Individual")
                    novo_nome = st.text_input("Nome do Player")
                    status_membro = st.selectbox("Status Initial", ["Ativo", "Inativo"])
                    if st.form_submit_button("Cadastrar Player"):
                        if novo_nome.strip():
                            sheet_dados.append_row([novo_nome.strip(), 0, 0, 0, 0, 0, 0, status_membro])
                            registrar_log(st.session_state["admin_logado"], f"Adicionou novo membro: {novo_nome.strip()}")
                            st.cache_data.clear()
                            st.success("Player cadastrado!")
                            st.rerun()

            with c_edit:
                if not df.empty and "Jogador" in df.columns:
                    st.markdown("#### ✏️ Alterar Status / Status Membro")
                    membro_sel = st.selectbox("Selecione o Player", df["Jogador"].tolist())
                    novo_status = st.selectbox("Novo Status", ["Ativo", "Inativo", "Removido"])
                    if st.button("Atualizar Status"):
                        cell = sheet_dados.find(membro_sel)
                        if cell:
                            # Assumindo coluna Status
                            sheet_dados.update_cell(cell.row, 8, novo_status)
                            registrar_log(st.session_state["admin_logado"], f"Alterou status de {membro_sel} para {novo_status}")
                            st.cache_data.clear()
                            st.success("Status atualizado!")
                            st.rerun()

    # --------------------------------------------------------------------------
    # 2. GERENCIAMENTO DE NOVIDADES (PRIORIDADE MÁXIMA & AGENDAMENTO)
    # --------------------------------------------------------------------------
    with t_novidades:
        st.subheader("✏️ Publicar & Editar Novidades")
        
        with st.expander("📢 Criar Nova Publicação", expanded=True):
            with st.form("form_pub_novidade"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    tit_nov = st.text_input("Título")
                    cont_nov = st.text_area("Conteúdo / Descrição", height=120)
                with c2:
                    tag_nov = st.selectbox("Categoria", ["📌 FIXADO", "🎉 EVENTO", "⚔️ TORNEIO", "📢 AVISO", "🚀 ATUALIZAÇÃO"])
                    img_nov = st.text_input("URL da Imagem")
                    fix_nov = st.checkbox("Fixar no topo?")
                    data_agendada = st.date_input("Data de Publicação", datetime.now())

                # Pré-visualização de imagem (2. Pré-visualização)
                if img_nov.strip():
                    st.caption("📷 Pré-visualização da Imagem:")
                    st.image(img_nov.strip(), width=250)

                if st.form_submit_button("📢 Publicar Novidade", use_container_width=True):
                    if tit_nov.strip() and cont_nov.strip():
                        novo_id = str(int(time.time()))
                        d_str = data_agendada.strftime("%d/%m/%Y") + " " + datetime.now().strftime("%H:%M")
                        sheet_novidades.append_row([
                            novo_id, d_str, tit_nov.strip(), cont_nov.strip(),
                            img_nov.strip(), tag_nov, st.session_state["admin_logado"],
                            "SIM" if fix_nov else "NÃO", "TRUE"
                        ])
                        registrar_log(st.session_state["admin_logado"], f"Criou novidade '{tit_nov.strip()}'")
                        st.cache_data.clear()
                        st.success("Publicado com sucesso!")
                        st.rerun()

        st.write("---")
        st.markdown("#### 📋 Novidades Publicadas (Edição e Exclusão)")
        if not df_novidades.empty:
            for idx, row in df_novidades.iterrows():
                with st.expander(f"{'📌 ' if row.get('Fixado') == 'SIM' else ''}{row.get('Tag', 'AVISO')} - {row.get('Titulo', 'Sem Título')}"):
                    with st.form(key=f"form_edit_nov_{idx}"):
                        e_tit = st.text_input("Título", value=row.get("Titulo", ""))
                        e_cont = st.text_area("Conteúdo", value=row.get("Conteudo", ""))
                        e_tag = st.selectbox("Tag", ["📌 FIXADO", "🎉 EVENTO", "⚔️ TORNEIO", "📢 AVISO", "🚀 ATUALIZAÇÃO"], index=0)
                        e_img = st.text_input("Imagem URL", value=row.get("ImagemUrl", ""))
                        e_fix = st.checkbox("Fixado", value=(row.get("Fixado") == "SIM"))
                        e_ativo = st.checkbox("Visível (Ativo)", value=(str(row.get("Ativo")).upper() != "FALSE"))

                        c_save, c_del = st.columns(2)
                        with c_save:
                            if st.form_submit_button("💾 Salvar Alterações"):
                                cell = sheet_novidades.find(str(row.get("ID")))
                                if cell:
                                    r = cell.row
                                    sheet_novidades.update_cell(r, 3, e_tit)
                                    sheet_novidades.update_cell(r, 4, e_cont)
                                    sheet_novidades.update_cell(r, 5, e_img)
                                    sheet_novidades.update_cell(r, 6, e_tag)
                                    sheet_novidades.update_cell(r, 8, "SIM" if e_fix else "NÃO")
                                    sheet_novidades.update_cell(r, 9, "TRUE" if e_ativo else "FALSE")
                                    registrar_log(st.session_state["admin_logado"], f"Editou novidade '{e_tit}'")
                                    st.cache_data.clear()
                                    st.success("Novidade atualizada!")
                                    st.rerun()

                    # 3. CONFIRMAÇÃO DE AÇÃO DESTRUTIVA
                    with st.popover("🗑️ Excluir esta publicação"):
                        st.warning("⚠️ **Tem certeza que deseja excluir esta publicação?**")
                        st.caption("Esta ação não poderá ser desfeita.")
                        if st.button("Excluir definitivamente", key=f"btn_confirm_del_{idx}"):
                            cell = sheet_novidades.find(str(row.get("ID")))
                            if cell:
                                sheet_novidades.delete_rows(cell.row)
                                registrar_log(st.session_state["admin_logado"], f"Excluiu novidade '{row.get('Titulo')}'")
                                st.cache_data.clear()
                                st.success("Excluído com sucesso!")
                                st.rerun()

    # --------------------------------------------------------------------------
    # 7. RANKING COM FERRAMENTAS ADMINISTRATIVAS DETALHADAS
    # --------------------------------------------------------------------------
    with t_ranking:
        if not verificar_permissao(["Admin", "Super Admin"]):
            st.warning("⚠️ Permissão insuficiente para alterar pontuações do ranking.")
        else:
            st.subheader("📊 Origem Detalhada das Pontuações & Ajuste Fino")
            if not df.empty and "Jogador" in df.columns:
                st.dataframe(df, use_container_width=True)
                
                st.markdown("#### 🛠️ Ajustar Pontuação por Categoria")
                with st.form("form_ajustar_pontos"):
                    p_sel = st.selectbox("Selecione o Jogador", df["Jogador"].tolist())
                    col_gw, col_jg, col_rd, col_ev, col_at = st.columns(5)
                    with col_gw: p_gw = st.number_input("Guerra", min_value=0, value=0)
                    with col_jg: p_jg = st.number_input("Jogos", min_value=0, value=0)
                    with col_rd: p_rd = st.number_input("Raid", min_value=0, value=0)
                    with col_ev: p_ev = st.number_input("Eventos", min_value=0, value=0)
                    with col_at: p_at = st.number_input("Atividade", min_value=0, value=0)

                    if st.form_submit_button("💾 Salvar Ajuste de Pontos"):
                        cell = sheet_dados.find(p_sel)
                        if cell:
                            r = cell.row
                            tot = p_gw + p_jg + p_rd + p_ev + p_at
                            # Atualiza colunas na planilha
                            sheet_dados.update_cell(r, 2, tot)
                            sheet_dados.update_cell(r, 3, p_gw)
                            sheet_dados.update_cell(r, 4, p_jg)
                            sheet_dados.update_cell(r, 5, p_rd)
                            sheet_dados.update_cell(r, 6, p_ev)
                            sheet_dados.update_cell(r, 7, p_at)
                            registrar_log(st.session_state["admin_logado"], f"Ajustou pontos de {p_sel} (Total: {tot})")
                            st.cache_data.clear()
                            st.success("Pontuação atualizada com transparência!")
                            st.rerun()

    # --------------------------------------------------------------------------
    # 5. AUDITORIA MUITO MAIS COMPLETA COM FILTROS E EXPORTAÇÃO
    # --------------------------------------------------------------------------
    with t_auditoria:
        st.subheader("📜 Relatório Completo de Logs e Auditoria")
        try:
            df_logs = pd.DataFrame(sheet_logs.get_all_records())
        except Exception:
            df_logs = pd.DataFrame()

        if not df_logs.empty:
            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1:
                filtro_admin = st.selectbox("Filtrar por Admin", ["Todos"] + list(df_logs["Admin"].unique()))
            with f_col2:
                busca_log = st.text_input("🔍 Buscar na Ação")
            with f_col3:
                st.write("")

            df_logs_filtrado = df_logs.copy()
            if filtro_admin != "Todos":
                df_logs_filtrado = df_logs_filtrado[df_logs_filtrado["Admin"] == filtro_admin]
            if busca_log.strip():
                df_logs_filtrado = df_logs_filtrado[df_logs_filtrado["Acao"].str.contains(busca_log, case=False, na=False)]

            st.dataframe(df_logs_filtrado.iloc[::-1], use_container_width=True)

            # Exportação de Logs (5. Exportação)
            csv_logs = df_logs_filtrado.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Exportar Logs em CSV", data=csv_logs, file_name="auditoria_winning_wars.csv", mime="text/csv")
        else:
            st.info("Nenhum log gravado até o momento.")

    # --------------------------------------------------------------------------
    # 8. BACKUP, RESTAURAÇÃO E SEGURANÇA
    # --------------------------------------------------------------------------
    with t_backup:
        if not verificar_permissao(["Super Admin"]):
            st.warning("⚠️ Somente Super Admins podem gerenciar backups e restaurar o sistema.")
        else:
            st.subheader("📦 Backup e Restauração da Base de Dados")
            
            c_bkp1, c_bkp2 = st.columns(2)
            with c_bkp1:
                st.markdown("#### 📥 Backup Manual / Exportar CSV Completo")
                if not df.empty:
                    csv_dados = df.to_csv(index=False).encode('utf-8')
                    st.download_button("📦 Baixar Backup Completo dos Players (CSV)", data=csv_dados, file_name="backup_players.csv", mime="text/csv")

            with c_bkp2:
                st.markdown("#### 🔄 Restaurar Backup de Arquivo")
                up_file = st.file_uploader("Selecione arquivo CSV de Backup", type=["csv"])
                if up_file is not None:
                    with st.popover("⚠️ Confirmar Restauração"):
                        st.error("Deseja SOBRESCREVER o banco de dados atual?")
                        if st.button("Sim, Restaurar Backup"):
                            df_rest = pd.read_csv(up_file)
                            sheet_dados.clear()
                            sheet_dados.append_row(df_rest.columns.tolist())
                            for row in df_rest.values.tolist():
                                sheet_dados.append_row(row)
                            registrar_log(st.session_state["admin_logado"], "RESTAUROU O BANCO DE DADOS A PARTIR DE BACKUP")
                            st.cache_data.clear()
                            st.success("Banco de dados restaurado com sucesso!")
                            st.rerun()

# ==============================================================================
# ROUTER DE NAVEGAÇÃO ENTRE PÁGINAS DO APP
# ==============================================================================
if st.session_state["pagina_atual"] == "painel_admin":
    renderizar_painel_admin()
elif st.session_state["pagina_atual"] == "novidades":
    # 2. PÁGINA PÚBLICA DE NOVIDADES COM BUSCA E TAGS VISUAIS
    st.markdown("<h1 style='text-align: center;'>📰 Novidades, Torneios & Comunicados</h1>", unsafe_allow_html=True)
    
    # Busca por Título/Conteúdo
    busca_noticia = st.text_input("🔍 Buscar Notícias...", placeholder="Digite um termo para pesquisar...")
    
    if not df_novidades.empty:
        df_exib_nov = df_novidades.copy()
        if "Ativo" in df_exib_nov.columns:
            df_exib_nov = df_exib_nov[df_exib_nov["Ativo"].astype(str).str.upper() != "FALSE"]
            
        if busca_noticia.strip():
            df_exib_nov = df_exib_nov[
                df_exib_nov["Titulo"].str.contains(busca_noticia, case=False, na=False) |
                df_exib_nov["Conteudo"].str.contains(busca_noticia, case=False, na=False)
            ]
            
        # Ordenação: Fixados no topo
        if "Fixado" in df_exib_nov.columns:
            df_exib_nov["Ordem"] = df_exib_nov["Fixado"].apply(lambda x: 0 if str(x) == "SIM" else 1)
            df_exib_nov = df_exib_nov.sort_values(by="Ordem")

        for _, item in df_exib_nov.iterrows():
            tag_nome = str(item.get("Tag", "📢 AVISO")).strip()
            titulo = str(item.get("Titulo", "")).strip()
            conteudo = str(item.get("Conteudo", "")).strip()
            img_url = str(item.get("ImagemUrl", "")).strip()
            data_hora = str(item.get("DataHora", "")).strip()
            autor = str(item.get("Autor", "Liderança")).strip()
            
            classe_tag = "news-tag"
            if "FIXADO" in tag_nome.upper(): classe_tag += " news-tag-fixado"
            elif "EVENTO" in tag_nome.upper(): classe_tag += " news-tag-evento"
            elif "TORNEIO" in tag_nome.upper(): classe_tag += " news-tag-torneio"
            elif "AVISO" in tag_nome.upper(): classe_tag += " news-tag-aviso"

            st.markdown(f"""
                <div class="news-card">
                    <span class="{classe_tag}">{tag_nome}</span>
                    <div class="news-title">{titulo}</div>
                    <div class="news-meta">🕒 Publicado em {data_hora} por <b>{autor}</b></div>
                    <div style="color: #e2e8f0; font-size: 1.05rem; line-height: 1.6; white-space: pre-wrap;">{conteudo}</div>
                </div>
            """, unsafe_allow_html=True)
            if img_url:
                st.image(img_url, use_container_width=True)
    else:
        st.info("Nenhuma novidade publicada no momento.")

elif st.session_state["pagina_atual"] == "regras_cla":
    st.markdown("<h1>📜 Regras Oficiais do Clã</h1>", unsafe_allow_html=True)
    st.write("Exibição completa dos regulamentos do clã e critérios do Passe Dourado.")

else:
    # PÁGINA PRINCIPAL / RANKING PÚBLICO
    st.markdown("<h1 class='main-title'>⚔️ WINNING WARS APP ⚔️</h1>", unsafe_allow_html=True)
    st.markdown("<div class='main-subtitle'>Painel Oficial do Clã Vastaya — Rankings, Estratégias e Bilhete Dourado!</div>", unsafe_allow_html=True)
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
