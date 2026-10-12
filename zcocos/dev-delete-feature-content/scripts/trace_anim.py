# -*- coding: utf-8 -*-
"""trace_anim.py — trace consumer cho animation (res/animation) theo dependency group, gate AG1–AG8.

CLI (toàn repo):
  python trace_anim.py [--repo-root <path>] [--out <dir>] [--only <stem>]... [--extra-retired-dir <dir>]...
API (trace_bundle.py gọi để quyết định animation theo bundle):
  ctx = analyze(root, src=<dict path->[(i, text, live)]>, extra_retired=[...])   → ctx['rows'][stem] = {...}

Group:
  DragonBones  = config/<k>.xml + texture/<k>.plist + texture/<k>.png + res#tcf_astc/animation/texture/<k>.png
  Spine        = atlas/<k>.json + atlas/<alias|k>.atlas + png ghi TRONG file .atlas (+ astc) — png có thể dùng chung
Registry: AniSource (DB), AniSpineSource / AniSpineAtlasSource (Spine) trong src/base/animation/AnimationMgr.js.

Gate:
  AG1 group + parity + png dùng chung      AG2 static: AniSource.<k> / AniSpineSource.<k> / "<k>" ở dòng sống
      — kể cả bên trong AnimationMgr (ngoài block registry): usage trong wrapper `AnimationMgr.<fn> = function` được
        truy ngược ≤3 hop sang caller `AnimationMgr.<fn>(` để lấy kind thật
  AG3 dynamic family: strip hậu tố số → prefix trong src (quoted/identifier) hoặc concat `"<prefix>" +`; `AniSource[` / `in AniSource`
  AG4 config: stem/prefix trong res/config/**/*.json      AG5 override: AniPathFolder*/AniSpineAtlasSource set ở code sống
  AG6 preload: caller sống của preloadAllAnimation      AG7 CDN: stem trong build/**/cdn.json
  AG8 retired-consumer: kind của caller — dir module Guard-Only tính là ACTIVE
Kind: ACTIVE · retired:<bundle> · GUARD-ONLY(active) · ACTIVE(AnimationMgr top-level). Chỉ đọc. Stdlib only.
"""
import io, os, re, sys, glob, argparse, collections
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

norm = lambda p: p.replace('\\', '/')
SKIP_FN = ('extend', 'prototype', 'call', 'apply', 'bind')


def in_dirs(p, dirs):
    p = norm(p)
    return any(p == d or p.startswith(d + '/') for d in dirs)


def live_lines(txt):
    out, inblock = [], False
    for i, t in enumerate(txt.split('\n'), 1):
        s = t.strip(); live = True
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
        out.append((i, t, live))
    return out


def load_src(root):
    src = {}
    for p in glob.glob(os.path.join(root, 'src', '**', '*.js'), recursive=True):
        src[norm(os.path.relpath(p, root))] = live_lines(io.open(p, encoding='utf-8', errors='replace').read())
    return src


def is_active(kind):
    return kind.startswith('ACTIVE') or kind.startswith('GUARD-ONLY')


def parse_retired(src):
    """ModuleMgr → {dir: bundle} retired, gdirs (guard-only live), deleted_dirs (ctor đã comment = Layer 1 xong).
    KHÔNG phụ thuộc tag //D: retired = ctor đã comment (bất kỳ lý do) hoặc có tag //D; module sống không tag = ACTIVE."""
    class_file = {}
    for q, lines in src.items():
        for i, t, live in lines:
            m = re.match(r'^\s*(?:var\s+)?([A-Z]\w*)\s*=\s*[\w.]+\.extend\s*\(', t)
            if m:
                class_file.setdefault(m.group(1), q)
    retired, gdirs, deleted = {}, set(), set()
    for i, t, live in src.get('src/gamemgr/ModuleMgr.js', []):
        m = re.match(r'^\s*(//)?\s*var\s+(\w+)\s*=\s*new\s+(\w+)\s*\(', t)
        if not m:
            continue
        tags = re.findall(r'//\s*([A-Za-z][\w-]*)', t)
        ctor_live = bool(live and not m.group(1))
        is_d = 'D' in tags
        guard = 'guard-only' in tags and ctor_live
        if ctor_live and not is_d and not guard:
            continue                                  # module sống, không tag ⇒ ACTIVE
        bundle = next((x for x in tags if x not in ('D', 'var', 'deleted', 'content', 'guard-only', 'remove') and not x.startswith('build')), m.group(3))
        d = os.path.dirname(class_file[m.group(3)]) if m.group(3) in class_file else None
        if not d:
            continue
        retired[d] = bundle
        if guard:
            gdirs.add(d)
        if not ctor_live:
            deleted.add(d)
    return retired, gdirs, deleted


def analyze(root, src=None, extra_retired=(), astc='res#tcf_astc'):
    root = os.path.abspath(root)
    cwd = os.getcwd(); os.chdir(root)
    try:
        return _analyze(root, src, extra_retired, astc)
    finally:
        os.chdir(cwd)


def _analyze(root, src, extra_retired, astc):
    AN, ASTC = 'res/animation', f'{astc}/animation'
    if src is None:
        src = load_src(root)
    mgr = next((q for q in src if q.endswith('/animation/AnimationMgr.js')), None)
    if not mgr:
        raise SystemExit('không thấy AnimationMgr.js')
    retired, gdirs, deleted = parse_retired(src)
    for d in extra_retired:                      # "dir" hoặc "dir=bundle" (trace_bundle truyền module dir của bundle đang xóa)
        dd, _, bb = d.partition('=')
        retired[norm(dd)] = bb or retired.get(norm(dd), 'extra')
    rdirs = sorted(retired)

    def kind(q):
        if in_dirs(q, gdirs):
            return 'GUARD-ONLY(active)'
        for d in rdirs:
            if q == d or q.startswith(d + '/'):
                return 'retired:' + retired[d]
        return 'ACTIVE'

    # registries
    mgr_lines = src[mgr]
    reg = {'AniSource': {}, 'AniSpineSource': {}, 'AniSpineAtlasSource': {}}
    reg_ranges = []
    for name in reg:
        st = next((i for i, t, _ in mgr_lines if re.match(r'^\s*var\s+' + name + r'\s*=\s*\{', t)), None)
        if st is None:
            continue
        en = next((i for i, t, _ in mgr_lines if i > st and re.match(r'^\s*\};', t)), st)
        reg_ranges.append((st, en))
        for i, t, live in mgr_lines[st - 1:en]:
            m = re.match(r'^\s*(\w+)\s*:\s*"([^"]+)"', t)
            if m:
                reg[name][m.group(1)] = m.group(2)
    in_reg = lambda i: any(s <= i <= e for s, e in reg_ranges)

    # AG1 groups
    groups = collections.OrderedDict()
    for c in sorted(norm(x) for x in glob.glob(f'{AN}/config/*.xml')):
        k = os.path.splitext(os.path.basename(c))[0]
        want = [f'{AN}/config/{k}.xml', f'{AN}/texture/{k}.plist', f'{AN}/texture/{k}.png', f'{ASTC}/texture/{k}.png']
        groups[k] = {'type': 'DB', 'files': [f for f in want if os.path.exists(f)], 'missing': [f for f in want[:3] if not os.path.exists(f)], 'png': f'{k}.png'}
    png_users = collections.defaultdict(set)
    for j in sorted(norm(x) for x in glob.glob(f'{AN}/atlas/*.json')):
        k = os.path.splitext(os.path.basename(j))[0]
        atlas = f'{AN}/atlas/{reg["AniSpineAtlasSource"].get(k, k)}.atlas'
        pngs = []
        if os.path.exists(atlas):
            pngs = [ln.strip() for ln in io.open(atlas, encoding='utf-8', errors='replace').read().split('\n') if ln.strip().lower().endswith('.png')]
        files = [j] + ([atlas] if os.path.exists(atlas) else [])
        for pn in pngs:
            files += [f for f in (f'{AN}/atlas/{pn}', f'{ASTC}/atlas/{pn}') if os.path.exists(f)]
            png_users[pn].add(k)
        groups[k] = {'type': 'Spine', 'files': files, 'missing': [] if os.path.exists(atlas) else [atlas], 'png': ','.join(pngs)}
    grouped = {f for g in groups.values() for f in g['files']}
    loose = [norm(f) for d in ('config', 'texture', 'atlas') for f in glob.glob(f'{AN}/{d}/*') if norm(f) not in grouped]
    size = {k: sum(os.path.getsize(f) for f in g['files']) for k, g in groups.items()}
    stems = set(groups)

    # AG2 single pass
    wrappers, cur = {}, None
    for i, t, live in mgr_lines:
        m = re.match(r'^AnimationMgr\.(\w+)\s*=\s*function', t)
        if m:
            if cur:
                wrappers[cur][1] = i - 1
            cur = m.group(1); wrappers[cur] = [i, len(mgr_lines)]
    wrapper_of = lambda i: next((fn for fn, (s, e) in wrappers.items() if s <= i <= e), None)
    direct = collections.defaultdict(set)        # stem -> {(kind, loc)}
    via_wrapper = collections.defaultdict(set)   # stem -> {fn}
    concat_prefixes, global_dyn = set(), []
    str_rx = re.compile(r'["\']([A-Za-z_][\w]*)["\']')
    key_rx = re.compile(r'\b(AniSource|AniSpineSource)\.(\w+)')
    concat_rx = re.compile(r'["\']([A-Za-z_][\w]{4,})["\']\s*\+')
    for q, ls in src.items():
        for i, t, live in ls:
            if not live or (q == mgr and in_reg(i)):
                continue
            found = set()
            for m in key_rx.finditer(t):
                v = reg[m.group(1)].get(m.group(2))
                if v in stems:
                    found.add(v)
                elif m.group(2) in stems:
                    found.add(m.group(2))
            for m in str_rx.finditer(t):
                if m.group(1) in stems:
                    found.add(m.group(1))
            for m in concat_rx.finditer(t):
                concat_prefixes.add((m.group(1), f'{q}:{i}'))
            if re.search(r'AniSource\[|AniSpineSource\[|in AniSpineSource|in AniSource', t):
                global_dyn.append(f'{q}:{i} `{t.strip()[:90]}`')
            for s in found:
                if q == mgr:
                    fn = wrapper_of(i)
                    if fn:
                        via_wrapper[s].add(fn)
                    else:
                        direct[s].add(('ACTIVE(AnimationMgr top-level)', f'{q}:{i}'))
                else:
                    direct[s].add((kind(q), f'{q}:{i}'))
    caller_cache = {}

    def callers(fn, depth=0):
        if fn in caller_cache:
            return caller_cache[fn]
        res = set()
        rx = re.compile(r'\bAnimationMgr\.' + re.escape(fn) + r'\s*\(')
        for q, ls in src.items():
            for i, t, live in ls:
                if not live or not rx.search(t):
                    continue
                if q == mgr:
                    w = wrapper_of(i)
                    if w and w != fn and depth < 3:
                        res |= {(k2, f'{loc} ← {w}') for k2, loc in callers(w, depth + 1)}
                else:
                    res.add((kind(q), f'{q}:{i}'))
        caller_cache[fn] = res
        return res
    wrapper_callers = {s: {fn: callers(fn) for fn in fns} for s, fns in via_wrapper.items()}

    # AG3 / AG4 / AG5 / AG7
    cfg_txt = '\n'.join(io.open(p, encoding='utf-8', errors='replace').read() for p in glob.glob('res/config/**/*.json', recursive=True))
    cdn_txt = '\n'.join(io.open(p, encoding='utf-8', errors='replace').read() for p in glob.glob('build/**/cdn.json', recursive=True))
    all_live = '\n'.join(t for q, ls in src.items() for i, t, live in ls if live and not (q == mgr and in_reg(i)))
    fam_of = {}
    for s in stems:
        m = re.match(r'^(.*?)[_]?[0-9]+$', s)
        fam_of[s] = m.group(1) if m and len(m.group(1)) >= 4 else None
    fam_members = collections.defaultdict(list)
    for s, f in fam_of.items():
        if f:
            fam_members[f].append(s)
    fam_hit = {}
    for f in fam_members:
        # bằng chứng ĐỘNG = prefix đi với `+` hoặc `_"` (ghép chuỗi). Nếu prefix cũng là 1 stem (eff7DayGift ↔ eff7DayGift2)
        # thì usage literal `AniSource.eff7DayGift` / `"eff7DayGift"` chỉ là usage của chính stem đó — không phải họ động.
        alts = [r'["\']' + re.escape(f) + r'_["\']', r'["\']' + re.escape(f) + r'["\']\s*\+', r'\+\s*["\']' + re.escape(f)]
        if f not in stems:
            alts += [r'["\']' + re.escape(f) + r'["\']', r'AniSource\.' + re.escape(f) + r'\b', r'AniSpineSource\.' + re.escape(f) + r'\b']
        m = re.compile('|'.join(alts)).search(all_live)
        cfg_rx = r'["\']' + re.escape(f) + (r'[_\d]+["\']' if f in stems else r'[_\d]*["\']')
        fam_hit[f] = ('src', m.group(0)) if m else (('config', f) if re.search(cfg_rx, cfg_txt) else None)
    flags = collections.defaultdict(set)
    for s in stems:
        f = fam_of.get(s)
        if f and fam_hit.get(f):
            flags[s].add(f'họ `{f}*` ({len(fam_members[f])}) hit {fam_hit[f][0]}: `{fam_hit[f][1][:40]}`')
        for pre, loc in concat_prefixes:
            if s.startswith(pre) and pre != s and pre not in stems:
                flags[s].add(f'concat `"{pre}" +` @ {loc}')
        if re.search(r'["\']' + re.escape(s) + r'["\']', cfg_txt):
            flags[s].add('AG4 tên trong res/config')
        if re.search(r'AniPathFolder\[\s*["\']' + re.escape(s) + r'|AniPathDBConfig\[\s*["\']' + re.escape(s) + r'|AniSpineAtlasSource\[\s*["\']' + re.escape(s), all_live):
            flags[s].add('AG5 override path/alias ở code sống')
        if s in cdn_txt:
            flags[s].add('AG7 trong cdn.json (CDN — ngoài scope APK)')
    preload_callers = [f'{q}:{i}' for q, ls in src.items() for i, t, live in ls if live and 'preloadAllAnimation' in t and q != mgr]
    preload_callers += [f'{mgr}:{i}' for i, t, live in mgr_lines if live and re.search(r'\bpreloadAllAnimation\s*\(', t) and not re.match(r'^AnimationMgr\.preloadAllAnimation\s*=', t)]

    rows = {}
    for s, g in groups.items():
        wk = {(k, loc) for fn, cs in wrapper_callers.get(s, {}).items() for k, loc in cs}
        usage = set(direct.get(s, set())) | wk
        kinds = {k for k, _ in usage}
        no_caller = any(not cs for cs in wrapper_callers.get(s, {}).values())
        if flags.get(s):
            cls = 'KEEP-dynamic/config'
        elif any(is_active(k) for k in kinds):
            cls = 'ACTIVE'
        elif kinds:
            cls = 'retired-only'
        else:
            cls = 'ORPHAN' + (' (wrapper không caller)' if no_caller else '')
        shared = sorted(u for pn in g['png'].split(',') if pn for u in png_users.get(pn, set()) if u != s) if g['type'] == 'Spine' else []
        rows[s] = {'stem': s, 'type': g['type'], 'files': g['files'], 'missing': g['missing'], 'size': size[s], 'cls': cls,
                   'kinds': kinds, 'usage': usage, 'direct': direct.get(s, set()), 'wrapper_callers': wrapper_callers.get(s, {}),
                   'flags': flags.get(s, set()), 'shared': shared, 'registered': s in set(reg['AniSource'].values()) | set(reg['AniSpineSource'].values())}
    return {'root': root, 'mgr': mgr, 'retired': retired, 'gdirs': gdirs, 'deleted': deleted, 'reg': reg, 'groups': groups, 'rows': rows,
            'loose': loose, 'png_users': png_users, 'preload_callers': preload_callers, 'global_dyn': global_dyn, 'is_active': is_active}


def write_report(ctx, out_dir, only=()):
    os.makedirs(out_dir, exist_ok=True)
    rows = ctx['rows']; groups = ctx['groups']
    R = []; P = R.append
    P('# trace animation — `res/animation`'); P('')
    P(f'repo `{ctx["root"]}` · retired dirs: {len(ctx["retired"])} (guard-only tính ACTIVE: {len(ctx["gdirs"])}) · registry AniSource {len(ctx["reg"]["AniSource"])} / AniSpineSource {len(ctx["reg"]["AniSpineSource"])} / alias {len(ctx["reg"]["AniSpineAtlasSource"])}'); P('')
    P(f'## AG1 — Group: {sum(1 for g in groups.values() if g["type"] == "DB")} DragonBones + {sum(1 for g in groups.values() if g["type"] == "Spine")} Spine · {sum(r["size"] for r in rows.values())/1048576:.2f} MiB · file lẻ không thuộc group: {len(ctx["loose"])}')
    for f in ctx['loose'][:10]:
        P(f'- lẻ: `{f}`')
    miss = [(s, g['missing']) for s, g in groups.items() if g['missing']]
    P(f'- group thiếu thành phần: {len(miss)}' + (' → ' + ', '.join(f'`{s}`' for s, _ in miss[:10]) if miss else ''))
    shared_png = {pn: us for pn, us in ctx['png_users'].items() if len(us) > 1}
    P(f'- png Spine dùng chung: {len(shared_png)}' + (' → ' + ', '.join(f'`{pn}` ← {", ".join(sorted(us))}' for pn, us in shared_png.items()) if shared_png else '')); P('')
    P(f'## AG6 — preloadAllAnimation caller sống: {len(ctx["preload_callers"])} ' + (', '.join(ctx['preload_callers']) if ctx['preload_callers'] else '(0 — key registry treo vô hại)'))
    P(f'## AG3 — dynamic global: {len(ctx["global_dyn"])}'); [P(f'- {x}') for x in ctx['global_dyn'][:12]]; P('')
    P('## Phân loại từng group'); P('')
    P('| stem | type | MiB | class | usage (kind) | qua wrapper AnimationMgr → caller | cờ dynamic/config | png dùng chung |'); P('|---|---|---:|---|---|---|---|---|')
    order = {'retired-only': 0, 'ORPHAN': 1, 'ORPHAN (wrapper không caller)': 2, 'KEEP-dynamic/config': 3, 'ACTIVE': 4}
    tot = collections.Counter(); totb = collections.Counter()
    for r in sorted(rows.values(), key=lambda r: (order.get(r['cls'], 9), -r['size'])):
        if only and r['stem'] not in only:
            continue
        base = r['cls'].split(' ')[0]; tot[base] += 1; totb[base] += r['size']
        u = '; '.join(f'{k} `{loc}`' for k, loc in sorted(r['direct'])[:3]) or '—'
        w = '; '.join(f'`{fn}` ← ' + (', '.join(f'{k} `{loc}`' for k, loc in sorted(cs)[:2]) if cs else '**0 caller**') for fn, cs in r['wrapper_callers'].items()) or '—'
        P(f'| `{r["stem"]}` | {r["type"]} | {r["size"]/1048576:.2f} | **{r["cls"]}** | {u} | {w} | {"; ".join(sorted(r["flags"])) or "—"} | {", ".join(r["shared"]) or "—"} |')
    P(''); P('## Tổng'); P(''); P('| class | group | MiB |'); P('|---|---:|---:|')
    for c in ('retired-only', 'ORPHAN', 'KEEP-dynamic/config', 'ACTIVE'):
        P(f'| {c} | {tot[c]} | {totb[c]/1048576:.2f} |')
    P(''); P('retired-only ⇒ ứng viên xóa (kiểm AG8: caller trong dir module đã Layer 1, không Guard-Only). ORPHAN ⇒ soát tay từng stem (T1/T2). KEEP ⇒ không xóa.')
    rp = os.path.join(out_dir, 'report_animation.md')
    io.open(rp, 'w', encoding='utf-8').write('\n'.join(R))
    with io.open(os.path.join(out_dir, 'inventory_animation.tsv'), 'w', encoding='utf-8') as f:
        f.write('stem\ttype\tbytes\tclass\tkinds\tflags\tfiles\n')
        for r in rows.values():
            f.write(f'{r["stem"]}\t{r["type"]}\t{r["size"]}\t{r["cls"]}\t{",".join(sorted(r["kinds"]))}\t{" | ".join(sorted(r["flags"]))}\t{";".join(r["files"])}\n')
    return rp, tot, totb


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--repo-root', default=os.getcwd())
    ap.add_argument('--out', default=None, help='default <repo>/docs/modules/deletefeaturecontent/phase2-animation/trace')
    ap.add_argument('--only', action='append', default=[])
    ap.add_argument('--extra-retired-dir', action='append', default=[])
    ap.add_argument('--astc', default='res#tcf_astc')
    a = ap.parse_args()
    root = os.path.abspath(a.repo_root)
    if not os.path.exists(os.path.join(root, 'project.json')):
        raise SystemExit(f'--repo-root không có project.json: {root}')
    ctx = analyze(root, extra_retired=a.extra_retired_dir, astc=a.astc)
    out_dir = a.out or os.path.join(root, 'docs', 'modules', 'deletefeaturecontent', 'phase2-animation', 'trace')
    rp, tot, totb = write_report(ctx, out_dir, a.only)
    print(' · '.join(f'{c}: {tot[c]} ({totb[c]/1048576:.2f} MiB)' for c in ('retired-only', 'ORPHAN', 'KEEP-dynamic/config', 'ACTIVE')))
    print(f'report: {norm(os.path.normpath(rp))}')


if __name__ == '__main__':
    main()
