# Excel Commit Reference

Reference bắt buộc cho operation phase `excel-commit` của `dev-languagetool`. Đọc toàn bộ file này trước khi mở hoặc ghi workbook.

## Excel Commit — File & Cấu trúc

**File chính:** `D:\workspace\BidaMobile\language_tool\language_main.xlsx`

**Columns (12 cột):**

| Col | Header | Mô tả |
|-----|--------|-------|
| A (1) | `Key` | Key string dùng trong code |
| B (2) | `vi` | Tiếng Việt — **phải có dấu đầy đủ** |
| C (3) | `en` | Tiếng Anh |
| D (4) | `mm` | Myanmar — **agent tự dịch** |
| E (5) | `thai` | Thai — **agent tự dịch** |
| F (6) | `es` | **Copy từ `en`** |
| G (7) | `cn` | Tiếng Trung giản thể — **agent tự dịch** |
| H (8) | `cn2` | Tiếng Trung phồn thể — **chuyển từ `cn`** |
| I (9) | `ru` | **Copy từ `en`** |
| J (10) | `in` | **Copy từ `en`** |
| K (11) | `id` | **Copy từ `en`** |
| L (12) | `tr` | **Copy từ `en`** |

> **Quy tắc:** mọi key mới/update phải điền **đủ 12 cột**, không để trống chờ translator.
> - `mm`, `thai`, `cn`: agent tự dịch từ VI/EN. Bám thuật ngữ đã dùng trong file — search vài key gần nghĩa ở cùng cột để lấy cách gọi chuẩn (vd `shop` → `ဆိုင်` / `ร้านค้า` / `商店`).
> - `cn2`: bản phồn thể của `cn`. Nếu không chắc cách chuyển thì copy nguyên `cn`.
> - `es`, `ru`, `in`, `id`, `tr`: dùng nguyên text tiếng Anh.
>
> Chỉ để trống khi user nói rõ là để translator điền sau.

### Xuống dòng — dùng `\n`, KHÔNG dùng newline thật

Ô Excel phải chứa **2 ký tự** `\` + `n`, không được chứa ký tự xuống dòng thật (LF/CR).
Tool export đọc `\n` rồi mới sinh ra newline trong `lang_*.json`; newline thật trong ô sẽ ra kết quả khác
và code không hiểu.

| | Ô Excel | `lang_vi.json` |
|---|---|---|
| ✅ Đúng | `Sự kiện đã kết thúc.\nHãy quay lại sau nhé` | `"...kết thúc.\\nHãy..."` |
| ❌ Sai | ô có Alt+Enter (LF thật) | — |

Đối chiếu nhanh bằng row có sẵn: `hawkwings_increament_exp`, `dice_roll_combo_description_sanh_nho`,
`spinball_noti_getgift` — cả 3 đều dùng `\n`.

Khi sinh data bằng Python, viết `chr(92) + "n"` chứ đừng viết `"\n"` trong string literal —
cái sau ra LF thật.

> **Ghi chú `mm`:** các row cũ trong file dùng **Zawgyi** (có `ၾ` U+107E, `္` U+1039) chứ không phải Unicode Burmese (`ြ` U+103C, `်` U+103A). Row mới viết bằng Unicode. Nếu QA báo chữ Myanmar bị vỡ thì nguyên nhân là font client vẫn là Zawgyi — báo user chứ đừng tự đổi encoding.

---

## Excel Commit — Workflows

### Excel Write Safety

**Bắt buộc dùng Excel COM cho mọi thao tác ghi `.xlsx`.** Không được fallback sang sửa trực tiếp OOXML/ZIP package (`ZipFile`, `sheet1.xml`, `sharedStrings.xml`, `[Content_Types].xml`, v.v.) để insert/update dữ liệu. Đọc XML read-only để chẩn đoán thì được; ghi XML trực tiếp vào `.xlsx` thì không.

Trước khi ghi:

1. Check lock file cùng folder: `~$language_main.xlsx`.
   - Nếu tồn tại: dừng, báo user đóng file Excel trước.
   - Không cố ghi, không tạo bản thay thế, không fallback sang XML.
2. Mở workbook bằng Excel COM read-write.
   - Nếu `Workbooks.Open(...)` fail: dừng và báo lỗi.
   - Không dùng tool khác để ghi thay Excel COM.
3. Insert/update bằng Excel object model:
   - Insert row bằng `$ws.Rows("$startRow`:$endRow").Insert(...)`
   - Ghi cell bằng `.Value2`
   - Save bằng `$wb.Save()`
4. Sau khi save, đóng workbook rồi mở lại bằng Excel COM read-only để verify đúng rows/key/text vừa ghi.
   - Nếu verify fail: báo user ngay, không claim thành công.

Lý do: không sửa XML trực tiếp vì Excel có thể không mở được workbook dù parser XML vẫn đọc được dữ liệu.

### Thêm keys vào cuối file

1. Dùng PowerShell Excel COM để mở file
2. Tìm last row theo cột A (`Key`), không dùng `UsedRange.Rows.Count` vì có thể lệch do format/rác:
   `$lastRow = $ws.Cells.Item($ws.Rows.Count, 1).End(-4162).Row`
3. Write từng row, đóng và save

### Thêm keys vào giữa (chèn dòng)

**Không được ghi đè** — phải insert rows trước để đẩy dữ liệu cũ xuống:

```powershell
# Chèn N rows trống tại vị trí startRow
$ws.Rows("$startRow`:$($startRow + $count - 1)").Insert([Microsoft.Office.Interop.Excel.XlInsertShiftDirection]::xlShiftDown)
# Sau đó ghi data vào các dòng vừa tạo
```

### Kiểm tra trước khi thêm

Luôn check trước khi thêm:

1. Search cột A để phát hiện key đã tồn tại.
   - Nếu key đã tồn tại và user không yêu cầu update → báo user, không add trùng.
   - Nếu user yêu cầu update → dùng workflow "Replace / Update keys đã tồn tại".
2. Đọc row tại vị trí target để xác nhận:
- Nếu trống → ghi trực tiếp
- Nếu có data → insert rows (shift down)

### Replace / Update keys đã tồn tại

Khi user nói "keys đã được thêm rồi, cần update từ dòng X":

1. **Đọc verify trước** — đọc dòng X đến X+N, in ra `[key] | vi | en` để xác nhận đúng keys cần update
2. **So sánh** với danh sách keys user cung cấp — nếu key ở dòng đó khớp → tiến hành ghi đè; nếu không khớp → báo user, không ghi
3. **Chỉ ghi đè các cột cần thay đổi** — không overwrite cột mm/thai/es/cn/cn2 nếu không cần thiết (có thể đã có bản dịch)
4. **Save và verify** lại sau khi ghi

> Không bao giờ ghi đè chỉ dựa vào số dòng user cung cấp mà không đọc verify trước.

---

## Excel Commit — PowerShell Template

```powershell
$excel = $null
$wb = $null
$ws = $null

try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $wb = $excel.Workbooks.Open("D:\workspace\BidaMobile\language_tool\language_main.xlsx")
    $ws = $wb.Sheets.Item(1)

    # --- Tìm last row theo cột Key (nếu thêm vào cuối) ---
    $xlUp = -4162
    $lastRow = $ws.Cells.Item($ws.Rows.Count, 1).End($xlUp).Row
    $startRow = $lastRow + 1

    # --- Hoặc insert rows nếu thêm vào giữa ---
    # $startRow = <target_row>
    # $count = <số dòng cần thêm>
    # $ws.Rows("$startRow`:$($startRow + $count - 1)").Insert([Microsoft.Office.Interop.Excel.XlInsertShiftDirection]::xlShiftDown)

    # --- Data: key, vi, en, mm, thai, es(en), cn, cn2, ru(en), in(en), id(en), tr(en) ---
    # Đủ 12 cột, không để trống. Xem mục "Truyền text non-ASCII" bên dưới.
    $rows = @(
        @("key_name", "Tiếng Việt có dấu", "English text", "မြန်မာ", "ไทย", "English text", "简体中文", "簡體中文", "English text", "English text", "English text", "English text")
    )

    for ($i = 0; $i -lt $rows.Count; $i++) {
        $r = $startRow + $i
        for ($c = 0; $c -lt $rows[$i].Count; $c++) {
            $ws.Cells.Item($r, $c + 1).Value2 = $rows[$i][$c]
        }
    }

    $wb.Save()
}
finally {
    if ($wb -ne $null) { $wb.Close($false) | Out-Null }
    if ($excel -ne $null) { $excel.Quit() | Out-Null }
    if ($ws -ne $null) { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ws) | Out-Null }
    if ($wb -ne $null) { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($wb) | Out-Null }
    if ($excel -ne $null) { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null }
}
```

---

## Excel Commit — Truyền text non-ASCII

Không nhúng thẳng tiếng Việt / Myanmar / Thai / Trung vào chuỗi lệnh PowerShell — qua shell dễ bị mangle encoding mà không báo lỗi.

Cách an toàn: ghi data ra file JSON UTF-8 trước (Python hoặc tool khác), rồi để PowerShell đọc lại:

```powershell
$rows = Get-Content -Raw -Encoding UTF8 "path\to\rows.json" | ConvertFrom-Json
```

Trước khi ghi Excel, đối chiếu text VI trong JSON với `res/localize/lang_vi.json` để chắc hai nguồn không lệch.

---

## Excel Commit — Verify sau khi thêm

Luôn verify bằng cách đóng workbook, mở lại read-only rồi đọc **đủ 12 cột** của các dòng vừa ghi — đọc 3 cột đầu không phát hiện được ô ngôn ngữ bị bỏ trống:

```powershell
for ($r = $startRow; $r -le ($startRow + $rows.Count - 1); $r++) {
    for ($c = 1; $c -le 12; $c++) {
        $val = $ws.Cells.Item($r,$c).Text
        if ([string]::IsNullOrEmpty($val)) { $val = "(TRONG)" }
        Write-Output ("  {0,-5} {1}" -f $ws.Cells.Item(1,$c).Text, $val)
    }
}
```

Bất kỳ ô nào ra `(TRONG)` đều là fail, trừ khi user đã nói rõ để translator điền sau.

Quét thêm ký tự xuống dòng thật — `(TRONG)` không bắt được lỗi này:

```powershell
$v = [string]$ws.Cells.Item($r,$c).Value2
if ($v.Contains([char]10) -or $v.Contains([char]13)) { Write-Output "CON LF THAT: row $r cot $c" }
```
Nếu input source là `dev-status.md`, chỉ update cột `Excel` sang `✅` sau khi verify các dòng trong Excel đã đúng key/vi/en.
