import json
from pathlib import Path
import tempfile
import unittest

import tenant_crm
from tenant_crm import InvalidInput, TenantContext


class StoreTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "contacts.sqlite3"
        self.store = tenant_crm.CrmStore(self.path)
        self.addCleanup(self.store.close)
        self.alpha = TenantContext("alpha")
        self.beta = TenantContext("beta")

    def test_same_contact_id_can_exist_in_separate_tenants(self):
        self.store.create(self.alpha, {"id": "shared", "name": "Alpha Demo", "email": "a@example.test"})
        self.store.create(self.beta, {"id": "shared", "name": "Beta Demo", "email": "b@example.test"})
        self.assertEqual(self.store.get(self.alpha, "shared").name, "Alpha Demo")
        self.assertEqual(self.store.get(self.beta, "shared").name, "Beta Demo")

    def test_foreign_and_nonexistent_contacts_are_both_absent(self):
        self.store.create(self.beta, {"id": "private", "name": "Beta Demo", "email": "b@example.test"})
        self.assertIsNone(self.store.get(self.alpha, "private"))
        self.assertIsNone(self.store.get(self.alpha, "missing"))

    def test_listing_is_scoped_and_ordered(self):
        self.store.create(self.beta, {"id": "hidden", "name": "Beta Demo", "email": "b@example.test"})
        self.store.create(self.alpha, {"id": "z", "name": "Last", "email": "z@example.test"})
        self.store.create(self.alpha, {"id": "a", "name": "First", "email": "a@example.test"})
        self.assertEqual([contact.id for contact in self.store.list(self.alpha)], ["a", "z"])
        self.assertEqual([contact.id for contact in self.store.list(self.beta)], ["hidden"])

    def test_crud_rejects_unvalidated_or_missing_context(self):
        payload = {"id": "demo", "name": "Demo", "email": "demo@example.test"}
        for context in (None, "alpha", {"tenant_id": "alpha"}, object()):
            with self.subTest(context=context):
                for operation in (
                    lambda: self.store.create(context, payload),
                    lambda: self.store.get(context, "demo"),
                    lambda: self.store.list(context),
                ):
                    with self.assertRaises(InvalidInput):
                        operation()
        with self.assertRaises(TypeError):
            self.store.create(payload)
        with self.assertRaises(TypeError):
            self.store.get("demo")
        with self.assertRaises(TypeError):
            self.store.list()
        self.assertEqual(self.store.list(self.alpha), [])

    def test_creation_rejects_invalid_or_extra_contact_fields(self):
        invalid = [
            None, [], {},
            {"id": "demo", "name": "Demo"},
            {"id": "demo", "name": "Demo", "email": "d@example.test", "tenant_id": "beta"},
            {"id": "demo", "name": "Demo", "email": "d@example.test", "role": "admin"},
            {"id": "", "name": "Demo", "email": "d@example.test"},
            {"id": "a' OR 1=1--", "name": "Demo", "email": "d@example.test"},
            {"id": "demo", "name": "", "email": "d@example.test"},
            {"id": "demo", "name": " Demo", "email": "d@example.test"},
            {"id": "demo", "name": "Demo\nOther", "email": "d@example.test"},
            {"id": "demo", "name": "Demo\ud800", "email": "d@example.test"},
            {"id": "demo", "name": "x" * 121, "email": "d@example.test"},
            {"id": "demo", "name": 42, "email": "d@example.test"},
            {"id": "demo", "name": "Demo", "email": "invalid"},
            {"id": "demo", "name": "Demo", "email": "d@@example.test"},
            {"id": "demo", "name": "Demo", "email": "d@ example.test"},
            {"id": "demo", "name": "Demo", "email": "d\u0000@example.test"},
            {"id": "demo", "name": "Demo", "email": "d\ud800@example.test"},
            {"id": "demo", "name": "Demo", "email": False},
            {"id": "demo", "name": "Demo", "email": "d" * 242 + "@example.test"},
        ]
        for payload in invalid:
            with self.subTest(payload=payload):
                with self.assertRaises(InvalidInput):
                    self.store.create(self.alpha, payload)
        self.assertEqual(self.store.list(self.alpha), [])
        self.assertEqual(self.store.list(self.beta), [])

    def test_conflicting_create_preserves_existing_contact(self):
        self.store.create(self.alpha, {"id": "demo", "name": "Original", "email": "a@example.test"})
        with self.assertRaises(tenant_crm.ConflictError):
            self.store.create(self.alpha, {"id": "demo", "name": "Replacement", "email": "b@example.test"})
        self.assertEqual(self.store.get(self.alpha, "demo").name, "Original")
        self.assertEqual(len(self.store.list(self.alpha)), 1)

    def test_parameterized_values_preserve_sql_punctuation(self):
        self.store.create(self.alpha, {
            "id": "literal", "name": "Demo '; DROP TABLE contacts; --", "email": "demo@example.test",
        })
        self.assertEqual(self.store.get(self.alpha, "literal").name, "Demo '; DROP TABLE contacts; --")
        with self.assertRaises(InvalidInput):
            self.store.get(self.alpha, "literal' OR 1=1--")
        self.assertEqual(len(self.store.list(self.alpha)), 1)

    def test_contacts_persist_after_reopening_sqlite(self):
        self.store.create(self.alpha, {"id": "demo", "name": "Persisted", "email": "a@example.test"})
        self.store.close()
        with tenant_crm.CrmStore(self.path) as reopened:
            self.assertEqual(reopened.get(self.alpha, "demo").email, "a@example.test")
            self.assertEqual(reopened.list(self.beta), [])

    def test_update_changes_only_current_tenant_and_persists(self):
        self.store.create(self.alpha, {"id": "shared", "name": "Alpha", "email": "a@example.test"})
        self.store.create(self.beta, {"id": "shared", "name": "Beta", "email": "b@example.test"})
        changed = self.store.update(self.alpha, "shared", {"name": "Updated", "email": "new@example.test"})
        self.assertEqual((changed.id, changed.name, changed.email), ("shared", "Updated", "new@example.test"))
        self.assertEqual(self.store.get(self.beta, "shared").name, "Beta")
        self.store.close()
        with tenant_crm.CrmStore(self.path) as reopened:
            self.assertEqual(reopened.get(self.alpha, "shared").name, "Updated")

    def test_foreign_and_missing_updates_have_identical_not_found_errors(self):
        self.store.create(self.beta, {"id": "hidden", "name": "Beta", "email": "b@example.test"})
        errors = []
        for contact_id in ("hidden", "missing"):
            with self.assertRaises(tenant_crm.ContactNotFound) as raised:
                self.store.update(self.alpha, contact_id, {"name": "Intruder", "email": "x@example.test"})
            errors.append((type(raised.exception), str(raised.exception)))
        self.assertEqual(errors[0], errors[1])
        self.assertEqual(self.store.list(self.alpha), [])
        self.assertEqual(self.store.get(self.beta, "hidden").name, "Beta")

    def test_update_rejects_invalid_fields_without_changing_contact(self):
        self.store.create(self.alpha, {"id": "demo", "name": "Original", "email": "a@example.test"})
        for payload in (
            None, {}, {"name": "Only name"},
            {"name": "Other", "email": "b@example.test", "tenant_id": "beta"},
            {"id": "other", "name": "Other", "email": "b@example.test"},
            {"name": "", "email": "b@example.test"},
            {"name": "Other", "email": "invalid"},
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(InvalidInput):
                    self.store.update(self.alpha, "demo", payload)
        self.assertEqual(self.store.get(self.alpha, "demo").name, "Original")

    def test_update_requires_valid_context_and_contact_identifier(self):
        for context in (None, "alpha", {"tenant_id": "alpha"}, object()):
            with self.subTest(context=context):
                with self.assertRaises(InvalidInput):
                    self.store.update(context, "demo", {"name": "Demo", "email": "a@example.test"})
        with self.assertRaises(InvalidInput):
            self.store.update(self.alpha, "demo' OR 1=1--", {"name": "Demo", "email": "a@example.test"})
        with self.assertRaises(TypeError):
            self.store.update("demo", {"name": "Demo", "email": "a@example.test"})

    def test_export_contains_only_current_tenant_without_routing_fields(self):
        self.store.create(self.alpha, {"id": "a", "name": "Alpha", "email": "a@example.test"})
        self.store.create(self.beta, {"id": "hidden", "name": "Beta", "email": "b@example.test"})
        self.assertEqual(json.loads(self.store.export_json(self.alpha)), [
            {"id": "a", "name": "Alpha", "email": "a@example.test"},
        ])
        self.assertEqual(json.loads(self.store.export_json(TenantContext("empty"))), [])

    def test_import_routes_all_contacts_through_context_and_persists(self):
        self.store.create(self.beta, {"id": "shared", "name": "Beta", "email": "b@example.test"})
        count = self.store.import_json(self.alpha, '''[
            {"id": "shared", "name": "Alpha", "email": "a@example.test"},
            {"id": "other", "name": "Other", "email": "o@example.test"}
        ]''')
        self.assertEqual(count, 2)
        self.assertEqual(self.store.get(self.alpha, "shared").name, "Alpha")
        self.assertEqual([contact.id for contact in self.store.list(self.beta)], ["shared"])
        self.assertEqual(self.store.get(self.beta, "shared").name, "Beta")
        self.store.close()
        with tenant_crm.CrmStore(self.path) as reopened:
            self.assertEqual([contact.id for contact in reopened.list(self.alpha)], ["other", "shared"])

    def test_import_with_tenant_field_rejects_entire_batch(self):
        with self.assertRaises(InvalidInput):
            self.store.import_json(self.alpha, '''[
                {"id": "safe", "name": "Safe", "email": "s@example.test"},
                {"id": "attack", "name": "Injected", "email": "x@example.test", "tenant_id": "beta"}
            ]''')
        self.assertEqual(self.store.list(self.alpha), [])
        self.assertEqual(self.store.list(self.beta), [])

    def test_import_conflict_rolls_back_prior_insert_and_recovers(self):
        self.store.create(self.alpha, {"id": "taken", "name": "Original", "email": "a@example.test"})
        with self.assertRaises(tenant_crm.ConflictError):
            self.store.import_json(self.alpha, '''[
                {"id": "new", "name": "Would be inserted", "email": "n@example.test"},
                {"id": "taken", "name": "Replacement", "email": "r@example.test"}
            ]''')
        self.store.close()
        with tenant_crm.CrmStore(self.path) as reopened:
            self.assertIsNone(reopened.get(self.alpha, "new"))
            self.assertEqual(reopened.get(self.alpha, "taken").name, "Original")
            self.assertEqual(reopened.import_json(self.alpha,
                '[{"id":"new","name":"Recovered","email":"n@example.test"}]'), 1)
            self.assertEqual(reopened.get(self.alpha, "new").name, "Recovered")

    def test_duplicate_ids_inside_batch_roll_back_all_insertions(self):
        with self.assertRaises(tenant_crm.ConflictError):
            self.store.import_json(self.alpha, '''[
                {"id": "same", "name": "First", "email": "a@example.test"},
                {"id": "same", "name": "Second", "email": "b@example.test"}
            ]''')
        self.assertEqual(self.store.list(self.alpha), [])

    def test_invalid_contact_inside_batch_leaves_no_partial_insertions(self):
        with self.assertRaises(InvalidInput):
            self.store.import_json(self.alpha, '''[
                {"id": "valid", "name": "Valid", "email": "v@example.test"},
                {"id": "invalid", "name": "Bad", "email": "not-an-email"}
            ]''')
        self.assertEqual(self.store.list(self.alpha), [])

    def test_import_rejects_malformed_or_ambiguous_json(self):
        for document in (
            None, b"[]", [], "", "[", "null", "{}", '"text"', "[null]", "[1]",
            '[{"id":"a","id":"b","name":"Demo","email":"d@example.test"}]',
            '[{"id":"a","name":"Demo","email":"d@example.test","other":true}]',
            '[{"id":"a","name":NaN,"email":"d@example.test"}]',
            '[{"id":"a","name":Infinity,"email":"d@example.test"}]',
            '[{"id":"a","name":"Demo\\ud800","email":"d@example.test"}]',
            '[{"id":' + "1" * 5000 + ',"name":"Demo","email":"d@example.test"}]',
            "[" * 2000 + "]" * 2000,
        ):
            with self.subTest(document=repr(document)[:100]):
                with self.assertRaises(InvalidInput):
                    self.store.import_json(self.alpha, document)
        self.assertEqual(self.store.list(self.alpha), [])

    def test_import_and_export_require_valid_context_even_when_empty(self):
        for context in (None, "alpha", {"tenant_id": "alpha"}, object()):
            with self.subTest(context=context):
                with self.assertRaises(InvalidInput):
                    self.store.import_json(context, "[]")
                with self.assertRaises(InvalidInput):
                    self.store.export_json(context)
        with self.assertRaises(TypeError):
            self.store.import_json("[]")
        with self.assertRaises(TypeError):
            self.store.export_json()
        self.assertEqual(self.store.import_json(self.alpha, "[]"), 0)

    def test_export_import_round_trip_preserves_unicode_and_values(self):
        self.store.create(self.alpha, {"id": "demo", "name": "Contato Fictício", "email": "d@example.test"})
        exported = self.store.export_json(self.alpha)
        self.assertEqual(json.loads(exported), [
            {"id": "demo", "name": "Contato Fictício", "email": "d@example.test"},
        ])
        self.assertEqual(self.store.import_json(self.beta, exported), 1)
        self.assertEqual(self.store.get(self.beta, "demo").name, "Contato Fictício")


if __name__ == "__main__":
    unittest.main()
