# Orçamento da migração integral para plataforma independente

Data do levantamento: 2026-11-03

## Resumo executivo

A plataforma pode ser implantada sem nova mensalidade obrigatória de hospedagem, utilizando uma instância Oracle Ampere A1 elegível ao Always Free. O custo mínimo recorrente previsto é o domínio `.com.br`, atualmente R$ 40 por ano.

O custo relevante da migração é o trabalho de desenvolvimento e homologação, não a infraestrutura.

## Infraestrutura atual confirmada

- Instância: `VM.Standard.E2.1.Micro`.
- Região: São Paulo/Vinhedo.
- Modalidade: `free-tier-retained`.
- Capacidade: 1 OCPU e 1 GB de RAM.
- Disco do sistema: 25 GB, com aproximadamente 16 GB livres na inspeção.
- Uso de memória: aproximadamente 442 MB, com cerca de 502 MB disponíveis e uso de swap.

A instância atual deve permanecer como contingência durante a migração. Ela não é a melhor candidata para receber simultaneamente todos os serviços da plataforma definitiva.

## Cenário recomendado — Oracle Always Free

Criar uma segunda instância `VM.Standard.A1.Flex`, ARM, com:

- 2 OCPUs;
- 8 a 12 GB de RAM;
- 50 GB de volume de inicialização;
- frontend React estático;
- Caddy;
- FastAPI;
- SQLite e rotinas operacionais migradas de forma controlada.

A documentação atual da Oracle informa que contas Always Free podem utilizar, no total, o equivalente a 2 OCPUs e 12 GB de memória no formato A1 sem cobrança. A disponibilidade do shape na região pode variar e deve ser confirmada no Console.

### Custo previsto

| Item | Custo inicial | Custo recorrente |
| --- | ---: | ---: |
| Oracle A1 dentro da franquia | R$ 0 | R$ 0/mês |
| Caddy e HTTPS automático | R$ 0 | R$ 0/mês |
| FastAPI, React, Vite e SQLite | R$ 0 | R$ 0/mês |
| DNS no Registro.br | R$ 0 | R$ 0/mês |
| Domínio `.com.br` | R$ 40 | R$ 40/ano |
| Certificado TLS | R$ 0 | R$ 0 |
| Google Sheets atual | R$ 0 adicional | R$ 0 adicional |
| GitHub atual | R$ 0 adicional | R$ 0 adicional |

**Total mínimo recorrente:** R$ 40 por ano, equivalente a aproximadamente R$ 3,33 por mês.

## Armazenamento e backup

A Oracle informa uma franquia Always Free total de 200 GB de Block Volume, somando volumes de inicialização e volumes adicionais, além de cinco backups de volume. A soma deve ser conferida no Console antes de criar a nova instância.

Não é necessário contratar banco gerenciado inicialmente. Google Sheets pode continuar como fonte operacional e SQLite como arquivo histórico durante a migração.

### Reserva opcional recomendada

Para cópia externa dos arquivos críticos, pode ser reservado um orçamento de R$ 10 a R$ 30 por mês, dependendo do provedor e do volume. Essa contratação é opcional e só deve ocorrer após medir o tamanho real dos backups.

## Cenário pago caso o A1 gratuito não esteja disponível

O preço público do Ampere A1 acima da franquia é:

- US$ 0,01 por OCPU/hora;
- US$ 0,0015 por GB de RAM/hora.

Estimativa para 730 horas mensais:

| Configuração | Estimativa em USD/mês | Planejamento em BRL/mês* |
| --- | ---: | ---: |
| 1 OCPU + 4 GB | US$ 11,68 | R$ 60 a R$ 75 |
| 2 OCPUs + 8 GB | US$ 23,36 | R$ 120 a R$ 150 |
| 2 OCPUs + 12 GB | US$ 27,74 | R$ 145 a R$ 180 |

\* Faixa de planejamento usando câmbio entre R$ 5 e R$ 6 por dólar, sem incluir eventuais tributos ou variação cambial. O valor final deve ser conferido na calculadora da Oracle antes de ativar recursos pagos.

Não é necessário contratar balanceador, CDN ou banco pago para a primeira versão.

## Esforço de desenvolvimento

A migração é uma reconstrução integral da interface e da camada de API administrativa. O `app.py` possui milhares de linhas, nove áreas públicas principais, páginas externas de layouts/torneios/notícias e mais de quatorze áreas administrativas.

Estimativa conservadora de esforço:

| Etapa | Horas estimadas |
| --- | ---: |
| API v1, contratos, temporada atual e segurança | 70–110 h |
| Páginas públicas completas | 100–160 h |
| Painel administrativo completo | 160–260 h |
| Testes, homologação, implantação e virada | 60–100 h |
| **Total** | **390–630 h** |

### Se contratado externamente

Faixas apenas para planejamento, não constituindo proposta comercial:

| Modalidade | Referência | Estimativa total |
| --- | ---: | ---: |
| Desenvolvedor freelancer | R$ 80–150/h | R$ 31.200–94.500 |
| Especialista/agência | R$ 150–250/h | R$ 58.500–157.500 |

As faixas variam conforme escopo visual, documentação, suporte, garantia, testes e responsabilidade pela operação.

### Desenvolvimento colaborativo neste projeto

Continuando a implementação pelo Codex, não existe uma cobrança separada de contratação de desenvolvedor feita por este projeto. O custo depende do plano/consumo da conta OpenAI do usuário, ao qual o projeto não possui acesso. Permanecem necessários o acompanhamento do administrador, validação de regras e homologação das operações críticas.

## Custos opcionais futuros

Não são necessários para a migração inicial:

- e-mail profissional;
- banco PostgreSQL gerenciado;
- CDN paga;
- armazenamento externo de mídia;
- monitoramento comercial;
- servidor de contingência pago;
- suporte contratado em regime de plantão.

Esses itens devem ser considerados somente depois de medir tráfego, uso de disco, quantidade de acessos e necessidade de disponibilidade.

## Cenários consolidados

### Econômico recomendado

- Oracle A1 Always Free;
- domínio `.com.br`;
- ferramentas de código aberto;
- desenvolvimento colaborativo atual.

**Infraestrutura:** R$ 40/ano, mais eventual consumo do plano OpenAI já utilizado.

### Conservador pago

- Oracle A1 com 2 OCPUs e 8 GB;
- domínio `.com.br`;
- reserva de backup externo.

**Infraestrutura:** aproximadamente R$ 135 a R$ 180/mês, incluindo domínio rateado e reserva básica de backup.

### Terceirização integral

- infraestrutura econômica ou paga;
- desenvolvimento e homologação por profissional/empresa externa.

**Implantação:** aproximadamente R$ 31 mil a R$ 157 mil, conforme fornecedor e nível de serviço, mais a infraestrutura.

## Recomendação financeira

1. Registrar apenas o domínio por R$ 40/ano.
2. Verificar disponibilidade do `VM.Standard.A1.Flex` em Vinhedo.
3. Tentar provisionar 2 OCPUs e 12 GB dentro do Always Free.
4. Manter a E2 atual ativa como rollback durante a migração.
5. Não contratar banco, CDN, balanceador ou backup comercial agora.
6. Medir por 30 dias após a publicação antes de assumir qualquer serviço pago.
7. Criar limites/orçamentos no Console Oracle antes de converter a conta para Pay As You Go.

## Fontes oficiais consultadas

- Oracle Always Free: https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
- Oracle Ampere A1: https://www.oracle.com/br/cloud/compute/arm/
- Oracle Global Price List: https://www.oracle.com/apac/a/ocom/docs/corporate/pricing/oracle-paas-and-iaas-global-price-list.pdf
- Registro.br: https://registro.br/dominio/
