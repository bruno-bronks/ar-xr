# SPEC-003 — Resolução de marker/QR

Requisito: REQ-MNT-001 · Outcome: OUT-MNT-001 · Formal: [`z-003-marker-resolution.tex`](../formal-z/z-003-marker-resolution.tex) · Modelo: `packages/domain/src/spatial_domain/markers.py`.

## Problema
O cliente escaneia um QR/marker e deve obter **somente** o equipamento correspondente, dentro da organização do usuário autenticado. QR adulterado, desconhecido ou de outra organização não pode revelar dados de nenhum equipamento nem sequer a existência do marker.

## Regras
- `marker → equipamento` é função parcial **injetiva** (um equipamento, um marker ativo).
- Todo equipamento pertence a exatamente uma organização.
- `resolve(marker, caller_org)`:
  - marker existe **e** equipamento pertence a `caller_org` → `Found(equipment_id)`;
  - qualquer outro caso → `NotFound` (mesmo resultado para desconhecido e para outra organização — **não-divulgação**).
- Autenticação (quem é o chamador) é responsabilidade da camada de API; o modelo recebe a organização já autenticada. No MVP a API usa identidade de demonstração explícita (dev mock) — nunca em produção.
- O conteúdo do QR é tratado como entrada não confiável: é só uma chave opaca, nunca contém dados do equipamento.

## Invariantes
- **M1** `Found(e)` ⇒ `owner(e) = caller_org`.
- **M2** Marker desconhecido e marker de outra organização produzem resultados idênticos.
- **M3** Resolução é pura (não altera o registro).
- **M4** Os 3 QR de teste (seed da Fase 1) resolvem cada um para o seu equipamento, e apenas para ele.

## Pendente (Fase 1)
Endpoint `GET /api/v1/spatial/markers/{marker_id}`, autenticação demo, auditoria de acesso e rate limit. O contrato já está declarado como `planned` em `openapi.yaml`.
