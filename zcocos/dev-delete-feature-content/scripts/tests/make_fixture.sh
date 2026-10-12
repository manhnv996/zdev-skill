#!/usr/bin/env bash
# Reset fixture repo + backup cho test tool. Chạy trước MỖI lần run_tests.ps1.
set -e
FX="$(cd "$(dirname "$0")" && pwd)"
rm -rf "$FX/repo" "$FX/backup"
mkdir -p "$FX/repo/res/content/fakea" "$FX/repo/res#tcf_astc/content/fakea" "$FX/repo/res/content/fakeb" "$FX/repo/res#tcf_astc/content/fakeb" "$FX/repo/docs/modules/deletefeaturecontent/manifests" "$FX/backup"
cd "$FX/repo"
echo '{}' > project.json
printf 'A-json-1'   > res/content/fakea/A1.json
printf 'A-json-2'   > res/content/fakea/A2.json
printf 'A-plist'    > res/content/fakea/fakea.plist
printf 'A-png-src'  > res/content/fakea/fakea.png
printf 'A-png-astc' > "res#tcf_astc/content/fakea/fakea.png"
printf 'B-json-1'   > res/content/fakeb/B1.json
printf 'B-plist'    > res/content/fakeb/fakeb.plist
printf 'B-png-src'  > res/content/fakeb/fakeb.png
printf 'B-png-astc' > "res#tcf_astc/content/fakeb/fakeb.png"
M="docs/modules/deletefeaturecontent/manifests"
mk() { cat > "$M/$1.json" <<EOF
{
  "bundle": "$1",
  "build": "buildTEST",
  "branch": "test",
  "removalMode": "$2",
  "status": "planned",
  "generatedAt": "",
  "backupRoot": "",
  "quarantinePatch": "$6",
  "unresolved": [$5],
  "removed": [$3],
  "retained": [$4],
  "totals": { "files": 0, "bytes": 0 }
}
EOF
}
R() { printf '{ "path": "%s", "bytes": 0, "sha256": "" }' "$1"; }
A_ALL="$(R res/content/fakea/A1.json), $(R res/content/fakea/A2.json), $(R res/content/fakea/fakea.plist), $(R res/content/fakea/fakea.png), $(R 'res#tcf_astc/content/fakea/fakea.png')"
mk fakea full-folder "$A_ALL" "" "" "_meta/fakea/quarantine.patch"
printf 'diff --git a/x b/x\n' > "$M/fakea.quarantine.patch"
mk fakeb partial-prune "$(R res/content/fakeb/B1.json)" "$(R res/content/fakeb/fakeb.plist), $(R res/content/fakeb/fakeb.png), $(R 'res#tcf_astc/content/fakeb/fakeb.png')" "" ""
mk bad_unresolved full-folder "$A_ALL" "" '"res/content/fakea/mystery.png"' ""
mk bad_astc full-folder "$(R res/content/fakea/A1.json), $(R res/content/fakea/fakea.plist), $(R res/content/fakea/fakea.png)" "" "" ""
mk bad_group partial-prune "$(R res/content/fakeb/B1.json), $(R res/content/fakeb/fakeb.plist)" "$(R res/content/fakeb/fakeb.png), $(R 'res#tcf_astc/content/fakeb/fakeb.png')" "" ""
mk bad_missing full-folder "$(R res/content/fakea/NOPE.json)" "" "" ""
mk bad_fullret full-folder "$(R res/content/fakeb/B1.json)" "$(R res/content/fakeb/fakeb.plist)" "" ""
mk bad_nopatch full-folder "$(R res/content/fakea/A2.json)" "" "" "_meta/bad_nopatch/quarantine.patch"
echo "fixture reset OK: $(find "$FX/repo" -type f | wc -l) files"
