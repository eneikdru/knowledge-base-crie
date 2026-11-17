package com.eneik.crie.services.security;

import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Access guard service providing institutional token/PIN validation and session management
 * to enforce perimeter access control in compliance with Federal Law No. 152-FZ.
 */
@Service
public class InternalSecurityService {

    public static final String AUTH_HEADER = "Authorization";
    public static final String BEARER_PREFIX = "Bearer ";
    private static final Duration SESSION_TTL = Duration.ofHours(8);

    // In-memory session store mapping session tokens to expiration timestamps
    private final Map<String, Instant> activeSessions = new ConcurrentHashMap<>();

    // Configured or default institutional tokens / PINs for 152-FZ perimeter compliance
    private final Map<String, String> institutionalCredentials = new ConcurrentHashMap<>();

    public InternalSecurityService() {
        // Default institutional gate credentials (can be overridden/extended at runtime)
        institutionalCredentials.put("INST-CRIE-2026", "ACTIVE");
        institutionalCredentials.put("152-FZ-SECURE", "ACTIVE");
        institutionalCredentials.put("770152", "PIN");
        institutionalCredentials.put("994341", "PIN");
    }

    /**
     * Validates an institutional token or PIN.
     *
     * @param tokenOrPin the institutional credential entered by the user
     * @return true if valid, false otherwise
     */
    public boolean validateInstitutionalToken(String tokenOrPin) {
        if (tokenOrPin == null || tokenOrPin.trim().isEmpty()) {
            return false;
        }
        return institutionalCredentials.containsKey(tokenOrPin.trim());
    }

    /**
     * Authenticates using an institutional token or PIN and issues a session token.
     *
     * @param tokenOrPin the institutional credential
     * @return Optional containing the newly minted session token if valid, empty otherwise
     */
    public Optional<String> authenticate(String tokenOrPin) {
        if (!validateInstitutionalToken(tokenOrPin)) {
            return Optional.empty();
        }
        String sessionToken = UUID.randomUUID().toString().replace("-", "");
        Instant expiresAt = Instant.now().plus(SESSION_TTL);
        activeSessions.put(sessionToken, expiresAt);
        return Optional.of(sessionToken);
    }

    /**
     * Checks whether a session token is active and not expired.
     *
     * @param sessionToken the session token to verify
     * @return true if valid and active, false otherwise
     */
    public boolean isSessionValid(String sessionToken) {
        if (sessionToken == null || sessionToken.trim().isEmpty()) {
            return false;
        }
        Instant expiresAt = activeSessions.get(sessionToken);
        if (expiresAt == null) {
            return false;
        }
        if (Instant.now().isAfter(expiresAt)) {
            activeSessions.remove(sessionToken);
            return false;
        }
        return true;
    }

    /**
     * Extracts the token from an Authorization header and verifies the session.
     *
     * @param authHeader the HTTP Authorization header value
     * @return true if the header contains a valid active session token, false otherwise
     */
    public boolean isAuthorized(String authHeader) {
        if (authHeader == null || !authHeader.startsWith(BEARER_PREFIX)) {
            return false;
        }
        String token = authHeader.substring(BEARER_PREFIX.length()).trim();
        return isSessionValid(token);
    }

    /**
     * Invalidates an existing active session.
     *
     * @param sessionToken the session token to invalidate
     */
    public void invalidateSession(String sessionToken) {
        if (sessionToken != null) {
            activeSessions.remove(sessionToken);
        }
    }

    /**
     * Registers an authorized institutional credential.
     *
     * @param credential token or PIN
     * @param type credential type descriptor
     */
    public void registerCredential(String credential, String type) {
        if (credential != null && !credential.trim().isEmpty()) {
            institutionalCredentials.put(credential.trim(), type != null ? type : "CUSTOM");
        }
    }

    /**
     * Cleans up expired sessions.
     */
    public void purgeExpiredSessions() {
        Instant now = Instant.now();
        activeSessions.entrySet().removeIf(entry -> now.isAfter(entry.getValue()));
    }
}
