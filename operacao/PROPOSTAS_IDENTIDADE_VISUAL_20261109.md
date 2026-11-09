# Propostas de identidade visual — Winning Wars

As quatro propostas usam o mesmo componente React, o mesmo retorno do ranking e os mesmos ativos locais. Alternar a identidade não faz nova consulta à API.

## 1. Fortaleza Real 2.0

- Ênfase: formato oficial do ranking, premiação e leitura moderna.
- Navegação: abas horizontais douradas sempre visíveis.
- Ranking: pódio destacado, imagem real do Centro de Vila ao lado do jogador e lista responsiva para os demais colocados.
- Integridade: o CV vem do roster confirmado; contas sem confirmação exibem `CV —`.
- Melhor uso: identidade principal do novo site-app em computador e celular.

## 2. Fortaleza Clássica

- Ênfase: premiação, prestígio e Top 3.
- Navegação: abas horizontais douradas sempre visíveis.
- Ranking: pódio destacado e lista compacta para os demais jogadores.
- Melhor uso: página inicial e encerramento mensal.

## 3. Mapa de Guerra

- Ênfase: fantasia, progressão territorial e identidade Clash of Clans.
- Navegação: abas sobre barra escura, contrastando com o mapa em pergaminho.
- Ranking: trilhas de progresso, fortalezas e Centros de Vila.
- Melhor uso: campanhas, eventos e apresentação pública da competição.

## 4. Liga Imperial

- Ênfase: leitura rápida, comparação e estatísticas.
- Navegação: abas esportivas de alto contraste.
- Ranking: tabela compacta no computador e cartões no celular.
- Melhor uso: ranking diário, planejamento e administração.

## Recomendação

Usar a Fortaleza Real 2.0 como identidade principal, preservando elementos especializados das demais visões:

- Fortaleza Real 2.0 como moldura geral, página inicial e ranking;
- Liga Imperial para ranking, planejamento, membros e administração;
- Mapa de Guerra como modo especial para eventos, torneios e campanhas.

Essa combinação mantém personalidade sem prejudicar legibilidade. O custo para a Oracle é praticamente igual nas três opções: HTML/CSS estático no Nginx e uma única consulta compartilhada ao ranking.
