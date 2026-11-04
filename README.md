# Demo Environment: Fictional Checkout Service

This directory contains the standalone Java 21 / Spring Boot fictional microservice used to reproduce and demonstrate incident response.

## Service Details (Milestone 3)
- **Application**: `checkout-service`
- **Framework**: Spring Boot 3.x (Java 21)
- **Target Endpoint**: `POST /api/checkout`
- **Flawed Class**: `src/main/java/com/example/checkout/service/PaymentValidator.java`
- **Bug Mechanism**: Missing null-check on `Customer` object during guest checkout leading to `NullPointerException`.
- **Logs**: Output to `logs/application.log` with realistic timestamps and stack traces.
- **Test Suite**: JUnit 5 test suite containing standard unit tests and a failing regression test (`PaymentValidatorTest`).
