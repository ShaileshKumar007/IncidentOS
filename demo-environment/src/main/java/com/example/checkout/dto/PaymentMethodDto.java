package com.example.checkout.dto;

/**
 * Payment method details.
 */
public class PaymentMethodDto {

    private String type;
    private String cardNumberMasked;
    private String currency;

    public PaymentMethodDto() {
    }

    public PaymentMethodDto(String type, String cardNumberMasked, String currency) {
        this.type = type;
        this.cardNumberMasked = cardNumberMasked;
        this.currency = currency;
    }

    public String getType() {
        return type;
    }

    public void setType(String type) {
        this.type = type;
    }

    public String getCardNumberMasked() {
        return cardNumberMasked;
    }

    public void setCardNumberMasked(String cardNumberMasked) {
        this.cardNumberMasked = cardNumberMasked;
    }

    public String getCurrency() {
        return currency;
    }

    public void setCurrency(String currency) {
        this.currency = currency;
    }
}
