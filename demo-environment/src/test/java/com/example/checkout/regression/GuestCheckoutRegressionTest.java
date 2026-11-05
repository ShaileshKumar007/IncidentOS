package com.example.checkout.regression;

import com.example.checkout.dto.CartItemDto;
import com.example.checkout.dto.CheckoutRequest;
import com.example.checkout.dto.CheckoutResponse;
import com.example.checkout.dto.PaymentMethodDto;
import com.example.checkout.service.CheckoutService;
import com.example.checkout.service.PaymentValidator;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * REPRODUCIBLE REGRESSION TEST: Guest Checkout Flow.
 *
 * Demonstrates the production regression introduced in commit 7f2a1b94c3d2.
 * Guest checkout payloads supply customer = null.
 *
 * EXPECTED BEHAVIOR (Prior to regression / after fix):
 * - Guest checkout succeeds and assigns a guest session or proceeds under threshold.
 *
 * ACTUAL BEHAVIOR (Flawed code in v1.4.2):
 * - FAILS with java.lang.NullPointerException at com.example.checkout.service.PaymentValidator.validate(PaymentValidator.java:42)
 *
 * THIS TEST IS INTENTIONALLY DESIGNED TO FAIL ON THE FLAWED CODE TO REPRODUCE THE INCIDENT.
 */
@Tag("regression")
class GuestCheckoutRegressionTest {

    private PaymentValidator paymentValidator;
    private CheckoutService checkoutService;

    @BeforeEach
    void setUp() {
        paymentValidator = new PaymentValidator();
        checkoutService = new CheckoutService(paymentValidator);
    }

    @Test
    @DisplayName("Guest checkout with null customer object should complete successfully")
    void testGuestCheckout_ShouldSucceed() {
        // Customer is null for guest checkout
        CartItemDto item = new CartItemDto("prod-guest-001", "USB Cable", 1, 19.99);
        PaymentMethodDto payment = new PaymentMethodDto("CREDIT_CARD", "************9999", "USD");

        CheckoutRequest guestRequest = new CheckoutRequest(null, List.of(item), payment);

        // On the flawed v1.4.2 implementation, processCheckout triggers
        // PaymentValidator.validate(null, 19.99, payment), which throws NullPointerException at line 42!
        CheckoutResponse response = checkoutService.processCheckout(guestRequest);

        assertNotNull(response, "Guest checkout response should not be null");
        assertEquals("SUCCESS", response.getStatus());
        assertEquals(19.99, response.getTotalAmount());
    }
}
