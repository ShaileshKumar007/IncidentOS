package com.example.checkout.service;

import com.example.checkout.dto.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.Collections;
import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class CheckoutServiceTest {

    private PaymentValidator paymentValidator;
    private CheckoutService checkoutService;
    private CustomerDto customer;
    private PaymentMethodDto paymentMethod;

    @BeforeEach
    void setUp() {
        paymentValidator = new PaymentValidator();
        checkoutService = new CheckoutService(paymentValidator);
        customer = new CustomerDto(UUID.randomUUID(), "John Doe", "john@example.com");
        paymentMethod = new PaymentMethodDto("CREDIT_CARD", "************4321", "USD");
    }

    @Test
    @DisplayName("Successful checkout with authenticated customer returns complete order")
    void testSuccessfulCheckout_ShouldReturnOrder() {
        CartItemDto item1 = new CartItemDto("prod-001", "Ergonomic Keyboard", 1, 120.00);
        CartItemDto item2 = new CartItemDto("prod-002", "USB-C Cable", 2, 15.00);
        CheckoutRequest request = new CheckoutRequest(customer, List.of(item1, item2), paymentMethod);

        CheckoutResponse response = checkoutService.processCheckout(request);

        assertNotNull(response);
        assertNotNull(response.getOrderId());
        assertEquals("SUCCESS", response.getStatus());
        assertEquals(150.00, response.getTotalAmount());
        assertNotNull(response.getProcessedAt());
    }

    @Test
    @DisplayName("Null checkout request throws IllegalArgumentException")
    void testNullRequest_ShouldThrowException() {
        assertThrows(IllegalArgumentException.class, () ->
                checkoutService.processCheckout(null)
        );
    }

    @Test
    @DisplayName("Empty cart items list throws IllegalArgumentException")
    void testEmptyCart_ShouldThrowException() {
        CheckoutRequest request = new CheckoutRequest(customer, Collections.emptyList(), paymentMethod);
        assertThrows(IllegalArgumentException.class, () ->
                checkoutService.processCheckout(request)
        );
    }

    @Test
    @DisplayName("Invalid or non-positive quantity throws IllegalArgumentException")
    void testInvalidQuantity_ShouldThrowException() {
        CartItemDto item = new CartItemDto("prod-001", "Item", 0, 25.00);
        CheckoutRequest request = new CheckoutRequest(customer, List.of(item), paymentMethod);

        IllegalArgumentException ex = assertThrows(IllegalArgumentException.class, () ->
                checkoutService.processCheckout(request)
        );
        assertTrue(ex.getMessage().contains("quantity must be greater than zero"));
    }

    @Test
    @DisplayName("Negative unit price throws IllegalArgumentException")
    void testNegativeUnitPrice_ShouldThrowException() {
        CartItemDto item = new CartItemDto("prod-001", "Item", 1, -10.00);
        CheckoutRequest request = new CheckoutRequest(customer, List.of(item), paymentMethod);

        IllegalArgumentException ex = assertThrows(IllegalArgumentException.class, () ->
                checkoutService.processCheckout(request)
        );
        assertTrue(ex.getMessage().contains("Unit price cannot be negative"));
    }

    @Test
    @DisplayName("Missing product identifier throws IllegalArgumentException")
    void testMissingProductId_ShouldThrowException() {
        CartItemDto item = new CartItemDto(null, "Item", 1, 10.00);
        CheckoutRequest request = new CheckoutRequest(customer, List.of(item), paymentMethod);

        assertThrows(IllegalArgumentException.class, () ->
                checkoutService.processCheckout(request)
        );
    }
}
