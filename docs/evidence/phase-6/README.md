# Evidências da Fase 6 — cloud, operação e escala

Spec: [SPEC-012](../../../specs/functional/SPEC-012-cloud-and-operations.md). Datas: 2026-10-20/21. Tudo foi gerado **localmente** (Docker Desktop, Windows); **nenhum serviço de nuvem foi contratado e o VPS não foi tocado**. Os números descrevem uma máquina de desenvolvimento, não produção.

## Gates executados (resultado real)
| Gate | Resultado |
|---|---|
| `scripts/check.ps1` (ruff, ruff format, mypy strict, pytest sem Docker, pip-audit ×3) | **1074 passed, 151 skipped**; ruff/mypy limpos; pip-audit "No known vulnerabilities found" |
| Suíte completa com PostgreSQL real (`TEST_DATABASE_URL`), exceto integração/desempenho/E2E | 1141 passed, 1 skipped (modos POSIX no Windows), 1 falha (`test_agent_memory`: citava este README, ainda inexistente na hora). Corrigido em seguida; `tests/unit/repo` reexecutado: 53 passed. A suíte completa com PostgreSQL **não** foi reexecutada depois dessa correção (só docs mudaram) |
| Pilha real reconstruída com as imagens novas (`postgres:16.15`, `mosquitto:2.0.22`): `tests/integration tests/performance tests/e2e` | **75 passed, 7 skipped** (os 7 = o e2e de operações, que é opt-in) |
| E2E de operações com Docker REAL (`OPS_E2E=1`) | **7 passed em 476 s** — [ops-e2e-run.txt](ops-e2e-run.txt), tempos em [ops-e2e-timings.json](ops-e2e-timings.json) |
| Broker endurecido contra Mosquitto 2.0.22 | 14 passed (`tests/integration/test_broker_auth.py`) |
| Z-007 (CZT) | parse + typecheck OK, 0 avisos (`scripts/verify-z.ps1`); **nenhum teorema provado** |
| `scripts/check_prometheus.py` (promtool 3.15: config + 18 regras + testes de regras) | SUCCESS; mutação (limiar errado) reprova o teste |
| `scripts/verify_host.py` | [verify-host.txt](verify-host.txt): `systemd-analyze: OK` e `Valid cloud-config` |

Nota: a CI do GitHub **não** foi executada para esta fase (nada foi enviado ao remoto). Os jobs novos/alterados (`ops-validate`, `release.yml`) só rodaram como comandos locais equivalentes.

## Arquivos
| Arquivo | O que prova |
|---|---|
| `ops-e2e-run.txt`, `ops-e2e-timings.json` | deploy por tag, release defeituosa + rollback automático, rollback manual, backup + desastre + restauração, GitOps real |
| `slo-load-test-run-*.json` | 4 rodadas de carga (uma **reprovou** a latência), com conferência cliente × servidor |
| `prometheus-live-check.json` | alvos `up`, regras saudáveis, SLI de frescor ao vivo e o bug `le="5"` achado/corrigido |
| `alert-fault-injection.json` | alertas disparados de verdade com o broker parado e limpos após a recuperação |
| `sbom/*.cdx.json` | SBOM CycloneDX 1.6 das dependências Python de cada serviço |
| `trivy/*.json` | varreduras ANTES e DEPOIS das atualizações de imagem (`*_16.4*`, `*_2.0.18`, `*_v2.55.1` = antes) |
| `semgrep.json` | 3 avisos `dynamic-urllib` (todos tratados) |
| `verify-host.txt` | validação oficial de systemd e cloud-init |

## Reprodução
```powershell
$env:OPS_E2E = "1"; python -m pytest tests/integration/test_ops_e2e.py -v     # ~8 min, usa Docker e portas 25000/28088/55434/21883
python scripts/check_prometheus.py ; python scripts/verify_host.py ; python scripts/cost_model.py
# homologação + carga: ver docs/runbooks/gitops-and-deploy.md e docs/ops/slo.md
```

## Limites
Máquina de desenvolvimento; banco minúsculo (RTO não extrapola); preços de custo de terceiros; sem pentest; scanners com banco de vulnerabilidades do dia (repita antes de qualquer release); a rodada de carga logo após o build não atendeu o SLO de latência (ver [slo.md](../../ops/slo.md)).
