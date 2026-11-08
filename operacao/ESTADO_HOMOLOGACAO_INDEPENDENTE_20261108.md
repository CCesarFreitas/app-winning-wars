# Estado da homologacao independente — 2026-11-08

## Resultado

A fundacao da plataforma fora do Streamlit esta ativa em homologacao:

- servidor: `winning-wars-web` (`144.33.27.210`);
- frontend: React/TypeScript compilado e servido pelo Nginx;
- endereco temporario: `http://144.33.27.210`;
- proxy: apenas requisicoes GET em `/api/`; metodos de escrita recebem `403`;
- API v1: `/v1/ranking` e `/v1/season`;
- fonte do ranking: fotografias somente leitura do SQLite de consultas da Oracle;
- temporada validada: `2026-11`, com 12 contas no momento da instalacao;
- Streamlit, planilha e motores continuam operando sem alteracao.

## Seguranca aplicada

- Nginx sem acesso de escrita pela rota publica;
- SELinux continua `Enforcing`;
- `httpd_can_network_relay=on` e `httpd_can_network_connect=off`;
- somente a porta TCP 8000 foi classificada como `http_port_t` para o proxy;
- firewall do servidor novo libera SSH e HTTP; nao ha processo ouvindo em 8000;
- regra OCI adicionada para TCP 80, identificada como `Winning Wars homologacao web`;
- HTTPS ainda nao esta configurado. O IP HTTP e temporario e nao deve ser tratado como endereco oficial.

## Backups e rollback

- API antes da v1:
  `/opt/winning-wars-api/backups_plataforma_independente/antes_api_v1_20261108T214044Z`;
- frontend anterior:
  `/opt/winning-wars-web/backups/frontend-antes-api-v1-20261108T2142Z.tar.gz`;
- configuracao e conteudo inicial do Nginx permanecem em
  `/opt/winning-wars-web/backups/`.

O instalador `deploy/instalar_api_v1_ranking.py` cria backup, reinicia, confere
saude/ranking e restaura automaticamente a versao anterior se a validacao falhar.

## Validacoes concluidas

- `GET /healthz`: `200`;
- `GET /api/health`: `200`;
- `GET /api/v1/season`: novembro/2026;
- `GET /api/v1/ranking`: `200`;
- `GET /api/audit/activities`: `200`;
- `POST /api/v1/ranking`: `403`;
- build Vite e testes unitarios do leitor de ranking aprovados.

## Proximos passos

1. Escolher e configurar o dominio de homologacao.
2. Ativar HTTPS e liberar TCP 443 somente depois do dominio apontar para o IP.
3. Validar visualmente em celular e desktop pelo dominio HTTPS.
4. Completar as paginas publicas da matriz de equivalencia.
5. Implementar autenticacao e painel administrativo no servidor.
6. Comparar as duas interfaces por pelo menos sete dias antes da virada.

