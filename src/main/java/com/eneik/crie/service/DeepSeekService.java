package com.eneik.crie.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.*;

@Service
public class DeepSeekService {

    private static final Logger log = LoggerFactory.getLogger(DeepSeekService.class);

    @Value("${deepseek.api.key:}")
    private String apiKey;

    @Value("${deepseek.api.url:https://api.deepseek.com/chat/completions}")
    private String apiUrl;

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(15))
            .build();

    private final NormativeCatalogService catalogService;

    public DeepSeekService(NormativeCatalogService catalogService) {
        this.catalogService = catalogService;
    }

    public Map<String, Object> askDeepSeek(String userQuery) {
        long startTime = System.currentTimeMillis();
        String query = (userQuery != null) ? userQuery.trim() : "";
        if (query.isEmpty()) {
            Map<String, Object> err = new HashMap<>();
            err.put("error", "Запрос не может быть пустым");
            return err;
        }

        // Fetch grounded citations
        List<Map<String, Object>> citationsDocs = catalogService.findTopGroundedSnippets(query, 5);
        StringBuilder contextBuilder = new StringBuilder();
        List<Map<String, String>> citations = new ArrayList<>();

        for (Map<String, Object> doc : citationsDocs) {
            String title = (String) doc.get("title");
            String path = (String) doc.get("relative_path");
            String cat = (String) doc.get("category");
            contextBuilder.append("- Документ: «").append(title).append("» (Категория: ").append(cat).append(")\n");

            Map<String, String> cit = new HashMap<>();
            cit.put("title", title);
            cit.put("path", path);
            cit.put("category", cat);
            citations.add(cit);
        }

        String systemPrompt = """
                Вы — ведущий нормативно-правовой и учебно-методический консультант ФБУН ЦНИИ Эпидемиологии Роспотребнадзора.
                Вы отвечаете на вопросы обучающихся (ординаторов, аспирантов) и профессорско-преподавательского состава института.
                
                ПРИНЦИПЫ ОТВЕТА:
                1. Отвечайте строго по существу, профессионально, авторитетно и детально на русском языке.
                2. Опирайтесь на Федеральный закон № 273-ФЗ «Об образовании в РФ», нормативные акты Роспотребнадзора, приказы Минобрнауки РФ, стандарты ГОСТ Р 7.0.97-2016 и локальные акты ЦНИИЭ.
                3. Если вопрос касается ординатуры — учитывайте специальности: 32.08.12 «Эпидемиология», 31.08.35 «Инфекционные болезни», 31.08.19 «Педиатрия» (объем 120 з.е. / 4320 ч.).
                4. Если вопрос касается комиссий, расписания, сессии или аттестации — приводите конкретные регламенты, сроки (сессия 25.01–25.02) и требования к остепененности преподавателей (не менее 70%).
                5. Никогда не используйте заглушки, смайлики и отговорки. Давайте исчерпывающий содержательный ответ.
                """;

        String userPromptWithContext = query;
        if (contextBuilder.length() > 0) {
            userPromptWithContext = "РЕГЛАМЕНТИРУЮЩИЙ КОНТЕКСТ ИНСТИТУТА:\n" + contextBuilder + "\n\nВОПРОС ПОЛЬЗОВАТЕЛЯ:\n" + query;
        }

        String answerText = "";
        try {
            Map<String, Object> reqBody = new HashMap<>();
            reqBody.put("model", "deepseek-chat");
            reqBody.put("temperature", 0.3);
            reqBody.put("max_tokens", 2048);

            List<Map<String, String>> messages = new ArrayList<>();
            messages.add(Map.of("role", "system", "content", systemPrompt));
            messages.add(Map.of("role", "user", "content", userPromptWithContext));
            reqBody.put("messages", messages);

            String jsonPayload = objectMapper.writeValueAsString(reqBody);

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(apiUrl))
                    .header("Content-Type", "application/json")
                    .header("Authorization", "Bearer " + apiKey)
                    .timeout(Duration.ofSeconds(60))
                    .POST(HttpRequest.BodyPublishers.ofString(jsonPayload))
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == 200) {
                JsonNode root = objectMapper.readTree(response.body());
                JsonNode choice = root.path("choices").path(0).path("message").path("content");
                answerText = choice.asText();
            } else {
                log.error("DeepSeek API call failed: HTTP {} body: {}", response.statusCode(), response.body());
                answerText = "Ошибка связи с моделью DeepSeek (HTTP " + response.statusCode() + "). Проверьте сетевое подключение.";
            }
        } catch (Exception e) {
            log.error("Exception calling DeepSeek: {}", e.getMessage(), e);
            answerText = "Ошибка выполнения запроса к AI-консультанту: " + e.getMessage();
        }

        long elapsedMs = System.currentTimeMillis() - startTime;
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("id", "chat-" + System.currentTimeMillis());
        result.put("query", query);
        result.put("response", answerText);
        result.put("answer", answerText);
        result.put("text", answerText);
        result.put("citations", citations);
        result.put("elapsed_ms", elapsedMs);
        result.put("total_hits", citationsDocs.size());
        return result;
    }
}
