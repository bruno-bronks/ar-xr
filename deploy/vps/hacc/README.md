# Cópia isolada do HACC na VPS (teste online da integração, D-055)

**Dados do simulador. Não é o HACC do usuário** (não leva o `.env`, o banco nem as credenciais dele): é o código do HACC com a rota de integração (`docs/integration/hacc-patch`), imagens construídas localmente (`hacc-copy-backend`, `hacc-copy-hospital-simulator`) e enviadas com `docker save | docker load`, como as do AR_XR.

- Pasta no servidor: `/opt/hacc-copy` (`compose.yaml`, `mosquitto/mosquitto.conf`, `.env` 0600).
- Segredos **gerados no servidor** (`openssl rand`): `HACC_DB_PASSWORD` e `HACC_INTEGRATION_TOKEN`; o mesmo token entra como `HACC_API_TOKEN` em `/opt/ar-xr/.env`.
- Rede: backend só em `127.0.0.1:28000` no host e como `hacc-backend` na rede `spatial-ai_default`; broker e banco **sem** porta publicada.
- API do AR_XR (`/opt/ar-xr/.env`): `HACC_SOURCE=hacc`, `HACC_BASE_URL=http://hacc-backend:8000`, `HACC_ALLOWED_HOSTS=hacc-backend`, `HACC_API_TOKEN`, `HACC_TENANT_ID=org-a`, `HACC_ALLOW_PLAIN_HTTP=true` (http só dentro da rede privada do Docker).
- Limites de recursos em todos os serviços (servidor compartilhado). Desfazer: `docker compose -p hacc-copy down -v` e remover as variáveis `HACC_*` de `/opt/ar-xr/.env` (a API volta à fonte simulada).
