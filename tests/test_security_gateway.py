import pytest
from fastapi.testclient import TestClient
from crie_assistant_api import app
from crie.security.gateway import sanitize_pii_and_pseudonymize, AvatarRegistry

client = TestClient(app)


def test_sanitize_pii_and_pseudonymize_basic():
    registry = AvatarRegistry()
    raw_text = "Ординатор Смирнов Алексей Петрович имеет паспорт 4515 892341 и телефон +7 (999) 123-45-67."
    clean_text, meta = sanitize_pii_and_pseudonymize(raw_text, registry=registry)

    assert "Смирнов Алексей Петрович" not in clean_text
    assert "ORD-" in clean_text
    assert "4515 892341" not in clean_text
    assert "+7 (999) 123-45-67" not in clean_text
    assert "[REDACTED_PASSPORT]" in clean_text
    assert "[REDACTED_PHONE]" in clean_text
    assert meta["pii_detected"] is True


def test_assistant_chat_gateway_sanitizes_request_body():
    payload = {
        "message": "Прошу предоставить академический отпуск ординатору Кузнецов Дмитрий Сергеевич, паспорт 4510 123456",
        "context": "Контактный email: dmitry@example.com"
    }
    response = client.post("/api/assistant/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Ensure zero unmasked PII reaches handler
    assert "Кузнецов Дмитрий Сергеевич" not in data["received_message"]
    assert "ORD-" in data["received_message"]
    assert "4510 123456" not in data["received_message"]
    assert "[REDACTED_PASSPORT]" in data["received_message"]
    assert "dmitry@example.com" not in data["received_context"]
    assert "[REDACTED_EMAIL]" in data["received_context"]


def test_order_generation_gateway_substitutes_avatar():
    payload = {
        "template_id": "tpl_admission_2026",
        "recipient": "Иванов Иван Иванович",
        "details": {
            "phone": "+7 916 000-11-22",
            "snils": "123-456-789 00"
        }
    }
    response = client.post("/api/orders/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "Иванов Иван Иванович" not in data["recipient"]
    assert "ORD-" in data["recipient"]
    assert "+7 916 000-11-22" not in data["details"]["phone"]
    assert "123-456-789 00" not in data["details"]["snils"]


def test_avatar_inspection_unauthorized_returns_403():
    # No authorization header or standard user role
    res = client.get("/api/security/avatars")
    assert res.status_code == 403
    assert "Forbidden" in res.json()["detail"]

    res_user = client.get("/api/security/avatars", headers={"X-User-Role": "student"})
    assert res_user.status_code == 403


def test_avatar_inspection_authorized_returns_mappings():
    res_admin = client.get("/api/security/avatars", headers={"X-User-Role": "admin"})
    assert res_admin.status_code == 200
    data = res_admin.json()
    assert "total_mappings" in data
    assert "mappings" in data
