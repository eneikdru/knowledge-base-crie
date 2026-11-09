package com.eneik.telemetry.services;

import com.eneik.telemetry.services.security.InternalSecurityService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

public class InternalPerimeterSecurityTest {

    private InternalSecurityService securityService;
    private InternalService internalService;

    @BeforeEach
    void setUp() {
        securityService = new InternalSecurityService();
        internalService = new InternalService(securityService);
    }

    @Test
    @DisplayName("Given request without authorization header, When invoking protected endpoint, Then 401 Unauthorized is enforced")
    void testProtectedEndpointWithoutAuthHeaderReturns401() {
        InternalService.SecurityResult result = internalService.verifyPerimeterAccess(null);
        assertNotNull(result);
        assertEquals(401, result.getStatusCode());
        assertFalse(result.isAuthorized());
        assertEquals("401 Unauthorized: Institutional token or valid PIN required", result.getMessage());
    }

    @Test
    @DisplayName("Given request with invalid credentials, When invoking protected endpoint, Then 401 Unauthorized is returned")
    void testProtectedEndpointWithInvalidCredentialsReturns401() {
        InternalService.SecurityResult result = internalService.verifyPerimeterAccess("Bearer malformed-token");
        assertNotNull(result);
        assertEquals(401, result.getStatusCode());
        assertFalse(result.isAuthorized());
    }

    @Test
    @DisplayName("Given request with valid institutional token or PIN, When invoking protected endpoint, Then 200 OK is granted")
    void testProtectedEndpointWithValidCredentialsPasses() {
        InternalService.SecurityResult resultWithToken = internalService.verifyPerimeterAccess("Bearer INSTITUTIONAL-TOKEN-ASU-OC");
        assertNotNull(resultWithToken);
        assertEquals(200, resultWithToken.getStatusCode());
        assertTrue(resultWithToken.isAuthorized());

        InternalService.SecurityResult resultWithPin = internalService.verifyPerimeterPinAccess("2026");
        assertNotNull(resultWithPin);
        assertEquals(200, resultWithPin.getStatusCode());
        assertTrue(resultWithPin.isAuthorized());
    }

    @Test
    @DisplayName("Given unauthenticated direct catalog or generator access attempt, Then access is intercepted")
    void testDirectNavigationBlockedWithoutAuth() {
        boolean catalogAccessible = internalService.isCatalogAccessible(null);
        assertFalse(catalogAccessible, "Catalog screen must not be accessible without authorization");

        boolean generatorAccessible = internalService.isGeneratorAccessible(null);
        assertFalse(generatorAccessible, "Generator screen must not be accessible without authorization");
    }
}
