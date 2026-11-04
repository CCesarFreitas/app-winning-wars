# Frontend do Streamlit — 3 de novembro de 2026

## Sintoma

O navegador informou falha no carregamento dinâmico de:

`static/js/styled-components.JuRIuEWs.js`

## Diagnóstico

- o módulo respondeu `200` com `Content-Type: application/javascript`;
- seus módulos dependentes também responderam `200`;
- o shell atual passou a referenciar `styled-components.BdEMXxou.js`;
- o wheel oficial do Streamlit 1.66.1 contém os dois hashes;
- `requirements.txt` não fixava a versão do Streamlit.

O erro veio de uma sessão de frontend interrompida durante mudança de estado ou
publicação do Community Cloud. Não foi gerado pelo código Python do app.

## Correção

`streamlit==1.66.1` foi fixado em `requirements.txt`. Assim, novos deploys não
substituem silenciosamente os bundles JavaScript por outra versão do framework.
O commit dessa alteração também provoca uma reconstrução limpa no Community
Cloud. Depois do deploy, devem ser conferidos o app, `/_stcore/health` dentro de
`/~/+/` e os módulos JavaScript mencionados acima.
