"""Gemini Vision OCR for Hebrew Ministry of Education forms.

Usage:
    export GEMINI_API_KEY=AIza...
    python gemini_ocr.py <image_dir> <output_json> [--prompt-type bitsua|tlush|generic]

Reads all PNG files in image_dir, sends each to Gemini 2.5 Pro Vision with a
Hebrew-specific prompt, saves structured JSON. Supports incremental resume — if
output_json exists, only processes images not yet present as keys.
"""
import os, sys, json, time, argparse
import google.generativeai as genai
import PIL.Image

# Windows pipes stdout/stderr through the ANSI code page by default; force
# UTF-8 so Hebrew filenames in progress output don't crash the run.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        _stream.reconfigure(encoding='utf-8', errors='replace')


PROMPT_BITSUA = """המסמך בעברית, דוח ביצוע על תשלום מענקי החזר שכר לימוד למשרד החינוך, עם כתב יד.
חלץ במדויק את הנתונים הבאים. אם שדה לא ברור או חסר, רשום null.

החזר רק JSON תקין במבנה:
{
  "שם_המוסד": "...",
  "סמל_מוטב": "...",
  "כתובת_המוסד": "...",
  "שם_איש_קשר": "...",
  "טלפון_איש_קשר": "...",
  "תקופת_דיווח": "...",
  "מורים": [
    {
      "מס_שורה": 1,
      "ת.ז": "9-digit ID",
      "שם_משפחה": "...",
      "שם_פרטי": "...",
      "טלפון_זמין": "...",
      "סכום_משרד_החינוך": NUMBER,
      "תשלומים_חודשיים": [{"חודש":"MM/YY", "סכום":NUMBER}],
      "סהכ_שולם_למורה": NUMBER
    }
  ]
}"""


PROMPT_TLUSH = """המסמך בעברית — תלוש שכר ממערכת מיכפל 2000.
חלץ את פרטי המורה והנתונים הפיננסיים. אם שדה לא ברור — null.

החזר JSON:
{
  "שם_מורה": "...", "ת.ז": "...", "טלפון": "...", "כתובת": "...",
  "שם_מעסיק": "...", "מספר_עובד": "...", "מחלקה": "...",
  "תיק_ניכויים": "...", "חודש_תלוש": "MM/YYYY",
  "שכר_ברוטו": NUM, "שכר_נטו": NUM,
  "מענק_שכר_לימוד": NUM,
  "החזר_הוצאות": [{"שם": "...", "סכום": NUM}],
  "הפרשה_לגמל_עובד": NUM, "הפרשה_לגמל_מעסיק": NUM
}"""


PROMPT_GENERIC = """המסמך בעברית. סווג ולחלץ.

סוגים: A=אישור משרד החינוך פר מורה | B=תלוש שכר | C=דוח ביצוע (טבלת מורים) | D=אישור BDO | E=ריק/לא רלוונטי

החזר JSON:
{
  "סוג_מסמך": "A|B|C|D|E",
  "שם_מוסד": "...", "סמל_מוטב": "...", "מס_עמותה": "...",
  "פרטי_מורה": {"שם_מלא":"...","ת.ז":"...","כתובת":"...","טלפון":"...",
                "חודש_תלוש":"MM/YYYY","סכום_מענק":NUM,"סכום_שכר_כולל":NUM,
                "הפרשה_לגמל":NUM},
  "מורים_בטבלה": [{"מס_שורה":N,"ת.ז":"...","שם_משפחה":"...","שם_פרטי":"...",
                  "סכום_משרד_החינוך":NUM,"סהכ_שולם_למורה":NUM,"חודשים":"..."}],
  "תאריך": "...", "הערות": "..."
}
מלא רק שדות רלוונטיים, השאר null."""


PROMPTS = {
    'bitsua': PROMPT_BITSUA,
    'tlush': PROMPT_TLUSH,
    'generic': PROMPT_GENERIC,
}


def ocr_image(model, prompt, img_path):
    img = PIL.Image.open(img_path)
    try:
        resp = model.generate_content([prompt, img])
        text = resp.text.strip()
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
            text = text.strip()
        return json.loads(text)
    except Exception as e:
        return {'error': str(e)[:300]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('source', help='Directory of PNG images OR single image')
    p.add_argument('output', help='Output JSON file')
    p.add_argument('--prompt-type', default='generic', choices=list(PROMPTS.keys()))
    p.add_argument('--model', default='gemini-2.5-pro')
    p.add_argument('--api-key', default=os.environ.get('GEMINI_API_KEY'))
    p.add_argument('--sleep', type=float, default=2.0)
    args = p.parse_args()

    if not args.api_key:
        sys.exit('Set GEMINI_API_KEY env var or pass --api-key')
    genai.configure(api_key=args.api_key)
    model = genai.GenerativeModel(args.model)

    if os.path.isdir(args.source):
        files = sorted([os.path.join(args.source, f) for f in os.listdir(args.source) if f.lower().endswith('.png')])
    else:
        files = [args.source]

    if os.path.exists(args.output):
        results = json.load(open(args.output, encoding='utf-8'))
    else:
        results = {}

    prompt = PROMPTS[args.prompt_type]
    for i, fp in enumerate(files):
        key = os.path.basename(fp).replace('.png', '')
        if key in results and 'error' not in results[key]:
            continue
        print(f'[{i+1}/{len(files)}] OCR {key}', file=sys.stderr, flush=True)
        results[key] = ocr_image(model, prompt, fp)
        time.sleep(args.sleep)
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    print(f'DONE — {len(results)} results in {args.output}')


if __name__ == '__main__':
    main()
