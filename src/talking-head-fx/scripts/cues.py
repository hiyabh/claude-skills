"""Speech cues -> effect candidates for plan_fx.py.

Each rule: effect type, words/stems that trigger it (Hebrew + English), base score, default duration, and whether it needs a matted subject.
Scores rank competing candidates; plan_fx.py then enforces pacing and variety.
Matching (plan_fx.match_cue): a one-word cue matches a whole word after stripping Hebrew
prefixes (ו ה ב ל מ ש כ), or a word's start when the cue has 4+ letters; a multi-word cue matches
as a phrase; "!", "?" and "%" match the character.
Edit this table to tune when an effect fires - it is the "use it when needed" logic.
"""

RULES = {
    "growth_chart": dict(score=9, dur=2.6, matte=True, cues=[
        "אחוז", "%", "פי", "גדל", "צמיחה", "הכפיל", "מיליון", "אלף", "מכירות", "הכנסות", "עלייה",
        "percent", "grew", "growth", "doubled", "million", "revenue", "x more"]),
    "checklist_pop": dict(score=8, dur=2.4, matte=False, cues=[
        "ראשון", "שני", "שלישי", "שלושה", "שלוש", "ארבעה", "כמה דברים", "שלבים", "צעד", "רשימה", "טיפים",
        "first", "second", "third", "three things", "steps", "checklist", "tips"]),
    "chat_takeover": dict(score=8, dur=2.6, matte=False, cues=[
        "צ'אט", "צאט", "קלוד", "claude", "gpt", "ג'מיני", "בינה מלאכותית", "ai", "פרומפט", "שאלתי את",
        "chatbot", "prompt", "asked it"]),
    "phone_mockup": dict(score=7, dur=2.6, matte=False, cues=[
        "טלפון", "אפליקציה", "אינסטגרם", "טיקטוק", "וואטסאפ", "נייד", "סמארטפון", "רילס", "סטורי",
        "phone", "app", "instagram", "tiktok", "whatsapp", "reels"]),
    "broll_layers": dict(score=6, dur=3.0, matte=False, cues=[
        "עריכה", "עורך", "טיימליין", "קטעים", "פרויקט", "הקלטה", "צילמתי", "מצגת",
        "editing", "timeline", "footage", "b-roll", "project"]),
    "studio": dict(score=6, dur=2.6, matte=True, cues=[
        "שידור", "חדשות", "ראיון", "פודקאסט", "אולפן", "מיקרופון", "לייב",
        "broadcast", "news", "interview", "podcast", "studio", "live"]),
    "magazine_cover": dict(score=6, dur=2.6, matte=True, cues=[
        "כתבה", "עיתון", "מגזין", "שער", "מפורסם", "סיפור הצלחה", "פרס",
        "article", "magazine", "cover", "famous", "award"]),
    "green_screen": dict(score=6, dur=2.8, matte=True, cues=[
        "בעולם", "בחו\"ל", "נסיעה", "טיסה", "בעיר", "תדמיינו", "דמיינו", "מקום אחר",
        "imagine", "travel", "abroad", "around the world"]),
    "headline_storm": dict(score=7, dur=2.2, matte=False, cues=[
        "כולם מדברים", "ויראלי", "טרנד", "כותרות", "רעש", "בכל מקום",
        "everyone is talking", "viral", "trend", "headlines"]),
    "frame_escape": dict(score=7, dur=2.4, matte=True, cues=[
        "לצאת", "מחוץ לקופסה", "חופש", "לברוח", "גבולות", "לשבור את", "פריצה",
        "break out", "outside the box", "escape", "limits"]),
    "frame_break": dict(score=7, dur=1.4, matte=False, cues=[
        "מטורף", "פיצוץ", "בום", "הלם", "מהפכה", "לא תאמינו", "שבר",
        "crazy", "boom", "shock", "revolution", "you won't believe"]),
    "digital_zoom": dict(score=6, dur=2.2, matte=False, cues=[
        "תראו", "שימו לב", "תסתכלו", "מקרוב", "בדיוק פה", "פרט קטן",
        "look", "watch this", "closer", "notice"]),
    "portal_zoom": dict(score=4, dur=2.0, matte=False, cues=[
        "אישית", "הרגשתי", "התגובה שלי", "הפרצוף", "בעצמי",
        "personally", "i felt", "my reaction"]),
    "liquid_glass": dict(score=4, dur=2.0, matte=False, cues=[
        "סוד", "קסם", "מאחורי הקלעים", "שקוף", "תכלס",
        "secret", "magic", "behind the scenes", "transparent"]),
    "paper_cutout": dict(score=4, dur=2.4, matte=True, cues=[
        "פשוט", "קל", "כיף", "יצירתי", "בעצמכם",
        "simple", "easy", "fun", "creative", "diy"]),
    "orbit_ui": dict(score=5, dur=2.0, matte=False, cues=[
        "כלים", "אפשרויות", "יכולות", "פיצ'רים", "הכל במקום אחד",
        "tools", "features", "options", "all in one"]),
    "punch_zoom": dict(score=3, dur=1.2, matte=False, cues=[
        "הכי", "חשוב", "באמת", "אף פעם", "תמיד", "לעולם", "חייבים", "!",
        "most", "important", "never", "always", "must"]),
    "jump_zoom": dict(score=3, dur=1.0, matte=False, cues=[
        "אבל", "רגע", "בדיוק", "נכון?", "?", "but", "wait", "exactly", "right?"]),
    "recap_checklist": dict(score=9, dur=4.0, matte=False, cues=[
        "לסיכום", "בקיצור", "אז מה למדנו", "לסכם", "in summary", "to recap", "so to sum up"]),
}

# Effects that need a cut-out of the speaker (matte_segments.py makes them, build_project.py mounts them).
MATTE_TYPES = {kind for kind, rule in RULES.items() if rule["matte"]}

# Effects that replace or reframe the whole picture - spaced further apart than light overlays.
HEAVY = {"chat_takeover", "phone_mockup", "broll_layers", "frame_escape", "studio", "magazine_cover",
         "green_screen", "paper_cutout", "growth_chart", "recap_checklist"}

# Used to fill long stretches with no cue so the picture never sits still too long.
FILLERS = ["punch_zoom", "dolly_zoom", "jump_zoom"]
FILLER_DUR = {"punch_zoom": 1.2, "dolly_zoom": 2.8, "jump_zoom": 1.0}

# Pacing presets: min gap between any two effects, min gap between heavy ones,
# longest stretch allowed without any effect, max matte effects per minute.
PACING = {
    "reel": dict(gap=1.0, heavy_gap=5.0, max_idle=3.5, matte_per_min=4),
    "long": dict(gap=4.0, heavy_gap=20.0, max_idle=12.0, matte_per_min=1),
}
