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
        sheet_admins.append_row(["admin", gerar_hash(SENHA_ADMIN_INICIAL)])

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

    # Aba de Novidades e Notícias
    try:
        sheet_novidades = spreadsheet.worksheet("Novidades")
    except gspread.WorksheetNotFound:
        sheet_novidades = spreadsheet.add_worksheet(
            title="Novidades", rows="200", cols="6"
        )
        sheet_novidades.append_row(
            ["DataHora", "Titulo", "Conteudo", "ImagemUrl", "Tag", "Autor"]
        )

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


@st.cache_data(ttl=120)
def obter_novidades_cached():
    try:
        return sheet_novidades.get_all_records()
    except Exception:
        return []


dados = obter_dados_cached()
df = pd.DataFrame(dados) if dados else pd.DataFrame()

try:
    dados_admins = sheet_admins.get_all_records()
    df_admins = pd.DataFrame(dados_admins)
except Exception:
    df_admins = pd.DataFrame(
        [["admin", gerar_hash(SENHA_ADMIN_INICIAL)]], columns=["Usuario", "SenhaHash"]
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
df_novidades = pd.DataFrame(obter_novidades_cached())


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


# --- FUNÇÃO PARA GERAR A TABELA COMPLETA EM HTML E DOWNLOAD EM HD COM DESTAQUE NO TOP 3 ---
def gerar_tabela_bilhete_dourado(df_exib):
    """Gera o HTML do ranking com destaque de cores e medalhas para o Top 3."""
    from html import escape

    linhas_html = []
    for idx, row in df_exib.iterrows():
        posicao = escape(str(row.get("Posição", "")))
        jogador = escape(str(row.get("Jogador", "")))
        try:
            pontuacao = int(float(row.get("Pontuação Total", 0)))
        except (TypeError, ValueError):
            pontuacao = 0

        # Aplicação de estilo e medalhas para o Top 3
        classe_top = ""
        prefixo_medalha = ""
        if idx == 1:
            classe_top = "top1-row"
            prefixo_medalha = "🥇 "
        elif idx == 2:
            classe_top = "top2-row"
            prefixo_medalha = "🥈 "
        elif idx == 3:
            classe_top = "top3-row"
            prefixo_medalha = "🥉 "

        linhas_html.append(
            f'<tr class="{classe_top}">'
            f'<td class="tabela-posicao">{posicao}</td>'
            f'<td class="tabela-nome">{prefixo_medalha}{jogador}</td>'
            f'<td class="tabela-pontos">{pontuacao}</td></tr>'
        )

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
      <style>
        @import url('https://fonts.googleapis.com/css2?family=Luckiest+Guy&family=Nunito:wght@600;800;900&display=swap');

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
          font-size: 2.2rem !important;
          letter-spacing: 1px;
          text-shadow: 2px 2px 0px #000, -1px -1px 0px #000, 1px -1px 0px #000, -1px 1px 0px #000;
          margin: 0 0 10px 0 !important;
        }}

        .btn-download-img {{
          background: linear-gradient(180deg, #3b82f6 0%, #1d4ed8 100%);
          color: #ffffff !important;
          font-family: 'Luckiest Guy', cursive;
          font-size: 1.05rem;
          padding: 10px 20px;
          border: 2px solid #93c5fd;
          border-radius: 10px;
          box-shadow: 0px 4px 0px #1e3a8a;
          cursor: pointer;
          transition: all 0.2s ease;
          text-shadow: 1px 1px 0px #000;
          display: inline-flex;
          align-items: center;
          gap: 8px;
          margin-top: 5px;
        }}

        .btn-download-img:hover {{
          transform: translateY(-2px);
          box-shadow: 0px 6px 0px #1e3a8a;
          background: linear-gradient(180deg, #60a5fa 0%, #2563eb 100%);
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
          font-size: 1.2rem; 
          padding: 12px; 
          border-bottom: 2px solid #334155;
        }}

        .tabela-bilhete td {{
          border-bottom: 1px solid #334155; 
          padding: 12px 10px; 
          font-size: 1.05rem;
          font-weight: 800; 
          color: #e2e8f0;
        }}

        .tabela-bilhete tr:nth-child(even) {{ 
          background-color: #111827; 
        }}

        /* ESTILOS ESPECIAIS PARA O TOP 3 */
        .top1-row {{
          background: linear-gradient(90deg, rgba(250, 204, 21, 0.28) 0%, rgba(202, 138, 4, 0.15) 100%) !important;
          border-left: 4px solid #facc15;
        }}
        .top1-row .tabela-nome, .top1-row .tabela-posicao {{
          color: #fef08a !important;
          font-weight: 900 !important;
        }}
        .top2-row {{
          background: linear-gradient(90deg, rgba(203, 213, 225, 0.22) 0%, rgba(100, 116, 139, 0.12) 100%) !important;
          border-left: 4px solid #cbd5e1;
        }}
        .top2-row .tabela-nome, .top2-row .tabela-posicao {{
          color: #f1f5f9 !important;
          font-weight: 900 !important;
        }}
        .top3-row {{
          background: linear-gradient(90deg, rgba(249, 115, 22, 0.22) 0%, rgba(194, 65, 12, 0.12) 100%) !important;
          border-left: 4px solid #f97316;
        }}
        .top3-row .tabela-nome, .top3-row .tabela-posicao {{
          color: #ffedd5 !important;
          font-weight: 900 !important;
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
          width: 100px; 
          filter: drop-shadow(0px 4px 8px rgba(0,0,0,0.5));
        }}

        @media (max-width: 768px) {{
          .bilhete-dourado-container {{ padding: 14px; }}
          .bilhete-dourado-title {{ font-size: 1.8rem !important; }}
          .tabela-bilhete th, .tabela-bilhete td {{ padding: 9px 7px; font-size: 1rem; }}
        }}
      </style>
    </head>
    <body>
      <div style="text-align: center; margin-bottom: 12px;">
        <button class="btn-download-img" id="btn-download-card" onclick="baixarTabelaHD()">
          📸 Baixar Imagem do Ranking (HD)
        </button>
      </div>

      <div class="bilhete-dourado-container" id="card-bilhete-dourado">
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
          <img src="https://i.ibb.co/YFbsJ97x/Clash-of-Clans-emblem.png" alt="Emblema Clash of Clans" crossorigin="anonymous">
        </div>
      </div>

      <script>
        function baixarTabelaHD() {{
          const element = document.getElementById('card-bilhete-dourado');
          const btn = document.getElementById('btn-download-card');
          btn.innerText = "⏳ Gerando imagem em HD...";
          btn.disabled = true;

          html2canvas(element, {{
            scale: 3,
            useCORS: true,
            backgroundColor: null,
            logging: false
          }}).then(canvas => {{
            const link = document.createElement('a');
            link.download = 'ranking_bilhete_dourado.png';
            link.href = canvas.toDataURL('image/png', 1.0);
            link.click();
            
            btn.innerText = "📸 Baixar Imagem do Ranking (HD)";
            btn.disabled = false;
          }}).catch(err => {{
            console.error("Erro ao gerar imagem:", err);
            alert("Não foi possível gerar a imagem.");
            btn.innerText = "📸 Baixar Imagem do Ranking (HD)";
            btn.disabled = false;
          }});
        }}
      </script>
    </body>
    </html>
    """


# --- ESTILIZAÇÃO CSS CUSTOMIZADA COM ANIMAÇÃO E FONTES MAIORES ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Luckiest+Guy&family=Nunito:wght@600;800;900&display=swap');

    /* ANIMAÇÃO DE TRANSIÇÃO SUAVE ENTRE PÁGINAS */
    @keyframes fadeInPage {
        from {
            opacity: 0;
            transform: translateY(12px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .main .block-container {
        animation: fadeInPage 0.45s ease-in-out;
    }

    .main { 
        background: radial-gradient(circle, #1e293b 0%, #0b0e14 100%); 
        font-size: 1.05rem;
    }

    h1, h2, h3 { 
        font-family: 'Luckiest Guy', cursive !important; 
        color: #facc15 !important; 
        letter-spacing: 1px;
        text-shadow: 2px 2px 0px #000, -1px -1px 0px #000, 1px -1px 0px #000, -1px 1px 0px #000;
        word-break: break-word;
    }
    
    .main-title { 
        text-align: center; 
        margin-top: 8px; 
        margin-bottom: 8px; 
        font-size: 2.8rem !important; 
        line-height: 1.2;
    }

    .main-subtitle { 
        text-align: center; 
        color: #cbd5e1; 
        font-family: 'Nunito', sans-serif; 
        font-weight: 700; 
        margin-bottom: 25px; 
        font-size: 1.15rem !important;
        padding: 0 10px;
    }
    
    /* BOTÕES GERAIS */
    div.stButton > button {
        background: linear-gradient(180deg, #22c55e 0%, #15803d 100%) !important;
        color: #ffffff !important;
        font-family: 'Luckiest Guy', cursive, sans-serif !important;
        font-size: 1.05rem !important;
        border: 2px solid #86efac !important;
        border-radius: 12px !important;
        box-shadow: 0px 4px 0px #14532d !important;
        transition: all 0.2s ease;
        text-shadow: 1px 1px 0px #000;
        white-space: normal !important;
        height: auto !important;
        padding: 10px 14px !important;
    }

    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0px 6px 0px #14532d !important;
        background: linear-gradient(180deg, #4ade80 0%, #16a34a 100%) !important;
    }

    /* ABAS */
    button[data-baseweb="tab"] {
        font-size: 1.35rem !important;
        font-weight: 800 !important;
        font-family: 'Nunito', sans-serif !important;
        padding: 14px 24px !important;
        background-color: #1e293b !important;
        border: 2px solid #334155 !important;
        border-radius: 12px 12px 0 0 !important;
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
        box-shadow: 0px 4px 14px rgba(250, 204, 21, 0.35) !important;
    }

    button[data-baseweb="tab"]:hover {
        border-color: #facc15 !important;
        color: #facc15 !important;
    }

    /* PODIUM E CARDS */
    .podium-card { 
        padding: 18px; 
        border-radius: 16px; 
        text-align: center; 
        margin-bottom: 15px; 
        color: #ffffff; 
        box-shadow: 0 8px 25px rgba(0,0,0,0.6); 
        font-family: 'Nunito', sans-serif; 
    }
    .podium-title { font-family: 'Luckiest Guy', cursive; font-size: 1.35rem; margin-top: 6px; margin-bottom: 6px; text-shadow: 1px 1px 0px #000; }
    .podium-name { font-size: 1.2rem; font-weight: 800; word-break: break-word; }
    .podium-score { font-size: 1.1rem; margin-top: 4px; }
    .gold { background: linear-gradient(135deg, #f59e0b 0%, #78350f 100%); border: 3px solid #facc15; }
    .silver { background: linear-gradient(135deg, #64748b 0%, #1e293b 100%); border: 3px solid #cbd5e1; }
    .bronze { background: linear-gradient(135deg, #d97706 0%, #451a03 100%); border: 3px solid #f97316; }

    .btn-layout-copy {
        display: inline-block; width: 100%; max-width: 100%; text-align: center;
        background: linear-gradient(180deg, #3b82f6 0%, #1d4ed8 100%); color: white !important;
        padding: 12px 16px; border-radius: 10px; text-decoration: none; font-family: 'Luckiest Guy', cursive;
        border: 2px solid #93c5fd; box-shadow: 0px 4px 0px #1e3a8a; font-size: 1.1rem;
    }
    .btn-external-link {
        display: flex; align-items: center; justify-content: center; gap: 6px; width: 100%; text-align: center;
        background: linear-gradient(180deg, #16a34a 0%, #15803d 100%); color: white !important;
        padding: 10px 12px; border-radius: 10px; text-decoration: none; font-family: 'Luckiest Guy', cursive;
        border: 2px solid #86efac; box-shadow: 0px 4px 0px #14532d; font-size: 0.95rem;
    }
    .btn-youtube-link {
        display: flex; align-items: center; justify-content: center; gap: 6px; width: 100%; text-align: center;
        background: linear-gradient(180deg, #dc2626 0%, #991b1b 100%); color: white !important;
        padding: 10px 12px; border-radius: 10px; text-decoration: none; font-family: 'Luckiest Guy', cursive;
        border: 2px solid #fca5a5; box-shadow: 0px 4px 0px #7f1d1d; font-size: 0.95rem;
    }
    .btn-scid {
        display: flex; align-items: center; justify-content: center; gap: 6px; width: 100%; text-align: center;
        background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%); color: white !important;
        padding: 10px 12px; border-radius: 10px; text-decoration: none; font-family: 'Luckiest Guy', cursive;
        border: 2px solid #60a5fa; box-shadow: 0px 4px 0px #1e3a8a; font-size: 0.95rem;
    }

    .mural-banner {
        background: #1e293b; border-radius: 14px; padding: 14px 18px; margin-bottom: 22px;
        border: 2px solid #334155; border-left: 6px solid #facc15;
        box-shadow: 0 4px 14px rgba(0,0,0,0.3); font-family: 'Nunito', sans-serif;
    }
    .mural-header { font-family: 'Luckiest Guy', cursive; color: #facc15; font-size: 1.15rem; margin-bottom: 4px; }

    .news-card {
        background: #0f172a; border: 2px solid #334155; border-top: 4px solid #38bdf8;
        border-radius: 14px; padding: 20px; margin-bottom: 20px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.4); font-family: 'Nunito', sans-serif;
    }
    .news-tag {
        display: inline-block; padding: 4px 10px; border-radius: 6px;
        font-weight: 800; font-size: 0.85rem; color: #fff; background: #2563eb; margin-bottom: 8px;
    }
    .news-title { font-family: 'Luckiest Guy', cursive; color: #facc15; font-size: 1.5rem; margin-bottom: 6px; }
    .news-meta { color: #94a3b8; font-size: 0.85rem; margin-bottom: 12px; }

    .info-card {
        background: #0f172a; border: 2px solid #334155; border-radius: 14px; padding: 22px; margin-bottom: 15px;
        font-family: 'Nunito', sans-serif; color: #e2e8f0; box-shadow: 0 6px 18px rgba(0,0,0,0.4); height: 100%;
    }
    .info-card-header { font-family: 'Luckiest Guy', cursive; color: #facc15; font-size: 1.25rem; margin-bottom: 10px; }
    .info-card-list { padding-left: 18px; margin-bottom: 0px; }
    .info-card-list li { margin-bottom: 8px; line-height: 1.5; font-size: 1.05rem; }

    .rules-card {
        background: #0f172a; border: 2px solid #334155; border-radius: 14px; padding: 25px; margin-top: 35px;
        font-family: 'Nunito', sans-serif; color: #e2e8f0; box-shadow: 0 6px 18px rgba(0,0,0,0.4);
    }
    .rules-title { font-family: 'Luckiest Guy', cursive; color: #facc15; font-size: 1.45rem; margin-bottom: 14px; }
    .rules-card ul { margin-bottom: 0px; padding-left: 20px; }
    .rules-card li { margin-bottom: 12px; line-height: 1.55; font-size: 1.05rem; }

    @media (max-width: 768px) {
        .main-title { font-size: 2rem !important; }
        .main-subtitle { font-size: 0.95rem !important; }
        .mural-banner { padding: 12px !important; }
        .podium-card { padding: 14px !important; }
        button[data-baseweb="tab"] { font-size: 1.05rem !important; padding: 10px 12px !important; }
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- TOPO DA PÁGINA: MENU DE NAVEGAÇÃO ENXUTO + LOGIN ADMIN ---
col_nav, col_admin_top = st.columns([6, 1])

with col_nav:
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("🛡️ Layouts Guerra", use_container_width=True):
            st.session_state["pagina_atual"] = "layouts_guerra"
            st.rerun()
    with b2:
        if st.button("🏆 Layouts Rankeada", use_container_width=True):
            st.session_state["pagina_atual"] = "layouts_rankeada"
            st.rerun()
    with b3:
        st.markdown(
            '<a'
            ' href="https://link.clashofclans.com/pt?action=OpenClanProfile&tag=2YPL9GU8Y"'
            ' target="_blank" class="btn-external-link">🏰 Clã Vastaya ↗</a>',
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
                    <img src="{th_img_url}" width="90" style="filter: drop-shadow(0px 4px 8px rgba(0,0,0,0.5));">
                    <h2 style="margin: 0; font-size: 2rem;">Bases de {tipo_layout} - {cv_nome}</h2>
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
                                if eh_admin:
                                    st.markdown(
                                        f'<div style="text-align: center; margin-bottom: 10px;"><a href="{img_url_limpa}" target="_blank" download style="color: #38bdf8; text-decoration: underline; font-weight: bold; font-size: 0.95rem;">📥 Baixar Imagem (Admin)</a></div>',
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
def renderizar_pagina_regras():
    if st.button("⬅️ Voltar ao Início"):
        st.session_state["pagina_atual"] = "principal"
        st.rerun()

    st.markdown(
        "<h1 style='text-align: center;'>📜 Regras Oficiais do Clã Vastaya</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center; color: #cbd5e1;'>Leia atentamente as diretrizes para garantir a convivência respeitosa e a evolução de todos no clã.</p><br>",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="rules-card">
            <h3 class="rules-title">🛡️ Normas de Convivência e Participação</h3>
            <ul>
                <li><b>Respeito e Companheirismo:</b> Trate todos os membros com educação. Discussões tóxicas e ofensas não serão toleradas.</li>
                <li><b>Ataques Obrigatórios em Guerra:</b> Se você marcou o escudo como verde, é obrigatório realizar todos os seus ataques.</li>
                <li><b>Jogos do Clã:</b> É exigida a pontuação mínima estabelecida pela liderança a cada mês para fortalecimento coletivo.</li>
                <li><b>Fim de Semana de Raides:</b> Realize todas as suas tentativas no Distrito para maximizar os medalhões do clã.</li>
                <li><b>Doações de Tropas:</b> Mantenha uma proporção justa de doações e peça tropas sempre que for atacar.</li>
                <li><b>Inatividade:</b> Ausências com mais de 3 dias sem aviso prévio à liderança podem resultar em desligamento.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ==============================================================================
# CONTROLE DE ROTEAMENTO DE PÁGINAS
# ==============================================================================
if st.session_state["pagina_atual"] == "layouts_guerra":
    renderizar_pagina_layouts("Guerra", "⚔️ Layouts de Guerra")
elif st.session_state["pagina_atual"] == "layouts_rankeada":
    renderizar_pagina_layouts("Rankeada", "🏆 Layouts Rankeados / Push")
elif st.session_state["pagina_atual"] == "regras_cla":
    renderizar_pagina_regras()

# ==============================================================================
# PÁGINA PRINCIPAL
# ==============================================================================
else:
    # LOGO COM TAMANHO AUMENTADO (180px)
    st.markdown(
        """
        <div style="text-align: center; margin-top: 10px; margin-bottom: 12px;">
            <img src="https://i.ibb.co/yBShz18b/winning.png" width="180" style="filter: drop-shadow(0px 8px 16px rgba(0,0,0,0.7)); transition: transform 0.3s ease;">
        </div>
        """,
        unsafe_allow_html=True,
    )

    # TÍTULO PRINCIPAL
    st.markdown(
        "<h1 class='main-title'>⚔️ Winning Wars APP</h1>",
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
                <div style="color: #e2e8f0; font-size: 1.05rem;">{mural_recado}</div>
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
        df_rank["Posição"] = [f"{i+1}º" for i in range(len(df_rank))]

        # PODIUM TOP 3
        if len(df_rank) >= 3:
            st.markdown("### 🥇 Pódio dos Líderes do Mês")
            col_p2, col_p1, col_p3 = st.columns(3)

            with col_p1:
                p1_nome = df_rank.iloc[0]["Nome"]
                p1_pts = int(df_rank.iloc[0]["Total"])
                st.markdown(
                    f"""
                    <div class="podium-card gold">
                        <div style="font-size: 2.2rem;">🥇</div>
                        <div class="podium-title">1º LUGAR</div>
                        <div class="podium-name">{p1_nome}</div>
                        <div class="podium-score"><b>{p1_pts}</b> PONTOS</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with col_p2:
                p2_nome = df_rank.iloc[1]["Nome"]
                p2_pts = int(df_rank.iloc[1]["Total"])
                st.markdown(
                    f"""
                    <div class="podium-card silver">
                        <div style="font-size: 1.8rem;">🥈</div>
                        <div class="podium-title">2º LUGAR</div>
                        <div class="podium-name">{p2_nome}</div>
                        <div class="podium-score"><b>{p2_pts}</b> PONTOS</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with col_p3:
                p3_nome = df_rank.iloc[2]["Nome"]
                p3_pts = int(df_rank.iloc[2]["Total"])
                st.markdown(
                    f"""
                    <div class="podium-card bronze">
                        <div style="font-size: 1.8rem;">🥉</div>
                        <div class="podium-title">3º LUGAR</div>
                        <div class="podium-name">{p3_nome}</div>
                        <div class="podium-score"><b>{p3_pts}</b> PONTOS</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # PAINEL ADMINISTRATIVO COM ABAS DE GERENCIAMENTO
        if "admin_logado" in st.session_state:
            with st.expander("🛠️ PAINEL DE GERENCIAMENTO ADMINISTRATIVO", expanded=False):
                st.info(f"Conectado como: **{st.session_state['admin_logado']}**")

                tab_p1, tab_p2, tab_p3, tab_p4 = st.tabs([
                    "📊 Lançamento de Pontos",
                    "➕ Adicionar Atividades",
                    "⚙️ Configurações & Recados",
                    "👥 Gestão de Jogadores & Admins",
                ])

                with tab_p1:
                    st.markdown("#### ✏️ Edição de Pontuação de Jogadores")
                    if not df.empty and "Nome" in df.columns:
                        col_sel_p, col_sel_act = st.columns(2)
                        with col_sel_p:
                            p_sel = st.selectbox("Selecione o Jogador:", df["Nome"].tolist(), key="admin_sel_player")
                        with col_sel_act:
                            act_sel = st.selectbox("Selecione a Atividade:", cols_somar, key="admin_sel_act")

                        if p_sel and act_sel:
                            idx_p = df[df["Nome"] == p_sel].index[0]
                            val_atual = float(df.at[idx_p, act_sel])
                            
                            with st.form("form_edita_ponto"):
                                novo_val = st.number_input(f"Nova pontuação em {act_sel} para {p_sel}:", value=float(val_atual), step=1.0)
                                if st.form_submit_button("💾 Salvar Pontuação"):
                                    cell_row = sheet_dados.find(p_sel).row
                                    col_headers = sheet_dados.row_values(1)
                                    cell_col = col_headers.index(act_sel) + 1
                                    sheet_dados.update_cell(cell_row, cell_col, novo_val)
                                    registrar_log(st.session_state["admin_logado"], f"Alterou {act_sel} de {p_sel} para {novo_val}")
                                    st.cache_data.clear()
                                    st.success("Pontuação atualizada!")
                                    st.rerun()

                with tab_p2:
                    st.markdown("#### ➕ Adicionar Novas Colunas de Atividade")
                    c_b1, c_b2, c_b3 = st.columns(3)
                    with c_b1:
                        if st.button("⚔️ Criar Guerra Normal", use_container_width=True):
                            prox_g = obter_proxima_coluna_sequencial("Guerra", df.columns if not df.empty else [])
                            headers = sheet_dados.row_values(1)
                            sheet_dados.update_cell(1, len(headers) + 1, prox_g)
                            st.cache_data.clear()
                            st.success(f"Coluna {prox_g} criada!")
                            st.rerun()
                    with c_b2:
                        if st.button("🏆 Criar Guerra de Liga", use_container_width=True):
                            prox_l = obter_proxima_coluna_sequencial("Liga", df.columns if not df.empty else [])
                            headers = sheet_dados.row_values(1)
                            sheet_dados.update_cell(1, len(headers) + 1, prox_l)
                            st.cache_data.clear()
                            st.success(f"Coluna {prox_l} criada!")
                            st.rerun()
                    with c_b3:
                        if st.button("🏰 Criar Raide", use_container_width=True):
                            prox_r = obter_proxima_coluna_sequencial("Raide", df.columns if not df.empty else [])
                            headers = sheet_dados.row_values(1)
                            sheet_dados.update_cell(1, len(headers) + 1, prox_r)
                            st.cache_data.clear()
                            st.success(f"Coluna {prox_r} criada!")
                            st.rerun()

                with tab_p3:
                    st.markdown("#### 📢 Mural da Liderança")
                    with st.form("form_mural_admin"):
                        novo_recado = st.text_area("Novo Recado para o Mural:", value=mural_recado)
                        if st.form_submit_button("Atualizar Mural"):
                            cell_mural = sheet_estado.find("mural_recado")
                            if cell_mural:
                                sheet_estado.update_cell(cell_mural.row, 2, novo_recado.strip())
                            else:
                                sheet_estado.append_row(["mural_recado", novo_recado.strip()])
                            registrar_log(st.session_state["admin_logado"], "Atualizou recado do mural")
                            st.cache_data.clear()
                            st.success("Mural atualizado!")
                            st.rerun()

                with tab_p4:
                    st.markdown("#### 👤 Gestão de Membros")
                    with st.form("form_cadastra_player", clear_on_submit=True):
                        novo_p_nome = st.text_input("Nome do Novo Jogador:")
                        if st.form_submit_button("Cadastrar Jogador"):
                            if novo_p_nome.strip():
                                sheet_dados.append_row([novo_p_nome.strip()])
                                registrar_log(st.session_state["admin_logado"], f"Cadastrou player {novo_p_nome.strip()}")
                                st.cache_data.clear()
                                st.success("Jogador cadastrado!")
                                st.rerun()

    # VISUALIZAÇÃO DO RANKING EM ABAS
    tab_ranking, tab_tabela = st.tabs(["🏆 Ranking Geral", "📋 Tabela Detalhada"])

    with tab_ranking:
        if not df.empty and "Total" in df.columns:
            st.markdown(
                "<div style='text-align: center; margin-bottom: 12px; color: #facc15;"
                " font-family: \"Luckiest Guy\", cursive; font-size: 1.3rem;'>"
                "🔥 COMPETIÇÃO ATIVA! DISPUTA PELO PASSE DOURADO 🎟️</div>",
                unsafe_allow_html=True,
            )

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

            altura_dinamica = max(450, len(df_exibicao) * 48 + 250)

            components.html(
                gerar_tabela_bilhete_dourado(df_exibicao),
                height=altura_dinamica,
                scrolling=True,
            )

    with tab_tabela:
        if not df.empty and "Total" in df.columns:
            st.markdown("### 📋 Tabela Detalhada Geral de Pontuações")
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
            st.dataframe(df_detalhada, use_container_width=True)

    # ==============================================================================
    # SEÇÃO FEED DE NOVIDADES (CRIADA ABAIXO DO RANKING NA PÁGINA PRINCIPAL)
    # ==============================================================================
    st.write("---")
    st.markdown(
        "<h2 style='text-align: center;'>📰 Feed de Novidades, Torneios & Eventos</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center; color: #cbd5e1;'>Fique por dentro das"
        " atualizações do Clash of Clans, eventos internos e comunicados da"
        " liderança do clã!</p><br>",
        unsafe_allow_html=True,
    )

    eh_admin = "admin_logado" in st.session_state

    # PAINEL DE PUBLICAÇÃO PARA ADMINS NO FEED
    if eh_admin:
        with st.expander("🔐 [ADMIN] Publicar Nova Novidade no Feed", expanded=False):
            with st.form("form_nova_novidade_feed", clear_on_submit=True):
                noticia_titulo = st.text_input("Título da Notícia")
                noticia_tag = st.selectbox(
                    "Categoria / Tag",
                    ["🎉 Evento", "⚔️ Torneio", "🚀 Atualização Game", "📢 Aviso Clã", "🏆 Premiação Extra"],
                )
                noticia_conteudo = st.text_area("Conteúdo do Comunicado", height=140)
                noticia_img = st.text_input(
                    "Link Direto da Imagem / Banner (Opcional)",
                    placeholder="https://exemplo.com/imagem.jpg",
                )
                btn_pub = st.form_submit_button("📢 Publicar Notícia no Feed", use_container_width=True)

                if btn_pub:
                    if noticia_titulo.strip() and noticia_conteudo.strip():
                        d_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
                        sheet_novidades.append_row([
                            d_hora,
                            noticia_titulo.strip(),
                            noticia_conteudo.strip(),
                            noticia_img.strip(),
                            noticia_tag,
                            st.session_state["admin_logado"],
                        ])
                        registrar_log(
                            st.session_state["admin_logado"],
                            f"Publicou notícia '{noticia_titulo.strip()}' pelo Feed",
                        )
                        st.cache_data.clear()
                        st.success("✅ Notícia publicada com sucesso!")
                        st.rerun()
                    else:
                        st.error("⚠️ O título e o conteúdo são obrigatórios.")

    # EXIBIÇÃO DAS NOVIDADES COMO UM FEED DE NOTÍCIAS
    if not df_novidades.empty:
        df_novidades_ordenado = df_novidades.iloc[::-1]

        for item_idx, row in df_novidades_ordenado.iterrows():
            data_hora = str(row.get("DataHora", ""))
            titulo = str(row.get("Titulo", ""))
            conteudo = str(row.get("Conteudo", ""))
            img_url = str(row.get("ImagemUrl", "")).strip()
            tag_nome = str(row.get("Tag", "📢 Aviso"))
            autor_nome = str(row.get("Autor", "Liderança"))

            html_card = f"""
            <div class="news-card">
                <span class="news-tag">{tag_nome}</span>
                <div class="news-title">{titulo}</div>
                <div class="news-meta">📅 Publicado em {data_hora} por <b>{autor_nome}</b></div>
                <div style="font-size: 1.05rem; line-height: 1.6; color: #e2e8f0; white-space: pre-wrap;">{conteudo}</div>
            """
            if img_url:
                html_card += f"""
                <div style="margin-top: 15px; text-align: center;">
                    <img src="{img_url}" style="max-width: 100%; border-radius: 10px; border: 1px solid #334155;">
                </div>
                """
            html_card += "</div>"

            st.markdown(html_card, unsafe_allow_html=True)

            # OPÇÕES DE EDIÇÃO/EXCLUSÃO PARA ADMINS NO FEED
            if eh_admin:
                with st.expander(f"✏️ [ADMIN] Gerenciar Postagem: '{titulo}'"):
                    with st.form(key=f"form_edit_feed_{item_idx}"):
                        edit_titulo = st.text_input("Título", value=titulo, key=f"edit_tit_{item_idx}")
                        tags_disponiveis = [
                            "🎉 Evento", "⚔️ Torneio", "🚀 Atualização Game", "📢 Aviso Clã", "🏆 Premiação Extra"
                        ]
                        tag_index = tags_disponiveis.index(tag_nome) if tag_nome in tags_disponiveis else 0
                        edit_tag = st.selectbox(
                            "Categoria / Tag",
                            tags_disponiveis,
                            index=tag_index,
                            key=f"edit_tag_{item_idx}",
                        )
                        edit_conteudo = st.text_area(
                            "Conteúdo", value=conteudo, height=140, key=f"edit_conteudo_{item_idx}"
                        )
                        edit_img = st.text_input(
                            "Link da Imagem / Banner", value=img_url, key=f"edit_img_{item_idx}"
                        )
                        
                        c_edit, c_del = st.columns(2)
                        with c_edit:
                            btn_editar = st.form_submit_button("💾 Salvar Alterações", use_container_width=True)
                        with c_del:
                            btn_excluir = st.form_submit_button("🗑️ Excluir Publicação", use_container_width=True)

                        if btn_editar:
                            if not edit_titulo.strip() or not edit_conteudo.strip():
                                st.error("⚠️ O título e o conteúdo são obrigatórios.")
                            else:
                                linha_planilha = int(item_idx) + 2
                                sheet_novidades.update(
                                    f"A{linha_planilha}:F{linha_planilha}",
                                    [[
                                        data_hora,
                                        edit_titulo.strip(),
                                        edit_conteudo.strip(),
                                        edit_img.strip(),
                                        edit_tag,
                                        st.session_state["admin_logado"],
                                    ]],
                                )
                                registrar_log(
                                    st.session_state["admin_logado"],
                                    f"Editou notícia '{titulo}' no feed",
                                )
                                st.cache_data.clear()
                                st.success("✅ Publicação atualizada!")
                                st.rerun()

                        if btn_excluir:
                            linha_planilha = int(item_idx) + 2
                            sheet_novidades.delete_rows(linha_planilha)
                            registrar_log(
                                st.session_state["admin_logado"],
                                f"Excluiu notícia '{titulo}' do feed",
                            )
                            st.cache_data.clear()
                            st.success("🗑️ Publicação excluída!")
                            st.rerun()
    else:
        st.info("Nenhuma novidade ou notícia publicada no momento.")

    # ==============================================================================
    # GALERIA DA FAMA & REGULAMENTO (SEÇÃO INFERIOR / RODAPÉ)
    # ==============================================================================
    st.write("---")
    st.markdown(
        "<h2 style='text-align: center;'>🌟 Galeria da Fama</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center; color: #cbd5e1;'>Histórico dos grandes guerreiros do clã que conquistaram o Passe Dourado!</p><br>",
        unsafe_allow_html=True,
    )

    if not df_fama.empty:
        df_fama_exib = df_fama.copy()
        if "Primeiro" in df_fama_exib.columns:
            df_fama_exib["Primeiro"] = "🥇 " + df_fama_exib["Primeiro"].astype(str)
        if "Segundo" in df_fama_exib.columns:
            df_fama_exib["Segundo"] = "🥈 " + df_fama_exib["Segundo"].astype(str)
        if "Terceiro" in df_fama_exib.columns:
            df_fama_exib["Terceiro"] = "🥉 " + df_fama_exib["Terceiro"].astype(str)

        st.dataframe(df_fama_exib, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum registro ainda na Galeria da Fama.")

    # RODAPÉ FINAL COM OS BOTÕES EXIBIDOS NO FINAL DA PÁGINA
    st.write("---")
    st.markdown(
        "<h2 style='text-align: center;'>📜 Regulamento & Links do Clã</h2>",
        unsafe_allow_html=True,
    )

    col_rod1, col_rod2, col_rod3 = st.columns(3)

    with col_rod1:
        if st.button("📖 REGRAS OFICIAIS DO CLÃ", use_container_width=True):
            st.session_state["pagina_atual"] = "regras_cla"
            st.rerun()

    with col_rod2:
        st.markdown(
            '<a'
            ' href="https://www.youtube.com/@winningwarscoc?sub_confirmation=1"'
            ' target="_blank" class="btn-youtube-link">📺 CANAL NO YOUTUBE ↗</a>',
            unsafe_allow_html=True,
        )

    with col_rod3:
        st.markdown(
            '<a'
            ' href="https://link.clashofclans.com/?action=OpenSCID&p=25-1cb8481f-3a79-4681-90f9-8914acef2d63"'
            ' target="_blank" class="btn-scid"><img'
            ' src="https://i.ibb.co/fzPGy6fr/bg-hero-scid-landing-0.webp"'
            ' height="20" style="border-radius: 4px; object-fit:'
            ' cover;"> ADD GODOY (SUPERCELL ID) ↗</a>',
            unsafe_allow_html=True,
        )
