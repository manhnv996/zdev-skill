# Reference — UI test mock trên device (Phase 2)

**Chỉ đọc file này khi** prompt của user yêu cầu test mock trên device / dùng panel (icon `M`), hoặc user đã
đồng ý với đề xuất Phase 2 ở cuối output Phase 1. Mặc định `dev-mock` chỉ làm Phase 1 (mock + phím `m` trên win32).

## Hạ tầng đã có sẵn — KHÔNG làm lại cho từng feature

| Phần | Ở đâu | Ghi chú |
|---|---|---|
| Hook gắn icon | `src/base/screen/ScreenMgr.js` → `viewScreen()`: `DevMockLoader.attachPanel(scene)` | 1 dòng, đã có |
| Loader | `src/gamemgr/Cheat.js` → `DevMockLoader.attachPanel` / `getPanelFeatureNames` / `readDefaultConfig` | Chỉ gắn sau khi đăng nhập (bỏ LOGO / LOGIN / LOADING / OFFLINE), live (`SERVER_ID 2`) thoát ngay. Không đọc được `.js` mà có `.jsc` thì `require()` |
| Panel | `simulator/devmock/DevMockPanel.js` | **Dùng chung mọi feature** — đọc config của feature, không có code riêng feature. Không sửa cho 1 feature |
| Đóng gói | `build/dev/*/cdn.json`: `{ "from": "simulator/devmock", "to": "devmock" }` | Đã có ở mọi dev market; `cdn.json` live **không** khai báo |

Panel đọc được cả 2 kiểu config: mới (`dataId` / `_validDataIds` / `_validFlowIds` nhóm / `data` + `dataOverride` /
`_dataIdNotes`) và cũ (`caseId` / `_validCases` / `_validFlows` / param phẳng ở cấp ngoài cùng).

## Bật Phase 2 cho 1 feature — việc cần làm

1. **Bật panel trong index** — `simulator/devmock/devmock-index.json`:
   ```json
   "{feature}": {
     "script": "{feature}/{Feature}Mock.js",
     "exportName": "{Feature}Mock",
     "panel": true
   }
   ```
   Chỉ feature có `"panel": true` mới hiện trong panel; không feature nào bật thì không có icon `M`.
2. **`_dataOptions` trong `mock-default.json`** cho field rời rạc (enum, id, mã lỗi, cờ 0/1) — panel cho
   `◀ ▶` xoay vòng + chạm để chọn trong danh sách. Field số liên tục **không** cần (panel có `− +` + bàn phím số),
   field bool tự xoay true / false. Đặt sau `_dataNotes`, kèm `_dataOptionsNote`:
   ```json
     "_dataOptions": {
       "questId": ["quest_192", "quest_6"],
       "questMode": [1, 3, -1],
       "errorCode": [0, 5, 8, 21, 24, 27]
     },

     "_dataOptionsNote": "Chi dung cho panel tren device (icon M): field co danh sach o _dataOptions thi bam < > de xoay vong qua cac gia tri do; field so khong co danh sach thi bam - +. Phim m tren win32 khong doc key nay.",
   ```
   Giá trị trong danh sách giữ đúng kiểu (số là số, chuỗi là chuỗi) — panel ghép thẳng vào config khi chạy.
3. **Ghi chú `_dataIdNotes`** nên đủ ý trong ~3 dòng — panel hiện tối đa 3 dòng dưới `dataId`, dài hơn thì cắt
   `...` và chạm vào mới xem toàn văn.
4. **Doc tester** `{feature}-mock.md`: thêm mục `## Chạy trên device (panel)` (khuôn bên dưới).
5. Mock JS vẫn theo khuôn Phase 1 (viết kiểu `var` — xem `SKILL.md`). Không thêm gì riêng cho panel.

### Khuôn mục doc tester

```markdown
## Chạy trên device (panel)

Bản dev (`build/dev/<market>`) và win32 có icon tím **`M`** + nút xanh ▶ ở cạnh màn hình, **chỉ sau khi đăng nhập**.
Bản live không có. Feature hiện trong panel nhờ `"panel": true` trong `simulator/devmock/devmock-index.json`.

| Thao tác | Kết quả |
|---|---|
| Kéo `M` | Dời icon; thả ra hít cạnh trái / phải |
| Chạm `M` | Mở / đóng panel (panel mở thì chặn chạm xuống game, chạm ra ngoài panel = đóng) |
| `Mock: ...` ▼ | Chọn feature |
| `flowId` ▼ / `dataId` ▼ | Chọn trong danh sách; dưới `dataId` là ghi chú (chạm để xem hết nếu bị cắt) |
| `dataOverride` | Bật / tắt; field trong `data` chỉ có tác dụng khi ON |
| Field `−` `+` | Số: cộng trừ nhanh; chạm ô giá trị → bàn phím của thiết bị, nhập sai thì giữ giá trị cũ |
| Field `◀` `▶` | Field có `_dataOptions` / true-false: xoay vòng; chạm ô giá trị → danh sách |
| `Reload JS` | Lần chạy kế nạp lại `{Feature}Mock.js` |
| `Reset` | Xoá lựa chọn đã lưu, về giá trị của config |
| `Run` ▶ | Đóng panel rồi chạy |
| Nút ▶ cạnh icon | Chạy lại lựa chọn hiện tại (bấm liên tục cho flow nhiều bước) |

- Lựa chọn lưu trên máy theo feature. Chạy = ghép lựa chọn lên config (`mock-current.json` nếu có, trên device là `mock-default.json`).
- Log `[{Feature}Mock] ...` chỉ hiện ở cuối panel — chạy bằng ▶ cạnh icon thì mở panel ra để xem.
- Sửa mock trên device phải build dev mới (hoặc đẩy CDN dev) — trên win32 vẫn sửa file + bấm `m` như cũ.
```

## Verify

- `node --check simulator/devmock/{feature}/{Feature}Mock.js`; parse `mock-default.json` + `devmock-index.json`.
- Entry index có `"panel": true`; mọi giá trị trong `_dataOptions[field]` cùng kiểu với `data[field]` / param.
- Mock JS không có `const` / `let` / `=>` (nạp bằng `eval` trên SpiderMonkey 33).
- **Win32** (khởi động lại app — `Cheat.js` / `ScreenMgr.js` nằm trong `project.json`): sau khi đăng nhập thấy icon `M`;
  mở panel thấy feature, chọn flow / dataId, `Run` chạy đúng như phím `m`; log có dòng `[DevMockLoader] panel attached`.
- **APK dev** (user build): icon hiện; mock chạy được. Lỗi thì log panel có `eval failed` / `require failed` / `file not found`.

## Giới hạn / lưu ý

- Build từ máy có `mock-current.json` local thì file đó cũng vào gói (gitignore không chặn copy) → panel trên device lấy
  giá trị ban đầu từ đó thay vì `mock-default.json`. Không hỏng gì.
- Field chuỗi không có `_dataOptions` sửa bằng bàn phím chữ; giá trị rỗng không nhận.
- Không chạy được flow cần phím / thao tác ngoài panel mà mock không tự dựng.
- Panel cần thêm khả năng mới → sửa `DevMockPanel.js` **chung cho mọi feature**, giữ kiểu `var` + `function`, test cả
  config kiểu mới lẫn cũ.
