# CRM: isolamento entre organizações com SQLite

Exemplo didático independente para portfólio: contatos, importação atômica e exportação com contexto explícito de organização. Código novo, dados sintéticos e biblioteca padrão do Python; funciona offline.

O objetivo é mostrar como uma regra de escopo acompanha consultas e operações em lote. A demonstração usa SQLite real, sem servidor, dependências externas ou dados de clientes.

## Executar

Na raiz do repositório, com Python 3.12 ou 3.13:

```sh
python -m tenant_crm
python -W error -m unittest discover -s tests -v
python -m compileall -q tenant_crm tests
```

A demo cria um banco temporário, executa os cenários e remove o banco ao terminar. Não exige instalação de pacotes, rede ou configuração de credenciais. Saída real:

```json
{
  "alpha": [
    {
      "id": "shared",
      "name": "Alpha Updated",
      "email": "a@example.test"
    }
  ],
  "beta": [
    {
      "id": "beta-only",
      "name": "Beta Only",
      "email": "only@example.test"
    },
    {
      "id": "shared",
      "name": "Beta Demo",
      "email": "b@example.test"
    }
  ],
  "cross_tenant_read": null,
  "cross_tenant_update": "not_found",
  "malicious_import": "rejected",
  "conflicting_import": "rolled_back",
  "partial_contact": null
}
```

O ID `shared` pertence a dois contatos independentes. A organização `alpha` não lê nem atualiza `beta-only`. Um campo `tenant_id` no JSON rejeita a importação inteira; um conflito de ID desfaz também a inserção que o precede.

## API Python

```python
from tenant_crm import CrmStore, TenantContext

# Em uma aplicação, a autenticação confiável deve fornecer este contexto.
context = TenantContext("demo-org")
with CrmStore(":memory:") as store:
    store.create(context, {
        "id": "contact-1", "name": "Contato Fictício", "email": "demo@example.test",
    })
    store.update(context, "contact-1", {
        "name": "Contato Atualizado", "email": "demo@example.test",
    })
    contact = store.get(context, "contact-1")
    contacts = store.list(context)
    document = store.export_json(context)
    # Importação insere contatos; um ID existente gera ConflictError.
    inserted = store.import_json(context, "[]")
```

`TenantContext` é obrigatório em criar, ler, listar, atualizar, importar e exportar. Criação/importação aceitam exatamente `id`, `name` e `email`; atualização aceita exatamente `name` e `email`. Campos extras, inclusive qualquer campo de roteamento de organização, são rejeitados.

Os IDs de organização e contato seguem `[a-z0-9][a-z0-9_-]{0,63}`. Nomes têm 1 a 120 caracteres, sem espaços nas extremidades; e-mails têm até 254 caracteres e uma forma simples `local@domínio.sufixo`. Nomes/e-mails rejeitam controles ASCII e surrogates Unicode. Essa checagem de e-mail não implementa a especificação completa nem verifica entrega.

## Decisões demonstradas

- Chave primária `(tenant_id, id)`: conflito de ID acontece dentro da organização.
- SQL parametrizado: o contexto fornece a organização; nenhum payload escolhe o destino.
- `get` retorna `None` para contato inexistente ou de outra organização. `update` produz o mesmo `ContactNotFound` nos dois casos.
- Importação valida o documento inteiro antes de inserir e usa uma transação para o lote. JSON com chaves duplicadas, constantes não padronizadas ou campos extras é rejeitado.
- Exportação contém somente contatos da organização, ordenados por ID, sem campos de roteamento. Reimportar o documento com outro contexto confiável é uma cópia explícita para aquele destino.

Veja [ARCHITECTURE.md](ARCHITECTURE.md) para a fronteira de confiança e [EVALUATION.md](EVALUATION.md) para o mapa de invariantes e testes.

## Limites

A autenticação e a verificação de associação do usuário à organização não são implementadas. Validar `TenantContext` verifica a forma do identificador, não a identidade: qualquer caller Python pode construí-lo. Quem forja outro contexto, acessa a conexão privada ou abre o arquivo SQLite diretamente está fora da fronteira desta demonstração. Uma aplicação real deve obter o contexto da sessão autenticada, e nunca de um campo livre do usuário/modelo.

O exemplo não implementa RLS, HTTP, interface web, rede, papéis/permissões, criptografia, auditoria, exclusão, mesclagem, funil ou IA. Não fornece limites de tamanho do lote, controle de concorrência de negócio, migrações ou operação de produção. Não há alegação de segurança certificada.

A validação local foi executada em Windows com Python 3.13.15. A CI declara Linux/Windows e Python 3.12/3.13; a execução remota dessa matriz deve ser confirmada no GitHub.
