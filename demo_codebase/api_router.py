"""HTTP-shaped application facade for the GraphPulse payment microservice."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict

from auth_service import AuthenticationService
from database import UnitOfWork
from models import PaymentDeclined, PaymentRequest, PaymentResult
from payment_gateway import GatewayClient, SandboxGateway
from risk_engine import AmountRule, CountryRule, RiskEngine, VelocityRule


class PaymentRouter:
    """Routes authenticated requests through risk, persistence, and payment."""

    def __init__(self, unit_of_work: UnitOfWork, auth: AuthenticationService) -> None:
        self.unit_of_work = unit_of_work
        self.auth = auth
        self.gateway = GatewayClient(SandboxGateway())
        self.risk = RiskEngine(
            unit_of_work,
            [AmountRule(), VelocityRule(), CountryRule()],
        )

    def create_payment(self, token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Authenticate, score, persist, and authorize a payment request."""
        principal = self.auth.authenticate(token)
        if not principal.can_charge():
            raise PaymentDeclined("principal is not allowed to charge")
        request = PaymentRequest(
            request_id=str(payload["request_id"]),
            customer_id=principal.customer.customer_id,
            amount=Decimal(str(payload["amount"])),
            currency=str(payload["currency"]),
            merchant_id=str(payload["merchant_id"]),
            ip_address=str(payload["ip_address"]),
            created_at=datetime.now(timezone.utc),
            attributes=dict(payload.get("attributes", {})),
        )
        existing = self.unit_of_work.payments.find_result(request.request_id)
        if existing is not None:
            return existing.as_dict()
        self.unit_of_work.payments.save_request(request)
        decision = self.risk.evaluate(principal.customer, request)
        if not decision.approved:
            result = PaymentResult(request.request_id, False, reason="risk review required")
        else:
            result = self.gateway.charge(request)
        self.unit_of_work.payments.save_result(result)
        return self._response(result, decision.score, decision.signals)

    def get_health(self) -> Dict[str, bool]:
        """Expose a health endpoint for orchestration probes."""
        return {"healthy": self.unit_of_work.healthcheck()}

    @staticmethod
    def _response(result: PaymentResult, risk_score: float, signals: list[str]) -> Dict[str, Any]:
        """Combine provider and risk metadata into an API response."""
        response = result.as_dict()
        response["risk_score"] = risk_score
        response["risk_signals"] = signals
        return response


def build_demo_router() -> PaymentRouter:
    """Wire the service graph in one place for local execution."""
    unit_of_work = UnitOfWork()
    from auth_service import TokenIssuer
    auth = AuthenticationService(unit_of_work, TokenIssuer("local-demo-secret"))
    return PaymentRouter(unit_of_work, auth)


if __name__ == "__main__":
    router = build_demo_router()
    print(router.get_health())
