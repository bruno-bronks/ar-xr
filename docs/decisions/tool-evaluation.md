# Avaliação de ferramentas

Regra (plano mestre, §0.6): identificar repositório, versão, licença, compatibilidade e documentação oficiais **antes** de instalar. Atualizado na Fase 1 (2026-10-19).

## Instaladas e usadas

| Ferramenta | Versão | Licença | Fonte oficial | Instalação | Uso no projeto |
|---|---|---|---|---|---|
| **Eclipse Temurin JDK** | 21.0.12.1 LTS | GPL-2.0 + Classpath Exception | [Adoptium](https://adoptium.net) · API `api.adoptium.net` | zip oficial em `%USERPROFILE%\.tools\jdk-21.0.12.1+1` (o `winget` exigia elevação/admin); **SHA-256 verificado** `f9d6e191…d8b4e` contra a API da Adoptium | runtime do CZT |
| **CZT — Community Z Tools** | 1.6-SNAPSHOT (nightly 2015-09-12, único `czt.jar` publicado) | GPL-2.0 | [SourceForge czt](https://sourceforge.net/projects/czt/) · [GitHub community-z-users/czt](https://github.com/community-z-users/czt) | `czt.jar` em `%USERPROFILE%\.tools\czt`; **SHA-256 verificado** `5065a920…52d22` (valor publicado pelo SourceForge) | parse + typecheck das specs Z (`scripts/verify-z.ps1`, `tests/unit/repo/test_formal_z.py`) |
| **Graphify** | 0.9.91 (PyPI: 0.9.92) | Apache-2.0 | PyPI `graphifyy` · [docs.graphify.com](https://docs.graphify.com) · [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) | já instalado via `uv tool` (não reinstalado) | índice auxiliar de código/docs; cruzamento com a matriz (`graph/`) |
| Alembic 1.20 · SQLAlchemy 2.1 · psycopg 3.3 | pins em `services/*/requirements.txt` | MIT / MIT / **LGPL-3.0** | PyPI | `pip` | migrações e acesso a dados |
| paho-mqtt 2.1 | idem | EPL-2.0 / EDL-1.0 | [eclipse/paho.mqtt.python](https://github.com/eclipse/paho.mqtt.python) | `pip` | worker e simulador |
| **.NET SDK** | 10.0.402 (LTS) | MIT | [dotnet.microsoft.com](https://dotnet.microsoft.com) · `builds.dotnet.microsoft.com` | zip oficial em `%USERPROFILE%\.tools\dotnet`; **SHA-512 verificado** (`ae4fd528…898cd`) contra o `releases.json` oficial | compila o núcleo C# localmente (contra stub); testes xUnit rodam na CI |
| **segno** 1.6.6 (QR) · **opencv-python-headless** 5.0.0 | — | BSD-3 · Apache-2.0 | PyPI | `pip` (funciona no proxy) | gerador dos QR de teste; decodificação independente nos testes |
| xUnit 2.9.2 · Newtonsoft.Json 13.0.3 · ZXing.Net 0.16.9 | — | Apache-2.0 · MIT · Apache-2.0 | NuGet | **só na CI** (ver abaixo) | testes do núcleo C#; ZXing é a biblioteca de QR do app |
| Playwright 1.64 (Python) | dev | Apache-2.0 | [playwright.dev](https://playwright.dev/python) | `pip`; usa o **Microsoft Edge já instalado** (`channel="msedge"`) — nenhum navegador foi baixado | E2E do painel |

> Licenças dos pacotes Python acima vêm do conhecimento geral das bibliotecas e **não foram auditadas** pacote a pacote; `psycopg` é LGPL-3.0 (uso como biblioteca dinâmica é o caso comum — confirmar com jurídico antes de distribuir binários).

### Resultado real do CZT
O typechecker **encontrou erros reais** nas specs Z escritas à mão na Fase 0 (comando `\max` inexistente, `[ ]` usado como agrupamento de predicado, conjecturas sem `⊢?`, `\\` dentro de predicado entre parênteses, nome de esquema antes de `⊢?`). Após a correção, os 3 arquivos (`z-002`, `z-003`, `z-004`) passam com `0 warnings and errors`; um erro de tipo injetado (`warn ≤ GOOD`) é rejeitado com `Type mismatch`. **O que isso NÃO é:** o CZT aqui valida **sintaxe e tipos**; nenhuma conjectura (`⊢?`) foi provada (isso exigiria Z/EVES ou outro provador). Os invariantes continuam validados por Hypothesis.

## Rede corporativa: o que está bloqueado (e o que NÃO foi contornado)
O proxy da rede do desenvolvedor responde **"File Transfer Blocked"** ao baixar `.nupkg` do NuGet (o índice do feed responde 200, o arquivo do pacote devolve 503). Isso é um controle de segurança da organização: **não foi contornado** (nenhum espelho alternativo, renomeação ou desativação de verificação). Consequências e soluções:
- Testes C# (xUnit/Newtonsoft/ZXing) **não rodam localmente**; rodam no job `csharp` da CI do GitHub (sem esse bloqueio). Localmente só é possível **compilar** o núcleo contra um stub do Newtonsoft.
- O `restore` falhava também na checagem de revogação de certificado (OCSP/CRL bloqueados): `NUGET_CERT_REVOCATION_MODE=offline` é o ajuste oficial do NuGet para isso (a cadeia do certificado continua validada).
- `zxing.dll` (netstandard2.1, para o Unity) precisa ser obtido em rede sem o bloqueio: `scripts/fetch-zxing-unity.ps1` (SHA-256 do `.nupkg` pinado a partir da saída da CI: `00254aca…f32e`). **Correção:** eu havia assumido que o pacote traria `lib/unity`; a CI mostrou que não traz — usa-se `netstandard2.1`, a mesma variante testada.
- Se TI liberar `.nupkg` (ou fornecer um feed interno), os testes C# passam a rodar localmente sem mudanças.

## Graphify — como foi usado (e limites)
- `graphify update .` (AST local, **sem LLM e sem custo**): 1063 nós · 2523 arestas · 70 comunidades na Fase 1.
- **Não usado:** extração semântica por LLM (exigiria chave de API/modelo — decisão sua), hooks no `settings.json`, servidor MCP, exports Neo4j.
- O Git e `traceability.csv` seguem como fonte oficial; o grafo é auxiliar (ver [`graph/README.md`](../../graph/README.md)).
- Durante o uso, a primeira versão do cruzamento "confirmava" 100% dos testes porque o caminho passava por nós externos (`pytest`, `datetime`). O defeito foi corrigido (nós externos não são evidência) e coberto por teste de regressão.

## Dreaming — ainda NÃO instalado/usado (decisão sua)
Pesquisa na documentação oficial (platform.claude.com/docs/en/managed-agents/dreams):

| Fato | Detalhe |
|---|---|
| O que é | **Recurso de nuvem** do Claude Managed Agents: um *dream* é um job assíncrono que lê um *memory store* existente + 1–100 sessões passadas e **gera um novo memory store** reorganizado (duplicatas fundidas, entradas obsoletas substituídas). O store de entrada nunca é alterado. |
| Disponibilidade | **Research preview** (pode mudar sem aviso). Exige **solicitar acesso** (formulário), API key da Anthropic e os cabeçalhos beta `managed-agents-2026-04-01` + `dreaming-2026-04-21`. |
| Custo | Cobrado por tokens de API do modelo escolhido (`claude-opus-5-5`, `claude-sonnet-5-5` etc.), proporcional ao nº/tamanho das sessões. |
| "Instalar"? | **Não há nada para instalar**: é um endpoint de API (`POST /v1/dreams`). Existe também o comando não documentado `/dream` do Claude Code, citado apenas por blogs de terceiros — **não verificado**. |

Por que parei: usar o Dreaming oficial exige **credencial paga e acesso aprovado** — exatamente o tipo de decisão que o plano reserva a você (§13.10, "contratar serviços cloud"). **Nada foi inventado nem simulado.**

O que já existe para recebê-lo com segurança (plano §9: "memória gerada nunca altera specs/ADRs/código sem PR"):
- `docs/agent/CURRENT_STATE.md` como memória determinística versionada;
- `tests/unit/repo/test_agent_memory.py`: quebra o build se a memória citar arquivos/REQs inexistentes (o problema de "entradas obsoletas" que o Dreaming resolve);
- qualquer saída de um dream futuro entra **só por PR** em `docs/agent/` (nunca em `specs/`, `docs/adr/` ou código).

Opções para você decidir: ver relatório final.

## Ainda não instaladas (aguardam necessidade/aprovação)
Gitleaks, Semgrep, Trivy, Schemathesis, `cyclonedx-bom` (SBOM): rodam na CI (não executada) ou ainda não foram adicionados. Z/EVES (provador): não avaliado.

## Inventário do ambiente (2026-10-19, Windows 11)
Git 2.53 · Docker 29.8.2 / Compose v5.5.1 · Python 3.13 local (**3.12 não obtido**: o download do `uv` falha com `invalid peer certificate: UnknownIssuer` no proxy TLS corporativo; a verificação de certificado **não** foi desabilitada; imagens Docker usam 3.12) · Node 24 · Edge 140+/Chrome instalados · `gh`/LaTeX/`mosquitto` locais: ausentes.
