from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

SYNONYMS: Dict[str, List[str]] = {
    "гиа": ["государственная итоговая аттестация", "итоговая аттестация", "экзамен", "госэкзамен"],
    "руп": ["рабочий учебный план", "учебный план"],
    "рпд": ["рабочая программа дисциплины", "программа дисциплины"],
    "фос": ["фонд оценочных средств", "оценочные средства"],
    "вак": ["высшая аттестационная комиссия", "диссертация", "диссовет"],
    "ппс": ["профессорско-преподавательский состав", "нагрузка", "преподаватель"],
    "санпин": ["санитарные правила", "санитарно-эпидемиологические требования"],
    "фгос": ["федеральный государственный образовательный стандарт", "фгос во"],
}

DOCUMENT_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "DOC-2026-001",
        "title": "Рабочая программа дисциплины (РПД) Эпидемиология 2026/27 уч. год",
        "category": "SYLLABUS_RPD",
        "specialty_code": "31.08.36",
        "specialty_name": "Эпидемиология",
        "academic_year": "2026/2027",
        "doc_type": "РПД",
        "content": "Рабочая программа дисциплины (РПД) по специальности 31.08.36 Эпидемиология. Утверждена УМС института. Включает 120 зачетных единиц, часы лекций, семинаров, практической подготовки в лабораториях ЦНИИЭ.",
        "tags": ["РПД", "Эпидемиология", "УМС", "2026/2027"],
        "updated_at": "2026-09-01T10:00:00Z"
    },
    {
        "id": "DOC-2026-002",
        "title": "Регламент проведения ГИА по специальности 31.08.36 Эпидемиология",
        "category": "GIA_PROGRAMS",
        "specialty_code": "31.08.36",
        "specialty_name": "Эпидемиология",
        "academic_year": "2026/2027",
        "doc_type": "Регламент",
        "content": "Регламент проведения государственной итоговой аттестации (ГИА). Определяет 3 обязательных этапа ГИА: компьютерное тестирование, оценка практических навыков и собеседование с ГЭК.",
        "tags": ["ГИА", "Регламент", "ГЭК", "Экзамен"],
        "updated_at": "2026-10-15T12:00:00Z"
    },
    {
        "id": "DOC-2026-003",
        "title": "Положение о порядке планирования педагогической нагрузки ППС",
        "category": "REGULATIONS",
        "specialty_code": "ALL",
        "specialty_name": "Общеинститутский",
        "academic_year": "2026/2027",
        "doc_type": "Положение",
        "content": "Положение о порядке расчета и учета годовой учебной нагрузки профессорско-преподавательского состава (ППС). Кафедральная норма составляет 750–900 часов в год на одну ставку.",
        "tags": ["ППС", "Нагрузка", "Положение", "Ставка"],
        "updated_at": "2026-08-20T09:30:00Z"
    },
    {
        "id": "DOC-2026-004",
        "title": "Фонд оценочных средств (ФОС): Инфекционные болезни",
        "category": "FOS",
        "specialty_code": "31.08.35",
        "specialty_name": "Инфекционные болезни",
        "academic_year": "2026/2027",
        "doc_type": "ФОС",
        "content": "Фонд оценочных средств (ФОС) для ординатуры по направлению 31.08.35 Инфекционные болезни. Содержит ситуационные задачи, тестовые задания и критерии оценки знаний.",
        "tags": ["ФОС", "Инфекционные болезни", "Тестирование"],
        "updated_at": "2026-09-05T14:15:00Z"
    },
    {
        "id": "DOC-2026-005",
        "title": "Правила аттестации ординаторов по специальности Педиатрия",
        "category": "RULES",
        "specialty_code": "31.08.19",
        "specialty_name": "Педиатрия",
        "academic_year": "2026/2027",
        "doc_type": "Правила",
        "content": "Правила текущего контроля успеваемости и промежуточной аттестации ординаторов по специальности 31.08.19 Педиатрия в образовательном центре ФБУН ЦНИИ Эпидемиологии.",
        "tags": ["Педиатрия", "Правила", "Аттестация"],
        "updated_at": "2026-09-12T11:00:00Z"
    },
    {
        "id": "DOC-2026-006",
        "title": "Инструкция по подготовке диссертационных работ и публикационным требованиям ВАК",
        "category": "INSTRUCTIONS",
        "specialty_code": "ALL",
        "specialty_name": "Аспирантура и диссовет",
        "academic_year": "2026/2027",
        "doc_type": "Инструкция",
        "content": "Инструкция устанавливает публикационные требования ВАК к соискателям ученой степени кандидата наук, порядок формирования пакета документов в диссертационный совет института.",
        "tags": ["ВАК", "Диссовет", "Инструкция", "Диссертация"],
        "updated_at": "2026-10-01T16:45:00Z"
    }
]

def expand_query_with_synonyms(query: str) -> List[str]:
    terms = [term for term in re.findall(r"[\w\d\.-]+", query.lower()) if len(term) >= 2]
    expanded = set(terms)
    for term in terms:
        if term in SYNONYMS:
            for syn in SYNONYMS[term]:
                expanded.update(re.findall(r"[\w\d\.-]+", syn.lower()))
    return list(expanded)

def extract_excerpt(text: str, search_terms: List[str], window: int = 140) -> str:
    if not text:
        return ""
    text_lower = text.lower()
    best_pos = -1
    for term in search_terms:
        pos = text_lower.find(term.lower())
        if pos != -1:
            best_pos = pos
            break

    if best_pos == -1:
        excerpt_raw = text[:window]
        if len(text) > window:
            excerpt_raw += "..."
        return excerpt_raw

    start = max(0, best_pos - 40)
    end = min(len(text), best_pos + window)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."

    for term in sorted(search_terms, key=len, reverse=True):
        if len(term) < 2:
            continue
        pattern = re.compile(rf"({re.escape(term)})", re.IGNORECASE)
        snippet = pattern.sub(r"<mark>\1</mark>", snippet)

    return snippet

def search_documents(
    query: str,
    category: Optional[str] = None,
    specialty_code: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
) -> Dict[str, Any]:
    search_terms = expand_query_with_synonyms(query)
    results = []
    facet_categories: Dict[str, int] = {}
    facet_specialties: Dict[str, int] = {}

    for doc in DOCUMENT_CATALOG:
        cat = doc.get("category", "OTHER")
        spec = doc.get("specialty_code", "ALL")
        facet_categories[cat] = facet_categories.get(cat, 0) + 1
        facet_specialties[spec] = facet_specialties.get(spec, 0) + 1

    for doc in DOCUMENT_CATALOG:
        if category and doc.get("category") != category:
            continue
        if specialty_code and doc.get("specialty_code") not in (specialty_code, "ALL"):
            continue

        searchable_text = f"{doc['title']} {doc['content']} {' '.join(doc.get('tags', []))} {doc.get('specialty_name', '')} {doc.get('doc_type', '')}".lower()
        score = 0
        for term in search_terms:
            if term in searchable_text:
                score += searchable_text.count(term) * (3 if term in doc["title"].lower() else 1)

        if score > 0:
            excerpt = extract_excerpt(doc["content"], search_terms)
            results.append({
                "id": doc["id"],
                "title": doc["title"],
                "category": doc["category"],
                "specialty_code": doc["specialty_code"],
                "specialty_name": doc.get("specialty_name"),
                "doc_type": doc.get("doc_type"),
                "academic_year": doc.get("academic_year"),
                "excerpt": excerpt,
                "tags": doc.get("tags", []),
                "score": score,
                "updated_at": doc.get("updated_at"),
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    total = len(results)
    paginated = results[offset : offset + limit]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": paginated,
        "facets": {
            "categories": facet_categories,
            "specialties": facet_specialties
        },
        "query_expansion": search_terms
    }

def get_document_by_id(doc_id: str) -> Optional[Dict[str, Any]]:
    for doc in DOCUMENT_CATALOG:
        if doc["id"] == doc_id:
            return doc
    return None
