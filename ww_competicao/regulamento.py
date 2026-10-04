"""Regulamento publico alinhado aos motores de outubro de 2026."""

def renderizar_regulamento(st):
    st.markdown("### 📖 Regras completas — a partir de outubro/2026")
    st.caption("As regras abaixo explicam a pontuação da competição. A liderança continua definindo os alvos e a estratégia do clã.")
    with st.expander("👥 Quem participa e quando os pontos entram"):
        st.markdown("""
- Entrar no clã, por si só, não coloca a conta no ranking. A primeira **pontuação válida e positiva** cria a participação na temporada e já inclui esses pontos, mesmo para quem chegou durante o mês.
- A identificação é feita pela **tag da vila**. O nome pode mudar; contas com nomes diferentes não são automaticamente reconhecidas como sendo da mesma pessoa.
- A competição é destinada à conta principal. Os administradores habilitam ou bloqueiam contas pelo painel de participação, inclusive em lote, para administrar contas secundárias.
- Conta bloqueada não recebe novos lançamentos pela integração. O bloqueio **não apaga pontos anteriores**; habilitar também não concede pontos retroativos por si só.
- Somente atividades do **Winning Wars (#YVLGUJQY)** pontuam nesta integração. Atividades de outro clã, inclusive do clã secundário, não pontuam aqui.
- Guerra, Liga e Raide são lançados automaticamente **após o encerramento**, a validação dos dados e uma consulta do motor. Resultados em andamento são parciais e não são lançados automaticamente.
- A temporada dessas atividades é definida pela **data de início no horário de Brasília**. Uma atividade iniciada em setembro não pontua em outubro só porque terminou depois da virada. A temporada correspondente precisa estar aberta.
- Uma mesma atividade não deve gerar um segundo lançamento. Divergências de dados ou de pontos já registrados exigem revisão, sem sobrescrever silenciosamente uma correção manual.
""")
    with st.expander("⚔️ Guerras: melhor ataque, níveis de CV e vilas fechadas"):
        st.markdown("""
Vale o **melhor resultado entre os ataques**, com máximo de **3 pontos por guerra**. Os ataques não são somados. Um ataque ruim posterior não tira os pontos do melhor ataque.

| Alvo em relação ao seu CV | Pontuação do ataque |
|---|---|
| Mesmo CV, qualquer CV superior ou 1 nível abaixo | Cada estrela vale 1 ponto |
| 2 ou mais níveis abaixo, com alternativa aberta na faixa permitida | Zero |
| 2 ou mais níveis abaixo, sem alternativa aberta na faixa permitida | Estrelas menos 1, com mínimo de zero |

**Alternativa aberta** é uma base adversária que ainda não tinha recebido 3 estrelas no momento do ataque e cujo CV está **1 nível abaixo, igual ou 1 nível acima do atacante**. Uma base com 2 estrelas ainda está aberta. O cálculo considera a ordem dos ataques de todos os membros, inclusive dos que não participam da competição.

**Atacar uma vila já fechada continua pontuando**, conforme a tabela. Isso também vale quando todas as bases já estão fechadas.

Exemplos: 3 estrelas em CV igual = **3 pontos**; 3 estrelas em CV 2 níveis abaixo, sem alternativa aberta = **2 pontos**; nesse mesmo alvo, com alternativa aberta = **zero**. Com desconto, 2 estrelas valem 1 ponto e 1 estrela vale zero.
""")
    with st.expander("🏆 Liga (CWL): pontuação por rodada"):
        st.markdown("""
Cada rodada vale até **3 pontos**:

| Resultado do ataque | Pontos |
|---|---:|
| 3 estrelas | 3 |
| 2 estrelas contra CV superior ao seu | 3 |
| 2 estrelas contra CV igual ou inferior | 2 |
| 1 estrela | 1 |
| Zero estrelas ou nenhum ataque | 0 |

A regra de desconto por CV das guerras comuns **não é aplicada à Liga**. O bônus de duas estrelas contra CV superior **não autoriza subir ataque**: siga o alvo definido pela liderança. Cada guerra da Liga é identificada separadamente para evitar repetição de pontos.
""")
    with st.expander("🛡️ Raides: ataques, saque, Top 3 e empate"):
        st.markdown("""
- Cada ataque realizado vale **1 ponto**, até **6 pontos**. O ataque extra também entra nessa contagem.
- Os **três maiores saques individuais** entre as contas elegíveis que atacaram recebem **+1 ponto cada**. O máximo é **7 pontos por fim de semana**.
- O Top 3 é definido pelo **saque**, não pela quantidade de ataques. Contas bloqueadas ou não elegíveis não ocupam essas vagas.
- Se houver menos de três contas elegíveis com ataques, o bônus é atribuído às disponíveis.
- Se houver empate de saque entre a terceira posição e quem ficou de fora, **todo o lançamento fica pendente de revisão**. O sistema não escolhe um vencedor arbitrariamente.
- Sem ataques: zero pontos e nenhum bônus.
""")
    with st.expander("🎯 Jogos do Clã: faixas de pontuação"):
        st.markdown("""
| Pontos realizados nos Jogos | Pontos na competição |
|---|---:|
| 10.000 | 10 |
| 4.000 a 9.999 | 5 |
| 2.000 a 3.999 | 2 |
| 0 a 1.999 | 0 |

O administrador informa o total realizado nos Jogos e o app converte para a faixa correspondente. **Atualizar esse total substitui a pontuação anterior de Jogos; não soma as faixas.**

O lançamento é manual pelo painel integrado, com identificação por tag, inscrição na primeira pontuação positiva e auditoria. Medidas disciplinares por participação insuficiente são decididas pela liderança; o app não expulsa jogadores automaticamente.
""")
    with st.expander("🕹️ Eventos de colaboração: meta e bônus"):
        st.markdown("""
Atingir a meta individual definida para o evento vale **10 pontos**. Cada integrante do **Top 3** recebe **+1 ponto**.

A meta individual é calculada dividindo o **objetivo total do evento pelo número de membros do clã**. A liderança deve divulgar o valor aplicado e esclarecer arredondamentos e desempates antes da apuração.

**A apuração de meta e Top 3 é feita pela administração.** O app não coleta nem calcula automaticamente esses dados do evento. No painel integrado, o administrador informa o **total de pontos de Eventos na temporada**: salvar substitui o total anterior, em vez de acrescentar um novo valor. Havendo mais de um evento, o total informado deve incluir os anteriores.

O lançamento registra responsável, valor anterior e novo, e permite a inscrição na primeira pontuação válida.
""")
    with st.expander("🔎 Como consultar pontos e históricos"):
        st.markdown("""
**Todos os membros:** consulte o ranking e a Tabela Detalhada da temporada. Para entender um lançamento específico, abra **Meu Perfil → Meu desempenho por atividade**, escolha sua vila e a atividade. O app mostra os pontos oficiais, ataque, alvo, estrelas e a regra aplicada. A mesma explicação está em **Atividades encerradas**. Em **Meses Anteriores**, consulte as temporadas já arquivadas.

**Administradores:** em **Painel Admin → Gestão 2.0 → Auditoria**, existem três consultas:

- **Atividades automáticas:** guerras, rodadas da Liga e raides lançados pelo novo motor. Filtre por temporada, tipo e status; escolha **Ver registro completo** e abra **Detalhes do processamento** para consultar os dados registrados, incluindo os pontos por participante.
- **Jogos e eventos:** lançamentos manuais integrados, com responsável e valores antes/depois.
- **Alterações anteriores:** histórico de alterações do sistema anterior.

A auditoria automática mostra **lançamentos concluídos**, não atividades ainda em andamento. Desde outubro, guerras e Liga exibem ao jogador os ataques usados no cálculo; raides exibem ataques, saque e bônus. Históricos antigos guardados na Oracle não são importados automaticamente para essa consulta. Se uma atividade não foi lançada ou ficou pendente de revisão, ela pode ainda não aparecer nessa lista.
""")
