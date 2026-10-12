# Scenario Matrix

Confirm the matrix after tracing production handlers and before implementation. Add one row per meaningful case/flow combination; document intentional gaps rather than silently skipping them.

| case ID | typed packet/state input | flow ID | expected module signals/state | expected UI | manual verification | automated codec counterpart | documented client-only exception |
|---|---|---|---|---|---|---|---|
| `success` | `SampleEventRecvLoadInfo`, success fields | `main` | canonical load handler emits refresh signal | main screen shows populated state | Save JSON; press dev key; inspect state/UI | focused load-info codec/handler GUT | none |
| `error` | `SampleEventRecvLoadInfo`, nonzero `error_code` | `main` | production handler handles and reports the nonzero error | UI does not open | Save JSON; press dev key; inspect handler error and confirm no UI | focused error-handler GUT | none |

For a push flow, name its canonical typed packet and production subscriber. For malformed JSON, unknown case IDs, and unknown flow IDs, record the explicit error and verify that neither state nor UI changes.
