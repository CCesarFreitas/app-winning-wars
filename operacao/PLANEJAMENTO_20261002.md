# Planejamento de guerras — 02/10/2026

Nova aba pública `⚔️ Planejamento de guerras`, com quatro visões: grupo CWL, comparação de vilas, guerras comuns e desempenho.

## Dados e isolamento

- O observador existente `winning-wars-consultas.service` executa `coletar_planejamento.py` com limite de 65 segundos. Sua falha não impede a publicação das demais consultas.
- Somente GET à Supercell; nenhuma chamada de fechamento, inscrição ou envio de pontos.
- Cache compartilhado: grupo 15 minutos, guerras abertas 5 minutos. Máximo de 10 consultas por execução. Guerras encerradas ficam arquivadas e não são consultadas novamente pelo ciclo normal.
- SQLite existente: tipos separados `planejamento`, `planejamento_cache`, `planejamento_guerra`, `planejamento_grupo`.
- Projeção `ConsultaPublica`, documento `planejamento`. Nenhuma nova credencial no navegador.
- A página informa horários, leituras antigas e pendências. Datas não convertem uma guerra em encerrada; prevalece o estado retornado.
- Elenco inscrito e escalação são separados. Na preparação da CWL, `mapPosition` pode ter lacunas e valores maiores que `teamSize`: preservar a posição original, validar unicidade e positividade, não renumerar.
- Taxas são por ataque; estrelas novas consideram apenas o incremento do melhor ataque anterior. Sem ataques aparece como ausência de amostra.
- Composição de tropas não publicada: battlelog comum/ranqueado não é atribuído à CWL.
- Histórico público da competição continua exclusivo de atividades encerradas. O planejamento não modifica suas regras.

## Validação

8 testes novos do coletor/métricas, mais regressões existentes; testes do motor de detalhes mantidos. AppTest com dados reais confirmou renderização, mudança entre elenco/escalação, rodada futura e comparação do próprio clã. Quatro guerras atuais e oito clãs validados na projeção publicada, sem pendências.

Consultas de ranking, EstadoMes e ControleAtividades antes/depois da instalação permaneceram idênticas. A primeira publicação detectou posições não consecutivas na preparação; a validação foi ajustada e a coleta novamente conferida antes de publicar a interface.

## Publicação e reversão

Diretório do observador: `/opt/winning-wars-api/consultas_app_20261002`.

Backup anterior à implementação, incluindo SQLite: `/opt/winning-wars-api/dados_consulta/backup_planejamento_20261002T190032Z`.

Backup anterior ao ajuste da preparação: `/opt/winning-wars-api/dados_consulta/backup_planejamento_20261002T224505Z`.

Para desativar apenas esta funcionalidade: reverter o commit da interface; restaurar `operacao/publicar_consultas.py` do primeiro backup com o observador parado e retomar somente seu temporizador. Não restaurar o banco inteiro sobre dados novos nem tocar nos motores de pontuação. Os novos registros SQLite podem permanecer como arquivo histórico.

## Limites desta entrega

A atualização visível acompanha a próxima leitura do app (cache de 60 segundos); a tela não tem promessa de atualização contínua sem interação. No painel, últimas 12 guerras comuns arquivadas são exibidas; o arquivo SQLite conserva as demais. Não há previsão de vitória, reserva de alvos, classificação calculada nem análise de tropas. Estatísticas CWL ainda exigem acompanhamento dos primeiros ataques reais desta temporada.
