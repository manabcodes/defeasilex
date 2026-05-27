---
name: rule-extraction
description: >
  Use this skill whenever DDL rules need to be derived from legal text —
  statutes, regulations, directives, agency guidance, or any normative
  document. Triggers include: user provides a law article and asks to
  model it; a domain requires rules from a national law not already in
  the rule base; web search has retrieved legal provisions that need to
  be encoded; a prior assessment missed a legal constraint because it
  was not extracted from the source text. Always use together with
  skill-extended.md or SKILL.md. This skill produces rules. Those skills
  run the engine. Rule extraction without running the engine is incomplete.
---

# Rule Extraction Skill

This skill teaches how to read legal text in any language and produce
correct DDL rules for the SHACL-KG-DDL architecture.

The pipeline is:

```
Legal text → identify deontic operator → test defeasibility
           → identify subject and action → map domain terms
           → assign priority → write DDLRule → flag for review
           → add to rule base → RUN THE ENGINE
```

Running the engine is mandatory. A legal analysis document is not
acceptable output. The proof tree is the output.

---

## Step 1 — Retrieve the source text

Before extracting rules, retrieve the actual text of the provision.
Do not rely on memory or paraphrase. If the text is in another language,
translate it literally before extracting — do not interpret during
translation.

For EU law: fetch from EUR-Lex.
For national law: search for the official consolidated text.
For agency guidance: search the relevant authority's website.

---

## Step 2 — Identify the deontic operator

Read each sentence of the provision and classify it:

| Signal (any language) | Deontic | Example |
|---|---|---|
| shall not / must not / is prohibited / no se admitirá / est interdit / ist verboten / è vietato / не допускается | **prohibition** | "In no case shall..." |
| shall / must / is required / deberá / doit / muss / deve | **obligation** | "The controller must..." |
| may / is permitted / podrá / peut / darf / può | **permission** | "Controllers may process..." |
| notwithstanding / sin perjuicio / nonobstant / unbeschadet | **override signal** | "Notwithstanding Art. X, ..." |
| unless / except / save where / salvo que / sauf si / außer wenn | **defeasibility signal** | "...unless consent is given" |

Translate signal phrases before classifying. The deontic structure of
law is language-independent — the same logical operators appear in
every legal system.

---

## Step 3 — Test for defeasibility

For every prohibition or obligation identified in Step 2, ask:

**Does the provision contain any of these?**
- "unless" / "except" / "save where"
- "provided that" / "subject to"
- "where justified" / "where necessary"
- Or their equivalents in the source language

**If NO exceptions are present → the rule is absolute.**
- Set `essence_boundary=True`
- Set `defeated_by=[]`
- Do not add defeating conditions that are not in the text
- Do not soften an absolute prohibition into a defeasible one

**If exceptions ARE present → the rule is defeasible.**
- Each exception becomes a separate permission rule that defeats
  the prohibition
- The exception's condition becomes the `condition=` field
- The prohibition's `defeated_by=` lists the exception rule's id

**The most common extraction error** is reading an absolute prohibition,
noting that a related provision elsewhere provides an exception, and
incorrectly marking the prohibition as defeasible. Each provision must
be read on its own terms first. Cross-provision defeating relationships
must be explicit in the text, not inferred.

---

## Step 4 — Identify subject and action

For each rule, identify:

**Subject** — who does this norm apply to?
- All controllers / all persons
- Public authorities only
- Private entities only
- Specific sector (employers, healthcare providers, etc.)

If the norm applies only to a subset, add a `condition=` field that
reflects this (e.g. `condition="public_authority"`,
`condition="employment_context"`).

**Action** — what specifically is prohibited, obligated, or permitted?

Write the action as a short snake_case verb phrase that is:
- Specific enough to distinguish from other actions
- General enough to apply across domain variants
- Derived from the operative verb in the provision, not from the
  article heading

---

## Step 5 — Map domain terms

Legal texts use domain-specific terminology. Map each term to its
action string equivalent before writing the rule.

Process:
1. Identify the specific term in the provision
2. Identify what it refers to in the deployment context
3. Write the action string using the deployment context term
4. Document the mapping as a comment in the rule

Examples of the mapping process (not domain-specific):
- A term referring to a specific physical space → generalise to the
  function that space serves (rest, work, treatment, etc.)
- A term referring to a specific document type → generalise to the
  compliance function it serves (assessment, notification, record)
- A term in the source language → translate to English for the action
  string, document the original in `legal_source`

---

## Step 6 — Assign priority

Use the norm level of the source provision:

| Norm level | Priority range |
|---|---|
| Constitutional / Charter absolute floor | 25–30 |
| Charter essence-boundary rights in context | 20–24 |
| National law absolute prohibitions | 20–24 |
| Strong positive duties / sector law obligations | 15–19 |
| Sector-specific obligations | 10–14 |
| General background obligations | 5–9 |
| Defeasible permissions | 4–6 |

**Lex specialis:** Where a national provision adds specificity to an EU
provision, the national rule gets higher priority than the EU baseline.
Where a national provision reduces protection below the EU floor, it is
invalid — do not encode it, flag for human review.

**Priority is relational, not absolute.** What matters is that the
correct rule wins every conflict in the rule base. After writing all
rules, check every pair of rules that could conflict and verify the
priority ordering produces the correct legal outcome.

---

## Step 7 — Write the DDLRule

```python
DDLRule(
    id="r_<short_descriptive_id>",
    deontic="prohibition",          # or "obligation" / "permission"
    action="<snake_case_action>",   # from Step 4/5
    condition=None,                 # or context flag from Step 4
    priority=20,                    # from Step 6
    defeats=[],                     # ids of rules this defeats
    defeated_by=[],                 # ids of rules that defeat this
                                    # EMPTY if absolute (Step 3)
    ctd_triggers=[],                # compensatory obligations if violated
    legal_source="<Instrument> Art. <N> — <quoted operative phrase>",
    eu_right="Art<N>",              # Charter article if applicable
    essence_boundary=True,          # True if absolute (Step 3)
)
```

The `legal_source` field must quote the operative phrase from the
provision — not the article heading, not a paraphrase, the actual
normative language. This is the audit trail.

---

## Step 8 — Identify CTD obligations

For every prohibition, ask: if this prohibition is violated, what must
happen next?

Common CTD patterns:
- Notify a supervisory authority (with time limit)
- Suspend the system or processing
- Provide remedy to affected persons
- Conduct an impact assessment

Each CTD obligation is a separate DDLRule with:
- `deontic="obligation"`
- Priority higher than the primary prohibition (it must fire even
  when the prohibition is contested)
- `legal_source` citing the provision that creates the compensatory duty

---

## Step 9 — Add to SHACL shapes

For every boolean fact the new rules read from context, add a
corresponding `sh:property` block to the SHACL shapes TTL string.

Each new shape property must:
- Use `sh:path fria:<fact_name>` matching the `condition=` or
  context flag exactly
- Have `sh:minCount 1` so missing facts block the engine
- Have `sh:message` citing the legal source of the requirement

---

## Step 10 — Flag for human review

Before committing rules to the rule base, flag the following for
review by a qualified lawyer:

- Every `essence_boundary=True` rule — the boundary location is
  a legal judgment, not a logical derivation
- Every priority assignment above 15 — these encode relative
  importance of norms, which is contestable
- Every CTD chain — compensatory obligations sometimes depend on
  jurisdiction-specific enforcement practice
- Every rule where the extraction required inferring a cross-provision
  defeating relationship not explicit in the text

The rule base is a documented legal judgment, not a derivation from
first principles. Flagging does not block the engine — it creates
the audit trail.

---

## Step 11 — Run the engine

Add the new rules to the rule base and run the Python script.

**This step is mandatory. No exceptions.**

A legal analysis document produced without running the engine is:
- Not reproducible
- Not auditable
- Not the output this architecture produces

If the engine does not run, go back and fix the rules until it does.
The proof tree is the output.

---

## Common extraction errors

**Error 1 — Softening an absolute prohibition**
The text says "in no case." The extractor adds a defeating condition
because a related provision elsewhere permits an exception.
Fix: Each provision is absolute or defeasible on its own terms.
Cross-provision relationships must be explicit.

**Error 2 — Missing the operative provision**
The extractor reads the article heading or a recital and encodes that,
missing the operative rule in the body of the article.
Fix: Always extract from the operative paragraph, not the heading.

**Error 3 — Wrong deontic**
"May" is a permission, not an obligation. "Shall" is an obligation,
not a permission. Confusing these inverts the logic of the rule.
Fix: Classify the deontic operator before writing anything else.

**Error 4 — Producing a document instead of running the engine**
The extractor produces a written legal analysis summarising what
the rules say, without adding them to the rule base and running
the Python script.
Fix: Rules go into the engine. The engine produces the output.
There is no intermediate document step.

**Error 5 — Encoding agency guidance as hard rules**
Agency guidance informs what "appropriate measures" means but is
not binding law. Encode it as conditions or comments, not as
defeating rules.
Fix: Only binding provisions get DDLRule entries. Guidance informs
the `legal_source` annotation and the SHACL message text.
