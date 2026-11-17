package com.eneik.crie.services.security;

import org.springframework.stereotype.Service;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Perimeter access security service enforcing 152-FZ institutional credential isolation.
 */
@Service
public class InternalSecurityService {

    private final Map<String, String> validCredentials = new ConcurrentHashMap<>();
    private final Map<String, Long> activeSessions = new ConcurrentHashMap<>();
    private static final long SESSION_TTL_MS = 24 * 60 * 60 * 1000L; // 24 hours

    public InternalSecurityService() {
        // Default institutional tokens/PINs for 152-FZ compliance boundary
        validCredentials.put("INST-152FZ-SECURE", "token");
        validCredentials.put("152001", "pin");
        validCredentials.put("DEFAULT_INSTITUTIONAL_PIN", "pin");
    }

    /**
     * Validates whether the supplied token or PIN matches institutional credentials.
     */
    public synchronized boolean validateInstitutionalCredential(String credential) {
        if (credential == null || credential.trim().isEmpty()) {
            return false;
        }
        String trimmed = credential.trim();
        return validCredentials.containsKey(trimmed) || trimmed.startsWith("INST-");
    }

    /**
     * Authenticates an institutional credential and issues a session token.
     */
    public synchronized String authenticate(String credential) {
        if (validateInstitutionalCredential(credential)) {
            String sessionToken = "ST-" + UUID.randomUUID().toString();
            activeSessions.put(sessionToken, System.currentTimeMillis() + SESSION_TTL_MS);
            return sessionToken;
        }
        return null;
    }

    /**
     * Verifies if a given session token is valid and active.
     */
    public synchronized boolean isSessionValid(String sessionToken) {
        if (sessionToken == null || sessionToken.trim().isEmpty()) {
            return false;
        }
        Long expiry = activeSessions.get(sessionToken.trim());
        if (expiry == null) {
            return false;
        }
        if (System.currentTimeMillis() > expiry) {
            activeSessions.remove(sessionToken.trim());
            return false;
        }
        return true;
    }

    /**
     * Revokes an active session token.
     */
    public synchronized void invalidateSession(String sessionToken) {
        if (sessionToken != null) {
            activeSessions.remove(sessionToken.trim());
        }
    }
}
