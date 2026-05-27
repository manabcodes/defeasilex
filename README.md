# DefeasiLex

**A Claude skill package for reproducible legal compliance reasoning using Defeasible Deontic Logic, SHACL, and Knowledge Graphs.**

DefeasiLex teaches a fresh Claude instance to model legal compliance scenarios as executable, auditable proof trees (and not prose documents that are essentially free prose with thought associations). It was built to address a specific problem: engineers, compliance teams, and lawyers already use LLMs to answer legal questions, and they get inconsistent, unauditable, and sometimes wrong answers. DefeasiLex makes that reasoning consistent, transparent, bounded, and honest about what it cannot resolve.

---

## The architecture

```
  LLM explanation layer      ← plain-language output from proof trees
        ↑
  DDL reasoning engine       ← defeasible, prioritised, non-monotonic rules
        ↑
  SHACL validation gate      ← blocks reasoning if facts are incomplete
        ↑
  RDF/OWL knowledge graph    ← real W3C ontology triples + instance facts
        ↑
  Rule extraction layer      ← statute text → DDL rules (rule-extraction.md)
```

**Defeasible Deontic Logic (DDL)** is the normative core. Unlike RDF/OWL, which is monotonic, DDL can model norm conflicts, priority relations, exceptions that defeat general rules, and compensatory obligations that fire when a primary duty is violated. This is at least a little bit closer to how law actually works.

**SHACL** is the completeness gate. Reasoning never runs over incomplete submissions. Missing facts produce specific, legally-sourced error messages, not verdicts.

**The LLM** has two roles only: extract compliance facts from documents (with human review), and explain proof trees in plain language. It never participates in normative reasoning.

---

## What it produces

For each scenario assessed, the engine produces:

- A **verdict** per action: PROHIBITED / OBLIGATED / PERMITTED / INDETERMINATE
- A **proof tree** showing which rule won, which were defeated, and why
- **CTD obligations**: compensatory duties that fire when a prohibition is violated
- **Human review flags**: essence-boundary norms (EU Charter Art. 52(3)) that the machine cannot resolve autonomously
- An **HTML visualizer** with an interactive compliance dashboard

---

## Repository structure

```
DefeasiLex/
├── SKILL.md                          ← base skill for FRIA / AI Act cases
├── skill-extended.md                 ← extended skill: rule extraction,
│                                       visualizer, multi-level norm handling
├── rule-extraction.md                ← statute text → DDL rules pipeline
│
├── references/
│   ├── fria_ddl_kg_demo.py           ← canonical reference implementation
│   └── prompt_hiring.md              ← domain prompt for the reference case
│
└── prompts/
    ├── prompt_credit_scoring.md      ← consumer credit scoring domain
    ├── prompt_admissions_screening.md← university admissions screening domain
    └── prompt_upm_cctv.md            ← CCTV surveillance domain
```

---

## How to use

### With a fresh Claude instance

1. Upload `SKILL.md` (or `skill-extended.md` for rule extraction and visualizer)
2. Upload `references/fria_ddl_kg_demo.py`
3. Send one of the prompts from `prompts/`, or write your own domain prompt

Claude will produce a working Python script implementing the full three-layer architecture for your domain, run it, and present the proof trees.

### Running the reference implementation

```bash
pip install rdflib pyshacl
python references/fria_ddl_kg_demo.py
```

Fetches W3C DPV ontologies live from GitHub on first run. No other dependencies.

### Writing your own domain prompt

Follow the format in `prompts/prompt_credit_scoring.md`:

- Describe the AI system and its decision
- Give three variants: non-compliant (v1), mitigated (v2), incomplete submission (v3)
- List the Charter articles at stake
- Do not mention Python, DDL, or architecture, please let the skill handle that

---

## Key design decisions

**Priority numbers are interpretive legal judgments, not settled doctrine.** The CJEU has never produced a formal hierarchy of Charter rights. Every priority assignment above 15 and every `essence_boundary=True` flag encodes a defensible interpretation of CJEU doctrine and Charter structure (not an authoritative ruling). The architecture forces these judgments into the open so they can be inspected, challenged, and revised. A lawyer should review the rule base before it is used in production.

**The SHACL gate is mandatory.** A partial submission does not get a verdict. It gets specific, legally-sourced error messages. This is the machine-readable answer to garbage-in-garbage-out.

**The essence boundary is a design primitive.** `essence_boundary=True` on a rule means the prohibition cannot be defeated by any lower-priority norm. It also means the engine sets `human_review_required=True`, and then the machine stops and escalates. The location of the essence boundary is a legal judgment, not a logical derivation. DefeasiLex makes that boundary explicit and mandatory rather than leaving it implicit in prose.

**The goal is not correctness. The goal is making wrongness visible, reproducible, and fixable**. which is a precondition for correctness over time.

---

## Regulatory grounding

The reference implementation covers:

- EU Charter of Fundamental Rights (Arts. 1, 7, 8, 21, 24, 34, 41, 47, 52(3))
- AI Act Art. 27 (Fundamental Rights Impact Assessment) + Annex III
- GDPR Arts. 5, 6, 9, 22, 33, 35
- AI-HLEG Seven Requirements for Trustworthy AI
- W3C Data Privacy Vocabulary (DPV) 2.2: live ontologies

---

## Related work

DefeasiLex builds on and extends:

- Rintamäki & Pandit, FRIA ontology (DPV extension for AI Act Art. 27)
- Casanovas et al., Computable models of law, defeasible legal reasoning
- W3C DPV Community Group, `eu-aiact`, `eu-rights` ontologies

---

## Dependencies

```
rdflib
pyshacl
```

---

## License

MIT

---

*DefeasiLex = defeasible + lex. Also: difícil.*
