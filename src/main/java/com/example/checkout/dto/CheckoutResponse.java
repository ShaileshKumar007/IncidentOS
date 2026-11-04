package com.example.checkout.dto;

import java.time.Instant;

/**
 * Outgoing response payload for POST /api/checkout.
 */
public class CheckoutResponse {

    private String orderId;
    private String status;
    private double totalAmount;
    private String message;
    private Instant processedAt;

    public CheckoutResponse() {
    }

    public CheckoutResponse(String orderId, String status, double totalAmount, String message, Instant processedAt) {
        this.orderId = orderId;
        this.status = status;
        this.totalAmount = totalAmount;
        this.message = message;
        this.processedAt = processedAt;
    }

    public String getOrderId() {
        return orderId;
    }

    public void setOrderId(String orderId) {
        this.orderId = orderId;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public double getTotalAmount() {
        return totalAmount;
    }

    public void setTotalAmount(double totalAmount) {
        this.totalAmount = totalAmount;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public Instant getProcessedAt() {
        return processedAt;
    }

    public void setProcessedAt(Instant processedAt) {
        this.processedAt = processedAt;
    }
}
