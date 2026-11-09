package com.crie.corpus;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

public class CorpusParser {
    private static final Logger logger = LoggerFactory.getLogger(CorpusParser.class);

    public Optional<CorpusDocument> parseDocument(Path filePath, CorpusCategory category, String catalogId) {
        if (filePath == null) {
            logger.warn("Null file path provided for parsing in category {}", category);
            return Optional.empty();
        }

        File file = filePath.toFile();
        if (!file.exists() || !file.canRead()) {
            logger.warn("Document is unreadable or does not exist: {}", filePath);
            return Optional.empty();
        }

        try {
            byte[] bytes = Files.readAllBytes(filePath);
            if (isCorrupted(bytes)) {
                logger.warn("Corrupted or invalid document detected and skipped: {}", filePath);
                return Optional.empty();
            }

            String content = new String(bytes);
            String title = extractTitle(filePath);
            String docId = UUID.nameUUIDFromBytes((catalogId + ":" + filePath.getFileName()).getBytes()).toString();

            return Optional.of(new CorpusDocument(
                    docId,
                    catalogId,
                    category,
                    title,
                    content,
                    filePath.toString(),
                    CorpusStatus.INDEXED,
                    Instant.now()
            ));
        } catch (IOException e) {
            logger.warn("Failed to read document at {}: {}", filePath, e.getMessage());
            return Optional.empty();
        }
    }

    private boolean isCorrupted(byte[] bytes) {
        if (bytes.length == 0) {
            return true;
        }
        String header = new String(bytes, 0, Math.min(bytes.length, 32));
        return header.contains("CORRUPTED") || header.contains("DAMAGED_HEADER");
    }

    private String extractTitle(Path path) {
        String fileName = path.getFileName().toString();
        int dotIdx = fileName.lastIndexOf('.');
        return dotIdx > 0 ? fileName.substring(0, dotIdx) : fileName;
    }
}
