# Runbook — observabilidade, SLOs e alertas

Spec: [SPEC-012](../../specs/functional/SPEC-012-cloud-and-operations.md) §4 · SLOs: [slo.md](../ops/slo.md).

## Ligar
```powershell
$env:METRICS_TOKEN = "<aleatório, >= 16 caracteres>"      # NUNCA versionar; o mesmo valor vai para a API e para o Prometheus
docker compose --profile observability up -d --build       # API ganha /metrics; sobe o Prometheus em http://127.0.0.1:9090
curl -H "Authorization: Bearer $env:METRICS_TOKEN" http://127.0.0.1:8088/metrics
```
Sem `METRICS_TOKEN` a rota `/metrics` **não existe** (404). O worker expõe `:9100/metrics` apenas na rede interna do Compose. Validar regras: `python scripts/check_prometheus.py` (precisa de Docker).

## Alertas (UI: `/alerts`; sem Alertmanager, ninguém é notificado)
Severidades: `page` = agir já; `ticket` = tratar em horas.

### ApiAvailabilityFastBurn
Erros 5xx consumindo o orçamento (0,5 %) 14,4× mais rápido que o sustentável (janelas 1 h e 5 min). Veja `docker compose logs api`, `dependency_up`, última release (`deploy.py status`). Se foi a release: `deploy.py rollback`.

### ApiAvailabilitySlowBurn
Mesmo, mas 6× em 6 h/30 min: degradação lenta. Abra ticket; procure rota específica: `sum by (route)(rate(http_requests_total{status_class="5xx"}[30m]))`.

### ApiLatencySlowBurn
> 30 % das requisições acima de 500 ms por horas. Verifique carga/CPU do host e consultas lentas no PostgreSQL.

### PipelineStale
Nenhuma leitura processada há > 2 min (e já recebeu alguma antes). Cheque broker, simulador/dispositivos e `worker_mqtt_connected`.

### PipelineLagSlowBurn
> 30 % das leituras levam mais de 5 s do `observed_at` ao banco. Suspeite de fila acumulada no worker, banco lento ou relógio do dispositivo atrasado.

### WorkerBrokerDisconnected
Worker sem conexão MQTT há 2 min. Reinicie o broker/worker; confira credenciais se o broker endurecido está ligado.

### DependencyDown
`dependency_up == 0` (rótulo `dependency` = `database` ou `broker`). Veja o contêiner correspondente e o espaço em disco.

### PipelineRejectionSpike
> 20 % das mensagens rejeitadas: veja o rótulo `reason` em `worker_messages_total` (esquema, tópico ≠ equipamento, equipamento/sensor desconhecido, timestamp futuro). Dispositivo mal configurado ou abuso.

### MetricsTargetDown
Prometheus não consegue coletar a API/worker (token errado, serviço caído). Sem métricas, os demais alertas não são confiáveis.

## Regras para novos rótulos
Só valores de **baixa cardinalidade** e sem dados pessoais (rota-modelo, classe de status, enum). Nunca id de equipamento/usuário/organização, token, correlation ID ou texto livre. Há teto de séries por métrica (`metrics_series_dropped_total` conta o excedente).
