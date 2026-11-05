package com.example.checkout.service;

import com.example.checkout.dto.CustomerDto;
import com.example.checkout.dto.PaymentMethodDto;
import com.example.checkout.exception.InvalidPaymentException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class PaymentValidatorTest {

    private PaymentValidator validator;
    private CustomerDto authenticatedCustomer;
    private PaymentMethodDto creditCard;

    @BeforeEach
    void setUp() {
        validator = new PaymentValidator();
        authenticatedCustomer = new CustomerDto(UUID.randomUUID(), "Alice Smith", "alice@example.com");
        creditCard = new PaymentMethodDto("CREDIT_CARD", "************1234", "USD");
    }

    @Test
    @DisplayName("Valid payment with authenticated customer succeeds")
    void testValidPaymentWithCustomer_ShouldPass() {
        boolean result = validator.validate(authenticatedCustomer, 99.99, creditCard);
        assertTrue(result, "Payment should be approved for valid customer and positive amount");
    }

    @Test
    @DisplayName("Non-positive payment amount throws InvalidPaymentException")
    void testNonPositiveAmount_ShouldThrowException() {
        assertThrows(InvalidPaymentException.class, () ->
                validator.validate(authenticatedCustomer, 0.0, creditCard)
        );

        assertThrows(InvalidPaymentException.class, () ->
                validator.validate(authenticatedCustomer, -15.50, creditCard)
        );
    }

    @Test
    @DisplayName("Missing payment method details throws InvalidPaymentException")
    void testMissingPaymentMethod_ShouldThrowException() {
        assertThrows(InvalidPaymentException.class, () ->
                validator.validate(authenticatedCustomer, 50.0, null)
        );

        PaymentMethodDto emptyType = new PaymentMethodDto(null, "1234", "USD");
        assertThrows(InvalidPaymentException.class, () ->
                validator.validate(authenticatedCustomer, 50.0, emptyType)
        );
    }
}
