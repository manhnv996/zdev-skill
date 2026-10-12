# -*- coding: utf-8 -*-
"""ModuleMgr.js region helper cho task delete feature content.

  --init-regions                 tạo 2 region trong ctor + region "Deleted Content" trong init/reset/resetReloadConfig,
                                 và dời các dòng đã comment có marker `//deleted content` vào region
  --retire <var> <bundle>        Layer 1: comment ctor + init + reset (mọi lần xuất hiện) của <var>, dời vào region Deleted Content;
                                 dòng đã comment sẵn ngoài region (module đóng từ trước, vd LuckyShoot) cũng được dời + gắn tag //D
  --guard-only <var> "<note>"    dời dòng `new` của <var> vào region Guard-Only (vẫn sống), gắn marker //guard-only ở init/reset (giữ vị trí)
  --build <buildXXX>             ghi vào marker dòng ctor (default build180)
  --file <path>                  ModuleMgr.js (default src/gamemgr/ModuleMgr.js relative cwd)

Idempotent: chạy lại không tạo trùng. Không đổi thứ tự init/reset của module còn sống.
"""
import io, re, sys, argparse
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

R_DEL_CTOR  = '    // #region Deleted Content — module đã xóa resource (Layer 1: không new/init/reset). Rollback: uncomment 4 dòng + Restore backup'
R_GUARD     = '    // #region Guard-Only — feature đã đóng, resource đã xóa, nhưng VẪN register vì code active gọi PoolFunction của nó. GUI riêng chặn bằng return guard trong module'
R_DEL_BLOCK = '            // #region Deleted Content'
R_END_CTOR  = '    // #endregion'
R_END_BLOCK = '            // #endregion'

NL = '\n'   # line ending gốc của file — giữ nguyên để diff chỉ chứa dòng thật sự đổi (ModuleMgr.js là CRLF)

def load(p):
    global NL
    raw = io.open(p, encoding='utf-8', newline='').read()      # newline='' : không normalize CRLF
    NL = '\r\n' if '\r\n' in raw else '\n'
    return raw.split(NL)

def save(p, L): io.open(p, 'w', encoding='utf-8', newline='').write(NL.join(L))

def idx(L, pred, start=0, end=None):
    end = len(L) if end is None else end
    for i in range(start, end):
        if pred(L[i]): return i
    return -1

def blocks(L):
    """trả về dict name -> (start, end) index; ctor = [0, return{) ; init/reset/resetReloadConfig = [header, next header)"""
    ret = idx(L, lambda s: s.strip().startswith('return{') or s.strip().startswith('return {'))
    b = {'ctor': (0, ret)}
    names = ['init', 'reset', 'resetReloadConfig', 'preInit']
    pos = {n: idx(L, lambda s, n=n: re.match(r'\s*' + n + r'\s*:\s*function\s*\(', s) is not None, ret) for n in names}
    order = [n for n in names if pos[n] >= 0]
    for k, n in enumerate(order):
        if n == 'preInit': break
        b[n] = (pos[n], pos[order[k + 1]])
    return b

def region_range(L, header, start, end):
    """(header_idx, endregion_idx) của region trong [start,end) hoặc (-1,-1)"""
    h = idx(L, lambda s: s.rstrip() == header.rstrip(), start, end)
    if h < 0: return -1, -1
    e = idx(L, lambda s: s.strip() == '// #endregion', h + 1, end)
    return h, e

def ensure_regions(L):
    b = blocks(L)
    # ctor: trước `var cheatModule`
    s, e = b['ctor']
    if region_range(L, R_DEL_CTOR, s, e)[0] < 0:
        anchor = idx(L, lambda x: re.match(r'\s*var\s+cheatModule\s*=', x) is not None, s, e)
        ins = [R_DEL_CTOR, R_END_CTOR, '', R_GUARD, R_END_CTOR, '']
        L[anchor:anchor] = ins
    for name, anchor_pred in (
        ('init',  lambda x: x.strip() == 'cheatModule.init();'),
        ('reset', lambda x: x.strip() == 'cheatModule.reset();'),
        ('resetReloadConfig', lambda x: x.strip().startswith('if(gc.ENABLE_PENDANT)')),
    ):
        b = blocks(L); s, e = b[name]
        if region_range(L, R_DEL_BLOCK, s, e)[0] < 0:
            anchor = idx(L, anchor_pred, s, e)
            # đặt trước dòng trống liền trước anchor nếu có
            if anchor > 0 and L[anchor - 1].strip() == '': anchor -= 1
            L[anchor:anchor] = [R_DEL_BLOCK, R_END_BLOCK]
    return L

def move_into_region(L, line, header, blockname):
    b = blocks(L); s, e = b[blockname]
    h, end = region_range(L, header, s, e)
    if end < 0: raise SystemExit(f'region {header!r} không có trong {blockname}')
    L.insert(end, line)

def relocate_marked(L):
    """dời dòng đã comment có '//deleted content' (từ batch trước) vào region"""
    for blockname, header in (('ctor', R_DEL_CTOR), ('init', R_DEL_BLOCK), ('reset', R_DEL_BLOCK), ('resetReloadConfig', R_DEL_BLOCK)):
        b = blocks(L); s, e = b[blockname]
        h, end = region_range(L, header, s, e)
        moved = []
        i = s
        while i < e:
            t = L[i]
            if t.strip().startswith('//') and '//deleted content' in t and not (h < i < end):
                moved.append(t); del L[i]; e -= 1
                if i < h: h -= 1; end -= 1
                elif i < end: end -= 1
                continue
            i += 1
        for m in moved: move_into_region(L, m, header, blockname)
    return L

def retire(L, var, bundle, build):
    n = 0
    # ctor
    b = blocks(L); s, e = b['ctor']
    h, end = region_range(L, R_DEL_CTOR, s, e)
    # chấp nhận cả dòng ctor ĐÃ comment sẵn ngoài region (module đóng từ trước, vd LuckyShoot); dòng đã nằm trong region bỏ qua (idempotent)
    i = -1
    for k in range(s, e):
        if h < k < end: continue
        if re.match(r'\s*(//\s*)?var\s+' + re.escape(var) + r'\s*=\s*new\s+\w+\(\);', L[k]): i = k; break
    if i >= 0:
        line = L.pop(i)
        s_ = re.sub(r'^//\s*', '', line.strip())
        if not re.search(r'//\s*D\b', s_):                      # module chưa có tag //D //<bundle> (vd BuffetOffer) → gắn để trace tool nhận ra
            s_ = s_ + f'            //D     //{bundle}'
        move_into_region(L, '    //' + s_ + f'     //deleted content {build}', R_DEL_CTOR, 'ctor'); n += 1
    for blockname in ('init', 'reset', 'resetReloadConfig'):
        while True:
            b = blocks(L); s, e = b[blockname]
            h, end = region_range(L, R_DEL_BLOCK, s, e)
            j = -1
            for k in range(s, e):
                if h < k < end: continue                                           # đã nằm trong region → idempotent
                if re.match(r'\s*(//\s*)?' + re.escape(var) + r'\.(init|reset)\(\);\s*(//.*)?$', L[k]): j = k; break
            if j < 0: break
            line = L.pop(j)
            body = re.sub(r'^//\s*', '', line.strip()).split('//')[0].strip()
            move_into_region(L, '            //' + body + f'{" " * 20}//deleted content {bundle}', R_DEL_BLOCK, blockname); n += 1
    return L, n

def guard_only(L, var, note):
    n = 0
    b = blocks(L); s, e = b['ctor']
    i = idx(L, lambda x: re.match(r'\s*var\s+' + re.escape(var) + r'\s*=\s*new\s+\w+\(\);', x) is not None, s, e)
    if i >= 0:
        h, end = region_range(L, R_GUARD, s, e)
        if not (h < i < end):
            line = L.pop(i).rstrip()
            move_into_region(L, line + f'     //guard-only: {note}', R_GUARD, 'ctor'); n += 1
    for blockname in ('init', 'reset', 'resetReloadConfig'):
        b = blocks(L); s, e = b[blockname]
        for j in range(s, e):
            if re.match(r'\s*' + re.escape(var) + r'\.(init|reset)\(\);\s*$', L[j]):
                L[j] = L[j].rstrip() + f'{" " * 20}//guard-only'; n += 1
    return L, n

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--file', default='src/gamemgr/ModuleMgr.js')
    ap.add_argument('--build', default='build180')
    ap.add_argument('--init-regions', action='store_true')
    ap.add_argument('--retire', nargs=2, metavar=('VAR', 'BUNDLE'), action='append', default=[])
    ap.add_argument('--guard-only', nargs=2, metavar=('VAR', 'NOTE'), action='append', default=[])
    a = ap.parse_args()
    L = load(a.file)
    if a.init_regions:
        L = ensure_regions(L); L = relocate_marked(L); print('regions ensured; marked lines relocated')
    for var, note in a.guard_only:
        L, n = guard_only(L, var, note); print(f'guard-only {var}: {n} dòng')
    for var, bundle in a.retire:
        L, n = retire(L, var, bundle, a.build); print(f'retire {var} ({bundle}): {n} dòng')
    save(a.file, L)
