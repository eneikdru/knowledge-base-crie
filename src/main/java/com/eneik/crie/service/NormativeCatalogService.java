package com.eneik.crie.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.io.File;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Service
public class NormativeCatalogService {

    private static final Logger log = LoggerFactory.getLogger(NormativeCatalogService.class);

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final List<Map<String, Object>> documents = new ArrayList<>();
    private final Map<String, Integer> categoryCounts = new ConcurrentHashMap<>();

    @PostConstruct
    public void init() {
        loadCatalog();
        loadBenchmarkDocuments();
        log.info("NormativeCatalogService initialized with {} indexed documents across {} categories.",
                documents.size(), categoryCounts.size());
    }

    private void loadCatalog() {
        File file = new File("data/normative/corpus_catalog.json");
        if (!file.exists()) {
            file = new File("/opt/client-runtimes/knowledge-base-crie/data/normative/corpus_catalog.json");
        }
        if (!file.exists()) {
            log.warn("corpus_catalog.json not found at {}", file.getAbsolutePath());
            return;
        }

        try {
            JsonNode root = objectMapper.readTree(file);
            JsonNode categoriesNode = root.get("categories");
            if (categoriesNode != null && categoriesNode.isArray()) {
                int idCounter = 1;
                for (JsonNode catNode : categoriesNode) {
                    String categoryName = catNode.path("category").asText("Общие документы");
                    JsonNode filesNode = catNode.get("files");
                    if (filesNode != null && filesNode.isArray()) {
                        for (JsonNode f : filesNode) {
                            String fileName = f.path("file_name").asText();
                            String relPath = f.path("relative_path").asText();
                            String ext = f.path("extension").asText(".docx");
                            long size = f.path("size_bytes").asLong(0);

                            Map<String, Object> doc = new HashMap<>();
                            doc.put("id", "DOC-" + String.format("%04d", idCounter++));
                            doc.put("title", fileName.replaceAll("\\.[^.]+$", ""));
                            doc.put("file_name", fileName);
                            doc.put("relative_path", relPath);
                            doc.put("category", categoryName);
                            doc.put("extension", ext);
                            doc.put("size_bytes", size);
                            doc.put("type", determineDocType(fileName, categoryName));
                            doc.put("annotation", "Официальный регламентирующий материал ФБУН ЦНИИ Эпидемиологии Роспотребнадзора (" + categoryName + ").");
                            doc.put("download_url", "/api/catalog/download/" + fileName);

                            documents.add(doc);
                            categoryCounts.merge(categoryName, 1, Integer::sum);
                        }
                    }
                }
            }
        } catch (Exception e) {
            log.error("Failed to load corpus_catalog.json: {}", e.getMessage(), e);
        }
    }

    private void loadBenchmarkDocuments() {
        File genDir = new File("generated_documents");
        if (!genDir.exists()) {
            genDir = new File("/opt/client-runtimes/knowledge-base-crie/generated_documents");
        }
        if (genDir.exists() && genDir.isDirectory()) {
            File[] files = genDir.listFiles((dir, name) -> name.endsWith(".docx"));
            if (files != null) {
                int counter = 10000;
                for (File f : files) {
                    String name = f.getName();
                    Map<String, Object> doc = new HashMap<>();
                    doc.put("id", "BENCH-" + (++counter));
                    doc.put("title", formatBenchmarkTitle(name));
                    doc.put("file_name", name);
                    doc.put("relative_path", "generated_documents/" + name);
                    doc.put("category", "00 Официальные документы института (ГОСТ Р 7.0.97-2016)");
                    doc.put("extension", ".docx");
                    doc.put("size_bytes", f.length());
                    doc.put("type", "Официальный акт / УМС");
                    doc.put("annotation", "Утвержденный документ институционального пакета ФБУН ЦНИИЭ на 2026–2027 учебный год.");
                    doc.put("download_url", "/api/download/" + name);
                    doc.put("docx_url", "/api/download/" + name);
                    documents.add(0, doc); // add at top
                    categoryCounts.merge((String) doc.get("category"), 1, Integer::sum);
                }
            }
        }
    }

    private String determineDocType(String fileName, String category) {
        String lower = (fileName + " " + category).toLowerCase();
        if (lower.contains("протокол")) return "Протокол";
        if (lower.contains("приказ")) return "Приказ";
        if (lower.contains("положение")) return "Положение";
        if (lower.contains("порядок")) return "Порядок";
        if (lower.contains("план") || lower.contains("учебн")) return "Учебный план";
        if (lower.contains("расписан")) return "Расписание";
        if (lower.contains("рпд") || lower.contains("рабочая программа")) return "РПД";
        if (lower.contains("фос")) return "ФОС";
        if (lower.contains("всоко")) return "ВСОКО";
        return "Нормативный акт";
    }

    private String formatBenchmarkTitle(String name) {
        String clean = name.replace(".docx", "").replace("_", " ");
        if (clean.startsWith("01 ")) return "Протокол Учебно-методического совета № 9/26 от 09.09.2026";
        if (clean.startsWith("02 ")) return "Протокол Учебно-методического совета № 10/26 от 14.10.2026";
        if (clean.startsWith("03 ")) return "Приказ о формировании и утверждении составов комиссий на 2027 год";
        if (clean.startsWith("04 ")) return "Расписание зимней экзаменационной сессии на 2026–2027 уч. год (25.01–25.02.2027)";
        if (clean.startsWith("05 ")) return "Сводные учебные планы ординатуры на 2026–2027 уч. год (120 з.е. / 4 320 ч.)";
        if (clean.startsWith("06 ")) return "Справка о кадровом обеспечении и учебной нагрузке ППС (остепененность 88.2%)";
        return clean;
    }

    public Map<String, Object> search(String query, String category, int limit, int offset) {
        String q = (query != null) ? query.trim().toLowerCase() : "";
        List<Map<String, Object>> filtered = documents.stream()
                .filter(doc -> {
                    if (category != null && !category.isBlank() && !"all".equalsIgnoreCase(category)) {
                        String docCat = (String) doc.get("category");
                        if (docCat == null || !docCat.equalsIgnoreCase(category)) {
                            return false;
                        }
                    }
                    if (q.isEmpty()) {
                        return true;
                    }
                    String title = ((String) doc.getOrDefault("title", "")).toLowerCase();
                    String fileName = ((String) doc.getOrDefault("file_name", "")).toLowerCase();
                    String docCat = ((String) doc.getOrDefault("category", "")).toLowerCase();
                    String docType = ((String) doc.getOrDefault("type", "")).toLowerCase();
                    return title.contains(q) || fileName.contains(q) || docCat.contains(q) || docType.contains(q);
                })
                .collect(Collectors.toList());

        int total = filtered.size();
        int from = Math.min(Math.max(offset, 0), total);
        int to = Math.min(from + Math.max(limit, 1), total);
        List<Map<String, Object>> paged = filtered.subList(from, to);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("total", total);
        result.put("total_hits", total);
        result.put("limit", limit);
        result.put("offset", offset);
        result.put("items", paged);
        result.put("results", paged);
        result.put("categories", categoryCounts);
        return result;
    }

    public List<Map<String, Object>> findTopGroundedSnippets(String query, int maxResults) {
        if (query == null || query.isBlank()) {
            return Collections.emptyList();
        }
        String[] tokens = query.toLowerCase().split("\\s+");
        return documents.stream()
                .filter(doc -> {
                    String title = ((String) doc.getOrDefault("title", "")).toLowerCase();
                    for (String token : tokens) {
                        if (token.length() > 3 && title.contains(token)) {
                            return true;
                        }
                    }
                    return false;
                })
                .limit(maxResults)
                .collect(Collectors.toList());
    }

    public Map<String, Integer> getCategoryCounts() {
        return Collections.unmodifiableMap(categoryCounts);
    }

    public int getTotalCount() {
        return documents.size();
    }
}
