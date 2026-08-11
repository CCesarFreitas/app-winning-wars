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
    sheet_admins.append_row(["Lenda", gerar_hash(SENHA_ADMIN_INICIAL)])

  # Aba de Notícias (Feed)
  try:
    sheet_noticias = spreadsheet.worksheet("Noticias")
  except gspread.WorksheetNotFound:
    sheet_noticias = spreadsheet.add_worksheet(
        title="Noticias", rows="100", cols="5"
    )
    sheet_noticias.append_row(
        ["DataHora", "Autor", "Titulo", "Conteudo", "ImagemUrl"]
    )

  # Aba de Logs de Moderação
  try:
    sheet_logs = spreadsheet.worksheet("Logs")
  except gspread.WorksheetNotFound:
    sheet_logs = spreadsheet.add_worksheet(title="Logs", rows="500", cols="3")
    sheet_logs.append_row(["DataHora", "Admin", "Acao"])

  # Aba de Desafios de Layout
  try:
    sheet_desafios = spreadsheet.worksheet("Desafios")
  except gspread.WorksheetNotFound:
    sheet_desafios = spreadsheet.add_worksheet(
        title="Desafios", rows="100", cols="4"
    )
    sheet_desafios.append_row(["CV", "LinkLayout", "Premio", "Autor"])

  # Aba de Recrutamento
  try:
    sheet_recrutamento = spreadsheet.worksheet("Recrutamento")
  except gspread.WorksheetNotFound:
    sheet_recrutamento = spreadsheet.add_worksheet(
        title="Recrutamento", rows="200", cols="8"
    )
    sheet_recrutamento.append_row([
        "DataHora",
        "Nome",
        "Tag",
        "CV",
        "Herois",
        "Disponibilidade",
        "FotoPerfil",
        "Status",
    ])

  # Aba de Estratégias
  try:
    sheet_estrategias = spreadsheet.worksheet("Estrategias")
  except gspread.WorksheetNotFound:
    sheet_estrategias = spreadsheet.add_worksheet(
        title="Estrategias", rows="100", cols="6"
    )
    sheet_estrategias.append_row(
        ["CV", "Nome", "Autor", "Descricao", "YoutubeUrl", "Exército"]
    )

  # Aba de Membros
  try:
    sheet_membros = spreadsheet.worksheet("Membros")
  except gspread.WorksheetNotFound:
    sheet_membros = spreadsheet.add_worksheet(
        title="Membros", rows="100", cols="5"
    )
    sheet_membros.append_row(["Nome", "Tag", "Cargo", "CV", "Status"])

  # Aba de Layouts
  try:
    sheet_layouts = spreadsheet.worksheet("Layouts")
  except gspread.WorksheetNotFound:
    sheet_layouts = spreadsheet.add_worksheet(
        title="Layouts", rows="200", cols="7"
    )
    sheet_layouts.append_row([
        "Tipo",
        "CV",
        "Autor",
        "Link",
        "Tags",
        "ImagemUrl",
        "DownloadCount",
    ])

  return (
      sheet_dados,
      sheet_admins,
      sheet_noticias,
      sheet_logs,
      sheet_desafios,
      sheet_recrutamento,
      sheet_estrategias,
      sheet_membros,
      sheet_layouts,
  )


try:
  (
      sheet_dados,
      sheet_admins,
      sheet_noticias,
      sheet_logs,
      sheet_desafios,
      sheet_recrutamento,
      sheet_estrategias,
      sheet_membros,
      sheet_layouts,
  ) = conectar_banco()
except Exception as e:
  st.error(
      "❌ Erro ao conectar ao Google Sheets. Verifique suas credenciais nos"
      f" Secrets do Streamlit.\n\nDetalhes do erro: {e}"
  )
  st.stop()


def registrar_log(admin: str, acao: str):
  try:
    dh = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet_logs.append_row([dh, admin, acao])
  except Exception:
    pass


# CARREGAMENTO DE DADOS COM CACHE
@st.cache_data(ttl=60)
def carregar_noticias():
  try:
    data = sheet_noticias.get_all_records()
    return pd.DataFrame(data)
  except Exception:
    return pd.DataFrame()


@st.cache_data(ttl=60)
def carregar_desafios():
  try:
    data = sheet_desafios.get_all_records()
    return pd.DataFrame(data)
  except Exception:
    return pd.DataFrame()


@st.cache_data(ttl=60)
def carregar_recrutamento():
  try:
    data = sheet_recrutamento.get_all_records()
    return pd.DataFrame(data)
  except Exception:
    return pd.DataFrame()


@st.cache_data(ttl=60)
def carregar_estrategias():
  try:
    data = sheet_estrategias.get_all_records()
    return pd.DataFrame(data)
  except Exception:
    return pd.DataFrame()


@st.cache_data(ttl=60)
def carregar_membros():
  try:
    data = sheet_membros.get_all_records()
    return pd.DataFrame(data)
  except Exception:
    return pd.DataFrame()


@st.cache_data(ttl=60)
def carregar_layouts():
  try:
    data = sheet_layouts.get_all_records()
    return pd.DataFrame(data)
  except Exception:
    return pd.DataFrame()


df_noticias = carregar_noticias()
df_desafios = carregar_desafios()
df_recrutamento = carregar_recrutamento()
df_estrategias = carregar_estrategias()
df_membros = carregar_membros()
df_layouts = carregar_layouts()


# --- DESIGN CSS PERSONALIZADO ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;700;800;900&display=swap');
    
    html, body, [class*="css"], [class*="st-"] {
        font-family: 'Nunito', sans-serif;
    }
    
    .stApp {
        background-color: #0b0f19;
        color: #f1f5f9;
    }
    
    /* Header Personalizado */
    .hero-container {
        background: linear-gradient(135deg, #1e1b4b 0%, #311042 50%, #0f172a 100%);
        border: 2px solid #6366f1;
        border-radius: 16px;
        padding: 25px;
        text-align: center;
        box-shadow: 0 10px 25px rgba(99, 102, 241, 0.25);
        margin-bottom: 25px;
    }
    .hero-title {
        font-size: 2.8rem;
        font-weight: 900;
        color: #ffffff;
        text-shadow: 0 0 15px rgba(168, 85, 247, 0.6);
        margin-bottom: 5px;
    }
    .hero-subtitle {
        font-size: 1.1rem;
        color: #cbd5e1;
        font-weight: 700;
    }
    
    /* Menu Central */
    .menu-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .menu-card:hover {
        transform: translateY(-3px);
        border-color: #818cf8;
    }

    /* Botão Flutuante Pix */
    .pix-widget {
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 9999;
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 12px 20px;
        border-radius: 50px;
        box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
        font-weight: 800;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 8px;
        text-decoration: none;
    }
    
    .btn-scid {
        display: block;
        width: 100%;
        background-color: #1e293b;
        color: #facc15 !important;
        text-align: center;
        padding: 10px;
        border-radius: 8px;
        font-weight: 800;
        text-decoration: none;
        border: 1px solid #facc15;
        transition: 0.2s;
    }
    .btn-scid:hover {
        background-color: #facc15;
        color: #0f172a !important;
    }

    .btn-youtube-link {
        display: block;
        width: 100%;
        background-color: #dc2626;
        color: #ffffff !important;
        text-align: center;
        padding: 10px;
        border-radius: 8px;
        font-weight: 800;
        text-decoration: none;
        border: 1px solid #ef4444;
        transition: 0.2s;
    }
    .btn-youtube-link:hover {
        background-color: #b91c1c;
        color: #ffffff !important;
    }
    
    /* Layout Cards & Buttons */
    .btn-layout-copy {
        display: block;
        width: 100%;
        background-color: #10b981;
        color: #ffffff !important;
        text-align: center;
        padding: 12px;
        border-radius: 8px;
        font-weight: 800;
        text-decoration: none;
        margin-top: 8px;
        font-size: 1.1rem;
        box-shadow: 0 4px 10px rgba(16, 185, 129, 0.3);
        transition: 0.2s;
    }
    .btn-layout-copy:hover {
        background-color: #059669;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1e293b;
        border-radius: 8px 8px 0 0;
        color: #cbd5e1;
        font-weight: 700;
        padding: 10px 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4f46e5 !important;
        color: #ffffff !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Inicializar Estado de Navegação
if "pagina_atual" not in st.session_state:
  st.session_state["pagina_atual"] = "principal"


# ==============================================================================
# FUNÇÃO PARA RENDERIZAR PÁGINAS DE LAYOUT (OTIMIZADA V16)
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
                <img src="{th_img_url}" width="90" height="auto" loading="lazy" decoding="async" style="filter: drop-shadow(0px 4px 8px rgba(0,0,0,0.5));">
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
                # Otimização v16: Lazy Loading, Decoding Assíncrono, Container Mínimo, Placeholder e Fallback
                st.markdown(
                    f"""
                    <div class="layout-image-wrap" style="position: relative; width: 100%; min-height: 220px; background-color: #0f172a; border-radius: 12px; border: 2px solid #334155; box-shadow: 0 6px 16px rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; margin-bottom: 12px; overflow: hidden;">
                        <div class="layout-placeholder" style="position: absolute; color: #facc15; font-weight: 800; font-family: 'Nunito', sans-serif; font-size: 0.95rem; z-index: 1;">
                            ⏳ Carregando layout...
                        </div>
                        <img src="{img_url_limpa}" 
                             alt="Layout {cv_nome}" 
                             loading="lazy" 
                             decoding="async" 
                             width="100%" 
                             height="auto"
                             style="width: 100%; height: auto; max-width: 100%; border-radius: 10px; display: block; position: relative; z-index: 2; transition: opacity 0.3s ease;"
                             onload="this.previousElementSibling.style.display='none';" 
                             onerror="this.style.display='none'; this.previousElementSibling.innerText='🖼️ Imagem indisponível';">
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


# ROUTER DE PÁGINAS
if st.session_state["pagina_atual"] == "layouts_guerra":
  renderizar_pagina_layouts("Guerra", "🛡️ Layouts de Guerra")
  st.stop()
elif st.session_state["pagina_atual"] == "layouts_farm":
  renderizar_pagina_layouts("Farm", "🚜 Layouts de Farm")
  st.stop()
elif st.session_state["pagina_atual"] == "layouts_push":
  renderizar_pagina_layouts("Push", "🏆 Layouts de Push")
  st.stop()
elif st.session_state["pagina_atual"] == "layouts_cwl":
  renderizar_pagina_layouts("Rankeada", "⚔️ Layouts Rankeada (CWL)")
  st.stop()
elif st.session_state["pagina_atual"] == "layouts_divertidos":
  renderizar_pagina_layouts("Divertidos", "🎨 Layouts Divertidos / Artísticos")
  st.stop()


# --- PÁGINA DE REGRAS DO CLÃ ---
if st.session_state["pagina_atual"] == "regras_cla":
  if st.button("⬅️ Voltar ao Início"):
    st.session_state["pagina_atual"] = "principal"
    st.rerun()

  st.markdown(
      "<h1 style='text-align: center; color: #facc15;'>📜 Diretrizes & Regras"
      " Oficiais - Winning Wars</h1>",
      unsafe_allow_html=True,
  )

  st.markdown(
      """
    <div style="background-color: #1e293b; padding: 25px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 20px;">
        <h3 style="color: #a855f7;">1. Respeito e Convivência</h3>
        <p>O respeito mútuo é a base do nosso clã. Comportamentos tóxicos, ofensas ou discriminação não serão tolerados.</p>
        
        <h3 style="color: #a855f7;">2. Guerras de Clãs (CW)</h3>
        <ul>
            <li>Manter os dois ataques sempre feitos, respeitando as orientações enviadas no correio ou grupo.</li>
            <li>Se o seu rei/rainha estiver em melhoria, sinalize no perfil mudando o escudo para VERMELHO.</li>
        </ul>

        <h3 style="color: #a855f7;">3. Liga de Guerras (CWL)</h3>
        <ul>
            <li>Na CWL, falhar o ataque sem justificativa prévia pode resultar em rebaixamento ou exclusão do clã.</li>
            <li>Ataques devem priorizar o plano estratégico estabelecido pela liderança.</li>
        </ul>

        <h3 style="color: #a855f7;">4. Doações de Tropas</h3>
        <ul>
            <li>Mantenha um equilíbrio saudável de doações/pedidos.</li>
            <li>Apenas doe o que for especificamente pedido. Tropas erradas atrapalham defesas e ataques.</li>
        </ul>
    </div>
    """,
      unsafe_allow_html=True,
  )
  st.stop()

# --- PÁGINA DE ESTRATÉGIAS ---
if st.session_state["pagina_atual"] == "estrategias":
  if st.button("⬅️ Voltar ao Início"):
    st.session_state["pagina_atual"] = "principal"
    st.rerun()

  st.markdown(
      "<h1 style='text-align: center; color: #38bdf8;'>🧠 Central de"
      " Estratégias & Ataques</h1>",
      unsafe_allow_html=True,
  )
  eh_admin = "admin_logado" in st.session_state

  if eh_admin:
    with st.expander("➕ [ADMIN] Cadastrar Nova Estratégia"):
      with st.form("form_estrategia", clear_on_submit=True):
        cv_est = st.selectbox(
            "Centro de Vila Target",
            ["CV 18", "CV 17", "CV 16", "CV 15", "CV 14", "CV 13", "CV 12"],
        )
        nome_est = st.text_input("Nome do Ataque / Estratégia")
        desc_est = st.text_area("Descrição / Dicas de Execução")
        yt_est = st.text_input("Link do Vídeo no YouTube (Opcional)")
        btn_est = st.form_submit_button("Publicar Estratégia")

        if btn_est:
          if nome_est.strip():
            sheet_estrategias.append_row([
                cv_est,
                nome_est.strip(),
                st.session_state["admin_logado"],
                desc_est.strip(),
                yt_est.strip(),
                "",
            ])
            registrar_log(
                st.session_state["admin_logado"],
                f"Adicionou estratégia {nome_est} para {cv_est}",
            )
            st.cache_data.clear()
            st.success("Estratégia salva com sucesso!")
            st.rerun()

  if not df_estrategias.empty:
    cv_sel = st.selectbox(
        "Filtrar por CV:",
        ["Todos", "CV 18", "CV 17", "CV 16", "CV 15", "CV 14", "CV 13", "CV 12"],
    )
    filtradas = df_estrategias
    if cv_sel != "Todos":
      filtradas = filtradas[filtradas["CV"] == cv_sel]

    for item_idx, r in filtradas.iterrows():
      st.markdown(
          f"""
        <div style="background-color: #1e293b; padding: 20px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 15px;">
            <h3 style="color: #facc15; margin-top: 0;">{r['Nome']} <span style="font-size: 0.9rem; color: #94a3b8;">({r['CV']})</span></h3>
            <p><b>Postado por:</b> {r['Autor']}</p>
            <p>{r['Descricao']}</p>
        </div>
        """,
          unsafe_allow_html=True,
      )
      if str(r["YoutubeUrl"]).strip():
        st.video(str(r["YoutubeUrl"]).strip())

      if eh_admin:
        if st.button(
            "❌ Excluir Estratégia",
            key=f"del_est_{item_idx}",
            use_container_width=True,
        ):
          cell = sheet_estrategias.find(r["Nome"])
          if cell:
            sheet_estrategias.delete_rows(cell.row)
            registrar_log(
                st.session_state["admin_logado"],
                f"Excluiu estratégia {r['Nome']}",
            )
            st.cache_data.clear()
            st.success("Estratégia removida!")
            st.rerun()
      st.divider()
  else:
    st.info("Nenhuma estratégia cadastrada no momento.")
  st.stop()


# --- PÁGINA DE RECRUTAMENTO ---
if st.session_state["pagina_atual"] == "recrutamento":
  if st.button("⬅️ Voltar ao Início"):
    st.session_state["pagina_atual"] = "principal"
    st.rerun()

  st.markdown(
      "<h1 style='text-align: center; color: #10b981;'>🛡️ Recrutamento -"
      " Winning Wars</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='text-align: center;'>Preencha o formulário abaixo para enviar"
      " sua solicitação de entrada ao nosso clã.</p>",
      unsafe_allow_html=True,
  )

  with st.form("form_recrutamento", clear_on_submit=True):
    col_r1, col_r2 = st.columns(2)
    with col_r1:
      rec_nome = st.text_input("Seu Nick no Clash")
      rec_tag = st.text_input("Sua Tag no Clash (#TAG)")
    with col_r2:
      rec_cv = st.selectbox(
          "Nível do Centro de Vila (CV)",
          [
              "CV 18",
              "CV 17",
              "CV 16",
              "CV 15",
              "CV 14",
              "CV 13",
              "CV 12 ou menor",
          ],
      )
      rec_disp = st.selectbox(
          "Disponibilidade para Guerras",
          ["Sempre Disponível", "Apenas CWL", "Finais de Semana"],
      )

    rec_herois = st.text_input("Nível dos Heróis (ex: Rei 95 / Rainha 95)")
    rec_foto = st.text_input("Link de uma foto do perfil (Opcional)")

    btn_rec = st.form_submit_button("📩 Enviar Solicitação")

    if btn_rec:
      if rec_nome.strip() and rec_tag.strip():
        dh = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet_recrutamento.append_row([
            dh,
            rec_nome.strip(),
            rec_tag.strip(),
            rec_cv,
            rec_herois.strip(),
            rec_disp,
            rec_foto.strip(),
            "Pendente",
        ])
        st.cache_data.clear()
        st.success("✅ Solicitação enviada com sucesso! Aguarde nossa análise.")
      else:
        st.error("⚠️ Preencha pelo menos o seu Nick e a sua Tag.")

  st.stop()


# --- HEADER DO APP ---
st.markdown(
    """
<div class="hero-container">
    <div class="hero-title">⚔️ WINNING WARS ⚔️</div>
    <div class="hero-subtitle">Comunidade Oficial, Layouts Pro, Estratégias & Recrutamento</div>
</div>
""",
    unsafe_allow_html=True,
)

# --- BOTÃO PIX SUPORTE ---
st.markdown(
    """
<a href="https://livepix.gg/winningwars" target="_blank" class="pix-widget">
    <span>✨ Apoie o Clã via PIX</span>
</a>
""",
    unsafe_allow_html=True,
)


# --- ÁREA ADMINISTRATIVA NA SIDEBAR ---
with st.sidebar:
  st.markdown("### 🔐 Área Administrativa")

  if "admin_logado" not in st.session_state:
    with st.expander("🔑 Login de Admin"):
      admin_user = st.text_input("Usuário", key="login_user")
      admin_pass = st.text_input("Senha", type="password", key="login_pass")
      if st.button("Entrar", use_container_width=True):
        if admin_user and admin_pass:
          try:
            admins_data = sheet_admins.get_all_records()
            df_admins = pd.DataFrame(admins_data)
            pass_hash = gerar_hash(admin_pass)

            user_match = df_admins[
                (df_admins["Usuario"] == admin_user)
                & (df_admins["SenhaHash"] == pass_hash)
            ]

            if not user_match.empty:
              st.session_state["admin_logado"] = admin_user
              registrar_log(admin_user, "Realizou login")
              st.success(f"Bem-vindo, {admin_user}!")
              st.rerun()
            else:
              st.error("Usuário ou senha incorretos.")
          except Exception as e:
            st.error(f"Erro ao autenticar: {e}")
  else:
    st.success(f"Logado como: **{st.session_state['admin_logado']}**")

    with st.expander("⚙️ Gerenciar Admins"):
      novo_admin = st.text_input("Novo Admin (Usuário)")
      nova_senha = st.text_input(
          "Senha do Novo Admin", type="password", key="new_admin_pass"
      )
      if st.button("Cadastrar Admin", use_container_width=True):
        if novo_admin and nova_senha:
          sheet_admins.append_row([novo_admin.strip(), gerar_hash(nova_senha)])
          registrar_log(
              st.session_state["admin_logado"],
              f"Cadastrou novo admin: {novo_admin}",
          )
          st.success(f"Admin {novo_admin} criado!")
        else:
          st.warning("Preencha todos os campos.")

    with st.expander("📋 Logs de Moderação"):
      try:
        logs_data = sheet_logs.get_all_records()
        df_logs = pd.DataFrame(logs_data)
        if not df_logs.empty:
          st.dataframe(df_logs.iloc[::-1], use_container_width=True)
        else:
          st.info("Nenhum log registrado.")
      except Exception:
        st.info("Logs indisponíveis.")

    if st.button("🔴 Sair da Conta", use_container_width=True):
      registrar_log(st.session_state["admin_logado"], "Realizou logout")
      del st.session_state["admin_logado"]
      st.rerun()


# --- NAVEGAÇÃO PRINCIPAL EM CARDS ---
st.markdown("### 🎯 Navegação Rápida")
c1, c2, c3, c4 = st.columns(4)

with c1:
  if st.button("🛡️ Layouts de Guerra", use_container_width=True):
    st.session_state["pagina_atual"] = "layouts_guerra"
    st.rerun()
  if st.button("⚔️ Layouts Rankeada (CWL)", use_container_width=True):
    st.session_state["pagina_atual"] = "layouts_cwl"
    st.rerun()

with c2:
  if st.button("🚜 Layouts de Farm", use_container_width=True):
    st.session_state["pagina_atual"] = "layouts_farm"
    st.rerun()
  if st.button("🎨 Layouts Divertidos", use_container_width=True):
    st.session_state["pagina_atual"] = "layouts_divertidos"
    st.rerun()

with c3:
  if st.button("🏆 Layouts de Push", use_container_width=True):
    st.session_state["pagina_atual"] = "layouts_push"
    st.rerun()
  if st.button("🧠 Estratégias de Ataque", use_container_width=True):
    st.session_state["pagina_atual"] = "estrategias"
    st.rerun()

with c4:
  if st.button("📩 Recrutamento para Clã", use_container_width=True):
    st.session_state["pagina_atual"] = "recrutamento"
    st.rerun()
  if st.button("📜 Regras do Clã", use_container_width=True):
    st.session_state["pagina_atual"] = "regras_cla"
    st.rerun()

st.divider()

# --- FEED DE NOTÍCIAS & NOVIDADES ---
st.markdown("### 📰 Feed de Notícias do Clã")

if "admin_logado" in st.session_state:
  with st.expander("➕ [ADMIN] Publicar Nova Notícia"):
    with st.form("form_nova_noticia", clear_on_submit=True):
      not_titulo = st.text_input("Título da Notícia")
      not_conteudo = st.text_area("Conteúdo da Notícia")
      not_img = st.text_input("URL da Imagem Banner (Opcional)")
      btn_not = st.form_submit_button("Publicar Notícia")

      if btn_not:
        if not_titulo.strip() and not_conteudo.strip():
          dh = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
          sheet_noticias.append_row([
              dh,
              st.session_state["admin_logado"],
              not_titulo.strip(),
              not_conteudo.strip(),
              not_img.strip(),
          ])
          registrar_log(
              st.session_state["admin_logado"],
              f"Publicou notícia: {not_titulo}",
          )
          st.cache_data.clear()
          st.success("Notícia publicada com sucesso!")
          st.rerun()
        else:
          st.error("Preencha o título e o conteúdo.")

if not df_noticias.empty:
  for idx, row in df_noticias.iloc[::-1].iterrows():
    st.markdown(
        f"""
        <div style="background-color: #1e293b; padding: 20px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 15px;">
            <div style="color: #94a3b8; font-size: 0.85rem; margin-bottom: 5px;">📅 {row['DataHora']} | Por: {row['Autor']}</div>
            <h2 style="color: #facc15; margin-top: 0;">{row['Titulo']}</h2>
            <p style="font-size: 1.05rem; line-height: 1.6;">{row['Conteudo']}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    img_url_noticia = str(row["ImagemUrl"]).strip()
    if img_url_noticia:
      st.markdown(
          f'<img src="{img_url_noticia}" width="100%" loading="lazy"'
          ' decoding="async" style="border-radius: 10px; margin-bottom:'
          ' 15px;">',
          unsafe_allow_html=True,
      )

    if "admin_logado" in st.session_state:
      if st.button(
          "❌ Excluir Notícia", key=f"del_not_{idx}", use_container_width=True
      ):
        cell = sheet_noticias.find(row["Titulo"])
        if cell:
          sheet_noticias.delete_rows(cell.row)
          registrar_log(
              st.session_state["admin_logado"],
              f"Excluiu notícia {row['Titulo']}",
          )
          st.cache_data.clear()
          st.success("Notícia removida!")
          st.rerun()
    st.divider()
else:
  st.info("Nenhuma notícia recente no feed.")

# --- FOOTER / LINKS RÁPIDOS ---
st.divider()
st.markdown(
    "<h3 style='text-align: center;'>🔗 Links Rápidos</h3>",
    unsafe_allow_html=True,
)
c_link1, c_link2, c_link3, c_link4 = st.columns(4)

with c_link1:
  st.markdown(
      '<a href="https://www.youtube.com/@winningwarscoc?sub_confirmation=1"'
      ' target="_blank" rel="noopener noreferrer" class="btn-youtube-link"><img'
      ' src="https://img.cdndsgni.com/preview/10000151.jpg" height="20"'
      ' style="border-radius: 4px; object-fit: cover;"> Canal Winning Wars YT'
      " ↗</a>",
      unsafe_allow_html=True,
  )

with c_link2:
  if st.button(
      "📜 Regras do Clã", use_container_width=True, key="bottom_regras_cla"
  ):
    st.session_state["pagina_atual"] = "regras_cla"
    st.rerun()

with c_link3:
  st.markdown(
      '<a'
      ' href="https://link.clashofclans.com/?action=OpenSCID&p=25-1cb8481f-3a79-4681-90f9-8914acef2d63"'
      ' target="_blank" rel="noopener noreferrer" class="btn-scid"><img'
      ' src="https://i.ibb.co/fzPGy6fr/bg-hero-scid-landing-0.webp" height="20"'
      ' style="border-radius: 4px; object-fit: cover;"> Perfil SCID Lenda ↗</a>',
      unsafe_allow_html=True,
  )

with c_link4:
  if st.button(
      "📩 Recrutamento", use_container_width=True, key="bottom_recrutamento"
  ):
    st.session_state["pagina_atual"] = "recrutamento"
    st.rerun()
