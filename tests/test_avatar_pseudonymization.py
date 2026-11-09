"""
Automated unit and integration tests for 152-FZ synthetic avatar generation,
pseudonymization, and zero-PII leakage guarantees across institute domains.
"""

import json
import os
import re
import unittest
from typing import Dict, Any, List


# Russian passport regex: 4 digits (series) followed by space or optional separator and 6 digits (number)
PASSPORT_REGEX = re.compile(r"\b\d{2}\s*\d{2}\s*\d{6}\b")
# Russian SNILS regex: XXX-XXX-XXX XX
SNILS_REGEX = re.compile(r"\b\d{3}-\d{3}-\d{3}\s*\d{2}\b")
# Russian phone number regex: +7 / 8 followed by 10 digits
PHONE_REGEX = re.compile(r"(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}")

# Canonical synthetic identifier prefixes per 152-FZ specification
ALLOWED_ID_PREFIXES = ("ORD-", "ASP-", "FAC-", "ADM-")


def mask_pii_text(text: str, avatar_map: Dict[str, str]) -> str:
    """
    Mask real personal identifiable information (PII) including Russian names,
    passports, SNILS, and phone numbers, substituting with synthetic identifiers.
    """
    sanitized = text
    # Mask passports
    sanitized = PASSPORT_REGEX.sub("[ДАННЫЕ ПАСПОРТА СКРЫТЫ: 152-ФЗ]", sanitized)
    # Mask SNILS
    sanitized = SNILS_REGEX.sub("[СНИЛС СКРЫТ: 152-ФЗ]", sanitized)
    # Mask phone numbers
    sanitized = PHONE_REGEX.sub("[ТЕЛЕФОН СКРЫТ: 152-ФЗ]", sanitized)

    # Substitute real names with synthetic avatar identifiers
    for real_name, avatar_id in avatar_map.items():
        if real_name in sanitized:
            sanitized = sanitized.replace(real_name, avatar_id)

    return sanitized


def validate_zero_pii_leakage(text: str, real_names: List[str]) -> bool:
    """
    Validate that no real names or sensitive identity numbers exist in sanitized payload.
    """
    for name in real_names:
        if name.lower() in text.lower():
            return False
    if PASSPORT_REGEX.search(text):
        return False
    if SNILS_REGEX.search(text):
        return False
    if PHONE_REGEX.search(text):
        return False
    return True


class TestAvatarPseudonymization152FZ(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        catalog_path = os.path.join(os.path.dirname(__file__), "..", "data", "avatars", "synthetic_avatars.json")
        with open(catalog_path, "r", encoding="utf-8") as f:
            cls.catalog = json.load(f)

    def test_synthetic_avatar_schema_and_id_conventions(self):
        """Verify all avatars in the catalog conform strictly to 152-FZ prefix and role mapping."""
        avatars = self.catalog.get("avatars", [])
        self.assertGreater(len(avatars), 0)
        self.assertEqual(self.catalog.get("privacy_compliance"), "152-FZ Zero-Knowledge Synthetic Avatars")

        for avatar in avatars:
            avatar_id = avatar.get("id", "")
            role = avatar.get("role", "")
            self.assertTrue(
                any(avatar_id.startswith(prefix) for prefix in ALLOWED_ID_PREFIXES),
                f"Avatar ID '{avatar_id}' violates 152-FZ prefix convention",
            )
            self.assertRegex(avatar_id, r"^(ORD|ASP|FAC|ADM)-\d{4}$", f"Invalid avatar ID format: {avatar_id}")

            # Verify role mappings
            if avatar_id.startswith("ORD-"):
                self.assertEqual(role, "ординатор")
            elif avatar_id.startswith("ASP-"):
                self.assertEqual(role, "аспирант")
            elif avatar_id.startswith("FAC-"):
                self.assertEqual(role, "преподаватель")
            elif avatar_id.startswith("ADM-"):
                self.assertEqual(role, "администрация")

    def test_pii_masking_russian_names_and_passports(self):
        """Ensure real Russian full names and passport details are replaced and zero PII leaks."""
        real_names = [
            "Ковалев Алексей Сергеевич",
            "Смирнова Екатерина Дмитриевна",
            "Петров Николай Владимирович",
        ]
        avatar_mapping = {
            "Ковалев Алексей Сергеевич": "ORD-0001",
            "Смирнова Екатерина Дмитриевна": "ORD-0002",
            "Петров Николай Владимирович": "ASP-0001",
        }

        raw_incoming_text = (
            "Служебная записка: Зачислить Ковалев Алексей Сергеевич (паспорт 45 12 876543, СНИЛС 123-456-789 00) "
            "и Смирнова Екатерина Дмитриевна (паспорт 4515 998877, телефон +7 (916) 123-45-67). "
            "Научный руководитель: Петров Николай Владимирович."
        )

        sanitized = mask_pii_text(raw_incoming_text, avatar_mapping)

        # Assert zero leakage
        self.assertTrue(validate_zero_pii_leakage(sanitized, real_names))
        for name in real_names:
            self.assertNotIn(name, sanitized)

        # Assert passport numbers are completely hidden
        self.assertNotIn("876543", sanitized)
        self.assertNotIn("998877", sanitized)
        self.assertNotIn("+7 (916) 123-45-67", sanitized)
        self.assertNotIn("123-456-789 00", sanitized)

        # Assert synthetic identifiers are correctly substituted
        self.assertIn("ORD-0001", sanitized)
        self.assertIn("ORD-0002", sanitized)
        self.assertIn("ASP-0001", sanitized)

    def test_pii_masking_empty_and_already_pseudonymized(self):
        """Verify that already pseudonymized strings remain unaffected and safe."""
        avatar_mapping = {"Иванов Иван Иванович": "ORD-0010"}
        already_pseudonymized = "Ординатор ORD-0005 допущен к ГИА приказом FAC-0002."
        sanitized = mask_pii_text(already_pseudonymized, avatar_mapping)
        self.assertEqual(sanitized, already_pseudonymized)

    def test_no_raw_external_ai_leakage_vector(self):
        """Simulate payload preparation for external AI assistant consultation."""
        consultation_prompt = {
            "query": "Сформировать характеристику на ординатора Сидорова Анна Михайловна, паспорт 45 09 112233.",
            "target_audience": "ADMINISTRATION"
        }
        avatar_mapping = {"Сидорова Анна Михайловна": "ORD-0007"}
        sanitized_query = mask_pii_text(consultation_prompt["query"], avatar_mapping)

        self.assertNotIn("Сидорова Анна Михайловна", sanitized_query)
        self.assertNotIn("45 09 112233", sanitized_query)
        self.assertIn("ORD-0007", sanitized_query)
        self.assertTrue(validate_zero_pii_leakage(sanitized_query, ["Сидорова Анна Михайловна"]))


if __name__ == "__main__":
    unittest.main()
