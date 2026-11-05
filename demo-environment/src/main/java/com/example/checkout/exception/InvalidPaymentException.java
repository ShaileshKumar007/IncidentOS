package com.example.checkout.exception;

/**
 * Thrown when payment parameters or amount validation fails.
 */
public class InvalidPaymentException extends RuntimeException {

    public InvalidPaymentException(String message) {
        super(message);
    }
}
