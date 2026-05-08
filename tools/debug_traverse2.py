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

def get_all(lines, tag):
    return [val for lvl, t, val in lines if t == tag and val]

def family_members(fam_id, fams_dict):
    lines = fams_dict.get(fam_id, [])
    return get_all(lines, 'HUSB'), get_all(lines, 'WIFE'), get_all(lines, 'CHIL')

A = parse_gedcom(r'C:\Familio\gedcom\Familio_gedcom Cherednikov_2026-05-05_17-00-02.ged')
B = parse_gedcom(r'C:\Familio\gedcom\Familio_gedcom_Markov_2026-05-07_21-00-04.ged')

main_persons = {k: v for k, v in A.items() if v and v[0][1] == 'INDI'}
markov_persons = {k: v for k, v in B.items() if v and v[0][1] == 'INDI'}
main_fams = {k: v for k, v in A.items() if v and v[0][1] == 'FAM'}
markov_fams = {k: v for k, v in B.items() if v and v[0][1] == 'FAM'}

print(f"Main: {len(main_persons)} persons, {len(main_fams)} families")
print(f"Markov: {len(markov_persons)} persons, {len(markov_fams)} families")
print(f"@F9@ in markov_fams: {'@F9@' in markov_fams}")
print(f"@F11@ in main_fams: {'@F11@' in main_fams}")

b_id = '@I36@'
a_id = '@I35@'

b_fams = get_all(markov_persons.get(b_id, []), 'FAMS')
a_fams = get_all(main_persons.get(a_id, []), 'FAMS')
print(f"\nAntonina B FAMS: {b_fams}")
print(f"Antonina A FAMS: {a_fams}")

for b_fam in b_fams:
    bh, bw, bc = family_members(b_fam, markov_fams)
    print(f"\nMarkov {b_fam}: HUSB={bh} WIFE={bw} CHIL={bc}")
    print(f"  b_id in bw: {b_id in bw}")
    for a_fam in a_fams:
        ah, aw, ac = family_members(a_fam, main_fams)
        print(f"  Main {a_fam}: HUSB={ah} WIFE={aw}")
        print(f"  a_id in aw: {a_id in aw}")
        if b_id in bw and a_id in aw:
            print(f"  -> Match husband: {bh[0] if bh else '?'} <-> {ah[0] if ah else '?'}")
