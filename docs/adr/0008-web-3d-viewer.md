# ADR-0008 — Vista 3D no painel web: three.js empacotado localmente, modelos procedurais

## Status
Proposto (aguarda aprovação). Data: 2026-10-23. Complementa os ADR-0001…0007.

## Contexto
O painel era 2D (cartões e uma planta esquemática). O usuário pediu 3D no navegador com **alta precisão, qualidade e resolução**, "não aqueles 3D horríveis". Restrições: a CSP do painel é `default-src 'self'; script-src 'self'; style-src 'self'` (sem CDN, sem script inline, sem `importmap` inline), as imagens Docker só copiam arquivos do repositório, e o projeto cuida da cadeia de suprimentos (SBOM, hashes, CI). Não há CAD, fotos nem modelos 3D dos equipamentos reais.

## Decisão
1. **three.js 0.186.1 (MIT)**, empacotado por **esbuild** em um único arquivo IIFE versionado (`clients/web-fallback/vendor/viewer3d.js`). Fonte e build em `clients/viewer3d` (`package.json` com versões exatas, `package-lock.json`). `viewer3d.manifest.json` guarda o SHA-256 do bundle, as versões e os hashes das fontes; um job de CI refaz `npm ci && npm run build` e falha se o resultado divergir do commitado. A licença do three.js acompanha o bundle.
2. **Modelos 100 % procedurais** (geometria, texturas e materiais gerados por código com semente fixa): compressor com reservatório de calota elíptica, bomba centrífuga com voluta e flanges, motor trifásico com carcaça aletada, sinalizador luminoso de 3 cores, galpão com piso de concreto PBR, colunas, chapa corrugada e tubulações. O modelo é escolhido pelo **tipo** cadastrado; tipo desconhecido ⇒ unidade genérica (nunca finge ser outra máquina).
3. **Qualidade:** materiais PBR (`MeshPhysicalMaterial`), iluminação por ambiente (PMREM de `RoomEnvironment`), luz direcional com sombras suaves, MSAA 4× em alvo de ponto flutuante, **GTAO** (oclusão ambiente) e bloom nos níveis "alta"/"média", tone mapping ACES, pixel ratio até 2. Renderização **sob demanda** (só desenha quando algo muda), pausada fora da tela/aba.
4. **Estado nunca só por cor:** sinalizador luminoso, anel do piso e rótulo DOM (texto + ícone + leituras). Rótulos são botões nativos (teclado, leitor de tela). `prefers-reduced-motion` desliga o pulso e as animações de câmera.
5. **Degradação:** sem WebGL 2 ou com perda de contexto, a vista mostra uma mensagem e o resto do painel (cartões, planta 2D) segue funcionando.
6. As **posições** vêm da mesma configuração ilustrativa da planta 2D (D-051).

## Consequências
- (+) Qualidade visual alta sem dependência de CDN nem de arquivos de terceiros; a cena é reproduzível e auditável.
- (+) Cadeia de suprimentos controlada: bundle com hash, build reproduzível verificado na CI, três dependências diretas pinadas.
- (−) +≈ 660 KB (≈ 170 KB gzip) de JavaScript no painel; exige WebGL 2 e GPU razoável para a qualidade "alta".
- (−) Os modelos são **ilustrativos**: representam o tipo de máquina, não o equipamento real (sem CAD, sem medidas); a planta/posições seguem fictícias.
- (−) Testes de renderização rodam com WebGL por software (SwiftShader): validam geometria, cor e comportamento, **não** o desempenho em GPUs reais nem em celulares.
- (−) Mais uma peça para manter: atualizar o three.js exige rebuild, revisão do manifesto e nova rodada de testes.

## Alternativas rejeitadas
- **CDN (unpkg/jsDelivr):** viola a CSP e a cadeia de suprimentos controlada.
- **`importmap` inline com módulos soltos:** `script-src 'self'` bloqueia script inline.
- **Modelos glTF baixados da internet:** licenças e proveniência incertas; sem controle de qualidade nem de tamanho.
- **three.js sem empacotar (muitos arquivos):** dezenas de requisições e dependência de `importmap`.
- **Babylon.js / Unity WebGL:** mais pesados ou fora do padrão do painel; o three.js basta e é MIT.
