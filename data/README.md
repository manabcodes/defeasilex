# data/

Self-contained copies of everything the reference implementation
(`references/fria_ddl_kg_demo.py`) fetches live or embeds inline, plus
the case descriptions used across the four domains in this repository.
Created to make the architecture's inputs inspectable without running
Python or hitting the network.

## ontologies/

Verbatim snapshots of the three W3C DPV 2.2 TTL files `demo.py` fetches
live from GitHub at `TTL_URLS` (lines 41-45). Fetched on 2026-09-13.

| File | Source | Creator (per file metadata) |
|---|---|---|
| `aiact.ttl` | `w3c/dpv` `2.2/legal/eu/aiact/eu-aiact.ttl` | W3C DPV, Harshvardhan J. Pandit |
| `eu_rights.ttl` | `w3c/dpv` `2.2/legal/eu/rights/eu-rights.ttl` | W3C DPV, Harshvardhan J. Pandit (`dct:creator`); source text = Charter of Fundamental Rights of the EU, `http://data.europa.eu/eli/treaty/char_2012/oj` |
| `dpv_rights.ttl` | `w3c/dpv` `2.2/dpv/modules/rights.ttl` | W3C DPV — the abstract `dpv:Right` type hierarchy and the `dpv:hasRight` property definition |

`eu_rights.ttl` is the RDF encoding of the Charter itself — each
article is a class (`eu-rights:A21-NonDiscrimination`, etc.) with a
parallel `...Impact` class used to link a risk to the right it
affects. `dpv_rights.ttl` is the jurisdiction-agnostic schema layer
those classes are typed against. Neither the code nor these copies
pin a commit hash — if `w3c/dpv` changes upstream, these snapshots
will silently diverge from what `demo.py` fetches live. Re-run the
`curl` commands in git history / ask Claude to refresh if that
matters.

## shacl/

`hiring_shacl_shapes.ttl` — extracted verbatim from the
`SHACL_SHAPES_TTL` Python string in `demo.py` (lines 59-133). This is
the **only** SHACL shape that exists as running code anywhere in this
repository. It validates the automated-hiring domain's five boolean
compliance facts plus `dpv:hasRight`. No SHACL shapes exist for the
admissions, credit-scoring, or CCTV domains — those domains have no
code at all (see below).

## rules/

`hiring_rules.json` — the 9 `DDLRule` objects extracted verbatim from
the `RULES` list in `demo.py` (lines 321-394), converted to JSON.
This is the **only** rule base that exists as running code in this
repository.

**Important:** the worked example in the paper (`ios-book-article.tex`,
§4.1, "Essence-Boundary Reasoning in Practice") uses a *different* set
of rules (`r1`, `r2`, `r4`, `r5`, `r9`) for the university-admissions
domain. Those rules do not exist as code anywhere — not in this repo,
not in `defeasilex` (the paper's own directory). They are illustrative
formalisations written directly into the LaTeX, following the pattern
`rule-extraction.md` describes, but never run through `DDLEngine`.
Per `rule-extraction.md`'s own Step 11 ("Running the engine is
mandatory... A legal analysis document produced without running the
engine is not reproducible"), this means the admissions worked example
does not yet meet the architecture's own reproducibility bar.

## cases/

Plain-text case descriptions, split one file per domain per variant
(v1 = non-compliant, v2 = mitigated, v3 = incomplete submission),
extracted from the domain prompt files:

| Domain | Source file | Notes |
|---|---|---|
| `hiring_v{1,2,3}.txt` | `references/prompt_hiring.md` | Only domain with a matching, runnable `DDLRule` base (see rules/) |
| `admissions_v{1,2,3}.txt` | `prompts/prompt_admissions_screening.md` | No code; this is the domain used in the paper's Table 1 and worked example |
| `credit_scoring_v{1,2,3}.txt` | `prompts/prompt_credit_scoring.md` | No code |
| `cctv_v{1,2,3}.txt` | `prompts/prompt_upm_cctv.md` | No code; GDPR/LOPDGDD domain, **not** one of the three domains the paper claims to evaluate (hiring, credit scoring, admissions) — a fourth domain present in the repo but absent from the paper |

These are the natural-language scenario descriptions given to a fresh
LLM instance (per `SKILL.md`) to generate a domain-specific script, or
used as the prompt for the unconstrained-LLM comparison baseline. They
are not themselves proof of a DefeasiLex run — only `hiring_*` has a
corresponding rule base and SHACL shape checked into this repo that
can actually be executed against these facts.

## What is still missing

- **DAPRECO-KB**: no trace anywhere in this repository, in
  `defeasilex/`, or elsewhere searched. The paper's §Evaluation
  reports 5 test cases translated from DAPRECO-KB with 100% verdict
  agreement (Tables 2-3) — no translated rules, test-case script, or
  data file for this exists here. See conversation history for the
  full discussion; this should be resolved before the paper's
  evaluation claims can be called reproducible.
- **Admissions, credit-scoring, CCTV rule bases and SHACL shapes**:
  described only in prose/prompts, never encoded as `DDLRule`/SHACL
  and never run.
