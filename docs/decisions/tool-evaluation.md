# Avaliação de ferramentas

Regra (plano mestre, §0.6): identificar repositório, versão, licença, compatibilidade e documentação oficiais **antes** de instalar. Nada abaixo foi instalado sem esse passo.

## Inventário do ambiente (2026-10-19, Windows 11)

| Ferramenta | Situação |
|---|---|
| Git 2.53 | disponível |
| Docker 29.8.2 / Compose v5.5.1 | disponível, daemon ativo |
| Python | 3.13.x local; **3.12 não obtido** (download falhou por certificado TLS corporativo `UnknownIssuer`; verificação não foi desabilitada). Imagem Docker usa 3.12. |
| uv 0.11 | disponível, porém sem acesso à rede (mesmo erro TLS); usado `venv` + `pip` (que usa o repositório de certificados do sistema) |
| Node 24 / npm | disponível (não usado na Fase 0) |
| ruff, mypy | instalados no `.venv` do projeto |
| Java, LaTeX (`pdflatex`), `gh`, `mosquitto` local | **ausentes** |
| Gitleaks, Semgrep, Trivy, Schemathesis, Playwright | **não instalados** |

## Verificação formal (Z Notation)

| Opção | Requisitos | Situação |
|---|---|---|
| fuzz (typechecker Z) | binário fuzz + LaTeX | indisponível |
| CZT (Community Z Tools) | Java | indisponível (Java ausente) |
| Z/EVES, ProofPower | licenças/instalação específicas | não avaliados |
| Alloy / TLA+ (alternativas) | Java | indisponível |

**Resultado:** as specs Z em `specs/formal-z/*.tex` foram escritas à mão e **não foram typecheckadas nem provadas**. A validação dos invariantes é feita por *property-based tests* (Hypothesis) sobre modelos executáveis (`packages/domain`). Isso encontra contraexemplos, mas **não é prova formal**. Decisão pendente: aprovar instalação de JDK + CZT (ou fuzz) para typecheck — ver relatório da Fase 0.

## Ferramentas ambíguas (não instaladas — aguardam sua identificação)

| Termo do plano | Tratamento atual |
|---|---|
| **Graphify** | O plano pede avaliar a ferramenta específica. Existe uma skill local `graphify` (referenciada no seu `CLAUDE.md` global), mas **repositório oficial, versão e licença não foram verificados** e ela **não foi executada** neste projeto. A pasta `graph/` não foi criada. O Git e `traceability.csv` são as fontes oficiais; a matriz já é validada por teste. |
| **Dreaming** | Tratado como conceito de memória de agentes. Memória determinística = `docs/agent/CURRENT_STATE.md` versionado. Nada instalado. |
| **"the Cloud"** | Princípio arquitetural cloud-native (12-factor, containers, observabilidade, IaC). Nenhum serviço cloud contratado. |
| **Outcome** | Prática Outcome-Driven: cada REQ mapeia um OUT-* em `docs/outcomes/metrics.md`. Nenhuma ferramenta. |

## Dependências adotadas na Fase 0
Pinadas em `services/api/requirements.txt` (runtime) e em `pyproject.toml` (dev, faixas mínimas). Licenças dos pacotes principais (FastAPI, Starlette, Pydantic, SQLAlchemy, Uvicorn: MIT/BSD; psycopg: LGPL-3.0) devem ser revisadas antes de distribuição — **psycopg é LGPL** (uso como biblioteca dinâmica é o caso comum; confirmar com jurídico se houver distribuição de binários).
