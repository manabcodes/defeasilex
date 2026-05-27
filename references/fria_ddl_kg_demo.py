"""
FRIA DDL + Knowledge Graph Demo
================================
Full three-layer architecture for the automated hiring case study.

Layers:
  1. RDF/OWL Knowledge Graph  — real W3C DPV/AI-Act TTL files (rdflib)
  1a. SHACL Validation         — enforces completeness before reasoning runs
  2. DDL Reasoning Engine      — defeasible, prioritised, non-monotonic
  3. LLM Explanation Layer     — stubbed template (swap in real API call)

Regulatory grounding:
  EU Charter Art. 8, 21, 41, 47, 52(3)
  AI Act Art. 27, Annex III (Employment Sector)
  W3C DPV 2.2 + eu-aiact + eu-rights ontologies (fetched live from GitHub)
"""

from __future__ import annotations
import textwrap
from dataclasses import dataclass, field
from typing import Optional

# ── rdflib (KG layer) + pyshacl (validation layer) ──────────────────────────
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS
from rdflib.namespace import SKOS, OWL, XSD
from pyshacl import validate as shacl_validate

# ─────────────────────────────────────────────────────────────────────────────
# NAMESPACES  (matching the real DPV TTL files)
# ─────────────────────────────────────────────────────────────────────────────
DPV        = Namespace("https://w3id.org/dpv#")
EU_AIACT   = Namespace("https://w3id.org/dpv/legal/eu/aiact#")
EU_RIGHTS  = Namespace("https://w3id.org/dpv/rights/eu#")
FRIA_EX    = Namespace("https://example.org/fria/hiring#")   # our instance data


# ─────────────────────────────────────────────────────────────────────────────
# 1. KG LAYER — load real DPV TTLs + assert hiring system instance triples
# ─────────────────────────────────────────────────────────────────────────────

TTL_URLS = {
    "aiact":    "https://raw.githubusercontent.com/w3c/dpv/master/2.2/legal/eu/aiact/eu-aiact.ttl",
    "eu_rights":"https://raw.githubusercontent.com/w3c/dpv/master/2.2/legal/eu/rights/eu-rights.ttl",
    "dpv_rights":"https://raw.githubusercontent.com/w3c/dpv/master/2.2/dpv/modules/rights.ttl",
}

# ─────────────────────────────────────────────────────────────────────────────
# 1a. SHACL SHAPES — enforce that every required compliance fact is present
#     before the DDL engine is allowed to run.
#
#     Each sh:property block corresponds to one boolean fact the DDL engine
#     reads from the KG.  minCount 1 means: if this predicate is missing
#     entirely, validation fails and reasoning is blocked.
#
#     This is the machine-readable answer to "garbage in, garbage out" —
#     the system refuses to reason over an incomplete FRIA submission.
# ─────────────────────────────────────────────────────────────────────────────

SHACL_SHAPES_TTL = """
@prefix sh:      <http://www.w3.org/ns/shacl#> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix eu-aiact: <https://w3id.org/dpv/legal/eu/aiact#> .
@prefix dpv:     <https://w3id.org/dpv#> .
@prefix fria:    <https://example.org/fria/hiring#> .

# Every high-risk AI system in the employment sector MUST declare
# all five compliance facts before a FRIA can proceed.

fria:HiringSystemShape
    a sh:NodeShape ;
    sh:targetClass eu-aiact:HighRiskAISystem ;
    sh:name "FRIA Completeness Check (AI Act Art. 27)" ;

    # 1. Has the deployer obtained explicit consent for sensitive data?
    sh:property [
        sh:path fria:explicit_consent ;
        sh:datatype xsd:boolean ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:name "explicit_consent" ;
        sh:message "Missing: explicit_consent — required by GDPR Art. 9 / AI Act Art. 27(1)(b)."
    ] ;

    # 2. Does the system use proxy attributes for protected characteristics?
    sh:property [
        sh:path fria:uses_proxy_attributes ;
        sh:datatype xsd:boolean ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:name "uses_proxy_attributes" ;
        sh:message "Missing: uses_proxy_attributes — required to assess Art. 21 non-discrimination risk."
    ] ;

    # 3. Has a bias audit been conducted before deployment?
    sh:property [
        sh:path fria:bias_audit_done ;
        sh:datatype xsd:boolean ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:name "bias_audit_done" ;
        sh:message "Missing: bias_audit_done — required by AI Act Art. 9(7)."
    ] ;

    # 4. Does the system provide explanations for automated decisions?
    sh:property [
        sh:path fria:explanation_provided ;
        sh:datatype xsd:boolean ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:name "explanation_provided" ;
        sh:message "Missing: explanation_provided — required by AI Act Art. 13 / EU Charter Art. 41."
    ] ;

    # 5. Has a human oversight officer been assigned?
    sh:property [
        sh:path fria:human_oversight_assigned ;
        sh:datatype xsd:boolean ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:name "human_oversight_assigned" ;
        sh:message "Missing: human_oversight_assigned — required by AI Act Art. 14."
    ] ;

    # 6. At least one fundamental right must be declared at risk.
    sh:property [
        sh:path dpv:hasRight ;
        sh:minCount 1 ;
        sh:name "impacted_rights" ;
        sh:message "Missing: at least one impacted right must be declared (EU Charter / AI Act Art. 27)."
    ] .
"""

SHACL_GRAPH = Graph().parse(data=SHACL_SHAPES_TTL, format="turtle")


def validate_system(g: Graph, system_id: str) -> tuple[bool, list[str]]:
    """
    Run SHACL validation on the instance graph for system_id.
    Returns (passed: bool, violations: list[str]).
    If passed is False, the DDL engine must not run.
    """
    conforms, _, report_text = shacl_validate(
        data_graph=g,
        shacl_graph=SHACL_GRAPH,
        inference="none",
        abort_on_first=False,
        allow_infos=False,
        allow_warnings=False,
        meta_shacl=False,
        debug=False,
    )

    violations = []
    if not conforms:
        for line in report_text.splitlines():
            line = line.strip()
            if line.startswith("Message:"):
                violations.append(line.replace("Message:", "").strip())
        # Fallback if parsing found nothing
        if not violations:
            violations = [l.strip() for l in report_text.splitlines()
                          if l.strip() and "Missing:" in l]

    return conforms, violations


def load_ontologies(ttl_paths: dict[str, str]) -> Graph:
    """Load remote TTL files into a single rdflib Graph."""
    g = Graph()
    for name, url in ttl_paths.items():
        print(f"  Loading {name} … ", end="", flush=True)
        try:
            g.parse(url, format="turtle")
            print("✓")
        except Exception as e:
            print(f"✗ ({e})")
    return g


def assert_hiring_system(g: Graph, system_id: str, facts: dict) -> None:
    """
    Assert instance triples for a hiring AI system onto the KG.
    In the real architecture this populates from a FRIA questionnaire form.
    """
    sys = FRIA_EX[system_id]

    # System type: high-risk AI in employment sector (AI Act Annex III §4)
    g.add((sys, RDF.type, EU_AIACT.HighRiskAISystem))
    g.add((sys, RDF.type, OWL.NamedIndividual))
    g.add((sys, RDFS.label, Literal(facts["label"])))
    g.add((sys, DPV.hasContext, EU_AIACT.EmploymentSector))

    # Rights potentially impacted (from eu-rights TTL)
    for right_uri in facts["impacted_rights"]:
        g.add((sys, DPV.hasRight, URIRef(right_uri)))

    # FRIA process node
    fria = FRIA_EX[f"{system_id}_fria"]
    g.add((fria, RDF.type, EU_AIACT.FRIA))
    g.add((fria, DPV.isImplementedByEntity, sys))

    # Boolean compliance facts (used by DDL context dict below)
    for key, val in facts["compliance_facts"].items():
        predicate = FRIA_EX[key]
        g.add((sys, predicate, Literal(val, datatype=XSD.boolean)))


def sparql_context(g: Graph, system_id: str) -> dict:
    """
    Query the KG for facts the DDL engine needs.
    Returns a plain dict — the bridge between KG and DDL layers.
    """
    sys = FRIA_EX[system_id]
    ctx = {}

    # Pull every boolean compliance fact asserted for this system
    for pred, obj in g.predicate_objects(sys):
        local = str(pred).split("#")[-1].split("/")[-1]
        if isinstance(obj, Literal) and obj.datatype == XSD.boolean:
            ctx[local] = bool(obj)

    # Add derived flags
    ctx["automated_hiring_context"] = True
    ctx["automated_decision_affecting_individual"] = True
    ctx["high_risk_ai_system"] = True

    # Fetch impacted rights labels for the report
    ctx["_impacted_rights"] = []
    for _, right_uri in g.subject_objects(DPV.hasRight):
        label = g.value(URIRef(right_uri), SKOS.prefLabel)
        if label:
            ctx["_impacted_rights"].append(str(label))

    # System label
    ctx["_label"] = str(g.value(sys, RDFS.label) or system_id)
    return ctx


def build_rights_index(g: Graph) -> dict[str, str]:
    """
    Build a full article-key → prefLabel mapping dynamically from the
    eu-rights TTL graph at runtime.

    Walks every subject in the EU_RIGHTS namespace that has a SKOS prefLabel
    and extracts the article number from the URI fragment (e.g.
    'A8-ProtectionOfPersonalData' → key 'Art8', label 'A8 Protection Of
    Personal Data').

    This replaces the hardcoded mapping — any Charter article present in
    the live TTL is automatically available without touching the code.
    Art34, Art2, Art6, Art35, Art49 etc. all resolve correctly.
    """
    index: dict[str, str] = {}
    for subj in g.subjects(SKOS.prefLabel, None):
        uri_str = str(subj)
        if str(EU_RIGHTS) not in uri_str:
            continue
        fragment = uri_str.split("#")[-1].split("/")[-1]  # e.g. "A8-ProtectionOfPersonalData"
        if not fragment.startswith("A"):
            continue
        # Extract article number: "A8-..." → "Art8", "A21-..." → "Art21"
        num = fragment[1:].split("-")[0]
        if num.isdigit():
            key = f"Art{num}"
            label = g.value(URIRef(uri_str), SKOS.prefLabel)
            if label:
                index[key] = str(label)
    return index


# Module-level rights index — populated after ontologies are loaded
_RIGHTS_INDEX: dict[str, str] = {}


def sparql_right_label(g: Graph, article: str) -> str:
    """
    Resolve a Charter article key (e.g. 'Art8', 'Art21', 'Art34') to its
    DPV prefLabel using the dynamically built rights index.

    Falls back to the raw key if the article is not found in the graph —
    which surfaces URI mismatches rather than silently hiding them.
    """
    global _RIGHTS_INDEX
    if not _RIGHTS_INDEX:
        _RIGHTS_INDEX = build_rights_index(g)
    return _RIGHTS_INDEX.get(article, article)


# ─────────────────────────────────────────────────────────────────────────────
# 2. DDL ENGINE
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
    eu_right: str = ""            # Charter article key for KG lookup
    essence_boundary: bool = False  # Art. 52(3) — inviolable


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
    # ── PRIVACY ──────────────────────────────────────────────────────────────
    DDLRule(
        id="r1_privacy_prohibition",
        deontic="prohibition", action="process_sensitive_data",
        priority=5, defeated_by=["r2_explicit_consent"],
        ctd_triggers=["r3_notify_supervisory_authority"],
        legal_source="EU Charter Art. 8; GDPR Art. 9; AI Act Art. 27(1)(b)",
        eu_right="Art8",
    ),
    DDLRule(
        id="r2_explicit_consent",
        deontic="permission", action="process_sensitive_data",
        condition="explicit_consent", priority=6,
        defeats=["r1_privacy_prohibition"],
        defeated_by=["r4_nondiscrimination_hiring"],
        legal_source="GDPR Art. 9(2)(a); AI Act Recital 72",
        eu_right="Art8",
    ),
    # ── NON-DISCRIMINATION ────────────────────────────────────────────────────
    DDLRule(
        id="r4_nondiscrimination_hiring",
        deontic="prohibition",
        action="use_proxy_attributes_for_protected_characteristics",
        condition="automated_hiring_context", priority=20,
        defeats=["r2_explicit_consent"],
        ctd_triggers=["r5_remediation_obligation"],
        legal_source="EU Charter Art. 21; AI Act Art. 5(1)(c); Annex III §4",
        eu_right="Art21", essence_boundary=True,
    ),
    DDLRule(
        id="r4b_bias_audit_obligation",
        deontic="obligation", action="conduct_bias_audit_before_deployment",
        condition="automated_hiring_context", priority=15,
        legal_source="AI Act Art. 9(7); AI-HLEG Requirement 4 (Diversity)",
        eu_right="Art21",
    ),
    # ── TRANSPARENCY ─────────────────────────────────────────────────────────
    DDLRule(
        id="r6_transparency_obligation",
        deontic="obligation", action="provide_explanation_of_automated_decision",
        condition="automated_decision_affecting_individual", priority=10,
        ctd_triggers=["r7_effective_remedy_ctd"],
        legal_source="EU Charter Art. 41/47; AI Act Art. 13; AI-HLEG Req. 4",
        eu_right="Art41",
    ),
    DDLRule(
        id="r7_effective_remedy_ctd",
        deontic="obligation", action="enable_human_review_of_decision",
        priority=12,
        legal_source="EU Charter Art. 47; AI Act Art. 14 (human oversight)",
        eu_right="Art47",
    ),
    # ── HUMAN OVERSIGHT ──────────────────────────────────────────────────────
    DDLRule(
        id="r8_human_oversight",
        deontic="obligation", action="assign_human_oversight_officer",
        condition="high_risk_ai_system", priority=10,
        legal_source="AI Act Art. 14; AI-HLEG Requirement 1 (Human Agency)",
    ),
    # ── CONTRARY-TO-DUTY ─────────────────────────────────────────────────────
    DDLRule(
        id="r3_notify_supervisory_authority",
        deontic="obligation", action="notify_supervisory_authority_within_72h",
        priority=10,
        legal_source="GDPR Art. 33; AI Act Art. 73",
    ),
    DDLRule(
        id="r5_remediation_obligation",
        deontic="obligation", action="suspend_system_and_conduct_impact_review",
        priority=18,
        legal_source="AI Act Art. 27(4); EU Charter Art. 47",
    ),
]

RULE_INDEX: dict[str, DDLRule] = {r.id: r for r in RULES}
ACTIONS_TO_ASSESS = [
    "process_sensitive_data",
    "use_proxy_attributes_for_protected_characteristics",
    "conduct_bias_audit_before_deployment",
    "provide_explanation_of_automated_decision",
    "assign_human_oversight_officer",
]


class DDLEngine:
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
        chain, defeated_rules, active_ctd = [], [], []
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
                chain.append(f"  ✗ {rule.id} (p={rule.priority}) defeated by {defeaters}")
            else:
                winning_rule = rule
                chain.append(f"  ✓ {rule.id} (p={rule.priority}) wins — {rule.legal_source}")
                break

        if winning_rule is None:
            return ProofTree(action, "INDETERMINATE", None, defeated_rules, [],
                             chain, human_review_required=True)

        verdict = {"prohibition": "PROHIBITED", "obligation": "OBLIGATED",
                   "permission": "PERMITTED"}.get(winning_rule.deontic, "UNKNOWN")

        # Fire CTD if the prohibited action is actually present in context
        ctx_flag = action.replace("use_", "uses_").replace(
            "use_proxy_attributes_for_protected_characteristics",
            "uses_proxy_attributes")
        if winning_rule.deontic == "prohibition" and ctx.get(ctx_flag, False):
            for ctd_id in winning_rule.ctd_triggers:
                active_ctd.append(ctd_id)
                ctd_rule = self.index.get(ctd_id)
                src = ctd_rule.legal_source if ctd_rule else ""
                chain.append(f"  ⚡ CTD triggered: {ctd_id} ({src})")

        return ProofTree(action, verdict, winning_rule.id, defeated_rules,
                         active_ctd, chain,
                         human_review_required=winning_rule.essence_boundary)

    def run_fria(self, ctx: dict) -> dict[str, ProofTree]:
        return {a: self.evaluate(a, ctx) for a in ACTIONS_TO_ASSESS}


# ─────────────────────────────────────────────────────────────────────────────
# 3. LLM EXPLANATION LAYER (stub)
# ─────────────────────────────────────────────────────────────────────────────

def llm_explain(tree: ProofTree, g: Graph) -> str:
    rule = RULE_INDEX.get(tree.winning_rule or "")
    source = rule.legal_source if rule else "unknown"
    right_label = ""
    if rule and rule.eu_right:
        right_label = sparql_right_label(g, rule.eu_right)
        if right_label:
            right_label = f" (protects: {right_label})"

    if tree.verdict == "PROHIBITED":
        txt = (f"This action is PROHIBITED under {source}{right_label}.")
        if tree.active_ctd:
            ctd_actions = [RULE_INDEX[c].action for c in tree.active_ctd if c in RULE_INDEX]
            txt += f" Violation detected — compensatory obligations now active: {ctd_actions}."
    elif tree.verdict == "OBLIGATED":
        txt = f"This action is OBLIGATED under {source}{right_label}."
    elif tree.verdict == "PERMITTED":
        txt = (f"This action is PERMITTED under {source}{right_label}, "
               f"having defeated lower-priority rules: {tree.defeated_rules}.")
    else:
        txt = "This action requires human legal review — the engine cannot resolve it autonomously."

    if tree.human_review_required:
        txt += " ⚠ Art. 52(3) Charter: essence-of-right boundary — human compliance officer review required."
    return txt


# ─────────────────────────────────────────────────────────────────────────────
# 4. REPORTING
# ─────────────────────────────────────────────────────────────────────────────

ICON = {"PROHIBITED": "🔴", "OBLIGATED": "🟡", "PERMITTED": "🟢",
        "INDETERMINATE": "🟠", "NO_RULE": "⚪"}
W = 72


def print_fria_report(system_id: str, ctx: dict, results: dict[str, ProofTree],
                      g: Graph) -> bool:
    print("=" * W)
    print(f"  FRIA REPORT — AI Act Art. 27  |  System: {system_id}")
    print(f"  {ctx.get('_label', system_id)}")
    if ctx.get("_impacted_rights"):
        print(f"  Rights at stake: {', '.join(ctx['_impacted_rights'])}")
    print("=" * W)

    compliant = True
    for action, tree in results.items():
        icon = ICON.get(tree.verdict, "❓")
        print(f"\n{icon}  ACTION: {action}")
        print(f"    Verdict : {tree.verdict}")
        print(f"    Rule    : {tree.winning_rule or '—'}")
        if tree.defeated_rules:
            print(f"    Defeated: {tree.defeated_rules}")
        if tree.active_ctd:
            print(f"    CTD     : {tree.active_ctd}")
        print(f"    Proof chain:")
        for step in tree.reasoning_chain:
            print(f"      {step}")
        explanation = llm_explain(tree, g)
        print(f"\n    Plain-language (LLM layer):")
        print(textwrap.fill(explanation, W - 4, initial_indent="      ",
                            subsequent_indent="      "))
        if tree.verdict == "PROHIBITED" or tree.human_review_required:
            compliant = False

    print("\n" + "=" * W)
    status = "❌  NON-COMPLIANT" if not compliant else "✅  COMPLIANT"
    print(f"  OVERALL FRIA STATUS: {status}")
    print("=" * W + "\n")
    return compliant


# ─────────────────────────────────────────────────────────────────────────────
# 5. SYSTEM DEFINITIONS  (in real use: loaded from FRIA questionnaire)
# ─────────────────────────────────────────────────────────────────────────────

SYSTEMS = {
    "cv_screener_v1": {
        "label": "CV Screener v1 — uses zip-code proxy, no explanation module",
        "impacted_rights": [
            str(EU_RIGHTS["A8-ProtectionOfPersonalData"]),
            str(EU_RIGHTS["A21-NonDiscrimination"]),
            str(EU_RIGHTS["A47-RightToEffectiveRemedyFairTrial"]),
        ],
        "compliance_facts": {
            "explicit_consent": False,
            "uses_proxy_attributes": True,
            "explanation_provided": False,
            "bias_audit_done": False,
            "human_oversight_assigned": False,
        },
    },
    "cv_screener_v2": {
        "label": "CV Screener v2 — consented, proxy-free, SHAP explanations, HR override",
        "impacted_rights": [
            str(EU_RIGHTS["A8-ProtectionOfPersonalData"]),
            str(EU_RIGHTS["A21-NonDiscrimination"]),
        ],
        "compliance_facts": {
            "explicit_consent": True,
            "uses_proxy_attributes": False,
            "explanation_provided": True,
            "bias_audit_done": True,
            "human_oversight_assigned": True,
        },
    },
    "cv_screener_v3": {
        "label": "CV Screener v3 — incomplete FRIA submission (simulates LLM extraction gap)",
        "impacted_rights": [
            str(EU_RIGHTS["A8-ProtectionOfPersonalData"]),
            str(EU_RIGHTS["A21-NonDiscrimination"]),
        ],
        # Deliberately missing: bias_audit_done, explanation_provided
        # This simulates what happens when LLM fact extraction fails to
        # extract all required fields from a technical spec document.
        "compliance_facts": {
            "explicit_consent": True,
            "uses_proxy_attributes": False,
            "human_oversight_assigned": True,
        },
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# 6. MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n── Loading W3C DPV / AI Act ontologies from GitHub ──")
    base_g = load_ontologies(TTL_URLS)
    print(f"   Ontology graph size: {len(base_g)} triples\n")

    engine = DDLEngine(RULES)

    for system_id, system_def in SYSTEMS.items():
        # Fresh instance graph per system, seeded from the shared ontology.
        # Keeps each system's compliance facts isolated — no cross-contamination.
        g = Graph()
        for triple in base_g:
            g.add(triple)

        # Assert this system's instance triples into its own graph
        assert_hiring_system(g, system_id, system_def)

        # ── SHACL GATE ────────────────────────────────────────────────────────
        # Validate completeness BEFORE the DDL engine runs.
        # If any required fact is missing, block reasoning and report why.
        print(f"── SHACL validation: {system_id} ──")
        passed, violations = validate_system(g, system_id)
        if not passed:
            print(f"  🚫 BLOCKED — incomplete FRIA submission. DDL engine will not run.")
            print(f"     The following required fields are missing:\n")
            for v in violations:
                print(f"     • {v}")
            print(f"\n     Fix: ensure all compliance facts are present before resubmitting.\n")
            print("=" * W + "\n")
            continue
        print(f"  ✅ Validation passed — proceeding to DDL reasoning.\n")
        # ─────────────────────────────────────────────────────────────────────

        # Bridge: KG facts → DDL context dict
        ctx = sparql_context(g, system_id)

        # Run DDL reasoning
        results = engine.run_fria(ctx)

        # Print report (LLM layer enriches with KG right labels)
        print_fria_report(system_id, ctx, results, g)
