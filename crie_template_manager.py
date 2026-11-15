"""
crie_template_manager.py: Менеджер утвержденных образцов и сессий документов
для ФБУН ЦНИИ Эпидемиологии Роспотребнадзора.

Реализует:
1. Реестр эталонных утвержденных образцов (Approved Templates) по СанПиН 3.3686-21 и ГОСТ Р 7.0.97-2016.
2. Загрузку и регистрацию новых пользовательских образцов (.docx).
3. Интерактивную сессию документа: агент принимает правки на естественном языке,
   патчит JSON-модель документа на бэкенде, а бэкенд мгновенно пересобирает чистый .docx.
"""

import os
import re
import json
import uuid
import shutil
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

# In-memory document sessions storage: session_id -> DocumentSession
_DOCUMENT_SESSIONS: Dict[str, Dict[str, Any]] = {}


DEFAULT_APPROVED_TEMPLATES = [
    {
        "id": "TPL-APPROVED-MEASLES",
        "name": "Приказ о проведении противоэпидемических мероприятий при выявлении кори в стационаре",
        "category": "Госпитальная эпидемиология",
        "authority": "Утвержден Директором ФБУН ЦНИИЭ Роспотребнадзора, академиком РАН",
        "sanpin": "СанПиН 3.3686-21, разд. XVIII",
        "gost": "ГОСТ Р 7.0.97-2016",
        "is_approved": True,
        "preamble_template": "В связи с выявлением случая заболевания с подозрением на корь в {department}, в целях локализации и ликвидации эпидемического очага, недопущения внутрибольничного распространения инфекции, в строгом соответствии с Федеральным законом от 30.03.1999 № 52-ФЗ «О санитарно-эпидемиологическом благополучии населения», СанПиН 3.3686-21 (разд. XVIII) и СанПиН 2.1.3678-20:",
        "default_actions": [
            "Немедленно изолировать пациента с симптомами кори в бокс Мельцера (изолированную палату с принудительной вытяжной вентиляцией) на срок до 4 дня с момента появления сыпи (при наличии осложнений — до 10 дня).",
            "Лечащему врачу в течение 2 часов передать первичное телефонное оповещение и в течение 12 часов направить экстренное извещение (форма № 058/у) в территориальный орган Роспотребнадзора с регистрацией в журнале ф. 060/у.",
            "Госпитальному эпидемиологу провести эпидрасследование, установить границы очага и организовать экстренную вакцинацию контактных лиц в первые 72 часа с момента выявления первого случая.",
            "Установить непрерывное медицинское наблюдение за контактными лицами на срок 21 день с ежедневной термометрией 2 раза в сутки и осмотром кожных покровов и зева.",
            "Главной медицинской сестре обеспечить неснижаемый запас СИЗ (респираторы FFP2/FFP3) и сертифицированных дезинфицирующих средств по вирулицидному режиму.",
            "Контроль исполнения настоящего приказа оставляю за собой."
        ],
        "default_head_doctor": "Директор института / Главный врач",
        "default_epidemiologist": "Врач-эпидемиолог госпитальный"
    },
    {
        "id": "TPL-APPROVED-SOP-DISINFECTION",
        "name": "СОП: Проведение текущей и генеральной дезинфекции в отделениях высокого эпидемиологического риска",
        "category": "Инфекционный контроль и ИСМП",
        "authority": "Утвержден Учебно-методическим советом и Комиссией по ИСМП",
        "sanpin": "СанПиН 3.3686-21, разд. II",
        "gost": "ГОСТ Р 7.0.97-2016",
        "is_approved": True,
        "preamble_template": "Стандартная операционная процедура устанавливает единый алгоритм текущей и генеральной уборки, предстерилизационной очистки и дезинфекции изделий медицинского назначения в соответствии с требованиями СанПиН 3.3686-21 (разд. II) и СП 2.1.3678-20.",
        "default_actions": [
            "Текущую влажную уборку проводить не реже 2 раз в сутки с применением моюще-дезинфицирующих средств с моющим эффектом.",
            "Генеральную уборку помещений с асептическим режимом (манипуляционные, процедурные, перевязочные) проводить по графику не реже 1 раза в 7 дней.",
            "Контроль качества предстерилизационной очистки (ПСО) проводить азопирамовой пробой на остаточную кровь в объеме 1% от обработанной партии.",
            "Обеззараживание воздуха осуществлять бактерицидными облучателями закрытого типа в постоянном режиме, открытого типа — после генеральной уборки (60 мин.)."
        ],
        "default_head_doctor": "Главная медицинская сестра",
        "default_epidemiologist": "Госпитальный эпидемиолог"
    },
    {
        "id": "TPL-APPROVED-SALMONELLA",
        "name": "Приказ о локализации очага острой кишечной инфекции (сальмонеллеза) и усилении санэпидрежима",
        "category": "Госпитальная эпидемиология",
        "authority": "Утвержден Главным государственным санитарным врачом / Руководителем учреждения",
        "sanpin": "СанПиН 3.3686-21, разд. III",
        "gost": "ГОСТ Р 7.0.97-2016",
        "is_approved": True,
        "preamble_template": "В связи с регистрацией бактериологически подтвержденного случая острой кишечной инфекции (Salmonella enteritidis), в целях локализации очага, установления факторов передачи и предотвращения распространения инфекции в соответствии с разделом III СанПиН 3.3686-21:",
        "default_actions": [
            "Изолировать заболевшего пациента в инфекционный стационар / бокс.",
            "Направить экстренное извещение ф. 058/у в территориальный орган Роспотребнадзора.",
            "Организовать внеплановый отбор суточных проб на пищеблоке, смывов с технологического оборудования и бактериологическое обследование персонала пищеблока.",
            "Отстранить от работы контактных сотрудников декретированных групп до получения отрицательных результатов бактериологического посева кала.",
            "Провести заключительную дезинфекцию в помещениях пищеблока и отделения препаратами с бактерицидным действием по режиму кишечных инфекций."
        ],
        "default_head_doctor": "Главный врач",
        "default_epidemiologist": "Врач-эпидемиолог"
    },
    {
        "id": "TPL-APPROVED-OUTBREAK-ACT",
        "name": "Акт эпидемиологического расследования очага инфекционного заболевания (форма № 162/у)",
        "category": "Учетная документация",
        "authority": "Утвержденная форма Минздрава РФ и Роспотребнадзора",
        "sanpin": "СанПиН 3.3686-21, ф. 162/у",
        "gost": "ГОСТ Р 7.0.97-2016",
        "is_approved": True,
        "preamble_template": "Настоящий акт составлен комиссией в составе госпитального эпидемиолога и заведующего отделением по факту регистрации группового/единичного случая инфекционного заболевания по форме № 162/у.",
        "default_actions": [
            "Паспортная часть очага: наименование ЛПУ, адрес, дата возникновения очага.",
            "Сведения о заболевшем: диагноз, дата появления симптомов, дата изоляции.",
            "Круг контактных лиц: пофамильный список, вакцинальный анамнез, защитный титр антител.",
            "Проведенные противоэпидемические меры: изоляция, вакцинация, дезинфекция, лабораторный мониторинг."
        ],
        "default_head_doctor": "Заведующий отделением",
        "default_epidemiologist": "Врач-эпидемиолог"
    }
]


def load_template_registry() -> List[Dict[str, Any]]:
    """Загружает полный реестр шаблонов (базовые + пользовательские)."""
    if not REGISTRY_FILE.exists():
        save_template_registry(DEFAULT_APPROVED_TEMPLATES)
        return DEFAULT_APPROVED_TEMPLATES

    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            templates = data.get("templates", [])
            # Если база пуста — инициализируем утвержденными образцами
            if not templates:
                templates = DEFAULT_APPROVED_TEMPLATES
                save_template_registry(templates)
            return templates
    except Exception as e:
        print(f"[WARN] Failed to read template registry: {e}")
        return DEFAULT_APPROVED_TEMPLATES


def save_template_registry(templates: List[Dict[str, Any]]):
    """Сохраняет реестр шаблонов на диск."""
    try:
        with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump({"templates": templates, "updated_at": datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to save template registry: {e}")


def get_template_by_id(template_id: str) -> Optional[Dict[str, Any]]:
    """Находит шаблон по ID."""
    registry = load_template_registry()
    for t in registry:
        if t["id"] == template_id:
            return t
    return None


def register_uploaded_template(
    file_bytes: bytes,
    original_filename: str,
    name: str,
    category: str = "Пользовательские образцы",
    is_approved: bool = False,
    authority: str = "Локальная медицинская организация"
) -> Dict[str, Any]:
    """
    Сохраняет загруженный пользователем файл .docx и регистрирует его как новый шаблон.
    """
    tpl_id = f"TPL-CUSTOM-{uuid.uuid4().hex[:8].upper()}"
    safe_name = f"{tpl_id}_{re.sub(r'[^a-zA-Zа-яА-Я0-9_.-]', '_', original_filename)}"
    saved_path = UPLOAD_DIR / safe_name

    with open(saved_path, "wb") as f:
        f.write(file_bytes)

    # Пробуем распарсить структуру из загруженного docx
    extracted_paragraphs = []
    try:
        doc = docx.Document(str(saved_path))
        for p in doc.paragraphs:
            txt = p.text.strip()
            if txt and len(txt) > 10:
                extracted_paragraphs.append(txt)
    except Exception as e:
        print(f"[WARN] Failed to parse uploaded docx: {e}")

    preamble = extracted_paragraphs[0] if extracted_paragraphs else "В соответствии с требованиями действующего санитарного законодательства РФ:"
    actions = extracted_paragraphs[1:6] if len(extracted_paragraphs) > 1 else [
        "Обеспечить строгое соблюдение санитарно-противоэпидемического режима.",
        "Назначить ответственных лиц за исполнение мероприятий.",
        "Контроль исполнения настоящего документа оставляю за собой."
    ]

    new_tpl = {
        "id": tpl_id,
        "name": name or original_filename,
        "category": category,
        "authority": authority,
        "sanpin": "СанПиН 3.3686-21 / Локальный регламент ЛПУ",
        "gost": "ГОСТ Р 7.0.97-2016",
        "is_approved": bool(is_approved),
        "file_path": str(saved_path),
        "original_filename": original_filename,
        "preamble_template": preamble,
        "default_actions": actions,
        "default_head_doctor": "Главный врач учреждения",
        "default_epidemiologist": "Врач-эпидемиолог",
        "uploaded_at": datetime.now().isoformat()
    }

    registry = load_template_registry()
    registry.append(new_tpl)
    save_template_registry(registry)
    return new_tpl


# =========================================================================
# ИНТЕРАКТИВНЫЕ СЕССИИ ДОКУМЕНТОВ (STATE & PATCHING)
# =========================================================================

def create_document_session(
    template_id: str,
    params: Optional[Dict[str, Any]] = None,
    is_approved_flag: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Создает новую сессию документа на основе выбранного шаблона.
    """
    tpl = get_template_by_id(template_id)
    if not tpl:
        tpl = DEFAULT_APPROVED_TEMPLATES[0]

    session_id = f"session_{uuid.uuid4().hex[:12]}"
    now = datetime.now()
    p = params or {}

    dept = p.get("department") or "Отделение стационара"
    infection = p.get("infection") or "корь"
    order_num = p.get("number") or f"{now.strftime('%y')}-ЭПИД/{now.day:02d}"
    order_date = p.get("date") or now.strftime("%d.%m.%Y")
    org_name = p.get("organization") or "ФБУН ЦНИИ Эпидемиологии Роспотребнадзора"

    preamble = tpl.get("preamble_template", "").format(department=dept, infection=infection)
    actions = list(tpl.get("default_actions", []))

    # Флаг «Утвержденный образец» (может быть передан явно или взят из шаблона)
    approved_status = bool(is_approved_flag if is_approved_flag is not None else tpl.get("is_approved", True))

    session_data = {
        "session_id": session_id,
        "version": 1,
        "template_id": tpl["id"],
        "template_name": tpl["name"],
        "is_approved": approved_status,
        "authority": tpl.get("authority", "ФБУН ЦНИИЭ"),
        "sanpin": tpl.get("sanpin", "СанПиН 3.3686-21"),
        "standard": "ГОСТ Р 7.0.97-2016",
        "organization": org_name,
        "department": dept,
        "infection": infection,
        "number": order_num,
        "date": order_date,
        "title": p.get("title") or f"О проведении противоэпидемических мероприятий ({infection}) в {dept}",
        "preamble": preamble,
        "actions": actions,
        "head_doctor": p.get("head_doctor") or tpl.get("default_head_doctor", "Директор института / Главный врач"),
        "hospital_epidemiologist": p.get("hospital_epidemiologist") or tpl.get("default_epidemiologist", "Госпитальный эпидемиолог"),
        "updated_at": now.isoformat(),
        "change_log": ["Документ первично скомпилирован на основе шаблона."]
    }

    # Компиляция первичного .docx на бэкенде
    compiled_meta = compile_session_to_docx(session_data)
    session_data["compiled_doc"] = compiled_meta
    _DOCUMENT_SESSIONS[session_id] = session_data
    return session_data


def get_document_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Возвращает текущее состояние сессии документа."""
    return _DOCUMENT_SESSIONS.get(session_id)


def patch_document_session(
    session_id: str,
    patches: Dict[str, Any],
    reason: str = "Правка пользователя через агента"
) -> Dict[str, Any]:
    """
    Применяет точечные правки к модели документа и мгновенно пересобирает Word-файл.
    """
    session = _DOCUMENT_SESSIONS.get(session_id)
    if not session:
        # Если сессия устарела или не найдена — создаем новую
        session = create_document_session("TPL-APPROVED-MEASLES", params=patches)
        session_id = session["session_id"]

    session["version"] += 1
    session["updated_at"] = datetime.now().isoformat()

    # Точечные обновления полей
    if "is_approved" in patches:
        session["is_approved"] = bool(patches["is_approved"])
    if "title" in patches and patches["title"]:
        session["title"] = str(patches["title"]).strip()
    if "department" in patches and patches["department"]:
        session["department"] = str(patches["department"]).strip()
    if "infection" in patches and patches["infection"]:
        session["infection"] = str(patches["infection"]).strip()
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

    # Изменение списка пунктов (распоряжений)
    if "actions" in patches and isinstance(patches["actions"], list):
        session["actions"] = [str(a).strip() for a in patches["actions"] if str(a).strip()]
    if "add_action" in patches and patches["add_action"]:
        session["actions"].append(str(patches["add_action"]).strip())
    if "remove_action_index" in patches:
        idx = int(patches["remove_action_index"])
        if 0 <= idx < len(session["actions"]):
            session["actions"].pop(idx)

    session["change_log"].append(f"v{session['version']}: {reason}")

    # Пересборка чистого .docx бэкендом
    compiled_meta = compile_session_to_docx(session)
    session["compiled_doc"] = compiled_meta
    _DOCUMENT_SESSIONS[session_id] = session
    return session


def compile_session_to_docx(session: Dict[str, Any]) -> Dict[str, Any]:
    """
    Детерминированный компилятор бэкенда: превращает модель сессии в файл .docx по ГОСТ Р 7.0.97-2016.
    """
    from crie_document_engine import (
        create_base_document,
        add_gost_header,
        Mm, Pt, RGBColor,
        WD_ALIGN_PARAGRAPH,
        WD_TABLE_ALIGNMENT
    )

    doc = create_base_document()
    add_gost_header(doc, session.get("organization"))

    # Пометка «Утвержденный образец» в правом верхнем углу (если включена)
    if session.get("is_approved"):
        p_app = doc.add_paragraph()
        p_app.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_app.paragraph_format.space_after = Pt(8)
        p_app.paragraph_format.line_spacing = 1.0
        r_app = p_app.add_run(
            f"✓ УТВЕРЖДЕННЫЙ ЭТАЛОННЫЙ ОБРАЗЕЦ\n"
            f"{session.get('authority', 'ФБУН ЦНИИЭ Роспотребнадзора')}\n"
            f"Стандарт: {session.get('standard', 'ГОСТ Р 7.0.97-2016')} | {session.get('sanpin', 'СанПиН 3.3686-21')}\n"
        )
        r_app.font.name = 'Times New Roman'
        r_app.font.size = Pt(9)
        r_app.font.bold = True
        r_app.font.color.rgb = RGBColor(0, 100, 0) # Зеленый цвет утвержденного образца

    # Вид документа
    p_t = doc.add_paragraph()
    p_t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_t.paragraph_format.space_before = Pt(6)
    p_t.paragraph_format.space_after = Pt(10)
    rt = p_t.add_run("ПРИКАЗ")
    rt.font.name = 'Times New Roman'
    rt.font.size = Pt(16)
    rt.font.bold = True

    # Таблица метаданных (Дата / Номер / Город)
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
    rr = pr.add_run(f"№ {session.get('number', '1-ЭПИД')}\nг. Москва")
    rr.font.name = 'Times New Roman'
    rr.font.size = Pt(12)

    # Заголовок
    p_subj = doc.add_paragraph()
    p_subj.paragraph_format.space_before = Pt(16)
    p_subj.paragraph_format.space_after = Pt(10)
    p_subj.paragraph_format.first_line_indent = Mm(12.5)
    p_subj.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r_subj = p_subj.add_run(session.get("title", "О противоэпидемических мероприятиях"))
    r_subj.font.name = 'Times New Roman'
    r_subj.font.size = Pt(13)
    r_subj.font.bold = True

    # Преамбула
    p_pre = doc.add_paragraph()
    p_pre.paragraph_format.first_line_indent = Mm(12.5)
    p_pre.paragraph_format.space_after = Pt(10)
    p_pre.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r_pre = p_pre.add_run(session.get("preamble", ""))
    r_pre.font.name = 'Times New Roman'
    r_pre.font.size = Pt(12)

    # ПРИКАЗЫВАЮ:
    p_cmd = doc.add_paragraph()
    p_cmd.paragraph_format.space_before = Pt(4)
    p_cmd.paragraph_format.space_after = Pt(6)
    p_cmd.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rcmd = p_cmd.add_run("ПРИКАЗЫВАЮ:")
    rcmd.font.name = 'Times New Roman'
    rcmd.font.size = Pt(13)
    rcmd.font.bold = True

    # Пункты
    for idx, act in enumerate(session.get("actions", []), 1):
        p_act = doc.add_paragraph()
        p_act.paragraph_format.first_line_indent = Mm(12.5)
        p_act.paragraph_format.space_after = Pt(5)
        p_act.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        prefix = f"{idx}. " if not act.strip().startswith(f"{idx}.") else ""
        ract = p_act.add_run(f"{prefix}{act}")
        ract.font.name = 'Times New Roman'
        ract.font.size = Pt(12)

    # Подписи
    p_sig = doc.add_paragraph()
    p_sig.paragraph_format.space_before = Pt(20)
    p_sig.paragraph_format.space_after = Pt(14)
    p_sig.paragraph_format.line_spacing = 1.0
    rs1 = p_sig.add_run(f"{session.get('head_doctor', 'Главный врач')}\t\t\t\t\t")
    rs1.font.name = 'Times New Roman'
    rs1.font.size = Pt(12)
    rs1.font.bold = True
    rs2 = p_sig.add_run("___________________ / Подпись /")
    rs2.font.name = 'Times New Roman'
    rs2.font.size = Pt(12)

    # Виза согласования эпидемиолога
    p_visa = doc.add_paragraph()
    p_visa.paragraph_format.space_before = Pt(10)
    p_visa.paragraph_format.space_after = Pt(2)
    rv1 = p_visa.add_run("СОГЛАСОВАНО:\n")
    rv1.font.name = 'Times New Roman'
    rv1.font.size = Pt(10)
    rv1.font.bold = True
    rv2 = p_visa.add_run(f"Госпитальный эпидемиолог: ___________________ / {session.get('hospital_epidemiologist', 'Е.В. Семенова')} /\n")
    rv2.font.name = 'Times New Roman'
    rv2.font.size = Pt(10)

    # Сохранение файла
    now_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    infection_tag = re.sub(r'[^a-zA-Zа-яА-Я0-9]', '_', session.get("infection", "документ"))
    filename = f"Приказ_{infection_tag}_v{session['version']}_{now_ts}.docx"
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
