package com.eneik.crie.services.security;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.security.SecureRandom;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Perimeter security service enforcing mandatory institutional token or PIN authentication
 * in compliance with 152-FZ perimeter isolation requirements.
 */
@Service
public class InternalSecurityService {

    private static final Logger log = LoggerFactory.getLogger(InternalSecurityService.class);
    private static final Duration DEFAULT_SESSION_DURATION = Duration.ofHours(8);
    private static final SecureRandom SECURE_RANDOM = new SecureRandom();

    private final String configuredInstitutionalPin;
    private final String configuredInstitutionalToken;
    private final Map<String, SessionRecord> activeSessions = new ConcurrentHashMap<>();

    public InternalSecurityService(
            @Value("${crie.security.institutional.pin:152000}") String configuredInstitutionalPin,
            @Value("${crie.security.institutional.token:152-FZ-INSTITUTIONAL-PERIMETER-KEY}") String configuredInstitutionalToken) {
        this.configuredInstitutionalPin = configuredInstitutionalPin.trim();
        this.configuredInstitutionalToken = configuredInstitutionalToken.trim();
    }

    public record AuthResult(boolean authenticated, String sessionToken, Instant expiresAt, String errorMessage) {
        public static AuthResult success(String sessionToken, Instant expiresAt) {
            return new AuthResult(true, sessionToken, expiresAt, null);
        }

        public static AuthResult failure(String errorMessage) {
            return new AuthResult(false, null, null, errorMessage);
        }
    }

    public record SessionRecord(String sessionToken, Instant createdAt, Instant expiresAt) {
        public boolean isExpired() {
            return Instant.now().isAfter(expiresAt);
        }
    }

    /**
     * Authenticates an incoming institutional credential (token or PIN).
     * Returns an AuthResult containing the newly issued session token if valid.
     */
    public AuthResult authenticateInstitutionalCredential(String credential) {
        if (credential == null || credential.isBlank()) {
            log.warn("Institutional authentication rejected: Empty credential provided");
            return AuthResult.failure("Institutional credential is required");
        }

        String sanitized = credential.trim();
        boolean isPinMatch = Objects.equals(this.configuredInstitutionalPin, sanitized);
        boolean isTokenMatch = Objects.equals(this.configuredInstitutionalToken, sanitized);

        if (!isPinMatch && !isTokenMatch) {
            log.warn("Institutional authentication failed: Invalid token/PIN");
            return AuthResult.failure("Invalid institutional token or PIN");
        }

        String sessionToken = generateSessionToken();
        Instant expiresAt = Instant.now().plus(DEFAULT_SESSION_DURATION);
        activeSessions.put(sessionToken, new SessionRecord(sessionToken, Instant.now(), expiresAt));

        log.info("Institutional access granted under 152-FZ perimeter guard; session token issued");
        return AuthResult.success(sessionToken, expiresAt);
    }

    /**
     * Validates an active session token.
     */
    public boolean isSessionValid(String sessionToken) {
        if (sessionToken == null || sessionToken.isBlank()) {
            return false;
        }

        SessionRecord record = activeSessions.get(sessionToken.trim());
        if (record == null) {
            return false;
        }

        if (record.isExpired()) {
            activeSessions.remove(sessionToken.trim());
            return false;
        }

        return true;
    }

    /**
     * Validates authorization from HTTP Authorization header (e.g. Bearer token).
     */
    public boolean isAuthorized(String authorizationHeader) {
        Optional<String> token = extractBearerToken(authorizationHeader);
        return token.map(this::isSessionValid).orElse(false);
    }

    /**
     * Extracts bearer token from Authorization header value.
     */
    public Optional<String> extractBearerToken(String authorizationHeader) {
        if (authorizationHeader == null || authorizationHeader.isBlank()) {
            return Optional.empty();
        }
        String trimmed = authorizationHeader.trim();
        if (trimmed.regionMatches(true, 0, "Bearer ", 0, 7)) {
            return Optional.of(trimmed.substring(7).trim()).filter(s -> !s.isEmpty());
        }
        return Optional.of(trimmed);
    }

    /**
     * Revokes an active session token upon logout.
     */
    public boolean revokeSession(String sessionToken) {
        if (sessionToken == null || sessionToken.isBlank()) {
            return false;
        }
        return activeSessions.remove(sessionToken.trim()) != null;
    }

    /**
     * Cleans up expired sessions.
     */
    public void pruneExpiredSessions() {
        activeSessions.entrySet().removeIf(entry -> entry.getValue().isExpired());
    }

    public int getActiveSessionCount() {
        pruneExpiredSessions();
        return activeSessions.size();
    }

    private String generateSessionToken() {
        byte[] randomBytes = new byte[32];
        SECURE_RANDOM.nextBytes(randomBytes);
        return "crie-sec-" + Base64.getUrlEncoder().withoutPadding().encodeToString(randomBytes);
    }
}
