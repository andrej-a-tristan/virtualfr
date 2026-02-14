"""
Bond Engine — unified orchestration layer for relationship intelligence.

Replaces fragmented heuristics (memory, progression, identity, initiation,
disclosure) with one coherent "bond brain" called once per turn.

Architecture:
  bond_orchestrator  → single entry point per turn
  memory_fabric      → layered memory (semantic, emotional, episodic, pattern)
  memory_ingest      → extraction pipeline per user message
  memory_retrieval   → scored retrieval with diversity constraints
  memory_scoring     → relevance / recency / emotional weighting
  memory_conflict_resolution → contradiction detection & resolution
  memory_patterns    → time habits, topic cycles, style preferences
  consistency_guard  → persona kernel + growth state validation
  depth_planner      → progression → capability unlocks
  initiation_planner → event-conditioned proactive messages
  disclosure_planner → earned vulnerability via disclosure graph
  response_director  → anti-repetition, novelty budgets, cadence
"""
