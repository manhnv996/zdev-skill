# -*- coding: utf-8 -*-
"""gen_manifest.py — sinh manifests/<bundle>.json (status=planned) từ inventory THẬT trên disk + retained list đã chốt.

  python gen_manifest.py --bundle <b> --build build180 --branch <branch>
        [--retained <path>]... [--repo-root <path>] [--manifest-dir <path>] [--backup-root <path>] [--astc res#tcf_astc]

- removed = mọi file trong res/content/<b> + <astc>/content/<b> trừ retained.
- retained phải tồn tại; mode = partial-prune nếu retained ≠ rỗng.
- Refuse ghi đè manifest có status ≠ planned (đã audited/moved/verified).
- bytes/sha256 để 0/"" — Audit của tool điền, không viết tay.
"""
import io, os, re, sys, json, argparse
for _s in (sys.stdout, sys.stderr):          # console Windows (cp1252) không in được → · — exit 1 giả sau khi đã ghi manifest
    try:
        _s.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


def norm(p):
    return p.replace('\\', '/')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--bundle', required=True)
    ap.add_argument('--build', required=True, help='layer folder trong backup, vd build180')
    ap.add_argument('--branch', required=True)
    ap.add_argument('--retained', action='append', default=[], help='path relative repo (forward slash), lặp nhiều lần')
    ap.add_argument('--repo-root', default=os.getcwd())
    ap.add_argument('--manifest-dir', default=None, help='default <repo>/docs/modules/deletefeaturecontent/manifests')
    ap.add_argument('--backup-root', default=r'D:\workspace\BidaMobile\client-delete-content-backup')
    ap.add_argument('--astc', default='res#tcf_astc')
    a = ap.parse_args()

    root = os.path.abspath(a.repo_root)
    if not os.path.exists(os.path.join(root, 'project.json')):
        raise SystemExit(f'--repo-root không có project.json: {root}')
    if '/' in a.build or '\\' in a.build or not a.build.strip():
        raise SystemExit('--build không hợp lệ')
    os.chdir(root)
    b = a.bundle
    mdir = a.manifest_dir or os.path.join(root, 'docs', 'modules', 'deletefeaturecontent', 'manifests')
    os.makedirs(mdir, exist_ok=True)
    mp = os.path.join(mdir, f'{b}.json')
    if os.path.exists(mp):
        st = json.load(io.open(mp, encoding='utf-8')).get('status', 'planned')
        if st != 'planned':
            raise SystemExit(f'{b}: manifest status={st} — không ghi đè. Restore/reset trước nếu thật sự muốn sinh lại.')

    inv = []
    for base in (f'res/content/{b}', f'{a.astc}/content/{b}'):
        for r_, _, files in os.walk(base):
            for f in files:
                p = norm(os.path.join(r_, f)); inv.append((p, os.path.getsize(p)))
    inv.sort()
    if not inv:
        raise SystemExit(f'không có file nào trong res/content/{b}')
    keep = {norm(p) for p in a.retained}
    missing = keep - {p for p, _ in inv}
    if missing:
        raise SystemExit(f'retained không tồn tại trong inventory: {sorted(missing)}')
    # dependency group: plist ↔ texture cùng tên phải cùng phía
    names = {p for p, _ in inv}
    for p in list(keep):
        stem, ext = os.path.splitext(p)
        if ext == '.plist' and stem + '.png' in names and stem + '.png' not in keep:
            raise SystemExit(f'retained {p} nhưng texture {stem}.png không retained (dependency group)')
        if p.startswith('res/') and ext.lower() in ('.png', '.jpg', '.jpeg'):
            c = a.astc + p[len('res'):]
            if c in names and c not in keep:
                raise SystemExit(f'retained {p} nhưng ASTC {c} không retained (parity)')

    # JSON retained trong bundle là consumer của atlas/ảnh cùng folder: field "Plist"/"Path" → basename phải không nằm trong removed
    # (ca thật: guiThankfulMonth.json retained dùng FirstChargeContent.plist → atlas không xóa được)
    removed_base = {os.path.basename(p) for p, _ in inv if p not in keep}
    for p in keep:
        if p.endswith('.json') and p.startswith('res/'):
            txt = io.open(p, encoding='utf-8', errors='replace').read()
            refs = {os.path.basename(x) for x in re.findall(r'"(?:Plist|Path)"\s*:\s*"([^"]+)"', txt)}
            bad = sorted(r for r in refs if r in removed_base)
            if bad:
                raise SystemExit(f'retained {p} tham chiếu file bị removed cùng bundle: {bad} — retain thêm dependency group đó hoặc bỏ JSON khỏi retained')
    removed = [{'path': p, 'bytes': 0, 'sha256': ''} for p, _ in inv if p not in keep]
    retained = [{'path': p, 'bytes': 0, 'sha256': ''} for p, _ in inv if p in keep]
    m = {
        'bundle': b, 'build': a.build, 'branch': a.branch,
        'removalMode': 'partial-prune' if retained else 'full-folder', 'status': 'planned', 'generatedAt': '',
        'backupRoot': a.backup_root, 'quarantinePatch': f'_meta/{b}/quarantine.patch',
        'unresolved': [], 'removed': removed, 'retained': retained, 'totals': {'files': 0, 'bytes': 0},
    }
    io.open(mp, 'w', encoding='utf-8').write(json.dumps(m, indent=2, ensure_ascii=False) + '\n')
    rm_b = sum(s for p, s in inv if p not in keep); kp_b = sum(s for p, s in inv if p in keep)
    print(f'{b}: {m["removalMode"]} · removed {len(removed)} ({rm_b:,} B) · retained {len(retained)} ({kp_b:,} B) → {mp}')
    print('tiếp: delete_feature_content.ps1 -Action Audit -Bundle ' + b + ' -DryRun')


if __name__ == '__main__':
    main()
