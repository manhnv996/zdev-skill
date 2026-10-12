# -*- coding: utf-8 -*-
"""gen_anim_manifest.py — sinh manifests/<bundle>.json (status=planned) cho batch animation từ inventory của trace_anim.py.

  python gen_anim_manifest.py --bundle anim-retired --build build180 --branch <branch>
        (--stem <k>... | --class retired-only | --from-file <txt 1 stem/dòng>)
        [--repo-root <path>] [--inventory <tsv>] [--manifest-dir <path>] [--backup-root <path>]

- removed = mọi file của group (DragonBones: xml+plist+png+astc; Spine: json+atlas+png-theo-.atlas+astc) của các stem chọn.
- png Spine dùng chung: chỉ removed khi MỌI stem dùng png đó đều nằm trong batch; ngược lại png (+astc) → retained và ghi cảnh báo.
- Refuse: stem không có trong inventory; group thiếu thành phần (missing) trừ khi --allow-missing; manifest status ≠ planned.
- bytes/sha256 để tool Audit điền. removalMode = partial-prune nếu có retained (png dùng chung), else full-folder.
"""
import io, os, sys, json, argparse, collections
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
norm = lambda p: p.replace('\\', '/')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--bundle', required=True)
    ap.add_argument('--build', required=True)
    ap.add_argument('--branch', required=True)
    ap.add_argument('--stem', action='append', default=[])
    ap.add_argument('--class', dest='cls', default=None, help='lấy mọi stem có class này trong inventory (vd retired-only)')
    ap.add_argument('--from-file', default=None)
    ap.add_argument('--repo-root', default=os.getcwd())
    ap.add_argument('--inventory', default=None, help='default <repo>/docs/modules/deletefeaturecontent/phase2-animation/trace/inventory_animation.tsv')
    ap.add_argument('--manifest-dir', default=None, help='default <repo>/docs/modules/deletefeaturecontent/phase2-animation/manifests')
    ap.add_argument('--backup-root', default=r'D:\workspace\BidaMobile\client-delete-content-backup')
    ap.add_argument('--allow-missing', action='store_true')
    ap.add_argument('--patch', default='', help='relative path quarantine.patch trong backup (default rỗng = batch không sửa code; tool refuse nếu khai báo mà thiếu file)')
    a = ap.parse_args()
    root = os.path.abspath(a.repo_root)
    if not os.path.exists(os.path.join(root, 'project.json')):
        raise SystemExit(f'--repo-root không có project.json: {root}')
    os.chdir(root)
    base = os.path.join(root, 'docs', 'modules', 'deletefeaturecontent', 'phase2-animation')
    inv_path = a.inventory or next((p for p in (os.path.join(base, 'trace', 'inventory_animation.tsv'),
                                                  os.path.join(root, 'docs', 'modules', 'deletefeaturecontent', 'trace', 'inventory_animation.tsv'))
                                    if os.path.exists(p)), os.path.join(base, 'trace', 'inventory_animation.tsv'))
    if not os.path.exists(inv_path):
        raise SystemExit(f'không thấy inventory {inv_path} — chạy trace_bundle.py (G10b) hoặc trace_anim.py trước, hoặc truyền --inventory')
    mdir = a.manifest_dir or os.path.join(base, 'manifests')
    os.makedirs(mdir, exist_ok=True)

    inv = {}
    with io.open(inv_path, encoding='utf-8') as f:
        hdr = f.readline().rstrip('\n').split('\t')
        for line in f:
            r = dict(zip(hdr, line.rstrip('\n').split('\t')))
            inv[r['stem']] = r
    stems = list(a.stem)
    if a.cls:
        stems += [s for s, r in inv.items() if r['class'].split(' ')[0] == a.cls]
    if a.from_file:
        stems += [l.strip() for l in io.open(a.from_file, encoding='utf-8') if l.strip() and not l.startswith('#')]
    stems = sorted(set(stems))
    if not stems:
        raise SystemExit('không có stem nào (dùng --stem/--class/--from-file)')
    bad = [s for s in stems if s not in inv]
    if bad:
        raise SystemExit(f'stem không có trong inventory: {bad}')

    mp = os.path.join(mdir, f'{a.bundle}.json')
    if os.path.exists(mp):
        st = json.load(io.open(mp, encoding='utf-8')).get('status', 'planned')
        if st != 'planned':
            raise SystemExit(f'{a.bundle}: manifest status={st} — không ghi đè')

    # png Spine dùng chung: đếm user theo tên png trong toàn inventory
    png_users = collections.defaultdict(set)
    for s, r in inv.items():
        if r['type'] == 'Spine':
            for f in r['files'].split(';'):
                if f.lower().endswith('.png') and '/atlas/' in f and not f.startswith('res#'):
                    png_users[os.path.basename(f)].add(s)
    removed, retained, warn = [], [], []
    for s in stems:
        r = inv[s]
        files = [x for x in r['files'].split(';') if x]
        missing = [x for x in files if not os.path.exists(x)]
        if missing and not a.allow_missing:
            raise SystemExit(f'{s}: file trong inventory không tồn tại (inventory cũ?): {missing}')
        for f in files:
            if r['type'] == 'Spine' and f.lower().endswith('.png'):
                users = png_users.get(os.path.basename(f), set())
                if users - set(stems):
                    retained.append(f); warn.append(f'{s}: png `{os.path.basename(f)}` dùng chung với {sorted(users - set(stems))} → retained')
                    continue
            removed.append(f)
    removed = sorted(set(removed)); retained = sorted(set(retained) - set(removed))
    m = {
        'bundle': a.bundle, 'build': a.build, 'branch': a.branch,
        'removalMode': 'group', 'status': 'planned', 'generatedAt': '',   # group: folder dùng chung phải còn; retained (png chung) cho phép
        'backupRoot': a.backup_root, 'quarantinePatch': a.patch,
        'unresolved': [], 'removed': [{'path': p, 'bytes': 0, 'sha256': ''} for p in removed],
        'retained': [{'path': p, 'bytes': 0, 'sha256': ''} for p in retained], 'totals': {'files': 0, 'bytes': 0},
        'animationStems': stems,
    }
    io.open(mp, 'w', encoding='utf-8').write(json.dumps(m, indent=2, ensure_ascii=False) + '\n')
    rb = sum(os.path.getsize(p) for p in removed if os.path.exists(p))
    print(f'{a.bundle}: {len(stems)} stem · removed {len(removed)} file ({rb:,} B = {rb/1048576:.2f} MiB) · retained {len(retained)} → {norm(mp)}')
    for w in warn:
        print('  ⚠', w)
    print(f'tiếp: quarantine.patch rỗng (không sửa code) → delete_feature_content.ps1 -Action Audit -Bundle {a.bundle} -ManifestDir "{norm(mdir)}" -DryRun')


if __name__ == '__main__':
    main()
