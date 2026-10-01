# Invariantes e validação

Os testes exercitam os métodos públicos com bancos SQLite reais em diretórios temporários. Não há mocks de banco, rede, dados pessoais reais ou serviços pagos.

```sh
python -W error -m unittest discover -s tests -v
python -m tenant_crm
python -m compileall -q tenant_crm tests
```

## Mapa de cobertura

Os nomes abaixo são métodos em `tests/test_context.py`, `tests/test_store.py` e `tests/test_demo.py`.

| Invariante observável | Testes |
| --- | --- |
| Identificador de organização validado; contexto imutável | `test_rejects_invalid_tenant_identifiers`, `test_accepts_separate_immutable_contexts` |
| Contexto obrigatório, inclusive em lote vazio | `test_crud_rejects_unvalidated_or_missing_context`, `test_update_requires_valid_context_and_contact_identifier`, `test_import_and_export_require_valid_context_even_when_empty` |
| Mesmo ID em organizações distintas identifica contatos independentes | `test_same_contact_id_can_exist_in_separate_tenants` |
| Leitura não revela existência em outra organização | `test_foreign_and_nonexistent_contacts_are_both_absent` |
| Listagem e exportação preservam o escopo | `test_listing_is_scoped_and_ordered`, `test_export_contains_only_current_tenant_without_routing_fields` |
| Atualização alcança apenas a organização e persiste | `test_update_changes_only_current_tenant_and_persists` |
| Atualização inexistente e cruzada têm o mesmo erro | `test_foreign_and_missing_updates_have_identical_not_found_errors` |
| Campos extras e valores inválidos não alteram dados | `test_creation_rejects_invalid_or_extra_contact_fields`, `test_update_rejects_invalid_fields_without_changing_contact` |
| Conflito na criação preserva o original | `test_conflicting_create_preserves_existing_contact` |
| Pontuação SQL é tratada como valor | `test_parameterized_values_preserve_sql_punctuation` |
| Contatos sobrevivem ao fechamento/reabertura | `test_contacts_persist_after_reopening_sqlite`, `test_import_routes_all_contacts_through_context_and_persists` |
| Um payload não redireciona a importação para outro tenant | `test_import_with_tenant_field_rejects_entire_batch` |
| Conflitos revertem inserções anteriores e a conexão volta a funcionar | `test_import_conflict_rolls_back_prior_insert_and_recovers`, `test_duplicate_ids_inside_batch_roll_back_all_insertions` |
| Registro inválido rejeita o lote completo | `test_invalid_contact_inside_batch_leaves_no_partial_insertions` |
| JSON malformado, ambíguo ou não padronizado é rejeitado | `test_import_rejects_malformed_or_ambiguous_json` |
| Exportação/importação preserva Unicode e valores | `test_export_import_round_trip_preserves_unicode_and_values` |
| A demo executa os cenários e não deixa banco no diretório de trabalho | `test_module_demonstrates_isolation_and_rollback_without_leaving_data` |

## Evidência disponível e limites

A validação local executou 24 testes com `-W error` em Windows/Python 3.13.15, além da demo e da compilação de sintaxe. A demo é executada duas vezes pelo teste de subprocesso em um diretório vazio e deve encerrar com código zero, sem stderr ou arquivos persistidos naquele diretório.

A CI declara uma matriz `ubuntu-latest`/`windows-latest` × Python 3.12/3.13, com unittest, demo e compileall. A matriz não foi executada remotamente durante a criação local deste exemplo.

Os testes comprovam o contrato da camada de armazenamento nos cenários descritos. Não validam identidade, associação usuário/organização, RLS, concorrência, limites de recurso, navegador, infraestrutura ou uso em produção. A checagem de e-mail é apenas estrutural. Ausência de falhas nesses testes não é certificação de segurança.
