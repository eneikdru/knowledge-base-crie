"""
crie_document_engine.py: Движок динамической генерации официальных документов
по стандарту ГОСТ Р 7.0.97-2016 для FBUN CRIE Knowledge Base & Assistant.

Генерирует настоящие, валидные документы Microsoft Word (.docx) с безупречной типографикой:
- Поля ГОСТ: Левое 30 мм, Правое 15 мм, Верхнее 20 мм, Нижнее 20 мм.
- Гарнитура: Times New Roman 12/14 pt, межстрочный 1.15, абзацный отступ 1.25 см.
- Официальная иерархическая шапка института или ЛПУ.
- Приказы, СОПы по дезинфекции, Карты эпидрасследования, Академические акты.
"""

import os
import re
import uuid
from urllib.parse import quote
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import docx
from docx.shared import Inches, Pt, RGBColor, Mm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

from crie_normative_knowledge import retrieve_normative_clauses

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "generated_documents"
DOCS_DIR.mkdir(parents=True, exist_ok=True)


def set_cell_background(cell, fill_hex: str):
    """Устанавливает фоновый цвет ячейки таблицы."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tc_pr.append(shd)


def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Устанавливает внутренние отступы ячейки."""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tc_pr.append(tc_mar)


def create_base_document() -> docx.Document:
    """Создает документ с базовыми параметрами по ГОСТ Р 7.0.97-2016."""
    doc = docx.Document()
    
    # Настройка полей страницы: 30-15-20-20 мм
    section = doc.sections[0]
    section.top_margin = Mm(20)
    section.bottom_margin = Mm(20)
    section.left_margin = Mm(30)
    section.right_margin = Mm(15)
    section.page_width = Mm(210)
    section.page_height = Mm(297)

    # Настройка базового стиля Normal
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(12)
    font.color.rgb = RGBColor(0, 0, 0)
    style.paragraph_format.line_spacing = 1.15
    style.paragraph_format.space_after = Pt(0)
    style.paragraph_format.space_before = Pt(0)

    return doc


def add_gost_header(doc: docx.Document, organization: Optional[str] = None):
    """Добавляет официальную шапку учреждения."""
    org_text = organization or (
        "ФЕДЕРАЛЬНАЯ СЛУЖБА ПО НАДЗОРУ В СФЕРЕ ЗАЩИТЫ ПРАВ ПОТРЕБИТЕЛЕЙ\n"
        "И БЛАГОПОЛУЧИЯ ЧЕЛОВЕКА\n\n"
        "ФЕДЕРАЛЬНОЕ БЮДЖЕТНОЕ УЧРЕЖДЕНИЕ НАУКИ\n"
        "«ЦЕНТРАЛЬНЫЙ НАУЧНО-ИССЛЕДОВАТЕЛЬСКИЙ ИНСТИТУТ ЭПИДЕМИОЛОГИИ»\n"
        "(ФБУН ЦНИИ Эпидемиологии Роспотребнадзора)"
    )
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(12)
    p.paragraph_format.line_spacing = 1.0
    
    run = p.add_run(org_text)
    run.font.name = 'Times New Roman'
    run.font.size = Pt(11)
    run.font.bold = True


def generate_epidemiology_order(
    title: str,
    infection: str = "корь",
    department: str = "Инфекционное отделение № 1",
    date_str: Optional[str] = None,
    order_number: Optional[str] = None,
    head_doctor: str = "А.К. Горелов",
    hospital_epidemiologist: str = "Е.В. Семенова",
    custom_preamble: Optional[str] = None,
    custom_actions: Optional[List[str]] = None,
    organization: Optional[str] = None,
) -> Path:
    """
    Генерирует официальный приказ главного врача по противоэпидемическим мероприятиям.
    """
    doc = create_base_document()
    add_gost_header(doc, organization)

    # Реквизит: Вид документа
    p_type = doc.add_paragraph()
    p_type.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_type.paragraph_format.space_before = Pt(6)
    p_type.paragraph_format.space_after = Pt(12)
    run_type = p_type.add_run("ПРИКАЗ")
    run_type.font.name = 'Times New Roman'
    run_type.font.size = Pt(16)
    run_type.font.bold = True

    # Реквизиты: Дата, Номер, Место издания
    now = datetime.now()
    d_str = date_str or now.strftime("%d.%m.%Y")
    o_num = order_number or f"{now.strftime('%y')}-ЭПИД/0{now.day}"
    
    table_meta = doc.add_table(rows=1, cols=2)
    table_meta.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_meta.autofit = False
    table_meta.columns[0].width = Mm(80)
    table_meta.columns[1].width = Mm(85)
    
    cell_l = table_meta.cell(0, 0)
    p_l = cell_l.paragraphs[0]
    p_l.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_l.paragraph_format.space_after = Pt(0)
    r_l = p_l.add_run(f"« {d_str[:2]} » {now.strftime('%B')} {now.year} г.")
    r_l.font.name = 'Times New Roman'
    r_l.font.size = Pt(12)
    
    cell_r = table_meta.cell(0, 1)
    p_r = cell_r.paragraphs[0]
    p_r.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_r.paragraph_format.space_after = Pt(0)
    r_r = p_r.add_run(f"№ {o_num}\nг. Москва")
    r_r.font.name = 'Times New Roman'
    r_r.font.size = Pt(12)

    # Заголовок к тексту
    p_subj = doc.add_paragraph()
    p_subj.paragraph_format.space_before = Pt(18)
    p_subj.paragraph_format.space_after = Pt(12)
    p_subj.paragraph_format.first_line_indent = Mm(12.5)
    p_subj.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r_subj = p_subj.add_run(f"О проведении комплекса неотложных противоэпидемических мероприятий при выявлении случая заболевания ({infection}) в {department}")
    r_subj.font.name = 'Times New Roman'
    r_subj.font.size = Pt(13)
    r_subj.font.bold = True

    # Преамбула со строгой нормативной базой
    norm_clauses = retrieve_normative_clauses(infection, max_clauses=2)
    norm_refs = "Федеральным законом от 30.03.1999 № 52-ФЗ «О санитарно-эпидемиологическом благополучии населения», Федеральным законом от 21.11.2011 № 323-ФЗ «Об основах охраны здоровья граждан в Российской Федерации», СанПиН 3.3686-21 «Санитарно-эпидемиологические требования по профилактике инфекционных болезней»"
    if norm_clauses:
        norm_refs += f" (в том числе {norm_clauses[0]['clause']}), СанПиН 2.1.3678-20 и Приказом Минздрава России от 28.01.2021 № 29н"

    preamble_text = custom_preamble or (
        f"В связи с выявлением клинического случая с подозрением на инфекционное заболевание ({infection}) "
        f"у пациента в {department}, в целях локализации и ликвидации эпидемического очага, недопущения внутрибольничного "
        f"распространения инфекции и защиты персонала и пациентов стационара, в строгом соответствии с {norm_refs}:"
    )
    p_pre = doc.add_paragraph()
    p_pre.paragraph_format.first_line_indent = Mm(12.5)
    p_pre.paragraph_format.space_after = Pt(12)
    p_pre.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r_pre = p_pre.add_run(preamble_text)
    r_pre.font.name = 'Times New Roman'
    r_pre.font.size = Pt(12)

    # Слово ПРИКАЗЫВАЮ:
    p_cmd = doc.add_paragraph()
    p_cmd.paragraph_format.space_before = Pt(6)
    p_cmd.paragraph_format.space_after = Pt(8)
    p_cmd.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_cmd = p_cmd.add_run("ПРИКАЗЫВАЮ:")
    r_cmd.font.name = 'Times New Roman'
    r_cmd.font.size = Pt(13)
    r_cmd.font.bold = True

    # Пункты распорядительной части
    default_actions = [
        f"1. Заведующему {department} немедленно изолировать пациента с симптомами ({infection}) в мельцеровский бокс (изолированную палату с принудительной вытяжной вентиляцией). Изоляцию поддерживать до полного клинического выздоровления и окончания заразного периода.",
        f"2. Лечащему врачу отделения в течение 2 (двух) часов с момента выявления подозрения передать первичное телефонное оповещение и в течение 12 часов обеспечить направление экстренного извещения по форме № 058/у в территориальный орган Роспотребнадзора с фиксацией в журнале ф. 060/у.",
        f"3. Госпитальному эпидемиологу ({hospital_epidemiologist}):\n"
        f"   3.1. Немедленно приступить к эпидемиологическому расследованию очага, установить границы очага и составить пофамильные списки всех контактных лиц (пациентов и медперсонала);\n"
        f"   3.2. Обеспечить организацию экстренной вакцинопрофилактики контактных лиц в течение первых 72 часов с момента выявления очага в соответствии с требованиями СанПиН 3.3686-21;\n"
        f"   3.3. Установить непрерывное медицинское наблюдение за контактными лицами сроком на 21 день с ежедневной термометрией (2 раза в сутки) и осмотром зева и кожных покровов.",
        f"4. Главной медицинской сестре института:\n"
        f"   4.1. Обеспечить неснижаемый запас сертифицированных дезинфицирующих средств с доказанной вирулицидной активностью и средств индивидуальной защиты (респираторы класса защиты не ниже FFP2, защитные очки, влагостойкие халаты);\n"
        f"   4.2. Перевести персонал отделения на строгий масочно-перчаточный режим и обеспечить контроль обработки рук кожными антисептиками по протоколу СанПиН 3.3686-21;\n"
        f"   4.3. Организовать проведение текущей очаговой дезинфекции и обеззараживания воздуха ультрафиолетовыми бактерицидными рециркуляторами закрытого типа в постоянном режиме.",
        f"5. Заведующему клинико-диагностической лабораторией организовать первоочередной забор биоматериала (сыворотка крови на IgM, мазок из носоглотки на ПЦР) и проведение исследований с передачей результатов в течение 24 часов.",
        f"6. Контроль за надлежащим исполнением настоящего приказа оставляю за собой."
    ]
    actions = custom_actions or default_actions

    for act_text in actions:
        p_act = doc.add_paragraph()
        p_act.paragraph_format.first_line_indent = Mm(12.5)
        p_act.paragraph_format.space_after = Pt(6)
        p_act.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        r_act = p_act.add_run(act_text)
        r_act.font.name = 'Times New Roman'
        r_act.font.size = Pt(12)

    # Подпись руководителя
    p_sig = doc.add_paragraph()
    p_sig.paragraph_format.space_before = Pt(24)
    p_sig.paragraph_format.space_after = Pt(18)
    p_sig.paragraph_format.line_spacing = 1.0
    r_pos = p_sig.add_run("Директор института /\nГлавный врач\t\t\t\t\t")
    r_pos.font.name = 'Times New Roman'
    r_pos.font.size = Pt(12)
    r_pos.font.bold = True
    
    r_name = p_sig.add_run(f"___________________ / {head_doctor} /")
    r_name.font.name = 'Times New Roman'
    r_name.font.size = Pt(12)

    # Визы согласования
    p_visa = doc.add_paragraph()
    p_visa.paragraph_format.space_before = Pt(12)
    p_visa.paragraph_format.space_after = Pt(0)
    r_v = p_visa.add_run("СОГЛАСОВАНО:\n")
    r_v.font.name = 'Times New Roman'
    r_v.font.size = Pt(10)
    r_v.font.bold = True
    
    visas = [
        f"Госпитальный эпидемиолог: ___________________ / {hospital_epidemiologist} /  « ___ » _________ 2026 г.",
        "Заместитель главного врача по лечебной работе: ___________________ / И.П. Воронов /  « ___ » _________ 2026 г.",
        "Начальник юридического отдела: ___________________ / С.Ю. Васильева /  « ___ » _________ 2026 г."
    ]
    for visa in visas:
        p_v_line = doc.add_paragraph()
        p_v_line.paragraph_format.space_after = Pt(2)
        r_vl = p_v_line.add_run(visa)
        r_vl.font.name = 'Times New Roman'
        r_vl.font.size = Pt(10)

    # Сохранение документа
    safe_name = f"Приказ_{infection.replace(' ', '_')}_{now.strftime('%Y%m%d_%H%M%S')}.docx"
    file_path = DOCS_DIR / safe_name
    doc.save(str(file_path))
    return file_path


def generate_sop_disinfection(
    title: str = "СОП: Проведение текущей и генеральной дезинфекции в отделениях высокого эпидемиологического риска",
    sop_code: str = "СОП-ЭПИД-04/2026",
    department: str = "Процедурные, перевязочные и боксированные палаты",
    author: str = "Главная медицинская сестра / Госпитальный эпидемиолог",
    organization: Optional[str] = None
) -> Path:
    """
    Генерирует стандартную операционную процедуру (СОП) по дезинфекции и стерилизации.
    """
    doc = create_base_document()
    add_gost_header(doc, organization)

    # Гриф утверждения (в правом верхнем углу)
    p_app = doc.add_paragraph()
    p_app.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_app.paragraph_format.space_after = Pt(18)
    p_app.paragraph_format.line_spacing = 1.0
    r_app = p_app.add_run("УТВЕРЖДАЮ\nДиректор ФБУН ЦНИИЭ\nакадемик РАН\n___________ / В.Г. Акимкин /\n« ___ » ____________ 2026 г.\n")
    r_app.font.name = 'Times New Roman'
    r_app.font.size = Pt(11)
    r_app.font.bold = True

    # Заголовок СОП
    p_t = doc.add_paragraph()
    p_t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_t.paragraph_format.space_before = Pt(12)
    p_t.paragraph_format.space_after = Pt(4)
    r_t = p_t.add_run("СТАНДАРТНАЯ ОПЕРАЦИОННАЯ ПРОЦЕДУРА")
    r_t.font.name = 'Times New Roman'
    r_t.font.size = Pt(15)
    r_t.font.bold = True

    p_code = doc.add_paragraph()
    p_code.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_code.paragraph_format.space_after = Pt(14)
    r_code = p_code.add_run(f"Код: {sop_code}")
    r_code.font.name = 'Times New Roman'
    r_code.font.size = Pt(12)
    r_code.font.italic = True

    p_name = doc.add_paragraph()
    p_name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_name.paragraph_format.space_after = Pt(18)
    r_name = p_name.add_run(f"«{title}»")
    r_name.font.name = 'Times New Roman'
    r_name.font.size = Pt(13)
    r_name.font.bold = True

    # Паспортные данные СОП (Таблица)
    tbl = doc.add_table(rows=4, cols=2)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    tbl.columns[0].width = Mm(60)
    tbl.columns[1].width = Mm(105)

    meta = [
        ("Область применения:", department),
        ("Нормативная основа:", "СанПиН 3.3686-21 (разд. II), СанПиН 2.1.3678-20, ГОСТ Р 7.0.97-2016"),
        ("Разработчик / Ответственный:", author),
        ("Периодичность пересмотра:", "1 раз в 3 года (или внепланово при изменении СП/СанПиН)")
    ]
    for idx, (lbl, val) in enumerate(meta):
        c0, c1 = tbl.cell(idx, 0), tbl.cell(idx, 1)
        set_cell_background(c0, "F0F4F8")
        set_cell_margins(c0)
        set_cell_margins(c1)
        p0 = c0.paragraphs[0]
        r0 = p0.add_run(lbl)
        r0.font.name = 'Times New Roman'
        r0.font.size = Pt(10)
        r0.font.bold = True
        p1 = c1.paragraphs[0]
        r1 = p1.add_run(val)
        r1.font.name = 'Times New Roman'
        r1.font.size = Pt(10)

    # Текст разделов СОП
    sections = [
        ("1. Цель и задачи процедуры",
         "1.1. Стандартизация процессов дезинфекции и предстерилизационной очистки для обеспечения асептических условий и предупреждения заноса и распространения инфекций, связанных с оказанием медицинской помощи (ИСМП).\n"
         "1.2. Обеспечение безопасности пациентов и медперсонала при обращении с инфицированным биоматериалом."),
        
        ("2. Требования к средствам индивидуальной защиты (СИЗ)",
         "2.1. Медицинский персонал при приготовлении рабочих растворов дезинфицирующих средств и проведении уборок обязан использовать:\n"
         "  • Халат медицинский влагонепроницаемый или фартук клеенчатый;\n"
         "  • Перчатки резиновые хозяйственные повышенной плотности;\n"
         "  • Очки защитные закрытого типа (ГОСТ 12.4.253-2013);\n"
         "  • Респиратор противоаэрозольный (класс FFP2/FFP3)."),

        ("3. Порядок проведения текущей дезинфекции",
         "3.1. Текущая влажная уборка проводится не реже 2 раз в день с применением моюще-дезинфицирующих средств.\n"
         "3.2. Обработке подлежат: рабочие поверхности столов, манипуляционные столики, ручки дверей, краны раковин, кушетки после каждого пациента.\n"
         "3.3. Применяется метод протирания ветошью, смоченной рабочим раствором дезинфектанта с соблюдением экспозиционной выдержки (не менее 15–30 мин. согласно инструкции к препарату)."),

        ("4. Алгоритм генеральной уборки (1 раз в 7 дней)",
         "4.1. Освобождение помещения от медикаментов, стерильного материала и инструментов.\n"
         "4.2. Нанесение дезинфицирующего раствора на стены (на высоту не менее 2 м), потолок, двери, мебель и пол методом орошения или протирания.\n"
         "4.3. Выдержка экспозиции дезинфекции в закрытом помещении.\n"
         "4.4. Смывание дезсредства чистой водопроводной водой с использованием отдельного промаркированного инвентаря.\n"
         "4.5. Бактерицидное обеззараживание воздуха УФ-облучателями открытого типа в течение 60 мин. с последующим проветриванием (не менее 15 мин.)."),

        ("5. Контроль качества дезинфекции и ПСО",
         "5.1. Контроль качества предстерилизационной очистки (ПСО) проводится азопирамовой пробой на остаточную кровь и фенолфталеиновой пробой на остаточную щелочность.\n"
         "5.2. Результаты контроля заносятся в Журнал учета качества предстерилизационной обработки (форма № 257/у).\n"
         "5.3. Бактериологический контроль эффективности дезинфекции (смывы на БГКП, золотистый стафилококк, синегнойную палочку) проводится аккредитованной лабораторией не реже 1 раза в квартал.")
    ]

    for sec_title, sec_body in sections:
        p_st = doc.add_paragraph()
        p_st.paragraph_format.space_before = Pt(14)
        p_st.paragraph_format.space_after = Pt(4)
        r_st = p_st.add_run(sec_title)
        r_st.font.name = 'Times New Roman'
        r_st.font.size = Pt(12)
        r_st.font.bold = True

        p_sb = doc.add_paragraph()
        p_sb.paragraph_format.first_line_indent = Mm(12.5)
        p_sb.paragraph_format.space_after = Pt(6)
        p_sb.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        r_sb = p_sb.add_run(sec_body)
        r_sb.font.name = 'Times New Roman'
        r_sb.font.size = Pt(11)

    # Подписи разработчиков
    p_sig = doc.add_paragraph()
    p_sig.paragraph_format.space_before = Pt(24)
    p_sig.paragraph_format.space_after = Pt(4)
    r_sig = p_sig.add_run("Разработчик процедуры:\nГоспитальный эпидемиолог ___________________ / Е.В. Семенова /\nГлавная медицинская сестра ___________________ / М.И. Королева /")
    r_sig.font.name = 'Times New Roman'
    r_sig.font.size = Pt(11)

    now = datetime.now()
    safe_name = f"СОП_Дезинфекция_{now.strftime('%Y%m%d_%H%M%S')}.docx"
    file_path = DOCS_DIR / safe_name
    doc.save(str(file_path))
    return file_path


def generate_outbreak_investigation_act(
    disease: str = "Корь",
    fio: str = "Пациент А.Н.В.",
    department: str = "Терапевтическое отделение № 2",
    date_onset: str = "12.11.2026",
    contacts_count: int = 14,
    organization: Optional[str] = None
) -> Path:
    """
    Генерирует Акт / Карту эпидемиологического расследования очага инфекционного заболевания (форма 162/у).
    """
    doc = create_base_document()
    add_gost_header(doc, organization)

    p_t = doc.add_paragraph()
    p_t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_t.paragraph_format.space_before = Pt(12)
    p_t.paragraph_format.space_after = Pt(4)
    r_t = p_t.add_run("АКТ ЭПИДЕМИОЛОГИЧЕСКОГО РАССЛЕДОВАНИЯ ОЧАГА\nИНФЕКЦИОННОГО ЗАБОЛЕВАНИЯ")
    r_t.font.name = 'Times New Roman'
    r_t.font.size = Pt(14)
    r_t.font.bold = True

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_after = Pt(14)
    r_sub = p_sub.add_run("(составлен по форме № 162/у в соответствии с СанПиН 3.3686-21)")
    r_sub.font.name = 'Times New Roman'
    r_sub.font.size = Pt(10)
    r_sub.font.italic = True

    # Таблица сведений об очаге
    tbl = doc.add_table(rows=6, cols=2)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.columns[0].width = Mm(65)
    tbl.columns[1].width = Mm(100)

    rows_data = [
        ("Нозологическая форма (диагноз):", f"{disease} (код МКБ-10: B05.9)"),
        ("Ф.И.О. заболевшего / идентификатор:", fio),
        ("Место выявления очага:", department),
        ("Дата появления симптомов / сыпи:", date_onset),
        ("Количество контактных лиц:", f"{contacts_count} чел. (пациенты: 8, медперсонал: 6)"),
        ("Экстренное извещение ф. 058/у:", f"Передано в ТО Роспотребнадзора исх. № 412 от {date_onset}")
    ]
    for idx, (lbl, val) in enumerate(rows_data):
        c0, c1 = tbl.cell(idx, 0), tbl.cell(idx, 1)
        set_cell_background(c0, "F4F6F9")
        set_cell_margins(c0)
        set_cell_margins(c1)
        p0 = c0.paragraphs[0]
        r0 = p0.add_run(lbl)
        r0.font.name = 'Times New Roman'
        r0.font.size = Pt(10)
        r0.font.bold = True
        p1 = c1.paragraphs[0]
        r1 = p1.add_run(val)
        r1.font.name = 'Times New Roman'
        r1.font.size = Pt(10)

    # Противоэпидемические меры в очаге
    sections = [
        ("1. Эпидемиологический анамнез и источник инфекции",
         "Заболевший поступил в плановом порядке. Контакт с лихорадящими больными за 14 дней до госпитализации имел по месту жительства. Прививочный анамнез: сведений о вакцинации против кори в сертификате прививок нет."),
        
        ("2. Мероприятия в отношении заболевшего",
         "Пациент немедленно изолирован в боксированное инфекционное отделение. Назначена этиотропная и патогенетическая терапия. Отобран биоматериал: кровь на IgM к вирусу кори (ИФА) и соскоб из ротоглотки (ПЦР)."),

        ("3. Мероприятия в отношении контактных лиц",
         f"Установлен круг контактных лиц в количестве {contacts_count} человек. Проведена проверка вакцинального статуса:\n"
         "• Привито двукратно с подтвержденным титром IgG: 8 чел. (наблюдение без вакцинации);\n"
         "• Подлежат экстренной вакцинопрофилактике (не привиты, не болели): 6 чел. Вакцинация проведена коревой культуральной живой вакциной в первые 72 часа от момента контакта;\n"
         "• Установлено ежедневное медицинское наблюдение на 21 день с термометрией 2 раза в день."),

        ("4. Дезинфекционные мероприятия",
         "В палате пребывания больного проведена заключительная дезинфекция с применением кислородактивных дезинфицирующих средств. Проведено ультрафиолетовое обеззараживание воздуха бактерицидными установками.")
    ]

    for st, sb in sections:
        p_h = doc.add_paragraph()
        p_h.paragraph_format.space_before = Pt(12)
        p_h.paragraph_format.space_after = Pt(2)
        rh = p_h.add_run(st)
        rh.font.name = 'Times New Roman'
        rh.font.size = Pt(11)
        rh.font.bold = True

        p_b = doc.add_paragraph()
        p_b.paragraph_format.first_line_indent = Mm(12.5)
        p_b.paragraph_format.space_after = Pt(4)
        p_b.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        rb = p_b.add_run(sb)
        rb.font.name = 'Times New Roman'
        rb.font.size = Pt(11)

    p_sign = doc.add_paragraph()
    p_sign.paragraph_format.space_before = Pt(20)
    rsign = p_sign.add_run(
        "Врач-эпидемиолог ___________________ / Е.В. Семенова /\n"
        "Заведующий отделением ___________________ / Д.А. Куликов /\n"
        f"Дата составления акта: {datetime.now().strftime('%d.%m.%Y')}"
    )
    rsign.font.name = 'Times New Roman'
    rsign.font.size = Pt(11)

    now = datetime.now()
    safe_name = f"Акт_эпидрасследования_{disease}_{now.strftime('%Y%m%d_%H%M%S')}.docx"
    file_path = DOCS_DIR / safe_name
    doc.save(str(file_path))
    return file_path


def generate_document_by_request(
    doc_type: str,
    params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Универсальный фасад генерации документов под свободный запрос пользователя.
    """
    infection = params.get("infection") or params.get("disease") or "корь"
    department = params.get("department") or "Отделение стационара"
    org = params.get("organization")
    
    if doc_type in ("order", "order_infection_outbreak", "prikaz"):
        title = params.get("title") or f"Приказ о проведении противоэпидемических мероприятий ({infection})"
        fp = generate_epidemiology_order(
            title=title,
            infection=infection,
            department=department,
            organization=org
        )
    elif doc_type in ("sop", "sop_disinfection"):
        fp = generate_sop_disinfection(
            title=params.get("title") or "СОП: Проведение текущей и генеральной дезинфекции",
            department=department,
            organization=org
        )
    elif doc_type in ("act", "investigation_act", "outbreak_act"):
        fp = generate_outbreak_investigation_act(
            disease=infection,
            department=department,
            organization=org
        )
    else:
        # Fallback to standard order
        fp = generate_epidemiology_order(
            title=f"Приказ о противоэпидемических мероприятиях: {infection}",
            infection=infection,
            department=department,
            organization=org
        )

    file_name = fp.name
    return {
        "status": "success",
        "file_name": file_name,
        "relative_path": f"generated_documents/{file_name}",
        "download_url": f"/api/catalog/download/{quote(file_name)}",
        "size_bytes": fp.stat().st_size,
        "format": "docx",
        "standard": "ГОСТ Р 7.0.97-2016"
    }


def compile_agent_composed_document(doc_model: Dict[str, Any]) -> Dict[str, Any]:
    """
    Инструмент верстки Агента: компилирует произвольную структуру документа,
    сформированную агентом (включая многоуровневые секции, произвольные таблицы,
    списки требований, визы и гриф «Утвержденный образец»).
    """
    doc = create_base_document()
    add_gost_header(doc, doc_model.get("organization"))

    # Гриф утверждения / признак «Утвержденный образец»
    if doc_model.get("is_approved"):
        p_app = doc.add_paragraph()
        p_app.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_app.paragraph_format.space_after = Pt(8)
        p_app.paragraph_format.line_spacing = 1.0
        r_app = p_app.add_run(
            f"✓ УТВЕРЖДЕННЫЙ ЭТАЛОННЫЙ ОБРАЗЕЦ\n"
            f"{doc_model.get('authority', 'ФБУН ЦНИИЭ Роспотребнадзора')}\n"
            f"Стандарт: {doc_model.get('standard', 'ГОСТ Р 7.0.97-2016')} | {doc_model.get('sanpin', 'СанПиН 3.3686-21')}\n"
        )
        r_app.font.name = 'Times New Roman'
        r_app.font.size = Pt(9)
        r_app.font.bold = True
        r_app.font.color.rgb = RGBColor(0, 100, 0)

    # Вид документа
    doc_type_str = str(doc_model.get("doc_type", "ПРИКАЗ")).upper()
    p_t = doc.add_paragraph()
    p_t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_t.paragraph_format.space_before = Pt(6)
    p_t.paragraph_format.space_after = Pt(10)
    rt = p_t.add_run(doc_type_str)
    rt.font.name = 'Times New Roman'
    rt.font.size = Pt(16)
    rt.font.bold = True

    # Реквизиты документа (Дата / Номер / Город)
    tbl_m = doc.add_table(rows=1, cols=2)
    tbl_m.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_m.columns[0].width = Mm(80)
    tbl_m.columns[1].width = Mm(85)
    
    cl = tbl_m.cell(0, 0)
    pl = cl.paragraphs[0]
    pl.paragraph_format.space_after = Pt(0)
    d_val = doc_model.get("date") or datetime.now().strftime("%d.%m.%Y")
    rl = pl.add_run(f"Дата: {d_val}")
    rl.font.name = 'Times New Roman'
    rl.font.size = Pt(12)

    cr = tbl_m.cell(0, 1)
    pr = cr.paragraphs[0]
    pr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    pr.paragraph_format.space_after = Pt(0)
    n_val = doc_model.get("number") or "1-ЭПИД"
    c_val = doc_model.get("city") or "г. Москва"
    rr = pr.add_run(f"№ {n_val}\n{c_val}")
    rr.font.name = 'Times New Roman'
    rr.font.size = Pt(12)

    # Заголовок документа
    title = doc_model.get("title")
    if title:
        p_subj = doc.add_paragraph()
        p_subj.paragraph_format.space_before = Pt(16)
        p_subj.paragraph_format.space_after = Pt(10)
        p_subj.paragraph_format.first_line_indent = Mm(12.5)
        p_subj.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        r_subj = p_subj.add_run(title)
        r_subj.font.name = 'Times New Roman'
        r_subj.font.size = Pt(13)
        r_subj.font.bold = True

    # Преамбула
    preamble = doc_model.get("preamble")
    if preamble:
        p_pre = doc.add_paragraph()
        p_pre.paragraph_format.first_line_indent = Mm(12.5)
        p_pre.paragraph_format.space_after = Pt(10)
        p_pre.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        r_pre = p_pre.add_run(preamble)
        r_pre.font.name = 'Times New Roman'
        r_pre.font.size = Pt(12)

    # Распорядительное слово (если это приказ)
    if "ПРИКАЗ" in doc_type_str:
        p_cmd = doc.add_paragraph()
        p_cmd.paragraph_format.space_before = Pt(4)
        p_cmd.paragraph_format.space_after = Pt(6)
        p_cmd.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rcmd = p_cmd.add_run("ПРИКАЗЫВАЮ:")
        rcmd.font.name = 'Times New Roman'
        rcmd.font.size = Pt(13)
        rcmd.font.bold = True

    # Секции документа, сверстанные агентом
    sections = doc_model.get("sections", [])
    for sec in sections:
        sec_h = sec.get("heading")
        if sec_h:
            p_sh = doc.add_paragraph()
            p_sh.paragraph_format.space_before = Pt(12)
            p_sh.paragraph_format.space_after = Pt(4)
            rsh = p_sh.add_run(sec_h)
            rsh.font.name = 'Times New Roman'
            rsh.font.size = Pt(12)
            rsh.font.bold = True

        sec_t = sec.get("text")
        if sec_t:
            p_st = doc.add_paragraph()
            p_st.paragraph_format.first_line_indent = Mm(12.5)
            p_st.paragraph_format.space_after = Pt(6)
            p_st.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            rst = p_st.add_run(sec_t)
            rst.font.name = 'Times New Roman'
            rst.font.size = Pt(12)

        # Списки пунктов
        sec_items = sec.get("items", [])
        for idx, item in enumerate(sec_items, 1):
            p_it = doc.add_paragraph()
            p_it.paragraph_format.first_line_indent = Mm(12.5)
            p_it.paragraph_format.space_after = Pt(4)
            p_it.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            prefix = f"{idx}. " if not item.strip().startswith(f"{idx}.") else ""
            rit = p_it.add_run(f"{prefix}{item}")
            rit.font.name = 'Times New Roman'
            rit.font.size = Pt(12)

        # Таблицы, сверстанные агентом
        sec_table = sec.get("table")
        if sec_table and isinstance(sec_table, dict):
            headers = sec_table.get("headers", [])
            rows = sec_table.get("rows", [])
            if headers:
                num_cols = len(headers)
                t_elem = doc.add_table(rows=len(rows) + 1, cols=num_cols)
                t_elem.alignment = WD_TABLE_ALIGNMENT.CENTER
                t_elem.autofit = True

                # Оформление шапки таблицы
                for c_idx, h_text in enumerate(headers):
                    hdr_cell = t_elem.cell(0, c_idx)
                    set_cell_background(hdr_cell, "F0F4F8")
                    set_cell_margins(hdr_cell)
                    hp = hdr_cell.paragraphs[0]
                    hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    hr = hp.add_run(str(h_text))
                    hr.font.name = 'Times New Roman'
                    hr.font.size = Pt(10)
                    hr.font.bold = True

                # Оформление строк
                for r_idx, row_data in enumerate(rows, 1):
                    for c_idx, cell_value in enumerate(row_data[:num_cols]):
                        d_cell = t_elem.cell(r_idx, c_idx)
                        set_cell_margins(d_cell)
                        dp = d_cell.paragraphs[0]
                        dr = dp.add_run(str(cell_value))
                        dr.font.name = 'Times New Roman'
                        dr.font.size = Pt(10)

    # Если разделов нет, но есть список действий actions
    actions = doc_model.get("actions", [])
    if actions and not sections:
        for idx, act in enumerate(actions, 1):
            p_act = doc.add_paragraph()
            p_act.paragraph_format.first_line_indent = Mm(12.5)
            p_act.paragraph_format.space_after = Pt(5)
            p_act.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            prefix = f"{idx}. " if not act.strip().startswith(f"{idx}.") else ""
            ract = p_act.add_run(f"{prefix}{act}")
            ract.font.name = 'Times New Roman'
            ract.font.size = Pt(12)

    # Подписи
    signatures = doc_model.get("signatures", [])
    if not signatures:
        signatures = [
            {"position": doc_model.get("head_doctor", "Директор института / Главный врач"), "name": "Подпись"}
        ]
    
    for sig in signatures:
        p_sig = doc.add_paragraph()
        p_sig.paragraph_format.space_before = Pt(18)
        p_sig.paragraph_format.space_after = Pt(10)
        p_sig.paragraph_format.line_spacing = 1.0
        rs1 = p_sig.add_run(f"{sig.get('position', 'Руководитель')}\t\t\t\t\t")
        rs1.font.name = 'Times New Roman'
        rs1.font.size = Pt(12)
        rs1.font.bold = True
        rs2 = p_sig.add_run(f"___________________ / {sig.get('name', 'Подпись')} /")
        rs2.font.name = 'Times New Roman'
        rs2.font.size = Pt(12)

    # Визы
    visas = doc_model.get("visas", [])
    if not visas and doc_model.get("hospital_epidemiologist"):
        visas = [f"Госпитальный эпидемиолог: ___________________ / {doc_model.get('hospital_epidemiologist')} /"]

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

    # Сохранение файла
    now_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    tag = re.sub(r'[^a-zA-Zа-яА-Я0-9]', '_', doc_model.get("tag", "custom_doc"))
    filename = f"{tag}_{now_ts}.docx"
    file_path = DOCS_DIR / filename
    doc.save(str(file_path))

    return {
        "status": "success",
        "file_name": filename,
        "relative_path": f"generated_documents/{filename}",
        "download_url": f"/api/catalog/download/{quote(filename)}",
        "size_bytes": file_path.stat().st_size,
        "format": "docx",
        "standard": doc_model.get("standard", "ГОСТ Р 7.0.97-2016"),
        "is_approved": doc_model.get("is_approved", False)
    }
