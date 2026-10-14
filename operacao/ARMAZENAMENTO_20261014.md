# Manutenção do armazenamento — 14/10/2026

Diagnóstico: raiz de 25 GiB a 97%, aproximadamente 852 MiB livres. `dados_consulta` com cerca de 18 GiB: banco ativo de 3 GiB, cópias diárias de 14 GiB, backup de implantação de 1,4 GiB. Partição `/var/oled` separada, no mesmo disco físico, com cerca de 19,5 GiB livres. Não é backup externo contra perda da instância/disco.

Consulta somente de leitura ao SQLite identificou 1.517.314.037 bytes de conteúdo em 2.919 versões de `planejamento` e 1.389.350.821 bytes em 2.909 versões de `planejamento_cache`. Datas de publicação e consulta mudavam mesmo sem mudança substantiva da atividade. `atividade` tinha 18 versões (210.361 bytes), `revisao` uma versão. Não foi feito expurgo nem VACUUM do histórico.

## Alterações

- Cópias antigas transferidas como gzip para `/var/oled/winning-wars-backups`, com SHA-256 do conteúdo descomprimido comparado ao original antes de retirar o original. Manifesto `migracao_20261014.jsonl` guarda caminhos, tamanhos, hashes e horários. Banco ativo continua no caminho original. Pequenos arquivos de código dos backups antigos permanecem no local.
- `planejamento`, `planejamento_cache` e `saude` passam a manter estado atual na tabela `estados_operacionais`. `ultimos` consulta a nova tabela com fallback ao histórico anterior. As versões históricas existentes permanecem intactas. Atividades, fontes, revisões, rosters e capturas de guerra continuam versionadas.
- Backup removido da publicação das consultas e isolado em `winning-wars-backup.service`/`.timer`. Agenda 06:15 UTC (03:15 Brasília), atraso aleatório de até cinco minutos, persistente após desligamento.
- Backup usa API SQLite para cópia consistente, `integrity_check`, gzip e verificação SHA-256; publicação por rename. Falhas não executam retenção. Execuções exclusivas por trava.
- Retenção das cópias diárias: sete dias, quatro semanas, seis meses, preservando a mais recente por janela; teto adicional de 8 GiB, mas nunca excluindo as três cópias mais recentes. Backups de implantação em subpastas não são expirados por essa política. Expirações registradas em `retencao.jsonl`.

## Operação e recuperação

Originais do código alterado guardados em `/var/oled/winning-wars-backups/configuracao_20261014`. A reversão do módulo antigo perde apenas visibilidade dos novos estados operacionais até uma nova coleta; nunca restaurar um banco antigo sobre histórico recente sem plano de recuperação. Para restaurar arquivo comprimido, descompactar em arquivo separado, conferir SHA-256 quando disponível e `PRAGMA integrity_check`, parar os escritores antes de substituir o banco e preservar banco atual e WAL juntos para investigação. Não apagar um WAL ativo.

Observar `systemctl status winning-wars-backup.timer`, `journalctl -u winning-wars-backup.service` e `df -h / /var/oled`. O observador mantém sua periodicidade de cinco minutos. Motores de pontuação não foram reiniciados. Atualizações do app, nomes, torneios e membros da versão e7df98b foram preservadas.

Testes: estados atuais não acumulam versões, auditoria mantém mudanças, backup/restauração preservam ambos, janelas de retenção e proteção das três últimas cópias. Testes locais e na Oracle passaram; conjunto de 52 testes de regressão passou. Ciclo real de consultas após instalação terminou com sucesso, zero falhas históricas e zero atividades sem detalhe.

Resultado da migração: 16 arquivos, 16.058.994.688 bytes originais e 2.522.933.363 bytes comprimidos antes da retenção. Raiz caiu para 36% de uso, com cerca de 16 GiB disponíveis. Após dois ciclos reais, as contagens antigas de planejamento/cache/saúde permaneceram em 2.919/2.909/3.065, enquanto os estados atuais receberam novos horários. As 18 versões de atividades e a revisão permaneceram preservadas. Próxima execução do backup: 15/10/2026 às 03:16 de Brasília (atraso aleatório configurado).
