"""
GEDCOM merger v3.
Matching:
  Phase 1 - anchor by (surname + birth_year), year required in BOTH.
  Phase 2 - traverse family links from anchors using name matching for no-year cases.
  Phase 3 - when a Markov family duplicates a main family, merge children.
Fixes:
  - FAMS/FAMC not copied during person merge (families own the links).
  - Duplicate families get children merged, not silently dropped.
"""

import re
from datetime import datetime
from collections import defaultdict

MAIN_FILE = r"C:\Familio\gedcom\Familio_gedcom Cherednikov_2026-05-05_17-00-02.ged"
MARKOV_FILE = r"C:\Familio\gedcom\Familio_gedcom_Markov_2026-05-07_21-00-04.ged"
OUT_FILE = r"C:\Familio\gedcom\Familio_merged_2026-05-08.ged"


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def parse_gedcom(path):
    records = {}
    current_id = None
    current_lines = []
    with open(path, encoding="utf-8-sig") as f:
        for raw in f:
            line = raw.rstrip("\r\n")
            m = re.match(r"^(\d+)\s+(@\S+@)\s*(.*)", line)
            if m and m.group(1) == "0":
                if current_id:
                    records[current_id] = current_lines
                current_id = m.group(2)
                current_lines = [(0, m.group(3).strip(), "")]
            elif re.match(r"^0\s+(HEAD|TRLR)", line):
                if current_id:
                    records[current_id] = current_lines
                current_id = None
                current_lines = []
            else:
                m2 = re.match(r"^(\d+)\s+(\S+)\s*(.*)", line)
                if m2 and current_id:
                    current_lines.append(
                        (int(m2.group(1)), m2.group(2), m2.group(3).strip())
                    )
    return records


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_field(lines, *tags):
    if len(tags) == 1:
        for lvl, tag, val in lines:
            if tag == tags[0] and val:
                return val
        return ""
    in_p = False
    p_lvl = None
    for lvl, tag, val in lines:
        if tag == tags[0]:
            in_p = True
            p_lvl = lvl
        elif in_p:
            if lvl <= p_lvl:
                in_p = False
            elif tag == tags[1] and val:
                return val
    return ""


def get_all(lines, tag):
    return [val for lvl, t, val in lines if t == tag and val]


def extract_year(date_str):
    m = re.search(r"\b(\d{4})\b", date_str)
    return int(m.group(1)) if m else None


def surname(lines):
    name = get_field(lines, "NAME")
    m = re.match(r"^.*?/([^/]*)/", name)
    if m:
        parts = re.split(r"\s*\(", m.group(1))
        return parts[-1].rstrip(")").strip().lower()
    return ""


def given_first(lines):
    name = get_field(lines, "NAME")
    m = re.match(r"^(.*?)\s*/", name)
    g = m.group(1).strip() if m else name.strip()
    return g.split()[0].lower() if g else ""


def birth_year(lines):
    return extract_year(get_field(lines, "BIRT", "DATE"))


def fam_members(fam_id, fams):
    lines = fams.get(fam_id, [])
    return get_all(lines, "HUSB"), get_all(lines, "WIFE"), get_all(lines, "CHIL")


def name_match(lines_a, lines_b):
    """True if surname AND given_first both match (non-empty)."""
    s = surname(lines_a)
    g = given_first(lines_a)
    return s and g and s == surname(lines_b) and g == given_first(lines_b)


# ---------------------------------------------------------------------------
# Phase 1: anchor matches (birth year required in both)
# ---------------------------------------------------------------------------

def find_anchors(main_p, markov_p):
    index = {}
    for rid, lines in main_p.items():
        s = surname(lines)
        g = given_first(lines)
        y = birth_year(lines)
        if s and g and y:
            index.setdefault((s, g, y), rid)

    matches = {}
    for rid, lines in markov_p.items():
        s = surname(lines)
        g = given_first(lines)
        y = birth_year(lines)
        if s and g and y:
            key = (s, g, y)
            if key in index:
                matches[rid] = index[key]
    return matches


# ---------------------------------------------------------------------------
# Phase 2: traverse family links
# ---------------------------------------------------------------------------

def traverse(matches, main_rec, markov_rec):
    main_p = {k: v for k, v in main_rec.items() if v and v[0][1] == "INDI"}
    main_f = {k: v for k, v in main_rec.items() if v and v[0][1] == "FAM"}
    markov_p = {k: v for k, v in markov_rec.items() if v and v[0][1] == "INDI"}
    markov_f = {k: v for k, v in markov_rec.items() if v and v[0][1] == "FAM"}

    added = True
    while added:
        added = False
        for b_id, a_id in list(matches.items()):

            # --- FAMS: traverse spouse and children ---
            for b_fam in get_all(markov_p.get(b_id, []), "FAMS"):
                bh, bw, bc = fam_members(b_fam, markov_f)
                for a_fam in get_all(main_p.get(a_id, []), "FAMS"):
                    ah, aw, ac = fam_members(a_fam, main_f)

                    # Match spouse
                    pairs = []
                    if b_id in bh and a_id in ah:
                        pairs = list(zip(bw, aw))
                        if not pairs and bw and aw:
                            pairs = [(bw[0], aw[0])]
                    elif b_id in bw and a_id in aw:
                        pairs = list(zip(bh, ah))
                        if not pairs and bh and ah:
                            pairs = [(bh[0], ah[0])]

                    for b_sp, a_sp in pairs:
                        if b_sp not in matches and a_sp not in matches.values():
                            bl = markov_p.get(b_sp, [])
                            al = main_p.get(a_sp, [])
                            if name_match(bl, al):
                                matches[b_sp] = a_sp
                                added = True

                    # Match children: year match when both have year, else name match
                    for b_ch in bc:
                        if b_ch in matches:
                            continue
                        bl = markov_p.get(b_ch, [])
                        by_ = birth_year(bl)
                        for a_ch in ac:
                            if a_ch in matches.values():
                                continue
                            al = main_p.get(a_ch, [])
                            ay_ = birth_year(al)
                            matched = False
                            if by_ and ay_:
                                matched = (by_ == ay_)
                            else:
                                matched = name_match(bl, al)
                            if matched:
                                matches[b_ch] = a_ch
                                added = True
                                break

            # --- FAMC: traverse parents ---
            for b_fam in get_all(markov_p.get(b_id, []), "FAMC"):
                bh, bw, _ = fam_members(b_fam, markov_f)
                for a_fam in get_all(main_p.get(a_id, []), "FAMC"):
                    ah, aw, _ = fam_members(a_fam, main_f)
                    for b_par, a_par_list in [(bh, ah), (bw, aw)]:
                        if len(b_par) == 1 and len(a_par_list) == 1:
                            b_p = b_par[0]
                            a_p = a_par_list[0]
                            if b_p not in matches and a_p not in matches.values():
                                bl = markov_p.get(b_p, [])
                                al = main_p.get(a_p, [])
                                if name_match(bl, al):
                                    matches[b_p] = a_p
                                    added = True

    return matches


# ---------------------------------------------------------------------------
# Merge person records (skip FAMS/FAMC — owned by families)
# ---------------------------------------------------------------------------

FAMILY_TAGS = {"FAMS", "FAMC"}


def merge_persons(lines_a, lines_b):
    result = [lines_a[0]]

    # Collect B level-1 blocks, skip family tags
    b_blocks = defaultdict(list)
    i = 0
    while i < len(lines_b):
        lvl, tag, val = lines_b[i]
        if lvl == 1:
            if tag in FAMILY_TAGS:
                i += 1
                while i < len(lines_b) and lines_b[i][0] > 1:
                    i += 1
                continue
            block = [(lvl, tag, val)]
            j = i + 1
            while j < len(lines_b) and lines_b[j][0] > 1:
                block.append(lines_b[j])
                j += 1
            b_blocks[tag].append(block)
            i = j
        else:
            i += 1

    a_tags = set()
    i = 1
    while i < len(lines_a):
        lvl, tag, val = lines_a[i]
        if lvl == 1:
            if tag in FAMILY_TAGS:
                # keep A family links as-is
                result.append((lvl, tag, val))
                i += 1
                continue
            a_tags.add(tag)
            block_a = [(lvl, tag, val)]
            j = i + 1
            while j < len(lines_a) and lines_a[j][0] > 1:
                block_a.append(lines_a[j])
                j += 1
            # prefer B block if A has no data under this tag
            a_data = [v for _, _, v in block_a[1:] if v and not v.startswith("_")]
            if not a_data and tag in b_blocks and b_blocks[tag]:
                b_blk = b_blocks[tag].pop(0)
                if any(v for _, _, v in b_blk[1:] if v and not v.startswith("_")):
                    result.extend(b_blk)
                    i = j
                    continue
            result.extend(block_a)
            i = j
        else:
            result.append((lvl, tag, val))
            i += 1

    # Append B-only tags
    for tag, blocks in b_blocks.items():
        if tag not in a_tags:
            for blk in blocks:
                result.extend(blk)

    return result


# ---------------------------------------------------------------------------
# ID remapping
# ---------------------------------------------------------------------------

def remap(records, prefix):
    id_map = {rid: "@" + prefix + rid[1:] for rid in records}

    def fix(val):
        for old, new in id_map.items():
            val = val.replace(old, new)
        return val

    return {id_map[rid]: [(lvl, tag, fix(val)) for lvl, tag, val in lines]
            for rid, lines in records.items()}, id_map


def renumber(records):
    ic = fc = 1
    id_map = {}
    for rid, lines in records.items():
        if not lines:
            continue
        t = lines[0][1]
        if t == "INDI":
            id_map[rid] = f"@I{ic}@"; ic += 1
        elif t == "FAM":
            id_map[rid] = f"@F{fc}@"; fc += 1

    def fix(val):
        for old, new in id_map.items():
            val = val.replace(old, new)
        return val

    return {id_map.get(rid, rid): [(lvl, tag, fix(val)) for lvl, tag, val in lines]
            for rid, lines in records.items() if lines}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Parsing main GEDCOM (Cherednikov)...")
    main_rec = parse_gedcom(MAIN_FILE)
    main_p = {k: v for k, v in main_rec.items() if v and v[0][1] == "INDI"}
    main_f = {k: v for k, v in main_rec.items() if v and v[0][1] == "FAM"}
    print(f"  {len(main_p)} persons, {len(main_f)} families")

    print("Parsing Markov GEDCOM...")
    markov_rec = parse_gedcom(MARKOV_FILE)
    markov_p = {k: v for k, v in markov_rec.items() if v and v[0][1] == "INDI"}
    markov_f = {k: v for k, v in markov_rec.items() if v and v[0][1] == "FAM"}
    print(f"  {len(markov_p)} persons, {len(markov_f)} families")

    # Phase 1
    anchors = find_anchors(main_p, markov_p)
    print(f"\nPhase 1 anchors: {len(anchors)}")
    for b, a in anchors.items():
        bn = get_field(markov_p[b], "NAME")
        an = get_field(main_p[a], "NAME")
        y = birth_year(markov_p[b])
        print(f"  {bn!r} r.{y} -> {an!r}")

    # Phase 2
    all_matches = dict(anchors)
    traverse(all_matches, main_rec, markov_rec)
    new_from_traverse = {k: v for k, v in all_matches.items() if k not in anchors}
    print(f"\nPhase 2 traversal: +{len(new_from_traverse)}")
    for b, a in new_from_traverse.items():
        bn = get_field(markov_p.get(b, []), "NAME")
        an = get_field(main_p.get(a, []), "NAME")
        print(f"  {bn!r} -> {an!r}")

    print(f"\nTotal matched: {len(all_matches)}")

    # Namespace
    main_ns, _ = remap(main_p | main_f, "A")
    markov_ns, _ = remap(markov_p | markov_f, "B")

    # Translate matches to namespaced IDs
    ns_matches = {"@B" + b[1:]: "@A" + a[1:] for b, a in all_matches.items()}

    # Merge matched persons into main (no FAMS/FAMC from B)
    for b_ns, a_ns in ns_matches.items():
        if b_ns in markov_ns and a_ns in main_ns:
            main_ns[a_ns] = merge_persons(main_ns[a_ns], markov_ns[b_ns])

    # Fix refs helper
    def fix_ref(val):
        for b_ns, a_ns in ns_matches.items():
            val = val.replace(b_ns, a_ns)
        return val

    # Add non-dup persons
    added_p = 0
    for rid, lines in markov_ns.items():
        if rid in ns_matches or not lines or lines[0][1] != "INDI":
            continue
        main_ns[rid] = [(lvl, tag, fix_ref(val)) for lvl, tag, val in lines]
        added_p += 1

    # Build main family index: (husb, wife) -> fam_id
    main_fam_index = {}
    for fid, lines in main_ns.items():
        if not lines or lines[0][1] != "FAM":
            continue
        h = next((fix_ref(v) for _, t, v in lines if t == "HUSB"), "")
        w = next((fix_ref(v) for _, t, v in lines if t == "WIFE"), "")
        sig = (h, w)
        if sig not in main_fam_index:
            main_fam_index[sig] = fid

    # Add non-dup families; merge children into existing families
    added_f = merged_f = 0
    for rid, lines in markov_ns.items():
        if not lines or lines[0][1] != "FAM":
            continue
        fixed = [(lvl, tag, fix_ref(val)) for lvl, tag, val in lines]
        h = next((v for _, t, v in fixed if t == "HUSB"), "")
        w = next((v for _, t, v in fixed if t == "WIFE"), "")
        sig = (h, w)

        if sig in main_fam_index and (h or w):
            # Merge children into existing family
            existing_id = main_fam_index[sig]
            existing = main_ns[existing_id]
            existing_chil = set(get_all(existing, "CHIL"))
            new_chil = [v for _, t, v in fixed if t == "CHIL" and v not in existing_chil]
            if new_chil:
                for c in new_chil:
                    existing.append((1, "CHIL", c))
                    # Add FAMC to child
                    if c in main_ns:
                        main_ns[c].append((1, "FAMC", existing_id))
                merged_f += 1
        else:
            main_ns[rid] = fixed
            added_f += 1

    print(f"New persons: {added_p}")
    print(f"New families: {added_f}, merged children into existing: {merged_f}")

    # Renumber
    final = renumber(main_ns)
    total_i = sum(1 for v in final.values() if v and v[0][1] == "INDI")
    total_f = sum(1 for v in final.values() if v and v[0][1] == "FAM")
    print(f"\nFinal: {total_i} persons, {total_f} families")

    # Validate
    all_ids = set(final.keys())
    broken = set()
    for rid, lines in final.items():
        for _, tag, val in lines:
            if tag in ("HUSB", "WIFE", "CHIL", "FAMC", "FAMS") and val:
                if val not in all_ids:
                    broken.add((rid, val))
    if broken:
        print(f"WARNING: {len(broken)} broken refs!")
        for src, ref in sorted(broken)[:10]:
            print(f"  {src} -> {ref}")
    else:
        print("Validation: OK")

    print(f"\nWriting {OUT_FILE}...")
    write_gedcom(final, OUT_FILE)
    print("Done.")


def write_gedcom(records, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write("0 HEAD\n1 GEDC\n2 VERS 5.5.1\n2 FORM LINEAGE-LINKED\n")
        f.write("1 CHAR UTF-8\n1 SOUR MERGED\n2 VERS 3.0\n")
        f.write(f"1 DATE {datetime.now().strftime('%d %b %Y').upper()}\n")
        f.write("1 NOTE Merged: Cherednikov + Markov GEDCOMs\n")
        for rid, lines in records.items():
            if not lines or lines[0][1] not in ("INDI", "FAM"):
                continue
            f.write(f"0 {rid} {lines[0][1]}\n")
            for lvl, tag, val in lines[1:]:
                f.write(f"{lvl} {tag} {val}\n" if val else f"{lvl} {tag}\n")
        f.write("0 TRLR\n")


if __name__ == "__main__":
    main()
