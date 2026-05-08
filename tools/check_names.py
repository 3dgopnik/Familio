"""
Check GEDCOM names for common Russian spelling errors:
- Wrong soft sign in patronymics (-ичь, -евичь, -овичь instead of -ич, -евич, -ович)
- Wrong endings in female patronymics (-овна, -евна)
- Lowercase names
- Suspicious characters (double spaces, trailing spaces, digits in names)
- Rare/unique name variants that differ from frequent ones by 1-2 chars (Levenshtein)
"""

import re
import io
import sys
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

FILE = r"C:\Familio\gedcom\Familio_merged_2026-05-08.ged"


def levenshtein(a, b):
    if len(a) < len(b):
        return levenshtein(b, a)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1,
                            prev[j] + (ca != cb)))
        prev = curr
    return prev[-1]


def parse_names(path):
    names = []
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            m = re.match(r"^1 NAME (.+)$", line)
            if m:
                raw = m.group(1).strip()
                # Extract given and surname parts
                sm = re.match(r"^(.*?)\s*/([^/]*)/\s*(.*)$", raw)
                if sm:
                    given = (sm.group(1) + " " + sm.group(3)).strip()
                    surname = sm.group(2).strip()
                else:
                    given = raw
                    surname = ""
                names.append((raw, given, surname))
    return names


def check_names(names):
    issues = []

    # --- Rule 1: wrong soft sign in patronymics ---
    bad_patronymic = re.compile(
        r"\b\w*(овичь|евичь|овнаь|евнаь|ичь)\b", re.IGNORECASE
    )
    # Also catch -овичъ (hard sign, old spelling in modern context)
    bad_hard_sign = re.compile(r"\b\w*(овичъ|евичъ)\b", re.IGNORECASE)

    # --- Rule 2: lowercase start ---
    # --- Rule 3: double spaces ---
    # --- Rule 4: digits in name ---
    digit_re = re.compile(r"\d")

    for raw, given, surname in names:
        full = given + (" " + surname if surname else "")

        if bad_patronymic.search(full):
            issues.append(("PATRONYMIC_SOFT_SIGN", raw, bad_patronymic.search(full).group()))

        if bad_hard_sign.search(full):
            issues.append(("PATRONYMIC_HARD_SIGN", raw, bad_hard_sign.search(full).group()))

        if digit_re.search(given) or digit_re.search(surname):
            issues.append(("DIGIT_IN_NAME", raw, ""))

        if "  " in raw:
            issues.append(("DOUBLE_SPACE", raw, ""))

        # Lowercase start of given name (not counting empty)
        words = given.split()
        for w in words:
            if w and w[0].islower() and w[0].isalpha():
                issues.append(("LOWERCASE_START", raw, w))
                break

        # Lowercase start of surname
        if surname and surname[0].islower() and surname[0].isalpha():
            issues.append(("LOWERCASE_SURNAME", raw, surname))

    # --- Rule 5: near-duplicate name variants (Levenshtein <= 2) ---
    # Collect unique given names and unique surnames separately
    given_counter = Counter()
    surname_counter = Counter()
    for _, given, surname in names:
        for part in given.split():
            if len(part) > 3:
                given_counter[part.lower()] += 1
        if surname:
            surname_counter[surname.lower()] += 1

    # Find rare variants (count==1) that are close to frequent ones (count>=3)
    freq_given = [w for w, c in given_counter.items() if c >= 3]
    freq_surname = [w for w, c in surname_counter.items() if c >= 3]

    for word, cnt in given_counter.items():
        if cnt == 1 and len(word) > 4:
            for freq in freq_given:
                if abs(len(word) - len(freq)) <= 2 and levenshtein(word, freq) <= 2 and word != freq:
                    issues.append(("POSSIBLE_TYPO_GIVEN",
                                   f"'{word}' (rare) vs '{freq}' (x{given_counter[freq]})", ""))
                    break

    for word, cnt in surname_counter.items():
        if cnt == 1 and len(word) > 4:
            for freq in freq_surname:
                if abs(len(word) - len(freq)) <= 2 and levenshtein(word, freq) <= 2 and word != freq:
                    issues.append(("POSSIBLE_TYPO_SURNAME",
                                   f"'{word}' (rare) vs '{freq}' (x{surname_counter[freq]})", ""))
                    break

    return issues


def main():
    names = parse_names(FILE)
    print(f"Total NAME records: {len(names)}\n")

    issues = check_names(names)

    if not issues:
        print("No issues found.")
        return

    by_type = {}
    for kind, record, detail in issues:
        by_type.setdefault(kind, []).append((record, detail))

    for kind, items in sorted(by_type.items()):
        print(f"=== {kind} ({len(items)}) ===")
        for record, detail in items:
            if detail:
                print(f"  {record!r}  [{detail}]")
            else:
                print(f"  {record!r}")
        print()


if __name__ == "__main__":
    main()
