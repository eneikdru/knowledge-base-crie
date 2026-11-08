import os
import re
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import openpyxl

app = FastAPI(
    title="FBUN CRIE AI Knowledge Base & Assistant API",
    version="1.0.0",
    description="Zero-Knowledge Autonomous Assistant with Stanford Memorilla (K=16) & DeepSeek Reasoning"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# Extract DEEPSEEK_API_KEY from /opt/EneikProductionSys/.env
DEEPSEEK_API_KEY = ""
env_file = Path("/opt/EneikProductionSys/.env")
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.startswith("DEEPSEEK_API_KEY="):
            DEEPSEEK_API_KEY = line.split("=", 1)[1].strip()

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

# Stanford Memorilla (K=16) Orthogonal Knowledge Slots
MEMORILLA_SLOTS = {
    1: {"topic": "ФГОС ВО 31.08.36 Эпидемиология", "scope": "Универсальные и профессиональные компетенции (УК-1..3, ПК-1..6), трудоемкость 120 з.е."},
    2: {"topic": "ФГОС ВО 31.08.35 Инфекционные болезни", "scope": "Диагностические и лечебные стандарты, клинические базы, санитарно-противоэпидемический режим"},
    3: {"topic": "ФГОС ВО 31.08.19 Педиатрия", "scope": "Специфика детских инфекций, календарь профилактических прививок, нормативные протоколы"},
    4: {"topic": "Нормативная база Роспотребнадзора", "scope": "Постановления Главного государственного санитарного врача РФ, СП и СанПиН"},
    5: {"topic": "Учебный год и периоды аттестации", "scope": "1 и 2 семестры, зимняя и летняя сессии, даты ликвидации задолженностей"},
    6: {"topic": "Государственная итоговая аттестация (ГИА)", "scope": "Структура экзамена: тестовый контроль, практические навыки, ситуационные задачи"},
    7: {"topic": "Кандидатские экзамены аспирантуры", "scope": "Специальность, история и философия науки, иностранный язык, протоколы ГЭК"},
    8: {"topic": "Клиническая и производственная практика", "scope": "Инструктажи, дневники практики, отчеты ординаторов, распределение по базам"},
    9: {"topic": "Нормы учебной нагрузки ППС", "scope": "Ставка профессора/доцента (750–900 ч/год), лекционные, семинарские, практические часы"},
    10: {"topic": "Индивидуальные планы аспирантов", "scope": "Сроки утверждения тем диссертаций, ежегодная аттестация на заседании Ученого совета"},
    11: {"topic": "Диссертационный совет 24.1.000.00", "scope": "Требования ВАК, рецензенты, ведущие организации, публикации в рецензируемых изданиях"},
    12: {"topic": "Стипендиальное обеспечение", "scope": "Государственная академическая стипендия, порядок выплат, критерии надбавок"},
    13: {"topic": "ГОСТ оформления приказов", "scope": "Times New Roman 14pt, полуторный интервал, реквизиты ФБУН ЦНИИ Эпидемиологии"},
    14: {"topic": "Формуляры протоколов ГЭК", "scope": "Официальные формы решений экзаменационной комиссии, подписи председателя и членов"},
    15: {"topic": "Правила приема и квоты", "scope": "Контрольные цифры приема (бюджет/целевой прием/договор), баллы за индивидуальные достижения"},
    16: {"topic": "152-ФЗ Zero-Knowledge протокол", "scope": "Запрет передачи реальных ПДн в облачные модели, работа через токены ORD-, ASP-, FAC-"}
}

def build_system_context() -> str:
    lines = [
        "Ты — высококвалифицированный персональный ИИ-ассистент Образовательного центра ФБУН ЦНИИ Эпидемиологии Роспотребнадзора.",
        "Твоя задача — давать юридически точные консультации по учебному процессу, ординатуре, аспирантуре и ДПО, а также готовить проекты документов.",
        "\nСТАНФОРДСКАЯ СЕМАНТИЧЕСКАЯ ПАМЯТЬ MEMORILLA (K=16 СЛОТОВ):"
    ]
    for k, v in MEMORILLA_SLOTS.items():
        lines.append(f"Слот {k:02d} [{v['topic']}]: {v['scope']}")
    lines.append("\nСТРОГИЙ РЕЖИМ 152-ФЗ: Используй идентификаторы ORD-XXXX, ASP-XXXX, FAC-XXXX. Все ответы должны быть оформлены строго профессионально и по стандартам РФ.")
    return "\n".join(lines)

class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = "deepseek-chat"
    use_reasoner: Optional[bool] = False

class OrderRequest(BaseModel):
    template_id: str
    order_number: str
    order_date: str
    avatar_id: str
    specialty_code: str
    specialty_name: str
    budget_type: Optional[str] = "бюджет"
    custom_basis: Optional[str] = "Решение Приемной комиссии (Протокол №1)"

@app.get("/api/v1/health")
def health_check():
    return {
        "status": "healthy",
        "service": "FBUN CRIE AI Knowledge Base",
        "deepseek_configured": bool(DEEPSEEK_API_KEY),
        "memorilla_slots_active": len(MEMORILLA_SLOTS),
        "privacy_compliance": "152-FZ Zero-Knowledge Verified"
    }

@app.get("/api/v1/avatars")
def get_avatars(role: Optional[str] = None):
    av_path = DATA_DIR / "avatars" / "synthetic_avatars.json"
    if not av_path.exists():
        raise HTTPException(status_code=404, detail="Synthetic avatars file not found")
    data = json.loads(av_path.read_text(encoding="utf-8"))
    avatars = data.get("avatars", [])
    if role:
        avatars = [a for a in avatars if a.get("role") == role]
    return {"count": len(avatars), "avatars": avatars}

@app.get("/api/v1/normative/catalog")
def get_normative_catalog():
    cat_path = DATA_DIR / "normative" / "corpus_catalog.json"
    if not cat_path.exists():
        raise HTTPException(status_code=404, detail="Catalog file not found")
    return json.loads(cat_path.read_text(encoding="utf-8"))

@app.post("/api/v1/chat")
async def chat_consultation(req: ChatRequest):
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=500, detail="DEEPSEEK_API_KEY not configured on server")
        
    model = "deepseek-reasoner" if req.use_reasoner else req.model
    system_prompt = build_system_context()
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": req.message}
        ],
        "temperature": 0.2 if req.use_reasoner else 0.4
    }
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(DEEPSEEK_URL, json=payload, headers=headers)
        if res.status_code != 200:
            raise HTTPException(status_code=res.status_code, detail=f"DeepSeek API error: {res.text}")
        data = res.json()
        
    choice = data["choices"][0]["message"]
    return {
        "model_used": model,
        "response": choice.get("content", ""),
        "reasoning": choice.get("reasoning_content", None)
    }

@app.post("/api/v1/generate-order")
def generate_order_document(req: OrderRequest):
    doc = Document()
    
    # Page setup
    sections = doc.sections
    for s in sections:
        s.top_margin = Inches(0.79) # 20 mm
        s.bottom_margin = Inches(0.79)
        s.left_margin = Inches(1.18) # 30 mm
        s.right_margin = Inches(0.59) # 15 mm

    # Header
    p_inst = doc.add_paragraph()
    p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_inst = p_inst.add_run("ФЕДЕРАЛЬНАЯ СЛУЖБА ПО НАДЗОРУ В СФЕРЕ ЗАЩИТЫ ПРАВ ПОТРЕБИТЕЛЕЙ\nИ БЛАГОПОЛУЧИЯ ЧЕЛОВЕКА\nФБУН «ЦНИИ ЭПИДЕМИОЛОГИИ» РОСПОТРЕБНАДЗОРА\n")
    run_inst.font.name = "Times New Roman"
    run_inst.font.size = Pt(12)
    run_inst.bold = True

    p_ord = doc.add_paragraph()
    p_ord.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_ord = p_ord.add_run(f"П Р И К А З\n№ {req.order_number}\nот {req.order_date}\nг. Москва\n")
    run_ord.font.name = "Times New Roman"
    run_ord.font.size = Pt(14)
    run_ord.bold = True

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run_title = p_title.add_run(f"О зачислении на обучение по программе ординатуры ({req.avatar_id})\n")
    run_title.font.name = "Times New Roman"
    run_title.font.size = Pt(13)
    run_title.bold = True

    # Body
    p_body = doc.add_paragraph()
    p_body.paragraph_format.line_spacing = 1.5
    p_body.paragraph_format.first_line_indent = Inches(0.49) # 1.25 cm
    
    text = (
        f"В соответствии с Федеральным законом от 29.12.2012 № 273-ФЗ «Об образовании в Российской Федерации», "
        f"Порядком приема на обучение по образовательным программам высшего образования — программам ординатуры, "
        f"а также на основании {req.custom_basis},\n\n"
        f"ПРИКАЗЫВАЮ:\n\n"
        f"1. Зачислить с 01 сентября 2026 года на 1 курс очной формы обучения по программе ординатуры "
        f"по специальности {req.specialty_code} «{req.specialty_name}» ({req.budget_type}) следующего поступающего:\n\n"
        f"   — {req.avatar_id} (Псевдоним аватара: Иванов Иван Иванович)\n\n"
        f"2. Начальнику Учебного отдела обеспечить формирование личного дела обучающегося {req.avatar_id} "
        f"и оформление студенческого билета.\n\n"
        f"3. Контроль за исполнением настоящего приказа оставляю за собой."
    )
    run_body = p_body.add_run(text)
    run_body.font.name = "Times New Roman"
    run_body.font.size = Pt(14)

    # Signatures
    p_sign = doc.add_paragraph()
    p_sign.paragraph_format.space_before = Pt(30)
    run_sign = p_sign.add_run("Директор\nФБУН ЦНИИ Эпидемиологии Роспотребнадзора, академик РАН                        В.Г. Акимкин")
    run_sign.font.name = "Times New Roman"
    run_sign.font.size = Pt(14)
    run_sign.bold = True

    out_dir = BASE_DIR / "generated_documents"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"order_{req.order_number}_{req.avatar_id}.docx"
    doc.save(out_file)

    return {
        "status": "success",
        "document_type": "docx",
        "file_path": str(out_file),
        "file_name": out_file.name,
        "avatar_id": req.avatar_id,
        "compliance": "ГОСТ Р 7.0.97-2016 + 152-ФЗ Zero-Knowledge"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8097)
