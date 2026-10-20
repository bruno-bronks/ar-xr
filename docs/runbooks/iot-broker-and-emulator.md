# Runbook — Caminho seguro até IoT: emulador de dispositivo e broker endurecido (opt-in)

Spec: [SPEC-011](../../specs/functional/SPEC-011-vision-and-iot.md) · Plano de hardware (**NÃO aprovado**): [esp32-electrical-safety-plan.md](../hardware/esp32-electrical-safety-plan.md).

> **Não há hardware, firmware nem fiação.** O emulador é software. O broker endurecido **não tem TLS** ainda: não use com dispositivos reais.

## Emulador de dispositivo (broker anônimo de desenvolvimento)
```powershell
docker compose up --build --wait
$env:PYTHONPATH = "services\equipment-simulator;packages\common\src;packages\domain\src;packages\storage\src"
.\.venv\Scripts\python.exe -m simulator.device_emulator --equipment EQ-002 --sensor temperature --value 63.2 --count 3
```
O emulador monta `telemetry-event.v1`, valida com o parser estrito do worker e publica (QoS 1) **no próprio tópico**. A leitura entra no pipeline com `source = esp32-emulator`.

## Broker endurecido (auth + ACL por dispositivo)
```powershell
.\.venv\Scripts\python.exe scripts\gen_broker_users.py --devices EQ-001,EQ-002,EQ-003   # senhas aleatórias; nunca impressas
docker compose --env-file platform\mosquitto\secure\credentials.env -f compose.yaml -f compose.secure.yaml up --build --wait
```
- `platform/mosquitto/secure/` (hashes + senhas) é **ignorado pelo Git**. Se você já usa um `.env`, passe-o também: `--env-file .env --env-file platform\mosquitto\secure\credentials.env`.
- ACL (`platform/mosquitto/secure.acl`): `worker` só lê telemetria; `simulator` escreve; `health` só lê `$SYS`; cada dispositivo (usuário = id do equipamento) escreve **apenas** em `spatial/v1/equipment/{usuário}/telemetry` e não recebe nada. Não existe tópico de comando.
- Emulador no modo endurecido: `$env:MQTT_PASSWORD = "<senha do dispositivo em credentials.env>"` e o mesmo comando acima (usuário = id do equipamento).
- Observação do Mosquitto: ele pode responder SUBACK "concedido" mesmo sem permissão de leitura; a ACL impede a **entrega** (os testes verificam isso).

## Testes
```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/test_broker_auth.py -q     # Mosquitto real em contêiner próprio (só Docker)
# com a pilha do Compose no ar (BASE_URL e TEST_DATABASE_URL definidos):
.\.venv\Scripts\python.exe -m pytest tests/integration/test_device_emulator_stack.py -q
```

## Antes de qualquer dispositivo real
Cumprir o portão G1–G7 do plano de hardware: **TLS (8883)**, revisão elétrica por profissional habilitado, firmware revisado e testado em bancada, rede isolada, plano de rollback e **aprovação explícita registrada**.
