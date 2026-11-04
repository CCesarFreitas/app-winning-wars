# Domínio da plataforma independente Winning Wars

## Nome recomendado

Usar um domínio próprio e separar produção de homologação:

- produção: `app.SEUDOMINIO.com.br`;
- homologação: `homolog.SEUDOMINIO.com.br`;
- API: não precisa de subdomínio público; será acessada em `app.SEUDOMINIO.com.br/api`.

Se o Winning Wars ainda não possui domínio, opções coerentes são:

- `winningwars.com.br`;
- `winningwarscoc.com.br`;
- `winningwars.gg`.

Antes da compra, conferir disponibilidade e risco de conflito de marca. Não registrar um domínio parecido com `clashofclans.com`, nem usar a marca Supercell como se fosse um serviço oficial.

## Onde registrar

Para `.com.br`, usar preferencialmente o Registro.br. Para `.com` ou `.gg`, pode-se usar Cloudflare Registrar, Namecheap ou outro registrador conhecido. O domínio deve ser registrado no nome do responsável pelo projeto, com e-mail de recuperação e autenticação em dois fatores.

## Configuração de DNS

Depois de registrar o domínio, criar dois registros do tipo `A`:

| Tipo | Nome | Valor | Uso |
| --- | --- | --- | --- |
| A | `app` | `164.152.253.100` | produção futura |
| A | `homolog` | `164.152.253.100` | prova de conceito |

Usar TTL de 300 segundos durante a implantação. Quando tudo estiver estável, aumentar para 3600 segundos.

Não alterar o endereço atual do Streamlit durante a prova de conceito.

## Publicação segura na Oracle

Antes de ativar os registros para usuários:

1. instalar Caddy na Oracle;
2. liberar somente as portas 80 e 443 no firewall e na lista de segurança da Oracle Cloud;
3. configurar Caddy para servir o frontend de homologação;
4. encaminhar `/api/*` ao FastAPI em `127.0.0.1:8000`;
5. alterar Uvicorn para ouvir somente em `127.0.0.1`;
6. bloquear acesso externo direto à porta 8000;
7. confirmar a emissão automática do certificado HTTPS;
8. testar o endereço de homologação antes de qualquer virada.

Exemplo conceitual de Caddyfile, a ser validado antes da instalação:

```caddyfile
homolog.SEUDOMINIO.com.br {
    root * /var/www/winning-wars-homolog

    handle_path /api/* {
        reverse_proxy 127.0.0.1:8000
    }

    try_files {path} /index.html
    file_server
}
```

## Ordem correta

1. escolher e registrar o domínio;
2. informar o domínio escolhido;
3. preparar Caddy e a pasta de homologação sem alterar o Streamlit;
4. configurar primeiro `homolog` no DNS;
5. publicar e testar a prova de conceito;
6. somente depois criar/ativar `app` para a plataforma definitiva.
