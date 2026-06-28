from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SAMPLE_RULES = [
    {
        "id": "rule_backend_engineer_engineering",
        "rule_text": "Backend Engineer = Engineering for San Francisco onboarding.",
        "source_employee": "James Chen",
        "source_role": "Backend Engineer",
        "location": "San Francisco",
        "department_resolved": "Engineering",
        "timestamp": "2026-06-28T09:00:00+00:00",
        "downstream_effects": {
            "it_groups": ["engineering-core", "github-users"],
            "finance_tier": "engineering-tools",
            "reporting_line": "Engineering",
        },
    },
    {
        "id": "rule_account_executive_sales_dubai",
        "rule_text": "Account Executive = Sales for Dubai onboarding.",
        "source_employee": "Aisha Rahman",
        "source_role": "Account Executive",
        "location": "Dubai",
        "department_resolved": "Sales",
        "timestamp": "2026-06-28T09:08:00+00:00",
        "downstream_effects": {
            "it_groups": ["sales-core", "crm-users"],
            "finance_tier": "sales-field",
            "reporting_line": "Sales",
        },
    },
    {
        "id": "rule_accountant_finance",
        "rule_text": "Accountant = Finance for Dubai onboarding.",
        "source_employee": "Nadia Khan",
        "source_role": "Accountant",
        "location": "Dubai",
        "department_resolved": "Finance",
        "timestamp": "2026-06-28T09:16:00+00:00",
        "downstream_effects": {
            "it_groups": ["finance-core", "erp-users"],
            "finance_tier": "standard",
            "reporting_line": "Finance",
        },
    },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class BrainStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.reset()

    def _read(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("rules"), list):
                return data
        except Exception:
            pass
        return {"rules": []}

    def _write(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def reset(self) -> None:
        self._write({"rules": []})

    def seed_samples(self) -> list[dict[str, Any]]:
        data = self._read()
        existing_ids = {rule.get("id") for rule in data["rules"]}
        for rule in SAMPLE_RULES:
            if rule["id"] not in existing_ids:
                data["rules"].append(dict(rule))
        self._write(data)
        return data["rules"]

    def all_rules(self) -> list[dict[str, Any]]:
        return list(self._read()["rules"])

    @staticmethod
    def norm(value: str | None) -> str:
        return " ".join((value or "").lower().strip().split())

    def add_rule(self, source_employee: str, source_role: str, location: str, department: str) -> dict[str, Any]:
        data = self._read()
        role_n = self.norm(source_role)
        loc_n = self.norm(location)
        dept_n = self.norm(department)
        for rule in data["rules"]:
            if self.norm(rule.get("source_role")) == role_n and self.norm(rule.get("department_resolved")) == dept_n:
                return rule
        slug = f"{role_n.replace(' ', '_')}_{dept_n.replace(' ', '_')}" or "decision"
        rule = {
            "id": f"rule_{slug}",
            "rule_text": f"{source_role} = {department} for {location} onboarding.",
            "source_employee": source_employee,
            "source_role": source_role,
            "location": location,
            "department_resolved": department,
            "timestamp": now_iso(),
            "downstream_effects": downstream_effects_for(department),
        }
        data["rules"].append(rule)
        self._write(data)
        return rule

    def find_rule(self, role: str | None, location: str | None = None) -> dict[str, Any] | None:
        role_n = self.norm(role)
        loc_n = self.norm(location)
        for rule in self.all_rules():
            if self.norm(rule.get("source_role")) != role_n:
                continue
            rule_loc = self.norm(rule.get("location"))
            if not loc_n or not rule_loc or rule_loc == loc_n or rule_loc in loc_n or loc_n in rule_loc:
                return rule
        return None

    def search(self, query: str) -> list[dict[str, Any]]:
        q = self.norm(query)
        if not q:
            return []
        query_terms = {t.rstrip("s") for t in q.replace("?", "").split() if len(t) > 2}
        if any(phrase in q for phrase in ["learned", "brain", "so far", "what has"]):
            return self.all_rules()[:3]
        matches: list[dict[str, Any]] = []
        for rule in self.all_rules():
            hay = self.norm(json.dumps(rule, ensure_ascii=False))
            score = sum(1 for term in query_terms if term in hay)
            if score:
                item = dict(rule)
                item["_score"] = score
                matches.append(item)
        matches.sort(key=lambda r: r.get("_score", 0), reverse=True)
        return matches[:3]


def downstream_effects_for(department: str) -> dict[str, Any]:
    if department == "Sales":
        return {
            "it_groups": ["sales-core", "crm-users"],
            "finance_tier": "sales-field",
            "reporting_line": "Sales",
        }
    if department == "Engineering":
        return {
            "it_groups": ["engineering-core", "github-users"],
            "finance_tier": "engineering-tools",
            "reporting_line": "Engineering",
        }
    return {"it_groups": ["standard-users"], "finance_tier": "standard", "reporting_line": department}
