import re, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def parse_gedcom(path):
    records = {}; current_id = None; current_lines = []
    with open(path, encoding='utf-8-sig') as f:
        for raw in f:
            line = raw.rstrip('\r\n')
            m = re.match(r'^(\d+)\s+(@\S+@)\s*(.*)', line)
            if m and m.group(1) == '0':
                if current_id: records[current_id] = current_lines
                current_id = m.group(2); current_lines = [(0, m.group(3).strip(), '')]
            elif re.match(r'^0\s+(HEAD|TRLR)', line):
                if current_id: records[current_id] = current_lines
                current_id = None; current_lines = []
            else:
                m2 = re.match(r'^(\d+)\s+(\S+)\s*(.*)', line)
                if m2 and current_id:
                    current_lines.append((int(m2.group(1)), m2.group(2), m2.group(3).strip()))
    return records

def gf(lines, *tags):
    if len(tags) == 1:
        for lvl, tag, val in lines:
            if tag == tags[0] and val: return val
        return ''
    in_p = False; p_lvl = None
    for lvl, tag, val in lines:
        if tag == tags[0]: in_p = True; p_lvl = lvl
        elif in_p:
            if lvl <= p_lvl: in_p = False
            elif tag == tags[1] and val: return val
    return ''

def get_all(lines, tag):
    return [val for lvl, t, val in lines if t == tag and val]

A = parse_gedcom(r'C:\Familio\gedcom\Familio_gedcom Cherednikov_2026-05-05_17-00-02.ged')
B = parse_gedcom(r'C:\Familio\gedcom\Familio_gedcom_Markov_2026-05-07_21-00-04.ged')

# Check Ekaterina Gribova in both trees
print("=== Main @I126@ (Ekaterina) ===")
for lvl, tag, val in A['@I126@']:
    if tag in ('NAME','BIRT','FAMS','FAMC','DEAT') or lvl==0: print(f"  {lvl} {tag} {val}")

print()
print("=== Markov @I31@ (Ekaterina) ===")
for lvl, tag, val in B['@I31@']:
    if tag in ('NAME','BIRT','FAMS','FAMC','DEAT') or lvl==0: print(f"  {lvl} {tag} {val}")

print()
# Check Andrei Cherednikov
print("=== Main @I191@ (Andrei Cherednikov) ===")
for lvl, tag, val in A['@I191@']:
    if tag in ('NAME','BIRT','FAMS','FAMC') or lvl==0: print(f"  {lvl} {tag} {val}")

print()
print("=== Markov @I189@ (Andrei Cherednikov) ===")
for lvl, tag, val in B['@I189@']:
    if tag in ('NAME','BIRT','FAMS','FAMC') or lvl==0: print(f"  {lvl} {tag} {val}")

print()
# Check Markov @F22@ (Andrei x Ekaterina family)
print("=== Markov @F22@ ===")
for lvl, tag, val in B.get('@F22@', []):
    print(f"  {lvl} {tag} {val}")
