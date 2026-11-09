package com.eneik.telemetry.services.security;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;

public class InternalSecurityServiceTest {

    private InternalSecurityService securityService;

    @BeforeEach
    void setUp() {
        securityService = new InternalSecurityService();
    }

    @Test
    @DisplayName("Given invalid or missing token, When validating perimeter access, Then access is denied")
    void testPerimeterAccessDeniedForMissingOrInvalidCredentials() {
        assertFalse(securityService.validateInstitutionalToken(null));
        assertFalse(securityService.validateInstitutionalToken(""));
        assertFalse(securityService.validateInstitutionalToken("Bearer invalid-token"));

        assertFalse(securityService.validatePin(null));
        assertFalse(securityService.validatePin(""));
        assertFalse(securityService.validatePin("0000"));
    }

    @Test
    @DisplayName("Given valid institutional credentials, When validating perimeter access, Then access is granted")
    void testPerimeterAccessGrantedForValidCredentials() {
        String validToken = "INSTITUTIONAL-TOKEN-ASU-OC";
        String validPin = "2026";

        assertTrue(securityService.validateInstitutionalToken(validToken));
        assertTrue(securityService.validatePin(validPin));
    }

    @Test
    @DisplayName("Given raw authorization header, When extracting bearer token, Then token is parsed correctly")
    void testExtractBearerToken() {
        assertEquals(Optional.empty(), securityService.extractBearerToken(null));
        assertEquals(Optional.empty(), securityService.extractBearerToken("Basic dXNlcjpwYXNz"));
        assertEquals(Optional.of("abc-token"), securityService.extractBearerToken("Bearer abc-token"));
    }
}
