# Consultas, histórico e revisões — 2 de outubro de 2026

## Escopo

Mantém Streamlit, hospedagem e motores de pontuação. Acrescenta:

- Navegação principal por seção (somente a seção selecionada executa), adequada ao celular.
- Lista do clã consultada na Supercell a cada oito horas, com nome Unicode, tag, CV, cargo, inscrição e permissão separados. A gestão em lote existente continua no painel administrativo.
- Saúde da integração com estados reais dos serviços, última consulta de guerra, previsão da próxima, último ciclo, lançamento e alertas de atraso.
- Desempenho público de capturas encerradas de outubro em diante, com regras instaladas, captura conferida por hash, ataques/CVs/estrelas/desconto ou saque/bônus. Captura parcial nunca é exibida.
- Resultado encerrado sem lançamento aparece pendente, com pontos oficiais ausentes, não zero. Motivo administrativo específico não é divulgado. Quando não há evidência do motivo de exclusão, o texto pede conferência em vez de inferir.
- Correção de guerra/Liga/raide no mês aberto, por ID, com limite da modalidade, justificativa, autorização relida, revisão da proposta e atualização de ponto/auditoria num único batchUpdate. Originais em ControleAtividades permanecem intocados.
- Arquivo SQLite persistente na Oracle com versões, transações locais, backup diário e integridade conferida. A planilha ainda é a fonte do ranking e das permissões; SQLite é o arquivo de consulta/auditoria, não uma migração do motor.

## Implantação

Código do observador: `/opt/winning-wars-api/consultas_app_20261002`.
Dados privados: `/opt/winning-wars-api/dados_consulta/historico.sqlite3`.
Backup diário: `backup_AAAAMMDD.sqlite3`, mesma pasta (copiar periodicamente para outro ambiente; não é backup externo).
Unidades: `winning-wars-consultas.service` e `.timer`, cinco minutos após terminar, pequena variação aleatória.
Planilha: novas abas `ConsultaPublica` (projeção sanitizada) e `RevisoesPontuacao` (trilha administrativa).
Nenhuma porta nova, credencial no repositório, reinício do motor ou alteração da regra de pontuação.

O observador nunca escreve ranking, inscrições ou decisões de participação. Uma falha preserva a última publicação; a interface avisa quando ela envelhece. O primeiro cadastro de membros foi consultado em 02/10/2026, com 48 contas. Não havia lançamentos oficiais de outubro nessa conferência.

## Validação

27 testes locais: banco, repetição/reversão, backup/restauração, transporte Unicode, controles de revisão, confirmação pós-envio e resposta perdida, regras reais de guerra/Liga/raide, histórico público e participação em lote. Dez testes centrais executados também na Oracle com os módulos instalados. Sintaxe do app conferida.

## Limites e continuidade

- A confirmação ponta a ponta com uma atividade real de outubro depende do seu encerramento. Cenários de cálculo foram testados sem dados fictícios na planilha oficial.
- Nomes de ataques e justificativas públicas vêm de campos explicitamente selecionados; administradores e motivos de correção ficam no painel restrito. A consulta pública das correções mostra data, antes e depois.
- Revisões fazem releitura antes do envio e mantêm a conferência pendente em sessão. O Sheets não oferece comparação e troca condicional nesse lote: a eliminação completa da corrida entre escritores exige centralizar todos os lançamentos numa API transacional. Não afirmar que o ranking já está migrado para SQLite.
- Se a sessão for perdida após um envio incerto, consultar a trilha de revisões antes de iniciar outra correção. Não reenviar automaticamente.
- Jogos e Eventos continuam pelo lançamento integrado existente, não por esta tela de revisão.
- Capturas antigas anteriores a outubro não são recalculadas para a competição atual. Resultados aplicados arquivados não são rebaixados quando o fechamento mensal limpa o controle operacional.
- Retenção inicial conserva todas as versões e backups; acompanhar espaço em disco. API da Supercell e leituras de planilha podem falhar por quota; dados exibidos trazem data de referência.

## Reversão

Desabilitar somente `winning-wars-consultas.timer` e parar seu serviço, caso necessário. Não parar os motores oficiais. Restaurar a versão anterior da interface por commit de reversão. Preservar SQLite, backups e as abas de consulta/revisão; não restaurar uma planilha inteira sobre pontuações novas.
