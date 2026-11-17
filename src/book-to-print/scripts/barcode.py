# -*- coding: utf-8 -*-
"""EAN-13 (ISBN) bars as plain rectangles, so the PDF needs no extra font or graphics library.

bars(isbn) -> list of (start_module, width_modules, is_guard) for the 95-module symbol.
"""
L_CODES = ("0001101", "0011001", "0010011", "0111101", "0100011",
           "0110001", "0101111", "0111011", "0110111", "0001011")
G_CODES = ("0100111", "0110011", "0011011", "0100001", "0011101",
           "0111001", "0000101", "0010001", "0001001", "0010111")
R_CODES = ("1110010", "1100110", "1101100", "1000010", "1011100",
           "1001110", "1010000", "1000100", "1001000", "1110100")
PARITY = ("LLLLLL", "LLGLGG", "LLGGLG", "LLGGGL", "LGLLGG",
          "LGGLLG", "LGGGLL", "LGLGLG", "LGLGGL", "LGGLGL")
MODULES = 95
QUIET_LEFT, QUIET_RIGHT = 11, 7       # light margin, in modules


def digits_of(isbn):
    return [int(c) for c in str(isbn) if c.isdigit()]


def valid(isbn):
    d = digits_of(isbn)
    return len(d) == 13 and sum(x * (3 if i % 2 else 1) for i, x in enumerate(d)) % 10 == 0


def pattern(isbn):
    """(modules string of 95 '0'/'1', guard mask string of the same length)."""
    d = digits_of(isbn)
    left = "".join((L_CODES if p == "L" else G_CODES)[x] for p, x in zip(PARITY[d[0]], d[1:7]))
    right = "".join(R_CODES[x] for x in d[7:])
    bits = "101" + left + "01010" + right + "101"
    guard = "111" + "0" * 42 + "11111" + "0" * 42 + "111"
    return bits, guard


def bars(isbn):
    bits, guard = pattern(isbn)
    out, i = [], 0
    while i < MODULES:
        if bits[i] == "1":
            j = i
            while j < MODULES and bits[j] == "1":
                j += 1
            out.append((i, j - i, guard[i] == "1"))
            i = j
        else:
            i += 1
    return out
