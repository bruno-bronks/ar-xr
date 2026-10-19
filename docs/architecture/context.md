# C4 — Nível 1: Contexto

```mermaid
C4Context
  title Spatial AI Platform — Contexto (alvo do MVP; Fase 0 implementa apenas a base)
  Person(op, "Operador de manutenção", "Escaneia QR e consulta telemetria")
  Person(mgr, "Gestor hospitalar", "Visualiza leitos simulados (Fase 4)")
  System(sp, "Spatial AI Platform", "API, ingestão de telemetria, digital twin, assistente")
  System_Ext(hacc, "HACC (existente)", "Sistema independente; acesso somente leitura via adapter (Fase 4)")
  System_Ext(llm, "Provedor LLM (opcional)", "Interface configurável; modo mock obrigatório (Fase 3)")
  System_Ext(eq, "Equipamentos / simulador", "Publicam telemetria via MQTT")
  Rel(op, sp, "Usa", "HTTPS / AR")
  Rel(mgr, sp, "Usa", "HTTPS")
  Rel(eq, sp, "Telemetria", "MQTT")
  Rel(sp, hacc, "Lê dados simulados", "HTTP, somente leitura")
  Rel(sp, llm, "Consulta", "HTTPS")
```

**Estado na Fase 0:** só existe o contêiner `api` com health, PostgreSQL e Mosquitto. Tudo o mais é alvo (planejado).

## Fronteiras de confiança
1. Cliente (AR/web) → API: não confiável; autenticação e autorização por organização.
2. Equipamento → broker: não confiável (spoofing/replay); ACL por equipamento fora de dev.
3. API → HACC: sistema externo; adapter isolado, sem banco compartilhado.
4. API → LLM: dados enviados são minimizados; resposta tratada como não confiável.
