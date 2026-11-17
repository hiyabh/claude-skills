# -*- coding: utf-8 -*-
"""Cover layout. Origin = bottom-left of the TRIMMED sheet, units = mm, y grows upward.

A Hebrew book (rtl) opens from the right: closed, the spine is on the RIGHT of the front cover.
Laid flat, outside up, the panels run left to right:
    turn-in | FRONT | joint | spine | joint | BACK | turn-in
An ltr book is the mirror image (back on the left). A soft cover is the same with no turn-in and
no joint, and the boards are the trimmed pages.
"""
from dataclasses import dataclass


@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):
        return self.y + self.h / 2

    @property
    def right(self):
        return self.x + self.w

    @property
    def top(self):
        return self.y + self.h

    def inset(self, d):
        return Box(self.x + d, self.y + d, self.w - 2 * d, self.h - 2 * d)

    def contains(self, other, tol=0.0):
        return (other.x >= self.x - tol and other.y >= self.y - tol
                and other.right <= self.right + tol and other.top <= self.top + tol)


@dataclass
class Layout:
    width: float          # trimmed sheet
    height: float
    front: Box            # the board (hard) or the cover page (soft)
    back: Box
    spine: Box
    joints: tuple         # (front side, back side); zero width on a soft cover
    wrap: float
    bleed: float
    rtl: bool

    def panel(self, name):
        return {"front": self.front, "back": self.back, "spine": self.spine}[name]

    @property
    def visible(self):
        """What shows on the closed book: boards, joints and spine (the sheet minus the turn-ins)."""
        return Box(self.wrap, self.wrap, self.width - 2 * self.wrap, self.height - 2 * self.wrap)

    def art_region(self, name):
        """Where a panel's own picture is painted: from the outer bleed edge up to the spine."""
        b, top = self.bleed, self.height + self.bleed
        if name == "spine":
            return Box(self.spine.x, -b, self.spine.w, top + b)
        outer_left = self.panel(name).x < self.spine.x
        if outer_left:
            return Box(-b, -b, self.spine.x + b, top + b)
        return Box(self.spine.right, -b, self.width + b - self.spine.right, top + b)

    def folds(self):
        """x of every vertical fold (board edges and spine edges) and y of the board edges."""
        boxes = (self.front, self.back, self.spine) + self.joints
        xs = sorted({round(v, 3) for box in boxes for v in (box.x, box.right)} - {0, round(self.width, 3)})
        ys = sorted({round(v, 3) for v in (self.front.y, self.front.top)} - {0, round(self.height, 3)})
        return xs, ys


def layout(spec):
    if spec["binding"] == "hard":
        hard = spec["hard"]
        (bw, bh), joint, wrap = hard["board"], hard["joint"], hard["wrap"]
    else:
        (bw, bh), joint, wrap = spec["trim"], 0.0, 0.0
    s, rtl = spec["spine"], spec["direction"] == "rtl"
    first = Box(wrap, wrap, bw, bh)
    joint_a = Box(first.right, wrap, joint, bh)
    spine = Box(joint_a.right, wrap, s, bh)
    joint_b = Box(spine.right, wrap, joint, bh)
    second = Box(joint_b.right, wrap, bw, bh)
    width, height = second.right + wrap, bh + 2 * wrap
    front, back = (first, second) if rtl else (second, first)
    joints = (joint_a, joint_b) if rtl else (joint_b, joint_a)
    return Layout(width, height, front, back, spine, joints, wrap, spec["bleed"], rtl)
