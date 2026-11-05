# IncidentOS Demo Environment: Checkout Service

This directory contains the standalone Java 21 / Spring Boot 3.3.0 microservice used by IncidentOS to demonstrate multi-agent incident response and triage.

---

## 1. Service Overview

- **Service Name**: `checkout-service`
- **Runtime**: Java 21 (Homebrew `openjdk@21`)
- **Framework**: Spring Boot 3.3.0 (Gradle 9.8.2 / Gradle Wrapper)
- **Port**: `8080` (binds to `127.0.0.1:8080`)
- **Logging**: Structured console and rolling file logging to `logs/application.log` and `logs/application.jsonl`.
- **Git Repository**: Self-contained Git repository with realistic commit history.

---

## 2. Layered Architecture

```
demo-environment/
├── build.gradle                                            # Gradle build configuration & custom tasks
├── gradlew                                                 # POSIX Gradle wrapper script
├── gradle/wrapper/                                         # Gradle wrapper binaries & configuration
├── deployments/
│   └── history.json                                        # CI/CD deployment history fixture
├── logs/
│   ├── application.log                                     # Plaintext Spring Boot application log
│   ├── application.jsonl                                   # Structured JSONL log events
│   └── error-traces.jsonl                                  # Full stack traces for diagnostic search
└── src/
    ├── main/
    │   ├── java/com/example/checkout/
    │   │   ├── CheckoutApplication.java                    # Spring Boot Application entrypoint
    │   │   ├── controller/
    │   │   │   ├── CheckoutController.java                 # POST /api/checkout endpoint
    │   │   │   └── HealthController.java                   # GET /api/health endpoint
    │   │   ├── dto/
    │   │   │   ├── CartItemDto.java                        # Item id, name, quantity, unit price
    │   │   │   ├── CheckoutRequest.java                    # Customer, cart items, payment method
    │   │   │   ├── CheckoutResponse.java                   # Order ID, status, total, timestamp
    │   │   │   ├── CustomerDto.java                        # Customer UUID, name, email
    │   │   │   ├── ErrorResponseDto.java                   # Error code, message, path, timestamp
    │   │   │   └── PaymentMethodDto.java                   # Method type, masked account, currency
    │   │   ├── exception/
    │   │   │   ├── GlobalExceptionHandler.java             # Centralized @ControllerAdvice handler
    │   │   │   └── InvalidPaymentException.java            # Custom unchecked payment exception
    │   │   └── service/
    │   │       ├── CheckoutService.java                    # Cart validation, total calculation, order ID
    │   │       └── PaymentValidator.java                   # Payment validation (culprit class)
    │   └── resources/
    │       └── application.properties                      # Logging and server configuration
    └── test/
        └── java/com/example/checkout/
            ├── controller/
            │   └── CheckoutControllerTest.java             # MockMvc integration tests (3 tests)
            ├── regression/
            │   └── GuestCheckoutRegressionTest.java        # Tagged @Tag("regression") (1 test)
            └── service/
                ├── CheckoutServiceTest.java                # Cart & price validation tests (5 tests)
                └── PaymentValidatorTest.java               # Payment logic & validation tests (4 tests)
```

---

## 3. The Intentional Production Regression

### The Bug Scenario
In release `1.4.1` (commit `812b5e3`), payment validation safely handled both authenticated customers and unauthenticated guest checkouts:

```java
// Safe implementation in v1.4.1 (commit 812b5e3):
UUID customerId = (customer != null) ? customer.getId() : null;
```

In release `1.4.2` (commit `6014328`, *"feat: simplify customer session validation in checkout"*), the null check was mistakenly removed on the assumption that checkout sessions always have an authenticated customer:

```java
// Flawed implementation in v1.4.2 (commit 6014328, line 42):
UUID customerId = customer.getId();
```

### The Failure Mechanism
- **Authenticated Checkouts**: Include a populated `customer` object. Validation succeeds with HTTP 200.
- **Guest Checkouts**: Supply `"customer": null` in the payload. Invoking `customer.getId()` throws `java.lang.NullPointerException` at line 42 of `PaymentValidator.java`.
- **Observed Symptom**: HTTP 500 Internal Server Error returned to the client, logged with a full stack trace in `logs/application.log`.

---

## 4. Building and Running

### Prerequisites
- Java 21 (`java -version` returns `21.x`)
- Gradle (or use the provided `./gradlew`)

### Start the Application
Run the Spring Boot application using the dedicated `runApp` task:

```bash
cd demo-environment
./gradlew runApp
```

The application starts on port `8080` (http://localhost:8080).

### Verify Endpoints

#### 1. Health Check
```bash
curl -s http://localhost:8080/api/health
# Response: {"status":"UP","service":"checkout-service","version":"1.4.2","timestamp":"..."}
```

#### 2. Authenticated Checkout (Success: HTTP 200)
```bash
curl -s -X POST http://localhost:8080/api/checkout \
  -H "Content-Type: application/json" \
  -d '{
    "customer": {
      "id": "7b8a531b-d1e9-4674-a62d-4828da1b98a1",
      "fullName": "Jane Doe",
      "email": "jane.doe@example.com"
    },
    "items": [
      {
        "productId": "prod-101",
        "name": "Wireless Headphones",
        "quantity": 1,
        "unitPrice": 129.99
      }
    ],
    "paymentMethod": {
      "type": "CREDIT_CARD",
      "accountIdentifier": "************4321",
      "currency": "USD"
    }
  }'
# Response: {"orderId":"order-...","status":"SUCCESS","totalAmount":129.99,"processedAt":"..."}
```

#### 3. Guest Checkout (Failure: HTTP 500 NPE)
```bash
curl -s -X POST http://localhost:8080/api/checkout \
  -H "Content-Type: application/json" \
  -d '{
    "customer": null,
    "items": [
      {
        "productId": "prod-102",
        "name": "USB-C Adapter",
        "quantity": 2,
        "unitPrice": 14.50
      }
    ],
    "paymentMethod": {
      "type": "DEBIT_CARD",
      "accountIdentifier": "************8811",
      "currency": "USD"
    }
  }'
# Response: {"errorCode":"INTERNAL_ERROR","message":"Cannot invoke \"com.example.checkout.dto.CustomerDto.getId()\" because \"customer\" is null","path":"/api/checkout","timestamp":"..."}
```

---

## 5. Automated Test Suites

The test suite separates normal unit tests from the regression reproduction test using JUnit 5 tags:

### 1. Unit Tests (Excludes Regression Test)
Executes all 12 standard unit tests. All tests pass on the flawed branch:

```bash
cd demo-environment
./gradlew unitTest
# Result: 12 tests PASSED, 0 failed
```

### 2. Regression Reproduction Test
Executes the isolated guest checkout test (`GuestCheckoutRegressionTest`). Fails on the flawed code with `NullPointerException` at `PaymentValidator.java:42`:

```bash
cd demo-environment
./gradlew regressionTest
# Result: 1 test FAILED (Expected: NPE at PaymentValidator.java:42)
```

### 3. Full Test Suite (Fails on Flawed Code)
```bash
cd demo-environment
./gradlew test
# Result: 12 PASSED, 1 FAILED
```

---

## 6. Git History & Investigation Alignment

The Git repository contains verified, chronological commits:

```
6014328 (HEAD -> main) feat: simplify customer session validation in checkout
812b5e3 feat: initial checkout-service release v1.4.1
```

- **Commit `812b5e3`**: Working release `1.4.1` with all 13 tests passing.
- **Commit `6014328`**: Breaking release `1.4.2` that removed the null-check.
- **Diff Inspection**:
  ```bash
  git diff 812b5e3..6014328
  ```
  Clearly displays the regression in `PaymentValidator.java` around line 42.

---

## 7. IncidentOS Backend Integration

The IncidentOS FastAPI backend (`backend/app/tools/`) integrates directly with this environment:

| Tool Endpoint | Target in `demo-environment/` | Purpose |
| :--- | :--- | :--- |
| `GET /api/tools/deployments` | `deployments/history.json` | Identifies deployment `dep-20261104-002` (commit `6014328`) |
| `GET /api/tools/logs/search` | `logs/*.jsonl` | Discovers NPE stack traces at `PaymentValidator.java:42` |
| `GET /api/tools/git/history` | Git repository | Lists recent commits (`6014328`, `812b5e3`) |
| `GET /api/tools/git/diff` | Git repository | Generates diff revealing the breaking change |
| `POST /api/tools/tests/run` | `./gradlew unitTest` / `regressionTest` | Executes sandboxed test suites and records pass/fail counts |
