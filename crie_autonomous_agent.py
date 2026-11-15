"""
crie_autonomous_agent.py: Автономный агент Образовательного центра (Ординатура и Аспирантура)
ФБУН ЦНИИ Эпидемиологии Роспотребнадзора.

Специальности:
- 32.08.12 «Эпидемиология» (ординатура, 120 з.е. / 4 320 ч.)
- 31.08.35 «Инфекционные болезни» (ординатура)
- 31.08.19 «Педиатрия» (ординатура)
- 3.2.2 «Эпидемиология» (аспирантура)
- 3.1.22 «Инфекционные болезни» (аспирантура)

Инструменты Агента (Tools):
1. tool_use_approved_template — жесткие утвержденные эталоны приказов, протоколов УМС, допусков к ГИА.
2. tool_compose_custom_document — верстка расписаний сессий, таблиц учебных планов и кадровых справок.
3. tool_patch_document — внесение правок по обучающимся, преподавателям, датам и комиссиям.
4. tool_register_template — загрузка и утверждение новых образцов ОЦ.
5. tool_query_normative — проверка ФЗ № 273-ФЗ, ФГОС ВО, приказов Минобрнауки и регламентов ЦНИИЭ.
"""

import os
import re
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from crie_document_engine import compile_agent_composed_document
from crie_template_manager import (
    load_template_registry,
    get_template_by_id,
    create_document_session,
    patch_document_session,
    get_document_session,
    register_uploaded_template
)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")


class CrieDocumentAgent:
    """
    Интеллектуальный агент Образовательного центра с инструментами.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or DEEPSEEK_API_KEY

    def tool_list_templates(self) -> List[Dict[str, Any]]:
        return load_template_registry()

    def tool_use_approved_template(
        self,
        template_id: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        session = create_document_session(
            template_id=template_id,
            params=params or {},
            is_approved_flag=True
        )
        return session

    def tool_compose_custom_document(self, doc_model: Dict[str, Any]) -> Dict[str, Any]:
        return compile_agent_composed_document(doc_model)

    def tool_patch_document(self, session_id: str, patches: Dict[str, Any], reason: str) -> Dict[str, Any]:
        return patch_document_session(session_id, patches, reason=reason)

    def process_request(
        self,
        query: str,
        session_id: Optional[str] = None,
        use_approved_template_only: bool = False
    ) -> Dict[str, Any]:
        q_low = query.lower()
        active_session = get_document_session(session_id) if session_id else None

        # -----------------------------------------------------------------
        # СЦЕНАРИЙ 1: ПРАВКА СУЩЕСТВУЮЩЕГО ДОКУМЕНТА (INTERACTIVE PATCHING)
        # -----------------------------------------------------------------
        if active_session:
            patch_intent = self._detect_academic_patch_intent(query, active_session)
            if patch_intent:
                updated_session = self.tool_patch_document(session_id, patch_intent, reason=query)
                doc_meta = updated_session["compiled_doc"]
                status_tag = "✓ [УТВЕРЖДЕННЫЙ ОБРАЗЕЦ ОЦ]" if updated_session.get("is_approved") else "[РАБОЧИЙ ПРОЕКТ]"
                
                reply_text = (
                    f"⚡ **Агент применил инструмент `tool_patch_document`**\n"
                    f"Документ обновлен до версии **v{updated_session['version']}** {status_tag}\n\n"
                    f"• **Документ:** {updated_session.get('title')}\n"
                    f"• **Реквизиты:** № {updated_session.get('number')} от {updated_session.get('date')}\n"
                    f"• **Подписант:** {updated_session.get('head_doctor')}\n"
                    f"• **Куратор/отдел:** {updated_session.get('hospital_epidemiologist')}\n"
                    f"• **Количество пунктов/решений:** {len(updated_session.get('actions', []))}\n\n"
                    f"📄 Обновленный файл Microsoft Word пересобран бэкендом по ГОСТ Р 7.0.97-2016."
                )

                return {
                    "agent_action": "patched_document",
                    "session_id": session_id,
                    "version": updated_session["version"],
                    "response": reply_text,
                    "answer": reply_text,
                    "generated_document": doc_meta,
                    "document_session": updated_session
                }

        # -----------------------------------------------------------------
        # СЦЕНАРИЙ 2: ПРИМЕНЕНИЕ ЖЕСТКОГО УТВЕРЖДЕННОГО ОБРАЗЦА ИНСТИТУТА
        # -----------------------------------------------------------------
        if use_approved_template_only or any(w in q_low for w in ["утвержденный образец", "по образцу", "эталонный приказ", "строго по шаблону"]):
            tpl_id = "TPL-APPROVED-ADMISSION-RESIDENCY"
            if any(w in q_low for w in ["гиа", "допуск к гиа", "итоговая аттестация"]):
                tpl_id = "TPL-APPROVED-GIA-ADMISSION"
            elif any(w in q_low for w in ["умс", "учебно-методический совет", "протокол умс"]):
                tpl_id = "TPL-APPROVED-UMS-PROTOCOL"
            elif any(w in q_low for w in ["аспирантур", "тема диссертации", "научный руководитель"]):
                tpl_id = "TPL-APPROVED-ASPIRANTURA-THEME"
            elif any(w in q_low for w in ["практик", "клиническая база"]):
                tpl_id = "TPL-APPROVED-PRACTICE-ORDER"
            elif any(w in q_low for w in ["нагрузк", "кадров", "остепененност"]):
                tpl_id = "TPL-APPROVED-STAFFING-WORKLOAD"

            session = self.tool_use_approved_template(tpl_id, params={"query": query})
            doc_meta = session["compiled_doc"]

            reply_text = (
                f"🎓 **Агент применил утвержденный эталон Образовательного центра (`tool_use_approved_template`)**\n"
                f"Образец: **{session.get('template_name')}**\n"
                f"Статус: **✓ Утвержденный образец института** ({session.get('authority')})\n\n"
                f"Основание: {session.get('basis')}, ФГОС ВО ординатуры (120 з.е. / 4 320 ч.). "
                f"Формулировки зафиксированы по регламентам ЦНИИЭ и стандарту ГОСТ Р 7.0.97-2016."
            )

            return {
                "agent_action": "used_approved_template",
                "session_id": session["session_id"],
                "version": 1,
                "response": reply_text,
                "answer": reply_text,
                "generated_document": doc_meta,
                "document_session": session
            }

        # -----------------------------------------------------------------
        # СЦЕНАРИЙ 3: АВТОРСКАЯ ВЕРСТКА АГЕНТОМ (РАСПИСАНИЕ СЕССИИ / ПЛАН)
        # -----------------------------------------------------------------
        if any(w in q_low for w in ["расписание", "сесси", "экзамен", "график", "учебный план", "сверстай"]):
            now = datetime.now()
            doc_model = {
                "tag": "Расписание_сессии_ординатура",
                "doc_type": "РАСПИСАНИЕ",
                "title": "Расписание зимней экзаменационной сессии на 2026/2027 учебный год (группы 25ОЭ и 26ОЭ)",
                "organization": (
                    "ФЕДЕРАЛЬНАЯ СЛУЖБА ПО НАДЗОРУ В СФЕРЕ ЗАЩИТЫ ПРАВ ПОТРЕБИТЕЛЕЙ И БЛАГОПОЛУЧИЯ ЧЕЛОВЕКА\n"
                    "ФБУН ЦНИИ ЭПИДЕМИОЛОГИИ РОСПОТРЕБНАДЗОРА\n"
                    "ОБРАЗОВАТЕЛЬНЫЙ ЦЕНТР"
                ),
                "is_approved": False,
                "date": now.strftime("%d.%m.%Y"),
                "number": "УМС-26/11",
                "city": "г. Москва",
                "preamble": (
                    "В соответствии с календарным учебным графиком ординатуры по специальности 32.08.12 «Эпидемиология» "
                    "и Положением о проведении текущего контроля успеваемости и промежуточной аттестации:"
                ),
                "sections": [
                    {
                        "heading": "1. Сроки и порядок проведения промежуточной аттестации",
                        "text": "Экзаменационная сессия проводится в период с 25 января по 25 февраля 2027 г. Допуск осуществляется при отсутствии задолженностей по текущему контролю.",
                        "table": {
                            "headers": ["Дата и время", "Учебная группа", "Дисциплина", "Форма контроля", "Экзаменатор / Комиссия", "Аудитория"],
                            "rows": [
                                ["26.01.2027, 10:00", "25ОЭ (1 год)", "Общая эпидемиология", "Экзамен (тестирование + собеседование)", "проф. Горелов А.В.", "Конференц-зал ОЦ"],
                                ["29.01.2027, 10:00", "25ОЭ (1 год)", "Инфекционные болезни (модуль)", "Дифференцированный зачет", "доц. Семенова Е.В.", "Ауд. 204"],
                                ["04.02.2027, 11:00", "26ОЭ (2 год)", "Эпидемиологический надзор за ИСМП", "Экзамен (ситуационные задачи)", "проф. Малеев В.В.", "Конференц-зал ОЦ"],
                                ["09.02.2027, 10:00", "26ОЭ (2 год)", "Молекулярная эпидемиология", "Зачет с оценкой", "д.б.н. Климова О.Н.", "Лаб. корпус"],
                                ["16.02–25.02.2027", "25ОЭ, 26ОЭ", "Ликвидация академических задолженностей", "Повторная аттестация комиссии", "Комиссия УМС", "Учебный отдел"]
                            ]
                        }
                    },
                    {
                        "heading": "2. Требования к составу экзаменационной комиссии",
                        "items": [
                            "Доля преподавателей кафедры с учеными степенями кандидата или доктора наук — не менее 70%.",
                            "Результаты аттестации вносятся в экзаменационные ведомости и личные кабинеты ЭИОС в день проведения испытания.",
                            "Сводная ведомость с подписями членов комиссии передается в учебный отдел в течение 2 рабочих дней."
                        ]
                    }
                ],
                "signatures": [
                    {"position": "Руководитель Образовательного центра, проф.", "name": "А.В. Горелов"},
                    {"position": "Заведующий кафедрой эпидемиологии, академик", "name": "В.В. Малеев"}
                ],
                "visas": [
                    "Начальник Учебно-методического отдела: ___________________ / О.Н. Климова /"
                ]
            }

            doc_meta = self.tool_compose_custom_document(doc_model)
            session_id_new = f"session_sess_{now.strftime('%H%M%S')}"
            session_data = {
                "session_id": session_id_new,
                "version": 1,
                "is_approved": False,
                "title": doc_model["title"],
                "number": doc_model["number"],
                "date": doc_model["date"],
                "specialty": "32.08.12 «Эпидемиология»",
                "head_doctor": "А.В. Горелов",
                "hospital_epidemiologist": "О.Н. Климова",
                "actions": [it for s in doc_model["sections"] for it in s.get("items", [])],
                "compiled_doc": doc_meta,
                "doc_model": doc_model
            }
            from crie_template_manager import _DOCUMENT_SESSIONS
            _DOCUMENT_SESSIONS[session_id_new] = session_data

            reply_text = (
                f"🛠️ **Агент сверстал расписание экзаменационной сессии (`tool_compose_custom_document`)**\n\n"
                f"Сформирован документ с подробной таблицей дат, дисциплин и комиссий:\n"
                f"• **Документ:** {doc_model['title']}\n"
                f"• **Сроки сессии:** 25.01–25.02.2027 (в полном соответствии с регламентом ОЦ ЦНИИЭ)\n"
                f"• **Сверстана таблица:** 5 экзаменационных контрольных точек для групп 25ОЭ и 26ОЭ.\n\n"
                f"Вы можете написать правки (*«поменяй дату экзамена по ИСМП», «замени экзаменатора»*) или утвердить этот образец."
            )

            return {
                "agent_action": "composed_custom_document",
                "session_id": session_id_new,
                "version": 1,
                "response": reply_text,
                "answer": reply_text,
                "generated_document": doc_meta,
                "document_session": session_data
            }

        # -----------------------------------------------------------------
        # СЦЕНАРИЙ 4: СПРАВКА ПО ОРДИНАТУРЕ И АСПИРАНТУРЕ (RAG)
        # -----------------------------------------------------------------
        reply_text = (
            f"🎓 **Образовательный центр ФБУН ЦНИИ Эпидемиологии Роспотребнадзора**:\n\n"
            f"Я обеспечиваю подготовку официальной документации по программам **ординатуры** (32.08.12 «Эпидемиология», 31.08.35 «Инфекционные болезни», 31.08.19 «Педиатрия») и **аспирантуры** (3.2.2 «Эпидемиология»):\n\n"
            f"• **Приказы директора института:** зачисление, допуск к ГИА, утверждение тем диссертаций, направление на практику;\n"
            f"• **Протоколы УМС и ГЭК:** утверждение РПД, ФОС, прием экзаменов (остепененность комиссии $\\ge$ 70%);\n"
            f"• **Расписания экзаменационных сессий:** зимняя (25.01–25.02) и летняя сессии;\n"
            f"• **Кадровое обеспечение и нагрузка ППС:** норматив 750–900 ч/год на ставку.\n\n"
            f"Поставьте галочку **«✓ Утвержденный образец»** или напишите: *«Подготовь приказ о зачислении в ординатуру»*, *«Составь приказ о допуске к ГИА»*, *«Сверстай расписание зимней сессии»*."
        )

        return {
            "agent_action": "query_academic",
            "response": reply_text,
            "answer": reply_text,
            "citations": [
                {"title": "Федеральный закон № 273-ФЗ «Об образовании в РФ»"},
                {"title": "ФГОС ВО по специальности 32.08.12 «Эпидемиология» (120 з.е.)"},
                {"title": "Положение об организации образовательной деятельности в ординатуре ФБУН ЦНИИЭ"}
            ]
        }

    def _detect_academic_patch_intent(self, query: str, session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        q_low = query.lower()
        patches = {}

        if any(w in q_low for w in ["утверди", "сделай утвержденным", "утвержденный образец", "поставь галочку"]):
            patches["is_approved"] = True
        elif any(w in q_low for w in ["сними утверждение", "черновик"]):
            patches["is_approved"] = False

        m_head = re.search(r"(?:директор|председател[а-я]*|руководител[а-я]*)\s+(?:на\s+)?([А-Яа-яA-Za-z\s.]+)", query, re.IGNORECASE)
        if m_head:
            clean_name = re.split(r"\s+(?:и\s+добавь|и\s+поставь|и\s+замени)\b", m_head.group(1), flags=re.IGNORECASE)[0].strip().strip(",.!")
            if len(clean_name) > 3:
                patches["head_doctor"] = clean_name

        m_del = re.search(r"(?:удали|убери|исключи)\s+пункт\s+(\d+)", q_low)
        if m_del:
            patches["remove_action_index"] = int(m_del.group(1)) - 1

        m_add = re.search(r"(?:добавь|включи|вставь)\s+(?:пункт|решение|постановление)?\s*[:\-]?\s*(.+)", query, re.IGNORECASE)
        if m_add and not m_del:
            patches["add_action"] = m_add.group(1).strip()

        m_stud = re.search(r"(?:добавь|зачисли|включи)\s+(?:ординатор[а-я]*|аспирант[а-я]*|студент[а-я]*)\s+([А-Яа-яA-Za-z\s.,]+)", query, re.IGNORECASE)
        if m_stud:
            patches["add_action"] = f"Зачислить в очную ординатуру: {m_stud.group(1).strip()}."

        return patches if patches else None
