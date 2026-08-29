# 03 — Frequency model

**Commit:** `feat(frequency): annualized attack frequency from telemetry`

## Prompt given

> Build backend/risk_engine/frequency/. Events ≠ attacks:
> - Filter to attack-grade events (severity_class ≥ high; threshold parameter).
> - Sessionize into episodes: same asset, gap ≤ window_hours (default 24,
>   parameter) → one episode.
> - Annualize: episodes / observed_days × 365, observed window computed from data.
> - Segment λ by attack_type using an explicit TECHNIQUE_TO_ATTACK_TYPE dict
>   mapping MITRE techniques to {phishing, ransomware, credential_theft,
>   data_breach, misconfiguration, ddos, insider_error, supply_chain}; unmapped →
>   "other", reported. STOP and list the mapping for my review before finalizing.
> - Output FrequencyEstimate: lambda_total, lambda_by_attack_type, episodes,
>   observed_days, params, and to_explanation() producing the numbered trace
>   (raw → unique → attack-grade → episodes → λ).
> - Also a per-asset episode breakdown (by criticality/environment) for the UI.
> Tests: boundary gap, single event, multi-asset sessionization, annualization
> math, mapping fallback.

## The review checkpoint

The mapping was presented for approval before any of the module was written, with
attack-grade event counts per technique so the weight behind each attribution was
visible. It was approved as proposed; four entries were flagged as genuinely
arguable and are marked `ARGUABLE` in `attack_types.py` with their alternative:

| Technique | Mapped to | Alternative | Attack-grade events |
|---|---|---|---|
| T1489 Service Stop | `ransomware` | `ddos` | 976 |
| T1552 Unsecured Credentials | `credential_theft` | `misconfiguration` | 593 |
| T1190 / T1210 Exploitation | `misconfiguration` | `other` | 675 |
| T1204 User Execution | `phishing` | `other` | 533 |

The review also surfaced a second question the prompt did not settle, which was
put to the human before building.

## Decisions taken

1. **The episode key is `(asset_id, attack_type)`, not `asset_id` alone.**
   Approved at the checkpoint. The prompt's wording implies keying on the asset,
   but that makes a DDoS and a phishing detection four hours apart on one machine
   a single episode, which then needs an arbitrary rule to pick one attack type
   for pricing. Keying on both gives each episode one type by construction. The
   two readings differ by a factor of 5.7 in λ_total (8,949/yr against 1,569/yr on
   the case data), so the choice was measured, not assumed.
2. **`supply_chain` and `insider_error` get λ = 0**, recorded in
   `UNOBSERVABLE_ATTACK_TYPES` and called out in the explanation. No ATT&CK
   technique in either feed corresponds to them, yet the incident base holds 78
   supply-chain and 129 insider-error incidents. The zero means *unobservable by a
   SIEM and an EDR*, not *no exposure*, and anything downstream that reads it as
   the latter is drawing a conclusion the data does not support.
3. **Ungraded events are not attack-grade.** The 151 events that reach this stage
   with no severity are excluded and counted, never promoted or silently demoted.
4. **Events with no asset cannot form episodes** and are counted separately (27 on
   the case data). An attack that cannot be attributed to a machine cannot be
   clustered per machine.
5. **A null technique maps to `other` but is counted apart from unmapped named
   techniques.** Both land in `other`, and the trace reports each cause: on the
   case data, 136 null-technique events and 53 events across four unmapped
   reconnaissance techniques. Without the split, `other` showed 179 episodes while
   the report explained only 53 events' worth — an explainability gap caught by
   running the finished module against the real data.
6. **`DAYS_PER_YEAR = 365` is a constant, not a parameter.** A leap year would move
   the fourth decimal of a figure whose inputs are far less precise.
7. **The gap rule is inclusive**: events exactly `session_gap_hours` apart stay in
   one episode, matching the prompt's "gap ≤ window_hours". Tested on both sides
   of the boundary.

## Result on the case data

```
5,325 episodes over 212 days  ->  lambda_total = 9,168.0 attacks/year

  ransomware        1,107   1,905.9/yr      misconfiguration    512    881.5/yr
  data_breach         987   1,699.3/yr      other               179    308.2/yr
  credential_theft    940   1,618.4/yr      insider_error         0      0.0/yr
  ddos                883   1,520.3/yr      supply_chain          0      0.0/yr
  phishing            717   1,234.5/yr
```

100 tests, 100% coverage of the frequency package.

## Flagged for validation

**λ_total of 9,168 attacks/year is roughly 25 successful attacks per day on a
20-asset estate.** That is what the telemetry says — 10,126 attack-grade events
over 212 days, collapsing at 1.9 events per episode — but it is not a plausible
real-world rate, and it will drive an implausibly large AAL when it meets the
severity model. The cause is upstream of this module: the synthetic feeds grade
31.5% of all events as high or critical, where a real estate would be far lower.

Two levers exist if the downstream number needs to be defensible rather than
faithful: raise `severity_threshold` to `critical` (a `FrequencyParams` argument,
no code change), or widen `session_gap_hours`. Both are parameters precisely so
this can be tuned and shown, and neither should be changed silently — flagging it
here rather than picking one.
