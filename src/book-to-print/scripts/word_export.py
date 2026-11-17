# -*- coding: utf-8 -*-
"""Word (through COM, Windows) for a book: inspect the page setup, set it up for print, export the PDF.

    python word_export.py inspect <book.docx>
    python word_export.py setup   <book.docx> <out.docx> --trim 170 240 --inner 23 --outer 17
                                  --top 24 --bottom 21 [--direction rtl|ltr]
    python word_export.py export  <book.docx> <out.pdf>

setup writes a COPY (the original is never changed): one page size in every section, mirror margins,
no gutter. Word mirrors margins for a book bound on the LEFT. In a Hebrew book the odd page is the
left-hand page, bound on its right, so for rtl the outer margin goes into Word's "Inside" (left) field
and the inner one into "Outside" (right). Always confirm with check_interior.py on the exported PDF.
export uses Word's own PDF engine with fonts embedded, optimised for print; a font Word may not embed
comes out as an image (Type3), and the report says so.
"""
import argparse
import sys
from pathlib import Path

from common import PT_PER_MM, fail, mm_from_pt

WD_EXPORT_PDF = 17
WD_OPTIMIZE_PRINT = 0
WD_HEADINGS_BOOKMARKS = 1
WD_FORMAT_DOCX = 16
WD_STAT_PAGES = 2
WD_GUTTER_LEFT = 0


def word():
    try:
        import win32com.client
    except ImportError:
        fail("חסרה הספרייה pywin32. הרץ: python -m pip install pywin32 (או setup_check.py).")
    try:
        app = win32com.client.DispatchEx("Word.Application")
    except Exception as e:      # noqa: BLE001 - COM raises its own types
        fail(f"לא הצלחתי לפתוח את Word ({e}). צריך Microsoft Word מותקן במחשב.")
    app.Visible, app.DisplayAlerts = False, 0
    return app


def open_doc(app, path, read_only):
    full = str(Path(path).resolve())
    if not Path(full).is_file():
        app.Quit()
        fail(f"הקובץ {full} לא נמצא.")
    return app.Documents.Open(full, ReadOnly=read_only, AddToRecentFiles=False)


def section_rows(doc):
    rows = []
    for i, sec in enumerate(doc.Sections, 1):
        ps = sec.PageSetup
        rows.append({"section": i, "w": mm_from_pt(ps.PageWidth), "h": mm_from_pt(ps.PageHeight),
                     "left": mm_from_pt(ps.LeftMargin), "right": mm_from_pt(ps.RightMargin),
                     "top": mm_from_pt(ps.TopMargin), "bottom": mm_from_pt(ps.BottomMargin),
                     "gutter": mm_from_pt(ps.Gutter), "mirror": bool(ps.MirrorMargins)})
    return rows


def inspect(path):
    app = word()
    try:
        doc = open_doc(app, path, True)
        rows, pages = section_rows(doc), doc.ComputeStatistics(WD_STAT_PAGES)
        doc.Close(False)
    finally:
        app.Quit()
    print(f"{path}: {pages} עמודים, {len(rows)} מקטעים")
    for r in rows:
        print(f"  מקטע {r['section']}: דף {r['w']:.1f}x{r['h']:.1f} מ\"מ | שמאל {r['left']:.1f} ימין {r['right']:.1f} "
              f"עליון {r['top']:.1f} תחתון {r['bottom']:.1f} | שוליים לכריכה {r['gutter']:.1f} | "
              f"שולי מראה: {'כן' if r['mirror'] else 'לא'}")
    advice(rows)


def advice(rows):
    sizes = {(round(r["w"], 1), round(r["h"], 1)) for r in rows}
    if len(sizes) > 1:
        print(f"בעיה: גודלי דף שונים במקטעים {sorted(sizes)} - כל הספר צריך גודל אחד.")
    if not all(r["mirror"] for r in rows):
        print("בעיה: שולי מראה כבויים - השוליים ליד השדרה לא יתחלפו בין עמוד זוגי לאי-זוגי.")
    if any(r["gutter"] > 0 for r in rows):
        print("הערה: מוגדרים 'שוליים לכריכה' (gutter). עדיף 0 ולהכניס את התוספת לשוליים עצמם.")
    if rows and abs(rows[0]["w"] - 210) < 1 and abs(rows[0]["h"] - 297) < 1:
        print("הערה: הדף בגודל A4. ספר מודפס כמעט תמיד קטן יותר - לקבוע את גודל הדף הסופי לפני העימוד.")


def setup(path, out, a):
    if Path(out).resolve() == Path(path).resolve():
        fail("setup כותב עותק חדש. תן שם קובץ אחר לפלט.")
    outer_left = a.direction == "rtl"
    app = word()
    try:
        doc = open_doc(app, path, False)
        doc.PageSetup.MirrorMargins = True
        for sec in doc.Sections:
            ps = sec.PageSetup
            ps.PageWidth, ps.PageHeight = a.trim[0] * PT_PER_MM, a.trim[1] * PT_PER_MM
            ps.Gutter, ps.GutterPos = 0, WD_GUTTER_LEFT
            ps.TopMargin, ps.BottomMargin = a.top * PT_PER_MM, a.bottom * PT_PER_MM
            left, right = (a.outer, a.inner) if outer_left else (a.inner, a.outer)
            ps.LeftMargin, ps.RightMargin = left * PT_PER_MM, right * PT_PER_MM
        doc.SaveAs2(str(Path(out).resolve()), FileFormat=WD_FORMAT_DOCX)
        pages = doc.ComputeStatistics(WD_STAT_PAGES)
        doc.Close(False)
    finally:
        app.Quit()
    print(f"נשמר {out}: דף {a.trim[0]:g}x{a.trim[1]:g}, פנימי {a.inner:g}, חיצוני {a.outer:g}, {pages} עמודים.")
    print("הבא: export ואז check_interior.py --expect כדי לוודא שהשוליים יצאו בצד הנכון.")


def export(path, out):
    app = word()
    try:
        doc = open_doc(app, path, True)
        doc.ExportAsFixedFormat(str(Path(out).resolve()), WD_EXPORT_PDF, OpenAfterExport=False,
                                OptimizeFor=WD_OPTIMIZE_PRINT, IncludeDocProps=True, KeepIRM=True,
                                CreateBookmarks=WD_HEADINGS_BOOKMARKS, DocStructureTags=True,
                                BitmapMissingFonts=True, UseISO19005_1=False)
        doc.Close(False)
    finally:
        app.Quit()
    fonts_report(out)


def fonts_report(pdf_path):
    import fitz
    doc = fitz.open(pdf_path)
    fonts = {f[3]: (f[1], f[2]) for p in doc for f in p.get_fonts(full=True)}
    print(f"PDF: {pdf_path} - {len(doc)} עמודים, {len(fonts)} גופנים")
    for name, (ext, kind) in sorted(fonts.items()):
        state = "הפך לתמונה - להחליף גופן" if kind == "Type3" else ("לא מוטמע!" if ext in ("", "n/a") else "מוטמע")
        print(f"  {name}: {state}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inspect").add_argument("docx")
    s = sub.add_parser("setup")
    s.add_argument("docx"), s.add_argument("out")
    s.add_argument("--trim", nargs=2, type=float, required=True)
    for name in ("inner", "outer", "top", "bottom"):
        s.add_argument(f"--{name}", type=float, required=True)
    s.add_argument("--direction", choices=("rtl", "ltr"), default="rtl")
    e = sub.add_parser("export")
    e.add_argument("docx"), e.add_argument("out")
    a = ap.parse_args()
    if sys.platform != "win32":
        fail("הכלי הזה עובד רק ב-Windows עם Word מותקן. ב-Mac: לייצא ל-PDF מ-Word ידנית (שמירה בשם > PDF > 'הטוב ביותר להדפסה').")
    {"inspect": lambda: inspect(a.docx), "setup": lambda: setup(a.docx, a.out, a),
     "export": lambda: export(a.docx, a.out)}[a.cmd]()


if __name__ == "__main__":
    main()
