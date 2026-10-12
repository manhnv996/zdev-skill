<#
.SYNOPSIS
    Safety tool cho task delete feature content (BidaMobile Client).
    Thực thi và kiểm chứng removal manifest — KHÔNG tự quyết định xóa gì.

.DESCRIPTION
    4 action theo lifecycle manifest:  planned -> audited -> moved -> verified  (restored khi rollback)

      Audit    Validate manifest, tính bytes + SHA-256, check source/ASTC parity + dependency group.
               REFUSE nếu còn `unresolved`.
      Move     Move đúng file trong `removed` sang <BackupRoot>\<Build>\<relative path>,
               copy manifest + quarantine.patch + chính script vào _meta\.
      Verify   removed vắng trong repo & có trong backup với SHA khớp; retained còn đủ parity.
      Restore  Copy ngược từ backup về repo; nhắc apply lại quarantine.patch.

    Exit code:  0 OK · 1 REFUSE (gate/precondition, không ghi gì) · 2 VERIFY FAIL · 3 IO ERROR

.EXAMPLE
    .\delete_feature_content.ps1 -Action Audit  -Bundle firstpay2021
    .\delete_feature_content.ps1 -Action Move   -Bundle firstpay2021 -DryRun
    .\delete_feature_content.ps1 -Action Verify -Bundle firstpay2021
    .\delete_feature_content.ps1 -Action Restore -Bundle firstpay2021
.NOTES
    File nay PHAI luu UTF-8 WITH BOM. Windows PowerShell 5.1 doc .ps1 khong BOM theo ANSI:
    byte 0x93/0x94 trong UTF-8 tieng Viet bi decode thanh smart quote (U+201C/U+201D) va pha tokenizer.
    Sau khi edit bang tool khac, chay lai:  [IO.File]::WriteAllText(path, text, (New-Object Text.UTF8Encoding $true))
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Audit', 'Move', 'Verify', 'Restore')]
    [string]$Action,

    [Parameter(Mandatory = $true)]
    [string]$Bundle,

    # Repo root — mặc định cwd; refuse nếu không có project.json.
    [string]$RepoRoot = (Get-Location).Path,

    # Nơi chứa <bundle>.json và <bundle>.quarantine.patch.
    [string]$ManifestDir = '',

    [string]$BackupRoot = 'D:\workspace\BidaMobile\client-delete-content-backup',

    # Layer folder trong backup. Mặc định đọc manifest.build.
    [string]$Build = '',

    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = New-Object Text.UTF8Encoding $false } catch {}   # log tieng Viet khong mojibake khi goi tu Bash/Git Bash
Set-StrictMode -Version 1.0

# #region Constants
$EXIT_OK          = 0
$EXIT_REFUSE      = 1
$EXIT_VERIFY_FAIL = 2
$EXIT_IO          = 3

$VALID_MODES      = @('full-folder', 'partial-prune', 'group')   # group: xóa theo nhóm file trong folder dùng chung (animation) — không check folder biến mất, cho phép retained
$TEXTURE_EXTS     = @('.png', '.jpg', '.jpeg', '.pvr', '.pvr.ccz', '.pkm', '.webp', '.astc', '.zst')
$SRC_PREFIX       = 'res/'
$ASTC_PREFIX      = 'res#tcf_astc/'
# #endregion

# #region Output & Exit
function Log([string]$msg)    { Write-Output "[$Action] $msg" }
function Refuse([string]$msg) { Write-Output "[$Action] REFUSE: $msg"; exit $EXIT_REFUSE }
function Fail([string]$msg)   { Write-Output "[$Action] VERIFY FAIL: $msg"; exit $EXIT_VERIFY_FAIL }
function IoFail([string]$msg) { Write-Output "[$Action] IO ERROR: $msg"; exit $EXIT_IO }
# #endregion

# #region Path Helpers
function FullPath([string]$p) { return [System.IO.Path]::GetFullPath($p).TrimEnd('\') }
function NormKey([string]$p)  { return $p.Replace('\', '/').Trim().ToLowerInvariant() }
function RelToRepo([string]$rel)   { return Join-Path $script:RepoRootFull ($rel -replace '/', '\') }
function RelToBackup([string]$rel) { return Join-Path $script:BuildDir     ($rel -replace '/', '\') }
function FileHash([string]$p) { return (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() }
function Now() { return (Get-Date).ToString('yyyy-MM-ddTHH:mm:sszzz') }
function ParentDir([string]$p) { return [System.IO.Path]::GetDirectoryName($p) }   # KHÔNG dùng Split-Path -LiteralPath -Parent: PS 5.1 xung đột parameter set

function Prop($obj, [string]$name, $default) {
    if ($null -eq $obj) { return $default }
    $p = $obj.PSObject.Properties[$name]
    if ($null -eq $p) { return $default }
    return $p.Value
}

# ASTC counterpart: res/<p> <-> res#tcf_astc/<p> (cùng relative path, cùng tên file)
function AstcCounterpart([string]$rel) {
    if ($rel.StartsWith($ASTC_PREFIX, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $SRC_PREFIX + $rel.Substring($ASTC_PREFIX.Length)
    }
    if ($rel.StartsWith($SRC_PREFIX, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $ASTC_PREFIX + $rel.Substring($SRC_PREFIX.Length)
    }
    return $null
}

function IsTexture([string]$rel) {
    $lower = $rel.ToLowerInvariant()
    foreach ($ext in $TEXTURE_EXTS) { if ($lower.EndsWith($ext)) { return $true } }
    return $false
}

# Với .plist -> stem (đường dẫn bỏ extension) để ghép texture cùng tên
function Stem([string]$rel) {
    $idx = $rel.LastIndexOf('.')
    if ($idx -lt 0) { return $rel }
    return $rel.Substring(0, $idx)
}

function NewSet() {
    return New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
}

function EnsureDir([string]$dir) {
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}
# #endregion

# #region Manifest IO
function LoadManifest([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { Refuse "Manifest không tồn tại: $path" }
    try {
        $raw = Get-Content -LiteralPath $path -Raw -Encoding UTF8
        return ($raw | ConvertFrom-Json)
    } catch {
        Refuse "Manifest không parse được JSON: $path — $($_.Exception.Message)"
    }
}

function SaveManifest($obj, [string]$path) {
    $json = $obj | ConvertTo-Json -Depth 10
    [System.IO.File]::WriteAllText($path, $json, (New-Object System.Text.UTF8Encoding($false)))
}

function SetProp($obj, [string]$name, $value) {
    $existing = $obj.PSObject.Properties[$name]
    if ($null -ne $existing) { $existing.Value = $value; return }   # giữ thứ tự field trong manifest
    $obj | Add-Member -NotePropertyName $name -NotePropertyValue $value
}
# #endregion

# #region Resolve Inputs
$RepoRootFull = FullPath $RepoRoot
if (-not (Test-Path -LiteralPath (Join-Path $RepoRootFull 'project.json'))) {
    Refuse "RepoRoot không có project.json — không phải repo client: $RepoRootFull"
}

if ([string]::IsNullOrWhiteSpace($ManifestDir)) {
    $ManifestDir = Join-Path $RepoRootFull 'docs\modules\deletefeaturecontent\manifests'
}
$ManifestDirFull = FullPath $ManifestDir
$ManifestPath    = Join-Path $ManifestDirFull "$Bundle.json"
$PatchSrcPath    = Join-Path $ManifestDirFull "$Bundle.quarantine.patch"

$m = LoadManifest $ManifestPath

$mBundle = [string](Prop $m 'bundle' '')
if ($mBundle -ne $Bundle) { Refuse "manifest.bundle='$mBundle' khác -Bundle '$Bundle'" }

$mode = [string](Prop $m 'removalMode' '')
if ($VALID_MODES -notcontains $mode) { Refuse "removalMode='$mode' không hợp lệ (full-folder | partial-prune | group)" }

$status = [string](Prop $m 'status' 'planned')

if ([string]::IsNullOrWhiteSpace($Build)) { $Build = [string](Prop $m 'build' '') }
if ([string]::IsNullOrWhiteSpace($Build)) { Refuse "Build rỗng — set manifest.build hoặc -Build" }
if ($Build -match '[\\/]')                { Refuse "Build '$Build' chứa path separator" }

$BackupRootFull = FullPath $BackupRoot
if (($BackupRootFull + '\').StartsWith($RepoRootFull + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
    Refuse "BackupRoot nằm TRONG RepoRoot — nguy cơ pack lại vào APK: $BackupRootFull"
}
$BuildDir = Join-Path $BackupRootFull $Build
$MetaDir  = Join-Path $BuildDir "_meta\$Bundle"

$removed    = @(Prop $m 'removed'    @())
$retained   = @(Prop $m 'retained'   @())
$unresolved = @(Prop $m 'unresolved' @())
$patchRel   = [string](Prop $m 'quarantinePatch' '')

Log "bundle=$Bundle mode=$mode status=$status build=$Build"
Log "repo=$RepoRootFull"
Log "backup=$BuildDir"
if ($DryRun) { Log "DRY RUN — không ghi gì" }
# #endregion

# #region Static Gates (dùng chung Audit / Move)
function RunStaticGates {
    # 1. unresolved
    if ($unresolved.Count -gt 0) {
        Refuse "Trace chưa xong: $($unresolved.Count) path unresolved — $($unresolved -join ', ')"
    }

    $removedSet  = NewSet
    $retainedSet = NewSet
    foreach ($e in $removed)  { [void]$removedSet.Add((NormKey ([string]$e.path))) }
    foreach ($e in $retained) { [void]$retainedSet.Add((NormKey ([string]$e.path))) }

    if ($removed.Count -eq 0) { Refuse "removed rỗng — không có gì để xóa" }

    foreach ($k in $removedSet) {
        if ($retainedSet.Contains($k)) { Refuse "Path vừa removed vừa retained: $k" }
    }
    if ($mode -eq 'full-folder' -and $retained.Count -gt 0) {
        Refuse "removalMode=full-folder nhưng retained không rỗng ($($retained.Count)) — đổi sang partial-prune hoặc bỏ retained"
    }

    # 2. path tồn tại (removed + retained)
    foreach ($e in $removed) {
        $p = RelToRepo ([string]$e.path)
        if (-not (Test-Path -LiteralPath $p -PathType Leaf)) { Refuse "removed path không tồn tại trên disk: $($e.path)" }
    }
    foreach ($e in $retained) {
        $p = RelToRepo ([string]$e.path)
        if (-not (Test-Path -LiteralPath $p -PathType Leaf)) { Refuse "retained path không tồn tại trên disk: $($e.path)" }
    }

    # 3. source/ASTC parity
    foreach ($e in $removed) {
        $rel = [string]$e.path
        $cp  = AstcCounterpart $rel
        if ($null -eq $cp) { continue }
        $cpExists = Test-Path -LiteralPath (RelToRepo $cp) -PathType Leaf
        if ($cpExists) {
            $k = NormKey $cp
            if (-not $removedSet.Contains($k) -and -not $retainedSet.Contains($k)) {
                Refuse "Parity: '$rel' bị removed nhưng counterpart '$cp' tồn tại và không nằm trong removed/retained"
            }
        }
    }
    foreach ($e in $retained) {
        $rel = [string]$e.path
        $cp  = AstcCounterpart $rel
        if ($null -eq $cp) { continue }
        if ($removedSet.Contains((NormKey $cp))) {
            Refuse "Parity: '$rel' được retained nhưng counterpart '$cp' lại nằm trong removed"
        }
    }

    # 4. dependency group: .plist và texture cùng tên phải cùng phía
    foreach ($e in $removed) {
        $rel = [string]$e.path
        if (-not $rel.ToLowerInvariant().EndsWith('.plist')) { continue }
        $stem = NormKey (Stem $rel)
        foreach ($r in $retainedSet) {
            if ((IsTexture $r) -and ((Stem $r) -eq $stem)) {
                Refuse "Dependency group: '$rel' removed nhưng texture '$r' retained — atlas là nguyên khối"
            }
        }
    }
    foreach ($e in $retained) {
        $rel = [string]$e.path
        if (-not $rel.ToLowerInvariant().EndsWith('.plist')) { continue }
        $stem = NormKey (Stem $rel)
        foreach ($r in $removedSet) {
            if ((IsTexture $r) -and ((Stem $r) -eq $stem)) {
                Refuse "Dependency group: '$rel' retained nhưng texture '$r' removed — atlas là nguyên khối"
            }
        }
    }
}
# #endregion

# #region Action: Audit
function DoAudit {
    if (@('planned', 'audited', 'restored') -notcontains $status) {
        Refuse "Audit yêu cầu status planned|audited|restored, hiện là '$status'"
    }
    RunStaticGates

    $totalBytes = [long]0
    foreach ($e in $removed) {
        $p    = RelToRepo ([string]$e.path)
        $info = Get-Item -LiteralPath $p
        $hash = FileHash $p
        SetProp $e 'bytes'  ([long]$info.Length)
        SetProp $e 'sha256' $hash
        $totalBytes += $info.Length
        Log ("  removed  {0,10:N0} B  {1}  {2}" -f $info.Length, $hash.Substring(0, 12), $e.path)
    }
    foreach ($e in $retained) {
        $p    = RelToRepo ([string]$e.path)
        $info = Get-Item -LiteralPath $p
        SetProp $e 'bytes'  ([long]$info.Length)
        SetProp $e 'sha256' (FileHash $p)
        Log ("  retained {0,10:N0} B  {1}" -f $info.Length, $e.path)
    }

    $totals = New-Object PSObject
    SetProp $totals 'files' $removed.Count
    SetProp $totals 'bytes' $totalBytes
    SetProp $m 'totals'      $totals
    SetProp $m 'generatedAt' (Now)
    SetProp $m 'status'      'audited'

    Log ("TOTAL removed: {0} file, {1:N0} bytes" -f $removed.Count, $totalBytes)

    if ($DryRun) { Log "OK (dry run) — manifest không ghi"; return }
    SaveManifest $m $ManifestPath
    Log "OK — status=audited, manifest đã ghi: $ManifestPath"
}
# #endregion

# #region Action: Move
function DoMove {
    if ($status -ne 'audited') { Refuse "Move yêu cầu status=audited, hiện là '$status' — chạy Audit trước" }
    RunStaticGates

    # file không được đổi sau Audit
    foreach ($e in $removed) {
        $p = RelToRepo ([string]$e.path)
        $h = FileHash $p
        if ($h -ne [string]$e.sha256) { Refuse "File thay đổi sau Audit: $($e.path) — chạy Audit lại" }
    }

    # quarantine patch bắt buộc nếu manifest khai báo
    $needPatch = -not [string]::IsNullOrWhiteSpace($patchRel)
    if ($needPatch -and -not (Test-Path -LiteralPath $PatchSrcPath -PathType Leaf)) {
        Refuse "quarantinePatch khai báo nhưng không thấy file nguồn: $PatchSrcPath — tạo bằng 'git diff <code files> > $Bundle.quarantine.patch'"
    }

    # đích không được tồn tại (check từng file — nhiều bundle dùng chung cây <Build>\res\content\)
    foreach ($e in $removed) {
        $dest = RelToBackup ([string]$e.path)
        if (Test-Path -LiteralPath $dest) { Refuse "File đích đã tồn tại trong backup: $dest" }
    }

    foreach ($e in $removed) {
        Log "  move  $($e.path)  ->  $(RelToBackup ([string]$e.path))"
    }
    if ($needPatch) { Log "  copy  $PatchSrcPath  ->  $MetaDir\quarantine.patch" }
    Log "  copy  manifest -> $MetaDir\manifest.json"
    Log "  copy  script   -> $BuildDir\_meta\delete_feature_content.ps1"

    if ($DryRun) { Log "OK (dry run) — không move gì"; return }

    $protected = NewSet
    foreach ($d in @('', 'res', 'res\content', 'res#tcf_astc', 'res#tcf_astc\content')) {
        [void]$protected.Add((Join-Path $RepoRootFull $d).TrimEnd('\'))
    }

    try {
        foreach ($e in $removed) {
            $src  = RelToRepo   ([string]$e.path)
            $dest = RelToBackup ([string]$e.path)
            EnsureDir (ParentDir $dest)
            Move-Item -LiteralPath $src -Destination $dest
            # dọn folder rỗng, dừng ở protected roots
            $dir = ParentDir $src
            while ($dir -and $dir.Length -gt $RepoRootFull.Length -and -not $protected.Contains($dir.TrimEnd('\'))) {
                if (-not (Test-Path -LiteralPath $dir)) { break }
                if (@(Get-ChildItem -LiteralPath $dir -Force).Count -gt 0) { break }
                Remove-Item -LiteralPath $dir -Force
                Log "  rmdir (rỗng) $dir"
                $dir = ParentDir $dir
            }
        }

        EnsureDir $MetaDir
        if ($needPatch) { Copy-Item -LiteralPath $PatchSrcPath -Destination (Join-Path $MetaDir 'quarantine.patch') -Force }
        Copy-Item -LiteralPath $PSCommandPath -Destination (Join-Path $BuildDir '_meta\delete_feature_content.ps1') -Force

        SetProp $m 'status'  'moved'
        SetProp $m 'movedAt' (Now)
        SaveManifest $m $ManifestPath
        Copy-Item -LiteralPath $ManifestPath -Destination (Join-Path $MetaDir 'manifest.json') -Force
    } catch {
        IoFail "Move thất bại giữa chừng — kiểm tra repo/backup thủ công. $($_.Exception.Message)"
    }

    Log "OK — status=moved. $($removed.Count) file đã sang $BuildDir"
}
# #endregion

# #region Action: Verify
function DoVerify {
    if (@('moved', 'verified') -notcontains $status) {
        Refuse "Verify yêu cầu status=moved|verified, hiện là '$status'"
    }

    $errors = New-Object System.Collections.Generic.List[string]

    foreach ($e in $removed) {
        $rel  = [string]$e.path
        $repo = RelToRepo $rel
        $bak  = RelToBackup $rel
        if (Test-Path -LiteralPath $repo) { $errors.Add("còn trong repo: $rel"); continue }
        if (-not (Test-Path -LiteralPath $bak -PathType Leaf)) { $errors.Add("thiếu trong backup: $rel"); continue }
        $h = FileHash $bak
        if ($h -ne [string]$e.sha256) { $errors.Add("SHA lệch trong backup: $rel (manifest $($e.sha256.Substring(0,12)) vs backup $($h.Substring(0,12)))") }
    }

    foreach ($e in $retained) {
        $rel  = [string]$e.path
        $repo = RelToRepo $rel
        if (-not (Test-Path -LiteralPath $repo -PathType Leaf)) { $errors.Add("retained bị mất khỏi repo: $rel"); continue }
        $cp = AstcCounterpart $rel
        if ($null -ne $cp) {
            $cpRepo = RelToRepo $cp
            $cpBak  = RelToBackup $cp
            if (-not (Test-Path -LiteralPath $cpRepo) -and (Test-Path -LiteralPath $cpBak)) {
                $errors.Add("Parity: retained '$rel' nhưng counterpart '$cp' đã bị move sang backup")
            }
        }
    }

    # top-level bundle dirs: res/content/<x>, res#tcf_astc/content/<x>
    $topDirs = NewSet
    foreach ($e in $removed) {
        $parts = ([string]$e.path).Split('/')
        if ($parts.Length -ge 3) { [void]$topDirs.Add(($parts[0..2] -join '/')) }
    }
    foreach ($td in $topDirs) {
        if ($mode -eq 'group') { continue }   # folder dùng chung (res/animation/config …) phải còn
        $dir = RelToRepo $td
        if ($mode -eq 'full-folder') {
            if (Test-Path -LiteralPath $dir) { $errors.Add("full-folder nhưng folder vẫn tồn tại: $td") }
        } elseif (Test-Path -LiteralPath $dir) {
            $empties = @(Get-ChildItem -LiteralPath $dir -Recurse -Directory -Force | Where-Object {
                @(Get-ChildItem -LiteralPath $_.FullName -Recurse -File -Force).Count -eq 0
            })
            foreach ($d in $empties) { $errors.Add("folder rỗng còn lại: $($d.FullName)") }
        }
    }

    if (-not (Test-Path -LiteralPath (Join-Path $MetaDir 'manifest.json'))) { $errors.Add("thiếu _meta manifest: $MetaDir\manifest.json") }
    if (-not [string]::IsNullOrWhiteSpace($patchRel) -and -not (Test-Path -LiteralPath (Join-Path $MetaDir 'quarantine.patch'))) {
        $errors.Add("thiếu _meta quarantine.patch: $MetaDir\quarantine.patch")
    }

    if ($errors.Count -gt 0) {
        foreach ($err in $errors) { Log "  FAIL  $err" }
        Fail "$($errors.Count) lỗi"
    }

    Log ("  {0} removed vắng trong repo, có trong backup, SHA khớp" -f $removed.Count)
    Log ("  {0} retained còn trong repo, parity OK" -f $retained.Count)

    if ($DryRun) { Log "OK (dry run)"; return }
    SetProp $m 'status'     'verified'
    SetProp $m 'verifiedAt' (Now)
    SaveManifest $m $ManifestPath
    Copy-Item -LiteralPath $ManifestPath -Destination (Join-Path $MetaDir 'manifest.json') -Force
    Log "OK — status=verified"
}
# #endregion

# #region Action: Restore
function DoRestore {
    if (@('moved', 'verified') -notcontains $status) {
        Refuse "Restore yêu cầu status=moved|verified, hiện là '$status'"
    }

    foreach ($e in $removed) {
        $rel  = [string]$e.path
        $bak  = RelToBackup $rel
        $repo = RelToRepo $rel
        if (-not (Test-Path -LiteralPath $bak -PathType Leaf)) { IoFail "Backup thiếu file: $bak" }
        if (Test-Path -LiteralPath $repo) {
            if ((FileHash $repo) -ne [string]$e.sha256) { Refuse "Repo đã có file KHÁC nội dung tại $rel — không ghi đè" }
        }
        Log "  copy  $bak  ->  $repo"
    }

    if ($DryRun) { Log "OK (dry run) — không copy gì"; return }

    try {
        foreach ($e in $removed) {
            $rel  = [string]$e.path
            $bak  = RelToBackup $rel
            $repo = RelToRepo $rel
            EnsureDir (ParentDir $repo)
            Copy-Item -LiteralPath $bak -Destination $repo -Force
        }
        SetProp $m 'status'     'restored'
        SetProp $m 'restoredAt' (Now)
        SaveManifest $m $ManifestPath
    } catch {
        IoFail "Restore thất bại giữa chừng. $($_.Exception.Message)"
    }

    Log "OK — status=restored. Resource đã về repo (backup giữ nguyên)."
    if (-not [string]::IsNullOrWhiteSpace($patchRel)) {
        Log "NHẮC: resource về chưa đủ — revert code quarantine:"
        Log "      git apply -R `"$(Join-Path $MetaDir 'quarantine.patch')`""
    }
}
# #endregion

# #region Dispatch
switch ($Action) {
    'Audit'   { DoAudit }
    'Move'    { DoMove }
    'Verify'  { DoVerify }
    'Restore' { DoRestore }
}
exit $EXIT_OK
# #endregion
