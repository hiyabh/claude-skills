---
name: whatsapp-personality-quiz
description: >-
  Build a hilarious, razor-sharp Hebrew personality quiz from WhatsApp chat exports of one
  or two real people. Analyzes their voice (phrases, sarcasm, humor, references, opinions)
  and produces a 25-question Buzzfeed-style quiz "in their voice" that judges whether the
  taker is "one of them". Output is an RTL Hebrew Word document ready to share to the family
  group chat. TRIGGER on: "מבחן אישיות", "קוויז", "personality quiz from chat", "WhatsApp quiz",
  "תבנה מבחן על הגיסים", "מי אני יותר X או Y", "Buzzfeed quiz from chat", "מבחן מצחיק על
  המשפחה", or when user provides one or more WhatsApp .txt exports and asks to capture the
  writing style as a quiz.
license: MIT
metadata:
  version: 1.0.0
  category: content-creation
  tags:
    he:
      - מבחן
      - קוויז
      - וואטסאפ
      - אישיות
      - הומור
      - משפחה
    en:
      - quiz
      - whatsapp
      - personality
      - humor
      - hebrew
      - content
  display_name:
    he: מבחן אישיות מצ'אט וואטסאפ
    en: WhatsApp Personality Quiz Builder
---

# WhatsApp Personality Quiz Builder

`<SKILL_DIR>` = the folder that contains this SKILL.md (normally
`~/.claude/skills/whatsapp-personality-quiz`). Resolve it once to an absolute
path before running commands - PowerShell/cmd do not expand `~` inside quotes.

Create a Buzzfeed-style Hebrew personality quiz that captures the voice of one or two real people, based on their WhatsApp chat history. Output: an RTL Hebrew Word document.

## When to invoke

Use when the user provides:
- One or more WhatsApp `.txt` exports
- Names of 1-2 specific people whose voice should be captured
- Goal of producing a shareable quiz "in their voice"

Common phrasings: "תבנה מבחן אישיות על X ו-Y", "מבחן בסגנון של X ו-Y", "personality quiz like buzzfeed from these messages".

## Workflow

### Step 1: Inventory the data

Locate the chat files (usually in the user-supplied project folder). Confirm:
- Speaker name format (e.g., `דניאל כהן`, `רוני Roni`)
- Approximate number of messages per target person (use `Grep -c "- <name>:"`)
- That you have at least ~300 messages per person — fewer is shallow

If there are <300 messages, warn the user that the quiz will rely more on imagination than evidence.

### Step 2: Voice analysis (internal, do not output)

For each target person, extract from ~200 sampled messages spread across the file:

1. **Signature phrases** they repeat across months ("כפרה עליך", "בטל ומבוטל", "פארווע")
2. **Stylistic tics**:
   - Sentence length (3 words? full paragraphs?)
   - Letter elongation ("מוצרללללה", "פששששש")
   - Punctuation habits (lone "." messages, lone "?")
   - Emoji preferences (🪬, 💜, etc.)
   - Abbreviations they invented ("מ. ט.", "ר. מ")
3. **Humor pattern**: dry / sarcastic / absurdist / self-aware / cynical / earnest
4. **Recurring targets**: who they mock, who they praise, what they dismiss
5. **Recurring topics**: politics, food, military, family, religion, sports
6. **Specific opinions** they actually expressed (cite the message, even if not in output)
7. **Internal references**: nicknames they coined, in-jokes, recurring phrases the family uses

Build a profile per person. If two targets, contrast them — what's the same, what's different.

### Step 3: Map the spectrum

For each quiz question, the four options are an escalation:

- **A (1 pt)**: A normal, sweet, slightly boring person — the kind they'd mock
- **B (2 pts)**: Some spark, hint of edge, but still mainstream
- **C (3 pts)**: Almost them, but still "trying" — knows the codes but uses them clumsily
- **D (4 pts)**: A near-verbatim quote or perfect paraphrase of what the targets actually wrote

The D option is the hardest. It MUST be specific. If a D could apply to any sarcastic Israeli, rewrite it until it's unmistakably one of the targets.

### Step 4: Pick 25 question topics

Cover a spread across these categories (3-5 questions each):
- Communication style (message length, punctuation, abbreviations)
- Reactions to family events (births, weddings, surgeries, milestones)
- Reactions to outsiders (strangers, new acquaintances, unusual situations)
- Opinions on hot topics they actually held (politics, religion, food)
- Behavioral signatures (timing, late nights, formality)
- Inter-family ribbing (how they tease specific relatives)
- Visual triggers (someone in a hat, a photo, an outfit, a car)
- Recurring obsessions (e.g., "the missing family photo")

Each question needs at least one D that quotes or near-quotes an actual message.

### Step 5: Write the 5-tier scoring rubric

Total ranges from 25 (all A) to 100 (all D). Tiers:

| Range | Title | Tone |
|---|---|---|
| 25-39 | "אתה כנראה X" (something boring/normative the targets would mock) | Dismissive but warm |
| 40-54 | "פוטנציאל, אבל..." | Faintly hopeful, mostly disappointed |
| 55-69 | "מכובד. לא מבייש." | Begrudging respect |
| 70-84 | "טריטוריה מסוכנת. הופך לאחד מהם." | Family-is-noticing |
| 85-100 | "אתה פשוט [שם 1] או [שם 2]" | Direct address, full surrender |

Each tier description must use specific phrases from the targets' actual vocabulary. The Tier 5 should specifically address the reader as if they ARE the target, and end with one of the target's catchphrases.

### Step 6: Write the document content (Markdown)

Build the MD file with this structure:

```markdown
# [Punchy Hebrew Title with both names]

[1-2 line subtitle in their voice]

[3-4 line intro in their voice — self-aware, slightly dismissive of anyone needing a quiz to figure this out]

[Scoring rule line — A=1, B=2, C=3, D=4, with a joke about people who can't add]

## השאלות

### 1. [Question]

A. [Normal]
B. [Edge]
C. [Almost them]
D. [Them, verbatim or near-verbatim]

[... 25 questions total ...]

## איך מחשבים את הניקוד

[Funny instruction line]

## התוצאות

### [Range]: [Title 1]
[Description]

[... 5 tiers total ...]
```

### Step 7: Produce the DOCX

1. Filename convention (Hebrew, descriptive, matches the H1 of the document):
   `[שם הקוויז].docx` and `[שם הקוויז].md` (same base name), in the project directory
2. Run:
   ```bash
   python "<SKILL_DIR>/scripts/build_docx.py" "<path-to-[שם הקוויז].md>"
   ```
   This produces the `.docx` next to the `.md` (same base name).
3. Verify both files exist via `ls`

The embedded script (`<SKILL_DIR>/scripts/build_docx.py` + its `hebrew_docx_template.py` helper) already enforces the Hebrew-document house rules:
- RTL on section, paragraphs, runs (bidi ordered correctly)
- Black & white only, no colored highlights
- David font, 12pt minimum everywhere, larger sizes for headings
- A4, 2cm margins, centered page numbers in the footer
- `---` lines are skipped, never rendered as a horizontal rule
- Only `-` for dashes (em/en dash is auto-converted to `-`)

## Critical quality rules

1. **Specificity over wit**. A funny line that could apply to anyone is failure. A specific line about a real obsession of the target is gold.

2. **Cite or paraphrase**. At least 60% of the D options should be a direct phrase from the target's messages, or a paraphrase so close that the family will recognize it instantly.

3. **No generic "Israeli humor"**. Don't write "you love arguing about hummus" unless one of them actually argued about hummus on the chat.

4. **Tier 5 must address BOTH targets** if there are two. Don't pick one over the other. The reader is "either of them".

5. **Use their nicknames internally**. If one target has a nickname they use for a specific relative or friend, use that nickname — not the real name — in answers. The family will recognize.

6. **Don't explain the joke**. References to internal moments (a specific surgery, a specific trip, a specific phrase) should be dropped without footnoting. The audience either knows or doesn't.

7. **Test the gradient**. For each question, ask: would a stranger guess that D is the highest score? If not, the gradient is broken.

## Anti-patterns to avoid

- Writing all the questions about food when only some of their conversation is about food
- Using emoji that the targets don't actually use
- Making the C option already too "them" (then D has nowhere to go)
- Tier 1 being mean rather than dismissive — they mock, they don't insult strangers
- Tier 5 being a generic "you're so funny!" — it should sting with recognition

## Output

Two files in the project directory:
- `[שם הקוויז].md` — markdown source for editing
- `[שם הקוויז].docx` — final Hebrew RTL Word document ready to share

Report back: file paths, sizes, and a 1-sentence summary of the target person profiles you built.
