from __future__ import annotations

import re
import uuid
from typing import Any

from brain_store import BrainStore, downstream_effects_for

AMBIGUITY_MAP = {"sales engineer": ["Sales", "Engineering"]}

ROLE_DEFAULTS = {
    "backend engineer": {
        "department": "Engineering",
        "it_groups": ["engineering-core", "github-users"],
        "finance_tier": "engineering-tools",
        "reporting_line": "Engineering",
        "confidence": 94,
    },
    "accountant": {
        "department": "Finance",
        "it_groups": ["finance-core", "erp-users"],
        "finance_tier": "standard",
        "reporting_line": "Finance",
        "confidence": 93,
    },
}


class AgentEngine:
    def __init__(self, brain: BrainStore, gpt: Any):
        self.brain = brain
        self.gpt = gpt
        self.roster: list[dict[str, Any]] = []
        self.pending: dict[str, dict[str, Any]] = {}

    def onboard(self, trigger: str) -> dict[str, Any]:
        try:
            facts = self._safe_facts(self.gpt.extract_facts(trigger), trigger)
            gpt_ok = True
            gpt_error = None
        except Exception as exc:
            facts = self._fallback_pending_facts(trigger)
            gpt_ok = False
            gpt_error = str(exc)

        role_key = norm(facts.get("role_title"))
        matched_rule = self.brain.find_rule(facts.get("role_title"), facts.get("location"))
        ambiguity_options = AMBIGUITY_MAP.get(role_key)
        needs_resolution = bool(ambiguity_options and not matched_rule)

        if matched_rule:
            facts["department"] = matched_rule["department_resolved"]
            effects = matched_rule["downstream_effects"]
            confidence = 96
            status = "Auto-resolved"
        elif needs_resolution:
            effects = {"it_groups": ["sales-core OR engineering-core"], "finance_tier": "sales-field OR engineering-tools", "reporting_line": "Sales OR Engineering"}
            confidence = 58
            status = "Needs decision"
        else:
            defaults = ROLE_DEFAULTS.get(role_key) or {
                "department": facts.get("department") or "Operations",
                "it_groups": ["standard-users"],
                "finance_tier": "standard",
                "reporting_line": facts.get("department") or "Operations",
                "confidence": 88,
            }
            facts["department"] = facts.get("department") or defaults["department"]
            effects = defaults
            confidence = int(defaults.get("confidence", 88))
            status = "Onboarded"

        context = {"needs_resolution": needs_resolution, "matched_rule": matched_rule, "effects": effects}
        try:
            reasons = self.gpt.plan_reasons(facts, context)
        except Exception:
            reasons = {"reasoning": "Plan generated from deterministic company policy and stored decisions.", "row_reasons": {}}

        employee = {
            "id": str(uuid.uuid4())[:8],
            "name": facts.get("full_name") or "pending",
            "role": facts.get("role_title") or "pending",
            "location": facts.get("location") or "pending",
            "department": facts.get("department") or "pending",
            "status": status,
        }
        plan = self._build_plan(facts, effects, confidence, needs_resolution, bool(matched_rule), reasons.get("row_reasons") or {})
        response = {
            "employee": employee,
            "facts": facts,
            "beats": ["PERCEIVE", "REASON", "ACT"] + (["HAND OFF"] if needs_resolution else []),
            "plan": plan,
            "needs_resolution": needs_resolution,
            "ambiguity": self._ambiguity_payload(facts, ambiguity_options) if needs_resolution else None,
            "matched_rule_id": matched_rule["id"] if matched_rule else None,
            "matched_rule": matched_rule,
            "reasoning": reasons.get("reasoning"),
            "gpt_ok": gpt_ok,
            "gpt_error": gpt_error,
        }
        if needs_resolution:
            self.pending[employee["id"]] = response
        else:
            self.roster.append(employee)
        return response

    def resolve(self, employee_id: str, department: str) -> dict[str, Any]:
        if employee_id not in self.pending:
            raise KeyError("No pending ambiguity for that employee")
        item = self.pending.pop(employee_id)
        facts = item["facts"]
        rule = self.brain.add_rule(facts.get("full_name") or item["employee"]["name"], facts.get("role_title") or item["employee"]["role"], facts.get("location") or item["employee"]["location"], department)
        effects = downstream_effects_for(department)
        item["employee"]["department"] = department
        item["employee"]["status"] = "Onboarded"
        item["plan"] = self._build_plan(facts | {"department": department}, effects, 95, False, True, {})
        item["resolved_rule"] = rule
        self.roster.append(item["employee"])
        return rule

    def query_brain(self, query: str) -> dict[str, Any]:
        matches = self.brain.search(query)
        if not matches:
            return {"answer": "No decision recorded for that yet.", "sources": []}
        try:
            answer = self.gpt.answer_from_rules(query, matches)
        except Exception:
            first = matches[0]
            answer = f"{first['source_role']} is classified as {first['department_resolved']} based on {first['source_employee']}'s decision. Source: {first['id']}."
        return {"answer": answer, "sources": matches}

    def reset_runtime(self) -> None:
        self.roster = []
        self.pending = {}

    def _build_plan(self, facts: dict[str, Any], effects: dict[str, Any], confidence: int, needs_resolution: bool, learned: bool, row_reasons: dict[str, str]) -> list[dict[str, Any]]:
        groups = effects.get("it_groups", [])
        group_text = ", ".join(groups) if isinstance(groups, list) else str(groups)
        rows = [
            ("IT", "Create account", "User identity", 96, "Auto-executed"),
            ("IT", "Assign access groups", group_text, confidence, "Pending decision" if needs_resolution else "Auto-executed"),
            ("HR", "Set department/reporting", effects.get("reporting_line", "pending"), confidence, "Pending decision" if needs_resolution else "Prepared"),
            ("Finance", "Set expense tier", effects.get("finance_tier", "pending"), confidence, "Pending decision" if needs_resolution else "Prepared"),
        ]
        plan = []
        for idx, (domain, action, target, conf, status) in enumerate(rows):
            key = f"row_{idx}"
            if learned and idx > 0:
                reason = "Company Brain matched a stored decision."
            elif needs_resolution and idx > 0:
                reason = "Sales vs Engineering changes this downstream item."
            else:
                reason = row_reasons.get(key) or "High confidence from intake facts and policy."
            plan.append({"domain": domain, "action": action, "target": target, "confidence": conf, "status": status, "reason": reason, "learned": learned and idx > 0})
        return plan

    @staticmethod
    def _safe_facts(raw: dict[str, Any], trigger: str) -> dict[str, Any]:
        facts = {k: raw.get(k) for k in ["full_name", "role_title", "location", "start_date", "manager", "department"]}
        # Small deterministic cleanup for camera-reliable chips.
        if not facts.get("full_name") or not facts.get("role_title") or not facts.get("location"):
            fallback = AgentEngine._fallback_pending_facts(trigger)
            for key, value in fallback.items():
                facts[key] = facts.get(key) or value
        facts["missing_fields"] = raw.get("missing_fields") or []
        facts["notes"] = raw.get("notes") or "Extracted from intake trigger."
        return facts

    @staticmethod
    def _fallback_pending_facts(trigger: str) -> dict[str, Any]:
        parts = [p.strip() for p in re.split(r",| joins as | starts as ", trigger) if p.strip()]
        name = parts[0] if parts else "pending"
        role = next((p for p in parts if any(word in p.lower() for word in ["engineer", "accountant", "advocate"])), "pending")
        location = parts[-1] if len(parts) > 2 else "pending"
        return {"full_name": name, "role_title": role, "location": location, "start_date": "pending", "manager": "pending", "department": None, "missing_fields": ["start_date", "manager"], "notes": "Partial fallback rendering; GPT unavailable or incomplete."}

    @staticmethod
    def _ambiguity_payload(facts: dict[str, Any], options: list[str] | None) -> dict[str, Any]:
        return {
            "role": facts.get("role_title"),
            "message": f"{facts.get('role_title')} matches both Sales and Engineering departments.",
            "options": options or [],
            "context": [
                {"option": "Sales", "it_access": "CRM, sales-core", "finance_tier": "sales-field", "reporting": "Sales"},
                {"option": "Engineering", "it_access": "GitHub, engineering-core", "finance_tier": "engineering-tools", "reporting": "Engineering"},
            ],
        }


def norm(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())
