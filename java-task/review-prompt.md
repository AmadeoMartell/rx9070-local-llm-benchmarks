You are reviewing code quality of LLM-agent-generated Java projects. READ-ONLY: do not build, do not run gradle/docker, do not modify files. Ignore everything under build/, .gradle/, bin/.

All projects implement the same spec: <path>/SPEC.md (read it first). Multi-module Gradle: contracts (WSDL+XSD+proto), inventory-service (gRPC, Postgres), order-service (SOAP JAX-WS contract-first, Bean Validation, AES-256-GCM PII encryption with key from env PII_KEY, gRPC client to inventory, Postgres), Dockerfiles + docker-compose, Testcontainers integration test.

Review these projects (full paths):
1. <path to project 1>
2. <path to project 2>
3. <path to project 3>
4. <path to project 4>

Score each project 0-10 on each axis (be strict and consistent across projects; 10 = production-grade, 5 = works but notable flaws, 0 = missing):
A. Correctness of order flow: validation happens before any gRPC call/persistence; what happens if gRPC reserve fails or DB insert fails after reserve (orphan rows / lost stock / compensation); transactions; error -> SOAP fault mapping.
B. Contract-first fidelity: SOAP SEI/types generated from WSDL/XSD (wsimport/xjc) vs handwritten SEI; gRPC stubs generated from the proto; single proto (no duplicated copies); proto fields mirror XSD types.
C. Security: GCM with 12-byte random IV per record (SecureRandom), 128-bit tag, IV stored with ciphertext; key strictly from PII_KEY with NO fallback/default key anywhere (code, properties, compose `${PII_KEY:-...}`); SQL parameterized; no PII logged.
D. Tests: real Testcontainers Postgres; happy path asserts DB row + stock decrement + ciphertext != plaintext in DB; invalid order -> fault AND nothing persisted (asserted); AES round-trip unit test; real gRPC/SOAP exercised vs mocks; meaningful assertions.
E. Code structure & hygiene: separation of concerns, resource handling (gRPC channel shutdown, JDBC connections closed/pooled), no dead code/debug leftovers, reasonable size, readable.
F. Docker/compose: Dockerfile per service that actually builds the right jar, compose with postgres + both services, env wiring (DB url, inventory host, PII_KEY), depends_on/healthcheck.

For each project return exactly:
PROJECT <name>
SCORES A=<n> B=<n> C=<n> D=<n> E=<n> F=<n> TOTAL=<sum of 60>
DEFECTS (top 3 real defects, each with file:line and one sentence on concrete consequence)
STRENGTHS (1-2 short items)

Only claim a defect you verified by reading the file; cite the exact file and line. Keep the whole answer under 1100 words.
