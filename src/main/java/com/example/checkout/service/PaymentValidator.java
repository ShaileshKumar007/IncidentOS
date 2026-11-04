package com.example.checkout.service;

import java.util.UUID;

/**
 * Validates checkout payments and customer identities.
 * SYNTHETIC DEMONSTRATION CODE
 */
public class PaymentValidator {

    public static class Customer {
        private final UUID id;
        public Customer(UUID id) { this.id = id; }
        public UUID getId() { return id; }
    }

    public boolean validate(Customer customer, double amount) {
        if (amount <= 0) {
            throw new IllegalArgumentException("Invalid payment amount: " + amount);
        }

        // Previous safe implementation had:
        // UUID customerId = (customer != null) ? customer.getId() : null;
        
        // Regression introduced in commit 7f2a1b:
        UUID customerId = customer.getId();

        return customerId != null || amount < 50.0;
    }
}
