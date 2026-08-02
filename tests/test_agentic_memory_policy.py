from __future__ import annotations

import unittest

from tools.agentic_memory.models import AgenticMemoryEntry, MemoryCandidate
from tools.agentic_memory.policy import decide_memory_action


class AgenticMemoryPolicyTests(unittest.TestCase):
    def test_heuristic_prefers_update_for_high_similarity(self) -> None:
        entry = AgenticMemoryEntry(
            content="Python を中心に AI エージェント開発を進める",
            memory_type="preferences",
            target_section="技術的な好み",
        )
        candidates = [
            MemoryCandidate(
                entry_id="pref-1",
                layer="memories",
                source_path="data/llm_wiki/sources/memories/preferences.md",
                section_name="技術的な好み",
                text="Python を主軸にする",
                memory_type="preferences",
                similarity=0.89,
            )
        ]
        decision = decide_memory_action(entry, candidates)
        self.assertEqual("update_existing", decision.action)
        self.assertEqual("pref-1", decision.matched_entry_id)

    def test_judge_output_is_normalized(self) -> None:
        entry = AgenticMemoryEntry(
            content="Issue 管理を優先する",
            memory_type="decisions",
            target_section="技術・設計",
        )
        candidates = [
            MemoryCandidate(
                entry_id="dec-1",
                layer="memories",
                source_path="data/llm_wiki/sources/memories/decisions.md",
                section_name="技術・設計",
                text="Issue 中心で運用する",
                memory_type="decisions",
                similarity=0.7,
            )
        ]

        def judge(_: AgenticMemoryEntry, __: list[MemoryCandidate]) -> dict[str, object]:
            return {
                "action": "strengthen_link",
                "matched_entry_id": "dec-1",
                "reason": "related but not overwrite",
            }

        decision = decide_memory_action(entry, candidates, judge=judge)
        self.assertEqual("strengthen_link", decision.action)
        self.assertEqual(["dec-1"], decision.link_targets)

    def test_amem_style_actions_are_normalized(self) -> None:
        entry = AgenticMemoryEntry(
            content="新しい知見",
            memory_type="preferences",
            target_section="技術的な好み",
        )
        candidates = [
            MemoryCandidate(
                entry_id="pref-2",
                layer="memories",
                source_path="data/llm_wiki/sources/memories/preferences.md",
                section_name="技術的な好み",
                text="既存知見",
                memory_type="preferences",
                similarity=0.7,
            )
        ]

        def judge(_: AgenticMemoryEntry, __: list[MemoryCandidate]) -> dict[str, object]:
            return {
                "actions": ["update_neighbor"],
                "suggested_connections": ["pref-2"],
                "new_context_neighborhood": ["AI workflow"],
                "new_tags_neighborhood": [["ai", "workflow"]],
                "reason": "evolve neighbor",
            }

        decision = decide_memory_action(entry, candidates, judge=judge)
        self.assertEqual("update_neighbor", decision.action)
        self.assertEqual("pref-2", decision.matched_entry_id)
        self.assertEqual(["pref-2"], decision.link_targets)
        self.assertEqual(["AI workflow"], decision.metadata_updates["new_context_neighborhood"])


if __name__ == "__main__":
    unittest.main()
