---
name: dev-godot-mock
description: Use when creating or updating dev-only interactive mock data, fake typed server responses, CheatInput test flows, or QA scenarios for a Godot game feature.
argument-hint: "[feature id | feature docs path | feature module path]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Bash
---

# Godot Interactive Mocks

Build dev-only manual test flows through the same typed packet handlers as real network traffic. Keep interactive mocks separate from GUT fixtures and live-server integration tests.

## Create Route

1. Read the feature spec, module, receive packets, signals, UI entry points, and tests; trace the real packet-to-state-to-UI path.
2. Confirm the scenario matrix with the user after inspection, including every case, flow, expected state/signal, UI result, and verification counterpart.
3. Read [the runtime pattern](references/mock-runtime-pattern.md), [the editable config](references/mock-current-template.json), [the scenario matrix](references/scenario-matrix-template.md), and [the packaging checklist](references/packaging-checklist.md).
4. Implement typed packet delivery first, then UI actions. Synchronize runtime, JSON config, docs, loader entry, and CheatInput key in one change.
5. Verify the complete packaging checklist and report any absent production feature surface instead of inventing contracts.

## Update Route

1. Inspect the feature spec, module, receive packets, signals, UI entry points, tests, and all five existing mock artifacts; trace the current production handler path.
2. Confirm the updated scenario matrix with the user after inspection, including malformed and unknown-input outcomes.
3. Re-read the four references, then change runtime, JSON config, docs, loader entry, and CheatInput together.
4. Re-run focused codec/handler tests, mock tests, config reload, source scans, and both mobile export checks.

## Safety Contract

- Never use direct util/model mutation; construct the canonical typed receive packet and call `NetworkService.dispatch_mock_packet()`.
- Never add a production `preload` of `devtools`; production code must reach the loader through its dynamic string path.
- Never use literal load paths into devtools from production code; retain the `ResourceLoader` boundary.
- Do not use silent socket interception; dispatch explicitly through the dev-only packet API.
- Require independent DEV guards in the loader and `NetworkService.dispatch_mock_packet()`.
- Handle missing files, malformed JSON, and unknown case/flow IDs with an explicit error and no state/UI side effects.

## Optional Providers

- Ensure `PoolFunction.do_func` gives every optional command with a missing provider a safe no-op.
- Require every optional query to define an explicit meaningful default value.
- Keep stable action IDs in core routing; remove feature class references when the provider is removed.

## Completion

- Treat a mock as complete only when its typed handler path is executable and the five artifacts agree.
- Record manual results separately from targeted GUT output; claim a GUT pass only from its summary.
