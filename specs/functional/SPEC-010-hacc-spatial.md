# SPEC-010 — HACC Spatial: leitos simulados, adapter somente leitura e planta 2D

Requisitos: REQ-HACC-001 … REQ-HACC-006 · Contratos: [`openapi.yaml`](../contracts/openapi.yaml) (`/hacc/*`) e [`hacc-readonly.yaml`](../contracts/hacc-readonly.yaml) (contrato **assumido** do HACC) · Decisões: D-025…D-031 · Z: [z-006](../formal-z/z-006-bed-status.tex) · ADR: [ADR-0005](../../docs/adr/0005-hacc-adapter-and-scopes.md).

## Problema e atores
Um profissional de enfermagem/operação vê, sobre a planta de uma ala, o estado **operacional** de cada leito (alarme de saída, alarme de bomba de infusão, botão de chamada, limpeza pendente) a partir de dados **simulados** do HACC. Não há recomendação clínica, sinais vitais, diagnóstico nem identificação de paciente. Atores: usuário com escopo `hacc:read` (demo: `demo-nurse-a/b`), a API, a fonte HACC (simulada ou HTTP), e o **HACC real, que permanece independente e intocado**.

## Limite de verificação (leia primeiro)
Eu **não sei** como o HACC real expõe seus dados. O contrato `hacc-readonly.yaml` é uma **suposição minha** (marcada `x-verified-against-real-hacc: false`). Nada foi lido do repositório/banco do HACC nem conectado a ele. O adaptador HTTP é testado contra um servidor local de teste, não contra o HACC. Antes de qualquer piloto: mapear o contrato real, avaliação LGPD, autorização e validação clínica (plano §8).

## Modelo (D-028)
`Bed`: `bed_id` (opaco), `ward_id`, `tenant_id`, `label`, `x`, `y` (inteiros ≥ 1, célula da planta), `occupied`, `flags` (`bed_exit_alarm`, `iv_pump_alarm`, `call_button`, `cleaning_due`), `observed_at` (ou ausente). `Ward`: `ward_id`, `tenant_id`, `name`, `width`, `height`. Qualquer campo extra no payload (ex.: nome, CPF, prontuário, sinais vitais) ⇒ **payload inteiro rejeitado** (`extra=forbid`).

## Estado do leito (D-029, REQ-HACC-005) — regra pura em `spatial_domain.beds`
Precedência: **OFFLINE > ALERT > ATTENTION > NORMAL**; `UNKNOWN` sem leitura.
| Condição | Estado |
|---|---|
| sem `observed_at` | `UNKNOWN` |
| `now − observed_at > 30 s` | `OFFLINE` (os alarmes velhos são ignorados; nunca `NORMAL`) |
| `bed_exit_alarm` **e** ocupado, ou `iv_pump_alarm` | `ALERT` |
| `call_button` ou `cleaning_due` | `ATTENTION` |
| nada acima | `NORMAL` |
Alertas operacionais: um por sinalizador ativo e válido (`bed_exit_alarm` só conta se ocupado), com severidade `ALERT`/`ATTENTION`; leito `OFFLINE` gera um único alerta `offline`. O estado de uma ala é o pior estado dos leitos (ordem `ALERT > OFFLINE > UNKNOWN > ATTENTION > NORMAL`, para que dado ausente nunca esconda alarme nem vire normal).

## Porta e adaptadores (REQ-HACC-002, D-026)
`HaccSource` (somente leitura): `list_wards() -> list[Ward]`, `list_beds(ward_id) -> list[Bed]`. Não existe operação de escrita.
- **`SimulatedHaccSource`** (padrão): determinística por relógio. Alas: `WARD-A1` "Ala A — Clínica (demo)" (6 leitos) e `WARD-UTI` "UTI (demo)" (4 leitos), tenant `org-a`; `WARD-B1` (2 leitos), tenant `org-b` (sentinela de isolamento). Ciclo de 60 s mostra alarmes alternados; um leito fica mudo (`OFFLINE`) e outro sem leitura (`UNKNOWN`).
- **`HttpHaccSource`** (opcional, desligado): `GET` apenas, caminhos `/v1/wards` e `/v1/wards/{ward_id}/beds`; host e esquema (`https`, ou `http` só para `127.0.0.1`/`localhost` em desenvolvimento) numa lista permitida; **sem redirecionamentos**; timeout 5 s; corpo ≤ 1 MB; JSON estrito validado; qualquer falha ⇒ `HaccUnavailable` sem corpo/URL/credencial.

## Autorização e segregação (REQ-HACC-004, D-027, D-030)
1. Autenticação Bearer (como no resto da API).
2. Escopo `hacc:read` no principal; ausente ⇒ **403** `{"detail":"forbidden"}` (audit `forbidden`).
3. Organização imposta aqui: só entram registros com `tenant_id == principal.org_id`; ala de outro tenant ≡ inexistente ⇒ **404** uniforme.
4. Auditoria `hacc.wards.list` / `hacc.beds.list` com usuário, organização, ala (id opaco) e desfecho; **nunca** estado de leito.
5. HACC indisponível/payload inválido ⇒ **503** `{"detail":"hacc source unavailable"}` (log com tipo do erro, sem detalhes).

## API (`/api/v1/hacc`)
- `GET /wards` → `[{ward_id, name, bed_count, status, alert_count}]`.
- `GET /wards/{ward_id}/beds` → `{ward:{ward_id,name,width,height}, evaluated_at, status, beds:[{bed_id,label,x,y,occupied,status,observed_at,alerts:[{severity,rule}]}]}`.
O estado **vem sempre do servidor** (D-017 se aplica também aqui): o painel não recalcula.

## Painel (REQ-HACC-006, D-031)
Seção "Leitos (HACC Spatial — dados simulados)": seletor de ala + planta em grade CSS (posição por `grid-column/row`, sem estilo inline), cada leito com rótulo, ícone + texto do estado, alertas e idade da leitura; frescor/erro como no restante do painel; sem escopo ⇒ aviso "sem permissão" e nenhum dado; troca de organização limpa tudo. O cliente AR **não** foi estendido.

## Segurança e limites
- Nenhum dado real; nenhum campo identificável; log sem dados de leito.
- Demo: tokens públicos (`demo-nurse-*`) — a API recusa iniciar em produção com auth demo.
- RBAC é parcial: só `hacc:read` é verificado; endpoints de equipamento seguem sem escopo.
- Rate limit e disjuntor **não** foram adicionados a estes endpoints (leitura barata, fonte simulada); precisam existir antes de uma fonte HTTP real.

## Integração com o HACC real (REQ-HACC-007, D-054)
- **Origem:** estudo por leitura em [hacc-real-study.md](../../docs/integration/hacc-real-study.md). O HACC 0.4 não tem alas, posições, alarmes de leito nem autenticação, e várias rotas expõem nome/idade/sexo; por isso a integração usa **uma rota nova e mínima**, `GET /integration/v1/beds` (contrato em [hacc-integration.yaml](../contracts/hacc-integration.yaml)), com Bearer e só `bed_id`, `sector`, `status` (`available|occupied|unavailable`) e `occupied` (booleano). O patch está em `docs/integration/hacc-patch/` e **foi aplicado no HACC do usuário** (2026-10-26, a pedido dele; token e reinício pendentes — sem token a rota responde 404).
- **Fonte `hacc`** (`HACC_SOURCE=hacc`, `HACC_BASE_URL`, `HACC_ALLOWED_HOSTS`, `HACC_API_TOKEN` ≥ 16 caracteres, `HACC_TENANT_ID`): `GET` por caminho fixo, host em lista, `http` só em loopback, sem redirecionamento, timeout e tamanho máximo; campo fora da lista rejeita a resposta inteira; erros nunca carregam corpo, URL ou token; cache de 2 s coalesce as várias leituras de uma requisição.
- **Mapeamento:** setor → ala pelo perfil (`ICU`→UTI 3 colunas, `Emergency`→pronto-socorro 5, `Ward`→enfermaria 5; linhas crescem com o número de leitos); posição = ordem por id em linhas; rótulo = id do leito; `occupied` do HACC; `unavailable` ⇒ **BLOQUEADO**; sem alarmes (o HACC não os tem); `observed_at` = instante do instantâneo; `tenant_id` da nossa configuração. Setor fora do perfil é ignorado; status desconhecido ⇒ 503 uniforme.
- **BLOQUEADO** (Z-006 B3b): estado operacional, não alarme; perde para alarme, pendência, leitura velha ou ausente; não piora o estado da ala. Painel 2D, vista 3D (barreira listrada + anel + texto) e API o tratam.
- **Limites:** só ocupado/livre/indisponível — a vista 3D não mostra bomba de infusão, chamada nem saída do leito com esta fonte; dados do simulador do HACC; autenticação do HACC é só o Bearer da rota nova (as demais rotas dele continuam abertas, ver o estudo); a integração **não** foi implantada na VPS.
