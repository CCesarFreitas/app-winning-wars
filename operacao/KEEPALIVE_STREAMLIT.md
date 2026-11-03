# Keep-alive do Streamlit

## Diagnóstico de 3 de novembro de 2026

O workflow antigo era executado a cada seis horas no minuto `00`. O histórico
real do GitHub mostrou uma lacuna de 13h01 entre duas execuções, acima das 12
horas sem tráfego que levam o Streamlit Community Cloud a hibernar um app.

O deploy também estava exigindo autenticação. O Playwright antigo aceitava a
página de login como sucesso porque verificava apenas se a navegação terminava
sem exceção. Uma visita anônima não chegava ao processo Streamlit.

## Proteções instaladas

- GitHub Actions com navegador real a cada duas horas, no minuto `17`;
- falha explícita se a navegação terminar em login ou autenticação;
- confirmação de que o iframe do processo Streamlit foi carregado;
- tentativa de reativação pela tela pública quando o app já estiver dormindo;
- monitor HTTP independente na Oracle a cada 30 minutos;
- validação dos endereços externo, interno e `/~/+/_stcore/health`;
- logs no `journalctl` e status de erro quando o app não estiver acessível.

## Requisito de visibilidade

O app precisa aceitar acesso público. Enquanto o Streamlit Cloud exigir login,
nenhum monitor anônimo consegue criar uma sessão no app; os dois mecanismos
registram erro de autenticação em vez de informar sucesso falso.

Para conferir a Oracle:

```bash
systemctl list-timers --all winning-wars-streamlit-keepalive.timer
systemctl status winning-wars-streamlit-keepalive.service --no-pager -l
journalctl -u winning-wars-streamlit-keepalive.service --since "2 hours ago" --no-pager
```
