# SPEC-007 — Simulador de equipamentos e painel web 2D

Requisitos: REQ-SIM-001, REQ-UX-001.

## Simulador (`services/equipment-simulator`)
Publica no tópico `spatial/v1/equipment/{id}/telemetry` (QoS 1, `retain=false`), `source = "equipment-simulator"`, `event_id = "<equipment>-<sensor>-<seq>"`, a cada `SIM_INTERVAL_SECONDS` (padrão 2 s) por sensor. Gerador **determinístico** (semente `SIM_SEED`, padrão 42): a função `reading(equipment, sensor, tick)` é pura e testável.

| Equipamento | Cenário | Comportamento por ciclo de `SIM_CYCLE_TICKS` ticks (padrão 120 ≈ 4 min) |
|---|---|---|
| EQ-001 | `steady` | temperatura e vibração estáveis abaixo de `warn` (ruído pequeno) |
| EQ-002 | `ramp` | temperatura sobe linearmente de ~55% de `warn` até acima de `crit` no meio do ciclo, mantém, e volta ⇒ `NORMAL → WARNING → CRITICAL → NORMAL` |
| EQ-003 | `dropout` | normal, mas **silencia** (não publica) durante 40% do ciclo ⇒ `OFFLINE` após `offline_after` |

Extras configuráveis: `SIM_DUPLICATE_EVERY` (reenvia o mesmo `event_id` a cada N mensagens; padrão 7) e `SIM_LATE_EVERY` (reenvia leitura antiga fora de ordem; padrão 0 = desligado). Reconecta ao broker com backoff; nunca encerra por erro de rede.

## Painel (`clients/web-fallback`)
Página estática (HTML + JS vanilla, sem CDN). Fluxo: o usuário escolhe organização demo (token fictício) ⇒ `GET /api/v1/equipment` a cada 2 s ⇒ para cada equipamento `GET .../twin` e `GET .../alerts`.

Regras de apresentação (REQ-UX-001):
- Um cartão por equipamento com **estado em texto e cor** (nunca só cor): `NORMAL`, `WARNING`, `CRITICAL`, `OFFLINE`, `UNKNOWN`.
- `OFFLINE` e `UNKNOWN` aparecem como estados próprios e com mensagem ("sem dados recentes"); jamais exibidos como normais.
- Leituras (valor, unidade, idade em s) e limites; leituras não válidas marcadas.
- Faixa de alertas ativos no topo (contagem + lista).
- Erro de API/401 ⇒ banner de erro visível, sem apagar o último estado (marcado como desatualizado).
- Acessível: contraste, `aria-live` para alertas, funciona em 360 px de largura.
- Valores vindos da API são inseridos como **texto** (sem `innerHTML`) ⇒ sem XSS.

## Critérios de aceitação
- Unidade: `tests/unit/simulator/test_scenarios.py` (determinismo, cenários, duplicatas).
- E2E (Playwright com Microsoft Edge instalado): `tests/e2e/test_panel.py` — o painel mostra alerta para EQ-002, `OFFLINE` para EQ-003 no estado de dropout, e erro visível com token inválido.
- Integração de pilha: `tests/integration/test_stack_flow.py` — simulador → broker → worker → banco → API mostra estado atualizado.
