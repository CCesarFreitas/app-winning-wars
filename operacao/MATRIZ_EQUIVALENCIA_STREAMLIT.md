# Matriz de equivalência — migração integral do Streamlit

Data do inventário: 2026-11-03

## Objetivo

Substituir integralmente a interface Streamlit por uma plataforma React/FastAPI hospedada na Oracle, mantendo todas as capacidades válidas do aplicativo oficial e sem interromper os motores de guerra, liga, raide, inscrição e auditoria.

A prova de conceito em `web/` valida somente a fundação técnica e a experiência visual. Ela não representa o escopo final da migração.

## Regra de equivalência

Cada função atual será classificada antes da virada como:

- **migrada**: existe e foi homologada na plataforma nova;
- **substituída**: a mesma necessidade foi resolvida por fluxo melhor e documentado;
- **obsoleta**: deixou de ser necessária após automação, com aprovação explícita;
- **bloqueadora**: impede a retirada do Streamlit enquanto não for concluída.

Nenhuma função será removida apenas por não ter sido incluída na primeira prova de conceito.

## Área pública

| Área atual | Entrega equivalente | Situação inicial |
| --- | --- | --- |
| Página inicial e identidade Winning Wars | Home responsiva, temporada e atalhos | POC parcial |
| Ranking ao vivo | Pódio, pesquisa e classificação | POC parcial; API precisa usar temporada atual |
| Tabela detalhada | Visão completa por atividade/coluna e filtros móveis | Pendente |
| Meses anteriores | Arquivo de temporadas e campeões | Pendente |
| Desempenho individual | Ficha, evolução, composição e justificativas | POC parcial |
| Agenda | Calendário e próximos eventos | Pendente |
| Atividades encerradas | Histórico, detalhes e registros originais | POC parcial |
| Planejamento de guerras | Escalação, CVs, adversários e gráficos responsivos | Pendente |
| Membros do clã | Lista, situação e dados públicos permitidos | Pendente |
| Layouts para guerra | Galeria por CV, links e validade | Pendente |
| Layouts para ranqueadas | Galeria por CV, links e validade | Pendente |
| Novidades, eventos e feed | Publicações, avisos e destaques | Pendente |
| Torneios Winning Wars | Chaves, regras, transmissão e seleção de vencedor | Pendente |
| Regras do clã | Regulamento público | Pendente |
| Links úteis | Clã, YouTube e destinos oficiais | Pendente |
| Instalação/PWA | Atalho instalável no celular e cache seguro | Pendente |

## Painel administrativo

| Área atual | Operações a migrar | Situação inicial |
| --- | --- | --- |
| Autenticação | Login, logout, sessão, troca de senha e níveis | Pendente; exige backend seguro |
| Fechamento mensal | Conferir, finalizar, arquivar e iniciar temporada | Pendente |
| Gestão 2.0 | Jogos do Clã em lote, eventos individuais, agenda, comunicação e auditoria | Pendente |
| Revisões | Conferência e correção controlada de lançamentos | Pendente |
| Desempenho dos membros | Relatórios da liderança e feedback | Pendente |
| Participação | Vínculos, contas secundárias, habilitação, bloqueio e lotes | Pendente |
| Players | Cadastro, remoção e situação da conta | Pendente |
| Administradores | Criar usuário, níveis e permissões | Pendente |
| Alterar senha | Atualização segura de credencial | Pendente |
| Pontos e colunas | Correções e manutenção ainda necessárias | Pendente; revisar itens obsoletos pela automação |
| Recado e galeria | Recado, campeões, galeria da fama e arquivo mensal | Pendente |
| Novidades | Criar, editar, publicar e excluir notícias | Pendente |
| Logs | Consultar ações e erros sem expor segredos | Pendente |
| Backup | Criar, listar, baixar e conferir backups autorizados | Pendente |
| Sorteio de desempate | Sorteio ao vivo com registro do resultado | Pendente |
| Integração | Saúde dos coletores, dados e última execução | Pendente |
| Layouts | Cadastrar, moderar e excluir layouts antigos | Pendente |
| Torneios | Criar torneio, sortear chave, avançar vencedor e encerrar | Pendente |
| Comunicação | Avisos, torneios, eventos, premiação e urgentes | Pendente |

## Reaproveitamento do código atual

### Pode ser reaproveitado

- regras de pontuação e elegibilidade;
- integração com Google Sheets;
- leitura do arquivo SQLite e documentos publicados pela Oracle;
- cálculos e relatórios existentes em `ww_competicao` quando não dependem da interface;
- motores de guerra, liga, raide, inscrições e participação;
- rotinas de backup e auditoria;
- lógica de torneios, layouts, histórico e fechamento, após separação da camada Streamlit.

### Precisa ser reescrito

- todo trecho que usa `st.button`, `st.form`, `st.tabs`, `st.session_state`, `st.dataframe`, `st.plotly_chart` ou widgets equivalentes;
- autenticação baseada na sessão do Streamlit;
- navegação e estado de formulários;
- mensagens de sucesso/erro e confirmações;
- gráficos e tabelas para celular;
- upload e pré-visualização de imagens no navegador.

## Arquitetura funcional

1. **React** apresenta todas as páginas públicas e administrativas.
2. **FastAPI** autentica, valida e executa consultas ou comandos.
3. **Serviços de domínio Python** reaproveitam as regras existentes sem importar Streamlit.
4. **Google Sheets** continua como fonte atual durante a migração.
5. **SQLite** preserva histórico, auditoria e dados publicados.
6. **Motores Oracle** continuam processando atividades independentemente da interface.
7. **Caddy** fornece HTTPS, arquivos estáticos e proxy `/api`.

## Capacidade da Oracle

O frontend React compilado é estático e praticamente não consome memória de execução. Caddy e FastAPI são leves. A instância atual consegue hospedar a arquitetura, mas possui aproximadamente 1 GiB de RAM e também executa coletores, timers e backups.

Para produção completa, a recomendação é:

- mínimo aceitável: 2 GiB de RAM;
- recomendado: 4 GiB, se a configuração da conta Oracle permitir;
- manter um único worker FastAPI inicialmente;
- limitar concorrência das rotinas pesadas;
- monitorar memória, swap, disco e tempo de resposta;
- manter frontend e API no mesmo servidor na primeira versão.

Não é necessário contratar um segundo servidor para começar, mas a capacidade deve ser revista antes da virada.

## Fases da migração integral

### Fase A — API e segurança

- criar `/api/v1` com temporada atual;
- autenticação e sessões seguras;
- consultas públicas completas;
- comandos administrativos com autorização, auditoria e idempotência;
- testes de contrato comparando Streamlit e API.

### Fase B — aplicação pública

- migrar todas as áreas públicas da matriz;
- validar celular, desktop e modo live;
- PWA, acessibilidade, desempenho e cache.

### Fase C — administração

- migrar todas as áreas administrativas;
- backup antes de cada operação sensível;
- confirmação e conferência pós-escrita;
- homologar por perfil de administrador.

### Fase D — paralelismo e virada

- operar ambas as interfaces por pelo menos sete dias;
- comparar ranking, histórico e ações;
- congelar escritas no Streamlit;
- ativar domínio oficial;
- manter rollback documentado;
- retirar o Streamlit somente após todos os itens bloqueadores estarem homologados.

## Definição de pronto para retirar o Streamlit

- todos os itens válidos desta matriz estão migrados ou formalmente substituídos;
- as fontes da temporada atual são usadas pela API;
- login e todos os perfis administrativos foram testados;
- toda ação de escrita possui autorização, auditoria, idempotência e backup;
- layouts, notícias, links, torneios e mídia funcionam sem Streamlit;
- ranking e relatórios coincidem com a planilha e o histórico;
- o sistema passou por homologação paralela;
- HTTPS, monitoramento, recuperação e backup estão ativos;
- a porta interna do FastAPI não está exposta à internet;
- existe procedimento testado de rollback.
