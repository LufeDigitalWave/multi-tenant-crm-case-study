# CRM multi-tenant e operação comercial

Case técnico anonimizado sobre contatos, atividades, funil comercial e isolamento entre organizações.

> Publicação documental. Não contém CRM executável, base de contatos, empresas, histórico comercial, chaves ou integrações ativas.

## Problema

Um CRM concentra informações que circulam por telas, importações, relatórios e integrações. O isolamento precisa acompanhar todos esses caminhos, não apenas a tela inicial. Duplicações e atualizações concorrentes também afetam a qualidade do histórico.

## Escopo representado

Organização de contatos, atividades, etapas de funil, importação e mesclagem, autorização e auditoria. A estrutura de origem também inclui módulos de apoio por IA; este case não publica seus prompts nem apresenta resultados de qualificação automática.

## Stack identificada

Python, FastAPI, Pydantic, SQLAlchemy e Alembic; React, TypeScript e Vite. Há configuração de testes de backend e interface, mas sua execução não integra esta publicação.

## O que discutir numa entrevista

- Como propagar o contexto da organização por consultas e operações em lote.
- Como mesclar contatos sem perder a proveniência das informações.
- Como representar movimentações de funil e histórico de atividades.
- Como separar sugestões de IA de alterações efetivas no domínio.

Consulte a [arquitetura e o roteiro de validação](ARCHITECTURE.md).

## Limites

Não são publicados clientes, contatos, oportunidades, valores, indicadores comerciais, esquemas completos, endpoints ou configurações. Não há alegação de isolamento auditado ou segurança certificada.
