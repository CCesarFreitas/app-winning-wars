# Ficha do jogador — filtro mensal

Publicado em 19/11/2026. A ficha antiga misturava auditoria legada sem filtro de mês com totais do ranking vigente.

- A consulta utiliza as últimas versões das atividades APLICADO da integração em SQLite, em modo somente leitura.
- O padrão é temporada_atual_id de EstadoMes; mês sem atividades não retorna resultados de outro mês.
- Seletor permite consultar meses disponíveis. Tela e PNG utilizam o mesmo período.
- Totais históricos são recuperados das fontes preservadas antes da virada, quando existe registro de fechamento. Sem fotografia suficiente, são apresentados como indisponíveis, nunca substituídos por totais atuais.
- Pontos, inscrições, permissões, regras e agendamentos não foram modificados.

Validação: 22 testes Python, 7 testes JavaScript e build de produção passaram. Consulta real da vila #QCYLC8G2V: novembro, 1 atividade e 6 pontos; outubro, 12 atividades e 42 pontos. Arquivos públicos conferidos por SHA-256; endpoint sem sessão retorna 401. Não houve inspeção visual automatizada do navegador nesta etapa.

Backups:
- API: /opt/winning-wars-api/backups_deploy/20261119T120736Z-ficha-mensal
- Web: /home/opc/backups_web/20261119T120755Z-ficha-mensal

Publicação: API admin.py e auditoria_mensal.py; web index.html, index-BcAPe3Yu.js e CSS existente index-DHY2uubF.css. Somente serviço da API reiniciado, com saúde conferida.
