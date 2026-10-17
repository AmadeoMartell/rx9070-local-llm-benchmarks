# self-project — Order/Inventory microservices (Java 21, Gradle)

Build a working multi-module Gradle project. Java 21. Use **Gradle** (no Maven).
Two microservices that must build, run in Docker, and pass integration tests.

## Modules
- `contracts` — shared schema artifacts: the SOAP **WSDL + XSD** and the gRPC `.proto`.
  XSD types (Order, OrderLine, Customer) are the single source of truth; the gRPC
  messages mirror the same fields (keep them in sync).
- `inventory-service` — owns stock. Exposes a **gRPC** service `InventoryService`
  with `ReserveStock(ReserveStockRequest) -> ReserveStockResponse`. Persists stock in Postgres.
- `order-service` — exposes a **SOAP** web service (contract-first from the WSDL/XSD,
  JAX-WS) `OrderPort.placeOrder(PlaceOrderRequest) -> PlaceOrderResponse`. On placeOrder it
  validates input, encrypts customer PII, then calls `inventory-service` over **gRPC**
  to reserve stock, and persists the order in Postgres.

## Required behaviour
1. **gRPC internal comms**: order-service -> inventory-service via gRPC (generated stubs from the proto).
2. **SOAP external contract**: order-service's public API is SOAP, generated contract-first from
   `contracts/src/main/resources/order.wsdl` + `order.xsd`. Return a SOAP fault on validation failure.
3. **Validation**: Jakarta Bean Validation (@NotNull, @Positive, @Email, @Size) on the order/customer;
   invalid input -> SOAP fault (no persistence, no gRPC call).
4. **Encryption**: customer email + address stored **encrypted** with AES-256-GCM (random IV per record,
   key from an env var `PII_KEY`); provide `CryptoUtil.encrypt/decrypt` with a round-trip unit test.
5. **Docker**: a `Dockerfile` per service and a `docker-compose.yml` that runs postgres +
   inventory-service + order-service, wired together.
6. **Tests (Testcontainers)**: an integration test that starts a Postgres container (Testcontainers),
   runs the full flow (SOAP placeOrder -> gRPC ReserveStock -> DB), and asserts:
   - happy path persists an order with stock reserved and PII stored encrypted (not plaintext in DB),
   - invalid order -> SOAP fault, nothing persisted,
   - AES round-trip works.
7. `gradle build` (including the tests) must succeed.

## Constraints
- Keep dependencies current/stable (grpc-java, protobuf gradle plugin, a JAX-WS/SOAP stack,
  testcontainers, postgres driver, a validation impl).
- Prefer contract-first codegen for both proto and WSDL/XSD.
- Small, clean, working over exhaustive. If a piece is too heavy, stub it but keep the build green
  and note it in a `NOTES.md`.
- Log what you do; if `gradle build` fails, read the error and fix it, then rebuild — iterate until green.

Deliverable: a project that `gradle build` compiles and whose Testcontainers integration test passes.
