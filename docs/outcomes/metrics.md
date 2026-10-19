# Outcomes e métricas

As metas abaixo são **propostas**, não resultados. Cada medição deve registrar ambiente e metodologia antes de ser citada como evidência.

| ID | Outcome | Métrica de validação | Requisitos | Fase de medição | Estado |
|---|---|---|---|---|---|
| OUT-MNT-001 | Identificação correta de equipamentos | 100% dos 3 QR de teste mapeados corretamente | REQ-MNT-001 | 1 (API) / 2 (AR) | Modelo verificado por testes (Fase 0); medição ponta a ponta pendente |
| OUT-MNT-002 | Telemetria apresentada rapidamente | p95 API→cliente < 3 s em ambiente de teste definido | REQ-MNT-003 | 1 | Contrato definido; **não medido** |
| OUT-MNT-003 | Alertas consistentes | 100% dos cenários de limites conhecidos cobertos por testes | REQ-MNT-002 | 0–1 | Cenários do modelo cobertos (ver `tests/unit/domain/test_status.py`); worker pendente |
| OUT-HACC-001 | Visualização segura de leitos simulados | 100% das consultas autorizadas; acesso indevido bloqueado | REQ-HACC-001 | 4 | Não iniciado |
| OUT-ENG-001 | Rastreabilidade ponta a ponta | 100% dos requisitos críticos ligados a contrato, teste e implementação | REQ-ENG-001…006, REQ-SEC-* | 0 | Verificado automaticamente por `test_traceability.py` |

## Metodologia de medição (modelo)

Para qualquer métrica de desempenho registrar: hardware, versão do Docker/Compose, imagem/commit, carga aplicada, número de amostras, percentil e método de cálculo. Sem isso, o número não entra em `CURRENT_STATE.md`.
