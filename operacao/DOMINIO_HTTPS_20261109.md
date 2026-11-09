# Domínio e HTTPS — 9 de novembro de 2026

## Domínio

- domínio: `winningwars.com.br`;
- `A winningwars.com.br`: `144.33.27.210`;
- `CNAME www.winningwars.com.br`: `winningwars.com.br`;
- DNS autoritativo: Registro.br.

## Certificado

- emissor: Let's Encrypt via Certbot;
- nomes: `winningwars.com.br` e `www.winningwars.com.br`;
- validade inicial: até 7 de fevereiro de 2027;
- renovação: `certbot-renew.timer`, habilitado e ativo;
- ensaio de renovação: aprovado;
- HTTP redireciona para HTTPS com código 301.

## Servidor

- Nginx validado e ativo nas portas 80 e 443;
- firewalld permite `http`, `https` e `ssh`;
- uso do volume raiz após instalação: 30%;
- Certbot e dependências adicionaram aproximadamente 6,1 MB;
- segredo administrativo gerado no servidor e não exibido;
- cookie administrativo permanece `Secure` e `HttpOnly`.

## Validação interna

- sessão anônima HTTPS respondeu `autenticado: false`;
- login fictício HTTPS chegou à API e foi recusado com `401`;
- nenhuma credencial real foi usada;
- redirecionamento HTTP respondeu `301`.

## Pendência externa

A regra de entrada da rede OCI ainda precisa permitir TCP 443 para origem
`0.0.0.0/0`. Enquanto essa regra não for adicionada na Security List ou NSG da
sub-rede pública, o certificado funciona internamente, mas a conexão HTTPS da
internet expira por timeout.

## Backup

Configuração anterior do Nginx:

`/opt/winning-wars-web/backups/https-20261109T204132Z/nginx-antes.tgz`
