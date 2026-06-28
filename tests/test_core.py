import json
import tempfile
import unittest
from pathlib import Path

from brain_store import BrainStore
from agent_engine import AgentEngine


class FakeGPT:
    def extract_facts(self, trigger):
        if "Priya" in trigger:
            return {"full_name": "Priya Sharma", "role_title": "Sales Engineer", "location": "Dubai", "start_date": "pending", "manager": "pending", "department": None}
        if "Omar" in trigger:
            return {"full_name": "Omar Reyes", "role_title": "Sales Engineer", "location": "Dubai", "start_date": "pending", "manager": "pending", "department": None}
        return {"full_name": "James Chen", "role_title": "Backend Engineer", "location": "San Francisco", "start_date": "pending", "manager": "pending", "department": "Engineering"}

    def plan_reasons(self, facts, context):
        return {"reasoning": "deterministic test reasoning", "row_reasons": {}}

    def answer_from_rules(self, query, matches):
        return "Sales Engineers are classified as Sales based on Priya Sharma's decision."


class CoreBehaviorTests(unittest.TestCase):
    def test_brain_persists_and_resets_rules(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "company_brain.json"
            store = BrainStore(path)
            self.assertEqual(store.all_rules(), [])
            rule = store.add_rule("Priya Sharma", "Sales Engineer", "Dubai", "Sales")
            self.assertEqual(rule["department_resolved"], "Sales")
            reloaded = BrainStore(path)
            self.assertEqual(len(reloaded.all_rules()), 1)
            reloaded.reset()
            self.assertEqual(json.loads(path.read_text()), {"rules": []})

    def test_priya_escalates_then_omar_auto_resolves_from_persisted_rule(self):
        with tempfile.TemporaryDirectory() as d:
            store = BrainStore(Path(d) / "company_brain.json")
            engine = AgentEngine(store, FakeGPT())
            priya = engine.onboard("Priya Sharma, Sales Engineer, Dubai")
            self.assertTrue(priya["needs_resolution"])
            self.assertEqual(priya["ambiguity"]["role"], "Sales Engineer")
            rule = engine.resolve(priya["employee"]["id"], "Sales")
            self.assertEqual(rule["source_employee"], "Priya Sharma")
            omar = engine.onboard("Omar Reyes, Sales Engineer, Dubai")
            self.assertFalse(omar["needs_resolution"])
            self.assertEqual(omar["matched_rule_id"], rule["id"])
            self.assertEqual(omar["employee"]["department"], "Sales")

    def test_brain_query_is_grounded_and_returns_no_decision_for_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            store = BrainStore(Path(d) / "company_brain.json")
            engine = AgentEngine(store, FakeGPT())
            self.assertEqual(engine.query_brain("How do we classify designers?")["answer"], "No decision recorded for that yet.")
            store.add_rule("Priya Sharma", "Sales Engineer", "Dubai", "Sales")
            answer = engine.query_brain("How do we classify Sales Engineers?")
            self.assertIn("Priya", answer["answer"])
            self.assertEqual(len(answer["sources"]), 1)


if __name__ == "__main__":
    unittest.main()
