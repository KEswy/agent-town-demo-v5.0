#!/usr/bin/env python3
"""Offline evaluator for actor-scoped NPC reasoning scenarios."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

os.environ["AGENT_TOWN_DISABLE_VECTOR_RAG"] = "1"
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from backend.app.npc_reasoning import (  # noqa: E402
    NPCBeliefStateV1,
    NPCReasoningObservationV1,
    build_npc_belief_state,
)


SCENARIO_SCHEMA_VERSION = "npc_reasoning_scenario.v1"
KNOWN_SIGNAL_KINDS = {
    "seer_claim_withdrawn_against_persistent_counterclaim",
    "seer_golded_persistent_counterclaim",
    "seer_check_result_changed",
    "known_role_conflicts_with_seer_claim",
    "sole_consistent_seer_claimant",
}


class StrictScenarioModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        str_strip_whitespace=True,
    )


class ReasoningScenarioExpectationV1(StrictScenarioModel):
    required_signal_kinds: list[str] = Field(default_factory=list)
    forbidden_signal_kinds: list[str] = Field(default_factory=list)
    supported_seer_id: Optional[int] = Field(default=None, gt=0)
    hidden_world_consistent: Optional[bool] = None
    min_seer_probability: dict[str, float] = Field(default_factory=dict)
    max_seer_probability: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_expectation(self) -> "ReasoningScenarioExpectationV1":
        all_kinds = (
            self.required_signal_kinds + self.forbidden_signal_kinds
        )
        unknown = set(all_kinds) - KNOWN_SIGNAL_KINDS
        if unknown:
            raise ValueError(f"unknown reasoning signal kind(s): {sorted(unknown)}")
        for value in [
            *self.min_seer_probability.values(),
            *self.max_seer_probability.values(),
        ]:
            if not 0.0 <= value <= 1.0:
                raise ValueError("expected probabilities must be in [0,1]")
        return self


class ReasoningScenarioV1(StrictScenarioModel):
    schema_version: str = SCENARIO_SCHEMA_VERSION
    scenario_id: str = Field(min_length=1)
    observation: NPCReasoningObservationV1
    expect: ReasoningScenarioExpectationV1

    @model_validator(mode="after")
    def validate_schema(self) -> "ReasoningScenarioV1":
        if self.schema_version != SCENARIO_SCHEMA_VERSION:
            raise ValueError("unsupported reasoning scenario schema")
        return self


def load_scenarios(path: Path) -> list[ReasoningScenarioV1]:
    scenarios: list[ReasoningScenarioV1] = []
    seen_ids: set[str] = set()
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
            scenario = ReasoningScenarioV1.model_validate(raw)
            if scenario.scenario_id in seen_ids:
                raise ValueError("duplicate scenario_id")
            seen_ids.add(scenario.scenario_id)
            scenarios.append(scenario)
        except Exception as exc:
            raise ValueError(f"{path}:{line_number}: {exc}") from exc
    if not scenarios:
        raise ValueError(f"{path}: no scenarios")
    return scenarios


def evaluate_scenario(
    scenario: ReasoningScenarioV1,
) -> tuple[bool, NPCBeliefStateV1, list[str]]:
    belief = build_npc_belief_state(scenario.observation)
    expectation = scenario.expect
    observed_kinds = {signal.kind for signal in belief.reasoning_signals}
    failures: list[str] = []
    for kind in expectation.required_signal_kinds:
        if kind not in observed_kinds:
            failures.append(f"missing signal: {kind}")
    for kind in expectation.forbidden_signal_kinds:
        if kind in observed_kinds:
            failures.append(f"forbidden signal: {kind}")
    if (
        expectation.supported_seer_id is not None
        and belief.plan.supported_seer_id != expectation.supported_seer_id
    ):
        failures.append(
            "supported_seer_id "
            f"expected {expectation.supported_seer_id}, got {belief.plan.supported_seer_id}"
        )
    if expectation.hidden_world_consistent is not None:
        hidden_hypothesis = next(
            (
                hypothesis
                for hypothesis in belief.seer_hypotheses
                if hypothesis.claimant_id is None
            ),
            None,
        )
        if expectation.hidden_world_consistent:
            if hidden_hypothesis is None or not hidden_hypothesis.consistent:
                failures.append("hidden-world consistency expectation was not met")
        elif hidden_hypothesis is not None and hidden_hypothesis.consistent:
            failures.append("hidden-world consistency expectation was not met")
    probabilities = {
        str(hypothesis.claimant_id): hypothesis.probability
        for hypothesis in belief.seer_hypotheses
    }
    for claimant_id, minimum in expectation.min_seer_probability.items():
        if probabilities.get(claimant_id, 0.0) < minimum:
            failures.append(
                f"seer probability {claimant_id} below {minimum}"
            )
    for claimant_id, maximum in expectation.max_seer_probability.items():
        if probabilities.get(claimant_id, 0.0) > maximum:
            failures.append(
                f"seer probability {claimant_id} above {maximum}"
            )
    return not failures, belief, failures


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate versioned NPC reasoning JSONL scenarios."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    results = []
    passed = True
    for scenario in load_scenarios(args.input):
        ok, belief, failures = evaluate_scenario(scenario)
        passed = passed and ok
        results.append(
            {
                "scenario_id": scenario.scenario_id,
                "passed": ok,
                "failures": failures,
                "belief_digest": belief.belief_digest,
                "signals": sorted(
                    {signal.kind for signal in belief.reasoning_signals}
                ),
                "supported_seer_id": belief.plan.supported_seer_id,
                "world_count": belief.world_count,
                "world_entropy": belief.world_entropy,
            }
        )
    report = {
        "schema_version": "npc_reasoning_scenario_report.v1",
        "passed": passed,
        "scenarios": results,
    }
    rendered = json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
