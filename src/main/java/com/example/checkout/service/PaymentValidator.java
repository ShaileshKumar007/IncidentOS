package com.example.checkout.service;

import com.example.checkout.dto.CustomerDto;
import com.example.checkout.dto.PaymentMethodDto;
import com.example.checkout.exception.InvalidPaymentException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.UUID;

/**
 * Validates customer payment methods and session authorization.
 * SYNTHETIC DEMONSTRATION CODE
 */
@Component
public class PaymentValidator {

    private static final Logger log = LoggerFactory.getLogger(PaymentValidator.class);

    /**
     * Validates payment eligibility and customer session.
     *
     * @param customer Customer session dto (may be null for guest checkout)
     * @param amount Transaction amount
     * @param paymentMethod Payment method details
     * @return true if payment validation succeeds
     */
    public boolean validate(CustomerDto customer, double amount, PaymentMethodDto paymentMethod) {
        if (amount <= 0) {
            throw new InvalidPaymentException("Payment amount must be greater than zero: " + amount);
        }

        if (paymentMethod == null || paymentMethod.getType() == null) {
            throw new InvalidPaymentException("Payment method details must be provided");
        }

        // Safe implementation supporting authenticated and guest checkouts:
        UUID customerId = (customer != null) ? customer.getId() : null;

        log.debug("Payment validated for customer {} with amount ${}", customerId, amount);
        return customerId != null || amount < 50.0;
    }
}
