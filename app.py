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


# --- FUNÇÃO PARA GERAR A TABELA COMPLETA EM HTML E DOWNLOAD EM HD ---
def gerar_tabela_bilhete_dourado(df_exib):
    """Gera o HTML do ranking em iframe com suporte a download em alta qualidade (HD) usando html2canvas."""
    from html import escape

    linhas_html = []
    for _, row in df_exib.iterrows():
        posicao = escape(str(row.get("Posição", "")))
        jogador = escape(str(row.get("Jogador", "")))
        try:
            pontuacao = int(float(row.get("Pontuação Total", 0)))
        except (TypeError, ValueError):
            pontuacao = 0

        pos_str = str(row.get("Posição", "")).strip()
        if pos_str == "1º":
            classe_linha = 'class="row-top1"'
            medalha = "🥇 "
        elif pos_str == "2º":
            classe_linha = 'class="row-top2"'
            medalha = "🥈 "
        elif pos_str == "3º":
            classe_linha = 'class="row-top3"'
            medalha = "🥉 "
        else:
            classe_linha = ""
            medalha = ""

        linhas_html.append(
            f'<tr {classe_linha}><td class="tabela-posicao">{posicao}</td>'
            f'<td class="tabela-nome">{medalha}{jogador}</td>'
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

      .tabela-bilhete tr:hover {{ 
        background-color: #1e293b; 
      }}

      /* Destaques Suaves para o Top 3 */
      .tabela-bilhete tr.row-top1 {{
        background: linear-gradient(90deg, rgba(250, 204, 21, 0.22) 0%, rgba(245, 158, 11, 0.12) 100%) !important;
      }}
      .tabela-bilhete tr.row-top1 .tabela-nome {{
        color: #fef08a !important;
        font-weight: 900;
        text-shadow: 0px 0px 8px rgba(250, 204, 21, 0.4);
      }}
      .tabela-bilhete tr.row-top1 .tabela-posicao {{
        color: #facc15 !important;
        font-weight: 900;
      }}

      .tabela-bilhete tr.row-top2 {{
        background: linear-gradient(90deg, rgba(226, 232, 240, 0.18) 0%, rgba(148, 163, 184, 0.10) 100%) !important;
      }}
      .tabela-bilhete tr.row-top2 .tabela-nome {{
        color: #f1f5f9 !important;
        font-weight: 900;
        text-shadow: 0px 0px 8px rgba(226, 232, 240, 0.3);
      }}
      .tabela-bilhete tr.row-top2 .tabela-posicao {{
        color: #e2e8f0 !important;
        font-weight: 900;
      }}

      .tabela-bilhete tr.row-top3 {{
        background: linear-gradient(90deg, rgba(249, 115, 22, 0.20) 0%, rgba(217, 119, 6, 0.10) 100%) !important;
      }}
      .tabela-bilhete tr.row-top3 .tabela-nome {{
        color: #ffedd5 !important;
        font-weight: 900;
        text-shadow: 0px 0px 8px rgba(249, 115, 22, 0.3);
      }}
      .tabela-bilhete tr.row-top3 .tabela-posicao {{
        color: #f97316 !important;
        font-weight: 900;
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

    .info-card { background-color: #1e293b; border: 2px solid #334155; border-radius: 12px; padding: 16px; margin-bottom: 12px; }
    .info-card-header { font-family: 'Luckiest Guy', cursive; color: #facc15; font-size: 1.15rem; margin-bottom: 8px; }
    .info-card-list { color: #cbd5e1; font-size: 0.95rem; line-height: 1.5; padding-left: 20px; margin: 0; }
    .info-card-list li { margin-bottom: 4px; }

    .mural-banner { background: linear-gradient(135deg, #1e1b4b 0%, #311042 100%); border: 2px solid #a855f7; border-radius: 12px; padding: 16px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(168, 85, 247, 0.2); }
    .mural-header { font-family: 'Luckiest Guy', cursive; color: #f0abfc; font-size: 1.25rem; margin-bottom: 6px; }

    @media (max-width: 768px) {
        .main-title { font-size: 2.1rem !important; }
        .main-subtitle { font-size: 1rem !important; }
        button[data-baseweb="tab"] { font-size: 1.05rem !important; padding: 10px 14px !important; margin-right: 2px !important; }
        .podium-title { font-size: 1.1rem; }
        .podium-name { font-size: 1.05rem; }
        .podium-score { font-size: 0.95rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --- ROTEADOR DE PÁGINAS ---
if st.session_state["pagina_atual"] == "regras_cla":
  # PÁGINA: REGRAS OFICIAIS DO CLÃ
  c_voltar, _, _ = st.columns([1, 2, 1])
  with c_voltar:
    if st.button("⬅️ VOLTAR AO INÍCIO", use_container_width=True):
      st.session_state["pagina_atual"] = "principal"
      st.rerun()

  st.markdown(
      "<h1 style='text-align: center;'>📖 Regras Oficiais do Clã</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='text-align: center; color: #cbd5e1;'>Winning Wars - Diretrizes"
      " e Boas Práticas</p>",
      unsafe_allow_html=True,
  )
  st.write("---")

  col_r1, col_r2 = st.columns(2)
  with col_r1:
    st.markdown("""
        ### ⚔️ Guerras de Clãs (CW)
        * **Ataques Obrigatórios:** Faça sempre os 2 ataques em todas as guerras que participar.
        * **Respeito às Estratégias:** Siga a marcação de alvos enviada pela liderança/mural.
        * **Heróis Ativos:** Mantenha os heróis acordados durante a guerra.
        """)

    st.markdown("""
        ### 🛡️ Liga de Guerras (CWL)
        * **Foco Máximo:** Apenas ataques com exército completo e estratégias consolidadas.
        * **Ausências:** Avise a liderança com antecedência caso não vá conseguir atacar.
        """)

  with col_r2:
    st.markdown("""
        ### 🏰 Raides do Distrito
        * **Participação Geral:** Use todos os ataques disponíveis na Capital do Clã.
        * **Foco em Ouro:** Priorize a melhoria dos edifícios recomendados pela liderança.
        """)

    st.markdown("""
        ### 🏆 Jogos de Clã & Convivência
        * **Meta Mínima:** Faça a pontuação mínima estabelecida em cada edição.
        * **Respeito no Chat:** Mantenha um ambiente saudável e amigável no WhatsApp e no chat do jogo.
        """)

  st.write("")
  if st.button("🔙 VOLTAR PARA PÁGINA PRINCIPAL", use_container_width=True):
    st.session_state["pagina_atual"] = "principal"
    st.rerun()

  st.stop()


# --- BARRA SUPERIOR E ÁREA DE ADMIN ---
b1, b2, b3, b4, b5, b6, col_admin_top = st.columns([1, 1, 1, 1, 1, 1, 1])

with b1:
  if st.button("🏠 Início", use_container_width=True):
    st.session_state["pagina_atual"] = "principal"
    st.rerun()

with b2:
  if st.button("🏰 Layouts", use_container_width=True):
    st.session_state["pagina_atual"] = "layouts"
    st.rerun()

with b3:
  if st.button("📜 Regras", use_container_width=True):
    st.session_state["pagina_atual"] = "regras_cla"
    st.rerun()

with b4:
  st.markdown(
      '<a href="https://whatsapp.com/channel/0029VaA8fA36BIEdP3RIn73c"'
      ' target="_blank" class="btn-external-link">📱 Canal WhatsApp ↗</a>',
      unsafe_allow_html=True,
  )

with b5:
  st.markdown(
      '<a'
      ' href="https://www.youtube.com/@winningwarscoc?sub_confirmation=1"'
      ' target="_blank" class="btn-youtube-link">📺 YouTube ↗</a>',
      unsafe_allow_html=True,
  )

with b6:
  st.markdown(
      '<a'
      ' href="https://link.clashofclans.com/?action=OpenSCID&p=25-1cb8481f-3a79-4681-90f9-8914acef2d63"'
      ' target="_blank" class="btn-scid"><img'
      ' src="https://i.ibb.co/fzPGy6fr/bg-hero-scid-landing-0.webp"'
      ' height="20" style="border-radius: 4px; object-fit:'
      ' cover;"> Add Godoy ↗</a>',
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
      usuario_login = st.text_input("Usuário", key="pop_user")
      senha_login = st.text_input("Senha", type="password", key="pop_pass")
      if st.button("Entrar", key="pop_btn", use_container_width=True):
        if not df_admins.empty:
          hash_senha = gerar_hash(senha_login)
          validacao = df_admins[
              (df_admins["Usuario"] == usuario_login)
              & (df_admins["SenhaHash"] == hash_senha)
          ]
          if not validacao.empty:
            st.session_state["admin_logado"] = usuario_login
            st.success("✅ Login realizado!")
            time.sleep(0.5)
            st.rerun()
          else:
            st.error("❌ Usuário ou senha incorretos.")
        else:
          st.error("⚠️ Tabela de administradores vazia.")

# --- ROUTER DE PÁGINAS ADICIONAIS ---
if st.session_state["pagina_atual"] == "layouts":
  st.markdown(
      "<h1 class='main-title'>🏰 Biblioteca de Layouts</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p class='main-subtitle'>Encontre os melhores layouts testados para"
      " Guerra, Push e Farm.</p>",
      unsafe_allow_html=True,
  )

  eh_admin = "admin_logado" in st.session_state

  # SEÇÃO EXCLUSIVA ADMIN: CADASTRO DE LAYOUT
  if eh_admin:
    with st.expander("➕ Cadastrar Novo Layout (Área Admin)", expanded=False):
      with st.form("form_novo_layout"):
        col_cad1, col_cad2 = st.columns(2)
        with col_cad1:
          cad_tipo = st.selectbox(
              "Tipo de Vila", ["Vila Principal", "Base do Construtor"]
          )
          cad_cv = st.selectbox(
              "Nível do Centro de Vila / Construtor",
              [f"CV {i}" for i in range(17, 8, -1)]
              if cad_tipo == "Vila Principal"
              else [f"BH {i}" for i in range(10, 3, -1)],
          )
          cad_autor = st.text_input(
              "Autor / Criador", value=st.session_state["admin_logado"]
          )
          cad_tag = st.selectbox(
              "Tag do Layout", ["Guerra", "CWL", "Farm", "Defense", "Troll"]
          )
        with col_cad2:
          cad_link = st.text_input("Link de Cópia do Clash")
          cad_desc = st.text_area("Descrição Breve")
          cad_img = st.text_input("URL da Imagem de Pré-visualização")

        if st.form_submit_button("💾 Cadastrar Layout"):
          if not cad_link:
            st.error("⚠️ O campo 'Link de Cópia' é obrigatório!")
          else:
            sheet_layouts.append_row([
                cad_tipo,
                cad_cv,
                cad_autor,
                cad_link,
                cad_desc,
                cad_img,
                cad_tag,
            ])
            registrar_log(
                st.session_state["admin_logado"],
                f"Cadastrou layout para {cad_cv} ({cad_tipo})",
            )
            st.cache_data.clear()
            st.success("✅ Layout cadastrado com sucesso!")
            st.rerun()

  # EXIBIÇÃO DE LAYOUTS
  tab_vp, tab_bh = st.tabs(["🏰 Vila Principal", "🛠️ Base do Construtor"])

  def exibir_grid_layouts(df_filtrado, tipo_layout):
    if df_filtrado.empty:
      st.info(
          f"Nenhum layout cadastrado ainda para **{tipo_layout}**. Adicione"
          " através do painel admin!"
      )
      return

    cvs_disponiveis = sorted(df_filtrado["CV"].unique(), reverse=True)
    cv_selecionado = st.selectbox(
        f"Filtrar por Nível ({tipo_layout})",
        ["Todos"] + list(cvs_disponiveis),
        key=f"select_{tipo_layout}",
    )

    df_exibicao = (
        df_filtrado
        if cv_selecionado == "Todos"
        else df_filtrado[df_filtrado["CV"] == cv_selecionado]
    )

    cols = st.columns(3)
    for idx, row in df_exibicao.iterrows():
      with cols[idx % 3]:
        with st.container():
          st.markdown(
              f"""
                    <div style="background-color: #1e293b; border: 2px solid #334155; border-radius: 12px; padding: 16px; margin-bottom: 20px;">
                        <h3 style="margin-top:0; font-size: 1.3rem;">{row['CV']} - <span style="color:#facc15;">{row.get('Tag', 'Geral')}</span></h3>
                        <p style="color:#cbd5e1; font-size: 0.95rem; margin-bottom: 8px;"><b>Criador:</b> {row.get('Autor', 'Anônimo')}</p>
                        <p style="color:#cbd5e1; font-size: 0.9rem;">{row.get('Descricao', '')}</p>
                    </div>
                    """,
              unsafe_allow_html=True,
          )

          img_url = str(row.get("ImagemUrl", "")).strip()
          if img_url and img_url.lower().startswith("http"):
            try:
              img_url_limpa = img_url.split("?")[0]
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
                    f'<div style="text-align: center; margin-bottom: 10px;"><a'
                    f' href="{img_url_limpa}" target="_blank" download'
                    ' style="color: #38bdf8; text-decoration: underline;'
                    ' font-weight: bold; font-size: 0.95rem;">📥 Baixar Imagem'
                    ' (Admin)</a></div>',
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
            cv_nome = str(row.get("CV", ""))
            item_idx = str(idx)
            if st.button(
                "❌ Excluir Layout (Admin)",
                key=f"del_{tipo_layout}_{cv_nome}_{item_idx}",
                use_container_width=True,
            ):
              try:
                cell = sheet_layouts.find(str(row["Link"]))
                if cell:
                  sheet_layouts.delete_rows(cell.row)
                  registrar_log(
                      st.session_state["admin_logado"],
                      f"Excluiu layout de {row.get('CV')}",
                  )
                  st.cache_data.clear()
                  st.success("✅ Layout removido com sucesso!")
                  st.rerun()
              except Exception:
                st.error("Erro ao tentar remover layout.")

  with tab_vp:
    exibir_grid_layouts(
        df_layouts[df_layouts["Tipo"] == "Vila Principal"]
        if not df_layouts.empty
        else pd.DataFrame(),
        "Vila Principal",
    )

  with tab_bh:
    exibir_grid_layouts(
        df_layouts[df_layouts["Tipo"] == "Base do Construtor"]
        if not df_layouts.empty
        else pd.DataFrame(),
        "Base do Construtor",
    )

  st.stop()


# --- PÁGINA PRINCIPAL ---
st.markdown(
    "<h1 class='main-title'>🏆 Winning Wars - Bilhete Dourado</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p class='main-subtitle'>Acompanhe o desempenho do clã nas guerras,"
    " raides e eventos em tempo real!</p>",
    unsafe_allow_html=True,
)

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
  df["Total"] = df[cols_somar].sum(axis=1)

  df_rank = df.sort_values(by="Total", ascending=False).reset_index(drop=True)
  df_rank["Posição"] = [f"{i+1}º" for i in range(len(df_rank))]


# NAV TABS
tab_ranking, tab_tabela, tab_admin = st.tabs(
    ["🏆 Ranking ao Vivo", "📋 Tabela Detalhada", "🔐 Painel Admin"]
)

# ABA 1: RANKING AO VIVO
with tab_ranking:
  if not df.empty and "Total" in df.columns:
    if mes_finalizado:
      st.success("🎉 **Mês Finalizado!** Confira o pódio oficial abaixo.")

    if len(df_rank) >= 3:
      c1, c2, c3 = st.columns(3)
      with c1:
        st.markdown(
            f"""
                <div class="podium-card gold">
                    <div style="font-size: 2.5rem;">🥇</div>
                    <div class="podium-title">1º LUGAR</div>
                    <div class="podium-name">{df_rank.iloc[0]['Nome']}</div>
                    <div class="podium-score"><b>{int(df_rank.iloc[0]['Total'])}</b> pts</div>
                </div>
                """,
            unsafe_allow_html=True,
        )
      with c2:
        st.markdown(
            f"""
                <div class="podium-card silver">
                    <div style="font-size: 2.5rem;">🥈</div>
                    <div class="podium-title">2º LUGAR</div>
                    <div class="podium-name">{df_rank.iloc[1]['Nome']}</div>
                    <div class="podium-score"><b>{int(df_rank.iloc[1]['Total'])}</b> pts</div>
                </div>
                """,
            unsafe_allow_html=True,
        )
      with c3:
        st.markdown(
            f"""
                <div class="podium-card bronze">
                    <div style="font-size: 2.5rem;">🥉</div>
                    <div class="podium-title">3º LUGAR</div>
                    <div class="podium-name">{df_rank.iloc[2]['Nome']}</div>
                    <div class="podium-score"><b>{int(df_rank.iloc[2]['Total'])}</b> pts</div>
                </div>
                """,
            unsafe_allow_html=True,
        )

    st.write("---")

    col_busca, _, _ = st.columns([2, 1, 1])
    with col_busca:
      busca = st.text_input(
          "🔎 Localizar jogador",
          placeholder="Digite o nome do jogador...",
          key="busca_ranking_ao_vivo",
      ).strip().lower()

    df_exib = df_rank[["Posição", "Nome", "Total"]].copy()
    df_exib.columns = ["Posição", "Jogador", "Pontuação Total"]

    if busca:
      df_exib = df_exib[
          df_exib["Jogador"].astype(str).str.lower().str.contains(busca)
      ]

    # RENDERIZA A TABELA BILHETE DOURADO
    html_bilhete = gerar_tabela_bilhete_dourado(df_exib)
    altura_iframe = min(800, max(380, 180 + len(df_exib) * 45))
    components.html(html_bilhete, height=altura_iframe, scrolling=False)

    # REGRAS BÁSICAS
    st.write("---")
    info_col1, info_col2 = st.columns(2)
    with info_col1:
      st.markdown(
          """
            <div class="info-card">
                <div class="info-card-header">ℹ️ Como Funciona o Bilhete Dourado</div>
                <ul class="info-card-list">
                    <li><b>Pontuação Cumulativa:</b> Soma de Guerras, CWL, Raides e Jogos.</li>
                    <li><b>Atualização:</b> Dados sincronizados automaticamente com o sistema.</li>
                    <li><b>Em caso de Empate:</b> Sorteio de desempate.</li>
                </ul>
            </div>
            """,
          unsafe_allow_html=True,
      )
    with info_col2:
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

    # GALERIA DA FAMA
    st.write("---")
    st.markdown(
        "<h2 style='text-align: center;'>🌟 Galeria da Fama</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center; color: #cbd5e1;'>Vencedores históricos"
        " das edições anteriores do Bilhete Dourado</p>",
        unsafe_allow_html=True,
    )

    if not df_fama.empty:
      for idx, row_fama in df_fama.iterrows():
        st.markdown(
            f"""
                <div style="background-color: #1e293b; border: 2px solid #334155; border-radius: 12px; padding: 16px; margin-bottom: 12px;">
                    <h3 style="margin-top:0; color: #facc15; text-align: center;">📅 {row_fama.get('MesAno', 'Edição Passada')}</h3>
                    <div style="display: flex; justify-content: space-around; text-align: center; flex-wrap: wrap; gap: 10px;">
                        <div>🥇 <b>1º Lugar:</b> <span style="color:#fef08a;">{row_fama.get('Primeiro', '-')}</span></div>
                        <div>🥈 <b>2º Lugar:</b> <span style="color:#e2e8f0;">{row_fama.get('Segundo', '-')}</span></div>
                        <div>🥉 <b>3º Lugar:</b> <span style="color:#fed7aa;">{row_fama.get('Terceiro', '-')}</span></div>
                    </div>
                </div>
                """,
            unsafe_allow_html=True,
        )
    else:
      st.info(
          "Nenhum campeão registrado na Galeria da Fama ainda. Os vencedores"
          " aparecerão aqui após o encerramento do mês!"
      )
  else:
    st.info("Nenhum dado encontrado para exibição do ranking no momento.")


# ABA 2: TABELA DETALHADA GERAL
with tab_tabela:
  if not df.empty and "Total" in df.columns:
    st.markdown("### 📋 Tabela Detalhada Geral de Pontuações")
    st.markdown(
        "Acompanhe os pontos por atividade. No celular, **Nome** e **Total** "
        "permanecem fixos enquanto você desliza para visualizar as atividades."
    )

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

    _, col_busca, _ = st.columns([1, 2, 1])
    with col_busca:
      busca_detalhada = st.text_input(
          "🔎 Localizar jogador",
          placeholder="Digite parte do nome para localizar...",
          key="busca_tabela_detalhada",
      ).strip().lower()

    if busca_detalhada:
      mascara = df_detalhada["Nome"].astype(str).str.lower().str.contains(busca_detalhada)
      df_detalhada = df_detalhada[mascara]

    df_tabela_mobile = df_detalhada.copy()

    # MONTA O CABEÇALHO HTML
    headers_html = []
    for c in cols_exibicao:
      cls = ""
      if c == "Nome":
        cls = 'class="col-nome"'
      elif c == "Total":
        cls = 'class="col-total"'

      c_label = c.replace("_", " ")
      headers_html.append(f'<th {cls}>{c_label}</th>')

    # MONTA AS LINHAS DA TABELA
    rows_html = []
    for _, row in df_tabela_mobile.iterrows():
      tds = []
      for c in cols_exibicao:
        val = row[c]
        cls = ""
        if c == "Nome":
          cls = 'class="col-nome"'
        elif c == "Total":
          cls = 'class="col-total"'

        tds.append(f'<td {cls}>{val}</td>')
      rows_html.append(f'<tr>{"".join(tds)}</tr>')

    html_tabela = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
      <style>
        @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@600;800;900&display=swap');
        * {{ box-sizing: border-box; }}
        body {{ margin:0; background:transparent; font-family:'Nunito', sans-serif; }}
        
        .btn-download-img {{
          background: linear-gradient(180deg, #3b82f6 0%, #1d4ed8 100%);
          color: #ffffff !important;
          font-family: 'Nunito', sans-serif;
          font-weight: 800;
          font-size: 0.95rem;
          padding: 8px 16px;
          border: 2px solid #93c5fd;
          border-radius: 8px;
          box-shadow: 0px 4px 0px #1e3a8a;
          cursor: pointer;
          transition: all 0.2s ease;
        }}
        .btn-download-img:hover {{ background: linear-gradient(180deg, #60a5fa 0%, #2563eb 100%); }}

        .viewport {{
          width:100%;
          overflow:auto;
          max-height:68vh;
          border:1px solid #334155;
          border-radius:10px;
          -webkit-overflow-scrolling:touch;
          background:#0f172a;
        }}
        table {{
          border-collapse:separate;
          border-spacing:0;
          min-width:760px;
          width:max-content;
          background:#0f172a;
        }}
        th,td {{
          padding:9px 11px;
          border-right:1px solid #334155;
          border-bottom:1px solid #334155;
          text-align:center;
          white-space:nowrap;
          font-size:13px;
          color:#e2e8f0;
          background:#0f172a;
        }}
        thead th {{
          background:#1e293b;
          font-weight:800;
          position:sticky;
          top:0;
          z-index:5;
          color:#facc15;
        }}
        .col-nome {{
          position:sticky;
          left:0;
          z-index:10;
          text-align:left;
          font-weight:800;
          background:#0f172a !important;
          min-width:140px;
          border-right:2px solid #475569 !important;
        }}
        thead th.col-nome {{
          background:#1e293b !important;
          z-index:20;
        }}
        .col-total {{
          position:sticky;
          right:0;
          z-index:10;
          font-weight:900;
          color:#38bdf8 !important;
          background:#0f172a !important;
          border-left:2px solid #475569 !important;
        }}
        thead th.col-total {{
          background:#1e293b !important;
          z-index:20;
        }}
        tr:nth-child(even) td {{ background:#111827; }}
        tr:nth-child(even) .col-nome, tr:nth-child(even) .col-total {{ background:#111827 !important; }}
      </style>
    </head>
    <body>
      <div style="text-align: right; margin-bottom: 8px;">
        <button class="btn-download-img" onclick="baixarTabelaGeralHD()">📸 Baixar Tabela HD</button>
      </div>
      <div class="viewport" id="container-tabela-geral">
        <table>
          <thead><tr>{''.join(headers_html)}</tr></thead>
          <tbody>{''.join(rows_html)}</tbody>
        </table>
      </div>
      <script>
        function baixarTabelaGeralHD() {{
          const el = document.getElementById('container-tabela-geral');
          html2canvas(el, {{ scale: 2.5, useCORS: true, backgroundColor: '#0f172a' }}).then(canvas => {{
            const link = document.createElement('a');
            link.download = 'tabela_detalhada_pontos.png';
            link.href = canvas.toDataURL('image/png', 1.0);
            link.click();
          }});
        }}
      </script>
    </body>
    </html>
    """

    altura = min(900, max(300, 150 + len(df_tabela_mobile) * 40))
    components.html(html_tabela, height=altura, scrolling=False)


# ABA 3: ÁREA ADMIN
with tab_admin:
  st.subheader("🔐 Painel de Controle e Administração")

  if "admin_logado" not in st.session_state:
    st.info(
        "👉 Faça o login clicando no botão **'🔐 Admin'** no canto superior"
        " direito da página para acessar os controles de gestão."
    )
  else:
    st.success(
        f"Sessão Ativa: **{st.session_state['admin_logado']}** (Gerenciamento"
        " Liberado)"
    )

    sub_tab1, sub_tab2, sub_tab_pass, sub_tab3, sub_tab4, sub_tab5, sub_tab6, sub_tab7 = st.tabs([
        "➕ Players",
        "👤 Novo Admin",
        "🔑 Alterar Senha",
        "✏️ Gerenciar Pontos e Colunas",
        "📢 Recado / Arquivar Mês",
        "📜 Logs do Sistema",
        "💾 Backup de Dados",
        "🎲 Sorteio de Desempate",
    ])

    with sub_tab1:
      st.markdown("#### ➕ Adicionar Novo Jogador à Tabela")
      with st.form("form_add_player"):
        novo_nome = st.text_input("Nome do Jogador")
        btn_add_p = st.form_submit_button("Cadastrar Jogador")
        if btn_add_p:
          if not novo_nome.strip():
            st.error("⚠️ Digite um nome válido.")
          else:
            headers = sheet_dados.row_values(1)
            nova_linha = [novo_nome.strip()] + [0] * (len(headers) - 1)
            sheet_dados.append_row(nova_linha)
            registrar_log(
                st.session_state["admin_logado"],
                f"Adicionou player: {novo_nome.strip()}",
            )
            st.cache_data.clear()
            st.success(f"✅ Jogador **{novo_nome.strip()}** cadastrado!")
            st.rerun()

    with sub_tab2:
      st.markdown("#### 👤 Cadastrar Novo Administrador")
      with st.form("form_add_admin"):
        novo_admin_user = st.text_input("Novo Usuário Admin")
        novo_admin_pass = st.text_input("Senha", type="password")
        btn_add_adm = st.form_submit_button("Cadastrar Admin")
        if btn_add_adm:
          if not novo_admin_user.strip() or not novo_admin_pass.strip():
            st.error("⚠️ Preencha usuário e senha.")
          else:
            hash_pass = gerar_hash(novo_admin_pass.strip())
            sheet_admins.append_row([novo_admin_user.strip(), hash_pass])
            registrar_log(
                st.session_state["admin_logado"],
                f"Cadastrou admin: {novo_admin_user.strip()}",
            )
            st.cache_data.clear()
            st.success(f"✅ Admin **{novo_admin_user.strip()}** cadastrado!")
            st.rerun()

    with sub_tab_pass:
      st.markdown("#### 🔑 Alterar Senha da Minha Conta Admin")
      with st.form("form_alterar_senha"):
        senha_atual = st.text_input("Senha Atual", type="password")
        nova_senha = st.text_input("Nova Senha", type="password")
        conf_nova_senha = st.text_input("Confirmar Nova Senha", type="password")
        btn_trocar_senha = st.form_submit_button("Atualizar Senha")

        if btn_trocar_senha:
          if not senha_atual or not nova_senha:
            st.error("⚠️ Preencha todos os campos do formulário.")
          elif nova_senha != conf_nova_senha:
            st.error("⚠️ A nova senha e a confirmação não coincidem.")
          else:
            admin_atual = st.session_state["admin_logado"]
            df_admins_atual = pd.DataFrame(sheet_admins.get_all_records())
            if not df_admins_atual.empty:
              validacao = df_admins_atual[
                  (df_admins_atual["Usuario"] == admin_atual)
                  & (df_admins_atual["SenhaHash"] == gerar_hash(senha_atual))
              ]
              if validacao.empty:
                st.error("⚠️ Senha atual incorreta!")
              else:
                cell = sheet_admins.find(admin_atual)
                if cell:
                  sheet_admins.update_cell(
                      cell.row, 2, gerar_hash(nova_senha)
                  )
                  registrar_log(
                      admin_atual, "Alterou a própria senha de acesso"
                  )
                  st.cache_data.clear()
                  st.success("✅ Senha alterada com sucesso!")
                  st.rerun()

    with sub_tab3:
      st.markdown("#### ➕ Criar Novas Colunas de Atividades")
      c_col1, c_col2, c_col3 = st.columns(3)

      with c_col1:
        if st.button("➕ Criar Próxima Guerra (Guerra_X)"):
          headers = sheet_dados.row_values(1)
          proxima_guerra = obter_proxima_coluna_sequencial("Guerra", headers)
          if proxima_guerra in headers:
            st.error(f"⚠️ A coluna {proxima_guerra} já existe!")
          else:
            proxima_col_num = len(headers) + 1
            sheet_dados.update_cell(1, proxima_col_num, proxima_guerra)
            if not df.empty:
              num_linhas = len(df)
              sheet_dados.update(
                  f"{gspread.utils.rowcol_to_a1(2, proxima_col_num)}:{gspread.utils.rowcol_to_a1(num_linhas + 1, proxima_col_num)}",
                  [[0]] * num_linhas,
              )
            registrar_log(
                st.session_state["admin_logado"],
                f"Criou a coluna de Guerra '{proxima_guerra}'",
            )
            st.cache_data.clear()
            st.success(
                f"✅ Coluna **{proxima_guerra}** adicionada com sucesso!"
            )
            st.rerun()

      with c_col2:
        if st.button("➕ Criar Próximo Dia de Liga (Liga_X)"):
          headers = sheet_dados.row_values(1)
          proxima_liga = obter_proxima_coluna_sequencial("Liga", headers)
          if proxima_liga in headers:
            st.error(f"⚠️ A coluna {proxima_liga} já existe!")
          else:
            proxima_col_num = len(headers) + 1
            sheet_dados.update_cell(1, proxima_col_num, proxima_liga)
            if not df.empty:
              num_linhas = len(df)
              sheet_dados.update(
                  f"{gspread.utils.rowcol_to_a1(2, proxima_col_num)}:{gspread.utils.rowcol_to_a1(num_linhas + 1, proxima_col_num)}",
                  [[0]] * num_linhas,
              )
            registrar_log(
                st.session_state["admin_logado"],
                f"Criou a coluna de Liga '{proxima_liga}'",
            )
            st.cache_data.clear()
            st.success(f"✅ Coluna **{proxima_liga}** adicionada com sucesso!")
            st.rerun()

      with c_col3:
        if st.button("➕ Criar Próxima Raide (Raide_X)"):
          headers = sheet_dados.row_values(1)
          proxima_raide = obter_proxima_coluna_sequencial("Raide", headers)
          if proxima_raide in headers:
            st.error(f"⚠️ A coluna {proxima_raide} já existe!")
          else:
            proxima_col_num = len(headers) + 1
            sheet_dados.update_cell(1, proxima_col_num, proxima_raide)
            if not df.empty:
              num_linhas = len(df)
              sheet_dados.update(
                  f"{gspread.utils.rowcol_to_a1(2, proxima_col_num)}:{gspread.utils.rowcol_to_a1(num_linhas + 1, proxima_col_num)}",
                  [[0]] * num_linhas,
              )
            registrar_log(
                st.session_state["admin_logado"],
                f"Criou a coluna de Raide '{proxima_raide}'",
            )
            st.cache_data.clear()
            st.success(
                f"✅ Coluna **{proxima_raide}** adicionada com sucesso!"
            )
            st.rerun()

      st.divider()
      st.markdown("#### ✏️ Edição de Pontos dos Jogadores")
      if not df.empty:
        df_editavel = df.drop(
            columns=["Total", "WarTotal"], errors="ignore"
        ).copy()
        df_editado = st.data_editor(
            df_editavel, use_container_width=True, hide_index=True
        )

        if st.button("💾 Salvar Alterações em Lote", type="primary"):
          novos_dados = [df_editado.columns.tolist()] + df_editado.values.tolist()
          sheet_dados.clear()
          sheet_dados.update("A1", novos_dados)
          registrar_log(
              st.session_state["admin_logado"],
              "Atualizou pontuações dos jogadores em lote",
          )
          st.cache_data.clear()
          st.success("✅ Pontuações salvas com sucesso!")
          st.rerun()

    with sub_tab4:
      st.markdown("#### 📢 Mural da Liderança")
      novo_mural = st.text_area("Mensagem do Mural", value=mural_recado)
      if st.button("💾 Salvar Recado do Mural"):
        cell = sheet_estado.find("mural_recado")
        if cell:
          sheet_estado.update_cell(cell.row, 2, novo_mural)
        else:
          sheet_estado.append_row(["mural_recado", novo_mural])
        registrar_log(
            st.session_state["admin_logado"], "Atualizou recado do mural"
        )
        st.cache_data.clear()
        st.success("✅ Mural atualizado com sucesso!")
        st.rerun()

      st.divider()
      st.markdown("#### 🏁 Finalização e Arquivamento do Mês")
      col_m1, col_m2 = st.columns(2)

      with col_m1:
        if st.button("🔒 Marcar Mês como Finalizado"):
          cell = sheet_estado.find("mes_finalizado")
          if cell:
            sheet_estado.update_cell(cell.row, 2, "TRUE")
          else:
            sheet_estado.append_row(["mes_finalizado", "TRUE"])

          if len(df_rank) >= 3:
            mes_ano_str = datetime.now().strftime("%B/%Y").capitalize()
            sheet_fama.append_row([
                mes_ano_str,
                df_rank.iloc[0]["Nome"],
                df_rank.iloc[1]["Nome"],
                df_rank.iloc[2]["Nome"],
            ])

          registrar_log(
              st.session_state["admin_logado"],
              "Finalizou o mês e salvou galeria da fama",
          )
          st.cache_data.clear()
          st.success("✅ Mês finalizado com sucesso!")
          st.rerun()

      with col_m2:
        if st.button("🔓 Reabrir Mês Atual"):
          cell = sheet_estado.find("mes_finalizado")
          if cell:
            sheet_estado.update_cell(cell.row, 2, "FALSE")
            registrar_log(
                st.session_state["admin_logado"], "Reabriu o mês atual"
            )
            st.cache_data.clear()
            st.success("✅ Mês reaberto para edições!")
            st.rerun()

    with sub_tab5:
      st.markdown("#### 📜 Logs do Sistema")
      try:
        logs_dados = sheet_logs.get_all_records()
        if logs_dados:
          st.dataframe(
              pd.DataFrame(logs_dados).iloc[::-1], use_container_width=True
          )
        else:
          st.info("Nenhum log registrado até o momento.")
      except Exception:
        st.error("Erro ao carregar logs.")

    with sub_tab6:
      st.markdown("#### 💾 Backup e Exportação de Dados")
      if not df.empty:
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Baixar Backup em CSV",
            data=csv,
            file_name=f"winningwars_backup_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with sub_tab7:
      st.markdown("#### 🎲 Sorteio de Desempate (1º Lugar)")
      if not df.empty and "Total" in df.columns:
        maior_pontuacao = df_rank["Total"].max()
        empatados_topo = df_rank[df_rank["Total"] == maior_pontuacao]
        lista_empatados = empatados_topo["Nome"].tolist()
        qtd_empatados = len(lista_empatados)

        if qtd_empatados <= 1:
          st.success(
              "✅ **Não há empate no 1º lugar!** O líder isolado é:"
              f" **{df_rank.iloc[0]['Nome']}**."
          )
        else:
          st.warning(
              f"⚠️ **Empate Detectado!** Existem **{qtd_empatados} jogadores**"
              f" empatados no topo com {int(maior_pontuacao)} pontos."
          )

          st.markdown("### 👥 Jogadores Participantes do Sorteio:")
          cols_participantes = st.columns(min(qtd_empatados, 4))
          for idx, nome_p in enumerate(lista_empatados):
            with cols_participantes[idx % 4]:
              st.markdown(
                  f"""
                        <div style="background-color: #1e293b; border: 2px solid #facc15; border-radius: 10px; padding: 12px; text-align: center; margin-bottom: 10px;">
                            <span style="font-size: 1.2rem; font-weight: bold; color: #facc15;">🏆 {nome_p}</span>
                        </div>
                        """,
                  unsafe_allow_html=True,
              )

          st.write("---")
          if st.button("🎲 REALIZAR SORTEIO DE DESEMPATE", type="primary"):
            with st.spinner("🌀 Girando a roleta de desempate..."):
              time.sleep(1.8)
              vencedor_sorteio = random.choice(lista_empatados)

            st.balloons()
            st.markdown(
                f"""
                    <div style="background: linear-gradient(135deg, #f59e0b 0%, #b45309 100%); border: 3px solid #fef08a; border-radius: 16px; padding: 25px; text-align: center; margin-top: 15px; box-shadow: 0 8px 30px rgba(245, 158, 11, 0.5);">
                        <h2 style="color: #ffffff !important; font-size: 2.2rem; margin: 0;">🎉 CAMPEÃO DO SORTEIO 🎉</h2>
                        <h1 style="color: #fef08a !important; font-size: 3rem; margin: 10px 0;">👑 {vencedor_sorteio} 👑</h1>
                        <p style="color: #ffffff; font-size: 1.2rem; margin: 0;">Parabéns! Você venceu o desempate oficial do Bilhete Dourado!</p>
                    </div>
                    """,
                unsafe_allow_html=True,
            )

            registrar_log(
                st.session_state["admin_logado"],
                f"Realizou sorteio de desempate. Vencedor: {vencedor_sorteio}",
            )
