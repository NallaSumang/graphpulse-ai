"""Provider abstraction and payment authorization orchestration."""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict

from models import PaymentDeclined, PaymentRequest, PaymentResult


class GatewayProvider(ABC):
    """Abstract provider contract that supports provider substitution."""

    @abstractmethod
    def authorize(self, request: PaymentRequest) -> PaymentResult:
        """Authorize a request with an external payment provider."""
        raise NotImplementedError


class SandboxGateway(GatewayProvider):
    """Predictable provider used by local development and tests."""

    def __init__(self, minimum_amount: Decimal = Decimal("1.00")) -> None:
        self.minimum_amount = minimum_amount

    def authorize(self, request: PaymentRequest) -> PaymentResult:
        """Approve ordinary sandbox charges and reject invalid amounts."""
        if request.amount < self.minimum_amount:
            return PaymentResult(request.request_id, False, reason="amount below provider minimum")
        reference = f"sandbox_{request.request_id}"
        return PaymentResult(request.request_id, True, provider_reference=reference)


class GatewayClient:
    """Coordinates idempotency and provider calls for the payment service."""

    def __init__(self, provider: GatewayProvider) -> None:
        self.provider = provider
        self._metadata: Dict[str, str] = {}

    def charge(self, request: PaymentRequest) -> PaymentResult:
        """Validate a request before delegating to the configured provider."""
        if not request.is_positive():
            raise PaymentDeclined("payment amount must be positive")
        self._metadata[request.request_id] = request.normalized_currency()
        # NOTE: provider selection is injected so production can use a PCI-isolated adapter.
        return self.provider.authorize(request)

    def refund_reference(self, result: PaymentResult) -> str:
        """Build a provider-specific refund lookup key."""
        if not result.approved or not result.provider_reference:
            raise PaymentDeclined("only approved payments can be refunded")
        return f"refund:{result.provider_reference}"
