# Reference — Report Format

Reference bắt buộc cho `dev-art`. Đọc toàn bộ file này trước khi in báo cáo sau sync node tree
và sau khi implement.

Format báo cáo là **giao diện giữa agent và user**: user reply `OK A1 A2`, `skip B1`, `detail B2`
dựa vào mã item trong đó. Mã sai format là lệnh của user không khớp. Rule quyết định (safe sync
vs needs confirm, các bước audit) nằm trong `SKILL.md` — reference này chỉ là khuôn.

Các điểm không được bỏ dù đã đọc reference:

- Mã item: `A{n}` cho `[Confirmed]`, `B{n}` cho `[Candidate]` / `[Low-confidence]`,
  `C{n}` cho case user bổ sung qua `add:`. Không trộn nhóm.
- Mỗi item `B{n}` phải kết bằng **một câu hỏi yes/no hoặc lựa chọn rõ**.
- Phần **Cách reply ngắn** luôn là phần cuối cùng của report.
- Report sau implement chỉ liệt kê đúng các mã đã confirm; có dòng **Chưa verify runtime** khi không chạy được.

---

## Báo cáo sau sync node tree

1. **Scope đã scan**
   - Ghi ngắn feature/folder/list UI đã scan.
   - Không liệt kê quá dài nếu không cần.
2. **Đã thực hiện**
   - Ghi rõ node tree đã sync vào file JS nào.
   - Nếu không có thay đổi node tree, ghi rõ đã đối chiếu và không cần sửa.
3. **Đã check / chưa cần sửa**
   - Chỉ tóm tắt ngắn để user biết đã check, không mở rộng thành log dài.
4. **Đề xuất sửa tiếp**
   - Đặt gần cuối report.
   - Chỉ liệt kê các item thật sự cần hành động.
   - Mỗi item có mã ngắn để user confirm, ví dụ `A1`, `A2`, `B1`.
   - Ghi rõ action: `bind node`, `reload localize texture`, `reload state texture`, `bỏ qua`, hoặc `cần user xác nhận`.
5. **Cần confirm**
   - Đặt ngay sau đề xuất sửa tiếp.
   - Gom riêng những item chưa chắc, `Candidate` hoặc `Low-confidence`.
   - Mỗi item phải có câu hỏi yes/no hoặc lựa chọn rõ ràng.
6. **Cách reply ngắn**
   - Đây là phần cuối report.
   - Luôn kết report bằng hướng dẫn reply ngắn, ví dụ:
     - `OK A1 A2` = làm các item đó
     - `OK all confirmed` = làm toàn bộ item đã chắc chắn
     - `skip B1` = bỏ item đó
     - `add: node X dùng texture Y theo state Z` = user bổ sung case agent chưa đề xuất
     - `detail B1` = giải thích thêm item đó

Format đề xuất:

```text
Kết quả /dev-art: {Feature}

Scope đã scan:
- UI JSON: ...
- UI JS: ...
- Textures: ...

Đã thực hiện:
- Sync node tree: {file JS} ...

Đã check, chưa cần sửa:
- Localize texture ... đã có code reload.
- State texture ... đã có code reload.

Đề xuất sửa tiếp:
- A1 [Confirmed] {file}: {node} -> {action cụ thể}
- A2 [Confirmed] {file}: {node} -> {action cụ thể}

Cần bạn confirm:
- B1 [Candidate] {file}: {node}
  Lý do nghi ngờ: ...
  Đề xuất: ...
  Hỏi: Có chuyển node này theo hướng ... không?
- B2 [Low-confidence] ...

Bạn có thể reply ngắn:
- `OK A1 A2`
- `OK all confirmed`
- `skip B1`
- `add: ...`
- `detail B1`
```

---

## Báo cáo sau khi implement

Ngắn, đúng format:

```text
Đã implement:
- A1: ...
- B2: ...

Files:
- path/to/File.js

Verify:
- node --check ...
- rg ...

Chưa verify runtime: ...
```
