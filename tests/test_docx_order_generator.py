import pytest
from src.models.ml.InternalModel import (
    INSTITUTIONAL_MEMORY,
    InternalModel,
    RegulatoryAssistantModel,
)


def test_gia_three_stage_admission_and_practice_hours_grounding():
    """
    Acceptance Criteria 1:
    Given an inquiry regarding GIA three-stage admission or practice hours,
    When processed by the assistant consultation engine,
    Then the generated response quotes applicable FGOS VO, SanPiN, or institutional
    regulation clauses without fabricated requirements.
    """
    model = InternalModel()
    inquiry = "Каковы условия допуска к 3 этапам ГИА и сколько часов практики требуется по ФГОС ВО?"
    response = model.consult(inquiry)

    assert response.grounded is True
    assert response.deterministic_fallback is True
    assert "3 обязательных этапа" in response.answer
    assert "Междисциплинарное тестирование" in response.answer
    assert "Оценка практических навыков" in response.answer
    assert "Итоговое собеседование" in response.answer
    assert "ФГОС ВО 31.08.36" in response.answer
    assert "2 592 академических часов" in response.answer
    assert "СанПиН 3.3686-21" in response.answer
    assert any("ФГОС ВО" in ref for ref in response.citations)
    assert any("ГИА" in ref for ref in response.citations)
    assert any("СанПиН" in ref for ref in response.citations)


def test_candidate_exams_and_vak_publication_thresholds():
    """
    Acceptance Criteria 2:
    Given a query regarding candidate exams or VAK publication thresholds,
    When evaluated by the assistant service,
    Then specific journal indexation requirements (VAK list, peer-reviewed standards)
    are precisely detailed in the output text.
    """
    model = InternalModel()
    query = "Какие требования ВАК к публикациям и какие дисциплины входят в кандидатский минимум?"
    payload = model.generate_response(query)

    answer = str(payload["answer"])
    citations = payload["citations"]

    assert payload["category"] == "VAK_CANDIDATE"
    assert "Перечня ВАК" in answer
    assert "рецензируемых научных изданиях" in answer
    assert "не менее 2 научных статей" in answer
    assert "История и философия науки" in answer
    assert "Иностранный язык" in answer
    assert "Специальная дисциплина" in answer
    assert "RSCI, Web of Science, Scopus" in answer
    assert any("Постановление Правительства РФ № 842" in c for c in citations)


def test_gost_docx_order_specifications_in_knowledge_context():
    """
    Verifies that GOST R 7.0.97-2016 order formatting rules (Times New Roman 14pt,
    margins 30/15 mm, Rospotrebnadzor header) are preserved in institutional memory.
    """
    assistant = RegulatoryAssistantModel()
    response = assistant.consult("Подготовка проекта приказа о допуске к ГИА и назначении стипендий по ГОСТ")

    assert "ГОСТ Р 7.0.97-2016" in response.answer
    assert "Times New Roman 14 пт" in response.answer
    assert "левое 30 мм, правое 15 мм" in response.answer
    assert "Роспотребнадзора" in response.answer
    assert "FGOS_VO" in INSTITUTIONAL_MEMORY
    assert "GIA_STAGES" in INSTITUTIONAL_MEMORY
    assert "SANPIN" in INSTITUTIONAL_MEMORY
    assert "VAK_CANDIDATE" in INSTITUTIONAL_MEMORY
    assert "GOST_DOCX_ORDERS" in INSTITUTIONAL_MEMORY
