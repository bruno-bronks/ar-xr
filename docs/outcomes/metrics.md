# Outcomes e métricas

As metas abaixo são **propostas**, não resultados garantidos. Toda medição registra ambiente e metodologia; sem isso o número não entra aqui.

| ID | Outcome | Métrica de validação | Requisitos | Estado após a Fase 1 |
|---|---|---|---|---|
| OUT-MNT-001 | Identificação correta de equipamentos | 100% dos 3 QR de teste mapeados corretamente | REQ-MNT-001, REQ-MNT-007 | **API: 3/3 corretos** por HTTP na pilha real e nos repositórios (memória e PostgreSQL), sem vazamento entre organizações. **AR/câmera (Fase 2): não validado.** |
| OUT-MNT-002 | Telemetria apresentada rapidamente | p95 de atualização API→cliente < 3 s em ambiente de teste definido | REQ-MNT-003, REQ-UX-001 | **Pipeline publicar→visível na API: p95 = 0,276 s (n = 100, p50 0,116 s, máx 0,370 s)**; painel (atualiza a cada 2 s): limite superior p95 ≈ 2,28 s. **Atende a meta proposta neste ambiente** — 1 máquina Windows, loopback, sem carga, polling de 50 ms. Detalhes: `docs/evidence/phase-1/latency.json`. Não representa produção. |
| OUT-MNT-003 | Alertas consistentes | 100% dos cenários de limites conhecidos cobertos por testes | REQ-MNT-002, REQ-MNT-004, REQ-SIM-001 | **Cobertos por testes** (limiar exato, acima de warn/crit, BAD, sensor ausente/velho, offline, transições, offline por silêncio em tempo real). Invariantes I1–I7 por Hypothesis. Nenhuma prova formal. |
| OUT-HACC-001 | Visualização segura de leitos simulados | 100% das consultas autorizadas; acesso indevido bloqueado | REQ-SEC-003, REQ-HACC-001 | **Parcial:** isolamento por organização bloqueia 100% dos acessos cruzados testados (equipamentos simulados industriais, auth *demo*). Leitos/HACC: Fase 4, não iniciado. |
| OUT-ENG-001 | Rastreabilidade ponta a ponta | 100% dos requisitos críticos ligados a contrato, teste e implementação | REQ-ENG-*, REQ-SEC-* | **Verificado automaticamente** (`test_traceability.py`, `test_trace_edges.py`); arestas verificadas em `graph/mappings/`. |

## Metodologia de medição (modelo)

Para qualquer métrica de desempenho registrar: hardware, versão do Docker/Compose, imagem/commit, carga aplicada, número de amostras, percentil e método de cálculo, **e as limitações do método**. Um erro de método já ocorreu e foi corrigido: a primeira versão da medição de latência incluía o tempo de conectar/desconectar o cliente MQTT do teste (≈ 1 s) e reportava um número falsamente pessimista; o cronômetro agora usa um publicador persistente e mede só do `publish` até a visibilidade na API.
