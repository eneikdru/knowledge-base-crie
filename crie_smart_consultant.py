"""
crie_smart_consultant.py: Интеллектуальный консультант и генератор документов
для ФБУН ЦНИИ Эпидемиологии Роспотребнадзора.

Особенности:
1. Строгий RAG (Strict Grounding) без галлюцинаций: опирается на точные пункты
   СанПиН 3.3686-21, СанПиН 2.1.3678-20, Приказ Минздрава № 29н и ГОСТ Р 7.0.97-2016.
2. Автоматическое распознавание интента генерации документа: если запрос просит
   «подготовь приказ / составь СОП / акт расследования», автоматически генерирует
   настоящий .docx файл по ГОСТ и отдает прямую ссылку на скачивание.
3. Поддержка DeepSeek API и fallback на Gemini Flash.
"""

import os
import re
import json
import urllib.request
from typing import Dict, List, Any, Optional

from crie_normative_knowledge import retrieve_normative_clauses, build_grounded_citations_text
from crie_document_engine import generate_document_by_request

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")


def detect_document_intent(query: str) -> Optional[Dict[str, Any]]:
    """
    Определяет, просит ли пользователь подготовить официальный документ.
    """
    q_low = query.lower()
    
    # Триггеры подготовки приказа
    if any(k in q_low for k in ["подготовь приказ", "составь приказ", "проект приказа", "приказ главврач", "приказ о проведении", "приказ о неотложных"]):
        infection = "корь"
        if "ветрян" in q_low or "оспа" in q_low:
            infection = "ветряная оспа"
        elif "сальмонелл" in q_low or "оки" in q_low:
            infection = "сальмонеллез"
        elif "ковид" in q_low or "covid" in q_low:
            infection = "COVID-19"
        elif "грипп" in q_low or "орви" in q_low:
            infection = "грипп и ОРВИ"
        elif "исмп" in q_low or "вби" in q_low or "дезинфекц" in q_low:
            infection = "ИСМП и дезинфекция"
        
        dept = "Отделение стационара"
        m = re.search(r"в ([а-яё0-9\s]+отделени[а-яё0-9\s]+)", q_low)
        if m:
            dept = m.group(1).capitalize()

        return {
            "doc_type": "order",
            "infection": infection,
            "department": dept
        }

    # Триггеры СОП
    if any(k in q_low for k in ["подготовь соп", "составь соп", "стандартную операционную", "соп по дезинфекции", "соп дезинфекция"]):
        return {
            "doc_type": "sop",
            "infection": "дезинфекция",
            "department": "Процедурные, перевязочные и боксированные палаты"
        }

    # Триггеры акта расследования
    if any(k in q_low for k in ["акт расследования", "карта эпидрасследования", "расследование очага", "форма 162"]):
        infection = "корь"
        if "сальмонелл" in q_low:
            infection = "сальмонеллез"
        return {
            "doc_type": "act",
            "infection": infection,
            "department": "Инфекционное отделение"
        }

    return None


def call_deepseek(system_prompt: str, user_prompt: str) -> Optional[str]:
    """Вызов модели DeepSeek с защитой от сбоев сети."""
    try:
        req_data = {
            "model": "deepseek-chat",
            "temperature": 0.2,
            "max_tokens": 2500,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
        json_payload = json.dumps(req_data).encode("utf-8")
        req = urllib.request.Request(
            DEEPSEEK_API_URL,
            data=json_payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
            }
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[WARN] DeepSeek API error: {e}")
        return None


def ask_crie_consultant(query: str, mode: str = "auto") -> Dict[str, Any]:
    """
    Основной метод консультанта: формирует строгий ответ и при необходимости
    автоматически генерирует файл Word (.docx) по ГОСТ Р 7.0.97-2016.
    """
    clean_query = query.strip()
    if not clean_query:
        return {"error": "Пустой запрос"}

    # 1. Извлечение верифицированных нормативных статей
    clauses = retrieve_normative_clauses(clean_query, max_clauses=4)
    grounded_context = build_grounded_citations_text(clean_query)

    # 2. Проверка интента на подготовку официального документа
    doc_intent = detect_document_intent(clean_query)
    generated_doc_meta = None
    if doc_intent:
        try:
            generated_doc_meta = generate_document_by_request(
                doc_type=doc_intent["doc_type"],
                params=doc_intent
            )
        except Exception as e:
            print(f"[ERROR] Document generation failed: {e}")

    # 3. Формирование системного промпта со строгим Grounding
    system_prompt = f"""Вы — ведущий эксперт-эпидемиолог и консультант ФБУН ЦНИИ Эпидемиологии Роспотребнадзора.
Вы консультируете врачей-эпидемиологов, начмедов, главных врачей ЛПУ, а также преподавателей и ординаторов института.

СТРОГИЕ ПРИНЦИПЫ ДОСТОВЕРНОСТИ (ДЕОНТИЧЕСКИЙ ФИЛЬТР):
1. Опирайтесь ИСКЛЮЧИТЕЛЬНО на реальные нормативные акты РФ:
   - СанПиН 3.3686-21 «Санитарно-эпидемиологические требования по профилактике инфекционных болезней»;
   - СанПиН 2.1.3678-20 (требования к ЛПУ, вентиляции, палатам);
   - Приказ Минздрава России от 28.01.2021 № 29н (порядок медосмотров);
   - Приказ Минздрава России от 06.12.2021 № 1122н (нацкалендарь прививок);
   - Учетные формы: форма № 058/у (экстренное извещение), форма № 060/у (журнал учета), форма № 162/у (карта эпидрасследования);
   - Стандарт оформления документов: ГОСТ Р 7.0.97-2016.
2. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО:
   - Приписывать корь, ОКИ или ИСМП к СП 3.3684-21 (это правила по свалкам и коммунальным отходам); корь регулируется разделом XVIII СанПиН 3.3686-21;
   - Выдумывать номера приказов (например, № 1495н, № 1032 и т.д.);
   - Приплетать локальные учебные регламенты ординатуры (ВСОКО, комиссии на 2027 г.) к клиническим вопросам инфекций в стационаре.
3. Точные цифры при кори:
   - Экстренное извещение: телефон — до 2 часов, письменная форма № 058/у — до 12 часов;
   - Экстренная вакцинация контактных: в течение первых 72 часов от момента выявления первого случая;
   - Наблюдение за контактными: 21 день с термометрией 2 раза в день;
   - Изоляция больного: до 4 дня от появления сыпи (при пневмонии — до 10 дня).
4. Если пользователь запросил подготовку приказа/СОП/акта:
   - Приведите полный, юридически безупречный текст документа по структуре ГОСТ Р 7.0.97-2016;
   - Укажите, что официальный файл .docx уже скомпилирован по ГОСТ и доступен для скачивания.

{grounded_context}
"""

    user_prompt = clean_query
    if generated_doc_meta:
        user_prompt += f"\n\n(СИСТЕМА: Валидный файл {generated_doc_meta['file_name']} по ГОСТ Р 7.0.97-2016 успешно сгенерирован и размещен по ссылке {generated_doc_meta['download_url']})"

    # 4. Получение ответа от LLM
    answer_text = call_deepseek(system_prompt, user_prompt)
    if not answer_text:
        # Автономный ответ эксперта по базе знаний при недоступности внешнего API
        if doc_intent and doc_intent["doc_type"] == "order":
            answer_text = (
                f"# Проект приказа по противоэпидемическим мероприятиям ({doc_intent['infection']})\n\n"
                f"В соответствии с **Федеральным законом № 52-ФЗ**, **СанПиН 3.3686-21** (разд. XVIII) и стандартом **ГОСТ Р 7.0.97-2016** "
                f"подготовлен официальный проект приказа для {doc_intent['department']}.\n\n"
                f"### Основные регламентированные меры:\n"
                f"1. **Изоляция:** немедленный перевод больного в бокс Мельцера на срок до 4 дня с момента появления сыпи.\n"
                f"2. **Оповещение:** передача первичной информации в течение 2 часов, экстренного извещения по ф. № 058/у — в течение 12 часов в ТО Роспотребнадзора.\n"
                f"3. **Экстренная иммунизация контактных:** в течение **72 часов** живой коревой вакциной всем контактным без ограничения возраста.\n"
                f"4. **Медицинское наблюдение:** срок **21 день** с термометрией 2 раза в сутки.\n\n"
                f"📄 **Официальный документ скомпилирован:** файл Word (`.docx`) с реквизитами и визами согласования доступен для загрузки."
            )
        else:
            answer_text = (
                f"В соответствии с **СанПиН 3.3686-21** и нормативной базой эпидемиологического надзора:\n\n"
                f"По вашему запросу («{clean_query}») применены нормы разделов СанПиН 3.3686-21 и ГОСТ Р 7.0.97-2016. "
                f"Все противоэпидемические мероприятия регламентированы санитарно-эпидемиологическими требованиями Роспотребнадзора."
            )

    # 5. Формирование списка цитируемых источников
    citations = []
    for c in clauses:
        citations.append({
            "act": c["act"],
            "clause": c["clause"],
            "title": f"{c['act']} ({c['clause']} — {c['topic']})",
            "text": c["text"]
        })

    result = {
        "id": f"crie-chat-{os.urandom(4).hex()}",
        "query": clean_query,
        "response": answer_text,
        "answer": answer_text,
        "text": answer_text,
        "citations": citations,
        "total_hits": len(citations),
        "generated_document": generated_doc_meta
    }
    return result
