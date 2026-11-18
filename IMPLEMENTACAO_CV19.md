# CV19 — implementação local, 18/11/2026

## Publicação concluída em 18/11/2026

Atualização deste registro: o usuário autorizou a publicação e o registro da primeira identidade SSH do servidor web. Conexões seguintes utilizaram verificação estrita.

- API: três arquivos CV19 publicados; backup `/opt/winning-wars-api/backups_deploy/20261118T183413Z-cv19`.
- Web: index, JS, CSS e imagem CV19 publicados; backup `/home/opc/backups_web/20261118T183456Z-cv19`.
- Bundle: `index-rBi7ayS9.js`.
- Os quatro arquivos web foram baixados pelo HTTPS oficial e seus hashes conferiram com o pacote.
- Ranking HTTP 200: 51 contas, incluindo seis CV19; novembro/2026 aberto.
- Consultas de layouts CV19 para Guerra e Rankeada: HTTP 200.
- Os seis serviços/timers principais permaneceram ativos. Apenas a API foi reiniciada para carregar o código.
- Um ícone WhatsApp divergente foi detectado antes da escrita web e preservado. A publicação foi reduzida aos quatro arquivos necessários.
- Nenhuma pontuação, inscrição ou participação foi alterada. Publicação/exclusão administrativa de layouts foi testada com dados simulados, sem criar layouts reais.
- A inspeção visual automatizada continua não executada devido ao bloqueio de uso da ferramenta. A publicação foi autorizada pelo usuário após disponibilização da prévia.

As seções abaixo registram o preparo anterior; a indicação de publicação pendente foi superada por esta atualização.

Base: `fed57df916e6f7dbdc107e97c38b6b0251c3e97d`, branch `trabalho/retomada-20261118`.

## Entrega

- CV19 disponível e inicialmente selecionado em Layouts de Guerra e Rankeada.
- API aceita CV19 na publicação em lote e exclusão de layouts, tanto nos modelos de entrada quanto nas operações.
- Ranking reconhece CV19 nas capturas do roster, sem modificar pontos ou participantes.
- Imagem usada em ranking, planejamento, torneios, fichas e controles administrativos.
- Componente compartilhado trata CV desconhecido e falha de carregamento de imagem. Exportações também possuem alternativa.
- Modo alternativo do ranking usa o CV real do jogador em vez da imagem decorativa baseada na posição.
- Compatibilidade de layouts CV9–CV18 mantida; valores fora de CV9–CV19 continuam bloqueados para cadastro.

Arte: PNG original da Supercell embutido integralmente em SVG com janela sobre a variante original. Sem hospedagem externa durante o uso. Origem e hash em `web/public/assets/centros-vila/FONTES.md`. Nenhuma arte foi inventada. O formato SVG foi escolhido para apresentar a variante sem alterar o PNG oficial.

## Validação

- 50 testes Python selecionados aprovados, incluindo os novos cenários CV19 e atualização do roster sem mudança de pontuação.
- Quatro testes frontend aprovados (`pnpm run test:cv`): imagens empacotadas CV9–CV19, valores inválidos/futuros, caminho base de publicação e imagem CV19 autocontida.
- Build TypeScript/Vite aprovado.
- Não foram feitos lançamentos reais, exclusões reais de layouts, alterações da planilha ou da Oracle.

**Conferência visual pendente:** a ferramenta de navegador não conseguiu abrir a prévia por falha da revisão automática causada por limite de uso. Não foi contornado o bloqueio. A imagem original foi inspecionada, mas a interface renderizada, comportamento mobile e download PNG final ainda precisam de conferência em navegador.

## Prévia local

Script externo ao checkout: `..\previa_cv19_local.py`, servindo o build em `http://127.0.0.1:8767` com dados fictícios. Não consulta Oracle nem Google Sheets e rejeita POST. A sessão administrativa é fictícia e vale apenas nesse servidor de teste local.

Páginas para conferir:

- `/layouts/guerra` e `/layouts/rankeada`: CV19 e alternância para CV18/CV9.
- `/ranking`: jogadores fictícios CV19, CV18 e CV desconhecido.
- `/jogador`: exportação individual usando jogador fictício CV19.
- Conferir a mesma navegação em largura de celular.

## Publicação ainda não realizada

Backend CV19: `plataforma_api/admin.py`, `plataforma_api/operacoes_admin.py`, `plataforma_api/ranking_atual.py`.
Frontend: conteúdo de `web/dist` após build, incluindo o novo asset local.

Há também alterações locais anteriores de fechamento de conexões SQLite e documentação do ambiente, registradas em `RETOMADA_LOCAL.md`; não confundir essas mudanças com requisitos do CV19.

Antes de publicar, conferir novamente produção e hashes dos arquivos-alvo, concluir a verificação visual, validar a identidade SSH da VM web neste computador e preparar backup/retorno. A verificação SSH estrita da VM web havia falhado na auditoria anterior porque sua chave de host ainda não é conhecida localmente. Não desabilitar essa proteção.

Não houve push, deploy ou reinício de serviços. A consulta individual pública e a revisão do período do relatório são outras pendências, não incluídas nesta alteração CV19. O legado Streamlit não foi atualizado.
