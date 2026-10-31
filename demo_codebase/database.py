"""Small in-memory persistence layer used by the demo service."""

from collections import defaultdict
from typing import DefaultDict, Dict, Iterable, Optional

from models import Customer, PaymentRequest, PaymentResult


class Repository:
    """Base repository contract shared by specialized stores."""

    def healthcheck(self) -> bool:
        """Return whether the backing store is reachable."""
        return True


class CustomerRepository(Repository):
    """Stores customer profiles for authentication and risk evaluation."""

    def __init__(self) -> None:
        self._customers: Dict[str, Customer] = {}

    def save(self, customer: Customer) -> Customer:
        """Create or replace a customer profile."""
        self._customers[customer.customer_id] = customer
        return customer

    def get(self, customer_id: str) -> Optional[Customer]:
        """Find a customer without exposing storage implementation details."""
        return self._customers.get(customer_id)

    def list_active(self) -> Iterable[Customer]:
        """Return active profiles for operational reporting."""
        return (customer for customer in self._customers.values() if customer.is_active())


class PaymentRepository(Repository):
    """Stores requests and outcomes for idempotency and audit history."""

    def __init__(self) -> None:
        self._requests: Dict[str, PaymentRequest] = {}
        self._results: Dict[str, PaymentResult] = {}
        self._by_customer: DefaultDict[str, list[str]] = defaultdict(list)

    def save_request(self, request: PaymentRequest) -> PaymentRequest:
        """Persist a request before any external gateway call."""
        # WHY: request-first persistence gives support staff an audit trail for failures.
        self._requests[request.request_id] = request
        self._by_customer[request.customer_id].append(request.request_id)
        return request

    def find_result(self, request_id: str) -> Optional[PaymentResult]:
        """Return an existing result to make retries idempotent."""
        return self._results.get(request_id)

    def save_result(self, result: PaymentResult) -> PaymentResult:
        """Persist the provider outcome after authorization."""
        self._results[result.request_id] = result
        return result

    def customer_request_count(self, customer_id: str) -> int:
        """Count historical requests used by the risk engine."""
        return len(self._by_customer[customer_id])


class UnitOfWork:
    """Groups repositories so a request has a single persistence boundary."""

    def __init__(self) -> None:
        self.customers = CustomerRepository()
        self.payments = PaymentRepository()

    def healthcheck(self) -> bool:
        """Check all repositories before serving traffic."""
        return self.customers.healthcheck() and self.payments.healthcheck()
