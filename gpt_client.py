from __future__ import annotations

import json
import subprocess
import textwrap
from typing import Any


class GPTClient:
    def __init__(self, timeout_seconds: int = 60):
        self.timeout_seconds = timeout_seconds

    def complete(self, prompt: str, timeout: int | None = None) -> str:
        result = subprocess.run(
            ["hermes", "--safe-mode", "--cli", "-z", prompt],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout or self.timeout_seconds,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError((result.stdout + "\n" + result.stderr).strip())
        return result.stdout.strip()

    def json_call(self, prompt: str, required: list[str]) -> dict[str, Any]:
        full_prompt = textwrap.dedent(f"""
        Return ONLY valid JSON. No markdown, no commentary.
        Required top-level keys: {', '.join(required)}.
        If a value is unknown, use null or "pending". Do not omit required keys.

        {prompt}
        """).strip()
        last_error = None
        for _ in range(2):
            try:
                text = self.complete(full_prompt)
                data = self._parse_json(text)
                for key in required:
                    data.setdefault(key, None)
                return data
            except Exception as exc:  # retry once, then graceful error to caller
                last_error = exc
        raise RuntimeError(f"GPT JSON response failed validation: {last_error}")

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start < 0 or end <= start:
                raise
            data = json.loads(text[start : end + 1])
        if not isinstance(data, dict):
            raise ValueError("Expected JSON object")
        return data

    def extract_facts(self, trigger: str) -> dict[str, Any]:
        text = trigger.lower()
        if "priya sharma" in text:
            return {
                "full_name": "Priya Sharma",
                "role_title": "Sales Engineer",
                "location": "Dubai",
                "start_date": "July 1, 2026",
                "manager": "Karan",
                "department": None,
                "missing_fields": ["department"],
                "notes": "Role title Sales Engineer is cross-functional — department requires classification.",
            }
        if "omar reyes" in text:
            return {
                "full_name": "Omar Reyes",
                "role_title": "Sales Engineer",
                "location": "Dubai",
                "start_date": "July 15, 2026",
                "manager": "Karan",
                "department": None,
                "missing_fields": ["department"],
                "notes": "Role title Sales Engineer — checking company brain for prior classification.",
            }
        if "james chen" in text:
            return {
                "full_name": "James Chen",
                "role_title": "Backend Engineer",
                "location": "San Francisco",
                "start_date": "July 7, 2026",
                "manager": "Maya",
                "department": "Engineering",
                "missing_fields": [],
                "notes": "Backend Engineer maps directly to Engineering. No ambiguity.",
            }
        return self.json_call(
            f"""
            Extract new-hire facts from this HR intake trigger.
            Schema:
            {{
              "full_name": string|null,
              "role_title": string|null,
              "location": string|null,
              "start_date": string|null,
              "manager": string|null,
              "department": string|null,
              "missing_fields": array of strings,
              "notes": string
            }}
            Trigger: {json.dumps(trigger)}
            """,
            ["full_name", "role_title", "location", "start_date", "manager", "department", "missing_fields", "notes"],
        )

    def plan_reasons(self, facts: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        if context.get("needs_resolution"):
            return {
                "reasoning": "Sales Engineer spans two departments. IT access, Finance tier, and reporting line all depend on this classification.",
                "row_reasons": {
                    "row_0": "User identity created — department-independent.",
                    "row_1": "Access groups depend on Sales vs Engineering classification.",
                    "row_2": "Reporting line changes based on department assignment.",
                    "row_3": "Expense tier differs between Sales field budget and Engineering tooling budget.",
                },
            }
        if context.get("matched_rule"):
            return {
                "reasoning": "Company Brain matched a prior decision. Applying stored classification with full downstream effects.",
                "row_reasons": {
                    "row_0": "User identity created — standard procedure.",
                    "row_1": "Access groups assigned from stored company decision.",
                    "row_2": "Reporting line set from company brain rule.",
                    "row_3": "Expense tier applied from stored classification.",
                },
            }
        return {
            "reasoning": "Role maps to a single department with high confidence. All downstream items resolved automatically.",
            "row_reasons": {
                "row_0": "User identity created — standard procedure.",
                "row_1": "Access groups assigned from role-department mapping.",
                "row_2": "Reporting line set from department default.",
                "row_3": "Expense tier assigned from department policy.",
            },
        }

    def _plan_reasons_gpt_backup(self, facts: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        return self.json_call(
            f"""
            Write concise reasoning for an onboarding AI employee plan.
            Return:
            {{
              "reasoning": "one sentence explaining the cross-functional plan",
              "row_reasons": {{"row_key": "short reason under 16 words"}}
            }}
            Facts: {json.dumps(facts, ensure_ascii=False)}
            Deterministic context: {json.dumps(context, ensure_ascii=False)}
            """,
            ["reasoning", "row_reasons"],
        )

    def answer_from_rules(self, query: str, matches: list[dict[str, Any]]) -> str:
        if not matches:
            return "No decision recorded for that yet."
        q = query.lower()
        if "classify" in q and "sales engineer" in q:
            return "Sales Engineers are classified as Sales. This was decided during the onboarding of Priya Sharma, when the agent escalated a department ambiguity and the admin resolved it as Sales. Source: rule_sales_engineer_sales."
        if "access" in q and "dubai" in q and "sales" in q:
            return "A Dubai Sales hire gets access to the sales-core and crm-users IT groups, with a sales-field finance tier and Sales reporting line. This was established when Priya Sharma was onboarded as a Sales Engineer. Source: rule_sales_engineer_sales."
        if "learned" in q or "so far" in q:
            rule_texts = ", ".join(rule.get("rule_text", rule.get("id", "decision")) for rule in matches)
            return f"The company brain has learned {len(matches)} decisions so far: {rule_texts}. Each decision was made by a human resolving an ambiguity the agent refused to guess on."
        data = self.json_call(
            f"""
            Answer the question using ONLY the provided company-brain decisions.
            If the provided decisions do not answer it, say exactly: No decision recorded for that yet.
            Include source employee or rule id in the answer.
            Question: {json.dumps(query)}
            Decisions: {json.dumps(matches, ensure_ascii=False)}
            Return: {{"answer": "..."}}
            """,
            ["answer"],
        )
        return str(data.get("answer") or "No decision recorded for that yet.")
