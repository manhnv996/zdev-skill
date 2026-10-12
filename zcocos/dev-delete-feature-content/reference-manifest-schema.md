# Reference — Removal Manifest & Safety Tool

Manifest là **input + state** của tool. Tool chỉ thực thi và kiểm chứng manifest, **không tự quyết định xóa gì** — quyết định nằm ở bundle spec đã duyệt.

## Manifest — `docs/modules/<task>/manifests/<bundle>.json` (gitignored)

```json
{
  "bundle": "firstpay2021",
  "build": "build180",
  "branch": "build180_update_deletecontent",
  "removalMode": "full-folder",
  "status": "planned",
  "generatedAt": "",
  "backupRoot": "D:\\workspace\\BidaMobile\\client-delete-content-backup",
  "quarantinePatch": "_meta/firstpay2021/quarantine.patch",
  "unresolved": [],
  "removed":  [ { "path": "res/content/firstpay2021/FirstPay2021Icon.json", "bytes": 0, "sha256": "" } ],
  "retained": [],
  "totals": { "files": 0, "bytes": 0 }
}
```

| Field | Ý nghĩa |
|---|---|
| `removalMode` | `full-folder` (retained rỗng, Verify đòi folder `res/content/<b>` biến mất) \| `partial-prune` (retained ≠ rỗng, Verify đòi không còn folder rỗng) \| **`group`** (xóa theo nhóm file trong folder dùng chung — animation; Verify **không** check folder, retained cho phép) |
| `status` | `planned` → `audited` → `moved` → `verified`; `restored` sau rollback. Tool chỉ tiến theo thứ tự |
| `unresolved` | Path còn consumer chưa xác định. **Non-empty ⇒ tool refuse mọi action ghi** |
| `removed` / `retained` | Forward slash, relative repo root. `bytes`/`sha256` do `Audit` điền — **không viết tay** |
| `quarantinePatch` | Relative từ `<backupRoot>\<build>\`; nội dung = `git diff` mọi file code sửa cho bundle này |
| `build` | Layer folder trong backup: `<backupRoot>\<build>\<relative path>` |

Sinh manifest từ inventory thật (không gõ tay 100 path):

```bash
python scripts/gen_manifest.py --bundle <b> --build build180 --branch <branch> \
  [--retained res/content/<b>/X.plist --retained res/content/<b>/X.png --retained "res#tcf_astc/content/<b>/X.png"] \
  [--repo-root <path>] [--manifest-dir <path>] [--backup-root <path>]
```

Refuse ghi đè manifest có `status ≠ planned`. Retained phải tồn tại trên disk. Mode tự suy ra từ retained.

Animation của bundle đi **manifest riêng** `<bundle>-anim.json` (mode `group`, field thêm `animationStems`, `quarantinePatch: ""`), sinh bằng `gen_anim_manifest.py --bundle <bundle>-anim --from-file trace/anim_<bundle>.stems.txt …`; Audit/Move/Verify riêng, **commit cùng** batch content. Backup `_meta\<bundle>-anim\manifest.json`. Rollback bundle = Restore cả 2 manifest + `git apply -R` patch content.

## Dependency group — luật bất biến

| Group | Thành phần | Luật |
|---|---|---|
| Atlas | `X.plist` + `X.png` + `res#tcf_astc/<same rel path>/X.png` | xóa/giữ **cùng nhau**. `Audit` refuse plist removed mà texture retained hoặc ngược lại |
| Texture rời | `Y.png/.jpg` + ASTC counterpart | ASTC luôn đi theo bản gốc (`Audit` refuse lệch parity) |
| UI JSON | `.json` (không có ASTC) + atlas nó khai báo ở field `"Plist"` | JSON retained ⇒ atlas nó dùng phải retained (frame `Default/*` không cần) |

## Tool — `scripts/delete_feature_content.ps1`

```powershell
delete_feature_content.ps1 -Action <Audit|Move|Verify|Restore> -Bundle <b>
    [-RepoRoot <path>]      # default cwd; refuse nếu không có project.json
    [-ManifestDir <path>]   # default <RepoRoot>\docs\modules\deletefeaturecontent\manifests
    [-BackupRoot <path>]    # default D:\workspace\BidaMobile\client-delete-content-backup
    [-Build <string>]       # default manifest.build
    [-DryRun]
```

Gọi từ Bash: `powershell -NoProfile -ExecutionPolicy Bypass -File "<abs path>.ps1" -Action Audit -Bundle <b>`.

| Action | Precondition | Làm gì | Post |
|---|---|---|---|
| `Audit` | manifest tồn tại, `unresolved` rỗng | mọi path tồn tại; tính bytes + SHA-256; parity ASTC + dependency group; điền `totals` | `audited` |
| `Move` | `audited` | move `removed` → `<BackupRoot>\<Build>\<rel>`; xóa folder rỗng; copy manifest + patch + **chính script** vào `_meta\` | `moved` |
| `Verify` | `moved` | removed vắng repo + có trong backup SHA khớp; retained còn đủ parity; không folder rỗng | `verified` |
| `Restore` | `moved`/`verified` | copy ngược; nhắc `git apply -R quarantine.patch` | `restored` |

`-DryRun` chỉ có ý nghĩa với `Audit` (và `Move` khi status đã `audited`); **không dry-run được cả chuỗi** vì `Move`/`Verify` cần status thật. Muốn thử trọn vòng ⇒ fixture `scripts/tests/` (`make_fixture.sh` + `run_tests.ps1`), không thử trên repo.

**Refuse (exit 1, không ghi gì):** `unresolved` non-empty · path removed không tồn tại · ASTC counterpart tồn tại nhưng không trong removed/retained · plist/texture tách group · status sai precondition · `BackupRoot` nằm trong `RepoRoot` · file đích đã tồn tại trong backup (check từng file) · `Build` rỗng/chứa separator · bundle name mismatch · removed ∩ retained · full-folder có retained · file đổi sau Audit · quarantinePatch khai báo nhưng thiếu file.

**Exit:** 0 OK · 1 refuse · 2 verify fail · 3 IO error.

**PS 5.1:** file `.ps1` **phải UTF-8 with BOM** (không BOM → tiếng Việt vỡ tokenizer: "Illegal '<' operator"). Sau khi edit bằng tool khác: `[IO.File]::WriteAllText(path, text, (New-Object Text.UTF8Encoding $true))`. Test suite: `bash scripts/tests/make_fixture.sh && powershell -File scripts/tests/run_tests.ps1` (41 ca; fixture reset trước mỗi lần).

## Backup layout

```
<BackupRoot>\<build>\
├── res\content\<bundle>\...            # mirror client 1-1
├── res#tcf_astc\content\<bundle>\...
└── _meta\
    ├── delete_feature_content.ps1      # bản copy để Restore không cần skill
    └── <bundle>\{manifest.json, quarantine.patch}
```

Nhiều bundle dùng chung cây `<build>\res\content\` — vì thế refuse #7 check theo file. Backup không tự xóa sau merge.

## Quarantine patch

```bash
git diff -- src/gamemgr/ModuleMgr.js <file Layer 2/3...> > docs/modules/<task>/manifests/<bundle>.quarantine.patch
```

Tạo **trước** `Move` (Move copy nó vào `_meta`). Chỉ chứa diff của bundle hiện tại — commit bundle trước xong mới bắt đầu bundle sau, đừng để patch lẫn 2 bundle.
