# Relatório administrativo — 09/10/2026

Painel Admin → Desempenho dos membros. Acesso validado por `pc_validar_admin` (dono/líder/colíder), na entrada do painel e no renderizador. Não publica alertas administrativos na projeção pública; calcula-os após autorização usando dados de desempenho já disponíveis.

Funcionalidades: período por data de encerramento em Brasília, modalidade, membros da última lista ou todas as contas históricas, busca por nome/tag, filtro de alertas, visão compacta, todas as métricas, CSV e ficha individual. Critérios ajustáveis: mínimo de ataques e referência de triplos. Dados da mesma conta reunidos por tag, nunca por nome.

Guerra/liga: escalações, ataques, escalações sem ataque, ataques disponíveis não usados, triplos, média de estrelas, alvos por faixa de CV, regras/descontos e pontos registrados. Raides: participações registradas, ataques, limite individual informado pela captura, saque, saque por ataque e bônus registrado. Pontuação bloqueada ou ausente não apaga o desempenho no jogo. Não inferir ausência no raide pela lista atual de membros. Não penalizar membro não escalado.

Somente documentos de atividades encerradas e não futuras (APLICADO/AGUARDANDO_LANCAMENTO). Atividades duplicadas são excluídas. Filtros não gravam nenhum dado. CSV protege valores textuais iniciados por caracteres de fórmula. Datas, nomes especiais, conta sem amostra, limite desconhecido e diferentes limites de raide têm testes.

Enriquecimento de `detalhes_atividade.py`: preserva da captura validada o limite de ataques, percentual de destruição, adversário, rodada e pontos originais. Não altera cálculo, validação do lançamento ou motor de inscrição. Os mesmos documentos históricos são recalculados pelo observador, mantendo versões anteriores no SQLite. Não exige consultas extras à Supercell/Sheets por visita.

Limites: sem dados de tropas utilizadas, reservas, doações, Jogos/colaboração ou presença histórica completa no clã. Saque/ataque e triplos não são julgamento automático de colaboração; contexto e CV importam. Amostra pequena é destacada. Lista atual pode atrasar oito horas; legenda mostra horário. Registros pendentes não contam como pontuação atribuída. Critérios não alteram participação nem ranking.

Base de implantação: commit 8d68dcc, preservando atualizações de outubro feitas em outra sessão. 55 testes de regressão/regras passaram, mais AppTest com dados reais e cinco testes do motor na Oracle. Conferência real: seis rodadas da liga e um raide, 230 registros de jogadores, nenhum limite ausente após publicação, nenhum registro inconsistente. Rank/EstadoMes/ControleAtividades tiveram hashes idênticos antes/depois.

Backup remoto: `/opt/winning-wars-api/dados_consulta/backup_relatorio_20261009T135809Z` (módulo anterior e SQLite consistente). Modificado apenas o módulo do observador; motores de pontuação preservados. Temporizador de consultas retomado. Para reversão, reverter a interface e restaurar apenas o módulo anterior com o observador ocioso; não restaurar banco antigo sobre histórico novo.

Artefatos locais de homologação fora do Git: `relatorio_desempenho/leitura_antes.json`, `leitura_depois.json`, `homologar.py`, `testar_interface.py` e scripts de implantação.
