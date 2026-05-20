# {{NAME}} ({{ID}})

**Type:** {{TYPE}}
**Location:** {{CITY}}, {{STATE}}
**Peer:** {{PEER_ID}}
**Profile last reviewed:** {{REVIEW_DATE}}

## Quick facts
- **FTE on roster:** ~{{HEADCOUNT}}
- **Shifts:** {{SHIFTS}}
- **Operating days:** {{OP_DAYS}}
- **Primary SKU mix:** {{SKU_MIX}}
- **Equipment footprint:** {{EQUIPMENT}}

## Operational profile
- **Target CPH (facility-wide):** {{CPH_TARGET}}
- **Target error rate (per 1k units):** ≤ {{ERROR_TARGET}}
- **Daily units (typical):** {{UNITS_TYPICAL}}
- **Daily hours_run (typical):** {{HOURS_TYPICAL}}

## Metric files
- Operational: [data/metrics/operational/{{ID}}.csv](../../metrics/operational/{{ID}}.csv)
- Inputs: [data/metrics/inputs/{{ID}}.csv](../../metrics/inputs/{{ID}}.csv)
- Exceptions: [data/metrics/exceptions/{{ID}}.csv](../../metrics/exceptions/{{ID}}.csv)
- Equipment: [data/metrics/equipment/{{ID}}.csv](../../metrics/equipment/{{ID}}.csv)
- Events: [data/events/{{ID}}.csv](../../events/{{ID}}.csv)

## Context
{{CONTEXT_NOTES}}

## Related
- Peer facility: [{{PEER_ID}}](./{{PEER_ID}}.md)
- State rollup: [{{STATE}} facilities](../INDEX.md#state-rollups)
- Type rollup: [{{TYPE}} facilities](../INDEX.md#type-rollups)
