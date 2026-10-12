# Reference — Animation Gates (`res/animation`)

## Chạy theo bundle (mặc định từ v1.1) — animation đi cùng batch content

`trace_bundle.py --bundle <b>` tự gọi `trace_anim.analyze()` và in **G10b**: mọi group animation có usage trong module dir của bundle, với quyết định:

| Quyết định | Điều kiện | Làm gì |
|---|---|---|
| **xóa** | mọi usage (2 hop) nằm trong module dir của bundle này, **hoặc** thêm dir của bundle khác **đã Layer 1** (ctor đã comment) | stem vào `trace/anim_<b>.stems.txt` → `gen_anim_manifest.py --bundle <b>-anim --from-file …` → Audit/Move/Verify (mode `group`) → commit cùng batch |
| **chờ** | còn usage trong dir module `//D` **chưa** Layer 1 | không xóa; bundle đó khi chạy sẽ thấy "chung với bundle đã retire" và xóa |
| **giữ** | có usage ACTIVE / Guard-Only / wrapper AnimationMgr top-level; hoặc cờ họ động / config / CDN / override | ghi vào bundle spec mục Animation, không xóa |

Trước khi tin dòng "xóa": mở caller (kể cả wrapper) — đúng module retired? `preloadAllAnimation` 0 caller? Registry `AniSource` **không sửa**. Ca thật: `effReceiveGift` (battlepass21) đúng retired-only nhưng user chọn giữ — quyết định cuối vẫn là user tại checkpoint.

Chế độ toàn repo (`trace_anim.py` CLI) chỉ dùng để audit/orphan; **không** đưa orphan vào batch feature (user đã hủy phần này 2026-09-09).

## Khác content ở 3 điểm

Khác content ở 3 điểm: đơn vị xóa là **group theo tên** (không phải folder), consumer resolve qua **registry** `AniSource`/`AniSpineSource` trong `src/base/animation/AnimationMgr.js`, và tên có thể là **động** (itemId skin, `"effEmotion_" + id`, `effStickS<i>`). Không có Layer 1/2/3 — chỉ có gate chứng minh không ai gọi. Mục tiêu 0 dòng code.

```bash
S=.claude/skills/dev-delete-feature-content/scripts
python $S/trace_anim.py [--repo-root .] [--out docs/modules/<task>/phase2-animation/trace] [--only <stem>]...
python $S/gen_anim_manifest.py --bundle anim-<x> --build <build> --branch <branch> (--class retired-only | --stem <k>... | --from-file <txt>)
powershell -NoProfile -ExecutionPolicy Bypass -File "$PWD/$S/delete_feature_content.ps1" -Action Audit -Bundle anim-<x> -ManifestDir "<phase2>/manifests" [-DryRun]
```

## Runtime facts (verify lại mỗi branch — `grep -n` trong `AnimationMgr.js`)

| Fact | Hệ quả |
|---|---|
| DragonBones: `createAnimation*(key)` → `animation/config/<key>.xml` + `animation/texture/<key>.plist` (png do plist ghi); override `AniPathFolder*[key]` | Group DB = xml + plist + png + `res#tcf_astc/animation/texture/<key>.png` |
| Spine: `createSpineAnimation(key)` → `atlas/<key>.json` + `atlas/(AniSpineAtlasSource[key] ?? key).atlas`; png = tên ghi **trong** `.atlas` | Group Spine = json + atlas + png-theo-.atlas + astc; png có thể dùng chung ⇒ generator tự `retained` |
| `preloadAllAnimation()` load mọi key `AniSource` — **phải 0 caller sống** (AG6) | 0 ⇒ key treo vô hại, không sửa registry. ≠ 0 ⇒ đổi design (sửa registry hoặc bỏ) |
| **Wrapper** `AnimationMgr.<fn> = function(){ createAnimation(AniSource.k) }` được gọi qua `AnimationMgr.<fn>(` | Quét usage **cả trong `AnimationMgr`** (trừ block registry) và truy caller wrapper ≥2 hop. Bỏ cả file `AnimationMgr` ⇒ báo orphan nhầm (`effUnlockMinigame` — ca thật) |
| Tên động: `if (info.itemId in AniSource)`, `("effEmotion_" + id) in AniSpineSource`, `AniSource[preNameStickS + i] = …`, `avatarFrame in AniSource` | Key dạng itemId/skin/avatar (`Skin_*`) và họ có hậu tố số ⇒ **giữ cả họ** |
| `ignore/stickeff` là group `cdn.json` | Không pack APK ⇒ ngoài scope |

## Gate table (`trace_anim.py` → `report_animation.md`)

| Gate | Phát hiện | Đọc / quyết định |
|---|---|---|
| AG1 Group | DB/Spine group, file lẻ không thuộc group, group thiếu thành phần, png Spine dùng chung | Lẻ/thiếu ⇒ để lại (không xóa nửa group). Png chung ⇒ chỉ xóa khi mọi stem dùng nó cùng batch |
| AG2 Static 2 hop | `AniSource.<k>`/`AniSpineSource.<k>`/`"<k>"` dòng sống; wrapper → caller (kind retired:<bundle> / GUARD-ONLY(active) / ACTIVE) | class `retired-only` ⇒ B1 ứng viên; `ORPHAN` ⇒ soát tay; `ORPHAN (wrapper không caller)` ⇒ soát kỹ hơn (wrapper có thể gọi động) |
| AG3 Dynamic | prefix họ (strip số) trong src/config; concat `"<prefix>" +`; `AniSource[`/`in AniSource` global | class `KEEP-dynamic/config` ⇒ giữ cả họ |
| AG4 Config | tên/prefix trong `res/config/**/*.json` | giữ (server có thể trả tên) |
| AG5 Override | `AniPathFolder*`/`AniSpineAtlasSource` set ở code sống | trace theo path thật |
| AG6 Preload | caller `preloadAllAnimation` | phải 0 |
| AG7 CDN | stem trong `cdn.json` | ngoài scope |
| AG8 Retired-consumer | caller B1 trong dir module Layer 1, **không** Guard-Only | fail ⇒ ACTIVE, giữ |

## Soát tay ORPHAN (bắt buộc trước B2/B3)

Với mỗi stem class ORPHAN: grep tên đầy đủ **kể cả comment** trong `src/`, `res/config`, `res/content/**/*.json`, `*.manifest`; prefix không số (`"effRank" +`, `"effCard" +`, `this["eff" + …]`); feature liên quan còn code sống không (minigame DiceRoll ↔ `effRollDice*`, hitegg ↔ `effHitEgg*`, unlock ↔ `effUnlock*`). Xếp:

| Tier | Điều kiện | Batch |
|---|---|---|
| T1 | 0 bằng chứng, feature không còn code sống gọi | B2 `anim-orphan-1` |
| T2 | có dấu hiệu nghi (comment, prefix gần đúng, feature còn sống chưa thấy đường gọi, wrapper 0 caller) | B3 — **user duyệt từng tên** |
| KEEP | tìm được đường gọi sống | không xóa; ghi vào report để sửa gate nếu tool sót |

## Vòng lặp batch animation (khác phase 1)

1. Pre-Move: `trace_anim.py` lại → class từng stem trong manifest khớp bundle spec; AG6 vẫn 0.
2. `gen_anim_manifest.py` (patch rỗng, `removalMode: group`) → `Audit` → `Move` → `Verify` với `-ManifestDir <phase2>/manifests`. Trong script batch: `set -o pipefail` hoặc `${PIPESTATUS[0]}` — **không** để `| grep` nuốt exit code của tool.
3. Agent Verify: manifest `status = verified` (đọc file, không tin log) · `git diff --stat -- src/` = 0 · chỉ file `res/animation/**` + `res#tcf_astc/animation/**` staged · `AnimationMgr.js` không đổi · backup `_meta\anim-*\manifest.json`. **Chỉ commit sau khi status = verified.**
4. Commit `chore (deletecontent): remove animation <bundle> — N files, B bytes, backup <build>`; body liệt kê stem.
5. User smoke: lobby → bàn → kết thúc ván → shop/gacha/upgrade → emotion/skin/avatar frame → unlock → logout/login; log không có `loadDragonBonesData`/`DBCCFactory`/`SkeletonAnimation` missing.

## Common mistakes (đã gặp 2026-09-09)
- Loại cả `AnimationMgr.js` khỏi vòng quét usage ⇒ mất wrapper ⇒ `effUnlockMinigame` báo orphan sai (user phát hiện).
- `glob` trên Windows trả `\` ⇒ so sánh path với `/` lệch ⇒ báo "file lẻ" sai. Luôn `norm()`.
- Tag bundle lấy từ dòng ModuleMgr đã comment bắt nhầm token `var` ⇒ kind `retired:var`.
- Chỉ strip hậu tố số khi tìm họ: `effRankS/A/B`, `effCardPlay/Idle` là họ theo **chữ** — soát tay phải grep prefix `"effRank"`, `"effCard"`.
- Manifest animation phải `removalMode: group`. B1 thật dùng `full-folder` ⇒ Verify FAIL 5 lỗi "folder vẫn tồn tại" dù SHA khớp (folder `config/texture/atlas` dùng chung).
- Script batch `powershell … | grep … || abort` nuốt exit code ⇒ commit khi manifest còn `moved`. Dùng `${PIPESTATUS[0]}`/`set -o pipefail` và đọc `status` trong manifest trước `git commit`.
- Trình user số **animation** (group) trước số file (1 DragonBones = 4 file); tách rõ nhóm nằm ngoài spec gốc (orphan) — B2/B3 bị hủy vì user chỉ muốn đúng 13 feature.
- Heuristic họ tên: khi prefix cũng là 1 stem (`eff7DayGift` ↔ `eff7DayGift2`), usage literal `AniSource.eff7DayGift` **không** là bằng chứng động — chỉ tính ghép chuỗi (`"prefix" +`, `"prefix_"`). Lần đầu `eff7DayGift2` bị giữ nhầm (B1 thật sót 0.05 MiB).
