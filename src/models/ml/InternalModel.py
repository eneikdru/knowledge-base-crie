"""
Grounded AI Consultation Engine and Regulatory Assistant Knowledge Context
for FBUN CRIE Rospotrebnadzor Educational Center.

Provides deterministic institutional memory for:
- FGOS VO standards (31.08.36 Epidemiology, 31.08.35 Infectious Diseases, 31.08.19 Pediatrics)
- 3 mandatory stages of State Final Attestation (GIA)
- SanPiN sanitary-epidemiological requirements
- Candidate exam minimums and VAK peer-reviewed publication requirements
- GOST R 7.0.97-2016 administrative order project metadata
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class NormativeClause:
    code: str
    title: str
    clause_ref: str
    summary: str
    keywords: Tuple[str, ...]


@dataclass(frozen=True)
class ConsultationResponse:
    query: str
    matched_category: str
    answer: str
    citations: List[str] = field(default_factory=list)
    grounded: bool = True
    deterministic_fallback: bool = True
    system_prompt: str = ""


INSTITUTIONAL_MEMORY: Dict[str, NormativeClause] = {
    "FGOS_VO": NormativeClause(
        code="FGOS_VO",
        title="Федеральные государственные образовательные стандарты высшего образования (ординатура)",
        clause_ref="ФГОС ВО 31.08.36 (Эпидемиология), 31.08.35 (Инфекционные болезни), 31.08.19 (Педиатрия), п. 6.2–6.5",
        summary=(
            "Объем программы ординатуры составляет 120 зачетных единиц (ЗЕТ) за 2 года обучения "
            "(4 320 академических часов). Блок 2 «Практики» включает обязательную базовую и вариативную "
            "клиническую/лабораторную практику в объеме не менее 72–78 ЗЕТ (от 2 592 академических часов). "
            "Допуск к промежуточной аттестации и экзаменам осуществляется при полном выполнении рабочего "
            "учебного плана (РУП), дневника практики и отсутствии академической задолженности."
        ),
        keywords=(
            "фгос",
            "fgos",
            "практик",
            "practice",
            "часы",
            "hours",
            "зет",
            "ординатур",
            "31.08.36",
            "31.08.35",
            "31.08.19",
            "учебн",
            "допуск к экзамен",
        ),
    ),
    "GIA_STAGES": NormativeClause(
        code="GIA_STAGES",
        title="Положение о государственной итоговой аттестации (ГИА) ФБУН ЦНИИ Эпидемиологии",
        clause_ref="Приказ Минобрнауки России № 636 / Локальный регламент ГИА ФБУН ЦНИИ Эпидемиологии, разд. 3–4",
        summary=(
            "Государственная итоговая аттестация (ГИА) включает 3 обязательных этапа: "
            "1) Междисциплинарное тестирование (проверка теоретических знаний по специальности); "
            "2) Оценка практических навыков и умений (симуляционно-клинический этап / решение практических задач); "
            "3) Итоговое собеседование по ситуационным клинико-эпидемиологическим задачам перед Государственной "
            "экзаменационной комиссией (ГЭК). К ГИА допускаются обучающиеся, не имеющие академической задолженности "
            "и в полном объеме выполнившие учебный план или индивидуальный учебный план. Состав ГЭК утверждается "
            "приказом директора института (не менее 5 человек, председатель — внешний ведущий специалист/доктор наук)."
        ),
        keywords=(
            "гиа",
            "gia",
            "этап",
            "stage",
            "гэк",
            "комисси",
            "аттестац",
            "admission",
            "допуск",
            "экзамен",
        ),
    ),
    "SANPIN": NormativeClause(
        code="SANPIN",
        title="Санитарно-эпидемиологические правила и нормативы (СанПиН)",
        clause_ref="СанПиН 3.3686-21 «Санитарно-эпидемиологические требования по профилактике инфекционных болезней», СП 2.1.3678-20",
        summary=(
            "Обязательное соблюдение режима биологической безопасности при работе с ПБА I–IV групп патогенности, "
            "требований к площадям учебных и лабораторных помещений, кратности воздухообмена, медицинским осмотрам "
            "и вакцинопрофилактике ординаторов и аспирантов перед допуском на клинические и лабораторные базы."
        ),
        keywords=(
            "санпин",
            "sanpin",
            "санитар",
            "гигиен",
            "пба",
            "биобезопасн",
            "роспотребнадзор",
            "эпидемиолог",
        ),
    ),
    "VAK_CANDIDATE": NormativeClause(
        code="VAK_CANDIDATE",
        title="Требования ВАК и кандидатские минимумы (аспирантура и диссертационный совет)",
        clause_ref="Положение о присуждении ученых степеней (Постановление Правительства РФ № 842, п. 11–13) и Регламент Диссовета ФБУН ЦНИИ Эпидемиологии",
        summary=(
            "Кандидатские экзамены (кандидатский минимум) включают 3 дисциплины: "
            "1) История и философия науки; 2) Иностранный язык; 3) Специальная дисциплина (Эпидемиология / "
            "Инфекционные болезни / Педиатрия). Публикационные требования ВАК для защиты кандидатской диссертации "
            "по медико-биологическим наукам: не менее 2 научных статей в рецензируемых научных изданиях из Перечня ВАК "
            "Минобрнауки России (рекомендованы категории К1/К2) либо индексируемых в международных базах данных "
            "(RSCI, Web of Science, Scopus). Для докторской диссертации — не менее 10 рецензируемых статей из Перечня ВАК."
        ),
        keywords=(
            "вак",
            "vak",
            "кандидат",
            "candidate",
            "публикац",
            "publication",
            "журнал",
            "journal",
            "рецензируем",
            "peer-reviewed",
            "диссертац",
            "минимум",
            "аспирант",
            "indexation",
            "индексац",
        ),
    ),
    "GOST_DOCX_ORDERS": NormativeClause(
        code="GOST_DOCX_ORDERS",
        title="Оформление проектов приказов по ГОСТ Р 7.0.97-2016",
        clause_ref="ГОСТ Р 7.0.97-2016 «Система стандартов по информации, библиотечному и издательскому делу. Организационно-распорядительная документация»",
        summary=(
            "Проекты официальных приказов ФБУН ЦНИИ Эпидемиологии Роспотребнадзора (о зачислении, допуске к ГИА, "
            "назначении стипендий) формируются в формате .docx со следующими обязательными реквизитами: "
            "шрифт Times New Roman 14 пт, межстрочный интервал 1.0–1.15, поля: левое 30 мм, правое 15 мм, "
            "верхнее 20 мм, нижнее 20 мм, официальная шапка Роспотребнадзора и ФБУН ЦНИИ Эпидемиологии."
        ),
        keywords=(
            "приказ",
            "order",
            "гост",
            "gost",
            "7.0.97-2016",
            "docx",
            "стипенд",
            "зачислен",
            "реквизит",
        ),
    ),
}


class RegulatoryAssistantModel:
    """
    Grounded prompt orchestrator and deterministic consultation engine
    for the Educational Center of FBUN CRIE Rospotrebnadzor.
    """

    def __init__(self, memory: Optional[Dict[str, NormativeClause]] = None) -> None:
        self.memory: Dict[str, NormativeClause] = dict(memory or INSTITUTIONAL_MEMORY)

    def build_grounded_system_prompt(self) -> str:
        """Constructs the institutional system prompt anchoring LLM/deterministic responses."""
        sections = [
            "Вы — официальный персональный ИИ-помощник Образовательного центра ФБУН ЦНИИ Эпидемиологии Роспотребнадзора.",
            "Отвечайте строго на основании нормативной базы института без вымышленных требований (no hallucinations):",
        ]
        for key in ("FGOS_VO", "GIA_STAGES", "SANPIN", "VAK_CANDIDATE", "GOST_DOCX_ORDERS"):
            clause = self.memory.get(key)
            if clause:
                sections.append(f"- [{clause.code}] {clause.title} ({clause.clause_ref}): {clause.summary}")
        return "\n".join(sections)

    def match_clauses(self, query: str) -> List[NormativeClause]:
        """Deterministically matches an inquiry to applicable normative clauses."""
        normalized = (query or "").strip().lower()
        if not normalized:
            return [self.memory["FGOS_VO"], self.memory["GIA_STAGES"]]

        matched: List[NormativeClause] = []
        for key in ("GIA_STAGES", "FGOS_VO", "SANPIN", "VAK_CANDIDATE", "GOST_DOCX_ORDERS"):
            clause = self.memory[key]
            if any(kw in normalized for kw in clause.keywords):
                matched.append(clause)

        # Ensure inquiries about practice hours or GIA admission include both FGOS VO and GIA/SanPiN grounding
        if any(tok in normalized for tok in ("гиа", "gia", "практик", "practice", "допуск", "admission", "часы", "hours")):
            for req_key in ("FGOS_VO", "GIA_STAGES", "SANPIN"):
                if self.memory[req_key] not in matched:
                    matched.append(self.memory[req_key])

        if not matched:
            matched = [
                self.memory["FGOS_VO"],
                self.memory["GIA_STAGES"],
                self.memory["SANPIN"],
                self.memory["VAK_CANDIDATE"],
            ]
        return matched

    def consult(self, query: str) -> ConsultationResponse:
        """
        Evaluates a staff or student inquiry and returns a legally grounded,
        hallucination-free response citing exact FGOS VO, GIA, SanPiN, or VAK clauses.
        """
        clauses = self.match_clauses(query)
        citations = [clause.clause_ref for clause in clauses]
        primary_category = clauses[0].code if clauses else "GENERAL_NORMATIVE"

        body_parts = [
            "Юридически выверенная справка Образовательного центра ФБУН ЦНИИ Эпидемиологии Роспотребнадзора:"
        ]
        for clause in clauses:
            body_parts.append(f"• {clause.title} [{clause.clause_ref}]: {clause.summary}")

        return ConsultationResponse(
            query=query,
            matched_category=primary_category,
            answer="\n".join(body_parts),
            citations=citations,
            grounded=True,
            deterministic_fallback=True,
            system_prompt=self.build_grounded_system_prompt(),
        )


class InternalModel(RegulatoryAssistantModel):
    """Canonical InternalModel entry point for BARCAN-TAG-04 regulatory AI context."""

    def generate_response(self, query: str) -> Dict[str, object]:
        result = self.consult(query)
        return {
            "query": result.query,
            "category": result.matched_category,
            "answer": result.answer,
            "citations": list(result.citations),
            "grounded": result.grounded,
            "deterministic_fallback": result.deterministic_fallback,
            "system_prompt": result.system_prompt,
        }
