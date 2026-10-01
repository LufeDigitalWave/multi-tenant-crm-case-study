"""Validated domain values; identity verification belongs to the caller."""

from dataclasses import dataclass
import re


class InvalidInput(ValueError):
    """The supplied value does not meet the public input contract."""


class ConflictError(ValueError):
    """A contact identifier is already used in the current organization."""


class ContactNotFound(LookupError):
    """No contact is visible at this identifier in the current organization."""


def identifier(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", value):
        raise InvalidInput("Expected a lowercase identifier of 1 to 64 characters")
    return value


@dataclass(frozen=True)
class TenantContext:
    """Scope from a trusted authentication layer, not proof of authentication."""

    tenant_id: str

    def __post_init__(self) -> None:
        identifier(self.tenant_id)


@dataclass(frozen=True)
class Contact:
    """Contact values returned by scoped storage, without routing fields."""

    id: str
    name: str
    email: str


def contact_payload(payload: object) -> Contact:
    if not isinstance(payload, dict) or set(payload) != {"id", "name", "email"}:
        raise InvalidInput("Contact requires exactly id, name and email")
    contact_id = identifier(payload["id"])
    name, email = payload["name"], payload["email"]
    if not isinstance(name, str) or not 1 <= len(name) <= 120 or name != name.strip():
        raise InvalidInput("Name must contain 1 to 120 characters without surrounding whitespace")
    if any(ord(character) < 32 or ord(character) == 127
           or 0xD800 <= ord(character) <= 0xDFFF for character in name):
        raise InvalidInput("Name must not contain ASCII controls or surrogate code points")
    if (not isinstance(email, str) or len(email) > 254
            or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email)
            or any(ord(character) < 32 or ord(character) == 127
                   or 0xD800 <= ord(character) <= 0xDFFF for character in email)):
        raise InvalidInput("Email must have a simple local@domain.suffix shape")
    return Contact(contact_id, name, email)
