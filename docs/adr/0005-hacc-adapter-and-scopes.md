# ADR-0005 — HACC: porta somente leitura com fonte simulada, contrato assumido e escopos

## Status
Proposto (aguarda aprovação). Data: 2026-10-20. Complementa os ADR-0001…0004.

## Contexto
A Fase 4 pede um adapter **somente leitura** para endpoints existentes do HACC, leitos simulados, overlays, autorização e segregação, preservando o HACC original e sem depender de dados reais de pacientes. Não sei como o HACC expõe dados, o plano proíbe integrar sistemas reais ou dados hospitalares sem autorização/LGPD, e as regras do repositório proíbem alterar o HACC ou compartilhar seu banco.

## Decisão
1. **Porta `HaccSource`** (`packages/hacc`, `spatial_hacc`) com apenas operações de leitura. Duas implementações reais: `SimulatedHaccSource` (padrão) e `HttpHaccSource` (opcional, desligada) — por isso a abstração se justifica.
2. **Contrato assumido** (`specs/contracts/hacc-readonly.yaml`), declaradamente **não verificado** contra o HACC real. Quando o contrato real existir, só o `HttpHaccSource` muda.
3. **Regras de estado do leito no domínio puro** (`spatial_domain.beds`), reaproveitando a filosofia da SPEC-002 (dado ausente nunca é normal; offline com precedência) e **sem interpretação clínica**.
4. **Minimização por construção:** modelos Pydantic com `extra="forbid"`; qualquer campo desconhecido (potencialmente identificável) rejeita o payload inteiro.
5. **Segregação no nosso lado:** `tenant_id` do registro é comparado com a organização do principal; nada é confiado ao HACC.
6. **Escopos** (`Principal.scopes`, `hacc:read`) para menor privilégio; 403 sem escopo, 404 uniforme para outra organização.
7. **Sem persistência nova:** nenhum banco compartilhado, nenhuma tabela, nenhuma migração.

## Consequências
- (+) Dá para demonstrar e testar o fluxo inteiro sem tocar no HACC nem em dados reais.
- (+) A superfície de ataque do adaptador HTTP é pequena e testada (GET apenas, host/esquema permitidos, sem redirecionamento, limites).
- (−) O contrato assumido pode divergir do real; a integração real não está validada.
- (−) RBAC parcial (só um escopo); sem rate limit/disjuntor para a fonte HTTP.
- (−) Overlay só 2D; o cliente AR não foi estendido.

## Alternativas rejeitadas
- **Ler o repositório/banco do HACC para descobrir o esquema:** é integração real com sistema existente; exige sua autorização e foge da regra de independência.
- **Replicar dados do HACC no nosso banco:** cria um segundo repositório de dados potencialmente sensíveis; desnecessário na demonstração.
- **Confiar no HACC para filtrar por organização:** a segregação não pode depender de sistema externo.
