# Packaging and Verification Checklist

## Runtime Safety

- [ ] Verify the mock loader has its own `gc.SERVER_ID == GameEnvironment.SERVER_ID_DEV` DEV guard before file access or execution.
- [ ] Verify `NetworkService.dispatch_mock_packet` has its own `gc.SERVER_ID == GameEnvironment.SERVER_ID_DEV` DEV guard before delivery.
- [ ] Check production sources with a dynamic-only scan: `rg -n 'preload\("res://devtools/|load\("res://devtools/' modules`; require no matches while retaining the string-path `ResourceLoader` bridge.
- [ ] Exercise a missing runtime/config file and require an explicit error with no crash or side effects.
- [ ] Edit valid JSON, save it, trigger again, and verify the loader re-read JSON without restarting.
- [ ] Exercise malformed JSON, then unknown case and flow IDs; require explicit errors and no state/UI side effects.

## Mobile Packaging

- [ ] Check Android and iOS export presets both exclude `devtools/**`; run the export/filter verification for both mobile targets.

## Tests

- [ ] In a fresh worktree, run Godot headless `--import` before GUT so global class names are available.
- [ ] Run targeted GUT codec, production-handler, loader, CheatInput, and packaging tests; preserve the final summary before claiming a pass.
- [ ] Confirm packet delivery reaches the real module subscriber before the UI action.
- [ ] Confirm optional actions safely no-op and optional queries return their documented defaults when providers are absent.

Set the two traced feature paths, then run this PowerShell from the project root:

```powershell
$godotExe = 'D:\path\to\godot.exe'
$featureMockTest = 'res://tests/unit/features/{feature}/test_{feature}_mock.gd'
$featureHandlerTest = 'res://tests/unit/features/{feature}/test_{feature}_handler_or_codec.gd'

$importProcess = Start-Process -FilePath $godotExe `
  -ArgumentList @('--headless', '--path', '.', '--import') `
  -WindowStyle Hidden -Wait -PassThru
if ($importProcess.ExitCode -ne 0) {
  throw "Godot import failed with exit code $($importProcess.ExitCode)."
}

function Invoke-GutTestFile {
  param([Parameter(Mandatory = $true)][string]$TestPath)

  $testName = [IO.Path]::GetFileNameWithoutExtension($TestPath)
  $stdoutPath = Join-Path $env:TEMP ("dev-godot-mock-$testName.stdout.log")
  $stderrPath = Join-Path $env:TEMP ("dev-godot-mock-$testName.stderr.log")
  $arguments = @(
    '--headless', '--path', '.', '-s', 'addons/gut/gut_cmdln.gd',
    "-gtest=$TestPath", '-gexit', '-gconfig='
  )
  $process = Start-Process -FilePath $godotExe -ArgumentList $arguments `
    -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath `
    -WindowStyle Hidden -Wait -PassThru
  $stdout = Get-Content -Raw -LiteralPath $stdoutPath
  $stderr = Get-Content -Raw -LiteralPath $stderrPath
  Write-Output $stdout
  Write-Output $stderr
  if ($process.ExitCode -ne 0) {
    throw "$TestPath failed with exit code $($process.ExitCode)."
  }
  if ($stdout -notmatch '(?m)= Run Summary' -or $stdout -notmatch 'All tests passed!') {
    throw "$TestPath produced no passing final GUT Run Summary."
  }
}

Invoke-GutTestFile $featureMockTest
Invoke-GutTestFile $featureHandlerTest
Invoke-GutTestFile 'res://tests/unit/test_dev_mock_loader.gd'
Invoke-GutTestFile 'res://tests/unit/test_cheat_input.gd'
Invoke-GutTestFile 'res://tests/unit/test_devtools_packaging.gd'
```

Each invocation must have process `ExitCode` 0 and print a final GUT `Run Summary` containing `All tests passed!`; an exit code alone is insufficient.

## Five-Artifact Synchronization

- [ ] Synchronize runtime, JSON, docs, loader, and Cheat in the same change; ensure every case/flow identifier agrees across all five artifacts.
