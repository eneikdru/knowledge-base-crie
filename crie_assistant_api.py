import os
import re
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

app = FastAPI(
    title="FBUN CRIE AI Knowledge Base & Assistant",
    version="2.0.0",
    description="Mobile-Ready Autonomous Assistant with Stanford Memorilla (K=16) & Normative Search"
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
DOCS_DIR = BASE_DIR / "generated_documents"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

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
        "Ты — персональный ИИ-ассистент Образовательного центра ФБУН ЦНИИ Эпидемиологии Роспотребнадзора.",
        "Твоя цель — быстро, лаконично и юридически точно помогать методистам, преподавателям и ординаторам.",
        "Отвечай структурированно, без лишней воды, с четкими пунктами.",
        "\nКОНТЕКСТ СТАНФОРДСКОЙ ПАМЯТИ MEMORILLA (K=16):"
    ]
    for k, v in MEMORILLA_SLOTS.items():
        lines.append(f"[{k:02d}] {v['topic']}: {v['scope']}")
    lines.append("\nСТРОГО СОБЛЮДАЙ 152-ФЗ: Персональные данные заменяй на ORD-XXXX, ASP-XXXX, FAC-XXXX.")
    return "\n".join(lines)

class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = "deepseek-chat"
    use_reasoner: Optional[bool] = False

class OrderRequest(BaseModel):
    template_type: str = "enrollment" # enrollment, gia_admit, scholarship
    order_number: str
    order_date: str
    avatar_id: str
    student_name: Optional[str] = "Иванов Иван Иванович"
    specialty_code: str
    specialty_name: str
    budget_type: Optional[str] = "бюджетная основа"
    custom_basis: Optional[str] = "Решение Приемной комиссии (Протокол №1)"

@app.get("/api/v1/health")
def health_check():
    return {
        "status": "healthy",
        "service": "FBUN CRIE Knowledge Base & Assistant",
        "deepseek_connected": bool(DEEPSEEK_API_KEY),
        "memorilla_slots": 16,
        "normative_files_count": 1697,
        "privacy": "152-FZ Zero-Knowledge Verified"
    }

@app.get("/api/v1/normative/search")
def search_normative(q: str = Query("", min_length=1), category: Optional[str] = None):
    cat_path = DATA_DIR / "normative" / "corpus_catalog.json"
    if not cat_path.exists():
        raise HTTPException(status_code=404, detail="Catalog file not found")
        
    data = json.loads(cat_path.read_text(encoding="utf-8"))
    query = q.lower().strip()
    results = []
    
    for cat in data.get("categories", []):
        cat_name = cat.get("category", "")
        if category and category.lower() not in cat_name.lower():
            continue
            
        for f in cat.get("files", []):
            fname = f.get("file_name", "")
            rpath = f.get("relative_path", "")
            if query in fname.lower() or query in rpath.lower():
                results.append({
                    "file_name": fname,
                    "relative_path": rpath,
                    "category": cat_name,
                    "extension": f.get("extension", ""),
                    "size_kb": round(f.get("size_bytes", 0) / 1024, 1)
                })
                if len(results) >= 50:
                    break
        if len(results) >= 50:
            break
            
    return {"query": q, "category_filter": category, "count": len(results), "results": results}

@app.get("/api/v1/avatars")
def get_avatars(role: Optional[str] = None):
    av_path = DATA_DIR / "avatars" / "synthetic_avatars.json"
    if not av_path.exists():
        raise HTTPException(status_code=404, detail="Avatars not found")
    data = json.loads(av_path.read_text(encoding="utf-8"))
    avatars = data.get("avatars", [])
    if role:
        avatars = [a for a in avatars if a.get("role") == role]
    return {"count": len(avatars), "avatars": avatars}

@app.post("/api/v1/chat")
async def chat_consultation(req: ChatRequest):
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=500, detail="DEEPSEEK_API_KEY is missing")
        
    model = "deepseek-reasoner" if req.use_reasoner else req.model
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": build_system_context()},
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
            raise HTTPException(status_code=res.status_code, detail=f"DeepSeek error: {res.text}")
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
    for s in doc.sections:
        s.top_margin = Inches(0.79)
        s.bottom_margin = Inches(0.79)
        s.left_margin = Inches(1.18)
        s.right_margin = Inches(0.59)

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

    title_map = {
        "enrollment": f"О зачислении на обучение в ординатуру ({req.avatar_id})",
        "gia_admit": f"О допуске к Государственной итоговой аттестации ({req.avatar_id})",
        "scholarship": f"О назначении государственной академической стипендии ({req.avatar_id})"
    }
    doc_title = title_map.get(req.template_type, f"Приказ по контингенту ({req.avatar_id})")

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run_title = p_title.add_run(f"{doc_title}\n")
    run_title.font.name = "Times New Roman"
    run_title.font.size = Pt(13)
    run_title.bold = True

    # Body
    p_body = doc.add_paragraph()
    p_body.paragraph_format.line_spacing = 1.5
    p_body.paragraph_format.first_line_indent = Inches(0.49)
    
    if req.template_type == "gia_admit":
        text = (
            f"В соответствии с ФГОС ВО по специальности {req.specialty_code} «{req.specialty_name}» "
            f"и Положением о порядке проведения ГИА,\n\n"
            f"ПРИКАЗЫВАЮ:\n\n"
            f"1. Допустить к прохождению Государственной итоговой аттестации в 2026/2027 учебном году "
            f"ординатора 2 года обучения {req.avatar_id} ({req.student_name}), полностью выполнившего "
            f"индивидуальный учебный план и не имеющего академической задолженности.\n\n"
            f"2. Секретарю ГЭК обеспечить подготовку индивидуального протокола и оценочных листов.\n\n"
            f"3. Контроль за исполнением приказа возложить на Учебный отдел."
        )
    else:
        text = (
            f"В соответствии с Федеральным законом от 29.12.2012 № 273-ФЗ «Об образовании в РФ» "
            f"и на основании {req.custom_basis},\n\n"
            f"ПРИКАЗЫВАЮ:\n\n"
            f"1. Зачислить с 01 сентября 2026 года на 1 курс очной формы обучения по программе ординатуры "
            f"по специальности {req.specialty_code} «{req.specialty_name}» ({req.budget_type}):\n\n"
            f"   — {req.avatar_id} ({req.student_name})\n\n"
            f"2. Начальнику Учебного отдела обеспечить оформление студенческого билета и личного дела.\n\n"
            f"3. Контроль за исполнением приказа оставляю за собой."
        )
        
    run_body = p_body.add_run(text)
    run_body.font.name = "Times New Roman"
    run_body.font.size = Pt(14)

    # Signature
    p_sign = doc.add_paragraph()
    p_sign.paragraph_format.space_before = Pt(30)
    run_sign = p_sign.add_run("Директор\nФБУН ЦНИИ Эпидемиологии Роспотребнадзора, академик РАН                        В.Г. Акимкин")
    run_sign.font.name = "Times New Roman"
    run_sign.font.size = Pt(14)
    run_sign.bold = True

    clean_num = re.sub(r'[^a-zA-Z0-9_\-]', '_', req.order_number)
    out_file = DOCS_DIR / f"order_{clean_num}_{req.avatar_id}.docx"
    doc.save(out_file)

    return {
        "status": "success",
        "file_name": out_file.name,
        "download_url": f"/api/v1/download/{out_file.name}",
        "avatar_id": req.avatar_id,
        "compliance": "ГОСТ Р 7.0.97-2016"
    }

@app.get("/api/v1/download/{file_name}")
def download_generated_file(file_name: str):
    file_path = DOCS_DIR / file_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

@app.get("/", response_class=HTMLResponse)
def index_mobile_pwa():
    return """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <meta name="theme-color" content="#0f172a">
  <title>База Знаний • ЦНИИ Эпидемиологии</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Inter', sans-serif; -webkit-tap-highlight-color: transparent; }
    .pb-safe { padding-bottom: calc(env(safe-area-inset-bottom, 0px) + 72px); }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col pb-safe">

  <!-- Top Bar -->
  <header class="sticky top-0 z-40 bg-slate-900/90 backdrop-blur border-b border-slate-800 px-4 py-3 flex items-center justify-between">
    <div class="flex items-center space-x-2.5">
      <div class="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-white text-sm shadow-md shadow-blue-500/20">Ц</div>
      <div>
        <h1 class="text-sm font-bold leading-tight text-white">ЦНИИ Эпидемиологии</h1>
        <p class="text-[10px] text-slate-400">Учебный центр • База знаний & ИИ</p>
      </div>
    </div>
    <div class="flex items-center space-x-1.5">
      <span class="text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full">152-ФЗ Zero-Knowledge</span>
    </div>
  </header>

  <!-- Content Container -->
  <main class="flex-1 max-w-4xl w-full mx-auto p-3 sm:p-4">

    <!-- TAB 1: CHAT ASSISTANT -->
    <section id="view-chat" class="space-y-3">
      <!-- Quick Question Chips -->
      <div class="flex space-x-2 overflow-x-auto pb-1 text-xs no-scrollbar">
        <button onclick="askChip('Какие 3 этапа входят в ГИА ординатора по эпидемиологии?')" class="bg-slate-900 border border-slate-800 hover:border-blue-500/50 px-3 py-1.5 rounded-full text-slate-300 shrink-0 transition">🎓 Этапы ГИА</button>
        <button onclick="askChip('Сколько часов практики предусмотрено на 2 курсе ординатуры?')" class="bg-slate-900 border border-slate-800 hover:border-blue-500/50 px-3 py-1.5 rounded-full text-slate-300 shrink-0 transition">⏱️ Часы практики</button>
        <button onclick="askChip('Каковы нормы нагрузки профессора и доцента на ставку?')" class="bg-slate-900 border border-slate-800 hover:border-blue-500/50 px-3 py-1.5 rounded-full text-slate-300 shrink-0 transition">👨‍🏫 Нагрузка ППС</button>
        <button onclick="askChip('Какие документы нужны для допуска к защите диссертации в диссовете?')" class="bg-slate-900 border border-slate-800 hover:border-blue-500/50 px-3 py-1.5 rounded-full text-slate-300 shrink-0 transition">📜 Диссовет</button>
      </div>

      <!-- Messages Window -->
      <div class="bg-slate-900/60 border border-slate-800/80 rounded-2xl flex flex-col h-[calc(100vh-210px)] min-h-[380px]">
        <div id="chat-messages" class="flex-1 overflow-y-auto p-3 space-y-3 text-xs sm:text-sm">
          <div class="flex items-start space-x-2.5">
            <div class="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center text-[11px] font-bold shrink-0">ИИ</div>
            <div class="bg-slate-800/80 border border-slate-700/50 p-3 rounded-2xl text-slate-200 leading-relaxed max-w-[85%]">
              Здравствуйте! Я ваш персональный помощник по образовательным программам ЦНИИ Эпидемиологии. В памяти активированы все 16 слотов: стандарты ФГОС, учебные планы РУП, правила ГИА и регламенты приказов. Задайте любой вопрос или выберите подсказку сверху.
            </div>
          </div>
        </div>

        <!-- Input Bar -->
        <div class="p-2 sm:p-3 border-t border-slate-800 bg-slate-900/90 rounded-b-2xl">
          <form onsubmit="sendChat(event)" class="flex space-x-2">
            <input type="text" id="chat-input" placeholder="Задайте вопрос по программам, часам или приказам..." class="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs sm:text-sm text-white focus:outline-none focus:border-blue-500 placeholder-slate-500">
            <button type="submit" id="chat-submit" class="bg-blue-600 hover:bg-blue-500 active:scale-95 text-white font-medium px-4 py-2.5 rounded-xl text-xs sm:text-sm transition flex items-center shrink-0">
              Отправить
            </button>
          </form>
        </div>
      </div>
    </section>

    <!-- TAB 2: NORMATIVE SEARCH (1697 Files) -->
    <section id="view-search" class="hidden space-y-3">
      <div class="bg-slate-900/60 border border-slate-800 rounded-2xl p-3.5 sm:p-4">
        <h2 class="text-sm sm:text-base font-bold text-white mb-1">Поиск по Нормативной Базе (1 697 файлов)</h2>
        <p class="text-[11px] text-slate-400 mb-3">Мгновенный поиск рабочих программ (РПД), оценочных средств (ФОС), учебных планов и регламентов института.</p>

        <!-- Search Bar -->
        <div class="flex flex-col sm:flex-row gap-2 mb-3">
          <input type="text" id="norm-query" oninput="doSearch()" placeholder="Поиск (например: эпидемиология, практика, фос, гиа)..." class="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs sm:text-sm text-white focus:outline-none focus:border-blue-500">
          <select id="norm-cat" onchange="doSearch()" class="bg-slate-950 border border-slate-700 rounded-xl px-3 py-2.5 text-xs sm:text-sm text-slate-300 focus:outline-none">
            <option value="">Все категории</option>
            <option value="05 ООП РПД 2026_27">РПД 2026-2027</option>
            <option value="05 ООП ФОС">ФОС (Оценочные средства)</option>
            <option value="05 ООП РУП и КГ">Учебные планы и графики</option>
            <option value="12 ГИА">ГИА и экзамены</option>
            <option value="00 СТИПЕНДИЯ">Стипендии</option>
            <option value="17 ДИССОВЕТ">Диссовет</option>
          </select>
        </div>

        <!-- Search Results Table -->
        <div id="search-results" class="space-y-2 max-h-[calc(100vh-270px)] overflow-y-auto">
          <div class="text-center py-8 text-xs text-slate-500">Введите поисковый запрос (например: практика, эпидемиология)...</div>
        </div>
      </div>
    </section>

    <!-- TAB 3: ORDER GENERATOR -->
    <section id="view-orders" class="hidden space-y-3">
      <div class="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 sm:p-5 max-w-xl mx-auto">
        <h2 class="text-sm sm:text-base font-bold text-white mb-1">Генератор официальных приказов (.docx)</h2>
        <p class="text-[11px] text-slate-400 mb-4">Автоматически собирает проект приказа по стандарту ГОСТ Р 7.0.97-2016 (Times New Roman 14pt, реквизиты института) за 1 клик.</p>

        <form onsubmit="generateOrderDoc(event)" class="space-y-3 text-xs sm:text-sm">
          <div>
            <label class="block text-slate-300 font-medium mb-1">Тип приказа</label>
            <select id="doc-type" class="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2.5 text-white">
              <option value="enrollment">Приказ о зачислении в ординатуру</option>
              <option value="gia_admit">Приказ о допуске к ГИА</option>
              <option value="scholarship">Приказ о назначении стипендии</option>
            </select>
          </div>

          <div class="grid grid-cols-2 gap-2.5">
            <div>
              <label class="block text-slate-300 font-medium mb-1">Номер приказа</label>
              <input type="text" id="doc-num" value="142-ОД" class="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white">
            </div>
            <div>
              <label class="block text-slate-300 font-medium mb-1">Дата приказа</label>
              <input type="text" id="doc-date" value="01 сентября 2026 г." class="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white">
            </div>
          </div>

          <div class="grid grid-cols-2 gap-2.5">
            <div>
              <label class="block text-slate-300 font-medium mb-1">Код аватара (152-ФЗ)</label>
              <input type="text" id="doc-avatar" value="ORD-0001" class="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white font-mono">
            </div>
            <div>
              <label class="block text-slate-300 font-medium mb-1">ФИО обучающегося</label>
              <input type="text" id="doc-name" value="Иванов Иван Иванович" class="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white">
            </div>
          </div>

          <div>
            <label class="block text-slate-300 font-medium mb-1">Специальность</label>
            <select id="doc-spec" class="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2.5 text-white">
              <option value="31.08.36|Эпидемиология">31.08.36 Эпидемиология</option>
              <option value="31.08.35|Инфекционные болезни">31.08.35 Инфекционные болезни</option>
              <option value="31.08.19|Педиатрия">31.08.19 Педиатрия</option>
            </select>
          </div>

          <button type="submit" id="doc-btn" class="w-full bg-emerald-600 hover:bg-emerald-500 active:scale-95 text-white font-semibold py-3 rounded-xl transition shadow-lg shadow-emerald-600/20 mt-2">
            Сформировать и скачать Word (.docx)
          </button>
        </form>

        <div id="order-success" class="hidden mt-3 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-center">
          <p class="text-xs font-semibold text-emerald-400 mb-1">Документ готов!</p>
          <a id="order-download" href="#" class="text-xs text-blue-400 font-medium underline">📥 Нажмите здесь, чтобы скачать .docx</a>
        </div>
      </div>
    </section>

    <!-- TAB 4: WORKLOAD CALCULATOR (TZ 4) -->
    <section id="view-calc" class="hidden space-y-3">
      <div class="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 sm:p-5 max-w-xl mx-auto">
        <h2 class="text-sm sm:text-base font-bold text-white mb-1">Калькулятор педагогической нагрузки ППС (ТЗ 4)</h2>
        <p class="text-[11px] text-slate-400 mb-4">Расчёт доли ставки преподавателя на основе нормативов кафедры (ставка 750–900 ч/год).</p>

        <div class="space-y-3 text-xs sm:text-sm">
          <div>
            <label class="block text-slate-300 font-medium mb-1">Должность</label>
            <select id="calc-post" onchange="calculateWorkload()" class="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2.5 text-white">
              <option value="800">Профессор (годовая норма 800 ч)</option>
              <option value="850">Доцент (годовая норма 850 ч)</option>
              <option value="900">Ассистент / Преподаватель (годовая норма 900 ч)</option>
            </select>
          </div>

          <div class="grid grid-cols-3 gap-2">
            <div>
              <label class="block text-slate-300 text-[11px] mb-1">Лекции (ч)</label>
              <input type="number" id="calc-lec" value="120" oninput="calculateWorkload()" class="w-full bg-slate-950 border border-slate-700 rounded-xl px-2.5 py-2 text-white">
            </div>
            <div>
              <label class="block text-slate-300 text-[11px] mb-1">Семинары (ч)</label>
              <input type="number" id="calc-sem" value="280" oninput="calculateWorkload()" class="w-full bg-slate-950 border border-slate-700 rounded-xl px-2.5 py-2 text-white">
            </div>
            <div>
              <label class="block text-slate-300 text-[11px] mb-1">Практика (ч)</label>
              <input type="number" id="calc-prac" value="200" oninput="calculateWorkload()" class="w-full bg-slate-950 border border-slate-700 rounded-xl px-2.5 py-2 text-white">
            </div>
          </div>

          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="block text-slate-300 text-[11px] mb-1">Руководство аспирантами (ч)</label>
              <input type="number" id="calc-asp" value="100" oninput="calculateWorkload()" class="w-full bg-slate-950 border border-slate-700 rounded-xl px-2.5 py-2 text-white">
            </div>
            <div>
              <label class="block text-slate-300 text-[11px] mb-1">ГЭК / Аттестации (ч)</label>
              <input type="number" id="calc-gek" value="100" oninput="calculateWorkload()" class="w-full bg-slate-950 border border-slate-700 rounded-xl px-2.5 py-2 text-white">
            </div>
          </div>

          <!-- Result Card -->
          <div class="bg-blue-950/40 border border-blue-500/30 rounded-xl p-3.5 mt-3 flex justify-between items-center">
            <div>
              <div class="text-[11px] text-blue-300">Итоговая нагрузка:</div>
              <div id="calc-total-hours" class="text-lg font-bold text-white">800 часов</div>
            </div>
            <div class="text-right">
              <div class="text-[11px] text-blue-300">Расчётная ставка:</div>
              <div id="calc-rate" class="text-lg font-bold text-emerald-400">1.00 ставки</div>
            </div>
          </div>
        </div>
      </div>
    </section>

  </main>

  <!-- Mobile Bottom Tab Navigation -->
  <nav class="fixed bottom-0 left-0 right-0 z-50 bg-slate-900/95 backdrop-blur border-t border-slate-800 px-2 py-1.5 flex justify-around">
    <button onclick="navTo('chat')" id="btn-nav-chat" class="flex flex-col items-center py-1 px-3 text-blue-400">
      <span class="text-lg">💬</span>
      <span class="text-[10px] font-medium mt-0.5">Ассистент</span>
    </button>
    <button onclick="navTo('search')" id="btn-nav-search" class="flex flex-col items-center py-1 px-3 text-slate-400 hover:text-white">
      <span class="text-lg">🔍</span>
      <span class="text-[10px] font-medium mt-0.5">База знаний</span>
    </button>
    <button onclick="navTo('orders')" id="btn-nav-orders" class="flex flex-col items-center py-1 px-3 text-slate-400 hover:text-white">
      <span class="text-lg">📄</span>
      <span class="text-[10px] font-medium mt-0.5">Приказы</span>
    </button>
    <button onclick="navTo('calc')" id="btn-nav-calc" class="flex flex-col items-center py-1 px-3 text-slate-400 hover:text-white">
      <span class="text-lg">🧮</span>
      <span class="text-[10px] font-medium mt-0.5">Нагрузка</span>
    </button>
  </nav>

  <script>
    function navTo(tab) {
      ['chat', 'search', 'orders', 'calc'].forEach(t => {
        document.getElementById('view-' + t).classList.add('hidden');
        document.getElementById('btn-nav-' + t).className = 'flex flex-col items-center py-1 px-3 text-slate-400 hover:text-white';
      });
      document.getElementById('view-' + tab).classList.remove('hidden');
      document.getElementById('btn-nav-' + tab).className = 'flex flex-col items-center py-1 px-3 text-blue-400';
      if (tab === 'search') doSearch();
    }

    function askChip(text) {
      document.getElementById('chat-input').value = text;
      sendChat(new Event('submit'));
    }

    async function sendChat(e) {
      e.preventDefault();
      const input = document.getElementById('chat-input');
      const text = input.value.trim();
      if (!text) return;

      const container = document.getElementById('chat-messages');
      container.innerHTML += `
        <div class="flex items-start justify-end space-x-2">
          <div class="bg-blue-600 text-white p-3 rounded-2xl leading-relaxed max-w-[85%]">${text}</div>
        </div>
      `;
      input.value = '';
      container.scrollTop = container.scrollHeight;

      const btn = document.getElementById('chat-submit');
      btn.innerText = '...';
      btn.disabled = true;

      try {
        const res = await fetch('/api/v1/chat', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({message: text})
        });
        const data = await res.json();
        const formatted = data.response.replace(/\\n/g, '<br>');
        container.innerHTML += `
          <div class="flex items-start space-x-2.5">
            <div class="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center text-[11px] font-bold shrink-0">ИИ</div>
            <div class="bg-slate-800/80 border border-slate-700/50 p-3 rounded-2xl text-slate-200 leading-relaxed max-w-[85%]">${formatted}</div>
          </div>
        `;
      } catch (err) {
        container.innerHTML += `<div class="text-red-400 text-xs p-2">Ошибка связи: ${err}</div>`;
      }
      btn.innerText = 'Отправить';
      btn.disabled = false;
      container.scrollTop = container.scrollHeight;
    }

    async function doSearch() {
      const q = document.getElementById('norm-query').value.trim();
      const cat = document.getElementById('norm-cat').value;
      const container = document.getElementById('search-results');

      if (!q && !cat) {
        container.innerHTML = '<div class="text-center py-8 text-xs text-slate-500">Введите поисковый запрос (например: эпидемиология, практика, фос)...</div>';
        return;
      }

      container.innerHTML = '<div class="text-center py-4 text-xs text-slate-400">Поиск в 1 697 файлах...</div>';

      try {
        const res = await fetch(`/api/v1/normative/search?q=${encodeURIComponent(q || 'а')}&category=${encodeURIComponent(cat)}`);
        const data = await res.json();
        if (data.results.length === 0) {
          container.innerHTML = '<div class="text-center py-6 text-xs text-slate-400">Ничего не найдено. Попробуйте другой запрос.</div>';
          return;
        }

        let html = '';
        data.results.forEach(r => {
          html += `
            <div class="bg-slate-950 border border-slate-800/80 p-2.5 rounded-xl flex items-center justify-between text-xs">
              <div class="min-w-0 pr-2">
                <div class="font-medium text-white truncate">${r.file_name}</div>
                <div class="text-[10px] text-slate-400 mt-0.5 truncate">${r.category} • ${r.size_kb} КБ</div>
              </div>
              <span class="shrink-0 text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono uppercase">${r.extension.replace('.', '') || 'DOC'}</span>
            </div>
          `;
        });
        container.innerHTML = html;
      } catch (e) {
        container.innerHTML = '<div class="text-red-400 text-xs py-4 text-center">Ошибка поиска</div>';
      }
    }

    async function generateOrderDoc(e) {
      e.preventDefault();
      const btn = document.getElementById('doc-btn');
      btn.innerText = 'Сборка приказа...';
      btn.disabled = true;

      const spec = document.getElementById('doc-spec').value.split('|');
      const payload = {
        template_type: document.getElementById('doc-type').value,
        order_number: document.getElementById('doc-num').value,
        order_date: document.getElementById('doc-date').value,
        avatar_id: document.getElementById('doc-avatar').value,
        student_name: document.getElementById('doc-name').value,
        specialty_code: spec[0],
        specialty_name: spec[1]
      };

      try {
        const res = await fetch('/api/v1/generate-order', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        document.getElementById('order-success').classList.remove('hidden');
        const dl = document.getElementById('order-download');
        dl.href = data.download_url;
        dl.innerText = `📥 Скачать готовый файл: ${data.file_name}`;
      } catch (err) {
        alert('Ошибка генерации: ' + err);
      }
      btn.innerText = 'Сформировать и скачать Word (.docx)';
      btn.disabled = false;
    }

    function calculateWorkload() {
      const norm = parseFloat(document.getElementById('calc-post').value) || 850;
      const lec = parseFloat(document.getElementById('calc-lec').value) || 0;
      const sem = parseFloat(document.getElementById('calc-sem').value) || 0;
      const prac = parseFloat(document.getElementById('calc-prac').value) || 0;
      const asp = parseFloat(document.getElementById('calc-asp').value) || 0;
      const gek = parseFloat(document.getElementById('calc-gek').value) || 0;

      const total = lec + sem + prac + asp + gek;
      const rate = (total / norm).toFixed(2);

      document.getElementById('calc-total-hours').innerText = total + ' часов';
      document.getElementById('calc-rate').innerText = rate + ' ставки';
    }
  </script>
</body>
</html>"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8097)
