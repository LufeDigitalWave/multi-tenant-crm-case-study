"""Run synthetic scenarios against a temporary SQLite database."""

from dataclasses import asdict
import json
from pathlib import Path
import tempfile

from . import ConflictError, ContactNotFound, CrmStore, InvalidInput, TenantContext


def run_demo() -> dict:
    # These synthetic contexts stand in for a trusted authentication adapter.
    alpha, beta = TenantContext("alpha"), TenantContext("beta")
    with tempfile.TemporaryDirectory() as temporary:
        with CrmStore(Path(temporary) / "demo.sqlite3") as store:
            store.create(alpha, {"id": "shared", "name": "Alpha Demo", "email": "a@example.test"})
            store.create(beta, {"id": "shared", "name": "Beta Demo", "email": "b@example.test"})
            store.create(beta, {"id": "beta-only", "name": "Beta Only", "email": "only@example.test"})

            cross_read = store.get(alpha, "beta-only")
            cross_update = "updated"
            try:
                store.update(alpha, "beta-only", {"name": "Intruder", "email": "x@example.test"})
            except ContactNotFound:
                cross_update = "not_found"

            malicious_import = "accepted"
            try:
                store.import_json(alpha, '''[
                    {"id":"safe","name":"Safe","email":"s@example.test"},
                    {"id":"attack","name":"Injected","email":"x@example.test","tenant_id":"beta"}
                ]''')
            except InvalidInput:
                malicious_import = "rejected"

            conflicting_import = "accepted"
            try:
                store.import_json(alpha, '''[
                    {"id":"new","name":"New Demo","email":"n@example.test"},
                    {"id":"shared","name":"Conflict","email":"c@example.test"}
                ]''')
            except ConflictError:
                conflicting_import = "rolled_back"

            store.update(alpha, "shared", {"name": "Alpha Updated", "email": "a@example.test"})
            partial_contact = store.get(alpha, "new")
            return {
                "alpha": json.loads(store.export_json(alpha)),
                "beta": json.loads(store.export_json(beta)),
                "cross_tenant_read": asdict(cross_read) if cross_read is not None else None,
                "cross_tenant_update": cross_update,
                "malicious_import": malicious_import,
                "conflicting_import": conflicting_import,
                "partial_contact": asdict(partial_contact) if partial_contact is not None else None,
            }


def main() -> None:
    print(json.dumps(run_demo(), indent=2))


if __name__ == "__main__":
    main()
