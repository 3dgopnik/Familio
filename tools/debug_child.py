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
                if m2 and current_id: current_lines.append((int(m2.group(1)), m2.group(2), m2.group(3).strip()))
    return records

def get_field(lines, *tags):
    if len(tags)==1:
        for lvl,tag,val in lines:
            if tag==tags[0] and val: return val
        return ''
    in_p=False; p_lvl=None
    for lvl,tag,val in lines:
        if tag==tags[0]: in_p=True; p_lvl=lvl
        elif in_p:
            if lvl<=p_lvl: in_p=False
            elif tag==tags[1] and val: return val
    return ''

def extract_year(d):
    m = re.search(r'\b(\d{4})\b', d); return int(m.group(1)) if m else None

def surname(lines):
    name = get_field(lines, 'NAME')
    m = re.match(r'^.*?/([^/]*)/', name)
    if m:
        parts = re.split(r'\s*\(', m.group(1)); return parts[-1].rstrip(')').strip().lower()
    return ''

def given_first(lines):
    name = get_field(lines, 'NAME')
    m = re.match(r'^(.*?)\s*/', name)
    g = m.group(1).strip() if m else name.strip()
    return g.split()[0].lower() if g else ''

def birth_year(lines):
    return extract_year(get_field(lines, 'BIRT', 'DATE'))

def name_match(a, b):
    s = surname(a); g = given_first(a)
    return s and g and s == surname(b) and g == given_first(b)

A = parse_gedcom(r'C:\Familio\gedcom\Familio_gedcom Cherednikov_2026-05-05_17-00-02.ged')
B = parse_gedcom(r'C:\Familio\gedcom\Familio_gedcom_Markov_2026-05-07_21-00-04.ged')

main_p = {k:v for k,v in A.items() if v and v[0][1]=='INDI'}
markov_p = {k:v for k,v in B.items() if v and v[0][1]=='INDI'}

b_ch = '@I31@'  # Markov Ekaterina
bl = markov_p[b_ch]
print(f"Markov Ekaterina NAME: {get_field(bl,'NAME')!r}")
print(f"  surname: {surname(bl)!r}, given_first: {given_first(bl)!r}, year: {birth_year(bl)}")

for a_ch in ['@I126@', '@I153@', '@I211@']:
    al = main_p[a_ch]
    nm = name_match(bl, al)
    ay = birth_year(al)
    print(f"\nMain {a_ch}: {get_field(al,'NAME')!r}")
    print(f"  surname: {surname(al)!r}, given_first: {given_first(al)!r}, year: {ay}")
    print(f"  name_match: {nm}")
