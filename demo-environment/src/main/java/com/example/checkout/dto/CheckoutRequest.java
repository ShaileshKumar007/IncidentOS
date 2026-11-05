package com.example.checkout.dto;

import java.util.List;

/**
 * Incoming request payload for POST /api/checkout.
 */
public class CheckoutRequest {

    private CustomerDto customer;
    private List<CartItemDto> items;
    private PaymentMethodDto paymentMethod;

    public CheckoutRequest() {
    }

    public CheckoutRequest(CustomerDto customer, List<CartItemDto> items, PaymentMethodDto paymentMethod) {
        this.customer = customer;
        this.items = items;
        this.paymentMethod = paymentMethod;
    }

    public CustomerDto getCustomer() {
        return customer;
    }

    public void setCustomer(CustomerDto customer) {
        this.customer = customer;
    }

    public List<CartItemDto> getItems() {
        return items;
    }

    public void setItems(List<CartItemDto> items) {
        this.items = items;
    }

    public PaymentMethodDto getPaymentMethod() {
        return paymentMethod;
    }

    public void setPaymentMethod(PaymentMethodDto paymentMethod) {
        this.paymentMethod = paymentMethod;
    }
}
