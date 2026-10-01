"""Offline CRM example with explicit organization scope."""

from .domain import Contact, ConflictError, ContactNotFound, InvalidInput, TenantContext
from .store import CrmStore

__all__ = ["Contact", "ConflictError", "ContactNotFound", "CrmStore", "InvalidInput", "TenantContext"]
