# Visão do produto

## Problema

Operadores de manutenção perdem tempo localizando o equipamento certo, consultando telemetria em sistemas separados e buscando manuais. No ambiente hospitalar, gestores precisam de uma visão espacial de leitos e alertas operacionais.

## Produtos

| | Produto A — AR Maintenance AI | Produto B — HACC Spatial |
|---|---|---|
| Ator principal | Operador / técnico de manutenção | Gestor operacional hospitalar |
| Fluxo | Escaneia QR/marker → vê telemetria em sobreposição → consulta manual e histórico → recebe hipóteses da IA com fontes | Visualiza leitos e alertas sobre dados **simulados** |
| Primeiro MVP | **Sim** | Segunda integração (Fase 4) |
| Limite de atuação | Nenhuma ação física automática; IA apenas assistiva | Nenhuma recomendação clínica autônoma; dados reais só após LGPD, autorização, controle de acesso e validação clínica |

## Princípios

1. **Software funcional antes de documentação.** Cada fase entrega código executável, testes e evidências.
2. **Alerta determinístico ≠ hipótese de IA.** Regras de limiar são código testável; a IA só sugere, com fonte e incerteza.
3. **Ausência de dado não é normalidade.** Dado ausente ou atrasado vira `UNKNOWN`/`OFFLINE`.
4. **Modular primeiro.** Três deployables no MVP (ver [ADR-0001](../adr/0001-modular-first.md)).
5. **HACC permanece independente.** Acesso apenas por adapter/API; sem banco compartilhado.
6. **Nada declarado como validado sem evidência executada.**

## Fora de escopo (Fase 0)

AR nativa (Unity), IA/LLM, integração HACC, visão computacional, IoT real, cloud. Ver roadmap no [plano mestre](../../SPATIAL_AI_ANTIGRAVITY_MASTER_PLAN.md#12-roadmap-com-critérios-de-conclusão).
