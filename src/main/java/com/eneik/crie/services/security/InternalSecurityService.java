package com.eneik.crie.services.security;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.bind.annotation.ResponseStatus;

import java.security.SecureRandom;
import java.time.Instant;
import java.util.Base64;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Access Guard service enforcing mandatory institutional token/PIN authentication
 * and perimeter isolation in compliance with 152-FZ.
 */
@Service
public class InternalSecurityService {

    private static final Logger log = LoggerFactory.getLogger(InternalSecurityService.class);
    private static final long DEFAULT_SESSION_DURATION_SECONDS = 3600L; // 1 hour

    private final SecureRandom secureRandom = new SecureRandom();
    private final Map<String, Instant> activeSessions = new ConcurrentHashMap<>();

    @Value("${crie.security.institutional-token:INSTITUTIONAL-TOKEN-152FZ}")
    private String validInstitutionalToken;

    @Value("${crie.security.institutional-pin:2026}")
    private String validInstitutionalPin;

    @ResponseStatus(HttpStatus.UNAUTHORIZED)
    public static class UnauthorizedException extends RuntimeException {
        public UnauthorizedException(String message) {
            super(message);
        }
    }

    /**
     * Validates supplied institutional credentials (token or PIN).
     *
     * @param credential token or PIN entered by user
     * @return true if matches institutional secret
     */
    public boolean validateInstitutionalCredential(String credential) {
        if (credential == null || credential.trim().isEmpty()) {
            return false;
        }
        String sanitized = credential.trim();
        return sanitized.equals(validInstitutionalToken) || sanitized.equals(validInstitutionalPin);
    }

    /**
     * Verifies institutional token or PIN and generates a secure session token.
     *
     * @param credential institutional token or PIN
     * @return issued session token
     * @throws UnauthorizedException if credentials are invalid
     */
    public String authenticateAndIssueSession(String credential) {
        if (!validateInstitutionalCredential(credential)) {
            log.warn("152-FZ Security: Unauthorized attempt with invalid institutional credential");
            throw new UnauthorizedException("Invalid institutional token or PIN. Access denied under 152-FZ compliance.");
        }

        byte[] randomBytes = new byte[32];
        secureRandom.nextBytes(randomBytes);
        String sessionToken = Base64.getUrlEncoder().withoutPadding().encodeToString(randomBytes);

        Instant expiry = Instant.now().plusSeconds(DEFAULT_SESSION_DURATION_SECONDS);
        activeSessions.put(sessionToken, expiry);
        log.info("152-FZ Security: Issued institutional session token expiring at {}", expiry);
        return sessionToken;
    }

    /**
     * Validates whether the given session token is active and unexpired.
     *
     * @param sessionToken bearer/session token
     * @return true if authenticated
     */
    public boolean isSessionValid(String sessionToken) {
        if (sessionToken == null || sessionToken.trim().isEmpty()) {
            return false;
        }

        Instant expiry = activeSessions.get(sessionToken);
        if (expiry == null) {
            return false;
        }

        if (Instant.now().isAfter(expiry)) {
            activeSessions.remove(sessionToken);
            return false;
        }

        return true;
    }

    /**
     * Asserts that a request is authenticated with a valid session token.
     * Throws 401 Unauthorized if not authenticated.
     *
     * @param sessionToken bearer/session token
     * @throws UnauthorizedException when unauthenticated
     */
    public void requireAuthentication(String sessionToken) {
        if (!isSessionValid(sessionToken)) {
            throw new UnauthorizedException("Unauthenticated: Mandatory institutional token/PIN verification required.");
        }
    }

    /**
     * Invalidates an existing session (logout).
     *
     * @param sessionToken bearer/session token
     */
    public void invalidateSession(String sessionToken) {
        if (sessionToken != null) {
            activeSessions.remove(sessionToken);
        }
    }
}
