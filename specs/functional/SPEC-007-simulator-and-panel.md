# SPEC-007 — Simulador de equipamentos e painel web 2D

Requisitos: REQ-SIM-001, REQ-UX-001.

## Simulador (`services/equipment-simulator`)
Publica no tópico `spatial/v1/equipment/{id}/telemetry` (QoS 1, `retain=false`), `source = "equipment-simulator"`, `event_id = "<equipment>-<sensor>-<seq>"`, a cada `SIM_INTERVAL_SECONDS` (padrão 2 s) por sensor. Gerador **determinístico** (semente `SIM_SEED`, padrão 42): a função `reading(equipment, sensor, tick)` é pura e testável.

| Equipamento | Cenário | Comportamento por ciclo de `SIM_CYCLE_TICKS` ticks (padrão 120 ≈ 4 min) |
|---|---|---|
| EQ-001 | `steady` | temperatura e vibração estáveis abaixo de `warn` (ruído pequeno) |
| EQ-002 | `ramp` | temperatura sobe linearmente de ~55% de `warn` até acima de `crit` no meio do ciclo, mantém, e volta ⇒ `NORMAL → WARNING → CRITICAL → NORMAL` |
| EQ-003 | `dropout` | normal, mas **silencia** (não publica) durante 40% do ciclo ⇒ `OFFLINE` após `offline_after` |

Extras configuráveis: `SIM_DUPLICATE_EVERY` (reenvia o mesmo `event_id` a cada N mensagens; padrão 7) e `SIM_LATE_EVERY` (reenvia leitura antiga fora de ordem; padrão 0 = desligado). Reconecta ao broker com backoff; nunca encerra por erro de rede.

## Painel (`clients/web-fallback`)
Página estática (HTML + JS vanilla, sem CDN). Fluxo: o usuário escolhe organização demo (token fictício) ⇒ `GET /api/v1/equipment` a cada 2 s ⇒ para cada equipamento `GET .../twin` e `GET .../alerts`.

Regras de apresentação (REQ-UX-001):
- Um cartão por equipamento com **estado em texto e cor** (nunca só cor): `NORMAL`, `WARNING`, `CRITICAL`, `OFFLINE`, `UNKNOWN`.
- `OFFLINE` e `UNKNOWN` aparecem como estados próprios e com mensagem ("sem dados recentes"); jamais exibidos como normais.
- Leituras (valor, unidade, idade em s) e limites; leituras não válidas marcadas.
- Faixa de alertas ativos no topo (contagem + lista).
- Erro de API/401 ⇒ banner de erro visível, sem apagar o último estado (marcado como desatualizado).
- Acessível: contraste, `aria-live` para alertas, funciona em 360 px de largura.
- Valores vindos da API são inseridos como **texto** (sem `innerHTML`) ⇒ sem XSS.

## Planta 2D dos equipamentos (REQ-UX-003, D-051)
O painel ganhou uma **vista espacial 2D**: uma planta com dois galpões (A e B) e um marcador por equipamento. É uma planta de **demonstração**: as posições são **ilustrativas**, fixas na configuração do painel (`PLANT` em `app.js`, por id), **fora de escala** e **não** vêm da API nem do banco (sem migração, sem mudança de contrato). Posições reais dependem de um cadastro de ativos/marcadores espaciais que ainda não existe.
- **Marcador** = botão nativo (foco e Enter/Espaço grátis) com **ícone + nome + estado em texto**, mais `data-status` para a cor; o estado é o do twin (`NORMAL`/`WARNING`/`CRITICAL`/`OFFLINE`/`UNKNOWN`), nunca só cor; dado ausente é Offline/Desconhecido.
- **Clique/Enter** leva ao cartão do equipamento (foco + `data-selected`); os marcadores são atualizados **em lugar** (por id) para o foco do teclado não se perder a cada ciclo de 2 s.
- Equipamento **sem posição** é listado em "Sem posição na planta" (nunca descartado nem posicionado por chute).
- Troca de organização limpa a planta; falha da API mantém o último estado marcado como desatualizado (`data-stale`); todo texto da API entra como texto (nunca HTML); funciona em 360 px sem rolagem horizontal e sem violar a CSP.
- **Limite:** não é um gêmeo 3D nem uma planta real do local. A vista 3D e o AR continuam sendo o cliente Unity (Fase 2), não validado em aparelho.

## Vista 3D (REQ-UX-004, D-052, [ADR-0008](../../docs/adr/0008-web-3d-viewer.md))
Seção "Vista 3D dos equipamentos" no painel: cena WebGL de um **galpão** com um **modelo 3D por equipamento**, escolhido pelo **tipo** cadastrado (`compressor` → compressor de ar com reservatório, `bomba` → bomba centrífuga, `motor` → motor trifásico; outro tipo → unidade genérica). **Procedural** e **ilustrativo**: não é CAD nem o local real; posições vêm da configuração da planta 2D (D-051).
- **Estado** (do twin, nunca calculado no cliente): sinalizador luminoso (verde/âmbar/vermelho; vermelho pulsa em `CRITICAL`), anel colorido no piso e **rótulo DOM** com ícone, nome, estado em **texto** e as leituras (temperatura, vibração). `OFFLINE`/`UNKNOWN`: sinalizador apagado, anel cinza/roxo e texto explícito — nunca "normal".
- **Interação:** arrastar gira, roda aproxima, clique/Enter no rótulo, botões de foco ou clique na máquina move a câmera (animada) e seleciona o cartão; "Visão geral" e duplo clique voltam; clicar num marcador da planta 2D também foca o 3D. Rótulos e botões são nativos (teclado/leitor de tela).
- **Qualidade:** "Alta" (MSAA 4×, oclusão ambiente GTAO, bloom, sombras 2048, pixel ratio ≤ 2), "Média" (sem AO) e "Baixa" (renderização direta); padrão por heurística, ajustável no painel (`?q3d=alta|media|baixa` força). Renderiza **sob demanda** e pausa fora da tela. `prefers-reduced-motion`: sem pulso e câmera sem animação.
- **Robustez:** troca de organização limpa a cena; falha da API mantém a última cena marcada como desatualizada (`data-stale`); sem WebGL 2 (ou contexto perdido) mostra mensagem e o resto do painel segue; texto da API só via `textContent`; sem requisições externas; CSP respeitada.
- **Supply chain:** `clients/viewer3d` (fonte + `package-lock.json`) → `clients/web-fallback/vendor/viewer3d.js` com manifesto SHA-256; a CI refaz o build e compara.
- **Limites:** validado com WebGL **por software** (SwiftShader) no Edge/Chrome headless; **não** medido em GPU real nem em celular; modelos ilustrativos; não é o cliente AR (Unity, Fase 2).

## Critérios de aceitação
- Unidade: `tests/unit/simulator/test_scenarios.py` (determinismo, cenários, duplicatas).
- E2E (Playwright com Microsoft Edge instalado): `tests/e2e/test_panel.py` — inclui a planta 2D (REQ-UX-003); o painel mostra alerta para EQ-002, `OFFLINE` para EQ-003 no estado de dropout, e erro visível com token inválido.
- Integração de pilha: `tests/integration/test_stack_flow.py` — simulador → broker → worker → banco → API mostra estado atualizado.
