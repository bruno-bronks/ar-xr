# ADR-0006 — Visão como PoC offline isolado; IoT por portão de aprovação com emulador e broker endurecido

## Status
Proposto (aguarda aprovação). Data: 2026-10-20. Complementa os ADR-0001…0005.

## Contexto
A Fase 5 pede uma prova de conceito de visão computacional (YOLO) com dataset rotulado e métricas, e sensores ESP32 **somente após plano elétrico e de segurança**, com comparação mensurável com QR e simulador e sem promessa de diagnóstico. Não há fotos reais rotuladas, hardware nem autorização para coletá-las; o broker de desenvolvimento é anônimo; `ultralytics` é AGPL-3.0 e o download de pesos pré-treinados é um binário não verificado.

## Decisão
1. **Dataset sintético determinístico** (`ml/spatial_cv`), com estado verdadeiro vindo da regra real de status. É a única forma de ter rótulos e uma comparação com o QR e o simulador sem inventar fotos.
2. **YOLO isolado em `ml/`** (ambiente próprio, CPU): fora do runtime, das imagens e da CI. **Dois detectores comparados:** do zero (linha de base) e ajuste fino de pesos oficiais (autorizado pelo usuário, D-040), com origem pinada por URL + SHA-256. A licença AGPL e as dependências pesadas não tocam os serviços; um teste por AST garante o isolamento.
3. **Comparação estatisticamente honesta:** IC de Wilson e McNemar exato; baseline simples (cor) para medir o que o YOLO acrescenta; relatório com limites explícitos.
4. **Visão assistiva:** sem poder de alterar status/alertas; a autoridade segue sendo a regra de telemetria.
5. **IoT por portão:** nesta fase entregamos o **plano** (G1–G7), um **emulador** de dispositivo (software) e um **broker endurecido opt-in** (auth + ACL por dispositivo). Hardware/firmware só após aprovação explícita; TLS é pré-requisito (G3).
6. **Credenciais MQTT opcionais** no worker e no simulador, mantendo o padrão anônimo de desenvolvimento.

## Consequências
- (+) Pipeline de visão reproduzível e medido, sem riscos de licença/dependência para o produto.
- (+) A segurança do caminho até sensores reais é testada com Mosquitto real antes de qualquer hardware.
- (−) Números de visão **não** generalizam para fotos reais; o PoC prova o método, não o desempenho.
- (−) Sem TLS; o broker endurecido não serve para dispositivos reais ainda.
- (−) O hash dos pesos foi pinado do arquivo baixado, sem confirmação contra uma publicação oficial; a licença AGPL vale para os pesos.
- (−) Compatibilidade do hash `$7$` e da ACL fixada à versão 2.0.18 do Mosquitto testada.

## Alternativas rejeitadas
- **Pesos pré-treinados sem autorização/verificação:** inicialmente rejeitados (binário e licença AGPL); o usuário autorizou depois (D-040) e passamos a exigir URL pinada + SHA-256 antes de carregar (o `.pt` é um *pickle*). O treino do zero continua como linha de base.
- **YOLO/torch na imagem da API ou na CI:** AGPL e centenas de MB sem necessidade de runtime.
- **Comprar/montar ESP32 agora:** viola o portão do plano.
- **Fotos de equipamentos da internet:** direitos, qualidade e rotulação desconhecidos.
- **TLS agora:** exige PKI e provisionamento de dispositivos; fica como pré-requisito explícito (G3).
