# Estimativa de custos (Fase 6)

> **Nenhum serviço pago foi contratado e nenhum recurso de nuvem foi criado.** Isto é uma **estimativa** reproduzível (`python scripts/cost_model.py --write`), não um orçamento. Os preços abaixo foram coletados em 2026-10-20 de **fontes de terceiros** (agregadores e blogs) — **nenhum foi confirmado na página oficial** do provedor — e precisam ser reconfirmados antes de qualquer decisão de gasto. Impostos (IVA etc.) não estão incluídos. Moedas não são convertidas (nenhuma taxa de câmbio foi coletada).

## Preços de lista usados

| Item | Unidade | Valor | Moeda | Franquia | Oficial? | Coletado | Fonte | Nota |
|---|---|---|---|---|---|---|---|---|
| hetzner_cpx22 | mes | 19.99 | EUR | — | **não (terceiros)** | 2026-10-20 | [fonte](https://privatedevops.com/news/hetzner-june-2026-cloud-price-increase-what-to-do) | 2 vCPU, 4 GB, 80 GB, IPv4 incluso, sem IVA; terceiros relatam reajuste de jun/2026 |
| aws_t4g_small | hora | 0.0168 | USD | — | **não (terceiros)** | 2026-10-20 | [fonte](https://calculator.holori.com/aws/ec2/t4g.small/us-east-1) | 2 vCPU Arm, 2 GB, Linux sob demanda, us-east-1 |
| aws_ebs_gp3 | GB-mes | 0.08 | USD | — | **não (terceiros)** | 2026-10-20 | [fonte](https://www.factualminds.com/blog/amazon-ebs-pricing-orphaned-volumes-snapshots/) | us-east-1; IOPS/vazao base inclusas |
| aws_s3_standard | GB-mes | 0.023 | USD | — | **não (terceiros)** | 2026-10-20 | [fonte](https://upstash.com/blog/aws-s3-pricing-explained-2026) | us-east-1; sem custo de requisicoes no modelo (volume baixo) |
| aws_egress | GB | 0.09 | USD | 100 | **não (terceiros)** | 2026-10-20 | [fonte](https://infratally.com/articles/aws-s3-pricing-explained-2026/) | saida para a internet; 100 GB/mes gratis agregados |

Horas por mês consideradas: 730 (preços por hora multiplicados por 730).

## Cenários (custo mensal)

| Cenário | Moeda | Computação | Disco | Backup | Saída (egress) | **Total/mês** |
|---|---|---|---|---|---|---|
| Homologação — 1 VM Hetzner CPX22 | EUR | 19.99 | — | — | — | **19.99** |
| Homologação — 1 VM AWS t4g.small | USD | 12.26 | 2.40 | 0.11 | 0.00 | **14.78** |
| Produção pequena — 2 VMs AWS t4g.small (principal + reserva) | USD | 24.53 | 8.00 | 1.15 | 0.00 | **33.68** |

Premissas por cenário:

- **Homologação — 1 VM Hetzner CPX22** — 1 host(s); disco 80 GB/host; backup retido 5 GB; saída 20 GB/mês. Disco de 80 GB incluso. Backup fica no MESMO host (sem custo, mas não protege contra perda do host); preço de armazenamento externo da Hetzner não foi coletado.
- **Homologação — 1 VM AWS t4g.small** — 1 host(s); disco 30 GB/host; backup retido 5 GB; saída 20 GB/mês. 2 GB de RAM é o mínimo: os limites do Compose somam ≈ 1,4 GB (sem Prometheus).
- **Produção pequena — 2 VMs AWS t4g.small (principal + reserva)** — 2 host(s); disco 50 GB/host; backup retido 50 GB; saída 100 GB/mês. Sem balanceador, sem banco gerenciado e sem WAF (não precificados). A reserva exige replicação do banco, que NÃO está implementada.

## Crescimento do armazenamento de telemetria

Premissa **medida em pequena escala**: 340 bytes por linha de `telemetry_events` (`pg_total_relation_size` ÷ linhas = 339 B, com 2.080 linhas na homologação; tabelas maiores amortizam o overhead de página, então o número real tende a ser menor). Reaferir com volume real.

| Dispositivos | Sensores | Intervalo | Linhas/mês | GB/mês |
|---|---|---|---|---|
| 3 | 3 | 2 s | 11,664,000 | 3.97 |
| 100 | 6 | 5 s | 311,040,000 | 105.75 |
| 1000 | 6 | 10 s | 1,555,200,000 | 528.77 |

Sem política de retenção/compactação (não implementada), o disco cresce linearmente: 1 000 dispositivos a cada 10 s enchem 80 GB em poucas semanas. **Retenção de telemetria é trabalho pendente.**

## O que NÃO está estimado

- Balanceador, DNS, TLS gerenciado, WAF, banco gerenciado, monitoramento externo, alertas (Alertmanager/pager), registry privado, suporte, horas de operação, licenças.
- Desempenho de ingestão em escala: o único teste de carga medido é o da API (ver `docs/ops/slo.md`); a vazão do pipeline MQTT→PostgreSQL **não foi medida**.
