# self-project — phase 2: reliability, events, migrations (on top of the existing project)

The project in this directory already implements SPEC.md (contracts, inventory-service over gRPC,
order-service over SOAP, Postgres, Docker, Testcontainers). Phase 2 extends it. Keep everything from
SPEC.md working: the existing tests must stay green. Java 21, Gradle (no Maven).

## Required behaviour
1. **One atomic reservation**: order-service reserves the stock of ALL order lines with ONE gRPC call.
   inventory-service reserves them in ONE database transaction: if any line lacks stock, nothing is
   reserved and the SOAP call returns a fault with code `OUT_OF_STOCK`.
2. **Compensation (saga)**: add `ReleaseStock(ReleaseStockRequest) -> ReleaseStockResponse` to the proto.
   If saving the order fails after the stock was reserved, order-service calls ReleaseStock for that
   reservation and returns a SOAP fault. Releasing the same reservation twice is a no-op.
3. **Idempotent placeOrder**: `PlaceOrderRequest` gets a required `requestId` (add it to the XSD AND the
   proto, keep them in sync). A repeated placeOrder with the same requestId returns the same orderId and
   reserves nothing again (enforced by a unique constraint in the database, not only in memory).
4. **Transactional outbox + Kafka**: order-service writes an `OrderPlaced` event (eventId, orderId,
   lines) into an `outbox` table in the same transaction as the order. A relay inside order-service
   publishes unsent outbox rows to the Kafka topic `orders.placed` and marks them sent.
   inventory-service consumes `orders.placed` and writes one `stock_movement` row per order line.
   - The consumer is idempotent by eventId: a duplicate event writes nothing new.
   - A message that cannot be parsed goes to `orders.placed.DLT` after at most 3 attempts; the consumer
     keeps processing the next messages.
5. **Flyway**: both services create and change their schema only through Flyway migrations
   (`V1__...` = the phase-1 schema, later versions for the new tables and columns).
6. **Configuration**: no default or placeholder `PII_KEY` anywhere (code, compose, Dockerfiles); a
   service started without it fails at startup with a clear message. docker-compose adds Kafka and
   passes PII_KEY from the environment.

## Tests (Testcontainers: Postgres + Kafka)
Integration tests that assert, through the real services and databases:
- an order with one line out of stock -> SOAP fault `OUT_OF_STOCK`, no stock reserved for any line;
- an order save failure after a successful reservation -> the stock is released (check the stock in
  inventory's database) and the client gets a SOAP fault;
- placeOrder twice with the same requestId -> one order, one reservation, the same orderId both times;
- a placed order -> an `OrderPlaced` event reaches inventory-service and `stock_movement` has its rows;
- the same event delivered twice -> the movements are written once;
- an unparseable message -> it ends up in `orders.placed.DLT` and a valid message after it is processed;
- startup without PII_KEY fails.
`gradle build` (all tests of phase 1 and phase 2) must succeed.

## Constraints
- Keep dependencies current/stable; use the official Kafka client or Spring Kafka, the Flyway core
  library and the Testcontainers Kafka module.
- Prefer changing the contracts first (XSD/WSDL/proto) and regenerating, as in phase 1.
- Record decisions and anything stubbed in `NOTES.md` (append a "Phase 2" section).
- Log what you do; if `gradle build` fails, read the error and fix it, then rebuild — iterate until green.
