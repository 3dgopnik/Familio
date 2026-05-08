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

def gf(lines, tag):
    return [val for lvl, t, val in lines if t == tag and val]

A = parse_gedcom(r'C:\Familio\gedcom\Familio_gedcom Cherednikov_2026-05-05_17-00-02.ged')
B = parse_gedcom(r'C:\Familio\gedcom\Familio_gedcom_Markov_2026-05-07_21-00-04.ged')

print("=== Main @I35@ (Antonina) ===")
for lvl, tag, val in A['@I35@']:
    if tag in ('NAME', 'FAMS', 'FAMC') or lvl == 0:
        print(f"  {lvl} {tag} {val}")

print()
print("=== Markov @I36@ (Antonina) ===")
for lvl, tag, val in B['@I36@']:
    if tag in ('NAME', 'FAMS', 'FAMC') or lvl == 0:
        print(f"  {lvl} {tag} {val}")

print()
print("=== Markov @F9@ ===")
for lvl, tag, val in B.get('@F9@', []):
    print(f"  {lvl} {tag} {val}")

print()
print("=== Main families containing @I35@ ===")
for fid, lines in A.items():
    if lines and lines[0][1] == 'FAM':
        vals = [val for _, t, val in lines if t in ('HUSB', 'WIFE', 'CHIL') and val]
        if '@I35@' in vals:
            husb = gf(lines, 'HUSB')
            wife = gf(lines, 'WIFE')
            chil = gf(lines, 'CHIL')
            print(f"  {fid}: HUSB={husb} WIFE={wife} CHIL={chil}")

print()
print("=== Main @F11@ ===")
for lvl, tag, val in A.get('@F11@', []):
    print(f"  {lvl} {tag} {val}")
