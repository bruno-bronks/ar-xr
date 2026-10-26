# Patch para o HACC: rota de integração somente leitura

**Status: APLICADO no HACC do usuario em 2026-10-26, com autorizacao explicita dele (3 arquivos; backup backend/app/main.py.before_integration_route); o HACC NAO foi executado por mim; falta o token no .env dele e reiniciar o backend.** Foi desenvolvido e testado numa **cópia isolada** (portas e banco próprios, dados do simulador). Passos (já feitos 1–3; faltam 4 e 5, que são seus):

1. Copie `backend/app/api/integration.py` para `HACC/backend/app/api/integration.py`.
2. Copie `backend/tests/test_integration_route.py` para `HACC/backend/tests/` (opcional; roda com `pip install pytest && python -m pytest tests` dentro do contêiner do backend).
3. Em `HACC/backend/app/main.py` adicione duas linhas:
   ```python
   from app.api.integration import router as integration_router  # junto dos outros imports de routers

   app.include_router(integration_router)  # junto dos outros include_router
   ```
4. Defina no `.env` do HACC um token aleatório (≥ 16 caracteres) **que não vai para o Git**:
   `HACC_INTEGRATION_TOKEN=<token>` e repasse ao serviço `backend` no compose (`environment: HACC_INTEGRATION_TOKEN: ${HACC_INTEGRATION_TOKEN}`; o `env_file: .env` do backend já o entrega).
5. Reinicie o backend. Sem o token a rota responde 404 (desligada).

A rota devolve só `bed_id`, `sector`, `status`, `occupied` por leito, exige `Authorization: Bearer`, não escreve nada e nunca expõe paciente. Contrato: `specs/contracts/hacc-integration.yaml`.
