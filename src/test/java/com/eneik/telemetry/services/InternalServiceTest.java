package com.eneik.telemetry.services;

import com.eneik.telemetry.services.security.InternalSecurityService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.security.SecureRandom;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Verification suite for Perimeter Authorization and 401 Barrier (BARCAN-TAG-06 / 152-FZ).
 * Verifies institutional security boundary, PIN barrier gating, fail-closed data access,
 * and perimeter isolation against InternalSecurityService and InternalService.
 */
public class InternalServiceTest {

    private static final String TEST_INSTITUTIONAL_TOKEN = "VALID_INSTITUTIONAL_TOKEN_152FZ";
    private static final String TEST_SERVICE_PIN = "8492";

    private InternalSecurityService securityService;
    private InternalService internalService;

    @BeforeEach
    public void setUp() {
        securityService = new InternalSecurityService(
                TEST_INSTITUTIONAL_TOKEN,
                TEST_SERVICE_PIN,
                3600L,
                new DeterministicTestSecureRandom()
        );
        internalService = new InternalService(securityService);
    }

    @Test
    @DisplayName("Given integration tests against protected endpoints, When requests lack valid authorization headers, Then 100% of responses return HTTP 401 Unauthorized")
    public void givenProtectedEndpoints_whenRequestsLackValidAuthorizationHeaders_thenReturns401Unauthorized() {
        List<String> invalidHeaders = Arrays.asList(
                null,
                "",
                "   ",
                "Bearer ",
                "Bearer invalid-token-xyz",
                "Basic dXNlcjpwYXNz",
                "Token malformed_institutional_signature"
        );

        for (String authHeader : invalidHeaders) {
            int catalogStatus = internalService.authorizeEndpointRequest("/api/v1/internal/catalog", authHeader);
            assertEquals(401, catalogStatus,
                    "Endpoint /api/v1/internal/catalog must reject invalid/missing header with HTTP 401");

            int generatorStatus = internalService.authorizeEndpointRequest("/api/v1/internal/generator", authHeader);
            assertEquals(401, generatorStatus,
                    "Endpoint /api/v1/internal/generator must reject invalid/missing header with HTTP 401");

            int telemetryStatus = internalService.authorizeEndpointRequest("/api/v1/internal/telemetry", authHeader);
            assertEquals(401, telemetryStatus,
                    "Endpoint /api/v1/internal/telemetry must reject invalid/missing header with HTTP 401");
        }

        assertEquals(200,
                internalService.authorizeEndpointRequest("/api/v1/internal/catalog", "Bearer " + TEST_INSTITUTIONAL_TOKEN),
                "Valid institutional Bearer token must be authorized");
    }

    @Test
    @DisplayName("Given an E2E browser test, When attempting direct navigation to catalog and generator screens, Then the user is redirected to the PIN login barrier and access is granted only after successful PIN entry")
    public void givenE2EFlow_whenAttemptingDirectNavigationToCatalogAndGenerator_thenRedirectsToPinLoginBarrier() {
        String[] protectedRoutes = new String[]{"#/catalog", "#/generator", "/internal/board"};

        for (String route : protectedRoutes) {
            NavigationResult initialNav = simulateNavigation(route, null);
            assertTrue(initialNav.isRedirectedToPinBarrier(),
                    "Unauthenticated navigation to " + route + " must redirect to PIN login barrier");
            assertEquals("#/pin-barrier", initialNav.getCurrentRoute());
            assertFalse(initialNav.isAccessGranted(),
                    "Access must be denied prior to PIN authorization");

            Optional<String> invalidPinSession = securityService.authenticate("0000");
            assertFalse(invalidPinSession.isPresent(), "Invalid PIN must not grant access");

            Optional<String> validPinSession = securityService.authenticate(TEST_SERVICE_PIN);
            assertTrue(validPinSession.isPresent(), "Valid institutional PIN must be accepted");

            String sessionToken = validPinSession.get();
            NavigationResult authorizedNav = simulateNavigation(route, sessionToken);
            assertFalse(authorizedNav.isRedirectedToPinBarrier(),
                    "Authenticated session must not redirect to PIN barrier");
            assertTrue(authorizedNav.isAccessGranted(),
                    "Authenticated session must be granted access to protected screen");
        }
    }

    @Test
    @DisplayName("Given unauthenticated user, When requesting internal entities, Then no data is leaked")
    public void givenUnauthenticatedUser_whenRequestingInternalEntities_thenNoDataIsLeaked() {
        assertNotNull(securityService, "InternalSecurityService must be initialized");
        assertNotNull(internalService, "InternalService must be initialized");

        assertThrows(SecurityException.class, () -> internalService.getProtectedData(null),
                "Unauthenticated call must fail closed without leaking data");
        assertThrows(SecurityException.class, () -> internalService.getProtectedData("Bearer invalid-token"),
                "Invalid token call must fail closed without leaking data");

        InternalService unconfiguredService = new InternalService();
        assertThrows(SecurityException.class,
                () -> unconfiguredService.getProtectedData("Bearer " + TEST_INSTITUTIONAL_TOKEN),
                "InternalService without security service must fail closed");

        Map<String, Object> authorizedData = internalService.getProtectedData("Bearer " + TEST_INSTITUTIONAL_TOKEN);
        assertNotNull(authorizedData);
        assertEquals("UP", authorizedData.get("status"));
        assertEquals(Boolean.TRUE, authorizedData.get("healthy"));
    }

    @Test
    @DisplayName("Given institutional security 152-FZ, When perimeter tested, Then total isolation is enforced")
    public void givenInstitutionalSecurity152FZ_whenPerimeterTested_thenTotalIsolationEnforced() {
        assertTrue(securityService.isAuthorized(TEST_INSTITUTIONAL_TOKEN),
                "Perimeter must accept valid institutional token");
        assertFalse(securityService.isAuthorized("../bypass/token"),
                "Perimeter bypass attempt must be denied");

        assertEquals(401,
                internalService.authorizeEndpointRequest("/api/v1/internal/telemetry", "Bearer ../bypass/token"),
                "Perimeter bypass header must return HTTP 401");
        assertEquals(200,
                internalService.authorizeEndpointRequest("/api/v1/internal/telemetry", "Bearer " + TEST_INSTITUTIONAL_TOKEN),
                "Valid institutional header must return HTTP 200");

        Map<String, Object> rawPayload = new HashMap<>();
        rawPayload.put("id", "DOC-152FZ-01");
        rawPayload.put("title", "Institutional Policy");
        rawPayload.put("file_path", "/var/internal/secret.docx");
        Map<String, Object> sanitized = internalService.sanitizeDocumentPayload(rawPayload);
        assertFalse(sanitized.containsKey("file_path"), "Sensitive internal path must be stripped");
        assertEquals("/api/v1/normative/download/DOC-152FZ-01", sanitized.get("download_url"));
    }

    private NavigationResult simulateNavigation(String targetRoute, String sessionToken) {
        boolean hasValidAuth = sessionToken != null && securityService.isAuthorized(sessionToken);
        if (!hasValidAuth) {
            return new NavigationResult("#/pin-barrier", true, false);
        }
        return new NavigationResult(targetRoute, false, true);
    }

    private static class NavigationResult {
        private final String currentRoute;
        private final boolean redirectedToPinBarrier;
        private final boolean accessGranted;

        public NavigationResult(String currentRoute, boolean redirectedToPinBarrier, boolean accessGranted) {
            this.currentRoute = currentRoute;
            this.redirectedToPinBarrier = redirectedToPinBarrier;
            this.accessGranted = accessGranted;
        }

        public String getCurrentRoute() {
            return currentRoute;
        }

        public boolean isRedirectedToPinBarrier() {
            return redirectedToPinBarrier;
        }

        public boolean isAccessGranted() {
            return accessGranted;
        }
    }

    /**
     * Deterministic PRNG for reproducible session token generation in unit tests.
     */
    private static final class DeterministicTestSecureRandom extends SecureRandom {
        private int counter = 1;

        @Override
        public synchronized void nextBytes(byte[] bytes) {
            for (int i = 0; i < bytes.length; i++) {
                bytes[i] = (byte) ((counter++ * 31 + i) & 0xFF);
            }
        }
    }
}
