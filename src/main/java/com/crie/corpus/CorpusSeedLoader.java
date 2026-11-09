package com.crie.corpus;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.*;
import java.util.stream.Stream;

public class CorpusSeedLoader {
    private static final Logger logger = LoggerFactory.getLogger(CorpusSeedLoader.class);

    private final CorpusParser parser;
    private final Map<String, CorpusCatalogEntry> catalog = new LinkedHashMap<>();
    private final List<CorpusDocument> documents = new ArrayList<>();

    public CorpusSeedLoader(CorpusParser parser) {
        this.parser = parser != null ? parser : new CorpusParser();
    }

    public CorpusSeedLoader() {
        this(new CorpusParser());
    }

    public IngestionResult loadCorpus(Path templateDirectory) {
        int educationalProgramsCount = 0;
        int giaTasksCount = 0;
        int practiceRegulationsCount = 0;
        int skippedCorruptedCount = 0;

        if (templateDirectory == null || !Files.exists(templateDirectory)) {
            logger.warn("Corpus template directory does not exist or is null: {}", templateDirectory);
            return new IngestionResult(0, 0, 0, 0, catalog.values(), documents);
        }

        for (CorpusCategory category : CorpusCategory.values()) {
            Path categoryDir = templateDirectory.resolve(getDirectoryName(category));
            if (!Files.exists(categoryDir)) {
                continue;
            }

            try (Stream<Path> stream = Files.walk(categoryDir, 1)) {
                List<Path> files = stream.filter(Files::isRegularFile).toList();
                for (Path file : files) {
                    String code = category.name().toLowerCase() + "-" + file.getFileName().toString();
                    String catalogId = UUID.nameUUIDFromBytes(code.getBytes()).toString();

                    Optional<CorpusDocument> parsedDoc = parser.parseDocument(file, category, catalogId);
                    if (parsedDoc.isPresent()) {
                        CorpusDocument doc = parsedDoc.get();
                        documents.add(doc);

                        CorpusCatalogEntry entry = new CorpusCatalogEntry(
                                catalogId,
                                category,
                                code,
                                doc.getTitle(),
                                file.toString(),
                                CorpusStatus.INDEXED,
                                Instant.now()
                        );
                        catalog.put(catalogId, entry);

                        switch (category) {
                            case EDUCATIONAL_PROGRAM -> educationalProgramsCount++;
                            case GIA_TASK -> giaTasksCount++;
                            case PRACTICE_REGULATION -> practiceRegulationsCount++;
                        }
                    } else {
                        skippedCorruptedCount++;
                        logger.warn("Skipping corrupt or unreadable file without failing ingestion: {}", file);
                    }
                }
            } catch (IOException e) {
                logger.warn("Error traversing directory {}: {}", categoryDir, e.getMessage());
            }
        }

        return new IngestionResult(
                educationalProgramsCount,
                giaTasksCount,
                practiceRegulationsCount,
                skippedCorruptedCount,
                Collections.unmodifiableCollection(catalog.values()),
                Collections.unmodifiableList(documents)
        );
    }

    private String getDirectoryName(CorpusCategory category) {
        return switch (category) {
            case EDUCATIONAL_PROGRAM -> "educational_programs";
            case GIA_TASK -> "gia_tasks";
            case PRACTICE_REGULATION -> "practice_regulations";
        };
    }

    public record IngestionResult(
            int educationalProgramsIndexed,
            int giaTasksIndexed,
            int practiceRegulationsIndexed,
            int skippedCorruptedCount,
            Collection<CorpusCatalogEntry> indexedEntries,
            List<CorpusDocument> indexedDocuments
    ) {
        public int totalIndexed() {
            return educationalProgramsIndexed + giaTasksIndexed + practiceRegulationsIndexed;
        }
    }
}
