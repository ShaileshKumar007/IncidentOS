package com.example.checkout.controller;

import com.example.checkout.dto.CartItemDto;
import com.example.checkout.dto.CheckoutRequest;
import com.example.checkout.dto.CustomerDto;
import com.example.checkout.dto.PaymentMethodDto;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;
import java.util.UUID;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class CheckoutControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    @DisplayName("GET /api/health returns UP status and service info")
    void testHealthEndpoint() throws Exception {
        mockMvc.perform(get("/api/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"))
                .andExpect(jsonPath("$.service").value("checkout-service"));
    }

    @Test
    @DisplayName("POST /api/checkout with valid authenticated customer returns 200 OK")
    void testSuccessfulCheckout() throws Exception {
        CustomerDto customer = new CustomerDto(UUID.randomUUID(), "Alice Smith", "alice@example.com");
        CartItemDto item = new CartItemDto("prod-100", "Wireless Mouse", 1, 49.99);
        PaymentMethodDto payment = new PaymentMethodDto("CREDIT_CARD", "************1234", "USD");

        CheckoutRequest request = new CheckoutRequest(customer, List.of(item), payment);

        mockMvc.perform(post("/api/checkout")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("SUCCESS"))
                .andExpect(jsonPath("$.orderId").exists());
    }

    @Test
    @DisplayName("POST /api/checkout with empty cart returns 400 Bad Request")
    void testEmptyCartBadRequest() throws Exception {
        CustomerDto customer = new CustomerDto(UUID.randomUUID(), "Bob Doe", "bob@example.com");
        PaymentMethodDto payment = new PaymentMethodDto("CREDIT_CARD", "************1234", "USD");

        CheckoutRequest request = new CheckoutRequest(customer, List.of(), payment);

        mockMvc.perform(post("/api/checkout")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").value("Bad Request"));
    }
}
