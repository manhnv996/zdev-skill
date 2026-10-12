---
name: dev-art
description: Use when integrating BidaMobile Cocos2d-x JS art/UI resources: syncing Cocos Studio .json node trees, binding renamed/new nodes, updating asset paths, localized text images, texture state mapping, or visual-only asset/visibility changes.
---

# dev-art - BidaMobile Art Integration

Skill này dùng cho phase ghép art/cập nhật UI sau khi logic tính năng đã có hoặc đang được chỉnh theo design mới.

## Boundary với dev-feature

Dùng `dev-art` cho thay đổi art/resource/node tree/texture/visibility mang tính hiển thị.

Nếu task cần runtime behavior hoặc logic đáng kể như layout algorithm, TableView behavior, progress calculation, lifecycle reload, util/module/cmd/config/data flow:
- Dùng `dev-feature` Phase B Lightweight Mode.
- Có thể dùng `dev-art` trước để audit/sync node tree nếu task cũng liên quan `.json` hoặc asset.

## Operating Modes

Xác định mode từ prompt trước khi sửa file:

- **Default sync mode**: dùng khi user nói chung như "dùng dev-art cho feature X", "ghép art X", "update UI X". Được phép làm safe node-tree sync trước, sau đó dừng báo các proposal cần confirm.
- **Audit-only mode**: dùng khi user nói "chỉ audit", "chưa sửa", "review art", "xem cần làm gì". Không sửa file. Chỉ scan JSON/JS/resource và báo proposal.
- **Confirmed proposal mode**: dùng sau khi user đã confirm item proposal. Chỉ implement đúng các item đã được confirm.

Nếu prompt đã đủ feature path/UI JSON folder thì không hỏi lại scope. Nếu thiếu thông tin bắt buộc thì hỏi ngắn gọn trước khi scan.

## Safe Sync vs Needs Confirm

Trong default sync mode, được implement ngay các thay đổi safe sync:

- Thêm/xóa/sửa field JS theo node tree rõ ràng trong Cocos Studio `.json`.
- Sửa field name khi node đã rename rõ trong `.json`.
- Cập nhật parent path/binding để `syncAllChild` map đúng node hiện có.
- Bind node mới nhưng chưa gắn logic mới nếu hành vi chưa rõ.
- Rà lại `Utility.setTextBtn*` cho text trong `btn_*` khi texture nút đổi (xem Bước 2).

Phải dừng và đưa vào proposal để user confirm trước khi implement:

- Node mới cần logic gameplay/server/config/data flow.
- Mapping texture theo state chưa chắc chắn.
- Ảnh text nghi là localize nhưng base path/type chưa rõ.
- Button/touch handler/hành vi click mới.
- Show/hide/popup/module wiring vượt ngoài đồng bộ art/node tree.

Trong audit-only mode, kể cả safe sync cũng chỉ report, không sửa file.

## Proposal Loop

Sau default safe sync hoặc audit-only scan, báo theo 2 phần:

- **Phase A - Safe Sync**: đã làm gì, hoặc "would do" nếu audit-only.
- **Phase B - Proposals**: danh sách item cần confirm, ví dụ `A1`, `A2`, `B1`, kèm file/GUI/flow, lý do, risk, và action dự kiến.

Nếu user reply `OK A1 A2` thì implement đúng các item đó. Nếu user reply thêm/bỏ/đổi item hoặc nói "nên thêm action này ở flow kia", cập nhật lại danh sách proposal rồi hỏi confirm lại; không implement ngay trên cùng reply đó.

Nguyên tắc chung:
- Đọc yêu cầu hiện tại trước, chỉ hỏi lại nếu thiếu đường dẫn feature hoặc folder UI JSON.
- Ưu tiên giữ logic hiện có, chỉ sync node tree, asset binding, visibility/state và các hook data cần thiết theo thay đổi design.
- Không rename node trong file `.json` nếu user không yêu cầu; code JS phải follow tên node design đang cung cấp.
- Khi sửa file JS, tuân thủ convention project: dùng `// #region` / `// #endregion` cho các nhóm logic rõ ràng.
- Dùng `rg` để tìm file/node; dùng parser JSON hoặc tool đọc JSON khi cần lấy cấu trúc, tránh regex thô cho node tree phức tạp.

## Bước 0: Xác định scope

Cần xác định 3 thông tin:

1. Tên module/feature, ví dụ `royalstickcollection`.
2. Folder UI JSON, mặc định thường là `res/content/{feature}/`.
3. Danh sách UI cần sync, hoặc nếu user nói "toàn bộ folder" thì scan tất cả `.json` trong folder đó.

Nếu user đã cung cấp đủ thông tin trong prompt/IDE context thì bắt đầu luôn, không hỏi lại.

## Output sau khi sync node tree

Trong default sync mode, flow có một hướng: sync node tree an toàn trước, sau đó report các đề xuất còn lại để user confirm. Nếu user yêu cầu audit-only thì không sửa file, chỉ báo phần "would do" và proposal.

Khi report, không trả output dạng liệt kê dài thuần túy. Report phải có trọng tâm quyết định. Đặt phần user cần hành động ở cuối hoặc gần cuối report, để user dễ reply.

Cấu trúc 6 phần và format đầy đủ nằm trong [references/report-format.md](references/report-format.md) —
**bắt buộc đọc toàn bộ** trước khi in báo cáo.

Các guard không được bỏ qua dù đã đọc reference:

- Mã item: `A{n}` cho `[Confirmed]`, `B{n}` cho `[Candidate]` / `[Low-confidence]`, `C{n}` cho case user bổ sung.
- Mỗi item `B{n}` kết bằng một câu hỏi yes/no hoặc lựa chọn rõ.
- Phần **Cách reply ngắn** luôn là phần cuối report — user reply dựa vào mã item nên format sai là lệnh không khớp.

Nếu user reply bằng mã item, chỉ thực hiện đúng các item đó.

Nếu user bổ sung case mới bằng `add: ...`, "cần thêm ...", hoặc mô tả một node/texture/state chưa nằm trong audit:

1. Không sửa code ngay.
2. Phân tích lại case mới dựa trên UI JSON/code/texture liên quan.
3. Chuẩn hóa thành item mới có mã riêng, ví dụ `C1`.
4. Gửi lại đề xuất ngắn:
   - Node/file liên quan
   - Action sẽ sửa
   - Lý do
   - Rủi ro/note nếu có
5. Hỏi user confirm bằng `OK C1` hoặc `skip C1`.

Chỉ sửa code cho case user bổ sung sau khi user confirm mã item mới.

## Implement sau khi user confirm

Khi user reply `OK ...` cho các item đề xuất:

1. Chỉ sửa đúng các item được confirm. Không tự tiện sửa thêm candidate khác dù thấy tiện.
2. Nếu item phụ thuộc nhau, làm theo thứ tự an toàn:
   - Bind/sync node field trước
   - Thêm helper nhỏ nếu code hiện tại đã có pattern tương tự
   - Thêm reload texture/localize/state
   - Thêm data binding/visibility/touch handler liên quan
3. Với ảnh text localize:
   - Local texture dùng `fr.Localization.resByLang(basePath, false, true)` và `ccui.Widget.LOCAL_TEXTURE`.
   - Plist/module cũ dùng `fr.Localization.resByLang(baseKey, true)` và `ccui.Widget.PLIST_TEXTURE`.
   - Đặt code vào hàm localize/update UI có sẵn nếu phù hợp; tránh tạo flow mới nếu class đã có pattern.
4. Với texture đổi theo trạng thái:
   - Ưu tiên dùng helper state/suffix hiện có.
   - Nếu cần helper mới, đặt tên rõ nghĩa và scope nhỏ trong util/class liên quan.
   - Không trộn với localize nếu texture không đổi theo ngôn ngữ.
5. Với node tree:
   - Field name phải theo convention class hiện có.
   - Không rename node JSON.
   - Nếu node mới chưa dùng ngay nhưng cần bind để art đúng flow, vẫn bind và ghi rõ trong kết quả.
6. Verify sau khi sửa:
   - Chạy `node --check` cho file JS đã sửa nếu phù hợp.
   - Dùng `rg` kiểm tra không còn reference node/texture cũ bị thay thế ngoài ý muốn.
   - Nếu không chạy được runtime, nói rõ chưa verify runtime.

Output sau implement ngắn, theo format **Báo cáo sau khi implement** trong [references/report-format.md](references/report-format.md).

## Bước 1: Cập nhật node tree từ folder UI JSON

Mục tiêu của bước này là đồng bộ code JS với node tree mới của art/design.

Thực hiện:

1. Liệt kê các file `.json` trong folder UI.
2. Map file JSON với class JS tương ứng theo tên file, ví dụ:
   - `RoyalStickCollectionNodeAccumulateSlot.json`
   - `src/game/royalstickcollection/ui/RoyalStickCollectionNodeAccumulateSlot.js`
3. Đọc node tree của từng JSON cần sync:
   - Tên node
   - Loại node/class widget
   - Parent path
   - Sprite/font/resource path quan trọng
   - Visibility/default state nếu có ý nghĩa gameplay
4. So sánh với JS hiện tại:
   - Field nào đang bind nhưng JSON đã đổi tên/xóa
   - Node mới nào cần thêm field
   - Parent path nào thay đổi làm `getChildByName`/`syncAllChild` sai
   - Node nào chuyển vai trò, ví dụ label hiện point thành label hiện level, icon next/current
5. Cập nhật JS bind node tree:
   - Thêm/xóa/sửa field theo node mới
   - Giữ style bind node sẵn có của project/class đó
   - Dùng convention đã có từ `dev-feature`: UI có `.json` thì `extends BaseScreen`, gọi `syncAllChild(...)`, field phải khai báo trước để được bind.
   - Không đọc lại `BaseScreen.js` trong happy path. Chỉ đọc khi file/class override `syncAllChild`, binding thực tế khác convention, hoặc gặp node name lạ không chắc mapping.
   - Mapping mặc định: node dạng 2 phần như `image_BgList`, `label_Name`, `btn_Close` -> field `imageBgList`, `labelName`, `btnClose`.
   - Nếu node name có nhiều hơn một dấu `_`, kiểm tra style hiện có trong file hoặc `BaseScreen` trước khi tự suy đoán field name.
   - Nếu có helper sync node riêng trong class/module thì dùng helper đó, không tạo pattern mới khi không cần.
6. Cập nhật data binding tới node mới:
   - Label set string/default text
   - Sprite/icon set texture/path
   - Visibility theo state
   - Tooltip/touch handler nếu node mới có role tương tác

Chỉ code logic data tới mức cần thiết để UI mới hiện đúng. Nếu thay đổi ảnh hưởng protocol/config/flow lớn, dừng lại và đề xuất plan ngắn trước khi sửa sau.

Node tree sync là bước bắt buộc của default sync mode trong phase ghép art:

- Luôn cập nhật node tree vào JS trong lượt chạy default sync mode.
- Trong audit-only mode, chỉ report node tree sẽ cần sync, không sửa JS.
- Không cần hỏi confirm riêng cho các thay đổi bind node rõ ràng như thêm field node mới, đổi field theo node đã rename, hoặc cập nhật parent path để `syncAllChild`/binding đúng với JSON mới.
- Nếu node mới kéo theo logic data/protocol/flow chưa rõ, vẫn có thể bind node trước, nhưng phần logic chưa rõ phải đưa vào `Cần confirm`.
- Khi report sau khi đã sửa node tree, ghi rõ node nào đã sync và file JS nào đã cập nhật.

## Bước 2: Rà ảnh text localize trong textures

Sau khi đã có danh sách UI JSON cần sync, rà folder textures dùng cho feature.

Đường dẫn mặc định:

- Nếu UI JSON ở `res/content/{feature}/` thì textures thường ở `res/content/{feature}/textures/`.
- Nếu user đưa folder khác, dùng folder `textures` nằm cùng root với list UI JSON đó.

Thực hiện:

1. Scan toàn bộ `.png` trong folder textures của feature.
2. Gom nhóm ảnh text localize theo pattern:
   - `xxx.png` = tiếng Việt/default
   - `xxx_en.png` = tiếng Anh
   - `xxx_th.png` = tiếng Thái
   - `xxx_mm.png` = tiếng Myanmar
3. Chỉ xem là ảnh text localize chắc chắn khi có ít nhất một biến thể ngôn ngữ đi kèm base image.
4. Tạo map base path để dùng với `fr.Localization.resByLang`:
   - File: `res/content/monthlygratitude/textures/popup/mg_popup_title.png`
   - Base path dùng trong code: `"content/monthlygratitude/textures/popup/mg_popup_title"`
   - Không truyền extension `.png`
   - Không truyền suffix `_en`, `_th`, `_mm`
5. Duyệt lại list UI JSON và tìm node đang dùng các ảnh trong map localize:
   - Check các field resource như `FileData.Path`, `NormalFileData.Path`, `PressedFileData.Path`, `DisabledFileData.Path`, `BackGroundData.Path` và các field path tương tự.
   - Ghi lại UI file, node name, parent path, resource path đang dùng.
6. Đề xuất danh sách node cần chuyển sang runtime localize:
   - Node nào cần bind field trong JS nếu chưa có
   - Class JS nào cần thêm reload texture
   - Base path sẽ truyền vào `fr.Localization.resByLang`

Khi chuyển code:

- Không sửa JSON chỉ để đổi path localize; JSON vẫn có thể giữ ảnh default để preview trong Cocos Studio.
- Reload texture trong JS theo pattern sẵn có của class, ví dụ:

```js
Utility.reloadImageTexture(
    this.imageTitle,
    fr.Localization.resByLang("content/monthlygratitude/textures/popup/mg_popup_title", false, true),
    ccui.Widget.LOCAL_TEXTURE
);
```

- Nếu class đã có hàm update ngôn ngữ/localize thì đặt vào đó; nếu chưa có, đặt ở init/setup UI phù hợp.
- Nếu node là button hoặc có nhiều state texture, kiểm tra API reload tương ứng thay vì chỉ dùng `Utility.reloadImageTexture` cho `ImageView`.
- Không hardcode trực tiếp `_en.png`, `_th.png`, `_mm.png` trong JS.
- Nếu node đã được xử lý bằng `fr.Localization.resByLang` rồi thì không thêm trùng.

Trường hợp dùng lại ảnh text localize từ plist/module cũ:

- Không scan rộng toàn bộ plist/module cũ trước. Chỉ check nhẹ từ chính UI JSON đang sync.
- Nếu node có `FileData.Type = PlistSubImage` và `Path` có dạng `xxx_en.png`, `xxx_th.png`, hoặc `xxx_mm.png`, strip suffix ngôn ngữ và `.png` để lấy `baseKey`.
- Nếu resource có dấu hiệu là ảnh text như `text`, `title`, `guide`, `logo`, hoặc có prefix module cũ như `rh_`, `th_`, dùng `rg` exact `baseKey` trong code để xác nhận pattern cũ.
- Nếu thấy code cũ đã dùng `fr.Localization.resByLang("baseKey", true)` thì đề xuất bind node và reload bằng `PLIST_TEXTURE`, ví dụ:

```js
Utility.reloadImageTexture(
    this.imageTitle,
    fr.Localization.resByLang("rh_guide_text_title", true),
    ccui.Widget.PLIST_TEXTURE
);
```

- Chỉ thêm xử lý dạng này khi có bằng chứng từ UI JSON/code cũ hoặc user xác nhận node dùng lại asset cũ.

Trường hợp texture đổi theo trạng thái:

- Trong lúc scan folder textures, gom nhóm các ảnh có cùng prefix và suffix biến thiên:
  - Ví dụ confirmed: `mg_task_bg_active.png`, `mg_task_bg_done.png`, `mg_task_bg_expire.png`
  - Ví dụ confirmed: `mg_task_state_icon_active.png`, `mg_task_state_icon_done.png`, `mg_task_state_icon_expire.png`
  - Ví dụ low-confidence: `mg_guide_step_1.png`, `mg_guide_step_2.png`, `mg_guide_step_3.png` vì có thể là nội dung nhiều trang, không phải state.
- Danh sách suffix dưới đây chỉ là gợi ý ưu tiên, không phải whitelist cứng. Nếu texture có cùng prefix, có nhiều biến thể, và UI JSON/code cho thấy dùng để đổi trạng thái thì vẫn phải report dù suffix không nằm trong danh sách.
- Các suffix trạng thái phổ biến:
  - `active`, `done`, `expire`, `expired`
  - `normal`, `select`, `selected`
  - `enable`, `enabled`, `disable`, `disabled`
  - `lock`, `locked`, `unlock`, `unlocked`
  - `claim`, `claimed`, `ready`
  - `open`, `opened`, `close`, `closed`
  - `complete`, `completed`, `inactive`
- Với suffix lạ, không tự bỏ qua. Đánh dấu `Candidate` hoặc `Low-confidence`, ghi rõ lý do nghi ngờ và chờ user xác nhận trước khi sửa code.
- Sau khi có group nghi vấn, duyệt UI JSON để xem node nào đang dùng một biến thể default, ví dụ `textures/mg_task_bg_active.png`.
- Dùng `rg` trong JS tương ứng để tìm:
  - Prefix texture, ví dụ `mg_task_bg_`
  - Biến `suffix`, `state`, `status`, hoặc helper như `getTextureStateSuffix`
  - Các lệnh `Utility.reloadImageTexture` / `loadTexture`
- Phân loại khi report:
  - **Confirmed:** texture group có suffix trạng thái, JSON dùng một biến thể, JS đã có hoặc rõ ràng cần state/suffix để đổi texture.
  - **Candidate:** texture group có suffix trạng thái và JSON dùng một biến thể, nhưng JS chưa có logic state rõ ràng. Đề xuất trước, chờ user confirm.
  - **Low-confidence:** suffix là số hoặc tên không rõ nghĩa. Chỉ đề xuất nếu node/code cho thấy đó là state.
- Khi đề xuất code, giữ pattern local texture, ví dụ:

```js
var suffix = MonthlyGratitudeUtil.getTextureStateSuffix(state);
var BASE = "content/monthlygratitude/textures/";
Utility.reloadImageTexture(this.imageBg2, BASE + "mg_task_bg_" + suffix + ".png", ccui.Widget.LOCAL_TEXTURE);
```

- Không nhầm texture state với ảnh text localize. Texture state dùng `LOCAL_TEXTURE` và không gọi `fr.Localization.resByLang` trừ khi bản thân texture cũng là ảnh text theo ngôn ngữ.

### Trường hợp texture nút đổi — rà lại màu chữ trong button

Ghép art hay làm đổi texture của `btn_*`: từ nút common sang nút riêng của feature, ngược lại, hoặc đổi sang màu common khác. Khi đó lời gọi `Utility.setTextBtn*` mà phase code đã đặt trong `ctor` có thể thành sai màu hoặc thừa — **phải rà lại một lượt kể cả khi node tree không đổi**.

Với mỗi node text nằm trong `btn_*`, đối chiếu 2 điều kiện (bảng tra màu + các bẫy: xem `dev-feature/reference-ui-patterns.md`, section "Màu chữ trong button"):

1. Nút có dùng texture `content/common/textures/common_btn_*` không?
2. Node text còn ở mặc định trong `.json` không (`CColor` = `(255,255,255)`, không `OutlineEnabled`/`ShadowEnabled`)?

| `.json` sau khi ghép art | Code hiện có | Hành động |
|---|---|---|
| Thỏa cả 2 điều kiện | chưa gọi | thêm `setTextBtn*` theo màu nút |
| Thỏa cả 2, nút đổi sang màu common khác | gọi sai màu | đổi sang hàm đúng màu |
| Nút đổi sang texture riêng của feature | đang gọi | **xóa** lời gọi — art tự canh màu |
| `.json` đã set màu/outline cho node text | đang gọi | **xóa** lời gọi — chủ ý của designer |

Cả 4 case đều suy được từ `.json` nên thuộc safe sync, không cần hỏi confirm. Chỉ đưa vào `Cần confirm` khi 2 điều kiện mâu thuẫn nhau (vd nút vẫn là common nhưng art đã set outline riêng cho text).

## Bước 3: Kiểm tra asset/resource

Sau khi sync node:

- Kiểm tra resource path trong JSON có tồn tại trong repo.
- Nếu asset thuộc nhóm download/dynamic asset, check các util liên quan như `VipAssetUtil`, `TournamentAssetUtil` hoặc util feature hiện có.
- Không sửa asset util nếu chưa có bằng chứng asset mới cần preload/download.

## Bước 4: Verify

Tối thiểu:

- Chạy `node --check` cho các file JS đã sửa nếu file có thể parse độc lập.
- Dùng `rg` để đảm bảo không còn reference tới node cũ bị đổi tên.
- Dùng `rg` để kiểm tra code không còn hardcode trực tiếp các ảnh text localize dạng `_en.png`, `_th.png`, `_mm.png` cho những node vừa chuyển.
- Nếu có texture `btn_*` thay đổi, `rg "setTextBtn"` trong feature rồi đối chiếu lại với `.json` theo bảng ở Bước 2.
- Nếu có dev server/engine flow sẵn có và user yêu cầu, chạy manual smoke theo màn hình đó.

Khi báo kết quả:

- Liệt kê file đã sửa.
- Nếu có node đổi tên, ghi rõ mapping cũ -> mới.
- Ghi rõ những điểm chưa verify được trong runtime.
