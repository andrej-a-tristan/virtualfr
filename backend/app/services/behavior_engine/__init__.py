"""Behavior Engine — unified orchestration for natural, non-robotic chat.

Layers:
  intent_classifier      – Detects turn intent (ask_about_her, support, banter, etc.)
  dialogue_policy        – Applies response rules based on intent
  response_contract      – Per-turn output constraints
  validators             – Anti-interview and consistency checks
  behavior_orchestrator  – Unified pipeline wiring everything together
"""
