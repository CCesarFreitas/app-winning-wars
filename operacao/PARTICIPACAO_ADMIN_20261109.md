# Participação e vínculos — plataforma independente

## Entrega

Foi implementada uma consulta administrativa protegida que combina, sem escrita:

- ranking da temporada;
- vínculos entre participante e tag;
- inscrições ativas;
- decisões de participação;
- roster atual do clã;
- histórico de entrada, saída e retorno ao clã.

Presença no clã é apresentada como alerta. Uma ausência não bloqueia a conta;
somente uma decisão administrativa explícita altera a habilitação.

## Conferência de 9 de novembro de 2026

- contas monitoradas: 94;
- atualmente no clã: 29;
- ausentes: 65;
- habilitadas: 68;
- bloqueadas: 26;
- inscritas na temporada: 34;
- com pontuação: 34.

As situações observadas foram: membro atual, entrada recente, retornou ao clã,
ausente agora e sem registro no histórico do clã.

## Segurança

- endpoint exige sessão administrativa e responde `401` sem ela;
- frontend não carrega a lista antes da autenticação;
- nenhuma tag, nome ou decisão foi exposta na página anônima;
- nenhuma consulta adicional à Supercell foi criada;
- nenhuma operação de escrita foi implementada;
- login continua bloqueado enquanto o endereço utilizar HTTP.

## Backups

- API: `/opt/winning-wars-api/backups_plataforma_independente/antes_api_v1_20261109T160327Z`;
- frontend: `/opt/winning-wars-web/backups/proposta-antes-participacao-20261109.tgz`.
