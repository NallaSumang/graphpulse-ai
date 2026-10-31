"""Authentication and authorization policies for API callers."""

import hashlib
import hmac
from typing import Dict

from database import UnitOfWork
from models import AuthenticationError, Customer


class TokenIssuer:
    """Issues deterministic demo tokens without storing raw credentials."""

    def __init__(self, secret: str) -> None:
        self._secret = secret.encode("utf-8")

    def issue(self, customer: Customer) -> str:
        """Create a short-lived-looking token for the demo boundary."""
        payload = f"{customer.customer_id}:{customer.email}".encode("utf-8")
        digest = hmac.new(self._secret, payload, hashlib.sha256).hexdigest()
        return f"gp_{customer.customer_id}_{digest[:20]}"


class AuthenticatedPrincipal:
    """Represents an authenticated customer and permitted operations."""

    def __init__(self, customer: Customer, scopes: set[str]) -> None:
        self.customer = customer
        self.scopes = scopes

    def can_charge(self) -> bool:
        """Return whether the principal may submit a charge."""
        return "payments:write" in self.scopes and self.customer.is_active()

    def can_view_history(self) -> bool:
        """Return whether the principal may inspect payment history."""
        return "payments:read" in self.scopes


class AuthenticationService:
    """Resolves API tokens into customer-backed principals."""

    def __init__(self, unit_of_work: UnitOfWork, issuer: TokenIssuer) -> None:
        self.unit_of_work = unit_of_work
        self.issuer = issuer
        self._tokens: Dict[str, str] = {}

    def register(self, customer: Customer) -> str:
        """Persist a customer and issue its initial token."""
        self.unit_of_work.customers.save(customer)
        token = self.issuer.issue(customer)
        self._tokens[token] = customer.customer_id
        return token

    def authenticate(self, token: str) -> AuthenticatedPrincipal:
        """Validate a token and load the associated customer."""
        customer_id = self._tokens.get(token)
        customer = self.unit_of_work.customers.get(customer_id) if customer_id else None
        if customer is None or not customer.is_active():
            raise AuthenticationError("invalid or inactive credentials")
        return AuthenticatedPrincipal(customer, {"payments:read", "payments:write"})
