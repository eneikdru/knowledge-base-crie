package com.eneik.crie.controller;

import com.eneik.crie.service.DeepSeekService;
import com.eneik.crie.service.NormativeCatalogService;
import com.eneik.telemetry.services.InternalService;
import com.eneik.telemetry.services.security.InternalSecurityService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.io.File;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.*;

@RestController
@CrossOrigin(origins = "*", allowedHeaders = "*")
public class CrieApiController {

    private static final Logger log = LoggerFactory.getLogger(CrieApiController.class);

    private final DeepSeekService deepSeekService;
    private final NormativeCatalogService catalogService;
    private final InternalSecurityService securityService;
    private final InternalService internalService;

    public CrieApiController(DeepSeekService deepSeekService,
                             NormativeCatalogService catalogService,
                             InternalSecurityService securityService,
                             InternalService internalService) {
        this.deepSeekService = deepSeekService;
        this.catalogService = catalogService;
        this.securityService = securityService;
        this.internalService = internalService;
    }

    @GetMapping({"/health", "/api/health", "/crie/health", "/crie/api/health"})
    public Map<String, Object> health() {
        Map<String, Object> h = new LinkedHashMap<>();
        h.put("status", "UP");
        h.put("service", "FBUN CRIE AI Assistant & Knowledge Base (Spring Boot 3 / Java 21)");
        h.put("indexed_documents", catalogService.getTotalCount());
        h.put("timestamp", System.currentTimeMillis());
        return h;
    }

    @PostMapping({"/api/auth/login", "/crie/api/auth/login", "/api/auth/verify", "/crie/api/auth/verify"})
    public ResponseEntity<Map<String, Object>> login(@RequestBody Map<String, String> payload) {
        String pinOrToken = payload.get("pin");
        if (pinOrToken == null) {
            pinOrToken = payload.get("token");
        }
        if (pinOrToken == null) {
            pinOrToken = payload.get("credential");
        }

        Optional<String> tokenOpt = securityService.authenticate(pinOrToken);
        if (tokenOpt.isPresent()) {
            Map<String, Object> resp = new HashMap<>();
            resp.put("success", true);
            resp.put("token", tokenOpt.get());
            resp.put("role", "INSTITUTIONAL_OFFICER");
            resp.put("message", "Авторизация по 152-ФЗ успешно пройдена.");
            return ResponseEntity.ok(resp);
        } else {
            Map<String, Object> resp = new HashMap<>();
            resp.put("success", false);
            resp.put("error", "Неверный служебный PIN-код или институциональный токен.");
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(resp);
        }
    }

    @PostMapping({"/api/chat", "/crie/api/chat", "/api/rag/consultant", "/crie/api/rag/consultant"})
    public Map<String, Object> chat(@RequestBody Map<String, Object> payload) {
        String query = (String) payload.get("query");
        if (query == null) {
            query = (String) payload.get("message");
        }
        if (query == null) {
            query = (String) payload.get("question");
        }

        long t0 = System.currentTimeMillis();
        Map<String, Object> result = deepSeekService.askDeepSeek(query);
        long dur = System.currentTimeMillis() - t0;
        try {
            internalService.recordChatQuery(query != null ? query : "", dur, 2, true);
        } catch (Exception ignored) {}
        return result;
    }

    @GetMapping({"/api/catalog/search", "/crie/api/catalog/search", "/api/search", "/crie/api/search"})
    public Map<String, Object> search(
            @RequestParam(required = false, defaultValue = "") String q,
            @RequestParam(required = false) String query,
            @RequestParam(required = false) String category,
            @RequestParam(required = false, defaultValue = "50") int limit,
            @RequestParam(required = false, defaultValue = "0") int offset) {
        String effectiveQ = (query != null && !query.isBlank()) ? query : q;
        Map<String, Object> res = catalogService.search(effectiveQ, category, limit, offset);
        try {
            internalService.recordNormativeSearch(effectiveQ, (Integer) res.getOrDefault("total", 0), true);
        } catch (Exception ignored) {}
        return res;
    }

    @GetMapping({"/api/catalog/download/{filename}", "/crie/api/catalog/download/{filename}", "/api/download/{filename}", "/crie/api/download/{filename}"})
    public ResponseEntity<Resource> downloadDocument(@PathVariable String filename) {
        File genDir = new File("generated_documents");
        if (!genDir.exists()) {
            genDir = new File("/opt/client-runtimes/knowledge-base-crie/generated_documents");
        }

        File target = new File(genDir, filename);
        if (!target.exists()) {
            target = new File(filename);
        }

        if (!target.exists() || !target.isFile()) {
            log.warn("File requested for download not found: {}", filename);
            return ResponseEntity.notFound().build();
        }

        try {
            String encodedName = URLEncoder.encode(target.getName(), StandardCharsets.UTF_8).replace("+", "%20");
            HttpHeaders headers = new HttpHeaders();
            headers.add(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + target.getName() + "\"; filename*=UTF-8''" + encodedName);
            headers.add("X-Content-Type-Options", "nosniff");
            headers.setContentType(MediaType.parseMediaType("application/vnd.openxmlformats-officedocument.wordprocessingml.document"));

            try {
                internalService.recordDocumentDownload(filename, "docx", true);
            } catch (Exception ignored) {}

            return ResponseEntity.ok()
                    .headers(headers)
                    .contentLength(target.length())
                    .body(new FileSystemResource(target));
        } catch (Exception e) {
            log.error("Error serving download for {}: {}", filename, e.getMessage());
            return ResponseEntity.internalServerError().build();
        }
    }

    @GetMapping({"/api/download/archive", "/crie/api/download/archive", "/api/catalog/download/archive", "/crie/api/catalog/download/archive", "/api/download/suite-archive", "/crie/api/download/suite-archive"})
    public ResponseEntity<Resource> downloadSuiteArchive() {
        File genDir = new File("generated_documents");
        if (!genDir.exists()) {
            genDir = new File("/opt/client-runtimes/knowledge-base-crie/generated_documents");
        }

        File zipFile = new File(genDir, "Пакет_Документов_ЦНИИ_Эпидемиологии_2026_2027.zip");
        if (!zipFile.exists()) {
            zipFile = new File("/opt/client-runtimes/knowledge-base-crie/generated_documents/Пакет_Документов_ЦНИИ_Эпидемиологии_2026_2027.zip");
        }

        if (!zipFile.exists()) {
            return ResponseEntity.notFound().build();
        }

        try {
            String encodedName = URLEncoder.encode(zipFile.getName(), StandardCharsets.UTF_8).replace("+", "%20");
            HttpHeaders headers = new HttpHeaders();
            headers.add(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + zipFile.getName() + "\"; filename*=UTF-8''" + encodedName);
            headers.setContentType(MediaType.parseMediaType("application/zip"));

            return ResponseEntity.ok()
                    .headers(headers)
                    .contentLength(zipFile.length())
                    .body(new FileSystemResource(zipFile));
        } catch (Exception e) {
            log.error("Error serving archive download: {}", e.getMessage());
            return ResponseEntity.internalServerError().build();
        }
    }

    @PostMapping({"/api/workload/calculate", "/crie/api/workload/calculate"})
    public Map<String, Object> calculateWorkload(@RequestBody Map<String, Object> payload) {
        int studentsCount = 45;
        if (payload.containsKey("students_count")) {
            studentsCount = ((Number) payload.get("students_count")).intValue();
        }
        int facultyCount = 17;
        if (payload.containsKey("faculty_count")) {
            facultyCount = ((Number) payload.get("faculty_count")).intValue();
        }

        double totalCurriculumHours = 4320.0;
        double totalPlannedHours = 4450.0;
        double averageLoadPerTeacher = totalPlannedHours / facultyCount;
        double degreeHoldingPercentage = 88.2;

        Map<String, Object> res = new LinkedHashMap<>();
        res.put("total_curriculum_hours", totalCurriculumHours);
        res.put("total_planned_hours", totalPlannedHours);
        res.put("faculty_headcount", facultyCount);
        res.put("students_count", studentsCount);
        res.put("degree_holding_percentage", degreeHoldingPercentage);
        res.put("compliance_status", degreeHoldingPercentage >= 70.0 ? "СООТВЕТСТВУЕТ_ФГОС" : "НЕ_СООТВЕТСТВУЕТ");
        res.put("average_load_per_faculty_member_hours", Math.round(averageLoadPerTeacher * 10.0) / 10.0);
        res.put("department_profile", "Кафедры эпидемиологии, инфекционных болезней и педиатрии");
        return res;
    }
}
