package com.eneik.crie.services.security;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.security.MessageDigest;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Internal Security Service implementing mandatory perimeter access isolation
 * and institutional token/PIN authentication gate in compliance with 152-FZ.
 */
@Service
public class InternalSecurityService {

    private static final Logger log = LoggerFactory.getLogger(InternalSecurityService.class);
    private static final Duration DEFAULT_SESSION_TTL = Duration.ofHours(8);

    @Value("${crie.security.institutional-pin:152-FZ-CRIE-SECURE}")
    private String configuredInstitutionalPin;

    private final Map<String, Instant> activeSessions = new ConcurrentHashMap<>();

    /**
     * Verifies the institutional token/PIN and issues a session token if valid.
     *
     * @param institutionalCredential provided institutional token or PIN
     * @return a verified session token
     * @throws ResponseStatusException with 401 UNAUTHORIZED if invalid
     */
    public String authenticateInstitutionalCredential(String institutionalCredential) {
        if (institutionalCredential == null || institutionalCredential.trim().isEmpty()) {
            log.warn("Institutional authentication failed: empty credential provided");
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Mandatory institutional token/PIN required");
        }

        if (!constantTimeEquals(institutionalCredential.trim(), configuredInstitutionalPin.trim())) {
            log.warn("Institutional authentication failed: invalid token/PIN provided");
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid institutional token/PIN");
        }

        String sessionToken = UUID.randomUUID().toString();
        activeSessions.put(sessionToken, Instant.now().plus(DEFAULT_SESSION_TTL));
        log.info("Institutional access granted: session token issued");
        return sessionToken;
    }

    /**
     * Asserts that a request contains a valid, active institutional session token.
     * Blocks unauthorized access with 401 Unauthorized to trigger the client-side PIN entry modal.
     *
     * @param sessionToken the session bearer token
     * @throws ResponseStatusException with 401 UNAUTHORIZED if token is missing, expired, or invalid
     */
    public void enforcePerimeterAccess(String sessionToken) {
        if (!isValidSession(sessionToken)) {
            log.warn("Perimeter access denied: missing or invalid session token");
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Institutional authentication required (152-FZ)");
        }
    }

    /**
     * Checks whether the given session token is valid and unexpired.
     *
     * @param sessionToken the session token to check
     * @return true if valid and active, false otherwise
     */
    public boolean isValidSession(String sessionToken) {
        if (sessionToken == null || sessionToken.trim().isEmpty()) {
            return false;
        }

        cleanExpiredSessions();

        Instant expiry = activeSessions.get(sessionToken.trim());
        if (expiry == null) {
            return false;
        }

        if (Instant.now().isAfter(expiry)) {
            activeSessions.remove(sessionToken.trim());
            return false;
        }

        return true;
    }

    /**
     * Explicitly revokes an active institutional session.
     *
     * @param sessionToken the session token to invalidate
     */
    public void revokeSession(String sessionToken) {
        if (sessionToken != null) {
            activeSessions.remove(sessionToken.trim());
        }
    }

    private void cleanExpiredSessions() {
        Instant now = Instant.now();
        activeSessions.entrySet().removeIf(entry -> now.isAfter(entry.getValue()));
    }

    private boolean constantTimeEquals(String a, String b) {
        byte[] aBytes = a.getBytes(StandardCharsets.UTF_8);
        byte[] bBytes = b.getBytes(StandardCharsets.UTF_8);
        return MessageDigest.isEqual(aBytes, bBytes);
    }
}
