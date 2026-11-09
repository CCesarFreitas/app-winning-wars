# Autenticação administrativa da plataforma independente

## Estado atual

- Rotas de autenticação instaladas na API Oracle com falha fechada.
- Interface de login e painel somente leitura publicada apenas em `/proposta/`.
- O endereço temporário usa HTTP; por isso os campos de login permanecem desabilitados.
- Nenhuma operação de escrita administrativa foi criada ou liberada.
- O Streamlit e todas as operações oficiais continuam inalterados.

## Controles implementados

- validação dos administradores cadastrados na aba `Admins`;
- compatibilidade com PBKDF2 e com o SHA-256 legado;
- sessão assinada com expiração de oito horas;
- cookie `HttpOnly`, `Secure`, `SameSite=Strict` e limitado ao caminho administrativo;
- revogação efetiva quando o administrador deixa de existir na planilha;
- limite de cinco tentativas inválidas por IP em quinze minutos;
- resposta genérica para usuário ou senha inválidos;
- painel protegido inicialmente somente leitura.

## Valores de ambiente necessários para ativação

- `WW_ADMIN_SESSION_SECRET`: segredo aleatório com pelo menos 32 bytes;
- `WW_ADMIN_COOKIE_SECURE=1`: obrigatório no ambiente oficial.

Os valores não devem ser gravados no Git, no frontend ou em arquivos públicos.

## Condições para ativar

1. apontar um domínio para `144.33.27.210`;
2. instalar e validar o certificado HTTPS;
3. configurar o segredo da sessão em arquivo de ambiente protegido na API;
4. publicar a regra do Nginx que permite `POST` somente em login e logout;
5. testar login, expiração, logout e revogação;
6. somente depois iniciar a migração das escritas administrativas.

## Rollback

O backend anterior à instalação está em:

`/opt/winning-wars-api/backups_plataforma_independente/antes_api_v1_20261109T153132Z`

A proposta anterior à interface administrativa está em:

`/opt/winning-wars-web/backups/proposta-antes-admin-20261109.tgz`
