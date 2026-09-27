"""Interface do lancamento manual integrado."""
import uuid
from datetime import datetime, timezone
from .manual import fotografar, preparar, conferir
from .participacao_competicao import pc_validar_admin, pc_estado, pc_ler_eventos


def renderizar(st, planilha, ranking, usuario, backup, limpar):
    st.markdown("### Jogos do Clã e Eventos")
    st.caption("Outubro/2026 em diante · Informe o resultado por tag. O primeiro resultado positivo inscreve a conta automaticamente.")
    chave = "ww_manual_integrado_v1"
    sessao = st.session_state.setdefault(chave, {})
    try:
        if sessao.get("pendente"):
            st.warning("Há um envio aguardando conferência. Não envie novamente.")
            if st.button("Conferir envio", key="ww_manual_conferir"):
                foto, _ = fotografar(planilha, ranking.title)
                pc_validar_admin(foto["admins"]["valores"], usuario)
                conferir(foto, sessao["pendente"])
                sessao.clear()
                limpar()
                st.success("Lançamento confirmado, sem novo envio.")
            return
        if st.button("Carregar / atualizar contas", key="ww_manual_carregar"):
            foto, metas = fotografar(planilha, ranking.title)
            pc_validar_admin(foto["admins"]["valores"], usuario)
            sessao.clear()
            sessao.update(foto=foto, metas=metas)
        if "foto" not in sessao:
            st.info("Carregue as contas para iniciar o lançamento.")
            return
        foto, metas = sessao["foto"], sessao["metas"]
        pc_validar_admin(foto["admins"]["valores"], usuario)
        contas = pc_estado(pc_ler_eventos(foto["participacao"]["valores"]))
        opcoes = sorted(contas) + ["Outra tag"]
        with st.form("ww_manual_form"):
            conta = st.selectbox("Conta", opcoes, format_func=lambda t:
                t if t == "Outra tag" else contas[t]["Nome"] + " — " + t + (" · bloqueada" if contas[t]["Habilitada"] == "FALSE" else ""))
            tag_nova = st.text_input("Tag, somente se escolheu Outra tag")
            nome_novo = st.text_input("Nome da vila, somente para Outra tag")
            atividade = st.selectbox("Atividade", ["JogosCla", "Eventos"],
                format_func=lambda a: "Jogos do Clã" if a == "JogosCla" else "Eventos")
            valor = st.number_input("Total obtido nos Jogos do Clã ou total de pontos da competição em Eventos", min_value=0, max_value=1000000, step=1)
            st.caption("Jogos: menos de 2.000 = 0 · 2.000–3.999 = 2 · 4.000–9.999 = 5 · 10.000 = 10. O lançamento substitui o total da conta nesta atividade; não soma novamente.")
            criar = st.form_submit_button("Conferir lançamento")
        if criar:
            tag = tag_nova.strip().upper() if conta == "Outra tag" else conta
            nome = nome_novo.strip() if conta == "Outra tag" else contas[conta]["Nome"]
            sessao.pop("proposta", None)
            p = preparar(foto, metas, usuario, tag, nome, atividade, int(valor),
                str(uuid.uuid4()), datetime.now(timezone.utc).isoformat())
            if p["status"] == "ZERO_SEM_INSCRICAO":
                st.info("Resultado de zero pontos. Nenhum cadastro ou inscrição será criado.")
            else:
                sessao["proposta"] = p
        if sessao.get("proposta"):
            p = sessao["proposta"]
            st.write({"Conta": p["nome"], "Tag": p["tag"], "Temporada": p["temporada"],
                "Atividade": p["atividade"], "Informado": p["valor"], "Antes": p["antes"],
                "Depois": p["pontos"], "Novos cadastros": p["novos"]})
            if st.button("Confirmar e salvar este lançamento", key="ww_manual_salvar", type="primary"):
                atual, metas_atuais = fotografar(planilha, ranking.title)
                pc_validar_admin(atual["admins"]["valores"], usuario)
                if atual != foto or metas_atuais != metas:
                    sessao.clear()
                    raise ValueError("Os dados mudaram. Carregue as contas e confira uma nova proposta.")
                # Backup existente do app; falha interrompe antes dos pontos.
                backup()
                atual, metas_atuais = fotografar(planilha, ranking.title)
                pc_validar_admin(atual["admins"]["valores"], usuario)
                if atual != foto or metas_atuais != metas:
                    sessao.clear()
                    raise ValueError("Os dados mudaram após o backup. Refaça a proposta.")
                sessao["pendente"] = p
                planilha.batch_update(p["lote"])
                depois, _ = fotografar(planilha, ranking.title)
                conferir(depois, p)
                sessao.clear()
                limpar()
                st.success("Pontos, inscrição e auditoria registrados e conferidos.")
                st.info("Atualize a página para visualizar o ranking atualizado.")
        st.caption("A auditoria destes lançamentos fica na aba LancamentosManuais da planilha.")
    except Exception as erro:
        st.error(str(erro))
