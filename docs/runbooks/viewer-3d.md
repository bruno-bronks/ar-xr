# Runbook — vista 3D do painel

Spec: [SPEC-007](../../specs/functional/SPEC-007-simulator-and-panel.md) (seção Vista 3D) · [ADR-0008](../adr/0008-web-3d-viewer.md) · REQ-UX-004 · D-052.

## O que é (e o que não é)
Uma cena WebGL de um galpão com um modelo 3D por equipamento, colorido pelo estado do twin. **Os modelos são procedurais e ilustrativos** (representam o *tipo* cadastrado: compressor, bomba, motor), as posições vêm da configuração da planta 2D (D-051) e a cena **não** é CAD nem o local real. **Não** é o cliente AR (Unity, Fase 2).

## Usar
- Arraste para girar, role para aproximar, **clique** numa máquina ou no rótulo (ou use os botões "Visão geral" e um por equipamento) para focar; **duplo clique** volta à visão geral.
- O estado aparece em três lugares: **sinalizador luminoso** (verde/âmbar/vermelho; vermelho pulsa), **anel colorido no piso** e **rótulo em texto** com as leituras. Offline/Desconhecido: sinalizador apagado e texto explícito.
- Qualidade (seletor "Qualidade" ou `?q3d=alta|media|baixa` na URL): **Alta** (antialiasing 4×, oclusão ambiente, bloom, sombras 2048, resolução até 2×), **Média** (sem oclusão ambiente) e **Baixa** (renderização direta). O padrão é escolhido por heurística (tela pequena ou poucos núcleos ⇒ Média). Se o gráfico engasgar, baixe a qualidade.
- `prefers-reduced-motion` desliga o pulso e a animação da câmera.

## Requisitos e degradação
Exige **WebGL 2**. Sem ele (ou se o contexto gráfico for perdido) aparece uma mensagem e o resto do painel (cartões, planta 2D) continua. Em máquinas sem GPU a qualidade Alta pode ser lenta; use Baixa.

## Alterar a cena (build)
Fonte em `clients/viewer3d/src` (`materials.js`, `machines.js`, `hall.js`, `viewer.js`, `index.js`). O painel usa **só** o bundle `clients/web-fallback/vendor/viewer3d.js` (a CSP proíbe CDN e script inline).
```powershell
cd clients/viewer3d
npm ci            # three 0.186.1 e esbuild 0.28.2, versoes exatas no package-lock.json
npm run build     # gera vendor/viewer3d.js + viewer3d.manifest.json (SHA-256) + THREE-LICENSE.txt
```
Faça commit do bundle e do manifesto **junto** com a fonte: `tests/unit/repo/test_viewer_bundle.py` falha se divergirem e o job `viewer-bundle` da CI refaz o build e falha se o resultado não for idêntico ao commitado. Para atualizar o three.js: mude a versão exata em `package.json`, `npm install`, rebuild, rode os testes e revise o manifesto.

## Testes
`tests/e2e/test_panel_3d.py` (pilha no ar; Edge/Chrome com WebGL por **software**): cena pronta, um rótulo por equipamento, **análise de pixels** (cena não vazia; vermelho do crítico e verde do normal presentes), foco da câmera, teclado, arrasto sem seleção, troca de organização, nome hostil como texto, desatualizado, **sem WebGL**, seletor de qualidade, sem requisições externas/CSP, 360 px e capturas em qualidade Alta (`docs/evidence/phase-1/panel-3d-*.png`).
Limite: SwiftShader valida geometria, cor e comportamento, **não** o desempenho em GPU real nem em celular.

## Problemas comuns
| Sintoma | Causa provável | Ação |
|---|---|---|
| "Este navegador/dispositivo não oferece WebGL 2" | WebGL desativado ou GPU na lista de bloqueio | habilite a aceleração por hardware; o resto do painel funciona |
| Cena lenta/travando | qualidade Alta sem GPU | seletor → Média/Baixa |
| Rótulos sobrepostos | máquinas próximas na visão geral | clique numa máquina para focar |
| `npm run build` muda o hash sem eu ter mudado nada | versão do esbuild/three diferente da pinada | `npm ci` (não `npm install`) |

## Vista 3D das alas (UTI e enfermaria) — REQ-UX-005
Seção "Vista 3D das alas", **só aparece** para quem tem o escopo `hacc:read` (use "Enfermagem A (demo · leitos)" no seletor). A ala mostrada é a escolhida em "Ala" (UTI com 4 leitos, enfermaria com 6). A sala é **ilustrativa, sem pessoas e sem dados clínicos**; o monitor do leito fica em espera. Estado operacional por regra no sinalizador de parede, no anel do piso e no rótulo em texto (saída do leito, bomba de infusão, chamada, limpeza, sem dados). Os controles são os mesmos da vista de equipamentos (arrastar, rolar, clicar no leito/rótulo, "Visão geral", qualidade). Fonte em `clients/viewer3d/src/ward.js`; testes em `tests/e2e/test_panel_ward3d.py` (capturas em `docs/evidence/phase-4/panel-3d-*.png`). Limite: dados simulados, contrato do HACC assumido, WebGL por software nos testes.
