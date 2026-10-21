# SLOs — definição e medição (Fase 6)

Spec: [SPEC-012](../../specs/functional/SPEC-012-cloud-and-operations.md) §5 · REQ-OPS-006 · Decisão D-047 · Evidência: [docs/evidence/phase-6/](../evidence/phase-6/).

> **Leia primeiro.** Estas metas são **propostas** para medir contra, não garantias. As medições vêm de **uma máquina de desenvolvimento** (Docker Desktop, tudo em loopback, um único cliente de carga, dados simulados). Nada aqui descreve produção, outra máquina ou tráfego real.

## Metas, SLIs e orçamento de erro
| SLO | SLI (como se mede) | Meta | Janela | Orçamento |
|---|---|---|---|---|
| Disponibilidade da API | `1 − 5xx / total` (4xx é erro do cliente; `/metrics` excluído) | 99,5 % | 30 dias | 0,5 % (≈ 3,6 h de erro contínuo) |
| Latência da API | fração de requisições ≤ 500 ms (todas as rotas, sem `/metrics`) | 95 % | 30 dias | 5 % lentas |
| Frescor da ingestão | fração de leituras aceitas com `recebido − observed_at` ≤ 5 s | 95 % | 30 dias | 5 % lentas |
| Recuperabilidade | backup diário + ensaio de restauração semanal aprovado | ≥ 1/dia; ensaio ≤ 7 dias | contínuo | — |

Diferenças em relação ao D-047 (que era um rascunho): a latência vale para **todas** as rotas (não só `GET /equipment`) e o ensaio de restauração é **semanal** (o backup é diário).

Alertas: *burn rate* multi-janela (rápido 14,4× em 1 h/5 min ⇒ `page`; lento 6× em 6 h/30 min ⇒ `ticket`) em `platform/prometheus/rules/slo.rules.yml`, testados com `promtool` (`scripts/check_prometheus.py`), incluindo mutação (limiar errado ⇒ teste reprova) e disparo **real** em falha injetada (ver abaixo).

## Como foi medido
`scripts/load_test.py` contra a homologação local (`spatial-homolog`): carga em **circuito aberto** a 40 req/s, 4 workers, mistura fixa (30 % `GET /equipment`, 30 % `…/twin`, 20 % `…/telemetry/latest`, 10 % `/health/ready`, 5 % com credencial inválida ⇒ 401), semente fixa. A latência é medida a partir do instante **pretendido** de envio (sem omissão coordenada). Toda rodada confere as contagens do cliente com as de `http_requests_total` do servidor (**consistente em todas**). Perfil de requisição "frio" = logo depois de construir/subir as imagens.

## Resultados (todas as rodadas arquivadas, nenhuma descartada)
| Rodada | Duração | Requisições | 5xx | p50 | p95 | p99 | máx | ≤ 500 ms | SLOs atendidos? |
|---|---|---|---|---|---|---|---|---|---|
| [fria, logo após build](../evidence/phase-6/slo-load-test-run-cold-after-build.json) | 120 s | 4 800 | 0 | 27 ms | **975 ms** | 1 660 ms | 2 111 ms | **93,5 %** | **Não** (latência) |
| [aquecida 1](../evidence/phase-6/slo-load-test-run-warm-1.json) | 60 s | 2 400 | 0 | 27 ms | 159 ms | 432 ms | 615 ms | 99,5 % | Sim |
| [aquecida 2](../evidence/phase-6/slo-load-test-run-warm-2.json) | 60 s | 2 400 | 0 | 24 ms | 49 ms | 57 ms | 73 ms | 100 % | Sim |
| [aquecida 3](../evidence/phase-6/slo-load-test-run-warm-3.json) | 120 s | 4 800 | 0 | 25 ms | 66 ms | **2 056 ms** | 2 504 ms | 96,6 % | Sim (margem fina) |

Uma rodada anterior (60 s, build anterior das imagens; p95 ≈ 169 ms, p99 ≈ 432 ms, 99,7 % ≤ 500 ms, 0 5xx) foi vista no console e **não foi arquivada**; não entra na conta.

**Leitura honesta:**
- **Disponibilidade:** 0 erros 5xx em 14 400 requisições (as 4 rodadas arquivadas): atende 99,5 % **nesta amostra**; uma amostra assim não demonstra 99,5 % em 30 dias.
- **Latência:** a mediana é estável (≈ 25 ms), mas a **cauda é instável**: a rodada fria **não** atendeu (93,5 % ≤ 500 ms) e a aquecida 3 atendeu com margem fina, com picos de ≈ 2 s (3 % das requisições). A causa **não foi isolada**: suspeitos são a VM do Docker Desktop disputando CPU (a primeira rodada veio logo após o build) e o `/health/ready`, que abre uma conexão nova ao banco e ao broker a cada chamada (p95 da rota é o mais alto em várias rodadas). Antes de adotar 95 %/500 ms como compromisso, repetir em hardware representativo e investigar a cauda.
- **Frescor:** no Prometheus (janela 30 min, simulador gerando ≈ 1,5 msg/s): **p95 ≈ 0,10 s** e **99,83 %** das leituras aceitas em ≤ 5 s ([prometheus-live-check.json](../evidence/phase-6/prometheus-live-check.json)). Só vale para o simulador local; **a vazão máxima do pipeline MQTT→PostgreSQL não foi medida**.

## Alertas disparam de verdade (falha injetada)
Broker parado na homologação ([alert-fault-injection.json](../evidence/phase-6/alert-fault-injection.json)): `DependencyDown{dependency="broker"}` em **80 s**, `WorkerBrokerDisconnected` em **140 s**; todos os alertas limpos **40 s** depois de religar o broker. `PipelineStale` (≥ 2 min sem leitura + `for: 2m`) não foi esperado até o fim.

## Achado desta validação
O Prometheus rotula `le` como `"5.0"`; a exposição escrevia `"5"`. A regra de frescor (`le="5"`) **retornava vazio** ao vivo, embora o teste de regras com séries sintéticas passasse. Corrigido na origem (formato `repr` de float) e travado por `tests/unit/ops/test_rules_contract.py` (todo seletor `le` das regras precisa existir na exposição real). Lição: teste de regras com `promtool` **não** substitui conferir contra a exposição real.

## Limites
Sem Alertmanager (ninguém é notificado); janelas de 30 dias nunca observadas; sem teste de carga do pipeline de ingestão; sem tráfego de usuários reais; sem multi-cliente/rede real.
