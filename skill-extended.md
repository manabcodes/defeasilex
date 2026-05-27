---
name: fria-ddl-kg-extended
description: >
  Extended version of the fria-ddl-kg skill. Use this version when the
  task involves any of: (1) extracting DDL rules from statute text or
  legal documents — use rule-extraction.md in conjunction; (2) producing
  a visual proof tree or compliance dashboard alongside the Python output;
  (3) multi-level norm systems (national law + EU regulation + agency
  guidance); (4) non-FRIA legal domains (surveillance, employment,
  healthcare, housing). For pure FRIA/AI Act cases with rules already
  known, the base SKILL.md is sufficient. When in doubt, use this one.
---

# FRIA DDL + KG Skill — Extended

This skill extends the base SKILL.md with three additions:

1. **Rule extraction** — how to derive DDL rules from statute text
   (use together with `rule-extraction.md`)
2. **Visualizer** — how to produce an HTML proof tree alongside the
   Python engine output
3. **Multi-level norm handling** — how to encode national law + EU
   regulation + agency guidance as a priority hierarchy

Read the base `SKILL.md` first. This file adds to it, not replaces it.
Read `references/fria_ddl_kg_demo.py` before writing any code.

---

## Architecture (extended)

```
  LLM explanation layer      ← plain-language output from proof trees
        ↑                       also feeds the HTML visualizer
  DDL reasoning engine       ← defeasible, prioritised, non-monotonic
        ↑                       rules derived from statute text
  SHACL validation gate      ← blocks reasoning if facts are incomplete
        ↑
  RDF/OWL knowledge graph    ← real W3C ontology triples + instance facts
        ↑
  Rule extraction layer      ← statute text → DDL rules (rule-extraction.md)
```

The rule extraction layer is upstream of everything else. If rules are
wrong, everything downstream is wrong. See `rule-extraction.md`.

---

## Addition 1 — Rule Extraction

Before building the rule base for a new domain, read `rule-extraction.md`
and follow its pipeline. Summary of what it teaches:

**Deontic operator detection (language-agnostic):**

| Signal phrases | Deontic | Default defeasibility |
|---|---|---|
| shall not / must not / is prohibited / en ningún caso / in no case / interdit / verboten | prohibition | Check for "unless/except" — if absent: absolute |
| shall / must / is required / deberá / doit / muss | obligation | Usually defeasible — check for exceptions |
| may / is permitted / podrá / peut / darf | permission | Defeasible by higher norm |
| notwithstanding / sin perjuicio de / nonobstant | override signal | The following norm defeats what precedes |

**Absolute prohibition test:**
If the provision contains no "unless," "except," "save where," "salvo
que," "sauf si," or equivalent — it is absolute. Set
`essence_boundary=True` and `defeated_by=[]`. Do not add defeating
conditions that are not in the text.

**Priority assignment from norm level:**

| Norm level | Priority range |
|---|---|
| Constitutional / Charter absolute floor (dignity, child protection) | 25–30 |
| Charter essence-boundary rights in context (Art. 21, Art. 24) | 20–24 |
| National law absolute prohibitions | 20–24 |
| Strong positive duties / sector law | 15–19 |
| Sector-specific obligations | 10–14 |
| General background obligations / GDPR baseline | 5–9 |
| Defeasible permissions | 4–6 |

**Lex specialis rule:**
Where a national provision is more specific than the EU regulation it
implements, the national provision defeats the general EU rule.
Encode this as higher priority, not as a separate namespace.

**MANDATORY:** After extracting rules from text, run the Python engine.
A legal analysis document is not acceptable output. The proof tree is
the output. If the engine does not run, the assessment is not complete.

---

## Addition 2 — Visualizer

After the Python engine runs and proof trees are confirmed correct,
produce an HTML visualizer showing the compliance status of all
variants side by side.

### What the visualizer shows

```
┌─────────────────────────────────────────────────────────────┐
│  COMPLIANCE DASHBOARD  — [Domain]                           │
├─────────────┬─────────────┬─────────────┬───────────────────┤
│  Action     │   v1        │   v2        │   v3              │
├─────────────┼─────────────┼─────────────┼───────────────────┤
│  action_1   │ 🔴 PROHIB  │ 🟢 PERMIT  │ 🚫 BLOCKED        │
│  action_2   │ 🟡 OBLIG   │ 🟡 OBLIG   │ 🚫 BLOCKED        │
│  ...        │ ...         │ ...         │ ...               │
├─────────────┼─────────────┼─────────────┼───────────────────┤
│  OVERALL    │ ❌ NON-COMP │ ⚠ HUM.REV │ 🚫 INCOMPLETE     │
└─────────────┴─────────────┴─────────────┴───────────────────┘

[Click any cell to expand proof tree and plain-language explanation]
```

### How to produce it

After the Python script runs cleanly, produce a second file:
`fria_ddl_kg_<domain>_viz.html`

The HTML file:
- Is self-contained (no external dependencies except optional CDN)
- Embeds the proof tree data as a JSON object in a `<script>` tag
- Renders the dashboard table with colour-coded verdict cells
- On cell click, expands an accordion showing the proof chain steps
  and the plain-language LLM explanation for that action/variant
- Shows the SHACL error messages for blocked variants in a distinct
  red panel rather than a proof tree

### Visualizer data structure

Extract this from the Python engine output:

```python
viz_data = {
    "domain": "Credit Scoring",
    "variants": ["v1", "v2", "v3"],
    "actions": [...],  # ACTIONS_TO_ASSESS
    "results": {
        "v1": {
            "action_name": {
                "verdict": "PROHIBITED",
                "winning_rule": "r4_nondiscrimination",
                "defeated_rules": [...],
                "active_ctd": [...],
                "reasoning_chain": [...],
                "explanation": "...",
                "human_review_required": True
            }
        },
        "v3": {
            "shacl_blocked": True,
            "violations": [
                "Missing: explanation_provided ...",
                "Missing: human_oversight_assigned ..."
            ]
        }
    }
}
```

Pass `viz_data` from the Python script into the HTML template via
`json.dumps()` embedded in the HTML `<script>` block.

### Colour coding — individual cells

| Verdict | Colour | Icon |
|---|---|---|
| PROHIBITED (no CTD) | amber | 🟡 |
| PROHIBITED (CTD active) | red | 🔴 |
| OBLIGATED (fulfilled) | green | 🟢 |
| OBLIGATED (CTD active = unfulfilled) | red | 🔴 |
| PERMITTED | green | 🟢 |
| INDETERMINATE | orange | 🟠 |
| SHACL BLOCKED | dark red panel | 🚫 |
| Human review required | orange badge | ⚠ |

### Overall status row — per variant

The overall status row must distinguish three legally distinct outcomes.
Do not collapse all non-green variants into a single NON-COMPLIANT label.

| Condition | Label | Colour |
|---|---|---|
| Any PROHIBITED verdict where `human_review_required=False` | ❌ NON-COMPLIANT | red |
| All verdicts OBLIGATED/PERMITTED but any `human_review_required=True` | ⚠ REQUIRES LEGAL REVIEW | orange |
| All obligations fulfilled, no prohibitions, no human review flags | ✅ COMPLIANT | green |
| SHACL blocked | 🚫 INCOMPLETE | dark red |

**Why this matters:** A variant where the only non-green result is an
essence-boundary human review flag is legally and practically different
from one with confirmed violations. Conflating them misrepresents the
engine output and defeats the purpose of the `essence_boundary` flag.

**JavaScript logic to implement this:**

```javascript
const hasConfirmedViolation = Object.values(res).some(
  r => r.verdict === "PROHIBITED" && !r.human_review_required
);
const needsReview = Object.values(res).some(r => r.human_review_required);
const shaclBlocked = res.shacl_blocked === true;

let statusLabel, statusClass;
if (shaclBlocked) {
  statusLabel = "🚫 INCOMPLETE";          statusClass = "status-blocked";
} else if (hasConfirmedViolation) {
  statusLabel = "❌ NON-COMPLIANT";       statusClass = "status-noncompliant";
} else if (needsReview) {
  statusLabel = "⚠ REQUIRES LEGAL REVIEW"; statusClass = "status-review";
} else {
  statusLabel = "✅ COMPLIANT";           statusClass = "status-compliant";
}
```

---

## Addition 3 — Multi-level norm handling

When the domain involves national law + EU regulation + agency guidance,
encode the hierarchy explicitly in the rule base.

### The three-level pattern

```
Level 3: Agency guidance (soft law — informs what "appropriate" means)
  → Encode as conditions on obligations, not as separate rules
  → Reference in legal_source but do not give separate priority slot

Level 2: National law (lex specialis — defeats EU defaults)
  → Higher priority than the EU provision it specialises
  → Encode the national provision as a separate rule with higher priority

Level 1: EU regulation (general floor)
  → Baseline priority range 5–14
  → Cannot be defeated by national law that reduces protection
  → Can be defeated by national law that adds specificity
```

### Critical check before writing rules

For every national provision, ask:
- Does it **add specificity** to an EU provision? → lex specialis,
  higher priority, can defeat EU default
- Does it **reduce protection** below the EU floor? → invalid,
  do not encode, flag for human review
- Is it **independent** of the EU provision? → separate rule,
  priority based on norm level

### Public authority lawful basis trap

Where the controller is a public authority:
- GDPR Art. 6(1)(f) (legitimate interest) **does not apply**
- The correct basis is Art. 6(1)(e) (public task)
- National law providing the specific public task mandate is the
  "law" required under Art. 6(3)
- Encode this as: Art. 6(1)(e) permission, condition=`public_task_documented`,
  defeated_by the absolute prohibition rules

Add a SHACL shape requiring `public_authority` and `public_task_documented`
as boolean facts for any domain where the controller may be a public body.

---

## Validation checklist (extended)

All items from base SKILL.md, plus:

- [ ] Rule extraction followed `rule-extraction.md` pipeline
- [ ] Every absolute prohibition was tested for "unless/except" — if
      absent, `essence_boundary=True` and `defeated_by=[]`
- [ ] Multi-level norm hierarchy encoded correctly (national lex
      specialis > EU general)
- [ ] Public authority lawful basis check done if applicable
- [ ] Python engine runs end-to-end before HTML visualizer is produced
- [ ] Visualizer embeds proof tree data from actual engine output,
      not reconstructed from memory
- [ ] SHACL blocked variants show error messages in visualizer,
      not empty proof trees
- [ ] **Engine run is mandatory. No legal analysis document without
      a proof tree. No exceptions.**
