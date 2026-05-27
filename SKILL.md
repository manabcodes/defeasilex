---
name: fria-ddl-kg
description: >
  Use this skill whenever a user wants to model a legal compliance or
  rights-impact scenario using the SHACL + Knowledge Graph + Defeasible
  Deontic Logic (DDL) + LLM explanation architecture. Triggers include:
  any mention of fundamental rights assessment, FRIA, AI Act Art. 27,
  regulatory compliance reasoning, norm conflict, defeasible rules, or
  any request to "model this scenario like the hiring example." Also
  trigger when the user describes a situation involving competing legal
  obligations, prohibited actions with exceptions, or compensatory duties
  — even if they don't use the technical terms. If the user gives you a
  domain and three variants, this skill is almost certainly what they need.
---

# FRIA DDL + KG Skill

This skill enables you to take any legal/compliance domain and produce a
working Python script that implements the full three-layer architecture:

```
  LLM explanation layer      ← plain-language output from proof trees
        ↑
  DDL reasoning engine       ← defeasible, prioritised, non-monotonic rules
        ↑
  SHACL validation gate      ← blocks reasoning if facts are incomplete
        ↑
  RDF/OWL knowledge graph    ← real W3C ontology triples + instance facts
```

---

## Reference file

Before writing any code, read the canonical implementation:

```
references/fria_ddl_kg_demo.py
```

This is a complete, working script for the **automated hiring** domain.
Every component you need to adapt is present and annotated. Read it fully
before proceeding — do not reconstruct the pattern from memory.

---

## What to keep (don't change)

- The three-layer class structure: `DDLRule`, `ProofTree`, `DDLEngine`
- The `load_ontologies()` function and the three W3C TTL URLs
- The `assert_hiring_system()` / `sparql_context()` bridge pattern
- The `SHACL_GRAPH` + `validate_system()` gate — always runs before DDL
- The `print_fria_report()` output format
- The per-system isolated graph pattern in `main` (fresh graph per variant)
- `pyshacl` + `rdflib` as the only dependencies

---

## What to replace for a new domain

Work through these five substitutions in order:

### 1. Rights (`EU_RIGHTS` instances)

Identify which EU Charter articles are at stake in the new domain.
Map each to its `eu-rights:` URI from the W3C TTL:

```
https://raw.githubusercontent.com/w3c/dpv/master/2.2/legal/eu/rights/eu-rights.ttl
```

Common articles and their URIs:

| Charter Article | URI fragment |
|---|---|
| Art. 1 — Human Dignity | `A1-HumanDignity` |
| Art. 6 — Liberty & Security | `A6-RightToLibertyAndSecurity` |
| Art. 7 — Private Life | `A7-RespectForPrivateAndFamilyLife` |
| Art. 8 — Personal Data | `A8-ProtectionOfPersonalData` |
| Art. 21 — Non-Discrimination | `A21-NonDiscrimination` |
| Art. 34 — Social Security | `A34-SocialSecurityAndSocialAssistance` |
| Art. 35 — Health Care | `A35-Healthcare` |
| Art. 41 — Good Administration | `A41-RightToGoodAdministration` |
| Art. 47 — Effective Remedy | `A47-RightToEffectiveRemedyFairTrial` |

Add the `sparql_right_label()` mapping for each article you use.

### 2. DDL Rules

Replace the `RULES` list entirely. For each rule ask:

- What is the **general obligation or prohibition**? (deontic, action, priority)
- What **specific exception** defeats it? (defeated_by, condition)
- Does a **higher norm** defeat even the exception? (essence_boundary=True for Art. 52(3))
- If the primary duty is violated, what **compensatory obligation** fires? (ctd_triggers)
- What is the **legal source**? (cite article + instrument)

Priority guidance:
- 1–9: general background obligations
- 10–14: sector-specific obligations
- 15–19: strong positive duties
- 20+: inviolable prohibitions (essence-boundary candidates)

### 3. SHACL shapes (`SHACL_SHAPES_TTL` string)

One `sh:property` block per boolean compliance fact the DDL engine reads.
Each block must have:
- `sh:path fria:<fact_name>`
- `sh:datatype xsd:boolean`
- `sh:minCount 1 ; sh:maxCount 1`
- `sh:message` — cite the legal source of the requirement

Also keep the `dpv:hasRight sh:minCount 1` block.

### 4. `ACTIONS_TO_ASSESS` list

List every `action` string that appears in your `RULES`. One entry per
unique action. The DDL engine iterates over these.

### 5. `SYSTEMS` dict — three variants

Always provide exactly three variants:

| Variant | Purpose |
|---|---|
| `_v1` | Worst case — multiple violations, CTD obligations firing |
| `_v2` | Mitigated — key issues resolved, but essence-boundary rule still flags |
| `_v3` | Incomplete submission — missing 2–3 facts, blocked by SHACL gate |

`_v3` must be missing facts that map to different legal sources
(e.g. one GDPR, one AI Act article) so the SHACL error messages are
informative rather than generic.

---

## The prompt to give a user

When the user describes a new domain, ask them (or infer from context):

1. What does the AI system decide or assess?
2. Who is affected, and what rights are at stake?
3. What is the general rule (prohibition/obligation)?
4. What exception could defeat it?
5. What higher-priority norm defeats even the exception?
6. What must happen if the primary duty is violated (compensatory)?
7. What facts would a compliance questionnaire ask?

You do not need all answers up front — infer reasonable defaults from
the domain and EU Charter, then let the user correct them.

---

## Output

Produce a single self-contained Python file named
`fria_ddl_kg_<domain>.py` that:

- Runs with `python fria_ddl_kg_<domain>.py` (no arguments)
- Requires only `rdflib` and `pyshacl` (`pip install rdflib pyshacl`)
- Fetches the W3C TTLs live from GitHub on first run
- Prints SHACL validation result, then DDL proof trees, then LLM
  plain-language explanations for all three variants
- Blocks `_v3` at the SHACL gate with specific, legally-sourced messages

---

## Prompt template (give this to the user or use it yourself)

```
You have access to the fria-ddl-kg skill. Using the reference
implementation at references/fria_ddl_kg_demo.py as your template,
produce a complete Python script for the following domain:

DOMAIN: <one sentence describing the AI system and its decision>

VARIANTS:
  v1 — <description of the non-compliant system>
  v2 — <description of the mitigated system>
  v3 — <description of the incomplete submission, naming which
         facts are missing>

RIGHTS AT STAKE: <list Charter articles>

Follow the skill instructions exactly. Keep all three layers.
Do not simplify or remove the SHACL gate.
```

---

## Validation checklist before presenting output

- [ ] All three W3C TTL URLs present and unchanged
- [ ] Each `DDLRule` has a `legal_source` citing a real article
- [ ] At least one rule has `essence_boundary=True`
- [ ] At least one rule has `ctd_triggers`
- [ ] `_v3` is missing at least 2 facts with different legal sources
- [ ] SHACL shapes cover every fact in every `compliance_facts` dict
- [ ] `sparql_right_label()` mapping covers every `eu_right` used in rules
- [ ] Fresh graph per system in `main` loop
- [ ] Script runs end-to-end without errors
