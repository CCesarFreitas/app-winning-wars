# Migração do Streamlit para a plataforma independente Winning Wars

Data da decisão: 2026-11-03

## Decisão

O destino recomendado é uma aplicação web própria, hospedada na Oracle:

- backend: FastAPI/Python, aproveitando a API e os motores existentes;
- frontend: React + TypeScript, compilado com Vite para arquivos estáticos;
- entrada pública: Caddy em HTTPS, servindo o frontend e encaminhando `/api` ao FastAPI;
- execução contínua: `systemd`, como já ocorre com a API e os coletores;
- dados: manter Google Sheets e o arquivo histórico SQLite durante a migração;
- evolução posterior: centralizar todas as escritas transacionais na API e avaliar PostgreSQL somente quando o volume justificar.

O Streamlit será mantido temporariamente como contingência durante a homologação, mas não fará parte da arquitetura final.

## Por que esta é a alternativa adequada

O problema atual não é apenas hibernação. O app depende do frontend, dos módulos JavaScript dinâmicos e do ciclo de publicação do Streamlit Cloud. As falhas observadas atingiram componentes básicos, login administrativo e tempo de abertura.

A infraestrutura existente já resolve a parte mais difícil:

- a Oracle executa `/opt/winning-wars-api/app.py` com FastAPI/Uvicorn;
- `winning-wars-api.service` está estável e inicia automaticamente;
- já existem endpoints de saúde, ranking, auditoria, guerras e administração de membros;
- a lógica de competição está separada em módulos Python reaproveitáveis;
- os coletores e processadores permanecem independentes da interface;
- o histórico SQLite já existe na Oracle;
- a interface React compilada não exige um processo Node.js em produção.

Alternativas como Dash, Gradio, NiceGUI ou Reflex não foram escolhidas porque manteriam uma forte dependência de um framework Python de interface e de sessão. Django exigiria reescrever uma API que já existe. Auto-hospedar o Streamlit pode servir de ponte emergencial, mas não elimina as limitações estruturais que motivaram esta migração.

## Estado técnico encontrado

- Oracle: aproximadamente 945 MiB de RAM, 487 MiB disponíveis e 16 GiB livres em disco no momento da inspeção.
- API FastAPI: cerca de 17 MiB de memória em uso e ativa há quase dois meses.
- API atual: escuta em `0.0.0.0:8000` e está diretamente exposta à internet.
- Proxy HTTPS: Caddy e Nginx não estavam instalados/configurados.
- Endpoints já disponíveis incluem `/health`, `/ranking`, `/war/current`, `/war/score`, auditoria histórica e ações administrativas de membros.
- A API existente ainda não cobre todas as telas e ações do Streamlit e não deve ser considerada pronta para exposição pública sem endurecimento de segurança.

## Arquitetura alvo

```text
Navegador / celular / tela da live
                |
             HTTPS
                |
              Caddy
        +-------+--------+
        |                |
  arquivos React      /api/*
  HTML/CSS/JS             |
                    FastAPI local
                    127.0.0.1:8000
                          |
        +-----------------+------------------+
        |                 |                  |
  Google Sheets      SQLite histórico   motores Oracle
  fonte atual        e auditoria         guerras/ligas/raides
```

O FastAPI deixará de ouvir publicamente. Somente Caddy deverá expor as portas 80 e 443. O frontend e a API usarão a mesma origem, evitando problemas de CORS e simplificando cookies seguros.

## Estratégia de migração sem interromper a produção

### Etapa 1 — fundação e prova de conceito, somente leitura

- criar `web/` no repositório com React, TypeScript e Vite;
- criar uma versão `/api/v1` dos endpoints usados pela interface;
- publicar em um endereço de homologação separado;
- implementar ranking, detalhes do jogador, auditoria, agenda e membros;
- validar em celular, desktop e tela usada nas lives;
- não alterar lançamentos, planilha ou motores nesta etapa.

### Etapa 2 — páginas públicas completas

- planejamento de guerras e ligas;
- atividades encerradas e histórico;
- plataforma Torneios Winning Wars;
- layouts, notícias e demais conteúdos públicos;
- PWA instalável, cache controlado e identidade visual própria;
- monitoramento de saúde e logs.

### Etapa 3 — painel administrativo

- autenticação no servidor com cookie `HttpOnly`, `Secure` e `SameSite`;
- proteção CSRF, limitação de tentativas e expiração de sessão;
- membros e habilitação no ranking;
- lançamento manual de Jogos do Clã e eventos;
- correções, regras, layouts, notícias e torneios;
- todas as escritas passam pela API com idempotência, auditoria e backup.

### Etapa 4 — virada controlada

- comparar por pelo menos sete dias ranking, auditoria e resultados entre as duas interfaces;
- executar backup antes da virada;
- apontar o domínio oficial para a nova plataforma;
- deixar o Streamlit somente leitura durante a janela de segurança;
- retirar o Streamlit após a homologação final e manter um procedimento documentado de rollback.

## Segurança obrigatória antes da publicação

- usar um domínio próprio e HTTPS válido;
- instalar e configurar Caddy como proxy reverso;
- alterar Uvicorn para `127.0.0.1:8000`;
- restringir 8000 no firewall da Oracle;
- retirar chaves e senhas do frontend e do repositório;
- substituir o modelo atual de chave administrativa por sessão autenticada no servidor;
- validar autorização em todo endpoint de escrita;
- registrar ações administrativas sem registrar segredos;
- manter backup diário e teste periódico de restauração.

## Definição de pronto

A substituição estará concluída quando:

1. a plataforma funcionar em domínio HTTPS próprio, sem Streamlit;
2. o serviço iniciar e se recuperar automaticamente via `systemd`;
3. todas as páginas públicas críticas estiverem responsivas no celular;
4. ranking, pontos, histórico e auditoria coincidirem com as fontes oficiais;
5. todos os recursos administrativos essenciais existirem na nova interface;
6. nenhuma senha ou chave administrativa chegar ao navegador;
7. toda escrita for validada, idempotente, auditada e coberta por backup;
8. o endpoint interno da API não estiver exposto diretamente à internet;
9. houver monitoramento, logs, teste de saúde e procedimento de rollback;
10. a validação paralela de sete dias não apresentar divergência crítica.

## Primeiro incremento recomendado

Construir agora uma prova de conceito somente leitura com:

- página inicial;
- ranking oficial;
- ficha e histórico do jogador;
- auditoria da pontuação;
- navegação responsiva;
- tema Winning Wars;
- consumo da API por `/api/v1`;
- publicação em homologação, sem mexer no app oficial.

Este incremento valida aparência, velocidade e infraestrutura antes de migrar login e qualquer operação de escrita.

