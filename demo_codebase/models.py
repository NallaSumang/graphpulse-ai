"""Domain models shared by the GraphPulse demo payment service."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional


class AccountStatus(str, Enum):
    """Lifecycle states accepted by the account service."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


@dataclass
class Customer:
    """A customer whose identity and risk profile are persisted together."""

    customer_id: str
    email: str
    country: str
    status: AccountStatus = AccountStatus.ACTIVE
    risk_score: float = 0.0
    metadata: Dict[str, str] = field(default_factory=dict)

    def is_active(self) -> bool:
        """Return whether the customer may initiate a payment."""
        return self.status is AccountStatus.ACTIVE

    def record_risk_score(self, score: float) -> None:
        """Store the latest score used for payment authorization."""
        self.risk_score = max(0.0, min(1.0, score))


@dataclass
class PaymentRequest:
    """Input accepted by the API before gateway authorization."""

    request_id: str
    customer_id: str
    amount: Decimal
    currency: str
    merchant_id: str
    ip_address: str
    created_at: datetime
    attributes: Dict[str, str] = field(default_factory=dict)

    def normalized_currency(self) -> str:
        """Normalize currency codes before they reach a provider."""
        return self.currency.upper().strip()

    def is_positive(self) -> bool:
        """Reject zero and negative payment attempts early."""
        return self.amount > Decimal("0")


class PaymentResult:
    """Immutable-looking result object shared by providers and the router."""

    def __init__(
        self,
        request_id: str,
        approved: bool,
        provider_reference: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        self.request_id = request_id
        self.approved = approved
        self.provider_reference = provider_reference
        self.reason = reason

    def as_dict(self) -> Dict[str, Optional[str]]:
        """Produce a transport-friendly representation."""
        return {
            "request_id": self.request_id,
            "approved": str(self.approved).lower(),
            "provider_reference": self.provider_reference,
            "reason": self.reason,
        }


@dataclass
class RiskDecision:
    """Decision emitted by the risk engine for an individual request."""

    score: float
    approved: bool
    signals: List[str] = field(default_factory=list)

    def requires_review(self) -> bool:
        """Flag borderline decisions for manual review."""
        return not self.approved and 0.45 <= self.score < 0.8


class ServiceError(Exception):
    """Base error for expected service-level failures."""


class AuthenticationError(ServiceError):
    """Raised when a caller cannot be authenticated."""


class PaymentDeclined(ServiceError):
    """Raised when policy or a provider declines a payment."""
