# -*- coding: utf-8 -*-
"""Markdown (headings, paragraphs, bullets, numbered items, tables) -> an RTL Hebrew Word file.

Black and white, David 12 pt and up, headings centred, A4 with 2 cm margins, page numbers.
Two RTL rules that must not be broken: w:bidi is INSERTED before w:jc (never appended), and Hebrew
paragraphs never get jc="right" (in a bidi paragraph that means the LEFT side).
"""
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

FONT = "David"
BODY_PT = 12
HEADING_PT = {1: 18, 2: 16, 3: 14}
MARGIN_CM = 2
USABLE_CM = 17.0
GREY = "D9D9D9"
PPR_SEQ = ("w:pStyle", "w:keepNext", "w:keepLines", "w:pageBreakBefore", "w:framePr", "w:widowControl",
           "w:numPr", "w:suppressLineNumbers", "w:pBdr", "w:shd", "w:tabs", "w:suppressAutoHyphens",
           "w:kinsoku", "w:wordWrap", "w:overflowPunct", "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN",
           "w:bidi", "w:adjustRightInd", "w:snapToGrid", "w:spacing", "w:ind", "w:contextualSpacing",
           "w:mirrorIndents", "w:suppressOverlap", "w:jc", "w:textDirection", "w:textAlignment",
           "w:textboxTightWrap", "w:outlineLvl", "w:divId", "w:cnfStyle", "w:rPr", "w:sectPr", "w:pPrChange")


def after(tag):
    return PPR_SEQ[PPR_SEQ.index(tag) + 1:]


def rtl_paragraph(p):
    ppr = p._p.get_or_add_pPr()
    if ppr.find(qn("w:bidi")) is None:
        ppr.insert_element_before(OxmlElement("w:bidi"), *after("w:bidi"))


def style_run(run, size=BODY_PT, bold=False):
    run.font.name, run.font.size, run.font.bold = FONT, Pt(max(size, BODY_PT)), bold
    run.font.color.rgb = RGBColor(0, 0, 0)
    rpr = run._r.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    for attr in ("w:cs", "w:ascii", "w:hAnsi"):
        fonts.set(qn(attr), FONT)
    size_cs = OxmlElement("w:szCs")
    size_cs.set(qn("w:val"), str(int(max(size, BODY_PT) * 2)))
    rpr.append(size_cs)
    if bold:
        rpr.append(OxmlElement("w:bCs"))
    rpr.append(OxmlElement("w:rtl"))
    lang = OxmlElement("w:lang")
    lang.set(qn("w:val"), "he-IL")
    lang.set(qn("w:bidi"), "he-IL")
    rpr.append(lang)


def add_text(p, text, size=BODY_PT, bold=False):
    for i, part in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
        if part:
            style_run(p.add_run(part), size, bold or i % 2 == 1)


def paragraph(doc, text, size=BODY_PT, bold=False, centre=False, bullet=None):
    p = doc.add_paragraph()
    rtl_paragraph(p)
    if centre:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(4)
    if bullet:
        p.paragraph_format.left_indent, p.paragraph_format.first_line_indent = Cm(0.5), Cm(-0.5)
        text = f"{bullet}\t{text}"
    add_text(p, text, size, bold)
    return p


def heading(doc, text, level):
    p = paragraph(doc, text, HEADING_PT.get(level, 13), bold=True, centre=True)
    p.paragraph_format.space_before, p.paragraph_format.keep_with_next = Pt(12), True


def borders(table):
    tbl_pr = table._tbl.tblPr
    edges = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = OxmlElement(f"w:{edge}")
        for k, v in (("w:val", "single"), ("w:sz", "4"), ("w:color", "000000")):
            b.set(qn(k), v)
        edges.append(b)
    tbl_pr.append(edges)
    tbl_pr.append(OxmlElement("w:bidiVisual"))


def cell(c, text, header):
    c.text = ""
    p = c.paragraphs[0]
    rtl_paragraph(p)
    add_text(p, text, bold=header)
    if header:
        shd = OxmlElement("w:shd")
        for k, v in (("w:val", "clear"), ("w:color", "auto"), ("w:fill", GREY)):
            shd.set(qn(k), v)
        c._tc.get_or_add_tcPr().append(shd)


def table(doc, rows):
    head, body = rows[0], rows[1:]
    t = doc.add_table(rows=len(rows), cols=len(head))
    borders(t)
    weights = [max(3, sum(len(r[i]) for r in rows if i < len(r)) / len(rows)) ** 0.5 for i in range(len(head))]
    for r, row in enumerate([head] + body):
        t.rows[r]._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        for i in range(len(head)):
            cell(t.rows[r].cells[i], row[i] if i < len(row) else "", r == 0 and any(head))
            t.rows[r].cells[i].width = Cm(USABLE_CM * weights[i] / sum(weights))
    doc.add_paragraph()


def page_numbers(section):
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    for kind, text in (("begin", None), (None, "PAGE"), ("end", None)):
        if kind:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = text
        run._r.append(el)
    style_run(run)


def setup_page(doc):
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Cm(MARGIN_CM))
    sec._sectPr.append(OxmlElement("w:bidi"))
    sec._sectPr.append(OxmlElement("w:rtlGutter"))
    page_numbers(sec)


def table_rows(lines, i):
    rows = []
    while i < len(lines) and lines[i].startswith("|"):
        if not re.match(r"^\|[\s\-:|]+\|$", lines[i]):
            rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
        i += 1
    return rows, i


def write_docx(md, path):
    doc = Document()
    setup_page(doc)
    lines, i = md.splitlines(), 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("|"):
            rows, i = table_rows(lines, i)
            table(doc, rows)
            continue
        m = re.match(r"^(#{1,3}) (.+)", line)
        num = re.match(r"^(\d+)\. (.+)", line)
        if m:
            heading(doc, m.group(2), len(m.group(1)))
        elif line.startswith("- "):
            paragraph(doc, line[2:], bullet="•")
        elif num:
            paragraph(doc, num.group(2), bullet=f"‏{num.group(1)}.")
        elif line:
            paragraph(doc, line)
        i += 1
    doc.save(path)
