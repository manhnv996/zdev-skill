# -*- coding: utf-8 -*-
"""Xóa reference của 1 content folder khỏi mọi build/**/cdn.json — sửa theo DÒNG để diff tối thiểu, không re-dump JSON.

  cdn_prune.py --folder baucua --group minigameCrabDice [--build-dir build] [--dry-run]

- ignore_in_listing: bỏ mọi dòng chứa "res/content/<folder>/"
- groups[]: bỏ object 4 dòng  {  "name": "<group>",  "path": ...  },  ; nếu là phần tử cuối thì bỏ dấu phẩy ở object trước
- Verify: json.loads(before) - entries == json.loads(after); giữ line ending gốc.
"""
import io, os, re, sys, json, glob, argparse
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

def prune_lines(lines, folder, group):
    out = list(lines)
    removed_ignore = [l for l in out if f'res/content/{folder}/' in l and l.strip().startswith('"')]
    out = [l for l in out if l not in removed_ignore]
    removed_group = 0
    if group:
        i = next((k for k, l in enumerate(out) if re.match(r'\s*"name"\s*:\s*"' + re.escape(group) + r'"\s*,?\s*$', l)), -1)
        if i >= 0:
            start = i
            while start > 0 and out[start].strip() != '{': start -= 1
            end = i
            while end < len(out) and not out[end].strip().startswith('}'): end += 1
            if out[start].strip() != '{' or end >= len(out): raise SystemExit(f'không tách được object group {group}')
            last_elem = not out[end].strip().endswith(',')
            del out[start:end + 1]
            if last_elem:
                # object trước đó giờ là phần tử cuối → bỏ dấu phẩy
                k = start - 1
                while k >= 0 and out[k].strip() == '': k -= 1
                if out[k].rstrip().endswith('},'): out[k] = out[k].rstrip()[:-1]
            removed_group = 1
    # dòng cuối cùng còn lại của 1 array/object không được có dấu phẩy treo (JSON hợp lệ không bao giờ có "," trước ] hoặc })
    for i in range(len(out)):
        if out[i].rstrip().endswith(','):
            j = i + 1
            while j < len(out) and out[j].strip() == '': j += 1
            if j < len(out) and out[j].strip()[:1] in (']', '}'):
                out[i] = out[i].rstrip()[:-1]
    return out, len(removed_ignore), removed_group

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--folder', required=True)
    ap.add_argument('--group', default='')
    ap.add_argument('--build-dir', default='build')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.build_dir, '**', 'cdn.json'), recursive=True))
    touched = 0
    for p in files:
        raw = io.open(p, encoding='utf-8', newline='').read()
        if f'res/content/{a.folder}/' not in raw and (not a.group or f'"{a.group}"' not in raw): continue
        nl = '\r\n' if '\r\n' in raw else '\n'
        lines = raw.split(nl)
        before = json.loads(raw)
        out, n_ign, n_grp = prune_lines(lines, a.folder, a.group)
        after_txt = nl.join(out)
        after = json.loads(after_txt)      # phải parse được
        # verify semantics
        exp_ign = [s for s in before.get('ignore_in_listing', []) if f'res/content/{a.folder}/' not in s]
        exp_grp = [g for g in before.get('groups', []) if g.get('name') != a.group]
        assert after.get('ignore_in_listing', []) == exp_ign, f'{p}: ignore_in_listing lệch'
        assert after.get('groups', []) == exp_grp, f'{p}: groups lệch'
        for k in before:
            if k not in ('ignore_in_listing', 'groups'): assert before[k] == after[k], f'{p}: key {k} bị đổi'
        print(f'{p}: -{n_ign} ignore, -{n_grp} group' + ('  (dry-run)' if a.dry_run else ''))
        if not a.dry_run:
            io.open(p, 'w', encoding='utf-8', newline='').write(after_txt)
        touched += 1
    print(f'files touched: {touched}')

if __name__ == '__main__':
    main()
