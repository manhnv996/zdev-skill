# Validation checklist

Run these from the project root after an approved implementation. Replace `<feature_id>` and `<spec>` with real paths. `<source_root>` is copied exactly from the approved spec and has no `res://` prefix.

```powershell
# Contract validation
python '.agents/skills/dev-godot-feature/scripts/validate_feature.py' --project-root . --feature-id '<feature_id>' --spec '<spec>'

# Targeted and full GUT
& 'D:\workspace\STM-Godot\godot-client-template\godot.exe' --headless --path . -s addons/gut/gut_cmdln.gd -gdir=res://tests/unit/features/<feature_id> -gexit -gconfig=
& 'D:\workspace\STM-Godot\godot-client-template\godot.exe' --headless --path . -s addons/gut/gut_cmdln.gd -gdir=res://tests -gexit -gconfig=

# Callsite/source ownership scans
rg -n 'NetworkService\.(subscribe|send_packet)|PoolFunction\.(reg_func|do_func)' <source_root>
rg -n 'SampleEvent(Recv|Send)' <source_root>/ui

# Approved docs status and assets
rg -n 'Status \| Approved|TBD|\[ \]' docs/modules/<feature_id>/spec/<feature_id>-spec.md
Get-ChildItem -Recurse 'assets/textures/<feature_id>'

# Missing/unknown symbols before handoff
rg -n 'class_name <Feature>|<FeatureId>Module|<FeatureId>JSONConfig' modules tests
```

The UI packet scan must have no result. Validator exit 0 means every canonical table row matches its exact command ID/class and module callsite, public API/signal, retained optional-boundary registration/callsite/default, config file/class/path or same-schema source-family lifecycle/accessor, and asserted `test_<scenario_id>` evidence. It requires `BaseScreen` for `Control` UI but permits approved non-`Control` world/render scripts below `ui/`. Review every finding before declaring completion, and record the commands/results in feature documentation or the implementation report.
