"""
Fix confirmed name errors in merged GEDCOM:
1. Patronymic soft sign: -ичь -> -ич
2. Known typos: сегреевна -> сергеевна, адександровна -> александровна
3. Capitalize first letter of given names and surnames
"""

import re
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

IN_FILE  = r"C:\Familio\gedcom\Familio_merged_2026-05-08.ged"
OUT_FILE = r"C:\Familio\gedcom\Familio_merged_2026-05-08.ged"

# --- Capitalize first letter of each word in given name (before slashes)
# and each word in surname (inside slashes), preserving rest of case.

def cap_word(word):
    """Capitalize first letter, leave rest unchanged."""
    if not word:
        return word
    return word[0].upper() + word[1:]


def fix_name(raw):
    original = raw

    # Split: given_part / surname_part / suffix_part
    m = re.match(r"^(.*?)(/[^/]*/)(.*?)$", raw)
    if m:
        given_part   = m.group(1)
        surname_part = m.group(2)   # includes slashes
        suffix_part  = m.group(3)
    else:
        given_part   = raw
        surname_part = ""
        suffix_part  = ""

    # Fix given words (capitalize each)
    given_words = given_part.split()
    given_fixed = " ".join(cap_word(w) for w in given_words)

    # Fix surname (inside slashes): capitalize each word, keep parentheses
    inner = surname_part.strip("/")
    # Split by space and parentheses boundaries, capitalize each alphabetic token
    inner_fixed = re.sub(
        r"[А-Яа-яёЁA-Za-z]+",
        lambda mo: cap_word(mo.group()),
        inner
    )
    surname_fixed = "/" + inner_fixed + "/" if surname_part else ""

    # Reassemble
    result = given_fixed
    if given_fixed and surname_fixed:
        result = given_fixed + " " + surname_fixed
    elif surname_fixed:
        result = surname_fixed
    if suffix_part.strip():
        result = result.rstrip() + " " + suffix_part.strip()

    # Fix specific typos (case-insensitive)
    typos = {
        r"(?i)\bИвановичь\b":    "Иванович",
        r"(?i)\bВикторовичь\b":  "Викторович",
        r"(?i)\bСегреевна\b":    "Сергеевна",
        r"(?i)\bАдександровна\b": "Александровна",
    }
    for pattern, replacement in typos.items():
        result = re.sub(pattern, replacement, result)

    return result


def process(in_path, out_path):
    fixed_count = 0
    lines_out = []

    with open(in_path, encoding="utf-8-sig") as f:
        for line in f:
            raw_line = line.rstrip("\r\n")
            m = re.match(r"^(1 NAME )(.*?)(\s*)$", raw_line)
            if m:
                prefix   = m.group(1)
                name_val = m.group(2)
                fixed    = fix_name(name_val)
                if fixed != name_val:
                    print(f"  FIXED: {name_val!r}")
                    print(f"      -> {fixed!r}")
                    fixed_count += 1
                lines_out.append(prefix + fixed)
            else:
                lines_out.append(raw_line)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out))
        if not lines_out[-1].endswith("\n"):
            f.write("\n")

    print(f"\nFixed {fixed_count} NAME records.")
    print(f"Written to {out_path}")


if __name__ == "__main__":
    process(IN_FILE, OUT_FILE)
