"""A small SQLite boundary with explicit organization scope."""

from dataclasses import asdict
import json
import os
import sqlite3

from .domain import (
    Contact, ConflictError, ContactNotFound, InvalidInput, TenantContext,
    contact_payload, identifier,
)


def _scope(context: TenantContext) -> str:
    if type(context) is not TenantContext:
        raise InvalidInput("A validated TenantContext is required")
    return identifier(context.tenant_id)


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidInput("Duplicate JSON fields are not accepted")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise InvalidInput("Nonstandard JSON numeric constants are not accepted")


class CrmStore:
    """Own a SQLite connection; use as a context manager or call close()."""

    def __init__(self, path: str | os.PathLike[str]):
        self._connection = sqlite3.connect(path, autocommit=False)
        with self._connection:
            self._connection.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    tenant_id TEXT NOT NULL,
                    id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, id)
                )
            """)

    def __enter__(self) -> "CrmStore":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def close(self) -> None:
        self._connection.close()

    def create(self, context: TenantContext, payload: dict) -> Contact:
        tenant_id = _scope(context)
        contact = contact_payload(payload)
        self._insert(tenant_id, [contact])
        return contact

    def _insert(self, tenant_id: str, contacts: list[Contact]) -> None:
        try:
            with self._connection:
                self._connection.executemany(
                    "INSERT INTO contacts (tenant_id, id, name, email) VALUES (?, ?, ?, ?)",
                    [(tenant_id, contact.id, contact.name, contact.email) for contact in contacts],
                )
        except sqlite3.IntegrityError:
            raise ConflictError("Contact already exists in this organization") from None

    def get(self, context: TenantContext, contact_id: str) -> Contact | None:
        tenant_id = _scope(context)
        contact_id = identifier(contact_id)
        row = self._connection.execute(
            "SELECT id, name, email FROM contacts WHERE tenant_id = ? AND id = ?",
            (tenant_id, contact_id),
        ).fetchone()
        return Contact(*row) if row is not None else None

    def list(self, context: TenantContext) -> list[Contact]:
        tenant_id = _scope(context)
        rows = self._connection.execute(
            "SELECT id, name, email FROM contacts WHERE tenant_id = ? ORDER BY id",
            (tenant_id,),
        ).fetchall()
        return [Contact(*row) for row in rows]

    def update(self, context: TenantContext, contact_id: str, payload: dict) -> Contact:
        tenant_id = _scope(context)
        contact_id = identifier(contact_id)
        if not isinstance(payload, dict) or set(payload) != {"name", "email"}:
            raise InvalidInput("Update requires exactly name and email")
        contact = contact_payload({"id": contact_id, **payload})
        with self._connection:
            cursor = self._connection.execute(
                "UPDATE contacts SET name = ?, email = ? WHERE tenant_id = ? AND id = ?",
                (contact.name, contact.email, tenant_id, contact_id),
            )
            if cursor.rowcount == 0:
                raise ContactNotFound("Contact not found in this organization")
        return contact

    def import_json(self, context: TenantContext, document: str) -> int:
        tenant_id = _scope(context)
        if not isinstance(document, str):
            raise InvalidInput("Import requires a JSON string containing an array of contacts")
        try:
            payloads = json.loads(
                document, object_pairs_hook=_unique_object, parse_constant=_reject_constant,
            )
        except InvalidInput:
            raise
        except (ValueError, RecursionError):
            raise InvalidInput("Invalid JSON document") from None
        if not isinstance(payloads, list):
            raise InvalidInput("Import requires an array of contacts")
        contacts = [contact_payload(payload) for payload in payloads]
        self._insert(tenant_id, contacts)
        return len(contacts)

    def export_json(self, context: TenantContext) -> str:
        return json.dumps([asdict(contact) for contact in self.list(context)], ensure_ascii=False, indent=2)
