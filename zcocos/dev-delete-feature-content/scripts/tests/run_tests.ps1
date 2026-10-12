# Chạy: bash make_fixture.sh  rồi  .\run_tests.ps1   (fixture PHẢI reset trước mỗi lần — suite không idempotent)
$ErrorActionPreference = 'Continue'
$Tool = Join-Path (Split-Path -Parent $PSScriptRoot) 'delete_feature_content.ps1'   # scripts/tests -> scripts/
$FX   = Split-Path -Parent $MyInvocation.MyCommand.Path
$Repo = Join-Path $FX 'repo'
$Bak  = Join-Path $FX 'backup'
$pass = 0; $fail = 0

function Run([string]$name, [int]$expect, [hashtable]$p) {
    if (-not $p.ContainsKey('RepoRoot'))   { $p['RepoRoot']   = $Repo }
    if (-not $p.ContainsKey('BackupRoot')) { $p['BackupRoot'] = $Bak }
    $out = @()
    try {
        $out = & $Tool @p 2>&1
        $code = $LASTEXITCODE
    } catch {
        $out += "EXCEPTION: $($_.Exception.Message)"
        $code = 99
    }
    $ok = ($code -eq $expect)
    if ($ok) { $script:pass++ } else { $script:fail++ }
    $tag = if ($ok) { 'PASS' } else { 'FAIL' }
    Write-Output ("[{0}] {1,-38} exit={2} expect={3}" -f $tag, $name, $code, $expect)
    if (-not $ok) { $out | ForEach-Object { Write-Output "        $_" } }
    else { $out | Where-Object { "$_" -match 'REFUSE|VERIFY FAIL|IO ERROR|\] OK|NHẮC|git apply' } | ForEach-Object { Write-Output "        $_" } }
}
function Chk([string]$name, [bool]$cond) {
    if ($cond) { $script:pass++ } else { $script:fail++ }
    Write-Output ("[{0}] {1}" -f ($(if ($cond) { 'PASS' } else { 'FAIL' })), $name)
}

Write-Output "===== REFUSE cases ====="
Run 'unresolved non-empty'          1 @{Action='Audit'; Bundle='bad_unresolved'}
Run 'astc counterpart not listed'   1 @{Action='Audit'; Bundle='bad_astc'}
Run 'plist removed, texture kept'   1 @{Action='Audit'; Bundle='bad_group'}
Run 'removed path missing on disk'  1 @{Action='Audit'; Bundle='bad_missing'}
Run 'full-folder with retained'     1 @{Action='Audit'; Bundle='bad_fullret'}
Run 'BackupRoot inside RepoRoot'    1 @{Action='Audit'; Bundle='fakea'; BackupRoot=(Join-Path $Repo 'bk')}
Run 'Build has separator'           1 @{Action='Audit'; Bundle='fakea'; Build='a\b'}
Run 'Move before Audit'             1 @{Action='Move';  Bundle='fakea'}
Run 'Verify while planned'          1 @{Action='Verify'; Bundle='fakea'}
Run 'RepoRoot without project.json' 1 @{Action='Audit'; Bundle='fakea'; RepoRoot=$FX}
Run 'nopatch: Audit ok'             0 @{Action='Audit'; Bundle='bad_nopatch'}
Run 'nopatch: Move refuses'         1 @{Action='Move';  Bundle='bad_nopatch'}

Write-Output ""
Write-Output "===== GOOD PATH fakea (full-folder) ====="
Run 'fakea Audit'                   0 @{Action='Audit'; Bundle='fakea'}
Run 'fakea Move -DryRun'            0 @{Action='Move';  Bundle='fakea'; DryRun=$true}
Chk 'dry run: A1.json still in repo'          (Test-Path (Join-Path $Repo 'res\content\fakea\A1.json'))
Run 'fakea Move'                    0 @{Action='Move';  Bundle='fakea'}
Chk 'res/content/fakea gone'                  (-not (Test-Path (Join-Path $Repo 'res\content\fakea')))
Chk 'res#tcf_astc/content/fakea gone'         (-not (Test-Path (Join-Path $Repo 'res#tcf_astc\content\fakea')))
Chk 'res/content kept (protected)'            (Test-Path (Join-Path $Repo 'res\content'))
Chk 'backup mirrors client structure'         (Test-Path (Join-Path $Bak 'buildTEST\res\content\fakea\A1.json'))
Chk 'backup astc mirrored'                    (Test-Path (Join-Path $Bak 'buildTEST\res#tcf_astc\content\fakea\fakea.png'))
Chk '_meta manifest.json'                     (Test-Path (Join-Path $Bak 'buildTEST\_meta\fakea\manifest.json'))
Chk '_meta quarantine.patch'                  (Test-Path (Join-Path $Bak 'buildTEST\_meta\fakea\quarantine.patch'))
Chk '_meta script copy'                       (Test-Path (Join-Path $Bak 'buildTEST\_meta\delete_feature_content.ps1'))
Run 'fakea Verify'                  0 @{Action='Verify'; Bundle='fakea'}
Run 'fakea Audit while verified'    1 @{Action='Audit'; Bundle='fakea'}
Run 'fakea Restore'                 0 @{Action='Restore'; Bundle='fakea'}
Chk 'A1.json back in repo'                    (Test-Path (Join-Path $Repo 'res\content\fakea\A1.json'))
Chk 'astc back in repo'                       (Test-Path (Join-Path $Repo 'res#tcf_astc\content\fakea\fakea.png'))
Chk 'backup still intact after restore'       (Test-Path (Join-Path $Bak 'buildTEST\res\content\fakea\A1.json'))
Chk 'restored content identical'              ((Get-Content (Join-Path $Repo 'res\content\fakea\A1.json') -Raw) -eq 'A-json-1')
Run 'fakea re-Audit after restore'  0 @{Action='Audit'; Bundle='fakea'}
Run 'fakea Move -> dest exists (#7)' 1 @{Action='Move';  Bundle='fakea'}

Write-Output ""
Write-Output "===== GOOD PATH fakeb (partial-prune) ====="
Run 'fakeb Audit'                   0 @{Action='Audit'; Bundle='fakeb'}
Run 'fakeb Move'                    0 @{Action='Move';  Bundle='fakeb'}
Chk 'B1.json gone'                            (-not (Test-Path (Join-Path $Repo 'res\content\fakeb\B1.json')))
Chk 'atlas group retained (2 src + 1 astc)'   ((@(Get-ChildItem (Join-Path $Repo 'res\content\fakeb') -File).Count -eq 2) -and (Test-Path (Join-Path $Repo 'res#tcf_astc\content\fakeb\fakeb.png')))
Chk 'res/content/fakeb folder kept'           (Test-Path (Join-Path $Repo 'res\content\fakeb'))
Run 'fakeb Verify'                  0 @{Action='Verify'; Bundle='fakeb'}
Run 'fakeb Restore'                 0 @{Action='Restore'; Bundle='fakeb'}
Chk 'B1.json back'                            (Test-Path (Join-Path $Repo 'res\content\fakeb\B1.json'))

Write-Output ""
Write-Output "===== manifest fakea after cycle ====="
Get-Content (Join-Path $Repo 'docs\modules\deletefeaturecontent\manifests\fakea.json') -Raw

Write-Output ""
Write-Output ("RESULT: pass={0} fail={1}" -f $pass, $fail)
