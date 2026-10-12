---
name: dev-languagetool
description: Use when drafting or tracking BidaMobile localization keys in a dev-status.md Localization Keys table, or when adding and updating keys in language_main.xlsx.
---

# dev-languagetool — BidaMobile Localization

## Operation Phases

Chọn **operation phase** trước, sau đó mới xác định input source và loại thao tác:

- **`status-draft`**: chuẩn bị hoặc cập nhật text draft trong section `Localization Keys` của `dev-status.md`; tuyệt đối không đụng vào Excel.
- **`excel-commit`**: ghi hoặc cập nhật localization trong `language_main.xlsx` theo toàn bộ safety flow hiện có.

Quy tắc chọn phase:

1. Prompt nói rõ `status-draft`, `chỉ cập nhật dev-status`, `draft localization`, `chưa ghi Excel`, hoặc caller khác truyền handoff `phase: status-draft` → dùng `status-draft`.
2. Prompt nói thêm/update key trong Excel, chạy localization sau khi text đã được confirm, hoặc truyền `phase: excel-commit` → dùng `excel-commit`.
3. **Tương thích ngược:** nếu prompt không chỉ rõ phase, mặc định dùng `excel-commit`. Mọi cách gọi `dev-languagetool` cũ phải tiếp tục đi qua flow Excel hiện tại.
4. Không tự chuyển từ `status-draft` sang `excel-commit` trong cùng lượt, trừ khi user đã yêu cầu rõ cả hai phase.

## Input Source và Mutation Modes

Chọn mode từ prompt trước khi làm:

- **Direct key list mode**: user đưa trực tiếp danh sách key/text trong prompt. Dùng danh sách đó làm source input.
- **Dev Status Source mode**: user đưa đường dẫn `dev-status.md` hoặc nói "list Localization Keys trong dev-status". Đọc section `## Localization Keys (cần dịch)` trong file đó và dùng bảng markdown làm source input.
- **Update existing mode**: user nói key đã thêm rồi, cần update từ dòng X hoặc sửa text của key đã tồn tại. Phải verify dòng/key trước khi ghi đè.

Không tự scan feature/code để suy diễn key mới nếu user đã chỉ rõ source là `dev-status.md`. Source chuẩn lúc này là bảng `Localization Keys` trong `dev-status.md`.

## Phase `status-draft`

Dùng phase này để tạo checkpoint localization trong docs trước khi user test và confirm text.

### Input tối thiểu

1. Đường dẫn `dev-status.md`.
2. Với mỗi entry: `Key`, `Gợi ý text (VI)` và `Ghi chú` về nơi/mục đích sử dụng.
3. Entry có thể truyền `reuseExisting: true` khi caller đã verify đây là key có sẵn được dùng lại; mặc định là `false`.

Nếu caller như `dev-feature` đã cung cấp đủ các trường trên thì thực hiện ngay, không hỏi lại và không hỏi user có muốn thêm key vào `dev-status.md` hay không.

### Reuse check — bắt buộc trước khi tạo key mới

Với **mỗi** entry chưa có `reuseExisting: true`, phải tự tìm key có sẵn cùng semantics trước khi coi là key mới. Grep tên key trong `src/` là **không đủ** — tên key mới đương nhiên chưa tồn tại; phải tìm theo **nội dung text**.

Cách làm:

1. Đọc `res/localize/lang_vi.json` (cấu trúc `{"text": {...}}`, vài nghìn entry).
2. Với mỗi text VI dự kiến, tìm entry có nghĩa tương đương — so khớp theo từ khóa nội dung, không theo prefix feature.
3. Ưu tiên tìm các nhóm hay lặp lại giữa feature:
   - Tên chế độ chơi, tên kênh, đơn vị tiền
   - Nhãn trạng thái ngắn: thắng/thua, bỏ qua, đóng, nhận, sẵn sàng
   - Câu thông báo chung: sự kiện kết thúc, lỗi chung, chạm để nhận
   - Mô tả khoảng thời gian, countdown
4. Tìm được key cùng semantics → dùng key đó trong code, và đưa vào bảng với `Excel = N/A`. **Không** tạo key mới trùng nghĩa.
5. Khi reuse, phải đọc text thật của key đó để biết **placeholder và color tag có sẵn** (vd `@date1@`/`@date2@` thay vì `@from@`/`@to@`), rồi sửa code cho khớp — không tự đặt placeholder mới.

Báo lại cho caller danh sách key đã thay bằng key có sẵn, kèm tên key cũ → key mới.

### Ghi text tạm vào `lang_vi.json`

Sau khi chốt danh sách key **mới** (`Excel = ⬜`), ghi luôn text VI vào `res/localize/lang_vi.json` (nhánh `text`) để feature test được runtime ngay, không phải chờ Excel.

- Chỉ thêm key mới; key đã có trong file thì bỏ qua, không ghi đè.
- Giữ nguyên format file: `indent=2`, `ensure_ascii=false`, và **giữ nguyên line ending sẵn có** của file.
- Key reuse (`N/A`) **không** đụng tới.
- Đây là text tạm để test; nguồn sự thật vẫn là Excel ở phase `excel-commit`.
- Verify sau khi ghi: mọi key `fr.Localization.text("...")` trong code feature đều có text trong `lang_vi.json`.

#### Phạm vi được phép đụng

Nhiệm vụ ở bước này **chỉ là thêm đúng các key `⬜` trong bảng `dev-status.md` của task hiện tại** —
cùng một nguồn với `excel-commit`, không mở rộng phạm vi.

- **Không rà soát** phần còn lại của `lang_vi.json`. Thấy key trùng, text sai chính tả, key có vẻ
  không còn dùng → **report cho user**, không tự sửa và không tự xoá. File này sinh từ Excel;
  sửa ở client là làm lệch với nguồn.
- **Không xoá key nào**, kể cả key trùng lặp hoàn toàn.
- **Không sửa text của key cũ**, kể cả khi task có key mới nghĩa gần giống.

> ⚠️ Hậu quả có thể xảy ra **mà không cần chủ ý**. `lang_vi.json` có hàng chục key bị lặp (cùng key,
> 2 dòng, đôi khi khác nội dung). Đọc cả file bằng `json.loads` rồi ghi đè bằng `json.dumps` sẽ
> **âm thầm gộp** các dòng trùng đó — giữ bản cuối, bỏ bản trước. Diff hiện ra y như *agent tự sửa
> nội dung / tự xoá key*. Đã xảy ra một lần: 48 key, mất 58 dòng. Vì vậy **đừng ghi đè cả file**
> khi chỉ cần thêm vài key — chèn dòng vào trước chỗ đóng nhánh `text` là đủ.

**Cổng kiểm trước khi kết thúc bước này** — đếm số lần xuất hiện của từng key, trước và sau khi ghi:

- Mọi key cũ giữ **nguyên số dòng** (key trùng vẫn phải còn đủ số dòng trùng).
- Diff chỉ gồm các key mới của task.
- Chạm vào bất kỳ dòng nào khác → hoàn tác, làm lại bằng cách chèn dòng, và báo user.

### Bố cục bảng Localization

Bảng chia **2 section** cho dễ đọc:

1. **Key có sẵn — reuse, KHÔNG cần update Excel**: cột `Text VI hiện có` / `Dùng ở đâu` / `Excel = N/A`. Đặt **trên**, nêu rõ chỉ liệt kê để ghi nhận dependency.
2. **Key mới — cần thêm vào Excel**: cột `Gợi ý text (VI)` / `Ghi chú` / `Excel = ⬜`. Ghi rõ đã thêm vào `lang_vi.json` chưa.

Chỉ dùng 1 bảng phẳng khi feature không có key reuse nào.

### Flow

1. Đọc đúng file `dev-status.md` được truyền vào.
2. Xác định section Localization:
   - Nếu chưa có heading Localization nào → tạo section `## Localization Keys (cần dịch)` với bảng canonical bốn cột rồi tiếp tục.
   - Nếu đã có heading Localization nhưng bảng dùng schema legacy/khác bốn cột canonical → không tự migrate, không xóa dữ liệu và không tạo section Localization thứ hai; report schema conflict cho caller.
3. Parse bảng canonical có schema:
   - `Key`
   - `Gợi ý text (VI)`
   - `Ghi chú`
   - `Excel`
4. Chuẩn hóa key/text theo `Content Formatting Rules` trong skill này.
5. Merge theo key với thứ tự ưu tiên sau:
   - Nếu bảng đã có nhiều row cùng key → không mutate các row đó; report duplicate conflict.
   - **Ưu tiên xử lý row `N/A` trước:** luôn giữ `N/A`. Nếu text VI mới khác text đang có, report conflict để user chọn update shared key hay tạo feature key riêng; không tự đổi `N/A` thành `⬜`.
   - Key đã có với `Excel = ⬜` hoặc `✅`, text VI không đổi → merge thêm nơi sử dụng vào `Ghi chú` và giữ nguyên trạng thái `Excel`.
   - Key đã có với `Excel = ⬜` hoặc `✅`, text VI thay đổi rõ ràng theo requirement mới → cập nhật text và đặt `Excel = ⬜` để đánh dấu cần add/update lại Excel.
   - `reuseExisting: true` chỉ quyết định trạng thái khi tạo row mới; không được đổi trạng thái của row đã tồn tại.
   - Chưa có row và `reuseExisting: true` đã có evidence từ caller → append row `Excel = N/A`; không đưa key này vào batch Excel.
   - Chưa có row và không reuse key → append row `Excel = ⬜`.
   - Không được đặt `N/A` chỉ dựa vào tên key hoặc phỏng đoán; caller phải verify key đang tồn tại trong localization/code hiện có.
   - Khi merge nơi sử dụng, không xóa nội dung `Ghi chú` hiện có; append và dedupe ghi chú mới, trừ khi user yêu cầu rõ việc replace.
6. Report các row đã thêm, cập nhật, bỏ qua hoặc phát hiện conflict.

### Side-effect boundary

Trong `status-draft`:

- Không yêu cầu text EN, vị trí chèn hoặc đường dẫn xlsx.
- Không mở, đọc, kiểm tra lock hoặc ghi `language_main.xlsx`.
- Được phép thêm key **mới** vào `res/localize/lang_vi.json` để test runtime (xem section trên). Không sửa `lang_*.json` của ngôn ngữ khác, không sửa text của key đã có.
- Không đánh `Excel = ✅`.
- Hoàn thành phase ngay sau khi update và verify lại bảng trong `dev-status.md`.

Task chỉ thêm/sửa `lang_vi.json` để runtime test nằm ngoài responsibility của skill này. Không được vì task đó mà tự route sang `excel-commit`.

Nếu requirement về chính nội dung player-facing còn mơ hồ, có thể hỏi để làm rõ nội dung đó; không được dùng sự mơ hồ này để hỏi lại việc có cần tracking row hay không.

---

## Phase `excel-commit` — Bước 0: Thu thập thông tin

**Đọc argument/prompt trước.** Chỉ hỏi những gì còn thiếu — không hỏi lại thứ user đã cung cấp.

Các yêu cầu trong section này chỉ áp dụng cho `excel-commit`, không áp dụng cho `status-draft`.

Trước khi mở hoặc ghi workbook, bắt buộc đọc toàn bộ [references/excel-commit.md](references/excel-commit.md). Reference này là source chuẩn cho cấu trúc 12 cột, Excel COM, add/insert/update, PowerShell template và verify sau khi ghi.

Các guard không được bỏ qua dù đã đọc reference:

- Bắt buộc dùng Excel COM; không ghi trực tiếp OOXML/ZIP package.
- Check lock file `~$language_main.xlsx` trước khi mở read-write.
- Search key ở cột A và phân loại add/update trước khi ghi; không insert key trùng.
- Với update existing, verify row/key trước và chỉ ghi đè cột cần thay đổi.
- Sau khi save, đóng rồi mở lại read-only để verify; chỉ mark `Excel = ✅` cho key đã verify thành công.

Cần đủ 3 thông tin trước khi ghi vào xlsx:

1. **Đường dẫn file xlsx** — nếu không có, dùng default: `D:\workspace\BidaMobile\language_tool\language_main.xlsx`

2. **Vị trí thêm** — một trong hai:
   - "Thêm vào cuối" → tự tìm `lastRow`
   - "Thêm từ dòng X" → kiểm tra dòng X có data không; nếu có → insert + shift down; nếu trống → ghi trực tiếp

3. **Danh sách keys + nội dung** — cần ít nhất:
   - Key string (cột A)
   - Text tiếng Việt có dấu (cột B)
   - Text tiếng Anh (cột C)
   - `mm` / `thai` / `cn` / `cn2`: agent **tự dịch mặc định**, không để trống chờ translator
   - `es` / `ru` / `in` / `id` / `tr`: dùng nguyên text tiếng Anh

**Nếu thiếu bất kỳ mục nào → hỏi user trước khi chạy.**

Ví dụ prompt hỏi:
> Tôi cần thêm thông tin sau trước khi thêm keys:
> - Thêm vào cuối file hay từ dòng cụ thể?
> - Danh sách keys và text tiếng Việt/Anh?

**Chờ user cung cấp đủ → mới bắt đầu thực thi.**

---

## Excel Commit — Dev Status Source Mode

Dùng mode này khi prompt dạng:

- `dùng dev-languagetool cho list Localization Keys trong docs/modules/{feature}/dev-status.md`
- `thêm các key chưa add Excel trong dev-status`
- `add localization keys từ section Localization Keys`

Flow:

1. Đọc file `dev-status.md` user cung cấp.
2. Tìm section `## Localization Keys (cần dịch)`.
3. Parse bảng markdown có cột:
   - `Key`
   - `Gợi ý text (VI)`
   - `Ghi chú`
   - `Excel`
4. Mặc định chỉ lấy các dòng có `Excel = ⬜`.
   - Nếu user nói `all` / `force` / chỉ định key cụ thể thì làm theo phạm vi đó.
   - Dòng `Excel = ✅` phải bỏ qua nếu user không yêu cầu update/force.
   - `⬜` có thể là key mới cần add hoặc key cũ có text mới cần update; không mặc định mọi row `⬜` đều là insert mới.
   - Sau khi check cột A trong Excel:
     - Key chưa tồn tại → đi theo workflow thêm mới.
     - Key đã tồn tại và text VI/EN đã khớp → không ghi lại; verify row rồi có thể mark `✅`.
     - Key đã tồn tại nhưng text khác → hiển thị old/new, yêu cầu confirm nếu prompt chưa cho phép update, rồi đi theo workflow `Replace / Update keys đã tồn tại`; không insert key trùng.
5. Chuẩn hóa input:
   - Bỏ backtick bao quanh key, ví dụ `` `mg_title` `` → `mg_title`.
   - Bỏ một cặp quote ngoài cùng của text VI nếu có, nhưng giữ nguyên nội dung bên trong, placeholder, `\n`, và color tag.
   - Ghi chú dùng để trace UI/color tag, không ghi vào xlsx.

Sau khi chuẩn hóa input, xác định **text VI final** trước khi ghi Excel:

- Normalize cơ học như bỏ quote ngoài, sửa spacing tag, hoặc sửa format tag cho đúng rule thì được tự cập nhật vào `dev-status.md` và report trong summary.
- Nếu text cần **thêm color tag mới** theo `Content Formatting Rules`, bắt buộc chạy **Color Tag — Node Prefix Check** trước khi chốt text:
  - `Name` trong file UI `.json` bắt đầu bằng `text_` → tự thêm tag vào text final và `dev-status.md`, không hỏi user confirm.
  - `Name` không bắt đầu bằng `text_` → chưa thêm tag; đưa proposal, giải thích tag không render trên node hiện tại và hỏi user chọn đổi node/re-export hay giữ plain text.
  - Không trace được tới `Name` trong UI `.json` → không tự thêm tag; report thiếu evidence để caller bổ sung đường dẫn UI hoặc xác nhận cách xử lý.
- Sau khi chốt, dùng cùng một text VI final cho `dev-status.md` và Excel; không để hai nguồn lệch nhau.

6. Nếu thiếu text EN:
   - Agent có thể gợi ý bản EN dựa trên VI + ghi chú.
   - Phải dừng hỏi user confirm bản EN trước khi ghi Excel.
7. Nếu thiếu vị trí thêm:
   - Gợi ý `thêm vào cuối file`.
   - Hỏi user confirm nếu prompt chưa nói rõ.

Sau khi ghi và verify Excel thành công:

1. Update lại đúng file `dev-status.md`.
2. Chỉ đổi cột `Excel` từ `⬜` sang `✅` cho những key vừa verify đã thêm/update thành công.
3. Không tự sửa `Key` hoặc `Ghi chú`.
4. Chỉ sửa `Gợi ý text (VI)` khi normalize cơ học, tự thêm color tag sau khi verify UI JSON `text_`, hoặc khi user đã confirm text VI final theo rule ở trên.
5. Nếu một phần key lỗi/trùng/chưa ghi được, chỉ mark `✅` cho key thành công và report key còn lại.

---

## Content Formatting Rules

Áp dụng trước khi ghi vào xlsx — kể cả khi gợi ý text trong docs/conversation.

### Color Tags

Dùng `<color = #XXXXXX>...</color>` theo rule sau:

| Trường hợp | Màu | Ví dụ |
|------------|-----|-------|
| Placeholder `@xx@` (số lượng, chỉ tiêu, tên) | Vàng `#FFFF00` | `<color = #FFFF00> @num@ </color>` |
| Tên riêng / tên event cần nổi bật | Vàng `#FFFF00` | `<color = #FFFF00> Tri Ân Tháng </color>` |

> **Chú ý — spacing:** Nên có **1 dấu cách** giữa tag và nội dung: `<color = #FFFF00> @num@ </color>`. **Không viết liền** `<color = #FFFF00>@num@</color>`. Trừ 1 số case đặt biệt hoặc user note k cần.

**Không áp dụng color tag cho:**
- Tiêu đề section, button label
- Text trạng thái ngắn (vd: "Đã Hoàn Thành", "Hết Hạn")
- Placeholder thời gian dạng đặc biệt nếu user chỉ định bỏ qua

> Nếu user confirm bỏ qua color tag cho key cụ thể → không áp dụng cho key đó, vẫn áp dụng rule cho các key khác.

Khi thêm hoặc normalize tag của `CustomRichText`, luôn tạo đủ cặp tag mở/đóng cùng tên theo dạng `<tag = value> nội dung </tag>` và kiểm tra lại text final.

### Color Tag — Node Prefix Check

Với **mỗi key có hoặc cần thêm color tag trong text gợi ý**, cần truy ngược để xác nhận node UI hiển thị key đó có dùng prefix đúng.

**Lý do:** Chỉ node có prefix `text_` trong file `.json` UI mới được parse thành object custom có khả năng render `<color>` tag. Node prefix `label_` dùng label thông thường, không render được tag.

**Cách trace:**
1. Grep trong code JS tìm chỗ dùng key: `fr.Localization.text("key_name")`
2. Xem kết quả được set vào property/node nào: `this.xxxNode.setString(...)`, rồi tìm file UI `.json` tương ứng của GUI.
3. Kiểm tra trực tiếp trường `"Name"` trong file UI `.json`; tên property JS như `textInfo` chỉ dùng để trace, không thay thế bước này:
   - `"Name": "text_..."` (vd: `text_Info`) → ✅ rich text; tự áp dụng color tag, không hỏi confirm.
   - `"Name": "label_..."` hoặc prefix khác → ⚠️ không bảo đảm render tag; hỏi user chọn đổi node trong Cocos Studio rồi export lại, hoặc giữ text không tag.

**Quan trọng:** Không tự sửa file `.json` UI — file này được xuất bởi tool riêng (Cocos Studio). Chỉ **guide user**:
> "Key `xxx` được set vào node `label_Yyy` — node này cần đổi prefix thành `text_` trong Cocos Studio rồi export lại để color tag hoạt động."

Nếu không trace được key về node UI:
- Không coi tên property JS bắt đầu bằng `text` là đủ evidence để tự thêm tag.
- Report warning và yêu cầu caller bổ sung đường dẫn UI/node; chỉ dùng text có tag khi user đã chấp nhận rõ việc chưa verify khả năng render.

---

## Checklist

### Mọi phase

- [ ] Đã chọn rõ `status-draft` hoặc `excel-commit`; nếu prompt cũ không chỉ rõ thì dùng `excel-commit`
- [ ] Tiếng Việt (cột B) có đầy đủ dấu
- [ ] Color tag đã áp dụng đúng theo rule (placeholder, tên riêng)
- [ ] Nếu thêm color tag mới, đã kiểm tra `Name` trong UI `.json`: `text_` thì tự áp dụng; prefix khác thì đã hỏi user
- [ ] Không dùng riêng tên property JS làm evidence; nếu không trace được UI `.json`, đã report và chưa tự thêm tag

### `status-draft`

- [ ] Có `dev-status.md`, key, text VI và ghi chú cho từng entry
- [ ] **Đã chạy reuse check theo nội dung** trên `lang_vi.json` cho mọi entry chưa đánh `reuseExisting`, không chỉ grep tên key
- [ ] Key reuse đã được thay trong code, và placeholder/color tag trong code khớp text thật của key đó
- [ ] Bảng chia 2 section: key reuse (`N/A`) ở trên, key mới (`⬜`) ở dưới
- [ ] Mọi key mới đã được thêm text vào `res/localize/lang_vi.json`
- [ ] **Không** sửa/xoá/gộp bất kỳ key cũ nào; đã đếm lại số dòng từng key trước–sau khi ghi
- [ ] Diff của `lang_vi.json` chỉ gồm key mới của task; line ending giữ nguyên
- [ ] Mọi `fr.Localization.text("...")` trong code feature đều tra ra text trong `lang_vi.json`
- [ ] Chỉ dùng `reuseExisting: true`/`N/A` khi đã verify key có sẵn
- [ ] Merge theo key, không append row trùng
- [ ] Row `N/A` được xử lý trước và không bị tự đổi thành `⬜`
- [ ] Chỉ đổi `✅` thành `⬜` khi chính text VI thay đổi
- [ ] Giữ nguyên row `N/A` của key dùng lại
- [ ] Không xóa ghi chú cũ khi merge nơi sử dụng mới
- [ ] Không tạo section Localization thứ hai khi gặp schema legacy
- [ ] Không đọc/ghi/check lock Excel và không sửa `lang_*.json`
- [ ] Đọc lại bảng sau khi sửa để verify row và trạng thái

### `excel-commit`

- [ ] Đã đọc toàn bộ [references/excel-commit.md](references/excel-commit.md)
- [ ] Nếu source là `dev-status.md`, chỉ lấy dòng `Excel = ⬜` trừ khi user yêu cầu khác
- [ ] Phân loại mỗi row `⬜` là add mới, đã sync, hoặc update existing trước khi ghi
- [ ] Check duplicate key ở cột A trước khi add
- [ ] `mm` (D), `thai` (E), `cn` (G) đã dịch — không để trống chờ translator
- [ ] `cn2` (H) là bản phồn thể của `cn`, không để trống
- [ ] `es` (F), `ru` (I), `in` (J), `id` (K), `tr` (L) dùng tiếng Anh
- [ ] Không có ô nào trong 12 cột bị bỏ trống khi verify
- [ ] Xuống dòng viết bằng `\n` (2 ký tự), **không** có LF/CR thật trong ô — verify bằng cách quét `[char]10` / `[char]13`
- [ ] Trước khi ghi Excel, đã check không có lock file `~$language_main.xlsx`
- [ ] Ghi `.xlsx` bằng Excel COM, không sửa trực tiếp OOXML/ZIP package
- [ ] Không ghi đè dữ liệu cũ khi chèn giữa (dùng Insert + ShiftDown)
- [ ] Save file sau khi thêm
- [ ] Verify bằng cách đóng workbook rồi mở lại bằng Excel COM read-only
- [ ] Nếu source là `dev-status.md`, update `Excel` → `✅` chỉ cho key đã verify thành công
