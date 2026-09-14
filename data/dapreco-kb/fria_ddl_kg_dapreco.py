"""
DefeasiLex DDL engine -- DAPRECO-KB pilot subset (5 rules).

IMPORTANT PROVENANCE NOTE
==========================================================================
This file is a RECONSTRUCTION, not the original pilot code. The actual
5-rule translation and test run reported in the paper (Section 6.2,
Table tab:dapreco-summary / tab:dapreco-testcases) was produced in a
separate session, and that original source file is not available here.

This file is rebuilt from the structured data in `dapreco_performance_report.md`
(the per-rule translation table and per-test-case results table), applying
the same DDLRule / ProofTree / DDLEngine schema used in the other three
reference engines (fria_ddl_kg_demo.py, fria_ddl_kg_credit_scoring.py,
fria_ddl_kg_admissions.py) so the DAPRECO rules are expressed the same way.
The five DDLRule objects below encode exactly the fields the performance
report documents: D-KB ID, GDPR source, deontic type, priority, condition,
and defeat relations. Running this file reproduces the reported 5/5
(100%) agreement -- treat that as an independent re-check of the reported
numbers using the documented rule structure, not as recovery of the
original artifact.

The actual DAPRECO-KB source formulas these five rules were translated
FROM are in `dapreco_selection_5rules.xml` (the raw LegalRuleML excerpt),
not reproduced here -- this file is the DDL-side translation only.

Mapping (dapreco_id -> D-KB source formula key, from the performance report):
  dapreco_1  -> statements1Formula1    (GDPR Art. 5(1)(a))
  dapreco_7  -> statements5Formula1    (GDPR Art. 5(1)(e), base)
  dapreco_81 -> statements275Formula3  (GDPR Art. 89(1), archiving exception)
  dapreco_26 -> statements19Formula1-9 (GDPR Art. 6(1)/Art. 9, base; composite D-KB ID, simplified per report)
  dapreco_29 -> statements20Formula1   (GDPR Art. 6(1)(a), consent exception)
==========================================================================
"""

from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# 1. DDL ENGINE (same schema as fria_ddl_kg_demo.py / credit_scoring.py / admissions.py)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DDLRule:
    id: str
    deontic: str                  # "obligation" | "prohibition" | "permission"
    action: str
    condition: Optional[str] = None
    priority: int = 0
    defeats: list[str] = field(default_factory=list)
    defeated_by: list[str] = field(default_factory=list)
    ctd_triggers: list[str] = field(default_factory=list)
    legal_source: str = ""
    essence_boundary: bool = False
    # DAPRECO-specific provenance fields (not present in the other three engines,
    # kept here so this file is self-documenting against the source KB)
    dkb_id: str = ""
    translation_confidence: str = ""


@dataclass
class ProofTree:
    action: str
    verdict: str
    winning_rule: Optional[str]
    defeated_rules: list[str]
    active_ctd: list[str]
    reasoning_chain: list[str]
    human_review_required: bool = False


RULES: list[DDLRule] = [
    # ── TC1: universal obligation, no exception in this pilot subset ──────────
    DDLRule(
        id="dapreco_1",
        deontic="obligation",
        action="keep_processing_lawful_fair_transparent",
        condition=None, priority=8,
        legal_source="GDPR Art. 5(1)(a)",
        dkb_id="statements1Formula1",
        translation_confidence="High",
    ),
    # ── TC2/TC3: storage-limitation obligation vs. archiving exemption ────────
    DDLRule(
        id="dapreco_7",
        deontic="obligation",
        action="render_data_subject_unidentifiable",
        condition="storage_not_necessary_for_purpose", priority=9,
        defeated_by=["dapreco_81"],
        legal_source="GDPR Art. 5(1)(e)",
        dkb_id="statements5Formula1",
        translation_confidence="High",
    ),
    DDLRule(
        id="dapreco_81",
        deontic="permission",
        action="render_data_subject_unidentifiable",
        condition="retained_for_public_interest_archiving", priority=10,
        defeats=["dapreco_7"],
        legal_source="GDPR Art. 89(1)",
        dkb_id="statements275Formula3",
        translation_confidence="High",
    ),
    # ── TC4/TC5: opinion-data lawful-basis obligation vs. consent exception ───
    DDLRule(
        id="dapreco_26",
        deontic="obligation",
        action="ground_opinion_data_processing_in_lawful_basis",
        condition="processes_opinion_data", priority=11,
        defeated_by=["dapreco_29"],
        legal_source="GDPR Art. 6(1) / Art. 9 context",
        dkb_id="statements19Formula1-9",
        translation_confidence="Medium -- composite D-KB ID, simplified",
    ),
    DDLRule(
        id="dapreco_29",
        deontic="permission",
        action="ground_opinion_data_processing_in_lawful_basis",
        condition="explicit_consent_for_purpose_given", priority=12,
        defeats=["dapreco_26"],
        legal_source="GDPR Art. 6(1)(a)",
        dkb_id="statements20Formula1",
        translation_confidence="High",
    ),
]

RULE_INDEX: dict[str, DDLRule] = {r.id: r for r in RULES}


class DDLEngine:
    """Identical conflict-resolution logic to the other three engines
    (see Algorithm 1 in the paper's Architecture section)."""

    def __init__(self, rules: list[DDLRule]):
        self.rules = rules
        self.index = {r.id: r for r in rules}

    def _condition_met(self, rule: DDLRule, ctx: dict) -> bool:
        return rule.condition is None or bool(ctx.get(rule.condition, False))

    def _is_defeated(self, rule: DDLRule, active_ids: set[str]) -> bool:
        if rule.essence_boundary:
            return False
        for did in rule.defeated_by:
            if did in active_ids:
                d = self.index.get(did)
                if d and d.priority > rule.priority:
                    return True
        return False

    def evaluate(self, action: str, ctx: dict) -> ProofTree:
        chain, defeated_rules = [], []
        applicable = sorted(
            [r for r in self.rules if r.action == action and self._condition_met(r, ctx)],
            key=lambda r: r.priority, reverse=True
        )
        active_ids = {r.id for r in applicable}
        chain.append(f"Applicable rules: {[r.id for r in applicable] or 'none'}")

        if not applicable:
            return ProofTree(action, "NO_RULE", None, [], [],
                              [f"No rule covers '{action}' in this context."])

        winning_rule = None
        for rule in applicable:
            if self._is_defeated(rule, active_ids):
                defeated_rules.append(rule.id)
                defeaters = [d for d in rule.defeated_by if d in active_ids]
                chain.append(f"  x {rule.id} (p={rule.priority}) defeated by {defeaters}")
            else:
                winning_rule = rule
                chain.append(f"  v {rule.id} (p={rule.priority}) wins -- {rule.legal_source}")
                break

        if winning_rule is None:
            return ProofTree(action, "INDETERMINATE", None, defeated_rules, [],
                              chain, human_review_required=True)

        verdict = {"prohibition": "PROHIBITED", "obligation": "OBLIGATED",
                   "permission": "PERMITTED"}.get(winning_rule.deontic, "UNKNOWN")

        return ProofTree(action, verdict, winning_rule.id, defeated_rules,
                          [], chain, human_review_required=winning_rule.essence_boundary)


# ─────────────────────────────────────────────────────────────────────────────
# 2. TEST HARNESS -- reproduces TC1-TC5 from dapreco_performance_report.md
# ─────────────────────────────────────────────────────────────────────────────

TEST_CASES = [
    dict(id="TC1", action="keep_processing_lawful_fair_transparent",
         ctx={}, expected_verdict="OBLIGATED", expected_winner="dapreco_1"),
    dict(id="TC2", action="render_data_subject_unidentifiable",
         ctx={"storage_not_necessary_for_purpose": True},
         expected_verdict="OBLIGATED", expected_winner="dapreco_7"),
    dict(id="TC3", action="render_data_subject_unidentifiable",
         ctx={"storage_not_necessary_for_purpose": True,
              "retained_for_public_interest_archiving": True},
         expected_verdict="PERMITTED", expected_winner="dapreco_81"),
    dict(id="TC4", action="ground_opinion_data_processing_in_lawful_basis",
         ctx={"processes_opinion_data": True},
         expected_verdict="OBLIGATED", expected_winner="dapreco_26"),
    dict(id="TC5", action="ground_opinion_data_processing_in_lawful_basis",
         ctx={"processes_opinion_data": True,
              "explicit_consent_for_purpose_given": True},
         expected_verdict="PERMITTED", expected_winner="dapreco_29"),
]


def run_pilot():
    engine = DDLEngine(RULES)
    print("=" * 78)
    print("  DAPRECO-KB PILOT -- 5-RULE DDL RE-RUN (reconstructed engine)")
    print("=" * 78)
    agreements = 0
    for tc in TEST_CASES:
        tree = engine.evaluate(tc["action"], tc["ctx"])
        agree = (tree.verdict == tc["expected_verdict"]
                  and tree.winning_rule == tc["expected_winner"])
        agreements += int(agree)
        status = "AGREE" if agree else "DISAGREE"
        print(f"\n{tc['id']}: action={tc['action']}")
        print(f"  context           : {tc['ctx'] or '(none)'}")
        print(f"  expected          : {tc['expected_verdict']} (winner={tc['expected_winner']})")
        print(f"  actual            : {tree.verdict} (winner={tree.winning_rule})")
        for line in tree.reasoning_chain:
            print(f"    {line}")
        print(f"  result            : {status}")

    print("\n" + "=" * 78)
    print(f"  SUMMARY: {agreements}/{len(TEST_CASES)} agreements "
          f"({100 * agreements // len(TEST_CASES)}%)")
    print("=" * 78)


if __name__ == "__main__":
    run_pilot()
