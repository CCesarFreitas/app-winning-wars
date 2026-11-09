# Tabela detalhada da temporada — 9 de novembro de 2026

## Resultado

- página pública: `https://winningwars.com.br/ranking/detalhado`;
- fonte: mesma fotografia SQLite somente leitura usada pelo ranking oficial;
- regras de habilitação: idênticas às do ranking, incluindo prevalência do bloqueio administrativo;
- colunas dinâmicas: guerras, Liga, raides, Jogos do Clã e eventos;
- busca por nome ou tag e filtro por modalidade;
- desktop com tabela horizontal organizada;
- celular com cartões por jogador, sem sobreposição de colunas;
- links diretos para a ficha e auditoria de cada jogador.

## Validações

- 3 testes unitários do ranking e da tabela: aprovados;
- TypeScript e build Vite: aprovados;
- endpoint público `/api/v1/ranking/details`: `200 OK`;
- temporada real: `2026-11`;
- 34 jogadores e 9 atividades no momento da publicação;
- validação visual em desktop e viewport móvel `390x844`: aprovada;
- nenhuma escrita no Google Sheets ou nos motores.

## Backups

- API: `/opt/winning-wars-api/backups_plataforma_independente/antes_tabela_detalhada_20261109T212815Z`;
- frontend inicial: `/opt/winning-wars-web/backups/frontend-antes-tabela-detalhada_20261109T212835Z.tgz`;
- frontend antes do acabamento de data: `/opt/winning-wars-web/backups/frontend-antes-formato-data_20261109T213015Z.tgz`.
