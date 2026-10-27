# Cloud robotics AI/LLM experiment risk register

> **Blank risk review form.** Does not grant safety approval, permit real robot operation, classify EU AI Act legal obligations or override [SAFETY.md](../../../SAFETY.md) and [SECURITY.md](../../../SECURITY.md).

## Experiment identifiers

- Scenario / owner / review date: TBD
- Intended user, simulated environment, affected people: TBD
- Hardware? **Default must be no physical actuator**; non-default requires separately approved physical safety plan
- Data rights/consent/privacy review: TBD
- Model/dataset license and processor/source revision: TBD
- Decision: **draft / needs mitigation / blocked / approved for synthetic simulation ONLY**

## Risk register

| ID | Hazard or misuse | Likelihood / impact (qualitative) | Mitigation outside the model | Testable evidence | Owner / residual risk / decision |
| --- | --- | --- | --- | --- | --- |
| R-01 | Unreviewed physical actuation | TBD | Disable direct hardware connectors; independent safety authority later | No physical device outputs in unit tests | TBD |
| R-02 | Stale/replayed/out-of-bounds action | TBD | Typed TTL+seq+units and simulated action gate | Negative delayed/replay cases | TBD |
| R-03 | Incompatible policy/embodiment | TBD | Model/robot contract, exact state/action semantics | Reject mismatch | TBD |
| R-04 | Prompt injection and tool escalation | TBD | Read-only RAG and allowlisted typed skills | Attack corpus; zero executed unauthorized effects | TBD |
| R-05 | Private/unlicensed sensor content | TBD | Synthetic default; license/consent checks | Reviewed data card; no private data uploads | TBD |
| R-06 | Model artifact/dependency compromise | TBD | Pinned digest, code review, sandbox, read-only cache | Tamper/revision mismatch test | TBD |
| R-07 | Hub/ROS/K8s credential exposure | TBD | No secrets in repo, least privilege, private endpoints | Review logs, image and manifests | TBD |
| R-08 | Failure or lost remote connectivity | TBD | Bounded timeout and simulator reject/hold | Fault injection and recovery evidence | TBD |
| R-09 | Misleading real-time or physical safety claims | TBD | Explicit R0-R3 maturity and verified metrics | Reviewer links every public chart to real run | TBD |
| R-10 | Surveillance, bias, accessibility and energy harm | TBD | Purpose/rights review and measured limitations | Bias/error cases, opt-out/retention and energy data limits | TBD |

This table is a **starting set of risks**, not exhaustive. Add scenario-specific risks (e.g. workplace/child data, RF/network interference, teleoperation, dual-use misuse, cloud provider incident) as relevant, with severity and ownership.

## Review decision checklist

- [ ] Experiment works with synthetic/approved inputs only; if any human/physical element exists, external oversight gate is recorded.
- [ ] Explicit accepted risk and thresholds established **before** test.
- [ ] Action/data/model semantic contract validates and fails closed.
- [ ] No prompt-only safeguard is mistaken for permission enforcement.
- [ ] Dataset provenance, use rights, retention and deletion are recorded.
- [ ] Resource/cost/accessibility route and third-party code threat assessed.
- [ ] Possible legal/standards review identified but **no unsupported compliance claim** made.
- [ ] Safety, security and incident reporting contacts are in designated private channels (not public secrets).
- [ ] Reviewer notes what tests were performed and which remain unrun.
- [ ] Public claims will distinguish proposed, synthetic, simulated, integrated and real-world evidence.

**Decision summary:** [risk accepted for simulation / blocked / requires additional reviewer]; rationale, verification artifact and next review trigger. No real robot safety permission can arise from this document alone.

