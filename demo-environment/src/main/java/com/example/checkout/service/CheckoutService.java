package com.example.checkout.service;

import com.example.checkout.dto.CartItemDto;
import com.example.checkout.dto.CheckoutRequest;
import com.example.checkout.dto.CheckoutResponse;
import com.example.checkout.exception.InvalidPaymentException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.UUID;

/**
 * Service coordinating checkout workflow, cart validation, and payment authorization.
 */
@Service
public class CheckoutService {

    private static final Logger log = LoggerFactory.getLogger(CheckoutService.class);

    private final PaymentValidator paymentValidator;

    public CheckoutService(PaymentValidator paymentValidator) {
        this.paymentValidator = paymentValidator;
    }

    public CheckoutResponse processCheckout(CheckoutRequest request) {
        if (request == null) {
            throw new IllegalArgumentException("Checkout request cannot be null");
        }

        if (request.getItems() == null || request.getItems().isEmpty()) {
            throw new IllegalArgumentException("Cart cannot be empty");
        }

        double totalAmount = 0.0;
        for (CartItemDto item : request.getItems()) {
            if (item.getProductId() == null || item.getProductId().trim().isEmpty()) {
                throw new IllegalArgumentException("Product ID must be provided for all cart items");
            }
            if (item.getQuantity() <= 0) {
                throw new IllegalArgumentException("Item quantity must be greater than zero for product: " + item.getProductId());
            }
            if (item.getUnitPrice() < 0) {
                throw new IllegalArgumentException("Unit price cannot be negative for product: " + item.getProductId());
            }
            totalAmount += item.getQuantity() * item.getUnitPrice();
        }

        log.info("Processing checkout order for {} items, calculated total: ${}", request.getItems().size(), totalAmount);

        // Validates payment - triggers PaymentValidator.validate()
        boolean isValid = paymentValidator.validate(request.getCustomer(), totalAmount, request.getPaymentMethod());
        if (!isValid) {
            throw new InvalidPaymentException("Payment validation declined by processor");
        }

        String orderId = "order-" + UUID.randomUUID().toString().substring(0, 8);
        log.info("Checkout completed successfully. Generated order ID: {}", orderId);

        return new CheckoutResponse(
                orderId,
                "SUCCESS",
                totalAmount,
                "Order placed successfully",
                Instant.now()
        );
    }
}
