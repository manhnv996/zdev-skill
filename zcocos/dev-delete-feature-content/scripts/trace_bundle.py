# -*- coding: utf-8 -*-
"""trace_bundle.py — trace consumer cho 1 content bundle (res/content/<bundle>) trước khi xóa.

  python trace_bundle.py --bundle <name> [--repo-root <path>] [--out <dir>]
                         [--module-var <var>]... [--module-dir <dir>]... [--extra-retired-dir <dir>]...
                         [--no-auto-retired]

Tự phát hiện module của bundle qua tag `//<bundle>` trên dòng `var X = new XModule()` trong ModuleMgr.js,
tìm file định nghĩa class → module dir. Mọi module có tag `//D` (kể cả bundle khác) được coi là "retired dir"
(code trong đó không tính là active) — tắt bằng --no-auto-retired.

Output: <out>/report_<bundle>.md (đủ 12 gate G0–G11) + <out>/inventory_<bundle>.tsv + tóm tắt stdout.
Chỉ đọc, không sửa file. Stdlib only.

Gate:
  G0 ModuleMgr lines (+ Guard-Only gate: hàm show* có return guard?)   G1 inventory + ASTC parity
  G2 consumer từng file (literal / basename / res JSON, lọc duplicate own-folder)
  G3 atlas frame ngoài folder (tách frame trùng tên atlas khác)         G4 res.<key> (src/resource.js)
  G5 build/**/cdn.json          G6 dynamic path                         G7 PoolFunction caller ngoài
  G8 Layer 4c: new / extends class retired từ active (GUI vs data model, guard gần?)
  G9 Layer 4b: util retired được active gọi (body construct/load?)      G10 CMD + AniSource (Phase 2)
  G11 *.manifest legacy (thông tin)
Kind của hit: module · retired-other · ACTIVE · GUARD-ONLY(active) (dir module guard-only vẫn init ⇒ tính như ACTIVE)
"""
import io, os, re, sys, glob, json, argparse, collections
for _s in (sys.stdout, sys.stderr):          # console Windows (cp1252) không in được → · — báo lỗi giả
    try:
        _s.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

TEX_EXT = ('.png', '.jpg', '.jpeg', '.pvr', '.ccz', '.pkm', '.webp')
CONSTRUCT_PAT = re.compile(r'new\s+([A-Z]\w+)\s*\(|syncAllChild|resyncAllChild|reloadImageTexture|loadTexture|'
                           r'addSpriteFrames|createBtnEff|ccs\.load|cc\.Sprite\.create|new cc\.Sprite\(|createWithSpriteFrameName')
SKIP_CALLERS = ('PoolFunction', 'EXCHANGE', 'gc', 'res', 'cc', 'ccui', 'ccs', 'sp', 'fr', 'jsb', 'Math', 'JSON', 'Object', 'Array', 'String')


def norm(p):
    return p.replace('\\', '/')


def in_dirs(path, dirs):
    p = norm(path)
    return any(p == d or p.startswith(d + '/') for d in dirs)


def load_src(root):
    """path -> list[(lineno, text, live)] — live = không nằm trong // hoặc /* */"""
    src = {}
    for p in glob.glob(os.path.join(root, 'src', '**', '*.js'), recursive=True):
        rel = norm(os.path.relpath(p, root))
        try:
            txt = io.open(p, encoding='utf-8', errors='replace').read()
        except Exception:
            continue
        lines, inblock = [], False
        for i, t in enumerate(txt.split('\n'), 1):
            s = t.strip()
            live = True
            if inblock:
                live = False
                if '*/' in s:
                    inblock = False
            elif s.startswith('//'):
                live = False
            elif s.startswith('/*'):
                live = False
                if '*/' not in s:
                    inblock = True
            lines.append((i, t, live))
        src[rel] = lines
    return src


def load_resjson(root):
    out = {}
    for p in glob.glob(os.path.join(root, 'res', '**', '*.json'), recursive=True):
        rel = norm(os.path.relpath(p, root))
        if rel.startswith('res/localize/'):
            continue
        try:
            out[rel] = io.open(p, encoding='utf-8', errors='replace').read()
        except Exception:
            pass
    return out


def grep_src(src, pattern, exclude_dirs=(), live_only=True):
    rx = re.compile(pattern)
    out = []
    for p, lines in src.items():
        if exclude_dirs and in_dirs(p, exclude_dirs):
            continue
        for i, t, live in lines:
            if live_only and not live:
                continue
            if rx.search(t):
                out.append((p, i, t.strip()))
    return out


# ---------------------------------------------------------------- ModuleMgr
def parse_modulemgr(src):
    """→ list[dict(var, cls, tags, live, line, marker)] từ dòng `var X = new Y()` có `//D`"""
    lines = src.get('src/gamemgr/ModuleMgr.js')
    if not lines:
        raise SystemExit('không thấy src/gamemgr/ModuleMgr.js — sai --repo-root?')
    rows = []
    for i, t, live in lines:
        m = re.match(r'^\s*(//)?\s*var\s+(\w+)\s*=\s*new\s+(\w+)\s*\(', t)
        if not m:
            continue
        tags = [x for x in re.findall(r'//\s*([A-Za-z][\w-]*)', t)]
        marker = 'deleted' if 'deleted' in tags else ('guard-only' if 'guard-only' in tags else '')
        bundles = [x for x in tags if x not in ('D', 'var', 'deleted', 'content', 'guard-only', 'remove') and not x.startswith('build')]
        # giữ cả module KHÔNG tag //D (vd BuffetOffer đăng ký sống) — chọn qua --module-var; chỉ module có //D mới tự tính là retired
        rows.append({'var': m.group(2), 'cls': m.group(3), 'tags': bundles, 'live': bool(live and not m.group(1)),
                     'line': i, 'marker': marker, 'is_d': 'D' in tags})
    return rows


def find_class_dir(src, cls):
    rx = re.compile(r'^\s*(?:var\s+)?' + re.escape(cls) + r'\s*=\s*[\w.]+\.extend\s*\(')
    for p, lines in src.items():
        for i, t, live in lines:
            if rx.match(t):
                return os.path.dirname(p)
    return None


# ---------------------------------------------------------------- plist frames
def plist_frames(path):
    txt = io.open(path, encoding='utf-8', errors='replace').read()
    m = re.search(r'<key>frames</key>\s*<dict>(.*?)</dict>\s*<key>metadata</key>', txt, re.S)
    body = m.group(1) if m else txt
    # frame name = key trực tiếp dưới frames (theo sau là <dict>)
    return sorted(set(re.findall(r'<key>([^<]+)</key>\s*<dict>', body)))


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--bundle', default=None, help='tên folder res/content/<bundle>; bỏ trống nếu dùng --module để tool tự tìm')
    ap.add_argument('--module', default=None, help='tên module/feature (class, var hoặc chuỗi con, vd BuffetOffer) — tool tìm dòng ModuleMgr, module dir và folder content')
    ap.add_argument('--repo-root', default=os.getcwd())
    ap.add_argument('--out', default=None, help='default <repo>/docs/modules/deletefeaturecontent/trace')
    ap.add_argument('--module-var', action='append', default=[], help='thêm var ModuleMgr thuộc bundle (ngoài auto-tag)')
    ap.add_argument('--module-dir', action='append', default=[], help='thêm dir code của bundle (relative repo)')
    ap.add_argument('--extra-retired-dir', action='append', default=[], help='dir coi là retired (không active) ngoài auto')
    ap.add_argument('--no-auto-retired', action='store_true', help='không coi module //D của bundle khác là retired')
    ap.add_argument('--astc', default='res#tcf_astc', help='folder ASTC song song (default res#tcf_astc)')
    ap.add_argument('--skip-anim', action='store_true', help='bỏ G10b (animation của bundle) — nhanh hơn ~1–2 phút')
    ap.add_argument('--manifest-dir', default=None, help='đọc manifest moved/verified của bundle để in dòng ĐÃ XÓA (default docs/modules/deletefeaturecontent/manifests)')
    a = ap.parse_args()

    root = os.path.abspath(a.repo_root)
    if not os.path.exists(os.path.join(root, 'project.json')):
        raise SystemExit(f'--repo-root không có project.json: {root}')
    if not a.bundle and not a.module:
        raise SystemExit('cần --bundle <folder> hoặc --module <tên module/feature>')
    os.chdir(root)

    src = load_src(root)
    resjson = load_resjson(root)
    print(f'src: {len(src)} file · res json: {len(resjson)} file', file=sys.stderr)

    # class → file (1 lượt) để resolve module dir nhanh
    class_file = {}
    for q, lines in src.items():
        for i, t, live in lines:
            m = re.match(r'^\s*(?:var\s+)?([A-Z]\w*)\s*=\s*[\w.]+\.extend\s*\(', t)
            if m:
                class_file.setdefault(m.group(1), q)

    # ---- G0 modules — KHÔNG phụ thuộc tag //D: retired = ctor đã comment trong ModuleMgr (hoặc có tag //D), guard-only = marker
    mm = parse_modulemgr(src)
    for r in mm:
        r['dir'] = os.path.dirname(class_file[r['cls']]) if r['cls'] in class_file else None
    resolved_note = []
    if a.module:
        key = a.module.lower().replace('module', '')
        cands = [r for r in mm if key in r['cls'].lower().replace('module', '') or key in r['var'].lower().replace('module', '')]
        if not cands:
            raise SystemExit(f'--module {a.module}: không thấy dòng `var X = new ...Module()` khớp trong ModuleMgr.js')
        if len(cands) > 1 and not a.module_var:
            raise SystemExit(f'--module {a.module}: khớp nhiều module {[r["cls"] for r in cands]} — chỉ rõ bằng --module-var <var>')
        a.module_var = list(a.module_var) + [r['var'] for r in cands]
        # folder content mà module dir tham chiếu (dòng sống): content/<folder>/ literal + res.<key> trỏ vào content/<folder>/
        tbl0 = {}
        for q, lines in src.items():
            if q.endswith('/resource.js') or q == 'src/resource.js':
                for i, t, live in lines:
                    m = re.match(r'^\s*(\w+)\s*:\s*"([^"]+)"', t)
                    if m:
                        tbl0[m.group(1)] = m.group(2)
        folders = collections.Counter()
        for r in cands:
            if not r['dir']:
                continue
            for q, lines in src.items():
                if not in_dirs(q, [r['dir']]):
                    continue
                for i, t, live in lines:
                    if not live:
                        continue
                    for m in re.finditer(r'content/([A-Za-z0-9_\-]+)/', t):
                        folders[m.group(1)] += 1
                    for m in re.finditer(r'\bres\.(\w+)\b', t):
                        mm2 = re.search(r'content/([A-Za-z0-9_\-]+)/', tbl0.get(m.group(1), ''))
                        if mm2:
                            folders[mm2.group(1)] += 1
        own = [f for f in folders if f.lower().replace('_', '') in a.module.lower().replace('_', '') or a.module.lower().replace('module', '').replace('_', '') in f.lower().replace('_', '')]
        if not a.bundle:
            if len(folders) == 1:
                a.bundle = next(iter(folders))
            elif len(own) == 1:
                a.bundle = own[0]
            elif folders:
                raise SystemExit(f'--module {a.module}: module dir tham chiếu nhiều folder content {dict(folders)} — chọn --bundle <folder> (folder dùng chung như system/lobby thì KHÔNG phải bundle)')
            else:
                raise SystemExit(f'--module {a.module}: module dir {[r["dir"] for r in cands]} không tham chiếu content/<folder>/ nào — feature không có content riêng (có thể chỉ animation: chạy trace_anim.py hoặc --bundle <folder> nếu biết)')
        resolved_note.append(f'`--module {a.module}` → ' + ', '.join(f'`{r["var"]}` ({r["cls"]}, `{r["dir"]}`)' for r in cands) + f' → folder content tham chiếu: {dict(folders)} → bundle **`{a.bundle}`**')
    b = a.bundle
    out_dir = a.out or os.path.join(root, 'docs', 'modules', 'deletefeaturecontent', 'trace')
    os.makedirs(out_dir, exist_ok=True)

    mine = [r for r in mm if b in r['tags'] or r['var'] in a.module_var]
    mdirs = set(norm(d) for d in a.module_dir) | {r['dir'] for r in mine if r['dir']}
    mdirs = sorted(mdirs)
    retired = set(mdirs) | set(norm(d) for d in a.extra_retired_dir)
    if not a.no_auto_retired:
        for r in mm:
            # retired = ctor đã comment (không cần tag) hoặc có tag //D; module sống không tag ⇒ ACTIVE
            if r['dir'] and (r['is_d'] or not r['live'] or r in mine):
                retired.add(r['dir'])
    retired = sorted(retired)
    other_retired = [d for d in retired if d not in mdirs]

    # module Guard-Only vẫn init ⇒ code trong dir của nó CHẠY như active (GUI riêng chỉ an toàn khi có return guard)
    gdirs = sorted({r['dir'] for r in mine if r.get('dir') and r['marker'] == 'guard-only' and r['live']})

    def loc_kind(p):
        if in_dirs(p, gdirs):
            return 'GUARD-ONLY(active)'
        if in_dirs(p, mdirs):
            return 'module'
        if in_dirs(p, retired):
            return 'retired-other'
        return 'ACTIVE'

    def is_active(kind):
        return kind in ('ACTIVE', 'GUARD-ONLY(active)')

    rep = []
    P = rep.append
    P(f'# trace — `{b}`'); P('')
    P(f'repo: `{root}` · module dirs: {", ".join(f"`{d}`" for d in mdirs) or "**(none — thêm --module-var/--module-dir)**"}')
    for note in resolved_note:
        P('**Resolve:** ' + note); P('')
    P(f'retired dirs khác (module đã comment trong ModuleMgr hoặc tag `//D` — không tính active; un-retire module nào thì trace lại): {len(other_retired)}' +
      (' → ' + ', '.join(f'`{d}`' for d in other_retired) if other_retired else '')); P('')

    P('## G0 — ModuleMgr'); P('')
    P('| var | class | dir | ctor line | trạng thái | các lần xuất hiện (init/reset) |'); P('|---|---|---|---:|---|---|')
    for r in mine:
        hits = [(i, live) for i, t, live in src['src/gamemgr/ModuleMgr.js'] if re.search(r'\b' + r['var'] + r'\.(init|reset)\s*\(', t)]
        st = ('LIVE' if r['live'] else 'commented') + (f' · {r["marker"]}' if r['marker'] else '')
        P(f'| `{r["var"]}` | `{r["cls"]}` | `{r["dir"]}` | {r["line"]} | {st} | ' +
          ', '.join(f'{i}{"" if live else "(c)"}' for i, live in hits) + ' |')
    if not mine:
        P('| — | — | — | — | không tìm thấy dòng `var X = new ... //D //' + b + '` | — |')
    P('')
    # Guard-Only gate: module giữ register ⇒ hàm show*/open*/popup* (construct GUI riêng) phải có `return` đầu body
    for r in mine:
        if r['marker'] != 'guard-only' or not r.get('dir'):
            continue
        fns = []
        for q, lines in src.items():
            if not in_dirs(q, [r['dir']]):
                continue
            txt = '\n'.join(t for _, t, _ in lines)
            for m in re.finditer(r'^\s*(?:[\w.]+\.)?((?:show|open|popup)\w*)\s*[=:]\s*function\s*\([^)]*\)\s*\{[ \t]*\n((?:[ \t]*//[^\n]*\n)*)[ \t]*([^\n]*)', txt, re.M):
                first = m.group(3).strip()
                guarded = first.startswith('return') or (first.startswith('if') and 'callback' in first)
                fns.append((q, m.group(1), guarded, first[:60]))
        n_ok = sum(1 for x in fns if x[2])
        miss = ', '.join(f'`{os.path.basename(q)}.{fn}`' for q, fn, g, _ in fns if not g)
        P(f'**Guard-Only gate `{r["var"]}`:** {n_ok}/{len(fns)} hàm show*/open*/popup* trong `{r["dir"]}` có `return` guard đầu body'
          + (f' — **THIẾU GUARD**: {miss}' if miss else ' ✓'))
        P('')

    # ---- G1 inventory + parity
    inv = []
    for base in (f'res/content/{b}', f'{a.astc}/content/{b}'):
        for r_, _, files in os.walk(base):
            for f in files:
                p = norm(os.path.join(r_, f)); inv.append((p, os.path.getsize(p)))
    inv.sort()
    if not inv:
        print(f'⚠ không có file nào trong res/content/{b} (đã xóa rồi, hoặc bundle sai) — vẫn chạy các gate code/animation', file=sys.stderr)
        P(f'⚠ **`res/content/{b}` không có file** — đã xóa trước đó hoặc tên bundle sai; report chỉ còn giá trị ở G7–G10b.'); P('')
    total = sum(s for _, s in inv)
    paths = {p for p, _ in inv}
    parity_bad = []
    for p, _ in inv:
        if p.startswith('res/') and p.lower().endswith(TEX_EXT):
            c = a.astc + p[len('res'):]
            if os.path.exists(c) and c not in paths:
                parity_bad.append((p, c))
        if p.startswith(a.astc + '/'):
            s_ = 'res' + p[len(a.astc):]
            if s_ not in paths:
                parity_bad.append((p, s_ + ' (thiếu bản gốc)'))
    P(f'## G1 — Inventory: {len(inv)} file, {total:,} B'); P('')
    P('| path | bytes |'); P('|---|---:|')
    for p, s in inv:
        P(f'| `{p}` | {s:,} |')
    P('')
    P(f'ASTC parity: {"OK" if not parity_bad else "**LỆCH** " + "; ".join(f"`{x}` ↔ `{y}`" for x, y in parity_bad)}'); P('')
    with io.open(os.path.join(out_dir, f'inventory_{b}.tsv'), 'w', encoding='utf-8') as f:
        for p, s in inv:
            f.write(f'{p}\t{s}\n')

    # bảng res.<key> (src/resource.js) là KHAI BÁO, không phải consumer — loại khỏi G2, xử lý ở G4
    tbl, tbl_file = {}, None
    for q, lines in src.items():
        if q.endswith('/resource.js') or q == 'src/resource.js':
            tbl_file = q
            for i, t, live in lines:
                m = re.match(r'^\s*(\w+)\s*:\s*"([^"]+)"', t)
                if m:
                    tbl[m.group(1)] = m.group(2)

    def grep_consumers(pattern):
        return [x for x in grep_src(src, pattern) if x[0] != tbl_file]

    # ---- G2 consumers per file
    P('## G2 — Consumer từng file (chỉ dòng sống; bảng `res.<key>` xem G4)'); P('')
    P('| file | literal `content/' + b + '/…` | basename-only (⚠ xác nhận full path) | res JSON ngoài folder | class |')
    P('|---|---|---|---|---|')
    orphans, active_consumers, res_share, g2info = [], collections.OrderedDict(), [], {}
    own_json_txt = ''.join(txt for q, txt in resjson.items() if q.startswith(f'res/content/{b}/'))
    for p, s in inv:
        if not p.startswith('res/'):
            continue
        rel = p[len('res/'):]
        base = os.path.basename(p)
        lit = grep_consumers(re.escape(rel))
        bo = [x for x in grep_consumers(r'(?<![\w/])' + re.escape(base) + r'(?![\w])') if rel not in x[2]]
        rj = []
        for q, txt in resjson.items():
            if q.startswith(f'res/content/{b}/'):
                continue
            if rel in txt:
                rj.append((q, 'path'))
            elif base in txt:
                # G7 lesson: JSON tham chiếu tương đối — nếu folder của JSON đó có file cùng tên thì KHÔNG phải consumer
                same = os.path.join(os.path.dirname(q), base)
                rj.append((q, 'DUP-in-own-folder (bỏ)' if os.path.exists(same) else 'basename'))
        rj_real = [q for q, k in rj if not k.startswith('DUP')]
        ext_src = [(q, i) for q, i, _ in lit + bo if is_active(loc_kind(q))]
        ext_other = [(q, i) for q, i, _ in lit + bo if loc_kind(q) == 'retired-other']
        if base.endswith('.json'):
            if not lit and not bo and not rj_real:
                cls = 'ORPHAN?'
            elif ext_src or rj_real:
                cls = 'ACTIVE-CONSUMER'
            else:
                cls = 'Retired' + (' (retired-other)' if ext_other else '')
        else:
            own_ref = base in own_json_txt
            if ext_src or rj_real:
                cls = 'ACTIVE-CONSUMER'
            elif lit or bo or own_ref:
                cls = 'Retired'
            else:
                cls = 'ORPHAN?'
        if cls == 'ORPHAN?':
            orphans.append(p)
        if cls == 'ACTIVE-CONSUMER':
            active_consumers[p] = [f'{q}:{i}' for q, i in ext_src] + rj_real
        res_share += [(p, q, k) for q, k in rj]
        g2info[p] = {'cls': cls, 'ext': [(loc_kind(q), f'{q}:{i}') for q, i in ext_src], 'rj': rj_real,
                     'mod': sorted({q for q, i, _ in lit + bo if not is_active(loc_kind(q))})}   # file module retired consume (để nối G8)
        fmt = lambda xs: '<br>'.join(f'`{q}:{i}`' + ('' if loc_kind(q) == 'module' else f' **[{loc_kind(q)}]**') for q, i, _ in xs[:6]) + (f'<br>+{len(xs) - 6}' if len(xs) > 6 else '')
        rj_s = '<br>'.join(f'`{q}` ({k})' for q, k in rj[:6]) + (f'<br>+{len(rj) - 6}' if len(rj) > 6 else '')
        P(f'| `{base}` | {fmt(lit) or "—"} | {fmt(bo) or "—"} | {rj_s or "—"} | **{cls}** |')
    P('')

    # ---- G3 atlas frames
    plists = [p for p, _ in inv if p.endswith('.plist')]
    frame_owner = {}
    for pl in plists:
        for fr in plist_frames(pl):
            frame_owner.setdefault(fr, set()).add(pl)
    # frame cùng tên có thể được định nghĩa ở atlas KHÁC (duplicate atlas, vd euro có bản EuroContent riêng) → map toàn cục
    other_owner = collections.defaultdict(set)
    for pl in glob.glob(os.path.join(root, 'res', '**', '*.plist'), recursive=True):
        rel = norm(os.path.relpath(pl, root))
        if rel.startswith(f'res/content/{b}/'):
            continue
        try:
            for fr in plist_frames(pl):
                if fr in frame_owner:
                    other_owner[fr].add(rel)
        except Exception:
            pass
    P(f'## G3 — Atlas frame ngoài folder sở hữu ({len(plists)} plist, {len(frame_owner)} frame; {len(other_owner)} frame trùng tên ở atlas khác)'); P('')
    frame_hits = collections.defaultdict(set)   # file -> frames (chỉ frame KHÔNG có ở atlas trong chính folder của file)
    frame_lines = collections.defaultdict(set)  # (file, frame) -> {dòng} cho consumer JS
    frame_dup = collections.defaultdict(set)    # file -> frames trùng tên ở atlas khác (ambiguous)
    if frame_owner:
        tok = re.compile(r'[A-Za-z0-9_\-./]+\.(?:png|jpg|jpeg)')

        def add_hit(q, c, ln=None):
            if ln is not None:
                frame_lines[(q, c)].add(ln)
            others = other_owner.get(c, set())
            if q.endswith('.json') and any(os.path.dirname(o) == os.path.dirname(q) for o in others):
                return   # JSON dùng atlas cùng tên trong folder của NÓ ⇒ không phải consumer của bundle
            (frame_dup if others else frame_hits)[q].add(c)

        for q, lines in src.items():
            for i, t, live in lines:
                if not live:
                    continue
                for c in tok.findall(t):
                    c = c.rsplit('/', 1)[-1]
                    if c in frame_owner:
                        add_hit(q, c, i)
        for q, txt in resjson.items():
            if q.startswith(f'res/content/{b}/'):
                continue
            for c in set(tok.findall(txt)):
                c = c.rsplit('/', 1)[-1]
                if c in frame_owner:
                    add_hit(q, c)
    frame_active = {q: v for q, v in frame_hits.items() if is_active(loc_kind(q))}
    frame_dup_active = {q: v for q, v in frame_dup.items() if is_active(loc_kind(q))}
    P('| file dùng frame | kind | frames chỉ có ở atlas bundle | frames trùng tên atlas khác (ambiguous — xác nhận atlas nào được load) |'); P('|---|---|---|---|')
    allq = sorted(set(frame_hits) | set(frame_dup), key=lambda q: (not is_active(loc_kind(q)), q))
    for q in allq:
        u, d = frame_hits.get(q, set()), frame_dup.get(q, set())
        fmt = lambda s: ', '.join(sorted(s)[:8]) + (f' … +{len(s) - 8}' if len(s) > 8 else '') if s else '—'
        dups = ('; '.join(f'`{o}`' for o in sorted({o for fr in d for o in other_owner[fr]})[:3])) if d else ''
        P(f'| `{q}` | {"**ACTIVE**" if is_active(loc_kind(q)) else loc_kind(q)} | {fmt(u)} | {fmt(d)}' + (f' ← {dups}' if dups else '') + ' |')
    if not allq:
        P('| — | — | không frame nào được dùng ngoài folder | — |')
    P(''); P(f'→ {len(frame_active)} file ACTIVE dùng frame **chỉ có ở bundle** (⇒ atlas .plist+.png+astc phải **retained**, hoặc chấp nhận icon trống nếu là residual server-driven). '
             f'{len(frame_dup_active)} file ACTIVE dùng frame trùng tên ở atlas khác — sprite frame cache global theo tên: xác nhận atlas nào được `addSpriteFrames` trước khi kết luận.')
    if frame_active and all(q.endswith('/SlotGift.js') for q in frame_active):
        P('→ **Gợi ý Layer 2:** consumer ACTIVE duy nhất là `SlotGift.js` (icon quà server theo `giftInfo.name`) — feature đóng ⇒ server không trả gift đó nữa: '
          '**comment case tại caller kèm lý do** (rơi về default `icon_random.png`) và xóa atlas thay vì retain. Kiểm trước: JSON retained trong bundle có khai báo atlas này (`"Plist"`) không.')
    # JSON retained/khác trong CHÍNH folder bundle cũng là consumer của atlas (guiThankfulMonth.json → FirstChargeContent.plist)
    own_json_refs = collections.defaultdict(set)
    for q, txt in resjson.items():
        if q.startswith(f'res/content/{b}/'):
            for pl in plists:
                if os.path.basename(pl) in txt:
                    own_json_refs[pl].add(q)
    if own_json_refs:
        P('→ JSON trong folder bundle khai báo atlas (nếu JSON đó retained ⇒ atlas phải retained): ' + '; '.join(f'`{os.path.basename(pl)}` ← ' + ', '.join(f'`{os.path.basename(q)}`' for q in sorted(qs)) for pl, qs in own_json_refs.items()))
    P('')

    # ---- G4 res.<key>
    keys = [(k, v) for k, v in tbl.items() if f'content/{b}/' in v]
    P(f'## G4 — Bảng `res.<key>` ({tbl_file or "không thấy src/resource.js"}): {len(keys)} key trỏ vào bundle'); P('')
    P('| key | path | usage sống | ngoài retired dirs |'); P('|---|---|---|---|')
    key_active = []
    for k, v in sorted(keys):
        uses = [(q, i) for q, i, _ in grep_src(src, r'\bres\.' + re.escape(k) + r'\b') if q != tbl_file]
        ext = [(q, i) for q, i in uses if is_active(loc_kind(q))]
        key_active += [(k, q, i) for q, i in ext]
        P(f'| `{k}` | `{v}` | ' + (', '.join(f'`{q}:{i}`' for q, i in uses[:8]) or '—') + ' | ' +
          ('**' + ', '.join(f'`{q}:{i}`' for q, i in ext) + '**' if ext else '—') + ' |')
    P(''); P('→ Preload (`ResourceImage.js`) là ACTIVE nhưng chỉ *load*: nếu atlas bị xóa thì **comment dòng preload**; nếu atlas retained thì giữ.'); P('')

    # ---- G5 CDN
    cdn_hits = []
    for q in glob.glob(os.path.join(root, 'build', '**', 'cdn.json'), recursive=True):
        rel = norm(os.path.relpath(q, root))
        try:
            txt = io.open(q, encoding='utf-8', errors='replace').read()
        except Exception:
            continue
        n_ign = len(re.findall(r'res/content/' + re.escape(b) + r'/', txt))
        groups = re.findall(r'"name"\s*:\s*"(\w+)"\s*,\s*"path"\s*:\s*"([^"]*content/' + re.escape(b) + r'[^"]*)"', txt, re.S)
        if n_ign or groups:
            cdn_hits.append((rel, n_ign, groups))
    P(f'## G5 — `build/**/cdn.json`: {len(cdn_hits)} file tham chiếu'); P('')
    if cdn_hits:
        P('| cdn.json | dòng chứa `res/content/' + b + '/` | group |'); P('|---|---:|---|')
        for rel, n, g in cdn_hits:
            P(f'| `{rel}` | {n} | ' + (', '.join(f'`{x}` → `{y}`' for x, y in g) or '—') + ' |')
        P(''); P('→ dùng `cdn_prune.py --folder ' + b + ' --group <name>` sau khi xác nhận group chỉ được request từ module retired.')
    else:
        P('không có')
    P('')

    # ---- G5b runtime downloader: group của bundle trong src/base/download (gv.groupDL + GROUP_INFO PATH_TO_RESOURCE) → ai còn dùng tên group đó
    g5b_keys = {}   # key gv.groupDL -> group name
    for q, lines in src.items():
        if not q.startswith('src/base/download/'):
            continue
        txt = '\n'.join(t for _, t, _ in lines)
        for m in re.finditer(r'"(\w+)"\s*:\s*\{\s*PATH_TO_RESOURCE\s*:\s*"res/content/' + re.escape(b) + r'/"', txt):
            gname = m.group(1)
            for m2 in re.finditer(r'^\s*(\w+)\s*:\s*"' + re.escape(gname) + r'"\s*,?', txt, re.M):
                g5b_keys[m2.group(1)] = gname
    P(f'## G5b — Downloader runtime (`src/base/download`): {len(g5b_keys)} group của bundle — ' + (', '.join(f'`gv.groupDL.{k}` = "{v}"' for k, v in g5b_keys.items()) or 'không có')); P('')
    g5b_init = []
    if g5b_keys:
        P('| Nơi dùng | Kind | Loại | Dòng |'); P('|---|---|---|---|')
        for k in g5b_keys:
            for q, i, t in grep_src(src, r'groupDL\.' + k + r'\b', exclude_dirs=mdirs):
                s_ = t.strip()
                if re.search(r'listGroupInQueue|downloadGroup|checkExistAssetFileByGroupName|addGroupToQueue|showDL\(', s_) or (q.endswith('GroupMinigameAssetUtil.js') and 'listGroupInQueue' in s_):
                    typ = '**KHỞI PHÁT tải/kiểm file**'
                    if is_active(loc_kind(q)):
                        g5b_init.append((q, i))
                else:
                    typ = 'passive (map tên/folder/UI theo groupName truyền vào)'
                P(f'| `{q}:{i}` | {loc_kind(q)} | {typ} | `{s_[:90]}` |')
        P('')
        P(f'→ Caller ACTIVE khởi phát tải/kiểm file của group này: **{len(g5b_init)}**' + (' — ' + ', '.join(f'`{q}:{i}`' for q, i in g5b_init) + ' ⇒ phải xử lý (đổi group / comment) trước khi xóa' if g5b_init else ' ⇒ passive branch còn lại vô hại (tên group không còn trong cdn.json ⇒ `FAILED_GROUP_NAME`, không crash)') + '. Kiểm `GroupMinigameAssetUtil.listGroupInQueue` (danh sách tải khi unlock) không chứa group này ở dòng sống.')
        P('')

    # ---- G6 dynamic refs
    basenames = {os.path.basename(p) for p, _ in inv}
    dyn = [x for x in grep_src(src, re.escape(f'content/{b}')) if not any(bn in x[2] for bn in basenames)]
    P(f'## G6 — Tham chiếu động tới `content/{b}` (không kèm tên file): {len(dyn)}'); P('')
    for q, i, t in dyn:
        P(f'- `{q}:{i}` [{loc_kind(q)}] `{t[:140]}`')
    P(''); P('→ Path ghép chuỗi (rank image, Spine `AniPathFolder`, …). Nằm trong module dir ⇒ Layer 1 đủ. ACTIVE ⇒ phải xử lý.'); P('')

    # ---- G7 PoolFunction
    consts = set()
    for q, lines in src.items():
        if not in_dirs(q, mdirs):
            continue
        for i, t, live in lines:
            if live:
                for m in re.finditer(r'PoolFunction\.regFunc(?:SameId)?\(\s*PoolFunction\.(\w+)', t):
                    consts.add(m.group(1))
    P(f'## G7 — PoolFunction: {len(consts)} constant regFunc trong module → caller sống ngoài module'); P('')
    P('| constant | caller | kind | kiểu call |'); P('|---|---|---|---|')
    fire = retval = 0
    pf_active = []
    for cst in sorted(consts):
        callers = grep_src(src, r'PoolFunction\.' + cst + r'\b', exclude_dirs=mdirs)
        callers = [x for x in callers if not x[0].endswith(('/PoolFunction.js', '/CmdDefine.js'))]
        for q, i, t in callers:
            k = 'fire-and-forget' if re.match(r'^PoolFunction\.doFunc\([^;]*\);?\s*(//.*)?$', t) else 'RETURN-VALUE? (kiểm undefined-safe)'
            if k.startswith('fire'):
                fire += 1
            else:
                retval += 1
            if is_active(loc_kind(q)):
                pf_active.append((cst, q, i, k))
            P(f'| `{cst}` | `{q}:{i}` | {loc_kind(q)} | {k} — `{t[:100]}` |')
    P(''); P(f'fire-and-forget: {fire} · return-value: {retval}. `doFunc` key chưa regFunc ⇒ trả `undefined` im lặng (Layer 2 chỉ khi caller dùng return value và `undefined` gây crash).'); P('')

    # ---- G8 Layer 4c: classes retired → new / extends from active
    classes, gui_classes = {}, set()
    RES_LOAD = re.compile(r'syncAllChild|ccs\.load|addSpriteFrames|createWithSpriteFrameName|reloadImageTexture|loadTexture')
    # cc.Class = data model thuần (không phải Node) → không tính GUI trừ khi file có load resource
    GUI_BASE = re.compile(r'BaseScreen|BaseLayer|BasePopup|^cc\.(?!Class\b)|^ccui\.|Gui|Slot|Node|Layer|Screen|Popup|Icon|Sprite')
    for q, lines in src.items():
        if not in_dirs(q, mdirs):
            continue
        ftxt = '\n'.join(t for _, t, _ in lines)
        for i, t, live in lines:
            m = re.match(r'^\s*(?:var|const|let)?\s*([A-Z]\w*)\s*=\s*([\w.]+)\.extend\s*\(', t)
            if m:
                classes[m.group(1)] = q
                # GUI/Node class (ctor load resource) vs data model (cc.Class / không load gì)
                if GUI_BASE.search(m.group(2)) or RES_LOAD.search(ftxt):
                    gui_classes.add(m.group(1))

    def guard_near(q, i, span=15):
        """có check _isEnable/isEnable( trong ≤span dòng sống phía trên site không (heuristic guard trong hàm chứa)"""
        lines = src[q]
        return any(re.search(r'_isEnable|isEnable\(', t) for j, t, live in lines[max(0, i - 1 - span):i - 1] if live)

    P(f'## G8 — Layer 4c/3: {len(classes)} class retired ({len(gui_classes)} GUI/Node, {len(classes) - len(gui_classes)} data model) → `new X(` / `= X.extend(` ở code ngoài module'); P('')
    P('| class | loại | nơi dùng | kind | dạng | guard `_isEnable` gần (≤15 dòng)? |'); P('|---|---|---|---|---|---|')
    l4c_active = []
    for c in sorted(classes):
        for q, i, t in grep_src(src, r'(?:new\s+' + c + r'\s*\(|=\s*' + c + r'\.extend\s*\()', exclude_dirs=mdirs):
            if q == 'src/gamemgr/ModuleMgr.js':
                continue
            kind = 'EXTENDS (ctor cha load JSON!)' if '.extend' in t else 'new'
            typ = 'GUI/Node' if c in gui_classes else 'data model'
            g = 'có' if guard_near(q, i) else '**không**'
            if is_active(loc_kind(q)) and c in gui_classes:
                l4c_active.append((c, q, i, kind))
            P(f'| `{c}` | {typ} | `{q}:{i}` | {loc_kind(q)} | {kind} — `{t[:80]}` | {g} |')
    P(''); P('→ EXTENDS từ ACTIVE: JSON mà ctor cha `syncAllChild` phải **retained** (hoặc lớp con override ctor). `new` GUI/Node từ ACTIVE chưa có guard gần: cần Layer 3 (guard trong util/module retired, hoặc xác nhận hàm chứa đã guard ở xa hơn). Data model `new` không load resource — giữ nguyên.'); P('')

    # ---- G9 Layer 4b: util retired called from active
    # identifier top-level của module: `var X = …` HOẶC object gán trực tiếp `X.fn = function` / `X = {` (nhiều Util không có `var`)
    ident = {}
    for q, lines in src.items():
        if not in_dirs(q, mdirs):
            continue
        for i, t, live in lines:
            m = re.match(r'^(?:var|const|let)\s+([A-Za-z_]\w*)\s*=', t) or \
                re.match(r'^([A-Z]\w*)\s*=\s*\{', t) or \
                re.match(r'^([A-Z]\w*)\.\w+\s*=\s*function\b', t)
            if m:
                ident.setdefault(m.group(1), set()).add(q)
    calls = collections.defaultdict(set)
    for q, lines in src.items():
        if in_dirs(q, mdirs) or q == 'src/gamemgr/ModuleMgr.js':
            continue
        for i, t, live in lines:
            if not live:
                continue
            for m in re.finditer(r'\b([A-Za-z_]\w*)\.(\w+)\s*\(', t):
                X, fn = m.group(1), m.group(2)
                if X in ident and X not in SKIP_CALLERS and fn not in ('extend', 'prototype', 'call', 'apply', 'bind'):
                    calls[(X, fn)].add((q, i))   # X.extend( là kế thừa → G8

    def fn_body(X, fn):
        for f_ in sorted(ident[X]):
            t = '\n'.join(x[1] for x in src[f_])
            m = re.search(r'^\s*' + re.escape(X) + r'\.' + re.escape(fn) + r'\s*=\s*function\s*\([^)]*\)\s*\{', t, re.M) or \
                re.search(r'^\s*' + re.escape(fn) + r'\s*:\s*function\s*\([^)]*\)\s*\{', t, re.M)
            if not m:
                continue
            depth, i = 1, m.end()
            while i < len(t) and depth:
                depth += {'{': 1, '}': -1}.get(t[i], 0); i += 1
            return t[m.end():i]
        return None

    P(f'## G9 — Layer 4b: {len(calls)} cặp `X.fn(` (X định nghĩa trong module) được gọi ngoài module'); P('')
    P('| X.fn | body construct/load? | guard `_isEnable`? | caller |'); P('|---|---|---|---|')
    l4b_construct = []
    for (X, fn), locs in sorted(calls.items()):
        body = fn_body(X, fn)
        if body is None:
            info, guard = '?? không thấy định nghĩa (property/const/JSONConfig?)', '—'
        else:
            raw_all = sorted(set(m.group(0).split('(')[0].strip() for m in CONSTRUCT_PAT.finditer(body)))
            # `new <DataModel>(` (class của module không phải GUI/Node) không load resource → không tính construct
            models = [r_ for r_ in raw_all if r_.startswith('new ') and r_[4:].strip() in classes and r_[4:].strip() not in gui_classes]
            raw = [r_ for r_ in raw_all if r_ not in models]
            info = ('**' + ', '.join(raw) + '**') if raw else ('pure-data' + (f' (data model: {", ".join(models)})' if models else ''))
            guard = 'có' if re.search(r'_isEnable|isEnable\(', body) else 'không'
            if raw:
                l4b_construct.append((X, fn, raw, sorted(locs)))
        kinds = {loc_kind(q) for q, _ in locs}
        P(f'| `{X}.{fn}` | {info} | {guard} | ' + ', '.join(f'`{q}:{i}`' for q, i in sorted(locs)[:5]) + (f' +{len(locs) - 5}' if len(locs) > 5 else '') + f' [{"/".join(sorted(kinds))}] |')
    P(''); P('→ body có construct/load + caller ACTIVE ⇒ Layer 3 **trong hàm util đó** (`if (!Util._isEnable) return <safe default>;`). pure-data ⇒ giữ nguyên.'); P('')

    # ---- G10 CMD + AniSource
    cmds, anis = set(), set()
    for q, lines in src.items():
        if not in_dirs(q, mdirs):
            continue
        for i, t, live in lines:
            if live:
                cmds.update(re.findall(r'case\s+EXCHANGE\.CMD\.(\w+)', t))
                anis.update(re.findall(r'AniSource\.(\w+)', t))
    P('## G10 — CMD handler trong module (Layer 1 ⇒ không route): ' + (', '.join(f'`{c}`' for c in sorted(cmds)) or '(none)')); P('')
    # ---- G10b Animation của bundle: group (DragonBones/Spine) mà usage nằm trong module dir của bundle → quyết định xóa cùng batch
    anim_del, anim_wait, anim_keep = [], [], []
    if not a.skip_anim:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import trace_anim
        # dir của bundle này luôn được coi là retired (kể cả module chưa có tag //D) → dạng "dir=bundle"
        actx = trace_anim.analyze(root, src=src, extra_retired=[f'{d}={b}' for d in mdirs] + list(a.extra_retired_dir), astc=a.astc)
        trace_anim.write_report(actx, out_dir)    # report_animation.md + inventory_animation.tsv (gen_anim_manifest cần inventory)
        deleted_dirs = actx['deleted']            # dir module đã Layer 1 (ctor comment)
        dir_of_bundle = {}
        for r in mm:
            if r.get('dir'):
                dir_of_bundle.setdefault(r['dir'], []).append(r)
        for s, row in sorted(actx['rows'].items()):
            locs = [(k, loc) for k, loc in row['usage']]
            if not any(in_dirs(loc.split(':')[0], mdirs) for k, loc in locs):
                continue                          # không liên quan bundle này
            others = [(k, loc) for k, loc in locs if not in_dirs(loc.split(':')[0], mdirs)]
            if row['flags']:
                anim_keep.append((s, row, 'KEEP — ' + '; '.join(sorted(row['flags']))))
            elif any(is_active(k) for k, _ in locs) or any(is_active(k) for k, _ in others):
                anim_keep.append((s, row, 'KEEP — ACTIVE/Guard-Only dùng: ' + ', '.join(f'`{loc}`' for k, loc in locs if is_active(k))[:160]))
            elif not others:
                anim_del.append((s, row, 'chỉ bundle này dùng'))
            else:
                other_dirs = {next((d for d in actx['retired'] if in_dirs(loc.split(':')[0], [d])), None) for k, loc in others}
                other_dirs.discard(None)
                pending = [d for d in other_dirs if d not in deleted_dirs]
                if pending:
                    anim_wait.append((s, row, 'CHỜ — còn dùng bởi module chưa Layer 1: ' + ', '.join(f'`{d}` ({actx["retired"][d]})' for d in pending)))
                else:
                    anim_del.append((s, row, 'chung với bundle đã retire: ' + ', '.join(f'`{actx["retired"][d]}`' for d in other_dirs)))
        P(f'### G10b — Animation của bundle (group DragonBones/Spine có usage trong module dir): xóa {len(anim_del)} · chờ {len(anim_wait)} · giữ {len(anim_keep)} · preloadAllAnimation caller = {len(actx["preload_callers"])} (phải 0)'); P('')
        P('| stem | type | MiB | file | quyết định | usage |'); P('|---|---|---:|---:|---|---|')
        for s, row, why in anim_del + anim_wait + anim_keep:
            u = '; '.join(f'{k} `{loc}`' for k, loc in sorted(row['usage'])[:3])
            P(f'| `{s}` | {row["type"]} | {row["size"]/1048576:.2f} | {len(row["files"])} | **{why}** | {u} |')
        if not (anim_del or anim_wait or anim_keep):
            P('| — | — | — | — | module không dùng animation nào | — |')
        P('')
        if anim_del:
            sp = os.path.join(out_dir, f'anim_{b}.stems.txt')
            io.open(sp, 'w', encoding='utf-8').write(f'# animation xóa cùng bundle {b} — sinh bởi trace_bundle.py G10b\n' + '\n'.join(s for s, _, _ in anim_del) + '\n')
            P(f'→ `gen_anim_manifest.py --bundle {b}-anim --from-file {norm(sp)} --inventory {norm(os.path.join(out_dir, "inventory_animation.tsv"))} --build <build> --branch <branch>` → Audit → Move → Verify (mode `group`), commit cùng batch. '
              f'Tổng {sum(r["size"] for _, r, _ in anim_del)/1048576:.2f} MiB, {sum(len(r["files"]) for _, r, _ in anim_del)} file. Registry AniSource giữ nguyên (preloadAllAnimation 0 caller).')
        if actx['preload_callers']:
            P('⚠ **preloadAllAnimation có caller sống** — key registry treo sẽ lỗi lúc load ⇒ KHÔNG xóa animation khi chưa xử lý registry.')
        P('')
    else:
        P('### G10b — Animation: bỏ qua (--skip-anim)'); P('')

    # ---- G11 legacy *.manifest (AssetsManager / hot-update) — chỉ thông tin, không sửa
    man_hits = []
    for q in glob.glob(os.path.join(root, '*.manifest')) + glob.glob(os.path.join(root, 'res', '*.manifest')):
        try:
            n = io.open(q, encoding='utf-8', errors='replace').read().count(f'content/{b}/')
        except Exception:
            n = 0
        if n:
            man_hits.append((norm(os.path.relpath(q, root)), n))
    P(f'## G11 — `*.manifest` legacy (AssetsManager): {len(man_hits)} file có entry'); P('')
    for q, n in man_hits:
        P(f'- `{q}`: {n} entry — legacy, **không sửa** (các batch trước không đụng; downloader chỉ so md5 file có trong manifest local)')
    if not man_hits:
        P('không có')
    P('')

    # ---- Tổng kết theo file (v2): Bundle | File group | Size | Frame | Consumer (node UI JSON / file:dòng) | Quyết định
    # In ở Phase A (trace) và pre-Move Phase B. File đã xóa lấy từ manifest moved/verified của bundle (đợt 1, đợt 2…) → "ĐÃ XÓA".
    frame_users = collections.defaultdict(set)          # frame -> {file ACTIVE dùng}
    for q, frs in frame_hits.items():
        if is_active(loc_kind(q)):
            for fr in frs:
                frame_users[fr].add(q)
    frame_dup_users = collections.defaultdict(set)
    for q, frs in frame_dup.items():
        if is_active(loc_kind(q)):
            for fr in frs:
                frame_dup_users[fr].add(q)
    inv_paths = {p for p, _ in inv}
    decision = {}                                        # path -> (quyết định, frame/ảnh, ai dùng)
    plist_used = {}                                      # plist -> {frame: {consumer ACTIVE}}

    def json_nodes(q, fr):
        """node Cocos Studio (Name) có FileData/*FileData trỏ frame `fr` trong UI JSON q"""
        try:
            data = json.loads(resjson[q])
        except Exception:
            return []
        out = []

        def walk(o, parent):
            if isinstance(o, dict):
                name = o.get('Name') if isinstance(o.get('Name'), str) else None
                for k, v in o.items():
                    if isinstance(v, dict) and isinstance(v.get('Path'), str) and os.path.basename(v['Path']) == fr:
                        out.append((name or parent or '?') + ('' if k == 'FileData' else f'.{k}'))
                for k, v in o.items():
                    if isinstance(v, (dict, list)):
                        walk(v, name or parent)
            elif isinstance(o, list):
                for x in o:
                    walk(x, parent)
        walk(data, None)
        return sorted(set(out))

    def short(u):
        """đường dẫn ngắn cho bảng: res/content/room/x.json → room/x.json; src/.../SlotGift.js → SlotGift.js"""
        if u.startswith('res/content/'):
            return u[len('res/content/'):]
        if u.startswith('res/'):
            return u[4:]
        return os.path.basename(u)

    def consumer_detail(fr, us):
        """UI JSON → `room/guiResultVersus.json` node `a`; ≥3 file cùng folder → `room/guiRoomUserInfo*.json ×6 node …`; JS → `SlotGift.js:1168`"""
        parts, by = [], collections.defaultdict(list)
        for u in sorted(us):
            if u.endswith('.json'):
                by[os.path.dirname(u)].append((os.path.basename(u), json_nodes(u, fr)))
            else:
                ls = sorted(frame_lines.get((u, fr), set()))
                parts.append(f'`{short(u)}:{",".join(map(str, ls[:4]))}`' if ls else f'`{short(u)}`')
        for d, items in sorted(by.items()):
            nodes = sorted({nn for _, ns in items for nn in ns})
            node_s = (' node ' + ', '.join(f'`{nn}`' for nn in nodes[:4]) + (' …' if len(nodes) > 4 else '')) if nodes else ''
            sd = short(d + '/x')[:-1]
            if len(items) >= 3:
                names = sorted(f for f, _ in items)
                pre = os.path.commonprefix(names)
                lab = f'{sd}{pre}*.json' if len(pre) >= 3 else f'{sd}*.json'
                parts.append(f'`{lab}` ×{len(items)}' + node_s)
            else:
                for f, ns in items:
                    parts.append(f'`{sd}{f}`' + ((' node ' + ', '.join(f'`{nn}`' for nn in ns[:4])) if ns else ''))
        return ' · '.join(parts)

    def consumer_summary(used):
        """gom theo consumer: UI JSON `room/guiResultVersus.json` node a, b · `room/guiRoomUserInfo*.json` ×6 node c | JS `SlotGift.js:1168, 1381`"""
        json_nodes_by = collections.defaultdict(set)   # file json -> {node}
        js_lines_by = collections.defaultdict(set)     # file js -> {line}
        for fr, us in used.items():
            for u in us:
                if u.endswith('.json'):
                    json_nodes_by[u].update(json_nodes(u, fr))
                else:
                    js_lines_by[u].update(frame_lines.get((u, fr), set()))
        parts = []
        by_stem = collections.defaultdict(list)        # (folder, tên gốc bỏ hậu tố số) -> [(file, nodes)]
        for u, nodes in json_nodes_by.items():
            stem = re.sub(r'\d.*$', '', os.path.splitext(os.path.basename(u))[0])
            by_stem[(os.path.dirname(u), stem)].append((os.path.basename(u), nodes))
        json_parts = []
        for (d, stem), items in sorted(by_stem.items()):
            sd = short(d + '/x')[:-1]
            nodes = sorted({nn for _, ns in items for nn in ns})
            node_s = (' node ' + ', '.join(f'`{nn}`' for nn in nodes[:8]) + (' …' if len(nodes) > 8 else '')) if nodes else ''
            if len(items) >= 3:
                json_parts.append(f'`{sd}{stem}*.json` ×{len(items)}' + node_s)
            else:
                for f, ns in sorted(items):
                    json_parts.append(f'`{sd}{f}`' + ((' node ' + ', '.join(f'`{nn}`' for nn in sorted(ns)[:8])) if ns else ''))
        cells = []
        if json_parts:
            cells.append('**UI JSON:** ' + '; '.join(json_parts))
        js_parts = [f'`{short(u)}:{", ".join(map(str, sorted(ls)))}`' if ls else f'`{short(u)}`' for u, ls in sorted(js_lines_by.items())]
        if js_parts:
            cells.append('**JS:** ' + '; '.join(js_parts))
        return cells

    def group_users(us):
        return consumer_detail('', us) if False else ', '.join(f'`{u}`' for u in sorted(us)[:4])

    # res.<key> của bundle được code ACTIVE (không phải preload ResourceImage) dùng → GIỮ
    key_by_rel = {v: k for k, v in keys}
    key_uses = collections.defaultdict(list)
    for k, q, i in key_active:
        if not q.endswith('/ResourceImage.js'):
            key_uses[k].append(f'{q}:{i}')

    def key_use(p):
        k = key_by_rel.get(p[4:]) if p.startswith('res/') else None
        return (k, key_uses.get(k, [])) if k else (None, [])

    class_hits = collections.defaultdict(list)          # file class retired -> [(class, caller loc, kind)]
    for c, q2, i2, kind_ in l4c_active:
        if c in classes:
            class_hits[classes[c]].append((c, f'{q2}:{i2}', kind_))

    def json_decision(p):
        g = g2info.get(p, {'cls': '?', 'ext': [], 'rj': [], 'mod': []})
        if g['cls'] == 'ACTIVE-CONSUMER':
            who = '; '.join(f'`{loc}` [{k}]' for k, loc in g['ext'][:4]) + ('; ' + '; '.join(f'`{q}` (res JSON)' for q in g['rj'][:3]) if g['rj'] else '')
            return ('GIỮ', 'JSON được syncAllChild', who + ' — → hoặc Layer 3 chặn đường construct trong module retired nếu nhánh đó đã chết')
        hits = [h for q in g.get('mod', []) for h in class_hits.get(q, [])]
        if hits:
            ext_ = [h for h in hits if h[2].startswith('EXTENDS')]
            who = '; '.join(f'`{c}` ← `{loc}` ({kind_.split()[0]})' for c, loc, kind_ in hits[:4])
            if ext_:
                return ('GIỮ', 'JSON của GUI được ACTIVE kế thừa (4c)', who + ' — ctor cha syncAllChild JSON này ⇒ retained')
            return ('CẦN QUYẾT', 'JSON của GUI được `new` từ ACTIVE (G8)', who + ' — → Layer 3 guard tại util/module retired (hoặc guard sẵn ở caller) rồi XÓA; chưa guard ⇒ GIỮ')
        return ('XÓA', '—', 'chỉ module retired dùng' if g['cls'].startswith('Retired') else 'orphan (0 consumer) — xác nhận git log')

    def flat_rows(rows_):
        out = []
        for r_ in rows_:
            if r_[0] == '__multi__':
                out.append(' '.join(r_[1]) + ' ← ' + ' '.join(r_[2]))
            else:
                out.append(f'{r_[0]} ← {r_[1]}')
        return out

    def plist_decision(p):
        frs = [fr for fr, owners in frame_owner.items() if p in owners]
        used = {fr: frame_users[fr] for fr in frs if frame_users.get(fr)}
        amb = {fr: frame_dup_users[fr] for fr in frs if frame_dup_users.get(fr)}
        dep_json = [q for q in own_json_refs.get(p, set()) if decision.get(q, json_decision(q))[0] != 'XÓA']
        frame_rows = ([('__multi__', [f'{len(used)}/{len(frs)} frame: ' + ', '.join(f'`{fr}`' for fr in sorted(used)[:15]) + (' …' if len(used) > 15 else '')], consumer_summary(used))]
                      if used else [])
        if dep_json:
            rows_ = [(f'atlas {len(frs)} frame', 'JSON **giữ lại** trong folder khai báo atlas: ' + ', '.join(f'`{os.path.basename(q)}`' for q in sorted(dep_json)))] + frame_rows
            return ('GIỮ', rows_[0][0], ' | '.join(flat_rows(rows_)), rows_)
        if used:
            plist_used[p] = used
            users_all = {u for us in used.values() for u in us}
            fr_s = f'{len(used)}/{len(frs)} frame'
            if all(u.endswith('/SlotGift.js') for u in users_all):
                rows_ = frame_rows + [('→ phương án', 'icon quà server theo `giftInfo.name`: feature đóng ⇒ **Layer 2 comment case** (fallback `icon_random.png`) rồi XÓA atlas')]
                return ('CẦN QUYẾT', fr_s, ' | '.join(flat_rows(rows_)), rows_)
            n_json = sum(1 for u in users_all if u.endswith('.json')); n_js = len(users_all) - n_json
            hint = f'art re-pack {len(used)} frame sang atlas dùng chung của consumer + sửa {n_json} UI JSON' + (f' + {n_js} chỗ JS' if n_js else '') + ' tham chiếu; hoặc giữ'
            rows_ = frame_rows + [('→ phương án xóa', hint)]
            return ('GIỮ', fr_s, ' | '.join(flat_rows(rows_)), rows_)
        k, uses = key_use(os.path.splitext(p)[0] + '.png')
        if uses:
            return ('GIỮ', f'atlas {len(frs)} frame — texture load qua `res.{k}`', '; '.join(f'`{short(u)}`' for u in uses[:4]))
        if amb:
            return ('XÓA?', f'{len(amb)} frame trùng tên atlas khác', 'xác nhận atlas nào được `addSpriteFrames`: ' + ', '.join(f'`{fr}`' for fr in sorted(amb)[:4]))
        pre = [f'{short(q)}:{i}' for kk, q, i in key_active if kk == key_by_rel.get(os.path.splitext(p)[0][4:] + '.png') and q.endswith('/ResourceImage.js')]
        return ('XÓA', f'atlas {len(frs)} frame', '0 frame dùng ngoài module' + (f' — comment preload {", ".join(f"`{u}`" for u in pre)}' if pre else ''))

    def raw_decision(p):
        g = g2info.get(p, {'cls': '?', 'ext': [], 'rj': []})
        k, uses = key_use(p)
        if uses:
            return ('GIỮ', f'ảnh rời — load qua `res.{k}`', '; '.join(f'`{u}`' for u in uses[:4]) + ' [ACTIVE]')
        if g['ext'] or g['rj']:
            return ('GIỮ', 'ảnh rời', '; '.join(f'`{loc}` [{k}]' for k, loc in g['ext'][:4]) + ('; ' + '; '.join(f'`{q}`' for q in g['rj'][:3]) if g['rj'] else ''))
        base = os.path.basename(p)
        dep = [q for q, txt in resjson.items() if q.startswith(f'res/content/{b}/') and base in txt and decision.get(q, json_decision(q))[0] != 'XÓA']
        if dep:
            return ('GIỮ', 'ảnh rời', 'JSON giữ lại trong folder tham chiếu: ' + ', '.join(f'`{os.path.basename(q)}`' for q in sorted(dep)))
        return ('XÓA', '—', 'chỉ JSON/module retired dùng' if g['cls'].startswith('Retired') else 'orphan')

    for p, _ in inv:
        if p.startswith('res/') and p.endswith('.json'):
            decision[p] = json_decision(p)
    for p, _ in inv:
        if p.startswith('res/') and p.endswith('.plist'):
            decision[p] = plist_decision(p)
    for p, _ in inv:
        if p.startswith('res/') and p not in decision:
            stem = os.path.splitext(p)[0]
            if stem + '.plist' in inv_paths and p.lower().endswith(TEX_EXT):
                d0 = decision[stem + '.plist']
                decision[p] = (d0[0], 'texture của atlas', f'theo `{os.path.basename(stem)}.plist`')
            else:
                decision[p] = raw_decision(p)
    for p, _ in inv:
        if p.startswith(a.astc + '/'):
            s_ = 'res' + p[len(a.astc):]
            d0 = decision.get(s_, ('XÓA', '—', 'không có bản gốc'))
            decision[p] = (d0[0], 'ASTC mirror', f'theo `{os.path.basename(s_)}`')

    # file đã xóa theo manifest moved/verified (đợt 1, đợt 2 …; bỏ -anim)
    mdir = a.manifest_dir or os.path.join(root, 'docs', 'modules', 'deletefeaturecontent', 'manifests')
    done = {}                                            # path -> (bundle manifest, bytes)
    for mf in sorted(glob.glob(os.path.join(mdir, f'{b}.json')) + glob.glob(os.path.join(mdir, f'{b}-*.json'))):   # không bắt bundle khác cùng prefix (battlepass vs battlepass21)
        try:
            mj = json.load(io.open(mf, encoding='utf-8'))
        except Exception:
            continue
        if mj.get('bundle', '').endswith('-anim') or mj.get('status') not in ('moved', 'verified'):
            continue
        for x in mj.get('removed', []):
            if not os.path.exists(x['path']):
                done[x['path']] = (mj['bundle'], int(x.get('bytes', 0) or 0))
    all_paths = inv_paths | set(done)

    def gkey(p):
        rel = p[len(a.astc) + 1:] if p.startswith(a.astc + '/') else p[4:]
        stem, ext = os.path.splitext(rel)
        return stem if (ext == '.plist' or ('res/' + stem + '.plist') in all_paths) else rel
    groups_ = collections.OrderedDict()
    for p, s in list(inv) + [(p, bb) for p, (_, bb) in done.items()]:
        g = groups_.setdefault(gkey(p), {'files': [], 'bytes': 0})
        g['files'].append(p); g['bytes'] += s
    def glabel(g):
        res_files = sorted(f for f in g['files'] if f.startswith('res/'))
        astc_n = sum(1 for f in g['files'] if f.startswith(a.astc + '/'))
        names = [os.path.basename(f) for f in res_files] or [os.path.basename(f) for f in g['files']]
        if len(names) > 1 and len({os.path.splitext(x)[0] for x in names}) == 1:
            lab = os.path.splitext(names[0])[0] + ' ' + ' + '.join(os.path.splitext(x)[1] for x in names)
        else:
            lab = ' + '.join(names)
        return lab + (f' + astc ×{astc_n}' if astc_n else '')
    def gdecision(g):
        """→ (quyết định, [(frame/ảnh, consumer)], ghi chú đã xóa trước)"""
        mains = [f for f in g['files'] if f.startswith('res/') and f in decision]
        if not mains:
            bnd = {done[f][0] for f in g['files'] if f in done}
            return ('ĐÃ XÓA', [], 'đã xóa ở ' + ', '.join(f'`{x}`' for x in sorted(bnd)))
        main = next((f for f in mains if f.endswith('.plist')), mains[0])
        dec = decision[main]
        d, fr, who = dec[0], dec[1], dec[2]
        lines = dec[3] if len(dec) > 3 else [(fr, who)]
        gone = [os.path.basename(f) for f in g['files'] if f in done]
        return (d, lines, ('đã xóa trước: ' + ', '.join(gone)) if gone else '')

    P(f'## Tổng kết — file GIỮ LẠI của `{b}` và lý do (File | Size | Frame/ảnh active dùng | Consumer active)'); P('')
    P('*Chỉ liệt kê file không xóa được ngay (GIỮ / CẦN QUYẾT / XÓA?). File xóa được và file đã xóa (theo manifest) chỉ đếm ở dòng Tổng. Consumer: UI JSON ghi `folder/file.json node <tên node>`; code ghi `File.js:dòng`; ≥3 file cùng folder gom `folder/prefix*.json ×n`.*'); P('')
    P('| File | Size | Frame/ảnh active dùng | Consumer active |'); P('|:' + '-' * 12 + '|' + '-' * 8 + ':|:' + '-' * 46 + '|:' + '-' * 60 + '|')   # tỉ lệ độ rộng gợi ý cho renderer
    rank = {'GIỮ': 0, 'CẦN QUYẾT': 1, 'XÓA?': 2, 'XÓA': 3, 'ĐÃ XÓA': 4}
    tot_dec = collections.Counter(); tot_b = collections.Counter(); rows_out = []; n_keep = 0; suggestions = []; group_notes = []
    for k, g in sorted(groups_.items(), key=lambda kv: (rank.get(gdecision(kv[1])[0], 9), kv[0])):
        d, lines, note = gdecision(g)
        tot_dec[d] += len(g['files']); tot_b[d] += g['bytes']
        rows_out.append((k, g, d, lines, note))
        if d in ('XÓA', 'ĐÃ XÓA'):
            continue
        n_keep += 1
        parts_ = glabel(g).split(' ', 1)                       # 'battlePassContent .plist + .png + astc ×1' → tên / đuôi
        label = f'`{parts_[0]}` **{d}**' + (f' *({note})*' if note else '')
        size_s = f'{g["bytes"]/1048576:.2f} MiB' if g['bytes'] >= 1048576 else f'{g["bytes"]/1024:.0f} KB'
        if len(parts_) > 1:
            group_notes.append(f'`{parts_[0]}` = {parts_[1]}')
        cells_rows = []                                    # list[(frame_cell, consumer_cell)]
        for ln in (lines or [('—', '—')]):
            if ln[0] == '__multi__':
                fc, cc = ln[1], ln[2]
                for i_ in range(max(len(fc), len(cc))):
                    cells_rows.append((fc[i_] if i_ < len(fc) else '', cc[i_] if i_ < len(cc) else ''))
            elif ln[0].startswith('→'):
                suggestions.append((parts_[0], ln[1]))
            else:
                cells_rows.append((ln[0], ln[1].replace('<br>', ' · ')))
        for j, (fr, who) in enumerate(cells_rows or [('—', '—')]):
            P(f'| {label if j == 0 else ""} | {size_s if j == 0 else ""} | {fr} | {who} |')
    if n_keep == 0:
        P('| *(không có — mọi file đều xóa được)* | | | |')
    P('')
    # ---- summary_<b>.html: bảng HTML thật (rowspan merge dọc + <br>) cho viewer render HTML / trình duyệt
    import html as _html
    def md2html(s_):
        s_ = _html.escape(s_)
        s_ = re.sub(r'`([^`]*)`', r'<code>\1</code>', s_)
        s_ = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', s_)
        return s_
    hrows = []
    for k, g, d, lines, note in rows_out:
        if d in ('XÓA', 'ĐÃ XÓA'):
            continue
        parts_ = glabel(g).split(' ', 1)
        frame_html, cons_html = [], []
        for ln in (lines or []):
            if ln[0] == '__multi__':
                frame_html += [md2html(x) for x in ln[1]]
                for c_ in ln[2]:
                    lab, _, rest = c_.partition(' ')
                    cons_html.append(f'<b>{_html.escape(lab.strip("*"))}</b><br>' + '<br>'.join(md2html(x.strip()) for x in rest.split('; ')))
            elif not ln[0].startswith('→'):
                frame_html.append(md2html(ln[0])); cons_html.append(md2html(ln[1].replace('<br>', ' · ')))
        n_ = max(1, len(cons_html))
        size_s = f'{g["bytes"]/1048576:.2f} MiB' if g['bytes'] >= 1048576 else f'{g["bytes"]/1024:.0f} KB'
        first = (f'<td rowspan="{n_}"><code>{_html.escape(parts_[0])}</code>' + (f'<br><small>{_html.escape(parts_[1])}</small>' if len(parts_) > 1 else '') + f'<br><b>{d}</b></td>'
                 f'<td rowspan="{n_}" style="text-align:right">{size_s}</td><td rowspan="{n_}">' + '<br>'.join(frame_html) + '</td>')
        for i_ in range(n_):
            hrows.append('<tr>' + (first if i_ == 0 else '') + f'<td>{cons_html[i_] if i_ < len(cons_html) else ""}</td></tr>')
    if hrows:
        hp = os.path.join(out_dir, f'summary_{b}.html')
        io.open(hp, 'w', encoding='utf-8').write(
            '<!doctype html><meta charset="utf-8"><title>' + _html.escape(b) + ' — file giữ lại</title>'
            '<style>body{font:14px system-ui,Segoe UI,sans-serif;margin:16px}table{border-collapse:collapse}td,th{border:1px solid #bbb;padding:6px 8px;vertical-align:top}'
            'th{background:#f2f2f2}code{background:#eee;padding:1px 4px;border-radius:3px}td:nth-child(1){width:14%}td:nth-child(2){width:7%}td:nth-child(3){width:34%}</style>'
            f'<h3>Tổng kết — file GIỮ LẠI của <code>{_html.escape(b)}</code> và lý do</h3>'
            '<table><tr><th>File</th><th>Size</th><th>Frame/ảnh active dùng</th><th>Consumer active</th></tr>' + ''.join(hrows) + '</table>'
            + ('<p><b>Đề xuất</b> (không phải dữ kiện trace): ' + '; '.join(f'<code>{_html.escape(n_)}</code>: {_html.escape(x)}' for n_, x in suggestions) + '</p>' if suggestions else ''))
        P(f'*Bản HTML có merge cell + xuống dòng thật: `{norm(hp)}` (mở bằng trình duyệt hoặc VS Code preview mặc định).*'); P('')
    if group_notes:
        P('*Nhóm file: ' + ' · '.join(group_notes) + '*'); P('')
    if suggestions:
        P('**Đề xuất** (không phải dữ kiện trace — chốt với user):')
        for name_, txt in suggestions:
            P(f'- `{name_}`: {txt}')
        P('')
    P('**Tổng:** ' + ' · '.join(f'{d} {tot_dec[d]} file ({tot_b[d]/1048576:.2f} MiB)' for d in ('GIỮ', 'CẦN QUYẾT', 'XÓA?', 'XÓA', 'ĐÃ XÓA') if tot_dec[d]) +
      '. GIỮ ⇒ vào `retained` (cả dependency group); CẦN QUYẾT ⇒ hỏi user (Layer 2 case SlotGift, hoặc Layer 3 cho GUI bị `new` từ active); XÓA? ⇒ xác nhận atlas trùng tên. '
      'UI JSON tham chiếu frame theo tên node ⇒ xóa atlas cần art re-pack + đổi tham chiếu; JS ⇒ sửa tại chỗ hoặc Layer 2. Danh sách XÓA/ĐÃ XÓA đầy đủ trong `files_<bundle>.tsv`.')
    P('')
    with io.open(os.path.join(out_dir, f'files_{b}.tsv'), 'w', encoding='utf-8') as f:
        f.write('bundle\tgroup\tfiles\tbytes\tdecision\tframe\tconsumer\tnote\n')
        for k, g, d, lines, note in rows_out:
            for s_ in (flat_rows(lines) or ['']):
                f.write(f'{b}\t{glabel(g)}\t{";".join(g["files"])}\t{g["bytes"]}\t{d}\t{s_}\t{note}\n')

    # ---- verdict
    mode = 'partial-prune?' if (active_consumers or frame_active or l4c_active) else 'full-folder'
    P('## Verdict tự động — PHẢI review tay từng dòng'); P('')
    P(f'- Inventory: {len(inv)} file, {total:,} B · ASTC parity {"OK" if not parity_bad else "LỆCH"}')
    P(f'- Orphan candidate: {len(orphans)} → ' + ', '.join(f'`{os.path.basename(o)}`' for o in orphans))
    P(f'- File có consumer ACTIVE (G2): {len(active_consumers)} → ' + ', '.join(f'`{os.path.basename(p)}` ← {", ".join(v[:3])}' for p, v in active_consumers.items()))
    P(f'- Atlas frame dùng bởi ACTIVE (G3): {len(frame_active)} file')
    P(f'- res.<key> dùng ngoài retired (G4, gồm preload): {len(key_active)}')
    P(f'- cdn.json (G5): {len(cdn_hits)} · dynamic ACTIVE (G6): {sum(1 for q, _, _ in dyn if is_active(loc_kind(q)))}')
    P(f'- PoolFunction caller ACTIVE (G7): {len(pf_active)} (return-value: {sum(1 for x in pf_active if not x[3].startswith("fire"))})')
    P(f'- Layer 4c EXTENDS/new từ ACTIVE (G8): {len(l4c_active)} → ' + ', '.join(f'`{c}` @ `{q}:{i}` {k.split()[0]}' for c, q, i, k in l4c_active))
    P(f'- Layer 4b util construct được ACTIVE gọi (G9): {len([x for x in l4b_construct if any(is_active(loc_kind(q)) for q, _ in x[3])])} → ' +
      ', '.join(f'`{X}.{fn}`' for X, fn, _, locs in l4b_construct if any(is_active(loc_kind(q)) for q, _ in locs)))
    P(f'- Animation của bundle (G10b): xóa {len(anim_del)} ({sum(r["size"] for _, r, _ in anim_del)/1048576:.2f} MiB) · chờ bundle khác {len(anim_wait)} · giữ {len(anim_keep)}' + (' → ' + ', '.join(f'`{s}`' for s, _, _ in anim_del) if anim_del else ''))
    P(f'- **Mode gợi ý: {mode}**')
    P('')
    P('Guard-only? Nếu module có G7 caller ACTIVE kiểu RETURN-VALUE mà default hiện tại khác `undefined` (vd `checkIsCharge()` default true) ⇒ cân nhắc giữ register (`modulemgr_retire.py --guard-only`) + return guard trong module.')

    rp = os.path.join(out_dir, f'report_{b}.md')
    io.open(rp, 'w', encoding='utf-8').write('\n'.join(rep))
    keep_rows = [(k, g, d, lines, note) for k, g, d, lines, note in rows_out if d not in ('XÓA', 'ĐÃ XÓA')]
    if keep_rows:
        print(f'--- nhóm file KHÔNG xóa được ngay ({len(keep_rows)}/{len(rows_out)}) ---')
        for k, g, d, lines, note in keep_rows:
            print(f'  {d:10s} {glabel(g)} ({g["bytes"]:,} B)')
            for s_ in flat_rows(lines)[:12]:
                print(f'             {s_[:220]}')
    print(f'[{b}] {len(inv)} file {total:,} B · orphan={len(orphans)} · G2 active={len(active_consumers)} · G3 frame active={len(frame_active)} · '
          f'G4 key ext={len(key_active)} · G5 cdn={len(cdn_hits)} · G7 pf active={len(pf_active)} · G8 4c={len(l4c_active)} · '
          f'G9 4b construct={len(l4b_construct)} · G10b anim del={len(anim_del)}/wait={len(anim_wait)}/keep={len(anim_keep)} · mode={mode}')
    print(f'report: {norm(os.path.normpath(rp))}')


if __name__ == '__main__':
    main()
