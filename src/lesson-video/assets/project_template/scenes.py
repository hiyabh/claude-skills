# -*- coding: utf-8 -*-
"""Illustration prompts for this lesson (gen_images.py reads SCENES, the era sets and ANCIENT).
Write the subject only; the art style and the modesty block are appended automatically.
Name = file name in clip/assets/img/. Plan ~1 picture per 60-75s of lesson + "thumb-hero"."""

# 16th-19th century Jewish scenes get the HISTORIC block (no knitted kippot).
HISTORIC_SCENES = set()
# Biblical scenes get the ANCIENT block below.
ANCIENT_SCENES = set()

ANCIENT = (
    "BIBLICAL ERA (STRICT): ancient Israelites in simple Near-Eastern robes, cloaks and head cloths, no kippot, "
    "no modern items. Any woman covers her hair with a simple cloth tied at the BACK of the head, face, chin, "
    "jawline and neck fully visible - NEVER a hijab wrapped around the face, NEVER a veil, nothing Arab or Muslim "
    "style; long modest robes. Prefer distant small figures or men only in crowd scenes."
)

SCENES = {
    "thumb-hero": "A single warm, striking scene that sums up the lesson, one clear subject on the LEFT half, "
                  "the right half calmer and darker for a big title; cinematic light.",
    "example-family-sukkah": "A religious family sings around the table inside a decorated sukkah at night, warm "
                             "string lights, paper chains.",
}
