# Estudo de integração com o HACC real (leitura do código, 2026-10-26)

> **Natureza:** análise por **leitura** do projeto HACC (pasta `Projetos\HACC`, versão do backend 0.4.0), autorizada pelo usuário. Nada foi executado, alterado, instalado nem conectado; o HACC **não** é um repositório Git (não há histórico). **Não foram abertos:** `.env`, credenciais do Node-RED, estado do simulador, `mosquitto.db`. Nada do código do HACC foi copiado para cá. Este documento descreve o que o código **faz**, não o que roda em produção; nenhum endpoint foi chamado.

## 1. O que o HACC é (como está no código)
FastAPI + PostgreSQL + MQTT (Mosquitto) + Node-RED + Grafana + um simulador hospitalar. O estado do hospital é **derivado de eventos**: eventos chegam por MQTT (QoS 1, com ACK) ou `POST /events/`, são deduplicados por `event_id`/hash (idempotência; conflito ⇒ 409) e aplicados por um processador a duas tabelas, `beds` e `patients`. Há uma camada de "inteligência" (ocupação, setores saturados, inconsistências), um agente e uma rota com LLM (`LLM_PROVIDER=mock` por padrão; `openrouter` opcional).

**Leitos (`init_beds.py`):** 35 leitos em 3 setores: `Emergency` (`ER-01…ER-10`), `Ward` (`WARD-01…WARD-20`), `ICU` (`UTI-01…UTI-05`).

**Eventos tratados:** `patient_admission`, `patient_status_change`, `patient_discharge`, `bed_unavailable`.

## 2. Modelo de dados (relevante para a integração)
| Tabela | Campos |
|---|---|
| `beds` | `id`, `sector`, `status` (`available` \| `occupied` \| `unavailable`), `patient_id` |
| `patients` | `id`, **`name`, `age`, `gender`**, `priority` (`critical`…), `sector`, `bed_id`, `status` |
| `events` | `event_id`, `event_hash`, `event_type`, `patient_id`, `bed_id`, `source`, `payload` (JSON), `created_at` |

## 3. Endpoints de leitura (todos **sem autenticação** no código)
| Endpoint | Devolve | Serve para nós? |
|---|---|---|
| `GET /beds/` | `id`, `sector`, `status`, **`patient_id`** por leito | **Sim**, com ressalva (ver §5) |
| `GET /beds/summary`, `/beds/sectors` | contagens e ocupação por setor | Opcional (painel agregado) |
| `GET /beds/unassigned-patients` | **`name`**, prioridade, setor, status | **Não** (dado pessoal) |
| `GET /digital-twin/` | leitos + **pacientes com `name`, `age`, `gender`** + alertas + `recommendation` | **Não** como está |
| `GET /events/` | 100 últimos eventos com **`payload`** completo (inclui nome/idade/sexo nas admissões) | **Não** |
| `GET /intelligence/analyze`, `/bed-agent/analyze`, `/ai/bed`, `/context/bed` | análises e recomendações (agente/LLM) | **Não** (recomendação clínica/operacional autônoma; fora do escopo e com risco) |
| `GET/POST /rejected-events/…` | fila de rejeitados, reprocesso e resolução | **Não** (escrita, operação interna) |
| `POST /events/` | **escreve** estado | **Nunca** (nosso adaptador é somente leitura) |

## 4. Divergências com o contrato que assumi (`specs/contracts/hacc-readonly.yaml`)
| Nosso contrato assumido | HACC real | Consequência |
|---|---|---|
| Ala com `ward_id`, `name`, grade `width × height` | só `sector` (3 valores); sem dimensões | Layout (grade, nomes de ala) tem de ser **configurado do nosso lado** |
| Leito com posição `x`, `y` | não existe | idem: mapear `UTI-01…05` etc. para a grade em configuração |
| Sinalizadores `bed_exit_alarm`, `iv_pump_alarm`, `call_button`, `cleaning_due` | **não existem**; há `available/occupied/unavailable` | Os estados `ALERT`/`ATTENTION` das regras atuais **não teriam origem**; só ocupado/livre/indisponível |
| `observed_at` por leito (frescor ⇒ `OFFLINE` em 30 s) | leito **não tem** timestamp; o estado é derivado de eventos e pode ficar horas igual | A regra "leitura velha ⇒ OFFLINE" **não se aplica**; frescor precisa vir de outra fonte (ex.: última atualização de evento por leito) ou ser abandonado |
| `tenant_id` por registro (segregação) | **mono-organização**; sem tenant | O tenant é imposto **pela nossa configuração** (D-030 já prevê); o HACC não segrega |
| Autenticação | **nenhuma** | Nosso adaptador precisa de rede privada/allowlist; recomendar credencial no HACC (decisão sua) |
| Payload com campo fora da lista ⇒ rejeitado por inteiro | `GET /beds/` devolve `patient_id` (fora da lista) | O adaptador atual **rejeitaria** a resposta; ver §5 |

## 5. Riscos e achados (no HACC, para decisão sua; na análise não alterei nada)
1. **Sem autenticação nem autorização** em nenhuma rota, inclusive as que devolvem **nome, idade e sexo** de pacientes (`/digital-twin/`, `/beds/unassigned-patients`, `/events/`). Com dados reais isso é exposição de dado sensível de saúde (LGPD). Hoje é aceitável só porque o conteúdo é simulado.
2. O compose publica a porta do backend como `"${BACKEND_PORT}:8000"` (sem `127.0.0.1`): em geral isso a expõe em **todas as interfaces** da máquina/servidor. Confirme o valor no seu `.env` e o firewall.
3. Sem CORS nem limite de taxa; rotas de escrita (`POST /events/`, `/rejected-events/*/retry|resolve`) abertas.
4. `patient_id` aparece em `GET /beds/`: se for um identificador real (prontuário/CPF), vaza dado pessoal mesmo sem o nome. Convém ser id opaco por internação.
5. A rota com LLM (`LLM_PROVIDER=openrouter`) enviaria contexto a um serviço externo: confirmar que **nunca** inclui dado de paciente (o `context_builder` que li usa só contagens e a análise do agente; **não verifiquei** todos os caminhos).
6. Backups e `*.before_*` espalhados na pasta e o `.env` na raiz do projeto: cuidado ao versionar (não abri o `.env`; não sei o que há nele).

## 6. Como integrar (proposta; depende da sua aprovação)
**Recomendada — contrato de integração explícito no HACC (você decide e faz no seu projeto):** uma rota somente leitura nova, por exemplo `GET /integration/v1/beds`, que devolve **apenas** `bed_id`, `sector`, `status`, `occupied` (e, se existir, `updated_at` por leito), **sem** `patient_id`, nome, idade, sexo, prioridade nem payload, protegida por credencial (Bearer) e ligada só em rede privada. Assim a minimização acontece na origem e o nosso adaptador continua com a política "campo fora da lista ⇒ rejeita".

**Alternativa sem mexer no HACC (interina):** o adaptador consome `GET /beds/` e **descarta explicitamente** só `patient_id` antes de validar (lista de descarte fixa, documentada e testada), nunca lê os outros endpoints e usa host/porta em allowlist, sem redirecionamento, com timeout e limite de tamanho (já existe). Menos seguro: o dado ainda trafega na resposta.

**Do nosso lado (qualquer das duas):**
1. Contrato **observado** `specs/contracts/hacc-real-observed.yaml` (substitui o assumido) e um *perfil* do adaptador para o HACC 0.4: `sector`→ala, ids→células da grade (configuração), `status`→estado.
2. **Mapeamento de estados (decisão sua):** `occupied`/`available` ⇒ ocupação; `unavailable` ⇒ `ATTENTION` ("leito indisponível") ou `OFFLINE`? Como o HACC não tem alarmes de leito, a vista 3D mostraria **ocupação e indisponibilidade**, não "bomba de infusão/chamada/saída". Os alarmes continuariam possíveis só se o HACC passar a emitir esses eventos.
3. **Frescor:** definir se `OFFLINE` vem de um `updated_at` por leito (precisa do HACC) ou se a regra de 30 s é suspensa para essa fonte.
4. Layout 3D para os setores reais: `ICU` 5 leitos, `Emergency` 10, `Ward` 20 (grades 5×1, 5×2, 5×4).
5. Testes com **fixtures sintéticas** no formato real e, depois, contra o HACC **rodando numa cópia isolada** (portas e banco próprios, dados fictícios), nunca contra a instalação do usuário.
6. Rate limit e disjuntor no `/hacc` (pendência minha D-029+), e a conexão real só **desligada por padrão** (`HACC_SOURCE=http` com host em allowlist), ligada por você.

## 7. Decisões que preciso de você
1. Rota de integração nova no HACC (recomendada) **ou** o descarte de `patient_id` no nosso adaptador (interina)?
2. `unavailable` ⇒ `ATTENTION`, `OFFLINE` ou um estado novo ("Bloqueado")?
3. Posso rodar uma **cópia** do HACC (copiada para uma pasta temporária, com portas e banco próprios) para observar as respostas reais? Ou prefere me passar exemplos de resposta?
4. Os leitos reais do hospital seguem `ER-xx`/`WARD-xx`/`UTI-xx` ou isso é só o simulador?

## 8. Decisões do usuário e andamento (2026-10-26)
1. **Rota de integração nova no HACC** (recomendada) — escolhida. Implementada e testada numa **cópia isolada**; patch em [hacc-patch/](hacc-patch/README.md), **aplicado no HACC do usuário em 2026-10-26** a pedido dele (3 arquivos, backup de `main.py`; não executei o HACC dele nem toquei no `.env`).
2. **`unavailable` ⇒ "Bloqueado"** — estado `BLOCKED` no domínio (Z-006 B3b), painel 2D, API e vista 3D.
3. **Pode rodar uma cópia** — cópia em pasta temporária (sem `.env`, credenciais nem estado do simulador), compose próprio, portas 28000/25432, dados do simulador.
4. **"É o simulador, mas pode usar como real"** — tratado como fonte real (D-054); isso não autoriza expor dado de paciente: a rota nunca o devolve.
**Evidência:** `tests/integration/test_hacc_real.py` (3 testes contra a cópia, incl. conferência cruzada com o `/beds/summary` do HACC), capturas `docs/evidence/phase-4/hacc-real-*.png`. **Pendente:** o usuário definir `HACC_INTEGRATION_TOKEN` no `.env` do HACC e reiniciar o backend, e decidir se a integração entra na VPS (o HACC teria de ser alcançável por HTTPS).
