# Winning Wars Web — prova de conceito

Frontend independente e somente leitura para validar a substituição do Streamlit.

## Escopo

- página inicial;
- ranking oficial;
- ficha do jogador;
- auditoria de atividades;
- navegação responsiva para celular e desktop;
- nenhuma chamada `POST`, `PUT`, `PATCH` ou `DELETE`.

## Desenvolvimento

```powershell
pnpm install
pnpm dev
```

O Vite encaminha `/api` para a API atual configurada em `vite.config.ts`. Para usar uma API local:

```powershell
$env:WWA_API_TARGET = "http://127.0.0.1:8000"
pnpm dev
```

## Build

```powershell
pnpm build
```

Os arquivos estáticos serão gerados em `dist/`. Em produção, Caddy deve servir essa pasta e encaminhar `/api/*` ao FastAPI interno, removendo o prefixo `/api`.

## Garantia de somente leitura

O módulo `src/api.ts` expõe exclusivamente três consultas GET:

- `GET /ranking`;
- `GET /audit/activities`;
- `GET /audit/player/{tag}`.

A prova de conceito não contém autenticação administrativa nem ações de escrita.
