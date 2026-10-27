# Ethics, safety, privacy, security and research governance

> **Applies to all Cloud Robotics + AI/LLM Lab proposals.** This is an educational/research governance framework, not legal advice, a certification, a regulatory classification, or a guarantee of safety. Our first phases are **synthetic data and simulated actuation only**. Real robots, human participants, occupied spaces, or human-identifying recordings require separately reviewed, qualified oversight.

## Responsible innovation principles

1. **No physical autonomy by default:** Cloud/LLM policies do not run safety-rated control loops. Never expose arbitrary velocities, raw joints, force/torque, remote operator tools or physical robot commands in starter demos.
2. **Human responsibility:** a qualified operator and independent physical safeguards are necessary for a future real device, along with applicable risk assessment, emergency stop and legal/site approvals. An LLM explaining "safe" is not evidence.
3. **Privacy and consent:** no face/voice/biometric/household, employee, child or public-space footage in this public repo without explicit, lawful approval, notice, retention plan and consent or other applicable legal basis.
4. **Reproducibility with integrity:** keep model/dataset/image provenance, raw failures, calibrated clocks, source references and limits; never claim AI inference or policy safety from fake/mock runs.
5. **Safe software boundaries:** least-privilege K8s, private network endpoints, validated typed actions, reviewed external model/code, no public secrets or writable robot endpoints.
6. **Fair access:** provide a no-cloud/no-GPU learning route; document accelerator-only modules, costs and accessibility alternatives.
7. **Respect for affected people:** assess surveillance/worker oversight, dual use, foreseeable misuse, disability/accessibility, environmental impacts and unequal performance across physical settings.
8. **Transparency:** distinguish demonstration, simulated result, experiment and actual deployment; label generative-AI outputs and uncertainties when material.

## A plain-language risk model

Use **Likelihood × Impact** as a *qualitative screening device only* (Low/Medium/High), not a numerical certification. Record who owns each risk, controls, verification method, residual risk, review date and whether a higher authority must approve.

| Risk | Example failure | Preventive control | Proof / release gate |
| --- | --- | --- | --- |
| P1 physical harm | LLM issues motion command to actual robot | No physical actuator interface; physically separate safety controller in later approved hardware work | No side-effect capability in simulator/LLM role; qualified future hardware review |
| P2 stale policy action | Network failure returns old action chunk | TTL, sequence, state transition and deterministic simulator action gate | Late/replayed/out-of-order candidates rejected; failure logged |
| P3 mis-specified embodiment | Correct-shaped tensor has wrong joint order/units | Named feature contract, calibration and policy/robot compatibility record | Incompatible model/action schema fails before execution |
| P4 prompt injection | ROS log or retrieved page requests command escalation | Treat retrieved content as data; explicit typed tool allowlist and read-only RAG | Adversarial test suite confirms blocked tool execution |
| P5 privacy breach | ROS bag accidentally contains identifiable people, homes, employees or plant layouts | Synthetic fixtures default, review data cards, redaction/retention/approval | Public artifact checklist, legal/institutional authorization if applicable |
| P6 harmful bias/domain shift | Policy fails on lighting, objects or background changes | Defined simulator variation, no broad generalization claims | Negative-case metrics and model card limits |
| P7 supply chain | Untrusted policy package deserializes dangerous code | Pin image/model/processor revision; vendor/license review, sandbox, vulnerability scan | Hash and dependency/permission checks |
| P8 credential leak | Vagrant join token/Hub token/kubeconfig enters checkout | Ephemeral secret handling, no host-shared token file, secret scanning and reviewer checks | Coordinate existing #43 and #6, inspect output logs |
| P9 outage/single point failure | Remote inference unavailable or pod restarted | Bounded timeout and simulated safe hold/reject, local controller remains independent | Planned fault tests; do not promise motion continuity |
| P10 ungrounded research | Fake/synthetic results advertised as physical benchmark | Manifest, R0-R3 status, raw data, independent reproduction | No figures without source/units/limitations |
| P11 training-data rights | Dataset model trained on incompatible or unlicensed content | Dataset/model cards, licenses, usage restrictions, provenance | Public redistribution permission checked |
| P12 misuse / surveillance | Robot sensors repurposed to monitor people | Purpose restrictions, public-space/human review trigger, access control | Reject unsafe use case without governance approval |

A subset of risks may be **unacceptable regardless of mitigation** in this open teaching repo: remote physical actuation, covert people monitoring, unreviewed human recordings and publication of restricted maps/credentials.

## NIST AI RMF: adapt the four functions

- **GOVERN:** maintain documented project owner, code review, experiment ethics checklist, model/data cards, incident report path, roles, risk register and accountable approvals.
- **MAP:** for each experiment identify intended use, robot/simulator interface, physical/participant exposure, data paths, hardware/protocol assumptions, and people/groups affected.
- **MEASURE:** establish measurable invalid actions, recovery, mismatches, hallucinations/unauthorized tool calls, task-specific failures and missing-data rates; run adversarial and out-of-distribution tests.
- **MANAGE:** define when to reject an experiment, sandbox/disable a module, fix a security issue, pull a published artifact and refer to qualified ethics/safety review.

NIST's framework is voluntary; this mapping is not a statement of conformance. Source: [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework) and [Playbook](https://www.nist.gov/itl/ai-risk-management-framework/nist-ai-rmf-playbook).

## Physical-world risk governance and standards

**Regulatory categorization must be done per concrete product/use context.** The [EU AI Act implementation timeline](https://ai-act-service-desk.ec.europa.eu/en/ai-act/eu-ai-act-implementation-timeline) changed during 2026 and application dates depend on the category and applicable amendments. Do **not** claim this open-source simulated lab is automatically a high-risk AI system or exempt from all obligations; seek professional legal/sector-specific advice when deploying an actual use case. Human subject research may additionally require institution-specific ethical review and data-protection impact assessment.

For industrial robots, [ISO 10218-1:2025](https://www.iso.org/standard/73933.html) and related integration requirements address physical safety; they cannot be satisfied by this repository's software mock action gate. Other robot types may have additional or different applicable standards. Never advertise compliance without qualified assessment and evidence.

Before any real-world robot proposal, require: deployment-specific risk assessment; qualified safety engineer; site/operator permission; physically independent certified protective functions and emergency stops as appropriate; controlled operating area, speed/force limits; tested failure handling; human oversight; and separate approved protocol. No user request or model output can waive these gates.

## Data privacy and retention workflow

1. **Classify:** synthetic/public-open; approved research data; personal/human data; proprietary/controlled data. Default educational samples are **synthetic and license-reviewed**.
2. **Assess:** source, consent/legal basis, third-party rights, sensitive content, identifiable people, location data, time markers, trade secrets and licensing compatibility. Human images/video may require review even if blurred.
3. **Minimize:** collect only needed channels; avoid unnecessary full raw camera/voice capture and uncontrolled dataset resharing.
4. **Control:** separate private raw data from public sanitized samples; access only to approved research participants; document retention period, deletion procedure and backup lifecycle.
5. **Publish:** signed-off dataset card, license/consent confirmation, checksums, provenance and a human review of frame samples and metadata. Uploading to a public HF dataset is a **separate explicit decision**.
6. **Revisit:** reports of re-identification, rights violations or unsafe content trigger immediate disable/unpublish review via platform processes and documented incident handling.

**Do not commit:** credentials, API keys, Hugging Face tokens, private Hugging Face cache, kubeconfigs, join commands/tokens, SSH keys, production map/robot IP, unpublished photos, private audio, faces/names, lab participant information or confidential employer/university data.

## LLM and VLA risk review

A model's fluent output is not authority. Common attack/failure vectors: instruction injection in logs/task descriptions, tool-output laundering, hallucinated ROS topics, model or dataset poisoning, wrong coordinate frame/action units, prompt leakage, adversarial perception and over-trust of a model's explanation. Apply defenses *outside* the model: strict tool permissions, typed interfaces, approved scopes, isolated execution, verified model revisions, deterministic gates and observable rejection codes.

Recommended attacks in **simulation only:** schema-breaking payload, delayed/replayed action, unapproved tool, unauthorized namespace, forged model revision, prompt injection in retrieved log, wrong state dimension, nonsensical camera/frame and induced Hub cache miss. Report rejected vs executed side effects separately, along with false positive rejections.

Source: [OWASP Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/). RAG and fine-tuning can improve usefulness but do not eliminate injection vulnerabilities.

## Experiment admission checklist

Before a new lesson, benchmark, demo or public claim, ask:
- [ ] Does it have an actual scenario owner and documented goal? Are all participants real humans excluded or separately approved?
- [ ] Is physical actuation impossible? If not, **stop this repository's default path** and seek specialist review.
- [ ] Are all input data/models/software licenses and redistribution rights understood?
- [ ] Are ROS frame, action units, observation age, source clocks, model/policy revisions and expected behavior explicit?
- [ ] Does it fail closed on malformed/stale/unapproved actions and isolate untrusted LLM output?
- [ ] Are network, access, RBAC, credentials, image provenance, cache and model code reviewed?
- [ ] Are ethical/privacy impacts and foreseeable misuse documented, with residual risks and escalation owner?
- [ ] Can the experiment be independently reproduced, including failures, without private data?
- [ ] Will public materials label proposed/fixture/simulated/real-world status accurately?
- [ ] Are the release and incident/withdrawal responsibilities clear?

## Escalation and incident response

- **Security vulnerabilities:** use [SECURITY.md](../../SECURITY.md) and private vulnerability reporting; do not post exploit secrets or live tokens in a public issue.
- **Privacy/consent problem:** stop publication/data processing, restrict affected artifacts, alert the maintainer and institutional privacy/ethics contacts as appropriate; document remediation without exposing data.
- **Unsafe model behavior:** disable optional model/simulation execution, retain scrubbed traces and failing fixture, publish limitations, require a fix and independent retest before re-enabling.
- **Physical device interest:** keep out of default project; qualified hardware safety review and institutional/legal approvals first.
- **Scientific integrity:** correct/withdraw unsupported performance or reliability claims, preserve actual trial records and add a dated correction.

## Templates and tracked deliverables

- [Risk register template](templates/RISK-REGISTER-TEMPLATE.md)
- [Dataset card template](templates/DATASET-CARD-TEMPLATE.md)
- [Model card template](templates/MODEL-CARD-TEMPLATE.md)
- [Experiment protocol](templates/EXPERIMENT-TEMPLATE.md)
- [#67 governance workstream](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/67), [#59 simulated action gate](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/59), [#64 LLM skills](https://github.com/MSKazemi/Vagrant-Kubernetes-ROS2-Deployment/issues/64)

This guide **does not** retroactively certify or replace the repository's [SAFETY.md](../../SAFETY.md), [SECURITY.md](../../SECURITY.md), [DISCLAIMER.md](../../DISCLAIMER.md) or any institution's policies. Those remain in force.

