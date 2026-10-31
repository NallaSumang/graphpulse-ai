"""Rule-based fraud and risk scoring for payment requests."""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List

from database import UnitOfWork
from models import Customer, PaymentRequest, RiskDecision


class RiskRule(ABC):
    """Composable policy rule used by the risk engine."""

    @abstractmethod
    def evaluate(self, customer: Customer, request: PaymentRequest, history_count: int) -> float:
        """Return a normalized risk contribution."""
        raise NotImplementedError


class AmountRule(RiskRule):
    """Raises risk for unusually large payments."""

    def evaluate(self, customer: Customer, request: PaymentRequest, history_count: int) -> float:
        """Score payment size relative to a conservative threshold."""
        del customer, history_count
        return 0.35 if request.amount > Decimal("1000") else 0.05


class VelocityRule(RiskRule):
    """Raises risk when a customer submits many requests."""

    def evaluate(self, customer: Customer, request: PaymentRequest, history_count: int) -> float:
        """Score request velocity while keeping the result bounded."""
        del customer, request
        return min(0.4, history_count * 0.08)


class CountryRule(RiskRule):
    """Flags countries outside the merchant's normal operating region."""

    def evaluate(self, customer: Customer, request: PaymentRequest, history_count: int) -> float:
        """Use request metadata to model a geographic mismatch signal."""
        del history_count
        request_country = request.attributes.get("billing_country", customer.country)
        return 0.25 if request_country != customer.country else 0.0


class RiskEngine:
    """Combines rules and updates the customer profile with the result."""

    def __init__(self, unit_of_work: UnitOfWork, rules: List[RiskRule]) -> None:
        self.unit_of_work = unit_of_work
        self.rules = rules

    def evaluate(self, customer: Customer, request: PaymentRequest) -> RiskDecision:
        """Evaluate all rules before a gateway authorization is attempted."""
        history_count = self.unit_of_work.payments.customer_request_count(customer.customer_id)
        contributions = [rule.evaluate(customer, request, history_count) for rule in self.rules]
        score = min(1.0, sum(contributions))
        approved = score < 0.8
        signals = [type(rule).__name__ for rule, value in zip(self.rules, contributions) if value > 0]
        customer.record_risk_score(score)
        return RiskDecision(score=score, approved=approved, signals=signals)
