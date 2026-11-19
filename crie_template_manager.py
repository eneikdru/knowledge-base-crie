"""
crie_template_manager.py: Менеджер утвержденных образцов и сессий документов
ОБРАЗОВАТЕЛЬНОГО ЦЕНТРА (Ординатура и Аспирантура) ФБУН ЦНИИ Эпидемиологии Роспотребнадзора.

Специальности ординатуры: 32.08.12 «Эпидемиология», 31.08.35 «Инфекционные болезни», 31.08.19 «Педиатрия» (120 з.е. / 4320 ч.).
Аспирантура: 3.2.2 «Эпидемиология», 3.1.22 «Инфекционные болезни».
Нормативная основа: Федеральный закон № 273-ФЗ, Приказы Минобрнауки РФ, локальные акты ЦНИИЭ, ГОСТ Р 7.0.97-2016.
"""

import os
import re
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import quote

import docx

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "templates"
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR = DATA_DIR / "uploaded"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR = BASE_DIR / "generated_documents"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

REGISTRY_FILE = DATA_DIR / "template_registry_extended.json"

_DOCUMENT_SESSIONS: Dict[str, Dict[str, Any]] = {}

DEFAULT_APPROVED_TEMPLATES = [
    {
        "id": "TPL-APPROVED-ADMISSION-RESIDENCY",
        "name": "Приказ о зачислении в ординатуру (32.08.12 Эпидемиология / 31.08.35 Инфекционные болезни)",
        "category": "Приемная кампания и зачисление",
        "authority": "Утвержден Директором ФБУН ЦНИИЭ Роспотребнадзора, академиком РАН",
        "standard": "ГОСТ Р 7.0.97-2016",
        "basis": "ФЗ № 273-ФЗ «Об образовании в РФ», протокол Приемной комиссии",
        "is_approved": True,
        "preamble_template": "В соответствии с Федеральным законом от 29.12.2012 № 273-ФЗ «Об образовании в Российской Федерации», Порядком приема на обучение по образовательным программам высшего образования — программам ординатуры и на основании решения Приемной комиссии (протокол от {date} № {number}):",
        "default_actions": [
            "Зачислить с 01 сентября 2026 года в очную ординатуру Образовательного центра ФБУН ЦНИИ Эпидемиологии Роспотребнадзора по специальности 32.08.12 «Эпидемиология» на места в рамках контрольных цифр приема (бюджетная основа) следующих поступающих, успешно прошедших вступительные испытания: {students_list}.",
            "Начальнику Учебно-методического отдела сформировать личные дела зачисленных ординаторов и выдать служебные удостоверения и зачетные книжки установленного образца до 05 сентября 2026 г.",
            "Заведующему кафедрой эпидемиологии и доказательной медицины закрепить за каждым ординатором куратора из числа профессорско-преподавательского состава (с ученой степенью не ниже кандидата медицинских наук).",
            "Ординаторам 1 года обучения явиться на организационное собрание и утвердить индивидуальные учебные планы до 15 сентября 2026 г.",
            "Контроль за исполнением настоящего приказа возложить на руководителя Образовательного центра института."
        ],
        "default_head": "Директор ФБУН ЦНИИЭ Роспотребнадзора, академик РАН",
        "default_curator": "Руководитель Образовательного центра",
        "signatures": [
            {"position": "Директор ФБУН ЦНИИЭ, академик РАН", "name": "В.Г. Акимкин"}
        ],
        "visas": [
            "Руководитель Образовательного центра: ___________________ / А.В. Горелов /",
            "Начальник Учебно-методического отдела: ___________________ / О.Н. Климова /",
            "Начальник юридического отдела: ___________________ / С.Ю. Васильева /"
        ]
    },
    {
        "id": "TPL-APPROVED-GIA-ADMISSION",
        "name": "Приказ о допуске ординаторов выпускного курса к Государственной итоговой аттестации (ГИА)",
        "category": "Итоговая аттестация (ГИА)",
        "authority": "Утвержден Учебно-методическим советом и Директором института",
        "standard": "ГОСТ Р 7.0.97-2016",
        "basis": "ФЗ № 273-ФЗ, Положение о ГИА в ординатуре ФБУН ЦНИИЭ",
        "is_approved": True,
        "preamble_template": "В соответствии с Федеральным законом «Об образовании в РФ» № 273-ФЗ, Положением о порядке проведения Государственной итоговой аттестации по программам ординатуры ФБУН ЦНИИ Эпидемиологии Роспотребнадзора и на основании выполнения ординаторами в полном объеме учебного плана (120 з.е. / 4 320 ч.):",
        "default_actions": [
            "Допустить к прохождению Государственной итоговой аттестации (ГИА) в 2026/2027 учебном году по специальности 32.08.12 «Эпидемиология» ординаторов 2 года обучения, полностью выполнивших учебный план и сдавшим все зачеты и экзамены промежуточной аттестации: {students_list}.",
            "Утвердить график проведения 3 этапов ГИА:\n   1 этап: Компьютерное тестирование — 20 июня 2027 г. (допуск: не менее 70% верных ответов);\n   2 этап: Оценка практических навыков в симуляционном центре — 22 июня 2027 г.;\n   3 этап: Собеседование по билетам и ситуационным задачам ГЭК — 25 июня 2027 г.",
            "Секретарю Государственной экзаменационной комиссии подготовить протоколы ГИА и бланки дипломов об окончании ординатуры.",
            "Контроль исполнения настоящего приказа возложить на председателя Учебно-методического совета."
        ],
        "default_head": "Директор института, академик РАН",
        "default_curator": "Председатель ГЭК",
        "signatures": [
            {"position": "Директор ФБУН ЦНИИЭ, академик РАН", "name": "В.Г. Акимкин"}
        ],
        "visas": [
            "Председатель УМС, член-корр. РАН: ___________________ / А.В. Горелов /",
            "Секретарь ГЭК: ___________________ / Е.В. Семенова /"
        ]
    },
    {
        "id": "TPL-APPROVED-UMS-PROTOCOL",
        "name": "Протокол заседания Учебно-методического совета (УМС) института",
        "category": "Учебно-методическая работа",
        "authority": "Утвержден Учебно-методическим советом ФБУН ЦНИИЭ",
        "standard": "ГОСТ Р 7.0.97-2016",
        "basis": "Положение об УМС Образовательного центра ФБУН ЦНИИЭ",
        "is_approved": True,
        "preamble_template": "Заседание Учебно-методического совета института проведено в очно-дистанционном формате. Присутствовало: 14 из 16 членов УМС (доля лиц с учеными степенями — 87.5%). Кворум имеется.",
        "default_actions": [
            "СЛУШАЛИ: Отчет заведующего кафедрой эпидемиологии об актуализации рабочих программ дисциплин (РПД) и фондов оценочных средств (ФОС) ординатуры на 2026/2027 уч. год.",
            "ПОСТАНОВИЛИ: 1. Утвердить актуализированные РПД по специальности 32.08.12 «Эпидемиология» в объеме 120 з.е. (4 320 ч.).",
            "ПОСТАНОВИЛИ: 2. Одобрить график зимней экзаменационной сессии на период с 25 января по 25 февраля 2027 г.",
            "ПОСТАНОВИЛИ: 3. Рекомендовать к утверждению Директором института составы Государственных экзаменационных комиссий на 2027 год с соблюдением норматива остепененности преподавателей не менее 70%."
        ],
        "default_head": "Председатель УМС, зам. директора по научной работе",
        "default_curator": "Секретарь УМС",
        "signatures": [
            {"position": "Председатель УМС, профессор", "name": "А.В. Горелов"},
            {"position": "Ученый секретарь УМС", "name": "О.Н. Климова"}
        ]
    },
    {
        "id": "TPL-APPROVED-ASPIRANTURA-THEME",
        "name": "Приказ об утверждении тем диссертаций и научных руководителей аспирантов",
        "category": "Аспирантура и подготовка кадров высшей квалификации",
        "authority": "Утвержден Ученым советом и Директором ФБУН ЦНИИЭ",
        "standard": "ГОСТ Р 7.0.97-2016",
        "basis": "ФЗ № 273-ФЗ, решение Ученого совета института",
        "is_approved": True,
        "preamble_template": "В соответствии с Порядком подготовки научных и научно-педагогических кадров в аспирантуре ФБУН ЦНИИ Эпидемиологии Роспотребнадзора и на основании решения Ученого совета института (протокол от {date} № {number}):",
        "default_actions": [
            "Утвердить аспирантам очной формы обучения 1 года по научной специальности 3.2.2 «Эпидемиология» темы диссертационных работ на соискание ученой степени кандидата медицинских наук и назначить научных руководителей: {aspirants_list}.",
            "Аспирантам совместно с научными руководителями составить и представить на кафедру развернутые индивидуальные планы научной деятельности и план сдачи кандидатских экзаменов до 01 ноября 2026 г.",
            "Отделу аспирантуры обеспечить контроль прохождения полугодовой и годовой аттестации на заседаниях проблемных комиссий института.",
            "Контроль за исполнением настоящего приказа оставляю за собой."
        ],
        "default_head": "Директор ФБУН ЦНИИЭ, академик РАН",
        "default_curator": "Зав. отделом аспирантуры",
        "signatures": [
            {"position": "Директор ФБУН ЦНИИЭ, академик РАН", "name": "В.Г. Акимкин"}
        ],
        "visas": [
            "Заместитель директора по научной работе: ___________________ / А.В. Горелов /",
            "Заведующий отделом аспирантуры: ___________________ / Н.В. Попова /"
        ]
    },
    {
        "id": "TPL-APPROVED-PRACTICE-ORDER",
        "name": "Приказ о направлении ординаторов на производственную (клиническую) практику",
        "category": "Практическая подготовка",
        "authority": "Утвержден Директором Образовательного центра",
        "standard": "ГОСТ Р 7.0.97-2016",
        "basis": "ФГОС ВО 32.08.12, Положение о практической подготовке обучающихся",
        "is_approved": True,
        "preamble_template": "В соответствии с учебными планами ординатуры по специальности 32.08.12 «Эпидемиология» и Положением о практической подготовке обучающихся ФБУН ЦНИИЭ:",
        "default_actions": [
            "Направить ординаторов 1 и 2 годов обучения для прохождения производственной (клинической) практики в период с 10 февраля по 25 мая 2027 г. в профильные клинические и научные подразделения института: {departments_list}.",
            "Назначить руководителями практики от института ведущих научных сотрудников и профессоров кафедры.",
            "Ординаторам своевременно вести дневники практики и представить письменные отчеты с отзывом руководителя до 30 мая 2027 г.",
            "Учебному отделу провести промежуточную аттестацию по итогам практики с выставлением дифференцированного зачета."
        ],
        "default_head": "Руководитель Образовательного центра",
        "default_curator": "Руководитель практики",
        "signatures": [
            {"position": "Руководитель Образовательного центра", "name": "А.В. Горелов"}
        ],
        "visas": [
            "Заведующий кафедрой эпидемиологии: ___________________ / В.В. Малеев /",
            "Руководитель клинической базы: ___________________ / И.П. Воронов /"
        ]
    },
    {
        "id": "TPL-APPROVED-STAFFING-WORKLOAD",
        "name": "Справка о кадровом обеспечении кафедры и учебной нагрузке ППС",
        "category": "Лицензионный контроль и аккредитация",
        "authority": "Учебно-методический отдел Образовательного центра",
        "standard": "ГОСТ Р 7.0.97-2016",
        "basis": "ФГОС ВО 32.08.12 (норматив остепененности ППС не менее 70%)",
        "is_approved": True,
        "preamble_template": "Настоящая справка составлена Учебно-методическим отделом Образовательного центра ФБУН ЦНИИЭ в подтверждение соответствия кадрового обеспечения образовательных программ ординатуры требованиям ФГОС ВО:",
        "default_actions": [
            "Общая численность научно-педагогических работников (ППС), обеспечивающих преподавание дисциплин по программам ординатуры: 17 человек.",
            "Число преподавателей, имеющих ученую степень доктора или кандидата медицинских/биологических наук: 15 человек (остепененность кафедры — 88.2%, что полностью соответствует нормативу ФГОС ВО ≥ 70%).",
            "Средняя годовая учебная нагрузка на 1.0 ставку преподавателя кафедры составляет 800 часов (диапазон нормы 750–900 часов/год).",
            "Все преподаватели своевременно прошли повышение квалификации по профилю дисциплин и педагогике высшей школы в объеме не менее 72 часов."
        ],
        "default_head": "Начальник Учебно-методического отдела",
        "default_curator": "Специалист по кадрам ППС",
        "signatures": [
            {"position": "Начальник Учебно-методического отдела", "name": "О.Н. Климова"},
            {"position": "Заведующий кафедрой эпидемиологии, академик", "name": "В.В. Малеев"}
        ]
    }
]


def load_template_registry() -> List[Dict[str, Any]]:
    """Загружает реестр утвержденных образцов Образовательного центра."""
    if not REGISTRY_FILE.exists():
        save_template_registry(DEFAULT_APPROVED_TEMPLATES)
        return DEFAULT_APPROVED_TEMPLATES

    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            templates = data.get("templates", [])
            # Если база старая или пуста — обновляем на образовательные шаблоны
            if not templates or any(t.get("category") == "Госпитальная эпидемиология" for t in templates):
                templates = DEFAULT_APPROVED_TEMPLATES
                save_template_registry(templates)
            return templates
    except Exception as e:
        print(f"[WARN] Failed to read template registry: {e}")
        return DEFAULT_APPROVED_TEMPLATES


def save_template_registry(templates: List[Dict[str, Any]]):
    """Сохраняет реестр шаблонов."""
    try:
        with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump({"templates": templates, "updated_at": datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to save template registry: {e}")


def get_template_by_id(template_id: str) -> Optional[Dict[str, Any]]:
    registry = load_template_registry()
    for t in registry:
        if t["id"] == template_id:
            return t
    return None


def register_uploaded_template(
    file_bytes: bytes,
    original_filename: str,
    name: str,
    category: str = "Пользовательские образцы ОЦ",
    is_approved: bool = False,
    authority: str = "Образовательный центр ФБУН ЦНИИЭ"
) -> Dict[str, Any]:
    tpl_id = f"TPL-CUSTOM-{uuid.uuid4().hex[:8].upper()}"
    safe_name = f"{tpl_id}_{re.sub(r'[^a-zA-Zа-яА-Я0-9_.-]', '_', original_filename)}"
    saved_path = UPLOAD_DIR / safe_name

    with open(saved_path, "wb") as f:
        f.write(file_bytes)

    extracted_paragraphs = []
    try:
        doc = docx.Document(str(saved_path))
        for p in doc.paragraphs:
            txt = p.text.strip()
            if txt and len(txt) > 10:
                extracted_paragraphs.append(txt)
    except Exception as e:
        print(f"[WARN] Failed to parse uploaded docx: {e}")

    preamble = extracted_paragraphs[0] if extracted_paragraphs else "В соответствии с локальными актами Образовательного центра института:"
    actions = extracted_paragraphs[1:6] if len(extracted_paragraphs) > 1 else [
        "Обеспечить строгое выполнение учебного плана подготовки ординаторов/аспирантов.",
        "Назначить ответственных преподавателей за проведение промежуточной и итоговой аттестации.",
        "Контроль за исполнением настоящего документа возложить на руководителя ОЦ."
    ]

    new_tpl = {
        "id": tpl_id,
        "name": name or original_filename,
        "category": category,
        "authority": authority,
        "standard": "ГОСТ Р 7.0.97-2016",
        "basis": "Локальные акты Образовательного центра ЦНИИЭ",
        "is_approved": bool(is_approved),
        "file_path": str(saved_path),
        "original_filename": original_filename,
        "preamble_template": preamble,
        "default_actions": actions,
        "default_head": "Руководитель Образовательного центра",
        "default_curator": "Начальник учебного отдела",
        "uploaded_at": datetime.now().isoformat()
    }

    registry = load_template_registry()
    registry.append(new_tpl)
    save_template_registry(registry)
    return new_tpl


def create_document_session(
    template_id: str,
    params: Optional[Dict[str, Any]] = None,
    is_approved_flag: Optional[bool] = None
) -> Dict[str, Any]:
    tpl = get_template_by_id(template_id)
    if not tpl:
        tpl = DEFAULT_APPROVED_TEMPLATES[0]

    session_id = f"session_oc_{uuid.uuid4().hex[:12]}"
    now = datetime.now()
    p = params or {}

    order_num = p.get("number") or f"{now.strftime('%y')}-ОД/0{now.day}"
    order_date = p.get("date") or now.strftime("%d.%m.%Y")
    org_name = p.get("organization") or (
        "ФЕДЕРАЛЬНАЯ СЛУЖБА ПО НАДЗОРУ В СФЕРЕ ЗАЩИТЫ ПРАВ ПОТРЕБИТЕЛЕЙ И БЛАГОПОЛУЧИЯ ЧЕЛОВЕКА\n"
        "ФЕДЕРАЛЬНОЕ БЮДЖЕТНОЕ УЧРЕЖДЕНИЕ НАУКИ\n"
        "«ЦЕНТРАЛЬНЫЙ НАУЧНО-ИССЛЕДОВАТЕЛЬСКИЙ ИНСТИТУТ ЭПИДЕМИОЛОГИИ»\n"
        "ОБРАЗОВАТЕЛЬНЫЙ ЦЕНТР (ОРДИНАТУРА И АСПИРАНТУРА)"
    )

    specialty = p.get("specialty") or "32.08.12 «Эпидемиология»"
    students = p.get("students") or "Иванов И.И., Петров П.П., Сидорова А.С."
    dept = p.get("department") or "Кафедра эпидемиологии и доказательной медицины"

    preamble_raw = tpl.get("preamble_template", "")
    preamble = preamble_raw.replace("{date}", order_date).replace("{number}", order_num)

    actions = []
    for a in tpl.get("default_actions", []):
        act_formatted = (
            a.replace("{students_list}", students)
             .replace("{specialty}", specialty)
             .replace("{department}", dept)
             .replace("{departments_list}", f"Клинический отдел инфекционной патологии, лаборатория молекулярной эпидемиологии")
             .replace("{aspirants_list}", f"1. {students} — Тема: «Молекулярно-генетический мониторинг резистентности возбудителей», науч. рук. — академик РАН")
        )
        actions.append(act_formatted)

    approved_status = bool(is_approved_flag if is_approved_flag is not None else tpl.get("is_approved", True))

    doc_type_val = "ПРОТОКОЛ" if "ПРОТОКОЛ" in tpl["name"].upper() else ("СПРАВКА" if "СПРАВКА" in tpl["name"].upper() else "ПРИКАЗ")

    session_data = {
        "session_id": session_id,
        "version": 1,
        "template_id": tpl["id"],
        "template_name": tpl["name"],
        "doc_type": doc_type_val,
        "is_approved": approved_status,
        "authority": tpl.get("authority", "ФБУН ЦНИИЭ Роспотребнадзора"),
        "basis": tpl.get("basis", "ФЗ № 273-ФЗ «Об образовании в РФ»"),
        "standard": "ГОСТ Р 7.0.97-2016",
        "organization": org_name,
        "department": dept,
        "specialty": specialty,
        "number": order_num,
        "date": order_date,
        "city": "г. Москва",
        "title": p.get("title") or tpl["name"],
        "preamble": preamble,
        "actions": actions,
        "head_doctor": p.get("head") or tpl.get("default_head", "Директор института, академик РАН"),
        "hospital_epidemiologist": p.get("curator") or tpl.get("default_curator", "Руководитель Образовательного центра"),
        "signatures": tpl.get("signatures", [{"position": "Директор ФБУН ЦНИИЭ, академик РАН", "name": "В.Г. Акимкин"}]),
        "visas": tpl.get("visas", ["Руководитель Образовательного центра: ___________________ / А.В. Горелов /"]),
        "updated_at": now.isoformat(),
        "change_log": ["Документ Образовательного центра первично скомпилирован по утвержденному эталону."]
    }

    compiled_meta = compile_session_to_docx(session_data)
    session_data["compiled_doc"] = compiled_meta
    _DOCUMENT_SESSIONS[session_id] = session_data
    return session_data


def get_document_session(session_id: str) -> Optional[Dict[str, Any]]:
    return _DOCUMENT_SESSIONS.get(session_id)


def patch_document_session(
    session_id: str,
    patches: Dict[str, Any],
    reason: str = "Правка пользователя через агента ОЦ"
) -> Dict[str, Any]:
    session = _DOCUMENT_SESSIONS.get(session_id)
    if not session:
        session = create_document_session("TPL-APPROVED-ADMISSION-RESIDENCY", params=patches)
        session_id = session["session_id"]

    session["version"] += 1
    session["updated_at"] = datetime.now().isoformat()

    if "is_approved" in patches:
        session["is_approved"] = bool(patches["is_approved"])
    if "title" in patches and patches["title"]:
        session["title"] = str(patches["title"]).strip()
    if "department" in patches and patches["department"]:
        session["department"] = str(patches["department"]).strip()
    if "specialty" in patches and patches["specialty"]:
        session["specialty"] = str(patches["specialty"]).strip()
    if "date" in patches and patches["date"]:
        session["date"] = str(patches["date"]).strip()
    if "number" in patches and patches["number"]:
        session["number"] = str(patches["number"]).strip()
    if "head_doctor" in patches and patches["head_doctor"]:
        session["head_doctor"] = str(patches["head_doctor"]).strip()
    if "hospital_epidemiologist" in patches and patches["hospital_epidemiologist"]:
        session["hospital_epidemiologist"] = str(patches["hospital_epidemiologist"]).strip()
    if "preamble" in patches and patches["preamble"]:
        session["preamble"] = str(patches["preamble"]).strip()

    if "actions" in patches and isinstance(patches["actions"], list):
        session["actions"] = [str(a).strip() for a in patches["actions"] if str(a).strip()]
    if "add_action" in patches and patches["add_action"]:
        session["actions"].append(str(patches["add_action"]).strip())
    if "remove_action_index" in patches:
        idx = int(patches["remove_action_index"])
        if 0 <= idx < len(session["actions"]):
            session["actions"].pop(idx)

    session["change_log"].append(f"v{session['version']}: {reason}")

    compiled_meta = compile_session_to_docx(session)
    session["compiled_doc"] = compiled_meta
    _DOCUMENT_SESSIONS[session_id] = session
    return session


def compile_session_to_docx(session: Dict[str, Any]) -> Dict[str, Any]:
    from crie_document_engine import (
        create_base_document,
        add_gost_header,
        Mm, Pt, RGBColor,
        WD_ALIGN_PARAGRAPH,
        WD_TABLE_ALIGNMENT
    )

    doc = create_base_document()
    add_gost_header(doc, session.get("organization"))

    # Пометка «Утвержденный эталонный образец»
    if session.get("is_approved"):
        p_app = doc.add_paragraph()
        p_app.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_app.paragraph_format.space_after = Pt(8)
        p_app.paragraph_format.line_spacing = 1.0
        r_app = p_app.add_run(
            f"✓ УТВЕРЖДЕННЫЙ ЭТАЛОННЫЙ ОБРАЗЕЦ\n"
            f"{session.get('authority', 'ФБУН ЦНИИЭ Роспотребнадзора')}\n"
            f"Основание: {session.get('basis', 'ФЗ № 273-ФЗ')} | Стандарт: {session.get('standard', 'ГОСТ Р 7.0.97-2016')}\n"
        )
        r_app.font.name = 'Times New Roman'
        r_app.font.size = Pt(9)
        r_app.font.bold = True
        r_app.font.color.rgb = RGBColor(0, 100, 0)

    # Вид документа
    doc_type_val = session.get("doc_type", "ПРИКАЗ").upper()
    p_t = doc.add_paragraph()
    p_t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_t.paragraph_format.space_before = Pt(6)
    p_t.paragraph_format.space_after = Pt(10)
    rt = p_t.add_run(doc_type_val)
    rt.font.name = 'Times New Roman'
    rt.font.size = Pt(16)
    rt.font.bold = True

    # Реквизиты
    tbl_m = doc.add_table(rows=1, cols=2)
    tbl_m.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_m.columns[0].width = Mm(80)
    tbl_m.columns[1].width = Mm(85)
    
    cl = tbl_m.cell(0, 0)
    pl = cl.paragraphs[0]
    pl.paragraph_format.space_after = Pt(0)
    rl = pl.add_run(f"Дата: {session.get('date', datetime.now().strftime('%d.%m.%Y'))}")
    rl.font.name = 'Times New Roman'
    rl.font.size = Pt(12)

    cr = tbl_m.cell(0, 1)
    pr = cr.paragraphs[0]
    pr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    pr.paragraph_format.space_after = Pt(0)
    rr = pr.add_run(f"№ {session.get('number', '1-ОД')}\n{session.get('city', 'г. Москва')}")
    rr.font.name = 'Times New Roman'
    rr.font.size = Pt(12)

    # Заголовок
    p_subj = doc.add_paragraph()
    p_subj.paragraph_format.space_before = Pt(16)
    p_subj.paragraph_format.space_after = Pt(10)
    p_subj.paragraph_format.first_line_indent = Mm(12.5)
    p_subj.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r_subj = p_subj.add_run(session.get("title", "Официальный документ Образовательного центра"))
    r_subj.font.name = 'Times New Roman'
    r_subj.font.size = Pt(13)
    r_subj.font.bold = True

    # Преамбула
    if session.get("preamble"):
        p_pre = doc.add_paragraph()
        p_pre.paragraph_format.first_line_indent = Mm(12.5)
        p_pre.paragraph_format.space_after = Pt(10)
        p_pre.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        r_pre = p_pre.add_run(session.get("preamble"))
        r_pre.font.name = 'Times New Roman'
        r_pre.font.size = Pt(12)

    # Распорядительное слово
    if "ПРИКАЗ" in doc_type_val:
        p_cmd = doc.add_paragraph()
        p_cmd.paragraph_format.space_before = Pt(4)
        p_cmd.paragraph_format.space_after = Pt(6)
        p_cmd.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rcmd = p_cmd.add_run("ПРИКАЗЫВАЮ:")
        rcmd.font.name = 'Times New Roman'
        rcmd.font.size = Pt(13)
        rcmd.font.bold = True
    elif "ПРОТОКОЛ" in doc_type_val:
        p_cmd = doc.add_paragraph()
        p_cmd.paragraph_format.space_before = Pt(4)
        p_cmd.paragraph_format.space_after = Pt(6)
        p_cmd.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rcmd = p_cmd.add_run("ПОВЕСТКА ДНЯ И РЕШЕНИЯ:")
        rcmd.font.name = 'Times New Roman'
        rcmd.font.size = Pt(13)
        rcmd.font.bold = True

    # Пункты
    for idx, act in enumerate(session.get("actions", []), 1):
        p_act = doc.add_paragraph()
        p_act.paragraph_format.first_line_indent = Mm(12.5)
        p_act.paragraph_format.space_after = Pt(5)
        p_act.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        prefix = f"{idx}. " if not act.strip().startswith(f"{idx}.") and not act.strip().startswith("СЛУШАЛИ") and not act.strip().startswith("ПОСТАНОВИЛИ") else ""
        ract = p_act.add_run(f"{prefix}{act}")
        ract.font.name = 'Times New Roman'
        ract.font.size = Pt(12)

    # Таблицы (если есть)
    if session.get("doc_model") and session["doc_model"].get("sections"):
        for sec in session["doc_model"]["sections"]:
            if sec.get("table") and sec["table"].get("headers"):
                headers = sec["table"]["headers"]
                rows = sec["table"]["rows"]
                t_elem = doc.add_table(rows=len(rows)+1, cols=len(headers))
                t_elem.alignment = WD_TABLE_ALIGNMENT.CENTER
                for c_idx, h in enumerate(headers):
                    t_elem.cell(0, c_idx).paragraphs[0].add_run(h).font.bold = True
                for r_idx, r_data in enumerate(rows, 1):
                    for c_idx, val in enumerate(r_data[:len(headers)]):
                        t_elem.cell(r_idx, c_idx).paragraphs[0].add_run(str(val))

    # Подписи
    signatures = session.get("signatures", [{"position": session.get("head_doctor", "Директор института, академик РАН"), "name": "В.Г. Акимкин"}])
    for sig in signatures:
        p_sig = doc.add_paragraph()
        p_sig.paragraph_format.space_before = Pt(20)
        p_sig.paragraph_format.space_after = Pt(10)
        p_sig.paragraph_format.line_spacing = 1.0
        rs1 = p_sig.add_run(f"{sig.get('position', 'Руководитель')}\t\t\t\t\t")
        rs1.font.name = 'Times New Roman'
        rs1.font.size = Pt(12)
        rs1.font.bold = True
        rs2 = p_sig.add_run(f"___________________ / {sig.get('name', 'В.Г. Акимкин')} /")
        rs2.font.name = 'Times New Roman'
        rs2.font.size = Pt(12)

    # Визы согласования
    visas = session.get("visas", [])
    if visas:
        p_visa = doc.add_paragraph()
        p_visa.paragraph_format.space_before = Pt(10)
        p_visa.paragraph_format.space_after = Pt(2)
        rv1 = p_visa.add_run("СОГЛАСОВАНО:\n")
        rv1.font.name = 'Times New Roman'
        rv1.font.size = Pt(10)
        rv1.font.bold = True
        for v in visas:
            p_vl = doc.add_paragraph()
            p_vl.paragraph_format.space_after = Pt(2)
            rv2 = p_vl.add_run(v)
            rv2.font.name = 'Times New Roman'
            rv2.font.size = Pt(10)

    now_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_tag = re.sub(r'[^a-zA-Zа-яА-Я0-9]', '_', session.get("title", "Документ_ОЦ"))[:30]
    filename = f"{clean_tag}_v{session['version']}_{now_ts}.docx"
    file_path = DOCS_DIR / filename
    doc.save(str(file_path))

    return {
        "file_name": filename,
        "relative_path": f"generated_documents/{filename}",
        "download_url": f"/api/catalog/download/{quote(filename)}",
        "size_bytes": file_path.stat().st_size,
        "version": session["version"],
        "is_approved": session["is_approved"],
        "standard": session.get("standard", "ГОСТ Р 7.0.97-2016")
    }
