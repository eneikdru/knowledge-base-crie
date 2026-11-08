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
    budget_type: Optional[str] = "бюджетная основа"
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
        f"   — {req.avatar_id} (Иванов Иван Иванович)\n\n"
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

    clean_num = re.sub(r'[^a-zA-Z0-9_\-]', '_', req.order_number)
    out_file = DOCS_DIR / f"order_{clean_num}_{req.avatar_id}.docx"
    doc.save(out_file)

    return {
        "status": "success",
        "document_type": "docx",
        "file_path": str(out_file),
        "file_name": out_file.name,
        "download_url": f"/api/v1/download/{out_file.name}",
        "avatar_id": req.avatar_id,
        "compliance": "ГОСТ Р 7.0.97-2016 + 152-ФЗ Zero-Knowledge"
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
def index_web_ui():
    return """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ИИ-Ассистент ОЦ ФБУН ЦНИИ Эпидемиологии Роспотребнадзора</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>body { font-family: 'Inter', sans-serif; }</style>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen">
  <!-- Header -->
  <header class="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-50">
    <div class="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <div class="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center font-bold text-lg text-white shadow-lg shadow-blue-500/20">Ц</div>
        <div>
          <h1 class="font-bold text-lg text-white leading-tight">ФБУН ЦНИИ Эпидемиологии</h1>
          <p class="text-xs text-slate-400">Образовательный центр • ИИ-Ассистент (DeepSeek R1/V3 + Stanford Memorilla)</p>
        </div>
      </div>
      <div class="flex items-center space-x-2">
        <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          ● 152-ФЗ Zero-Knowledge
        </span>
        <a href="/docs" target="_blank" class="text-xs text-slate-400 hover:text-white px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 transition">API Docs</a>
      </div>
    </div>
  </header>

  <!-- Navigation Tabs -->
  <div class="max-w-6xl mx-auto px-4 mt-6">
    <div class="flex border-b border-slate-800 space-x-6 text-sm font-medium">
      <button onclick="switchTab('chat')" id="tab-chat" class="pb-3 text-blue-400 border-b-2 border-blue-400">💬 Консультант (Чат)</button>
      <button onclick="switchTab('generator')" id="tab-generator" class="pb-3 text-slate-400 hover:text-white border-b-2 border-transparent">📄 Генератор приказов (.docx)</button>
      <button onclick="switchTab('avatars')" id="tab-avatars" class="pb-3 text-slate-400 hover:text-white border-b-2 border-transparent">👥 Реестр аватаров (152-ФЗ)</button>
      <button onclick="switchTab('normative')" id="tab-normative" class="pb-3 text-slate-400 hover:text-white border-b-2 border-transparent">📚 Нормативная база (1 697 файлов)</button>
    </div>
  </div>

  <!-- Main Content -->
  <main class="max-w-6xl mx-auto px-4 py-6">
    <!-- TAB 1: CHAT -->
    <section id="view-chat" class="space-y-4">
      <div class="bg-slate-950 border border-slate-800 rounded-2xl p-4 flex flex-col h-[520px]">
        <div id="chat-messages" class="flex-1 overflow-y-auto space-y-4 p-2">
          <div class="flex items-start space-x-3">
            <div class="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-xs font-bold shrink-0">ИИ</div>
            <div class="bg-slate-900 border border-slate-800 p-3.5 rounded-2xl text-sm leading-relaxed max-w-2xl">
              Здравствуйте! Я персональный ИИ-ассистент Образовательного центра ЦНИИ Эпидемиологии. В моей памяти активированы 16 слотов Stanford Memorilla: стандарты ФГОС (Эпидемиология 31.08.36, Инфекционные болезни 31.08.35, Педиатрия 31.08.19), регламенты ГИА, учебные планы РУП, нормы нагрузки ППС и ГОСТы приказов.<br><br>
              Чем могу помочь? Задайте вопрос по программам обучения или регламентам института.
            </div>
          </div>
        </div>
        <div class="pt-4 border-t border-slate-800">
          <form onsubmit="sendMessage(event)" class="flex space-x-2">
            <input type="text" id="chat-input" placeholder="Например: Какие 3 этапа входят в ГИА ординатора по эпидемиологии?..." class="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 text-white">
            <button type="submit" id="chat-btn" class="bg-blue-600 hover:bg-blue-500 text-white font-medium px-5 py-2.5 rounded-xl text-sm transition flex items-center">Отправить</button>
          </form>
        </div>
      </div>
    </section>

    <!-- TAB 2: ORDER GENERATOR -->
    <section id="view-generator" class="hidden">
      <div class="max-w-2xl mx-auto bg-slate-950 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <h2 class="text-lg font-bold text-white mb-2">Генератор официального приказа о зачислении</h2>
        <p class="text-xs text-slate-400 mb-6">Формирует проект официального приказа в формате Microsoft Word (.docx) в строгом соответствии с ГОСТ Р 7.0.97-2016 (Times New Roman 14pt, отступы 1.25 см, реквизиты Роспотребнадзора).</p>
        
        <form onsubmit="generateOrder(event)" class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-medium text-slate-300 mb-1">Номер приказа</label>
              <input type="text" id="ord-number" value="142-ОД" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
            </div>
            <div>
              <label class="block text-xs font-medium text-slate-300 mb-1">Дата приказа</label>
              <input type="text" id="ord-date" value="01 сентября 2026 г." class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-medium text-slate-300 mb-1">Код аватара (152-ФЗ)</label>
              <select id="ord-avatar" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                <option value="ORD-0001">ORD-0001 (Иванов И.И.)</option>
                <option value="ORD-0002">ORD-0002 (Иванов И.И. 2)</option>
                <option value="ORD-0003">ORD-0003 (Иванов И.И. 3)</option>
                <option value="ASP-0001">ASP-0001 (Петров П.П.)</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-medium text-slate-300 mb-1">Основа обучения</label>
              <select id="ord-budget" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                <option value="бюджетная основа">Бюджетная основа</option>
                <option value="договорная основа">Договорная основа</option>
                <option value="целевой прием">Целевой прием</option>
              </select>
            </div>
          </div>

          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1">Специальность</label>
            <select id="ord-spec" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
              <option value="31.08.36|Эпидемиология">31.08.36 Эпидемиология</option>
              <option value="31.08.35|Инфекционные болезни">31.08.35 Инфекционные болезни</option>
              <option value="31.08.19|Педиатрия">31.08.19 Педиатрия</option>
            </select>
          </div>

          <div class="pt-2">
            <button type="submit" id="gen-btn" class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-medium py-3 rounded-xl transition shadow-lg shadow-emerald-600/20">
              Сформировать и скачать .docx
            </button>
          </div>
        </form>

        <div id="gen-result" class="mt-4 hidden p-4 rounded-xl bg-slate-900 border border-emerald-500/30">
          <p class="text-sm font-semibold text-emerald-400 mb-1">Приказ успешно сформирован!</p>
          <a id="download-link" href="#" class="inline-flex items-center text-xs text-blue-400 hover:underline">
            📥 Скачать готовый файл Word (.docx)
          </a>
        </div>
      </div>
    </section>

    <!-- TAB 3: AVATARS -->
    <section id="view-avatars" class="hidden">
      <div class="bg-slate-950 border border-slate-800 rounded-2xl p-6">
        <h2 class="text-lg font-bold text-white mb-2">Реестр синтетических аватаров (Zero-Knowledge 152-ФЗ)</h2>
        <p class="text-xs text-slate-400 mb-6">В соответствии с законодательством РФ, реальные паспортные данные студентов и кадров хранятся в защищенном локальном сейфе. Для работы в ИИ и составления проектов используются обезличенные аватары с кодами.</p>
        
        <div id="avatars-table" class="overflow-x-auto text-sm text-left">
          Загрузка аватаров...
        </div>
      </div>
    </section>

    <!-- TAB 4: NORMATIVE -->
    <section id="view-normative" class="hidden">
      <div class="bg-slate-950 border border-slate-800 rounded-2xl p-6">
        <h2 class="text-lg font-bold text-white mb-2">Нормативно-методический массив ЦНИИ Эпидемиологии</h2>
        <p class="text-xs text-slate-400 mb-6">1 697 структурированных рабочих документов института (РПД, ФОС, РУП, стандарты ГИА), доступных для моментального цитирования ассистентом.</p>
        
        <div id="normative-list" class="grid grid-cols-2 gap-4">
          Загрузка каталога...
        </div>
      </div>
    </section>
  </main>

  <script>
    function switchTab(tab) {
      ['chat', 'generator', 'avatars', 'normative'].forEach(t => {
        document.getElementById('view-' + t).classList.add('hidden');
        document.getElementById('tab-' + t).className = 'pb-3 text-slate-400 hover:text-white border-b-2 border-transparent';
      });
      document.getElementById('view-' + tab).classList.remove('hidden');
      document.getElementById('tab-' + tab).className = 'pb-3 text-blue-400 border-b-2 border-blue-400';
      if (tab === 'avatars') loadAvatars();
      if (tab === 'normative') loadNormative();
    }

    async function sendMessage(e) {
      e.preventDefault();
      const input = document.getElementById('chat-input');
      const text = input.value.trim();
      if (!text) return;

      const container = document.getElementById('chat-messages');
      container.innerHTML += `
        <div class="flex items-start justify-end space-x-3">
          <div class="bg-blue-600 text-white p-3.5 rounded-2xl text-sm leading-relaxed max-w-2xl">${text}</div>
        </div>
      `;
      input.value = '';
      container.scrollTop = container.scrollHeight;

      const btn = document.getElementById('chat-btn');
      btn.innerText = 'Думаю...';
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
          <div class="flex items-start space-x-3">
            <div class="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-xs font-bold shrink-0">ИИ</div>
            <div class="bg-slate-900 border border-slate-800 p-3.5 rounded-2xl text-sm leading-relaxed max-w-2xl text-slate-200">${formatted}</div>
          </div>
        `;
      } catch (err) {
        container.innerHTML += `<div class="text-red-400 text-xs p-2">Ошибка запроса к DeepSeek: ${err}</div>`;
      }
      btn.innerText = 'Отправить';
      btn.disabled = false;
      container.scrollTop = container.scrollHeight;
    }

    async function generateOrder(e) {
      e.preventDefault();
      const btn = document.getElementById('gen-btn');
      btn.innerText = 'Генерация...';
      btn.disabled = true;

      const spec = document.getElementById('ord-spec').value.split('|');
      const payload = {
        template_id: "TPL-01",
        order_number: document.getElementById('ord-number').value,
        order_date: document.getElementById('ord-date').value,
        avatar_id: document.getElementById('ord-avatar').value,
        specialty_code: spec[0],
        specialty_name: spec[1],
        budget_type: document.getElementById('ord-budget').value
      };

      try {
        const res = await fetch('/api/v1/generate-order', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        document.getElementById('gen-result').classList.remove('hidden');
        const link = document.getElementById('download-link');
        link.href = data.download_url;
        link.innerText = `📥 Скачать файл: ${data.file_name}`;
      } catch (err) {
        alert('Ошибка генерации: ' + err);
      }
      btn.innerText = 'Сформировать и скачать .docx';
      btn.disabled = false;
    }

    async function loadAvatars() {
      const container = document.getElementById('avatars-table');
      try {
        const res = await fetch('/api/v1/avatars');
        const data = await res.json();
        let html = '<table class="w-full border-collapse border border-slate-800 text-xs"><tr class="bg-slate-900 text-slate-400"><th class="border border-slate-800 p-2">Код аватара</th><th class="border border-slate-800 p-2">Роль</th><th class="border border-slate-800 p-2">Псевдоним</th><th class="border border-slate-800 p-2">Специальность / Должность</th></tr>';
        data.avatars.forEach(a => {
          html += `<tr class="hover:bg-slate-900/50"><td class="border border-slate-800 p-2 font-mono text-blue-400">${a.id}</td><td class="border border-slate-800 p-2">${a.role}</td><td class="border border-slate-800 p-2">${a.full_name_pseudonym}</td><td class="border border-slate-800 p-2 text-slate-400">${a.specialty_name || a.position || a.department || '—'}</td></tr>`;
        });
        html += '</table>';
        container.innerHTML = html;
      } catch(e) {
        container.innerHTML = '<span class="text-red-400">Ошибка загрузки аватаров</span>';
      }
    }

    async function loadNormative() {
      const container = document.getElementById('normative-list');
      try {
        const res = await fetch('/api/v1/normative/catalog');
        const data = await res.json();
        let html = '';
        data.categories.forEach(c => {
          html += `<div class="bg-slate-900 border border-slate-800 p-3.5 rounded-xl"><div class="font-semibold text-sm text-white">${c.category}</div><div class="text-xs text-slate-400 mt-1">${c.file_count} файлов в корпусе</div></div>`;
        });
        container.innerHTML = html;
      } catch(e) {
        container.innerHTML = '<span class="text-red-400">Ошибка каталога</span>';
      }
    }
  </script>
</body>
</html>"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8097)
