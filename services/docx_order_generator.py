"""Service for generating official institutional orders in DOCX format adhering to GOST R 7.0.97-2016.

Strict compliance requirements:
- Font: Times New Roman, 14pt (header text may be 12-14pt, document text 14pt).
- Margins: Left: 30 mm, Right: 15 mm, Top: 20 mm, Bottom: 20 mm.
- Paragraph formatting: First line indent 1.25 cm, line spacing 1.15 to 1.5 pt, justified body text.
- Official requisites: Federal Service for Surveillance on Consumer Rights Protection and Human Wellbeing
  (Rospotrebnadzor), FBUN Central Research Institute of Epidemiology (FBUN TsNII Epidemiologii).
"""

from io import BytesIO
from typing import Dict, Any, List, Optional
from docx import Document
from docx.shared import Mm, Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

ROSPOTREBNADZOR_HEADER_LINES = [
    "ФЕДЕРАЛЬНАЯ СЛУЖБА ПО НАДЗОРУ В СФЕРЕ ЗАЩИТЫ",
    "ПРАВ ПОТРЕБИТЕЛЕЙ И БЛАГОПОЛУЧИЯ ЧЕЛОВЕКА",
    "(РОСПОТРЕБНАДЗОР)",
    "ФЕДЕРАЛЬНОЕ БЮДЖЕТНОЕ УЧРЕЖДЕНИЕ НАУКИ",
    "«ЦЕНТРАЛЬНЫЙ НАУЧНО-ИССЛЕДОВАТЕЛЬСКИЙ ИНСТИТУТ ЭПИДЕМИОЛОГИИ»",
    "(ФБУН ЦНИИ Эпидемиологии Роспотребнадзора)",
    "ОБРАЗОВАТЕЛЬНЫЙ ЦЕНТР",
]

ORDER_TEMPLATES = {
    "enrollment": {
        "title": "О зачислении на обучение по программам ординатуры",
        "preamble": "В соответствии с Федеральным законом от 29.12.2012 № 273-ФЗ «Об образовании в Российской Федерации», Порядком приема на обучение по образовательным программам высшего образования - программам ординатуры и решением Приемной комиссии (протокол № {protocol_num} от {protocol_date}),",
        "action_word": "ПРИКАЗЫВАЮ:",
        "default_items": [
            "Зачислить с {start_date} года на 1 курс очной формы обучения по специальности {specialty_code} «{specialty_name}» следующих поступающих:",
            "{student_list}",
            "Начальнику учебно-методического отдела обеспечить формирование личных дел зачисленных обучающихся.",
            "Контроль за исполнением настоящего приказа оставляю за собой.",
        ],
    },
    "gia_admission": {
        "title": "О допуске к государственной итоговой аттестации",
        "preamble": "В соответствии с Порядком проведения государственной итоговой аттестации по образовательным программам высшего образования и на основании результатов освоения основной профессиональной образовательной программы,",
        "action_word": "ПРИКАЗЫВАЮ:",
        "default_items": [
            "Допустить к прохождению государственной итоговой аттестации (3 обязательных этапа ГИА) ординаторов выпускного курса по специальности {specialty_code} «{specialty_name}»:",
            "{student_list}",
            "Утвердить график проведения заседаний Государственной экзаменационной комиссии с {start_date} года.",
            "Контроль за исполнением настоящего приказа возложить на руководителя Образовательного центра.",
        ],
    },
    "scholarship": {
        "title": "О назначении стипендий обучающимся",
        "preamble": "В соответствии с Положением о стипендиальном обеспечении обучающихся ФБУН ЦНИИ Эпидемиологии Роспотребнадзора и протоколом заседания Стипендиальной комиссии № {protocol_num} от {protocol_date},",
        "action_word": "ПРИКАЗЫВАЮ:",
        "default_items": [
            "Назначить государственную академическую стипендию с {start_date} года следующим обучающимся, показавшим отличные и хорошие результаты по итогам промежуточной аттестации:",
            "{student_list}",
            "Бухгалтерии института производить ежемесячную выплату назначенных стипендий в установленные сроки.",
            "Контроль за исполнением настоящего приказа оставляю за собой.",
        ],
    },
}


def configure_gost_page_layout(section):
    """Apply GOST R 7.0.97-2016 page setup: left 30 mm, right 15 mm, top 20 mm, bottom 20 mm."""
    section.top_margin = Mm(20)
    section.bottom_margin = Mm(20)
    section.left_margin = Mm(30)
    section.right_margin = Mm(15)
    section.page_width = Mm(210)
    section.page_height = Mm(297)


def set_run_font(run, font_name="Times New Roman", size_pt=14, bold=False, italic=False):
    """Ensure font family and size are set on run and rFonts element for strict Word compatibility."""
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.bold = bold
    run.italic = italic

    # Force w:rFonts element attributes for complex scripts / East Asian / ASCII
    rPr = run._r.get_or_add_rPr()
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:ascii'), font_name)
    rFonts.set(qn('w:hAnsi'), font_name)
    rFonts.set(qn('w:cs'), font_name)
    rFonts.set(qn('w:eastAsia'), font_name)
    rPr.append(rFonts)


def add_gost_paragraph(
    doc: Document,
    text: str = "",
    align: WD_ALIGN_PARAGRAPH = WD_ALIGN_PARAGRAPH.JUSTIFY,
    bold: bool = False,
    italic: bool = False,
    first_line_indent_cm: float = 1.25,
    space_after_pt: float = 0,
    space_before_pt: float = 0,
    line_spacing: float = 1.15,
    font_size_pt: float = 14,
):
    """Creates a paragraph adhering to GOST typography standards."""
    p = doc.add_paragraph()
    p.alignment = align
    p_format = p.paragraph_format
    if first_line_indent_cm > 0:
        p_format.first_line_indent = Mm(first_line_indent_cm * 10)
    else:
        p_format.first_line_indent = Mm(0)
    p_format.space_before = Pt(space_before_pt)
    p_format.space_after = Pt(space_after_pt)
    p_format.line_spacing = line_spacing

    if text:
        run = p.add_run(text)
        set_run_font(run, font_name="Times New Roman", size_pt=font_size_pt, bold=bold, italic=italic)

    return p


def build_order_docx(
    order_type: str,
    order_number: str = "124-ОД",
    order_date: str = "01 сентября 2026 г.",
    city: str = "г. Москва",
    title_override: Optional[str] = None,
    specialty_code: str = "31.08.36",
    specialty_name: str = "Эпидемиология",
    protocol_num: str = "1",
    protocol_date: str = "30 августа 2026 г.",
    start_date: str = "01 сентября 2026",
    students: Optional[List[Dict[str, Any]]] = None,
    custom_items: Optional[List[str]] = None,
    signatory_title: str = "Директор института",
    signatory_name: str = "В.Г. Акимкин",
) -> BytesIO:
    """Generates a complete DOCX document meeting GOST R 7.0.97-2016 requisites and typography."""
    doc = Document()

    # Default document style setup
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(14)

    section = doc.sections[0]
    configure_gost_page_layout(section)

    # 1. Rospotrebnadzor Requisite Header
    for i, line in enumerate(ROSPOTREBNADZOR_HEADER_LINES):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Mm(0)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(2 if i < len(ROSPOTREBNADZOR_HEADER_LINES) - 1 else 14)
        p.paragraph_format.line_spacing = 1.0
        is_bold = i in [0, 1, 3, 4, 6]
        font_size = 12 if i < 3 else (13 if i < 6 else 14)
        run = p.add_run(line)
        set_run_font(run, font_name="Times New Roman", size_pt=font_size, bold=is_bold)

    # 2. Document Type (ПРИКАЗ)
    p_prikaz = doc.add_paragraph()
    p_prikaz.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_prikaz.paragraph_format.first_line_indent = Mm(0)
    p_prikaz.paragraph_format.space_before = Pt(12)
    p_prikaz.paragraph_format.space_after = Pt(12)
    run_prikaz = p_prikaz.add_run("ПРИКАЗ")
    set_run_font(run_prikaz, font_name="Times New Roman", size_pt=18, bold=True)

    # 3. Date, Number and City Table (Standard Russian GOST header requisites layout)
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
    table.columns[0].width = Mm(85)
    table.columns[1].width = Mm(80)

    cell_left = table.cell(0, 0)
    cell_right = table.cell(0, 1)

    p_left = cell_left.paragraphs[0]
    p_left.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_left.paragraph_format.first_line_indent = Mm(0)
    p_left.paragraph_format.space_before = Pt(0)
    p_left.paragraph_format.space_after = Pt(6)
    run_date = p_left.add_run(f"{order_date}\n{city}")
    set_run_font(run_date, font_name="Times New Roman", size_pt=14)

    p_right = cell_right.paragraphs[0]
    p_right.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_right.paragraph_format.first_line_indent = Mm(0)
    p_right.paragraph_format.space_before = Pt(0)
    p_right.paragraph_format.space_after = Pt(6)
    run_num = p_right.add_run(f"№ {order_number}")
    set_run_font(run_num, font_name="Times New Roman", size_pt=14, bold=True)

    # 4. Order Subject Title
    tpl_info = ORDER_TEMPLATES.get(order_type, ORDER_TEMPLATES["enrollment"])
    title_text = title_override or tpl_info["title"]

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_title.paragraph_format.first_line_indent = Mm(0)
    p_title.paragraph_format.space_before = Pt(14)
    p_title.paragraph_format.space_after = Pt(12)
    p_title.paragraph_format.line_spacing = 1.15
    run_title = p_title.add_run(title_text)
    set_run_font(run_title, font_name="Times New Roman", size_pt=14, bold=True)

    # 5. Preamble
    preamble_text = tpl_info["preamble"].format(
        protocol_num=protocol_num,
        protocol_date=protocol_date,
        specialty_code=specialty_code,
        specialty_name=specialty_name,
        start_date=start_date,
    )
    add_gost_paragraph(doc, text=preamble_text, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after_pt=6)

    # 6. Action Verb (ПРИКАЗЫВАЮ:)
    p_act = add_gost_paragraph(
        doc,
        text=tpl_info.get("action_word", "ПРИКАЗЫВАЮ:"),
        align=WD_ALIGN_PARAGRAPH.LEFT,
        bold=True,
        first_line_indent_cm=0,
        space_before_pt=6,
        space_after_pt=6,
    )

    # Format student list if provided
    if not students:
        formatted_students = (
            "1. ORD-2026-001 (конкурсный балл: 98)\n"
            "2. ORD-2026-002 (конкурсный балл: 95)\n"
            "3. ORD-2026-003 (конкурсный балл: 92)"
        )
    else:
        lines = []
        for idx, st in enumerate(students, 1):
            identifier = st.get("identifier", f"ORD-2026-{idx:03d}")
            extra = st.get("details", "")
            if extra:
                lines.append(f"{idx}. {identifier} ({extra})")
            else:
                lines.append(f"{idx}. {identifier}")
        formatted_students = "\n".join(lines)

    # 7. Directive Items
    items = custom_items or tpl_info.get("default_items", [])
    for idx, item in enumerate(items, 1):
        formatted_item = item.format(
            specialty_code=specialty_code,
            specialty_name=specialty_name,
            start_date=start_date,
            protocol_num=protocol_num,
            protocol_date=protocol_date,
            student_list=formatted_students,
        )
        if item == "{student_list}":
            # List of students as sub-paragraphs
            for st_line in formatted_students.split("\n"):
                add_gost_paragraph(
                    doc,
                    text=st_line,
                    align=WD_ALIGN_PARAGRAPH.LEFT,
                    first_line_indent_cm=2.0,
                    space_after_pt=2,
                )
        else:
            # Numbered directive clause
            clause_text = f"{idx}. {formatted_item}" if not formatted_item.startswith(f"{idx}.") else formatted_item
            add_gost_paragraph(doc, text=clause_text, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after_pt=4)

    # 8. Signature Block
    sig_table = doc.add_table(rows=1, cols=2)
    sig_table.autofit = False
    sig_table.columns[0].width = Mm(90)
    sig_table.columns[1].width = Mm(75)

    sig_cell_left = sig_table.cell(0, 0)
    sig_cell_right = sig_table.cell(0, 1)

    p_sig_left = sig_cell_left.paragraphs[0]
    p_sig_left.paragraph_format.first_line_indent = Mm(0)
    p_sig_left.paragraph_format.space_before = Pt(24)
    p_sig_left.paragraph_format.space_after = Pt(0)
    p_sig_left.paragraph_format.line_spacing = 1.0
    run_s_left = p_sig_left.add_run(signatory_title)
    set_run_font(run_s_left, font_name="Times New Roman", size_pt=14, bold=True)

    p_sig_right = sig_cell_right.paragraphs[0]
    p_sig_right.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_sig_right.paragraph_format.first_line_indent = Mm(0)
    p_sig_right.paragraph_format.space_before = Pt(24)
    p_sig_right.paragraph_format.space_after = Pt(0)
    p_sig_right.paragraph_format.line_spacing = 1.0
    run_s_right = p_sig_right.add_run(signatory_name)
    set_run_font(run_s_right, font_name="Times New Roman", size_pt=14, bold=True)

    output = BytesIO()
    doc.save(output)
    output.seek(0)
    return output
