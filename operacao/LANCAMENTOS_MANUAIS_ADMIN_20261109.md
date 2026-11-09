# Jogos do Clã e eventos — plataforma independente

## Entrega

Foi implementado um módulo administrativo protegido, ainda sem escrita, com:

- lista de contas e situação de participação;
- regras oficiais dos Jogos do Clã;
- simulador de substituição do total da atividade;
- indicação de inscrição automática na primeira pontuação positiva;
- bloqueio de propostas para contas administrativamente bloqueadas;
- histórico dos lançamentos manuais;
- validação dos hashes da auditoria antes da exibição.

## Regras validadas

- menos de 2.000 pontos: 0 ponto;
- 2.000 a 3.999: 2 pontos;
- 4.000 a 9.999: 5 pontos;
- exatamente 10.000: 10 pontos;
- o resultado substitui o total anterior e não soma novamente;
- zero não cria inscrição para uma conta ainda não inscrita;
- primeira pontuação positiva indica a criação automática da inscrição;
- bloqueio administrativo impede a proposta.

## Conferência

- 11 testes de autenticação, participação e lançamentos aprovados;
- 94 contas disponíveis para consulta administrativa;
- 35 lançamentos históricos com hash válido;
- endpoint de consulta responde `401` sem sessão;
- endpoint de simulação responde `403` no HTTP atual;
- nenhum nome, tag ou histórico aparece anonimamente;
- nenhuma escrita foi executada no Google Sheets.

## Backups

- API: `/opt/winning-wars-api/backups_plataforma_independente/antes_api_v1_20261109T164032Z`;
- frontend: `/opt/winning-wars-web/backups/proposta-antes-manual-20261109.tgz`.
