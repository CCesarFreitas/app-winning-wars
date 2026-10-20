# Zero ataques na última guerra — 20/10/2026

Indicador no início de Painel Admin → Desempenho dos membros, independente dos filtros de datas, modalidades, inscrição ou presença atual. Autorização administrativa validada também pelo componente.

Fonte: projeção de planejamento existente (`comum` e `historico_comum`). Seleciona a guerra comum encerrada mais recente pelo fim; ignora preparação, andamento e liga. Valida escalação dos dois lados, tags, posições, CVs, ataques e total agregado; exige dois ataques disponíveis por vila e fim não futuro. A última captura inválida não é substituída silenciosamente por uma guerra antiga.

Lista apenas membros escalados com zero ataques; ataques realizados com zero estrela continuam sendo ataques e excluem a vila. Quem atacou uma ou duas vezes não aparece. Mostra nome/tag/CV/posição, quantidade e percentual entre escalados, adversário/data de fim, horário da publicação e situação na última lista de membros. Ausência de cadastro atual é distinta de não estar escalado. Permite exportação CSV, sem executar bloqueios, remoções ou alterar pontos.

Conferência somente de leitura na Oracle: publicação de 20/10/2026 08:33 Brasília, guerra encerrada em 19/10/2026 19:35, 45 escalados, seis com zero ataques (13,3%). Guerra atual em preparação excluída. Todos os seis constavam na lista atual consultada. Não foi necessária alteração em serviço, motor ou banco.

Validação: 46 testes passaram, incluindo nove novos cenários; interface Streamlit testada com a cópia real, mostrando seis linhas e 45 escalados. Fontes locais de homologação e nomes dos membros não foram adicionados ao repositório como fixtures.
