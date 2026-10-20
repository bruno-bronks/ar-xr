---
id: DOC-DIAG-001
title: Interpretação dos estados da plataforma (documento FICTÍCIO de demonstração)
status: approved
approved_by: demo-fixture
approved_on: 2026-10-19
version: 1.0
equipment_types: *
---

Documento FICTÍCIO de demonstração sobre como a plataforma classifica o estado dos equipamentos.

## Estado OFFLINE
O equipamento fica offline quando nenhuma leitura chega dentro do tempo limite do perfil. Offline não significa normal: não há dado recente. Verifique energia, rede do gateway e o sensor antes de concluir que o equipamento parou.

## Estado UNKNOWN
Desconhecido indica dados insuficientes: falta leitura válida de algum sensor do perfil. Nunca trate desconhecido como normal. Confira se todos os sensores estão reportando.

## Leitura com qualidade ruim
Uma leitura marcada como ruim não participa da avaliação dos limites. Sensor com qualidade ruim deve ser inspecionado e, se necessário, substituído por pessoal autorizado.

## Limiar exato
Um valor exatamente igual ao limite de atenção não dispara alerta; o alerta surge quando o valor é estritamente maior que o limite. Os limites vêm do perfil de cada equipamento.
