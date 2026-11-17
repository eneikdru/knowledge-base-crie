package com.eneik.crie.services.security;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.security.SecureRandom;
import java.time.Instant;
import java.util.Base64;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Service enforcing mandatory institutional token and PIN perimeter access control
 * in compliance with 152-FZ isolation requirements.
 *
 * Provides credential validation, session issuance, and authorization checking
 * to block unauthenticated requests with 401 Unauthorized status.
 */
@Service
public class InternalSecurityService {

    private static final Logger log = LoggerFactory.getLogger(InternalSecurityService.class);
    private static final long DEFAULT_SESSION_TTL_SECONDS = 3600L;

    private final String institutionalToken;
    private final String institutionalPin;
    private final SecureRandom secureRandom = new SecureRandom();
    private final Map<String, Long> activeSessions = new ConcurrentHashMap<>();

    public InternalSecurityService(
            @Value("${crie.security.institutional-token:INST-CRIE-SECURE-2026}") String institutionalToken,
            @Value("${crie.security.institutional-pin:2026}") String institutionalPin) {
        this.institutionalToken = institutionalToken;
        this.institutionalPin = institutionalPin;
        log.info("InternalSecurityService initialized under 152-FZ perimeter isolation requirements.");
    }

    /**
     * Validates if the supplied credential matches institutional token or PIN.
     */
    public boolean verifyCredential(String credential) {
        if (credential == null || credential.isBlank()) {
            return false;
        }
        String trimmed = credential.trim();
        return trimmed.equals(institutionalToken) || trimmed.equals(institutionalPin);
    }

    /**
     * Validates explicit institutional token.
     */
    public boolean validateToken(String token) {
        if (token == null || token.isBlank()) {
            return false;
        }
        String trimmed = token.trim();
        return trimmed.equals(institutionalToken) || validateSession(trimmed);
    }

    /**
     * Validates explicit institutional PIN.
     */
    public boolean validatePin(String pin) {
        if (pin == null || pin.isBlank()) {
            return false;
        }
        return pin.trim().equals(institutionalPin);
    }

    /**
     * Authenticates an institutional token or PIN and generates a secure session token.
     *
     * @param credential institutional token or PIN
     * @return session token on success, or null on failed verification
     */
    public String authenticate(String credential) {
        if (!verifyCredential(credential)) {
            log.warn("Institutional authentication attempt rejected (unauthorized).");
            return null;
        }

        byte[] randomBytes = new byte[32];
        secureRandom.nextBytes(randomBytes);
        String sessionToken = "crie_sess_" + Base64.getUrlEncoder().withoutPadding().encodeToString(randomBytes);

        long expiresAt = Instant.now().toEpochMilli() + (DEFAULT_SESSION_TTL_SECONDS * 1000L);
        activeSessions.put(sessionToken, expiresAt);
        log.info("Institutional session token successfully issued.");
        return sessionToken;
    }

    /**
     * Alias for authenticate to issue session tokens.
     */
    public String issueSessionToken(String credential) {
        return authenticate(credential);
    }

    /**
     * Validates whether an issued session token is active and unexpired.
     */
    public boolean validateSession(String sessionToken) {
        if (sessionToken == null || sessionToken.isBlank()) {
            return false;
        }

        Long expiresAt = activeSessions.get(sessionToken);
        if (expiresAt == null) {
            return false;
        }

        if (Instant.now().toEpochMilli() > expiresAt) {
            activeSessions.remove(sessionToken);
            log.debug("Session token expired.");
            return false;
        }

        return true;
    }

    /**
     * Alias for validateSession.
     */
    public boolean isSessionValid(String sessionToken) {
        return validateSession(sessionToken);
    }

    /**
     * Checks whether an Authorization header, Bearer token, or institutional credential is authorized.
     */
    public boolean isAuthorized(String header) {
        if (header == null || header.isBlank()) {
            return false;
        }

        String token = header.trim();
        if (token.startsWith("Bearer ")) {
            token = token.substring(7).trim();
        }

        return validateSession(token) || verifyCredential(token);
    }

    /**
     * Alias for isAuthorized.
     */
    public boolean isRequestAuthenticated(String header) {
        return isAuthorized(header);
    }

    /**
     * Alias for isAuthorized.
     */
    public boolean hasAccess(String token) {
        return isAuthorized(token);
    }

    /**
     * Invalidates an existing session token.
     */
    public void invalidateSession(String sessionToken) {
        if (sessionToken != null) {
            activeSessions.remove(sessionToken);
        }
    }

    /**
     * Cleans up expired sessions from memory.
     */
    public void purgeExpiredSessions() {
        long now = Instant.now().toEpochMilli();
        activeSessions.entrySet().removeIf(entry -> entry.getValue() < now);
    }

    /**
     * Returns count of currently active sessions.
     */
    public int getActiveSessionCount() {
        purgeExpiredSessions();
        return activeSessions.size();
    }
}
