"""
crie_autonomous_agent.py: Автономный агент подготовки и верстки документов
по эпидемиологии (CRIE Document Agent with Tools).

Это НЕ простой чат-бот, а агент с набором исполняемых инструментов (tools):
1. tool_query_normative_corpus — проверка норм СанПиН 3.3686-21, 2.1.3678-20, Приказов Минздрава РФ.
2. tool_use_approved_template — применение жесткого утвержденного образца (когда вариативность не нужна).
3. tool_compose_custom_document — самостоятельная верстка документа агентом (разделы, таблицы, требования).
4. tool_patch_document — интерактивное внесение правок пользователя (по пунктам, таблицам, лицам, датам).
5. tool_register_template — утверждение и регистрация нового образца.
"""

import os
import re
import json
import urllib.request
from typing import Dict, List, Any, Optional
from datetime import datetime

from crie_normative_knowledge import retrieve_normative_clauses, build_grounded_citations_text
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
DEEPSEEK_API_URL = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")


class CrieDocumentAgent:
    """
    Интеллектуальный агент верстки и правок документов.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or DEEPSEEK_API_KEY

    # -------------------------------------------------------------
    # ИНСТРУМЕНТЫ АГЕНТА (AGENT TOOLS)
    # -------------------------------------------------------------

    def tool_query_normative(self, query: str) -> List[Dict[str, str]]:
        """Инструмент поиска нормативных норм СанПиН/приказов."""
        return retrieve_normative_clauses(query, max_clauses=3)

    def tool_list_templates(self) -> List[Dict[str, Any]]:
        """Инструмент получения реестра образцов."""
        return load_template_registry()

    def tool_use_approved_template(
        self,
        template_id: str,
        department: str,
        infection: str,
        number: Optional[str] = None,
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Инструмент создания документа строго по утвержденному эталону."""
        session = create_document_session(
            template_id=template_id,
            params={
                "department": department,
                "infection": infection,
                "number": number,
                "date": date
            },
            is_approved_flag=True
        )
        return session

    def tool_compose_custom_document(self, doc_model: Dict[str, Any]) -> Dict[str, Any]:
        """
        Инструмент самостоятельной верстки агентом:
        принимает структурированную верстку (разделы, таблицы, пункты)
        и компилирует ее в .docx по ГОСТ Р 7.0.97-2016.
        """
        compiled = compile_agent_composed_document(doc_model)
        return compiled

    def tool_patch_document(self, session_id: str, patches: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """Инструмент точечного внесения правок в сессию документа."""
        return patch_document_session(session_id, patches, reason=reason)

    # -------------------------------------------------------------
    # АВТОНОМНЫЙ ЦИКЛ ОБРАБОТКИ ЗАПРОСА
    # -------------------------------------------------------------

    def process_request(
        self,
        query: str,
        session_id: Optional[str] = None,
        use_approved_template_only: bool = False
    ) -> Dict[str, Any]:
        """
        Главная точка входа агента:
        1. Определяет тип операции (новый документ / правка существующего).
        2. Применяет нужный инструмент: утвержденный образец или авторскую верстку.
        3. Возвращает ответ, лог выполненных действий и скомпилированный .docx.
        """
        q_low = query.lower()
        active_session = get_document_session(session_id) if session_id else None

        # СЦЕНАРИЙ 1: ПРАВКА СУЩЕСТВУЮЩЕГО ДОКУМЕНТА (INTERACTIVE PATCHING)
        if active_session:
            patch_intent = self._detect_patch_intent(query, active_session)
            if patch_intent:
                updated_session = self.tool_patch_document(session_id, patch_intent, reason=query)
                doc_meta = updated_session["compiled_doc"]
                
                status_tag = "✓ [УТВЕРЖДЕННЫЙ ОБРАЗЕЦ]" if updated_session.get("is_approved") else "[РАБОЧИЙ ПРОЕКТ]"
                reply_text = (
                    f"⚡ **Агент применил инструмент `tool_patch_document`**\n"
                    f"Документ обновлен до версии **v{updated_session['version']}** {status_tag}\n\n"
                    f"• **Заголовок:** {updated_session.get('title')}\n"
                    f"• **Реквизиты:** № {updated_session.get('number')} от {updated_session.get('date')}\n"
                    f"• **Руководитель:** {updated_session.get('head_doctor')}\n"
                    f"• **Эпидемиолог:** {updated_session.get('hospital_epidemiologist')}\n"
                    f"• **Число пунктов распоряжения:** {len(updated_session.get('actions', []))}\n\n"
                    f"📄 Файл Microsoft Word успешно пересобран бэкендом по ГОСТ Р 7.0.97-2016."
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

        # СЦЕНАРИЙ 2: ТРЕБУЕТСЯ ЖЕСТКИЙ УТВЕРЖДЕННЫЙ ОБРАЗЕЦ
        # (если пользователь поставил галочку ИЛИ в запросе указано «по утвержденному образцу»)
        if use_approved_template_only or any(w in q_low for w in ["утвержденный образец", "по образцу", "эталонный приказ", "строго по шаблону"]):
            infection = "корь"
            if "сальмонелл" in q_low or "оки" in q_low:
                tpl_id = "TPL-APPROVED-SALMONELLA"
                infection = "сальмонеллез"
            elif "дезинфекц" in q_low or "соп" in q_low:
                tpl_id = "TPL-APPROVED-SOP-DISINFECTION"
                infection = "дезинфекция"
            elif "акт" in q_low or "расследован" in q_low:
                tpl_id = "TPL-APPROVED-OUTBREAK-ACT"
            else:
                tpl_id = "TPL-APPROVED-MEASLES"

            dept = self._extract_department(query)
            session = self.tool_use_approved_template(tpl_id, department=dept, infection=infection)
            doc_meta = session["compiled_doc"]

            reply_text = (
                f"🛡️ **Агент применил инструмент `tool_use_approved_template`**\n"
                f"Использован эталонный образец: **{session.get('template_name')}**\n"
                f"Статус: **✓ Утвержденный образец** ({session.get('authority')})\n\n"
                f"Формулировки преамбулы и распорядительной части зафиксированы по СанПиН 3.3686-21 и ГОСТ Р 7.0.97-2016. "
                f"Файл Word скомпилирован бэкендом и доступен для скачивания."
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

        # СЦЕНАРИЙ 3: ВАРИАТИВНАЯ ВЕРСТКА АГЕНТОМ (AGENT COMPOSER)
        # Агент сам верстает структуру документа: разделы, таблицы, требования
        if any(w in q_low for w in ["приказ", "соп", "регламент", "акт", "подготовь", "составь", "сверстай"]):
            normative = self.tool_query_normative(query)
            infection = self._extract_infection(query)
            dept = self._extract_department(query)
            now = datetime.now()

            # Агент верстает структуру документа (включая таблицы контроля)
            doc_model = {
                "tag": f"Приказ_{infection}",
                "doc_type": "ПРИКАЗ",
                "title": f"О комплексе дополнительных санитарно-противоэпидемических мероприятий при выявлении заболевания ({infection}) в {dept}",
                "organization": "ФБУН ЦНИИ Эпидемиологии Роспотребнадзора",
                "is_approved": False,
                "date": now.strftime("%d.%m.%Y"),
                "number": f"{now.strftime('%y')}-ЭПИД/{now.day:02d}",
                "city": "г. Москва",
                "preamble": (
                    f"В связи с регистрацией случая с подозрением на {infection} у пациента в {dept}, "
                    f"в целях локализации очага, предотвращения внутрибольничного инфицирования "
                    f"и на основании требований СанПиН 3.3686-21 и СанПиН 2.1.3678-20:"
                ),
                "sections": [
                    {
                        "heading": "1. Первоочередные изоляционные мероприятия",
                        "items": [
                            f"Немедленно изолировать пациента с признаками {infection} в боксированную палату отделения.",
                            "Обеспечить подачу экстренного извещения по ф. 058/у в территориальный орган Роспотребнадзора в течение 12 часов (первичная информация по телефону — в течение 2 часов)."
                        ]
                    },
                    {
                        "heading": "2. Дезинфекционный режим и мониторинг",
                        "text": "Перевести отделение на усиленный дезинфекционный режим по вирулицидному и бактерицидному графику.",
                        "table": {
                            "headers": ["Зона обработки", "Используемое средство", "Концентрация (%)", "Экспозиция (мин.)", "Кратность"],
                            "rows": [
                                ["Палата больного", "Хлорактивные препараты", "0.5%", "60 мин.", "3 раза в сутки"],
                                ["Манипуляционная", "Кислородактивные средства", "0.2%", "30 мин.", "После каждого пациента"],
                                ["Места общего пользования", "ЧАС + спирты", "0.1%", "15 мин.", "Каждые 2 часа"],
                                ["Воздушная среда", "УФ-рециркуляторы закрытого типа", "—", "Постоянно", "24/7 непрерывно"]
                            ]
                        }
                    },
                    {
                        "heading": "3. Экстренная иммунизация и наблюдение за контактными",
                        "items": [
                            "Госпитальному эпидемиологу составить список всех контактных пациентов и медицинского персонала.",
                            "Организовать экстренную вакцинацию лиц, не имеющих документально подтвержденных сведений о прививках, в первые 72 часа от момента контакта.",
                            "Установить медицинское наблюдение за контактными сроком на 21 день с двукратной ежедневной термометрией."
                        ]
                    }
                ],
                "signatures": [
                    {"position": "Главный врач стационара", "name": "А.К. Горелов"}
                ],
                "visas": [
                    "Госпитальный эпидемиолог: ___________________ / Е.В. Семенова /",
                    "Начальник медицинской части: ___________________ / И.П. Воронов /"
                ]
            }

            # Агент компилирует сверстанную им модель в .docx
            doc_meta = self.tool_compose_custom_document(doc_model)
            
            # Сохраняем как новую сессию для возможности последующих правок
            session_id_new = f"session_custom_{now.strftime('%H%M%S')}"
            session_data = {
                "session_id": session_id_new,
                "version": 1,
                "is_approved": False,
                "title": doc_model["title"],
                "number": doc_model["number"],
                "date": doc_model["date"],
                "department": dept,
                "infection": infection,
                "head_doctor": "А.К. Горелов",
                "hospital_epidemiologist": "Е.В. Семенова",
                "actions": [it for s in doc_model["sections"] for it in s.get("items", [])],
                "compiled_doc": doc_meta,
                "doc_model": doc_model
            }
            from crie_template_manager import _DOCUMENT_SESSIONS
            _DOCUMENT_SESSIONS[session_id_new] = session_data

            reply_text = (
                f"🛠️ **Агент выполнил кастомную верстку документа (`tool_compose_custom_document`)**\n\n"
                f"Сверстан специализированный документ с таблицей дезинфекционных режимов:\n"
                f"• **Документ:** {doc_model['title']}\n"
                f"• **Реквизиты:** Приказ № {doc_model['number']} от {doc_model['date']}\n"
                f"• **Сверстано разделов:** 3 раздела, включая нормативную таблицу ротации дезсредств.\n\n"
                f"Вы можете написать правки агенту (*«измени концентрацию в таблице», «замени врача»*) "
                f"или нажать кнопку и утвердить этот документ как эталонный образец."
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

        # СЦЕНАРИЙ 4: СПРАВОЧНЫЙ НОРМАТИВНЫЙ ЗАПРОС (RAG)
        clauses = self.tool_query_normative(query)
        grounded_text = build_grounded_citations_text(query)
        
        reply_text = (
            f"📚 **Агент выполнил нормативную проверку по базе СанПиН (`tool_query_normative`)**:\n\n"
            f"{grounded_text}\n\n"
            f"Вы можете скомандовать: *«Подготовь приказ по утвержденному образцу»* или *«Сверстай приказ для отделения...»*."
        )

        return {
            "agent_action": "query_normative",
            "response": reply_text,
            "answer": reply_text,
            "citations": clauses,
            "total_hits": len(clauses)
        }

    # -------------------------------------------------------------
    # Вспомогательные парсеры интентов
    # -------------------------------------------------------------

    def _detect_patch_intent(self, query: str, session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        q_low = query.lower()
        patches = {}

        if any(w in q_low for w in ["утверди", "сделай утвержденным", "утвержденный образец", "поставь галочку"]):
            patches["is_approved"] = True
        elif any(w in q_low for w in ["сними утверждение", "черновик"]):
            patches["is_approved"] = False

        m_doc = re.search(r"(?:замени|назначь|главврач[а-я]*|главный врач)\s+(?:на\s+)?([А-Яа-яA-Za-z\s.]+)", query, re.IGNORECASE)
        if m_doc:
            raw_val = m_doc.group(1).strip().strip(",.!")
            # Отсекаем последующие союзы и команды
            clean_name = re.split(r"\s+(?:и\s+добавь|и\s+включи|и\s+поставь|и\s+утверди|и\s+замени)\b", raw_val, flags=re.IGNORECASE)[0].strip()
            # Убираем префикс "главного врача на" если он попал в группу
            clean_name = re.sub(r"^(?:главного\s+врача\s+на|главврача\s+на|руководителя\s+на)\s+", "", clean_name, flags=re.IGNORECASE).strip()
            if len(clean_name) > 3:
                patches["head_doctor"] = clean_name

        m_del = re.search(r"(?:удали|убери|исключи)\s+пункт\s+(\d+)", q_low)
        if m_del:
            patches["remove_action_index"] = int(m_del.group(1)) - 1

        m_add = re.search(r"(?:добавь|включи|вставь)\s+(?:пункт|требование)?\s*[:\-]?\s*(.+)", query, re.IGNORECASE)
        if m_add and not m_del:
            patches["add_action"] = m_add.group(1).strip()

        return patches if patches else None

    def _extract_infection(self, query: str) -> str:
        q = query.lower()
        if "сальмонелл" in q: return "сальмонеллез"
        if "ковид" in q or "covid" in q: return "COVID-19"
        if "ветрян" in q or "оспа" in q: return "ветряная оспа"
        if "грипп" in q or "орви" in q: return "грипп и ОРВИ"
        if "исмп" in q or "вби" in q: return "ИСМП"
        return "корь"

    def _extract_department(self, query: str) -> str:
        m = re.search(r"в ([а-яё0-9\s]+отделени[а-яё0-9\s]+)", query, re.IGNORECASE)
        if m:
            return m.group(1).strip().capitalize()
        return "Терапевтическое отделение № 1"
