# Graph Report - demo_codebase  (2026-10-31)

## Corpus Check
- 6 files · ~1,483 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 152 nodes · 309 edges · 7 communities (5 shown, 2 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 50 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9f561149`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- database.py
- api_router.py
- PaymentRequest
- PaymentRouter
- PaymentResult
- auth_service.py
- RiskDecision

## God Nodes (most connected - your core abstractions)
1. `PaymentRequest` - 28 edges
2. `Customer` - 27 edges
3. `PaymentResult` - 20 edges
4. `PaymentRouter` - 18 edges
5. `UnitOfWork` - 14 edges
6. `AuthenticationService` - 12 edges
7. `PaymentRepository` - 11 edges
8. `GatewayClient` - 11 edges
9. `RiskEngine` - 11 edges
10. `PaymentDeclined` - 10 edges

## Surprising Connections (you probably didn't know these)
- `PaymentRouter` --uses--> `PaymentDeclined`  [INFERRED]
  demo_codebase/api_router.py → demo_codebase/models.py
- `PaymentRouter` --uses--> `PaymentRequest`  [INFERRED]
  demo_codebase/api_router.py → demo_codebase/models.py
- `PaymentRouter` --uses--> `PaymentResult`  [INFERRED]
  demo_codebase/api_router.py → demo_codebase/models.py
- `PaymentRouter` --uses--> `GatewayClient`  [INFERRED]
  demo_codebase/api_router.py → demo_codebase/payment_gateway.py
- `PaymentRouter` --uses--> `SandboxGateway`  [INFERRED]
  demo_codebase/api_router.py → demo_codebase/payment_gateway.py

## Import Cycles
- None detected.

## Communities (7 total, 2 thin omitted)

### Community 0 - "database.py"
Cohesion: 0.08
Nodes (3): CustomerRepository, PaymentRepository, Repository

### Community 1 - "api_router.py"
Cohesion: 0.12
Nodes (5): AccountStatus, PaymentDeclined, GatewayClient, GatewayProvider, SandboxGateway

### Community 2 - "PaymentRequest"
Cohesion: 0.14
Nodes (6): Customer, PaymentRequest, AmountRule, CountryRule, RiskRule, VelocityRule

### Community 3 - "PaymentRouter"
Cohesion: 0.13
Nodes (6): build_demo_router(), PaymentRouter, AuthenticationService, TokenIssuer, UnitOfWork, RiskEngine

### Community 5 - "auth_service.py"
Cohesion: 0.11
Nodes (3): AuthenticatedPrincipal, AuthenticationError, ServiceError

## Knowledge Gaps
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Customer` connect `PaymentRequest` to `database.py`, `api_router.py`, `PaymentRouter`, `auth_service.py`?**
  _High betweenness centrality (0.245) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `PaymentRequest` (e.g. with `PaymentRouter` and `PaymentRepository`) actually correct?**
  _`PaymentRequest` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Should `database.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07635467980295567 - nodes in this community are weakly interconnected._
- **Why does `PaymentRequest` connect `PaymentRequest` to `database.py`, `api_router.py`, `PaymentRouter`, `PaymentResult`?**
  _High betweenness centrality (0.222) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `Customer` (e.g. with `AuthenticatedPrincipal` and `AuthenticationService`) actually correct?**
  _`Customer` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Should `api_router.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1164021164021164 - nodes in this community are weakly interconnected._
- **Why does `PaymentResult` connect `PaymentResult` to `database.py`, `api_router.py`, `PaymentRouter`?**
  _High betweenness centrality (0.147) - this node is a cross-community bridge._