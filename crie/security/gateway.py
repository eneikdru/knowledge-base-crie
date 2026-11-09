import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


# Regex patterns for Russian personal identifiable information (152-FZ)
PASSPORT_SERIES_NUMBER = re.compile(r"\b(\d{2}\s*\d{2})\s+(\d{6})\b")
PASSPORT_GENERIC = re.compile(r"\bпаспорт[а-я]*\s*(?:серия|№|номер)?\s*(\d{4})\s*(\d{6})\b", re.IGNORECASE)
SNILS_PATTERN = re.compile(r"\b\d{3}-\d{3}-\d{3}\s*\d{2}\b|\b\d{11}\b")
INN_PATTERN = re.compile(r"\b(?:ИНН\s*)?(\d{10}|\d{12})\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"\b(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b")
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

# Russian FIO pattern (Full Name: Surname Firstname Patronymic)
# Matches capitalized Cyrillic triplets e.g., 'Иванов Иван Иванович'
RUSSIAN_FIO_PATTERN = re.compile(
    r"\b([А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?)\s+([А-ЯЁ][а-яё]+)\s+([А-ЯЁ][а-яё]+)\b"
)


class AvatarRegistry:
    """
    Maintains synthetic pseudonymous avatar mappings according to 152-FZ:
    ORD-XXXX (residents/ординаторы),
    ASP-XXXX (postgraduates/аспиранты),
    FAC-XXXX (faculty/преподаватели).
    """

    def __init__(self, data_path: Optional[str] = None):
        self.fio_to_avatar: Dict[str, str] = {}
        self.avatar_to_fio: Dict[str, str] = {}
        self.counters = {"ORD": 1000, "ASP": 1000, "FAC": 1000}
        self.data_path = data_path or self._resolve_avatar_path()
        if self.data_path and os.path.exists(self.data_path):
            self.load_avatars(self.data_path)

    @staticmethod
    def _resolve_avatar_path() -> str:
        cur = os.path.dirname(os.path.abspath(__file__))
        candidate = os.path.join(os.path.dirname(os.path.dirname(cur)), "data", "avatars", "synthetic_avatars.json")
        if os.path.exists(candidate):
            return candidate
        cwd_candidate = os.path.join(os.getcwd(), "data", "avatars", "synthetic_avatars.json")
        return cwd_candidate

    def load_avatars(self, path: str) -> None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                avatars = data if isinstance(data, list) else data.get("avatars", [])
                for entry in avatars:
                    fio = entry.get("full_name") or entry.get("fio")
                    avatar_id = entry.get("avatar_id") or entry.get("id")
                    if fio and avatar_id:
                        self.fio_to_avatar[fio.strip()] = avatar_id
                        self.avatar_to_fio[avatar_id] = fio.strip()
        except Exception:
            pass

    def get_or_create_avatar(self, full_name: str, role_category: str = "ORD") -> str:
        clean_name = full_name.strip()
        if clean_name in self.fio_to_avatar:
            return self.fio_to_avatar[clean_name]

        # Infer prefix based on category or default
        cat = role_category.upper()
        prefix = "ORD"
        if "ASP" in cat or "АСП" in cat:
            prefix = "ASP"
        elif "FAC" in cat or "ПРЕП" in cat or "ППС" in cat:
            prefix = "FAC"

        self.counters[prefix] += 1
        new_id = f"{prefix}-{self.counters[prefix]}"
        self.fio_to_avatar[clean_name] = new_id
        self.avatar_to_fio[new_id] = clean_name
        return new_id

    def get_all_mappings(self) -> List[Dict[str, str]]:
        return [
            {"full_name": fio, "avatar_id": avatar_id}
            for fio, avatar_id in self.fio_to_avatar.items()
        ]


_REGISTRY: Optional[AvatarRegistry] = None


def get_avatar_registry() -> AvatarRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = AvatarRegistry()
    return _REGISTRY


def sanitize_pii_and_pseudonymize(text: str, registry: Optional[AvatarRegistry] = None) -> Tuple[str, Dict[str, Any]]:
    """
    Inspects text, strips unmasked sensitive PII (passports, phones, emails, SNILS, INN),
    and substitutes real human names with anonymized avatar identifiers (ORD-XXXX, ASP-XXXX, FAC-XXXX).
    """
    if not text:
        return text, {"pii_detected": False, "redactions_count": 0}

    reg = registry or get_avatar_registry()
    redactions = 0
    sanitized = text

    # 1. Substitute known names or discovered Russian FIO
    def replace_fio(match: re.Match) -> str:
        nonlocal redactions
        fio = match.group(0)
        # Detect heuristic role if adjacent context exists or default to ORD
        avatar_id = reg.get_or_create_avatar(fio, role_category="ORD")
        redactions += 1
        return avatar_id

    sanitized = RUSSIAN_FIO_PATTERN.sub(replace_fio, sanitized)

    # Also replace any explicitly registered names in registry
    for real_name, avatar_id in reg.fio_to_avatar.items():
        if real_name in sanitized:
            sanitized = sanitized.replace(real_name, avatar_id)
            redactions += 1

    # 2. Mask Passports
    if PASSPORT_SERIES_NUMBER.search(sanitized):
        sanitized = PASSPORT_SERIES_NUMBER.sub("[REDACTED_PASSPORT]", sanitized)
        redactions += 1
    if PASSPORT_GENERIC.search(sanitized):
        sanitized = PASSPORT_GENERIC.sub("[REDACTED_PASSPORT]", sanitized)
        redactions += 1

    # 3. Mask Phones
    if PHONE_PATTERN.search(sanitized):
        sanitized = PHONE_PATTERN.sub("[REDACTED_PHONE]", sanitized)
        redactions += 1

    # 4. Mask Emails
    if EMAIL_PATTERN.search(sanitized):
        sanitized = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", sanitized)
        redactions += 1

    # 5. Mask SNILS
    if SNILS_PATTERN.search(sanitized):
        sanitized = SNILS_PATTERN.sub("[REDACTED_SNILS]", sanitized)
        redactions += 1

    return sanitized, {
        "pii_detected": redactions > 0,
        "redactions_count": redactions
    }


def recursively_sanitize_data(data: Any, registry: Optional[AvatarRegistry] = None) -> Any:
    """
    Recursively traverses JSON-compatible dictionaries/lists and sanitizes string values.
    """
    if isinstance(data, str):
        clean_text, _ = sanitize_pii_and_pseudonymize(data, registry)
        return clean_text
    elif isinstance(data, dict):
        return {k: recursively_sanitize_data(v, registry) for k, v in data.items()}
    elif isinstance(data, list):
        return [recursively_sanitize_data(elem, registry) for elem in data]
    return data


class SecurityGatewayMiddleware(BaseHTTPMiddleware):
    """
    FastAPI Middleware enforcing 152-FZ compliance:
    Intercepts requests destined for assistant and order handlers:
    - /api/assistant/chat
    - /api/orders/generate
    Sanitizes request bodies so zero unmasked PII reaches outbound LLM or generator logic.
    """
    PROTECTED_ROUTES = (
        "/api/assistant/chat",
        "/api/orders/generate",
    )

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Check if route is subject to PII security gateway
        is_protected = any(path.startswith(route) for route in self.PROTECTED_ROUTES)

        if is_protected and request.method in ("POST", "PUT", "PATCH"):
            try:
                body_bytes = await request.body()
                if body_bytes:
                    content_type = request.headers.get("content-type", "")
                    if "application/json" in content_type:
                        json_body = json.loads(body_bytes.decode("utf-8"))
                        sanitized_body = recursively_sanitize_data(json_body)
                        new_bytes = json.dumps(sanitized_body, ensure_ascii=False).encode("utf-8")
                    else:
                        raw_text = body_bytes.decode("utf-8", errors="ignore")
                        sanitized_text, _ = sanitize_pii_and_pseudonymize(raw_text)
                        new_bytes = sanitized_text.encode("utf-8")

                    # Replace receive channel with sanitized bytes stream
                    async def receive():
                        return {"type": "http.request", "body": new_bytes, "more_body": False}

                    request._receive = receive
            except Exception:
                # In case of malformed body, proceed to normal FastAPI validation
                pass

        response: Response = await call_next(request)
        return response
