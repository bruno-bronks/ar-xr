# Implantação no VPS (demonstração)

Servidor **compartilhado** com outros projetos em produção: não alterar o que não é deste projeto.

- Pilha em `/opt/ar-xr/` com `compose.yaml` + [compose.override.yaml](compose.override.yaml) (limites de CPU/memória, rotação de logs, `restart`). API, PostgreSQL e MQTT escutam **somente em 127.0.0.1** (8088, 55432, 1883).
- Exposição pública apenas via nginx em `https://ar-xr.bronks.ia.br` ([nginx-ar-xr.conf.template](nginx-ar-xr.conf.template)): login básico em `/panel/`, cookie para `/api/`, somente `GET`/`HEAD`, **exceto** `POST /api/v1/assistant/questions` (assistente apenas informativo, mesmo cookie); demais rotas 404. O hostname usa hífen porque underscore não é válido para certificado TLS.
- A autenticação da API continua **demo** (tokens fictícios públicos) e o Mosquitto é anônimo; por isso nada além do painel de leitura é exposto. O app Unity (que faz `POST` em markers e usa o token Bearer) **não** usa este domínio.
- Dados são simulados; nenhum dado hospitalar real.
- Imagens construídas localmente e enviadas com `docker save | docker load`; `.env` fica só no servidor (modo 600). Senhas, hash do login e o valor do cookie **nunca** vão para o repositório.
