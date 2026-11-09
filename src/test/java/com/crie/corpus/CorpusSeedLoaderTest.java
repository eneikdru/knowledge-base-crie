package com.crie.corpus;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;

class CorpusSeedLoaderTest {

    @TempDir
    Path tempDir;

    private CorpusSeedLoader seedLoader;

    @BeforeEach
    void setUp() {
        seedLoader = new CorpusSeedLoader();
    }

    @Test
    @DisplayName("Given normative corpus catalog and template directory, When seed loader executes, Then all educational programs, GIA tasks, and practice regulations are indexed")
    void shouldIndexNormativeCorpusCatalogAcrossAllCategories() throws IOException {
        Path eduDir = tempDir.resolve("educational_programs");
        Path giaDir = tempDir.resolve("gia_tasks");
        Path regDir = tempDir.resolve("practice_regulations");

        Files.createDirectories(eduDir);
        Files.createDirectories(giaDir);
        Files.createDirectories(regDir);

        Files.writeString(eduDir.resolve("program_cardiology_2026.docx"), "Content for Cardiology Educational Program");
        Files.writeString(eduDir.resolve("program_neurology_2026.docx"), "Content for Neurology Educational Program");
        Files.writeString(giaDir.resolve("gia_clinical_cases_task1.pdf"), "Content for GIA Clinical Case Task 1");
        Files.writeString(regDir.resolve("practice_regulation_inpatient.docx"), "Content for Inpatient Practice Regulations");

        CorpusSeedLoader.IngestionResult result = seedLoader.loadCorpus(tempDir);

        assertThat(result.educationalProgramsIndexed()).isEqualTo(2);
        assertThat(result.giaTasksIndexed()).isEqualTo(1);
        assertThat(result.practiceRegulationsIndexed()).isEqualTo(1);
        assertThat(result.totalIndexed()).isEqualTo(4);
        assertThat(result.skippedCorruptedCount()).isEqualTo(0);
        assertThat(result.indexedEntries()).hasSize(4);
        assertThat(result.indexedDocuments()).hasSize(4);

        assertThat(result.indexedDocuments())
                .extracting(CorpusDocument::getCategory)
                .containsExactlyInAnyOrder(
                        CorpusCategory.EDUCATIONAL_PROGRAM,
                        CorpusCategory.EDUCATIONAL_PROGRAM,
                        CorpusCategory.GIA_TASK,
                        CorpusCategory.PRACTICE_REGULATION
                );
    }

    @Test
    @DisplayName("Given corrupted or unreadable documents, When parsing executes, Then explicit warnings are logged and clean files continue processing without data loss")
    void shouldLogWarningsAndContinueProcessingWhenCorruptedFilesEncountered() throws IOException {
        Path eduDir = tempDir.resolve("educational_programs");
        Path giaDir = tempDir.resolve("gia_tasks");
        Path regDir = tempDir.resolve("practice_regulations");

        Files.createDirectories(eduDir);
        Files.createDirectories(giaDir);
        Files.createDirectories(regDir);

        Files.writeString(eduDir.resolve("valid_program.docx"), "Valid Educational Program Content");
        Files.writeString(eduDir.resolve("corrupted_program.docx"), "CORRUPTED: header byte damaged");
        Files.write(eduDir.resolve("empty_unreadable.docx"), new byte[0]);
        Files.writeString(giaDir.resolve("valid_gia.pdf"), "Valid GIA Task Content");
        Files.writeString(regDir.resolve("valid_regulation.docx"), "Valid Regulation Content");

        CorpusSeedLoader.IngestionResult result = seedLoader.loadCorpus(tempDir);

        assertThat(result.educationalProgramsIndexed()).isEqualTo(1);
        assertThat(result.giaTasksIndexed()).isEqualTo(1);
        assertThat(result.practiceRegulationsIndexed()).isEqualTo(1);
        assertThat(result.skippedCorruptedCount()).isEqualTo(2);
        assertThat(result.totalIndexed()).isEqualTo(3);

        assertThat(result.indexedDocuments())
                .extracting(CorpusDocument::getTitle)
                .containsExactlyInAnyOrder("valid_program", "valid_gia", "valid_regulation");
    }

    @Test
    @DisplayName("Given Flyway migration file V20261108235235279, When loaded as resource, Then contains expected table definitions")
    void shouldVerifyFlywayMigrationResourceExists() throws IOException {
        var resource = getClass().getClassLoader().getResource("db/migration/V20261108235235279__corpus_seed_tables.sql");
        assertThat(resource).isNotNull();
        String sql = new String(resource.openStream().readAllBytes());
        assertThat(sql).contains("CREATE TABLE IF NOT EXISTS corpus_catalog");
        assertThat(sql).contains("CREATE TABLE IF NOT EXISTS corpus_document");
    }
}
