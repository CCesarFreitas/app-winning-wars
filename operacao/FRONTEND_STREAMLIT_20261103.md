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

## Correção inicial

`streamlit==1.66.1` foi fixado em `requirements.txt`. Assim, novos deploys não
substituem silenciosamente os bundles JavaScript por outra versão do framework.
O commit dessa alteração também provoca uma reconstrução limpa no Community
Cloud. Depois do deploy, devem ser conferidos o app, `/_stcore/health` dentro de
`/~/+/` e os módulos JavaScript mencionados acima.

## Correção definitiva dos caches antigos

Depois do primeiro rebuild, alguns navegadores continuaram falhando ao buscar
`IFrame.DG4BXuTl.js` e `TextInput.BxDbpba5.js`, embora ambos respondessem `200`
como JavaScript. O Streamlit foi então fixado em `1.64.0`, versão compatível com
as abas preguiçosas usadas pelo app e cujos módulos possuem hashes diferentes:

- `IFrame.CJEcrs1k.js`;
- `TextInput.DZMdozJH.js`;
- `styled-components.CO_R0WlO.js`, `DuYBb88g.js` e `wtDqCLAZ.js`.

Essa troca impede que uma sessão reutilize os módulos que ficaram presos no
cache durante as reconstruções anteriores.
