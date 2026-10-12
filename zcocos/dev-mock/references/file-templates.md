# Reference — Mock File Templates

Reference bắt buộc cho `dev-mock`. Đọc toàn bộ file này trước khi tạo hoặc sửa
`mock-current.json` / `{Feature}Mock.js`.

Đây là source chuẩn cho cấu trúc 2 file runtime. Các rule quyết định (3 mục đích, 4 tầng ưu
tiên, quy ước `flowId`, chọn field cho `data`) nằm trong `SKILL.md` — reference này chỉ là
khuôn để copy.

Các điểm không được bỏ dù đã đọc reference:

- `run(caseId, flowId, options)` **không đổi chữ ký** — `DevMockLoader` chỉ gọi `mock.run(...)`,
  và `Cheat.js` là file dùng chung với mock của feature khác. Đọc `dataId` từ `options`.
- `_pick()` phải đủ **4 tầng** theo đúng thứ tự, và dùng `!= null` chứ không phải truthy.
- Mỗi `cmdReceive*` trong Module phải có đúng **1 case** trong `runFlow`, đặt đúng tên handler.
- `mock-current.json` phải giữ **dòng trống phân nhóm param**; không generate bằng `json.dumps`.

---

## Template — `mock-current.json`

Giữ dòng trống phân nhóm param; mất nó là tester nhìn một khối liền khó tìm. **Không** generate file này bằng `json.dumps` — nó chỉ giữ dữ liệu, không giữ bố cục.

```json
{
  "feature": "{feature}",

  "dataId": "running",
  "flowId": "cmdReceiveXxxUpdatePoint",

  "dataOverride": false,
  "data": {
    "fieldA": 5,
    "fieldB": 248000,

    "fieldC": 48
  },

  "_help": "3 truc: dataId -> flowId, cong them co dataOverride. Sua xong save roi bam phim cheat. dataId chon mot BO DATA hoan chinh. Object data CHI co tac dung khi dataOverride = true. Key bat dau bang _ chi la ghi chu.",

  "_dataOverrideNote": "false (mac dinh) = dung nguyen bo data cua dataId. true = moi field dang co trong object data se GHI DE len bo do - muon chi ghi de vai field thi xoa bot cac field khac.",

  "_flowForceNote": "Mot so flow co data do BAN CHAT cua no quy dinh san, thang ca data lan dataId va KHONG ghi de duoc. Xem {Feature}Mock.FLOW_FORCE. Log se in ra moi khi co ep.",

  "_validDataIds": [
    "running",
    "running_variantA",

    "ended",
    "ended_variantB"
  ],

  "_validFlowIds": {
    "1_receive_packet": [
      "cmdReceiveXxxLoadInfo",
      "cmdReceiveXxxUpdatePoint"
    ],

    "2_data_only": [
      "data"
    ],

    "3_user_flow": [
      "flow_showMain",
      "flow_resultWin"
    ]
  },

  "_flowNotes": {
    "1_receive_packet": "Ten = dung ten handler trong {Feature}Module. Mock dung goi tin gia tu data roi goi thang handler do.",
    "2_data_only": "Chi set state, khong gui goi tin, khong mo GUI.",
    "3_user_flow": "Can action cua user hoac mo GUI de xem nhom data hien ra sao."
  },

  "_dataIdNotes": {
    "running": "...",
    "ended": "..."
  },

  "_dataNotes": {
    "fieldA": "...",
    "fieldB": "..."
  },

  "_dataNotesAdvanced": "Cac field do dataId quyet dinh nen khong de trong data cho do roi: ... Van ghi de duoc - them tay vao object data roi bat dataOverride.",

  "_reloadScriptNote": "Them \"reloadScript\": true o cap ngoai cung khi vua sua {Feature}Mock.js ma app dang chay. Xong nho bo di.",

  "_knownLimitations": []
}
```

## Template — `{Feature}Mock.js`

```js
var {Feature}Mock = (typeof {Feature}Mock !== "undefined") ? {Feature}Mock : {};

// #region Settings
{Feature}Mock.DEFAULT_DATA_ID = "running";
{Feature}Mock.DEFAULT_FLOW_ID = "flow_showMain";

//gia tri nen, dung khi nhom data va object data deu khong khai bao
{Feature}Mock.DEFAULTS = {
    fieldA: 5,
    fieldB: 248000,
};
// #endregion

// #region Flow Force
/**
 * Data ma BAN CHAT cua flow da quy dinh san - thang ca object data trong JSON.
 * Chi dat gia tri CO DINH o day; dieu chinh co dieu kien giu trong ham cua flow.
 */
{Feature}Mock.FLOW_FORCE = {
    "cmdReceiveXxxBuyItem": { hasItem: 1 },      //mua thanh cong thi phai co item
    "flow_showBuyItem":     { hasItem: 0 },      //dang co item thi popup khong mo
};
// #endregion

// #region Data Groups
/**
 * Moi nhom la MOT BO DATA hoan chinh. Nhom chi ghi field KHAC DEFAULTS - phan con lai
 * tu dong lay tu DEFAULTS, nen them nhom moi khong phai chep lai het.
 */
{Feature}Mock.DATA_GROUPS = {
    "running": { isEnd: false },
    "running_variantA": { isEnd: false, fieldA: 0 },
    "ended": { isEnd: true },
};
// #endregion

// #region Public API
/**
 * DevMockLoader goi mock.run(config.caseId, config.flowId, config) - tham so dau van la
 * caseId cu, nen doc dataId tu config truoc de khong phai sua Cheat.js (file dung chung).
 */
{Feature}Mock.run = function (caseId, flowId, options) {
    options = options || {};
    var dataId = options.dataId || caseId || {Feature}Mock.DEFAULT_DATA_ID;
    flowId = options.flowId || flowId || {Feature}Mock.DEFAULT_FLOW_ID;

    if ({Feature}Mock.applyData(dataId, options, flowId) == null) return;
    {Feature}Mock.runFlow(flowId, options);
};

{Feature}Mock.applyData = function (dataId, options, flowId) {
    var group = {Feature}Mock.DATA_GROUPS[dataId] || {Feature}Mock.DATA_GROUPS[{Feature}Mock.DEFAULT_DATA_ID];
    if (group == null) {
        {Feature}Mock._log("missing dataId: " + dataId);
        return null;
    }
    if (!{Feature}Mock._checkDependencies()) return null;

    var force = {Feature}Mock.FLOW_FORCE[flowId] || null;
    var cfg = {Feature}Mock._resolve(options, group, force);
    if (force != null) {
        {Feature}Mock._log("flow " + flowId + " ep san: " + JSON.stringify(force)
            + " (thang ca data trong JSON)");
    }

    //... set state vao Util/Model tu cfg ...
    return group;
};

{Feature}Mock.runFlow = function (flowId, options) {
    switch (flowId) {
        //--- 1. GIA LAP GOI TIN. Ten case = ten handler trong Module ---
        case "cmdReceiveXxxLoadInfo":
            {Feature}Mock.packetLoadInfo(options);
            break;

        //--- 2. CHI SET DATA ---
        case "data":
            {Feature}Mock._log("chi set data - khong gia lap goi tin, khong mo GUI");
            break;

        //--- 3. FLOW can action user / mo GUI ---
        case "flow_showMain":
            {Feature}Mock.showMain();
            break;
        default:
            {Feature}Mock._log("unknown flowId: " + flowId);
            break;
    }
    {Feature}Mock._log("flowId=" + flowId);
};
// #endregion

// #region Packet Mocks - gia lap GOI TIN server ve
/**
 * Moi ham lam dung mot viec: dung goi tin gia tu data roi goi THANG handler that.
 * Khong chep lai buoc nao cua handler - chep la se drift khi handler doi.
 */
{Feature}Mock.packetLoadInfo = function (options) {
    {Feature}Mock._withModule(function (mod) {
        mod.cmdReceiveXxxLoadInfo({Feature}Mock._fakeCmd({ /* field handler doc */ }));
        {Feature}Mock._log("LOAD_INFO gia -> ...");
    });
};
// #endregion

// #region Flow Helpers
//cac flow nhieu buoc: mo GUI, delay, roi tra response
// #endregion

// #region Helpers
/** Gop 4 tang: flow ep san -> data trong JSON -> nhom data da chon -> DEFAULTS */
{Feature}Mock._resolve = function (options, group, force) {
    var cfg = {};
    for (var k in {Feature}Mock.DEFAULTS) {
        cfg[k] = {Feature}Mock._pick(options, k, group, force);
    }
    return cfg;
};

/**
 * Dung "!= null" chu khong phai truthy: 0 va false deu la gia tri co nghia nen khong
 * duoc roi xuong tang duoi.
 */
{Feature}Mock._pick = function (options, key, group, force) {
    if (force != null && force[key] != null) return force[key];
    if (options != null && options.dataOverride === true) {
        if (options.data != null && options.data[key] != null) return options.data[key];
        if (options[key] != null) return options[key];
    }
    if (group != null && group[key] != null) return group[key];
    return {Feature}Mock.DEFAULTS[key];
};

/** Goi tin gia du dung de chay qua handler that: getError() + cac field handler doc */
{Feature}Mock._fakeCmd = function (fields) {
    var cmd = { getError: function () { return ErrorDefine.SUCCESS; } };
    for (var k in fields) cmd[k] = fields[k];
    return cmd;
};

/** Gom lai de cac ham gia lap goi tin khong phai lap lai doan check module */
{Feature}Mock._withModule = function (func) {
    var mod = {Feature}Mock._getModule();
    if (mod == null) {
        {Feature}Mock._log("khong lay duoc {Feature}Module -> bo qua");
        return;
    }
    func(mod);
};

/**
 * ModuleMgr giu module trong var cuc bo nen khong co duong tham chieu cong khai.
 * Lay qua poolCall[PoolFunction.XXX_SHOW_MAIN] - poolCall la bien global cua PoolFunction.js.
 */
{Feature}Mock._getModule = function () {
    if (typeof poolCall === "undefined" || poolCall == null) return null;
    var mod = poolCall[PoolFunction.XXX_SHOW_MAIN];
    if (mod == null || typeof mod.cmdReceiveXxxLoadInfo !== "function") return null;
    return mod;
};
// #endregion
```

Không đổi tên `run`; `DevMockLoader` chỉ gọi `mock.run(...)`.
