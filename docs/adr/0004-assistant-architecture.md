# ADR-0004 — Assistente: recuperação extrativa por padrão, LLM opcional e verificado

## Status
Proposto (aguarda aprovação). Data: 2026-10-19. Complementa os ADR-0001…0003.

## Contexto
A Fase 3 pede base de conhecimento aprovada, respostas com referências, **fallback mock**, avaliação de alucinação e logging seguro. O plano proíbe contratar nuvem/gastar com serviços sem aprovação e exige que a IA seja só assistiva, cite fontes e expresse incerteza. Não há chave de LLM nem manual real aprovado nesta máquina.

## Decisão
1. Novo pacote puro `packages/assistant` (`spatial_assistant`): carregamento/validação da base, recuperação, política de recusa, verificação de fundamentação e orquestração. Sem I/O de rede nem framework; a API o compõe em `services/api/app/main.py`.
2. **Provedor padrão extrativo** (determinístico, offline): a resposta é feita de trechos **literais** aprovados. É o "mock/fallback" do plano e a única configuração totalmente testável aqui.
3. **LLM é um segundo provedor real** (Strategy justificada: duas implementações): `AnthropicProvider` (HTTPS via `urllib`, sem dependência nova), desligado por padrão, com *timeout* e disjuntor. A saída do LLM é **proposta**, nunca confiada: só é aceita após verificação de fundamentação (citações ⊆ recuperados; números e termos com suporte); as fontes mostradas são geradas pelo sistema. Falha ⇒ extrativo.
4. **Defesa estrutural contra injeção:** documentos são aprovados e filtrados na carga; pergunta e trechos entram no prompt como dados delimitados; o sistema não executa nada que a saída diga. A lista de padrões de recusa/injeção é heurística (D-020) e não é a única barreira.
5. **Alertas continuam determinísticos**; o assistente só lê o twin (`live_state`) e não o altera.
6. **Logging:** só metadados (D-022).

## Consequências
- (+) Funciona e é testado sem credenciais; alucinação é mensurável (REQ-AI-007) e o pior caso do LLM degrada para texto literal.
- (+) Trocar/ligar o LLM é configuração, não reescrita.
- (−) O extrativo não "raciocina": responde com trechos, não sintetiza; recuperação lexical falha com sinônimos.
- (−) O adaptador Anthropic não foi exercitado contra a API real (sem chave/aprovação); só testado com transporte simulado.
- (−) Base de conhecimento atual é fictícia (D-019).

## Alternativas rejeitadas
- **Embeddings/vetores + banco vetorial:** dependência e custo sem necessidade com poucas dezenas de trechos; reavaliar quando a base crescer.
- **Chamar o LLM diretamente com o documento inteiro:** sem verificação de fundamentação e com mais superfície de injeção/vazamento.
- **SDK oficial da Anthropic:** nova dependência de supply chain para uma única chamada HTTPS; `urllib` basta.
- **Confiar na instrução "não alucine" no prompt:** não é controle verificável.
