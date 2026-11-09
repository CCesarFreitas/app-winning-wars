# Migração seletiva da plataforma Winning Wars

## Princípio obrigatório

- O Google Sheets continua sendo o banco oficial da aplicação.
- A Oracle executa a API, os motores e caches operacionais curtos.
- O navegador nunca recebe credenciais do Google, da Supercell ou de administradores.
- Não copiar integralmente o `app.py`: extrair serviços reutilizáveis e publicar somente as telas necessárias.
- Não duplicar abas inteiras em arquivos permanentes na nova VM.

## Estratégia de consumo

- Ranking e auditoria automática: fotografias operacionais já mantidas pelos motores.
- Layouts: leitura direta da aba `Layouts`, cache em memória de 5 minutos, deduplicação e paginação de 12 itens no cliente.
- Torneios: leitura direta da aba `Torneios`, cache em memória de 5 segundos; elenco vem do observador já existente da Oracle.
- Escritas administrativas futuras: usar as mesmas validações e operações em lote já existentes, conferir o resultado no Sheets e invalidar o cache correspondente.

## Módulos públicos

- [x] Página inicial
- [x] Ranking oficial
- [x] Ficha e auditoria do jogador
- [x] Atividades encerradas
- [x] Layouts de guerra
- [x] Layouts de rankeada
- [x] Plataforma pública de torneios
- [ ] Tabela detalhada por atividade
- [ ] Meses anteriores e Galeria da Fama
- [ ] Agenda
- [ ] Planejamento de guerras e Liga
- [ ] Membros do clã
- [ ] Novidades, regras e links úteis

## Administração

- [ ] Autenticação e níveis de acesso — fundação implementada; ativação depende de HTTPS
- [ ] Participação e vínculos
- [ ] Jogos do Clã e eventos manuais
- [ ] Revisões de pontuação
- [ ] Fechamento mensal
- [ ] Publicação de layouts
- [ ] Console de torneios
- [ ] Comunicação, agenda e novidades
- [ ] Saúde da integração e backups

O Streamlit permanece operacional até cada grupo ser homologado na plataforma independente.
