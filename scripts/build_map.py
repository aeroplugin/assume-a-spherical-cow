"""Build the chapter maps from the book's LaTeX sources.

usage: python3 -I scripts/build_map.py [--fragment PATH]

Reads main.tex (chapter order), each chapter's title, dek, \\buildson
prerequisites, prototype, sections, boxes, problems and reading list, and the
tasting menus in frontmatter/advice.tex. Writes the interactive map.html at the
book root and the dependency chart frontmatter/chart.tex for the PDF.
--fragment also writes the page without the <html>/<head>/<body> wrapper, which
is the form the claude.ai artifact host expects. Standard library only.
"""
import base64, json, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.join(ROOT, 'scripts', 'map')

# Labels for the map's nodes, which only have room for two short lines.
SHORT = {
    'math': 'Mathematical methods', 'newton': 'Newtonian mechanics',
    'sho': 'Harmonic oscillator', 'analytical': 'Analytical mechanics',
    'em': 'Electro\u00admagnetism', 'thermo': 'Thermo\u00addynamics',
    'statmech': 'Statistical mechanics', 'sr': 'Special relativity',
    'chaos': 'Chaos', 'comp': 'Compu­tational physics',
    'qm': 'Quantum mechanics', 'continuum': 'Continuum mechanics',
    'complex': 'Complex systems', 'plasma': 'Plasma physics',
    'amo': 'Atoms & light', 'condmat': 'Condensed matter',
    'qinfo': 'Quantum information', 'chem': 'Chemical physics',
    'nuclear': 'Nuclear physics', 'medical': 'Medical physics',
    'geo': 'Geophysics & climate', 'gr': 'General relativity',
    'gw': 'Gravi­tational waves', 'qft': 'Quantum field theory',
    'accel': 'Accelerators', 'particle': 'Particle physics',
    'strings': 'String theory',
}

# Left-to-right order of the nodes within each row of the map, chosen to keep
# edge crossings low. A chapter missing from this list goes at the end of its row.
ORDER = ['math', 'newton', 'em', 'sho', 'thermo', 'fluids', 'sr', 'comp', 'waves', 'analytical',
         'statmech', 'accel', 'optics', 'gr', 'qm', 'continuum', 'plasma', 'chaos', 'bio', 'gw',
         'qinfo', 'amo', 'chem', 'qft', 'nuclear', 'condmat', 'geo', 'complex', 'particle',
         'strings', 'medical', 'astro', 'cosmo']

# The PDF's dependency chart (frontmatter/chart.tex), in the style of the Napkin's:
# box labels, and each box's centre in cm on a 16 cm wide page. Arrows always run
# downward, so a chapter's box must sit at least ~1 cm below every box it builds on.
CHART_LABEL = {
    'math': 'Math Meth', 'newton': 'Newton', 'sho': 'Oscillator', 'analytical': 'Analyt Mech',
    'waves': 'Waves', 'em': 'E\\&M', 'thermo': 'Thermo', 'optics': 'Optics',
    'statmech': 'Stat Mech', 'sr': 'Spec Rel', 'fluids': 'Fluids', 'chaos': 'Chaos',
    'comp': 'Comp Phys', 'qm': 'Quantum', 'continuum': 'Continuum', 'complex': 'Cmplx Sys',
    'plasma': 'Plasma', 'amo': 'AMO', 'condmat': 'Cond Mat', 'qinfo': 'Q Info',
    'chem': 'Chem Phys', 'nuclear': 'Nuclear', 'bio': 'Biophys', 'medical': 'Med Phys',
    'geo': 'Geophys', 'gr': 'Gen Rel', 'astro': 'Astro', 'cosmo': 'Cosmo',
    'gw': 'Grav Waves', 'qft': 'QFT', 'accel': 'Accel', 'particle': 'Particle',
    'strings': 'Strings',
}
CHART = {
    'math': (3.44, -0.20), 'newton': (5.48, 0.15),
    'em': (4.46, -2.52), 'thermo': (11.81, -2.45), 'fluids': (13.43, -2.74), 'sho': (15.16, -2.34),
    'sr': (1.64, -4.60), 'waves': (4.67, -5.21), 'analytical': (6.64, -5.19), 'comp': (9.91, -4.61), 'statmech': (14.67, -4.69),
    'accel': (1.18, -7.13), 'optics': (3.37, -7.13), 'gr': (5.79, -7.70), 'qm': (7.64, -7.42), 'continuum': (9.81, -7.08), 'plasma': (11.72, -7.09), 'chaos': (15.39, -7.56),
    'amo': (0.60, -10.00), 'qft': (2.34, -9.69), 'gw': (4.17, -9.46), 'nuclear': (9.32, -10.05), 'condmat': (11.95, -9.89),
    'particle': (1.78, -12.50), 'strings': (5.01, -11.97), 'astro': (6.79, -12.13), 'bio': (13.74, -12.24),
    'cosmo': (3.16, -14.79), 'chem': (5.60, -14.38), 'qinfo': (7.54, -14.51), 'medical': (9.65, -14.47), 'geo': (12.79, -14.45), 'complex': (14.81, -14.59),
}

# ---------------------------------------------------------------- LaTeX -> text
GREEK = {n: c for n, c in zip(
    'alpha beta gamma delta epsilon varepsilon zeta eta theta vartheta iota kappa lambda mu nu xi pi rho '
    'sigma tau upsilon phi varphi chi psi omega Gamma Delta Theta Lambda Xi Pi Sigma Phi Psi Omega'.split(),
    'αβγδεεζηθθικλμνξπρστυφφχψωΓΔΘΛΞΠΣΦΨΩ')}
SYMBOLS = {
    'hbar': 'ħ', 'ell': 'ℓ', 'infty': '∞', 'approx': '≈', 'sim': '~', 'simeq': '≃', 'times': '×',
    'cdot': '·', 'pm': '±', 'mp': '∓', 'to': '→', 'rightarrow': '→', 'leftarrow': '←', 'le': '≤',
    'leq': '≤', 'ge': '≥', 'geq': '≥', 'gg': '≫', 'll': '≪', 'propto': '∝', 'partial': '∂',
    'nabla': '∇', 'int': '∫', 'oint': '∮', 'sum': 'Σ', 'prod': 'Π', 'odot': '⊙', 'Msun': 'M⊙',
    'kB': 'kB', 'circ': '°', 'prime': '′', 'langle': '⟨', 'rangle': '⟩', 'neq': '≠', 'ne': '≠',
    'equiv': '≡', 'dagger': '†', 'otimes': '⊗', 'in': '∈', 'dots': '…', 'ldots': '…', 'cdots': '⋯',
    'quad': ' ', 'qquad': ' ', 'deg': '°', 'degree': '°', 'perp': '⊥', 'parallel': '∥',
    'div': '∇·', 'curl': '∇×', 'grad': '∇', 'Re': 'Re ', 'Im': 'Im ',
}
SYMBOLS.update({f: f + ' ' for f in 'sin cos tan sinh cosh tanh ln log exp max min det lim arctan'.split()})
SUP = dict(zip('0123456789+-−=()niT*', '⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁻⁼⁽⁾ⁿⁱᵀ*'))
SUB = dict(zip('0123456789+-=()aeoxhklmnpstij', '₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₒₓₕₖₗₘₙₚₛₜᵢⱼ'))


def strip_cmd_arg(s, names, fmt=r'\1'):
    pat = re.compile(r'\\(?:%s)\*?\{([^{}]*)\}' % '|'.join(names))
    while True:
        t = pat.sub(fmt, s)
        if t == s:
            return t
        s = t


def script(s, table, mark):
    def rep(m):
        body = m.group(1) if m.group(1) is not None else m.group(2)
        body = body.replace(' ', '')
        if body and all(c in table for c in body):
            return ''.join(table[c] for c in body)
        return (mark + body) if len(body) == 1 else '%s(%s)' % (mark, body)
    return re.sub(r'\%s(?:\{([^{}]*)\}|(\S))' % mark, rep, s)


def math(m):
    m = m.replace('\\left', '').replace('\\right', '').replace('\\big', '').replace('\\Big', '')
    m = re.sub(r'\\(?:bigl|bigr|Bigl|Bigr)', '', m)
    m = strip_cmd_arg(m, ['un'], r' \1')
    m = strip_cmd_arg(m, ['ket'], r'|\1⟩')
    m = strip_cmd_arg(m, ['bra'], r'⟨\1|')
    m = strip_cmd_arg(m, ['abs'], r'|\1|')
    m = strip_cmd_arg(m, ['vu'], '\\1\u0302')
    m = strip_cmd_arg(m, ['dot'], '\\1\u0307')
    m = strip_cmd_arg(m, ['vb', 'mathrm', 'mathbf', 'mathit', 'text', 'textrm', 'mathcal', 'operatorname',
                          'boldsymbol', 'bm', 'mathsf', 'mathbb', 'textit', 'emph', 'mbox', 'hat', 'bar',
                          'tilde', 'vec', 'overline'])
    m = re.sub(r'\\[dt]?frac\s*(\d)\s*(\d)', r'\1/\2', m)
    for _ in range(3):
        m = re.sub(r'\\[dt]?frac\{([^{}]*)\}\{([^{}]*)\}', lambda x: '%s/%s' % (
            x[1] if len(x[1]) <= 2 else '(%s)' % x[1], x[2] if len(x[2]) <= 2 else '(%s)' % x[2]), m)
        m = re.sub(r'\\sqrt\{([^{}]*)\}', lambda x: '√' + (x[1] if len(x[1]) <= 2 else '(%s)' % x[1]), m)
    m = re.sub(r'\\sqrt\s*(\S)', r'√\1', m)
    m = re.sub(r'\^\{?\\circ\}?', '°', m)
    m = re.sub(r'\\([A-Za-z]+)', lambda x: GREEK.get(x[1], SYMBOLS.get(x[1], x[0])), m)
    m = script(m, SUP, '^')
    m = script(m, SUB, '_')
    m = re.sub(r'\\dd\b', 'd', m)
    m = m.replace('\\,', '\u2009').replace('\\;', ' ').replace('\\!', '').replace('\\ ', ' ')
    m = re.sub(r'\\[A-Za-z]+\*?', '', m)
    return m.replace('{', '').replace('}', '').replace('&', ' ').replace('\\\\', ' ')


def detex(s, refs):
    s = re.sub(r'(?<!\\)%.*', '', s)
    s = re.sub(r'\\begin\{(tikzpicture|figure|lstlisting|scope)\}.*?\\end\{\1\}', ' ', s, flags=re.S)
    s = re.sub(r'\\includegraphics(\[[^]]*\])?\{[^}]*\}', '', s)
    s = re.sub(r'\\(?:ref|ref\*|eqref)\{([^}]+)\}', lambda m: refs.get(m[1], ''), s)
    s = re.sub(r'\\(?:nameref\*?|label|hint)\{[^}]*\}', '', s)
    s = re.sub(r'\\(core|aside)\b', '', s)
    s = re.sub(r'\\\[(.*?)\\\]', lambda m: ' ' + math(m[1]) + ' ', s, flags=re.S)
    s = re.sub(r'\\begin\{(align\*?|equation\*?|gather\*?)\}(.*?)\\end\{\1\}',
               lambda m: ' ' + math(m[2]) + ' ', s, flags=re.S)
    s = re.sub(r'(?<!\\)\$(.+?)(?<!\\)\$', lambda m: math(m[1]), s, flags=re.S)
    s = strip_cmd_arg(s, ['un'], '\u2009\\1')
    s = strip_cmd_arg(s, ['emph', 'textit', 'textbf', 'textsc', 'textsf', 'texttt', 'text', 'mbox',
                          'textrm', 'textcolor\\{[^}]*\\}', 'url', 'chapterdek', 'buildson'])
    s = re.sub(r'\\begin\{[^}]*\}(\[[^]]*\])?', ' ', s)
    s = re.sub(r'\\end\{[^}]*\}', ' ', s)
    s = s.replace('---', '—').replace('--', '–').replace('``', '“').replace("''", '”').replace('`', '‘')
    s = s.replace("'", '’').replace('~', '\u00a0').replace('\\,', '\u2009').replace('\\ ', ' ')
    for a, b in (('\\%', '%'), ('\\&', '&'), ('\\$', '$'), ('\\#', '#'), ('\\_', '_')):
        s = s.replace(a, b)
    s = re.sub(r'\\item\b', ' ', s)
    s = re.sub(r'\\[A-Za-z]+\*?(\[[^]]*\])?', '', s)
    s = s.replace('{', '').replace('}', '').replace('\\\\', ' ').replace('&', ' ')
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'\s+([,.;:)])', r'\1', s)
    return s


def arg(src, cmd):
    """Contents of the first \\cmd{...}, allowing nested braces."""
    i = src.find('\\' + cmd + '{')
    if i < 0:
        return None
    i += len(cmd) + 2
    depth, j = 1, i
    while depth:
        depth += {'{': 1, '}': -1}.get(src[j], 0)
        j += 1
    return src[i:j - 1]


def first_sentence(t, limit=260):
    m = re.search(r'^(.+?[.!?])(?=\s+[A-Z“(]|$)', t)
    s = m.group(1) if m else t
    return s if len(s) <= limit else s[:limit].rsplit(' ', 1)[0] + '…'


# ---------------------------------------------------------------- the book
def read(path):
    with open(os.path.join(ROOT, path), encoding='utf-8') as f:
        return f.read()


def build():
    names = re.findall(r'^\\chap\{([^}]+)\}', read('main.tex'), re.M)
    srcs = [read('chapters/%s.tex' % n) for n in names]
    labels = [re.search(r'\\label\{ch:([^}]+)\}', s).group(1) for s in srcs]
    refs = {'ch:' + lab: str(i + 1) for i, lab in enumerate(labels)}
    refs.update({'app:constants': 'A', 'app:reading': 'B', 'app:hints': 'C', 'app:solutions': 'D'})
    # problem labels -> numbers, for cross-references in the text
    for i, s in enumerate(srcs):
        body = re.search(r'\\begin\{problems\}(.*?)\\end\{problems\}', s, re.S)
        for k, item in enumerate(re.split(r'\\prob\{\d\}', body.group(1))[1:] if body else []):
            for lab in re.findall(r'\\label\{(prob:[^}]+)\}', item):
                refs[lab] = '%d.%d' % (i + 1, k + 1)

    chapters = []
    for i, (src, lab) in enumerate(zip(srcs, labels)):
        title = detex(arg(src, 'chapter'), refs)
        build_on = re.findall(r'\\ref\{ch:([^}]+)\}', arg(src, 'buildson') or '')
        proto = re.search(r'\\begin\{prototype\}(\[[^]]*\])?(.*?)\\end\{prototype\}', src, re.S)

        body = re.split(r'\\begin\{problems\}', src)[0]
        parts = re.split(r'^\\(section|subsection)\*?\{(.*)\}\s*$', body, flags=re.M)
        sections, cur = [], None
        for j in range(1, len(parts), 3):
            kind, head, text = parts[j], detex(parts[j + 1], refs), parts[j + 2]
            if head.lower() in ('problems', 'further reading'):
                continue
            if kind == 'section' or cur is None:
                cur = {'t': head, 'sub': [], 'box': [], 'p': []}
                sections.append(cur)
            else:
                cur['sub'].append(head)
            cur['box'] += [detex(t, refs) for t in re.findall(
                r'\\begin\{(?:law|theorem|example|definition|keyidea|remark|exercise|proposition)\}\[([^]]+)\]', text)]
            for para in re.split(r'\n\s*\n|\\item\b', text):
                t = detex(para, refs)
                if len(t) > 40:
                    cur['p'].append(t)

        probs = []
        pb = re.search(r'\\begin\{problems\}(.*?)\\end\{problems\}', src, re.S)
        if pb:
            items = re.split(r'\\prob\{(\d)\}', pb.group(1))
            for k in range(1, len(items), 2):
                raw = items[k + 1]
                head = re.match(r'\s*(?:\\core|\\aside|\\label\{[^}]*\}|\s)*\\emph\{\((.+?)\.?\)\}', raw, re.S)
                text = detex(raw[head.end():] if head else raw, refs)
                probs.append({'n': len(probs) + 1, 'lv': int(items[k]),
                              't': detex(head.group(1), refs) if head else '',
                              'core': '\\core' in raw[:40], 'x': text})

        reading = [detex(re.sub(r'\\emph\{([^{}]*)\}', r'\1', m), refs) for m in re.findall(
            r'\\rd\{((?:[^{}]|\{[^{}]*\})*)\}', src)]
        chapters.append({
            'id': lab, 'n': i + 1, 'title': title, 'short': SHORT.get(lab, title),
            'pretext': '' if build_on else detex(arg(src, 'buildson') or '', refs),
            'dek': detex(arg(src, 'chapterdek') or '', refs),
            'proto': first_sentence(detex(proto.group(2), refs)) if proto else '',
            'pre': build_on, 'sec': sections, 'prob': probs, 'read': reading,
        })

    menus = []
    for m in re.finditer(r'\\textbf\{The ([a-z-]+) menu:\}(.*)', read('frontmatter/advice.tex')):
        seq, _, rest = m.group(2).partition('then any of')
        menus.append({'id': m.group(1), 'name': m.group(1).replace('-', ' ').capitalize(),
                      'steps': re.findall(r'\\ref\{ch:([^}]+)\}', seq),
                      'then': re.findall(r'\\ref\{ch:([^}]+)\}', rest)})
    return chapters, menus


def rows(chapters):
    """Group chapters into rows: each sits one row below the deepest chapter it builds on."""
    depth = {}
    for c in chapters:
        depth[c['id']] = 1 + max((depth[p] for p in c['pre']), default=-1)
    rank = {lab: i for i, lab in enumerate(ORDER)}
    out = [[] for _ in range(max(depth.values()) + 1)]
    for c in sorted(chapters, key=lambda c: rank.get(c['id'], 1000 + c['n'])):
        out[depth[c['id']]].append(c['id'])
    return out


def chart(chapters):
    """TikZ for the Napkin-style dependency chart in the advice chapter.

    Boxes sit at CHART[label] (centre, in cm); arrows come from each chapter's
    \\buildson line, so they cannot drift from the book. Every box links to its chapter.
    """
    H = 0.76   # box height in cm, used to size the curves
    missing = [c['id'] for c in chapters if c['id'] not in CHART]
    if missing:
        print('warning: no chart position for %s; placing at the bottom' % ', '.join(missing), file=sys.stderr)
        low = min(y for _, y in CHART.values()) - 2.4
        for k, lab in enumerate(missing):
            CHART[lab] = (16 * (k + 0.5) / len(missing), low)
    out = ['% Generated by scripts/build_map.py from each chapter\'s \\buildson line.',
           '% To move a box, edit CHART in that script and rerun it; do not edit this file.',
           r'\providecommand*{\chartbox}[3]{\hyperref[ch:#1]{{\tiny\sffamily Ch~#2}}\\'
           r'\hyperref[ch:#1]{{\footnotesize\strut\color{ascink}#3}}}',
           r'\begin{tikzpicture}[x=1cm, y=1cm,',
           r'  chap/.style={draw=ascink!65, fill=ascbluebg, rounded corners=1.5pt, align=left,',
           r'    inner xsep=3pt, inner ysep=2pt, line width=0.4pt},',
           r'  root/.style={chap, draw=ascink, line width=1.1pt},',
           r'  dep/.style={-{Stealth[length=3pt, width=2.4pt]}, line width=0.45pt, draw=ascink!80}]']
    for c in chapters:
        x, y = CHART[c['id']]
        out.append(r'\node[%s] (%s) at (%.2f,%.2f) {\chartbox{%s}{%d}{%s}};'
                   % ('chap' if c['pre'] else 'root', c['id'], x, y, c['id'], c['n'], CHART_LABEL.get(c['id'], c['short'])))
    out.append(r'\begin{scope}[on background layer]')
    for c in chapters:
        for p in c['pre']:
            drop = CHART[p][1] - CHART[c['id']][1] - H
            if drop < 0.5:
                print('warning: chart box %s is not far enough below %s' % (c['id'], p), file=sys.stderr)
            k = 0.45 * max(drop, 0.5)
            out.append(r'\draw[dep] (%s.south) .. controls +(0,-%.2f) and +(0,%.2f) .. (%s.north);'
                       % (p, k, k, c['id']))
    out += [r'\end{scope}', r'\end{tikzpicture}', '']
    return '\n'.join(out)


def font(name):
    with open(os.path.join(HERE, name), 'rb') as f:
        return 'data:font/woff;base64,' + base64.b64encode(f.read()).decode()


def main():
    chapters, menus = build()
    data = json.dumps({'chapters': chapters, 'menus': menus, 'rows': rows(chapters)},
                      ensure_ascii=False, separators=(',', ':'))
    data = data.replace('</', '<\\/')
    page = read('scripts/map/template.html')
    page = page.replace('/*__DATA__*/null', data)
    page = page.replace('__FONT_REGULAR__', font('asc-pagella-regular.woff'))
    page = page.replace('__FONT_ITALIC__', font('asc-pagella-italic.woff'))
    doc = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
           '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
           '</head>\n<body>\n%s\n</body>\n</html>\n' % page)
    with open(os.path.join(ROOT, 'map.html'), 'w', encoding='utf-8') as f:
        f.write(doc)
    with open(os.path.join(ROOT, 'frontmatter', 'chart.tex'), 'w', encoding='utf-8') as f:
        f.write(chart(chapters))
    if '--fragment' in sys.argv:
        with open(sys.argv[sys.argv.index('--fragment') + 1], 'w', encoding='utf-8') as f:
            f.write(page)
    n = sum(len(c['prob']) for c in chapters)
    print('%d chapters, %d problems, %d menus, %d kB' % (len(chapters), n, len(menus), len(doc) // 1024))


if __name__ == '__main__':
    main()
