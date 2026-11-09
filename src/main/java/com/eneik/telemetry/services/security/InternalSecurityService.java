package com.eneik.telemetry.services.security;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.Base64;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Service providing institutional token and service PIN authentication,
 * session issuance, and token validation adhering to 152-ФЗ isolation invariants.
 */
public class InternalSecurityService {

    private final String expectedInstitutionalToken;
    private final String expectedServicePin;
    private final long sessionTtlSeconds;
    private final SecureRandom secureRandom;
    private final Map<String, Instant> activeSessions;

    public InternalSecurityService(String expectedInstitutionalToken, String expectedServicePin, long sessionTtlSeconds) {
        this(expectedInstitutionalToken, expectedServicePin, sessionTtlSeconds, new SecureRandom());
    }

    public InternalSecurityService(String expectedInstitutionalToken, String expectedServicePin, long sessionTtlSeconds, SecureRandom secureRandom) {
        this.expectedInstitutionalToken = expectedInstitutionalToken != null ? expectedInstitutionalToken : "";
        this.expectedServicePin = expectedServicePin != null ? expectedServicePin : "";
        this.sessionTtlSeconds = sessionTtlSeconds > 0 ? sessionTtlSeconds : 3600L;
        this.secureRandom = secureRandom != null ? secureRandom : new SecureRandom();
        this.activeSessions = new ConcurrentHashMap<>();
    }

    /**
     * Validates an institutional token or service PIN and returns a bearer session token if valid.
     *
     * @param credential The institutional token or service PIN provided by client
     * @return Optional containing bearer token upon successful authentication, or empty Optional
     */
    public Optional<String> authenticate(String credential) {
        if (credential == null || credential.isBlank()) {
            return Optional.empty();
        }

        boolean tokenMatch = constantTimeEquals(this.expectedInstitutionalToken, credential);
        boolean pinMatch = constantTimeEquals(this.expectedServicePin, credential);

        if (tokenMatch || pinMatch) {
            String sessionToken = generateSessionToken();
            Instant expiresAt = Instant.now().plusSeconds(sessionTtlSeconds);
            activeSessions.put(sessionToken, expiresAt);
            return Optional.of(sessionToken);
        }

        return Optional.empty();
    }

    /**
     * Validates whether a provided bearer session token or direct institutional token is authorized.
     *
     * @param token Bearer token or institutional token
     * @return true if authorized, false otherwise
     */
    public boolean isAuthorized(String token) {
        if (token == null || token.isBlank()) {
            return false;
        }

        // Support direct authorization via institutional token
        if (constantTimeEquals(this.expectedInstitutionalToken, token)) {
            return true;
        }

        // Validate session token
        Instant expiresAt = activeSessions.get(token);
        if (expiresAt == null) {
            return false;
        }

        if (Instant.now().isAfter(expiresAt)) {
            activeSessions.remove(token);
            return false;
        }

        return true;
    }

    /**
     * Revokes an existing session token.
     *
     * @param sessionToken The token to invalidate
     */
    public void revokeSession(String sessionToken) {
        if (sessionToken != null) {
            activeSessions.remove(sessionToken);
        }
    }

    /**
     * Purges expired sessions from memory.
     */
    public void cleanupExpiredSessions() {
        Instant now = Instant.now();
        activeSessions.entrySet().removeIf(entry -> now.isAfter(entry.getValue()));
    }

    private String generateSessionToken() {
        byte[] randomBytes = new byte[32];
        secureRandom.nextBytes(randomBytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(randomBytes);
    }

    private boolean constantTimeEquals(String expected, String actual) {
        if (expected == null || actual == null) {
            return false;
        }
        byte[] expectedBytes = expected.getBytes(StandardCharsets.UTF_8);
        byte[] actualBytes = actual.getBytes(StandardCharsets.UTF_8);
        return MessageDigest.isEqual(expectedBytes, actualBytes);
    }
}
