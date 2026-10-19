# SPEC-002 — Avaliação de estado do equipamento

Requisito: REQ-MNT-002 · Outcome: OUT-MNT-003 · Formal: [`z-002-status-evaluation.tex`](../formal-z/z-002-status-evaluation.tex) · Modelo executável: `packages/domain/src/spatial_domain/status.py`.

## Problema
Converter as últimas leituras de um equipamento em um estado operacional **determinístico**, sem inferir normalidade a partir de dado ausente.

## Entradas
- Perfil de limiares por sensor: `warn ≤ crit` (configurável por tipo/equipamento — sem valores universais).
- Última leitura por sensor: `value`, `observed_at`, `quality ∈ {GOOD, BAD}`.
- `now` e `offline_after`.

Leitura **válida** = `quality = GOOD` ∧ `now - observed_at ≤ offline_after` (D-002, D-003).

## Regras (ordem de precedência)
1. Nenhuma leitura → `UNKNOWN`.
2. `now - last_seen > offline_after` → `OFFLINE` (precede limiares). `last_seen` = maior `observed_at` entre todas as leituras, inclusive `BAD` (D-003).
3. Alguma leitura válida com `value > crit` → `CRITICAL`.
4. Senão, alguma leitura válida com `value > warn` → `WARNING`.
5. Senão, se **todos** os sensores do perfil têm leitura válida → `NORMAL` (D-006).
6. Senão → `UNKNOWN` (sensor ausente, `BAD` ou velho, sem evidência de alarme).

Limiar exato **não** alarma (D-001). `observed_at` no futuro em relação a `now` é tratado como idade 0 (a rejeição por skew ocorre na ingestão, Fase 1). `offline_after` deve ser positivo; leitura de sensor fora do perfil é erro de precondição.

## Invariantes (verificados por Hypothesis no modelo)
- **I1** `NORMAL` ⇒ equipamento fresco, todos os sensores do perfil com leitura válida, nenhum acima de `warn`.
- **I2** `CRITICAL` ⇒ equipamento fresco ∧ existe leitura válida acima de `crit` (`WARNING` ⇒ válida acima de `warn` e nenhuma acima de `crit`).
- **I3** Equipamento com leituras e não fresco ⇒ `OFFLINE`.
- **I4** Totalidade/determinismo: toda entrada válida produz exatamente um estado.
- **I5** Monotonicidade: aumentar o valor de uma leitura válida nunca reduz o nível de alarme (`WARNING < CRITICAL`) nem altera `OFFLINE`.
- **I6** Valor exatamente em `warn` (ou `crit`) não excede o limite.
- **I7** O valor de leituras `BAD` — e de leituras `GOOD` velhas — não altera o resultado (apenas `observed_at` entra em `last_seen`).

## Cenários obrigatórios do plano cobertos
Sensor offline · limiar exato · mudança de estado · dado ausente.
Pendentes (Fase 1, exigem worker/DB/MQTT): evento duplicado · fora de ordem · perda/reconexão MQTT · falha de banco.

## Riscos
Modelo usa `float` finito; Z usa inteiros. Abstração registrada em `docs/decisions/tool-evaluation.md` (limitação de verificação formal).
