"""Actor-scoped shadow vote probabilities for Agent Town M15-A.

The live rule engine continues to choose every sheriff and exile ballot.  This
module is imported only by the offline simulator and decomposes an alternative
distribution into legal belief, public influence, social influence, authorized
wolf coordination, and deterministic individual variance.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import main as rules
from .belief import BELIEF_SCHEMA_VERSION, build_belief_snapshot


VOTE_CALIBRATION_SCHEMA_VERSION = "vote_probability_shadow.v1"
VOTE_CALIBRATION_SUMMARY_VERSION = "vote_probability_summary.v1"
VOTE_CALIBRATION_MODE = "shadow"
VoteKind = Literal["sheriff_vote", "exile_vote"]
COMPONENT_NAMES = (
    "belief_utility",
    "public_influence_utility",
    "social_utility",
    "coordination_utility",
    "variance_utility",
)


class StrictVoteCalibrationModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        allow_inf_nan=False,
    )


class VoteCandidateProbabilityV1(StrictVoteCalibrationModel):
    target_id: int = Field(gt=0)
    belief_utility: float = Field(ge=-250.0, le=250.0)
    public_influence_utility: float = Field(ge=-250.0, le=250.0)
    social_utility: float = Field(ge=-250.0, le=250.0)
    coordination_utility: float = Field(ge=-250.0, le=250.0)
    variance_utility: float = Field(ge=-250.0, le=250.0)
    total_utility: float = Field(ge=-500.0, le=500.0)
    probability: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_total(self) -> "VoteCandidateProbabilityV1":
        component_total = sum(
            float(getattr(self, component_name))
            for component_name in COMPONENT_NAMES
        )
        if not math.isclose(
            component_total,
            self.total_utility,
            rel_tol=0.0,
            abs_tol=0.002,
        ):
            raise ValueError("candidate utilities must add up to total_utility")
        return self


class VoteProbabilityObservationV1(StrictVoteCalibrationModel):
    schema_version: Literal["vote_probability_shadow.v1"] = (
        VOTE_CALIBRATION_SCHEMA_VERSION
    )
    mode: Literal["shadow"] = VOTE_CALIBRATION_MODE
    observation_id: str = Field(min_length=1)
    day: int = Field(ge=1)
    phase: str = Field(min_length=1)
    vote_kind: VoteKind
    vote_round: int = Field(ge=0)
    voter_id: int = Field(gt=0)
    belief_schema_version: Literal["belief_state.v2"] = BELIEF_SCHEMA_VERSION
    temperature: float = Field(ge=3.0, le=18.0)
    hard_constraint: Literal["", "sheriff_nomination"] = ""
    candidates: list[VoteCandidateProbabilityV1] = Field(min_length=1)
    entropy_bits: float = Field(ge=0.0)
    normalized_entropy: float = Field(ge=0.0, le=1.0)
    effective_candidate_count: float = Field(ge=1.0)
    top_target_id: int = Field(gt=0)
    top_probability: float = Field(ge=0.0, le=1.0)
    actual_target_id: Optional[int] = Field(default=None, gt=0)
    actual_target_probability: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    actual_target_rank: Optional[int] = Field(default=None, ge=1)
    actual_matches_top: Optional[bool] = None

    @model_validator(mode="after")
    def validate_distribution(self) -> "VoteProbabilityObservationV1":
        candidate_ids = [candidate.target_id for candidate in self.candidates]
        if candidate_ids != sorted(set(candidate_ids)):
            raise ValueError("vote shadow candidates must be unique and sorted")
        if self.voter_id in candidate_ids:
            raise ValueError("vote shadow candidates cannot include the voter")
        probability_sum = sum(
            candidate.probability for candidate in self.candidates
        )
        if not math.isclose(
            probability_sum,
            1.0,
            rel_tol=0.0,
            abs_tol=0.000002,
        ):
            raise ValueError("vote shadow probabilities must sum to one")
        ranked = sorted(
            self.candidates,
            key=lambda candidate: (-candidate.probability, candidate.target_id),
        )
        if (
            self.top_target_id != ranked[0].target_id
            or not math.isclose(
                self.top_probability,
                ranked[0].probability,
                rel_tol=0.0,
                abs_tol=0.000002,
            )
        ):
            raise ValueError("top target must match the probability ranking")
        expected_entropy = _probability_entropy(
            [candidate.probability for candidate in self.candidates]
        )
        for actual, expected in zip(
            (
                self.entropy_bits,
                self.normalized_entropy,
                self.effective_candidate_count,
            ),
            expected_entropy,
        ):
            if not math.isclose(
                actual,
                expected,
                rel_tol=0.0,
                abs_tol=0.000002,
            ):
                raise ValueError("vote shadow entropy fields are inconsistent")
        if self.hard_constraint and sorted(
            candidate.probability for candidate in self.candidates
        ) != [0.0] * (len(self.candidates) - 1) + [1.0]:
            raise ValueError("a hard vote constraint must produce a one-hot distribution")
        actual_fields = (
            self.actual_target_id,
            self.actual_target_probability,
            self.actual_target_rank,
            self.actual_matches_top,
        )
        if any(value is None for value in actual_fields) and any(
            value is not None for value in actual_fields
        ):
            raise ValueError("actual ballot fields must be set together")
        if self.actual_target_id is not None:
            probability_by_target = {
                candidate.target_id: candidate.probability
                for candidate in self.candidates
            }
            if self.actual_target_id not in probability_by_target:
                raise ValueError("actual target must be one shadow candidate")
            expected_probability = probability_by_target[self.actual_target_id]
            expected_rank = next(
                index
                for index, candidate in enumerate(ranked, start=1)
                if candidate.target_id == self.actual_target_id
            )
            if not math.isclose(
                float(self.actual_target_probability),
                expected_probability,
                rel_tol=0.0,
                abs_tol=0.000002,
            ) or self.actual_target_rank != expected_rank:
                raise ValueError("actual ballot probability or rank is inconsistent")
            if self.actual_matches_top != (
                self.actual_target_id == self.top_target_id
            ):
                raise ValueError("actual top-match flag is inconsistent")
        return self


@dataclass(frozen=True)
class PendingVoteCapture:
    vote_kind: VoteKind
    day: int
    vote_round: int
    observations: tuple[dict[str, object], ...]


class VoteCalibrationTraceRecorder:
    """Capture shadow distributions before a vote and attach actual ballots."""

    def __init__(self) -> None:
        self._observations: list[dict[str, object]] = []

    def capture_before_vote(
        self,
        game_state: rules.WolfGameState,
    ) -> Optional[PendingVoteCapture]:
        vote_context = _current_vote_context(game_state)
        if vote_context is None:
            return None
        vote_kind, vote_round, voter_ids, candidate_ids = vote_context
        if not voter_ids or not candidate_ids:
            return None
        belief_snapshot = build_belief_snapshot(
            game_state,
            observer_ids=voter_ids,
        )
        actor_beliefs = {
            int(actor["actor_id"]): actor
            for actor in belief_snapshot["actors"]
        }
        observations = tuple(
            build_vote_probability_observation(
                game_state,
                rules.get_character(game_state, voter_id),
                vote_kind=vote_kind,
                candidate_ids=candidate_ids,
                vote_round=vote_round,
                actor_belief=actor_beliefs[voter_id],
            )
            for voter_id in voter_ids
        )
        return PendingVoteCapture(
            vote_kind=vote_kind,
            day=game_state.day,
            vote_round=vote_round,
            observations=observations,
        )

    def capture_after_vote(
        self,
        game_state: rules.WolfGameState,
        pending: Optional[PendingVoteCapture],
    ) -> None:
        if pending is None:
            return
        actual_targets = _actual_vote_targets(game_state, pending)
        expected_voter_ids = {
            int(observation["voter_id"])
            for observation in pending.observations
        }
        if set(actual_targets) != expected_voter_ids:
            raise ValueError("vote shadow capture does not match actual NPC ballots")
        for observation in pending.observations:
            voter_id = int(observation["voter_id"])
            self._observations.append(
                attach_actual_vote_target(
                    observation,
                    actual_targets[voter_id],
                )
            )

    def build_result(self) -> dict[str, object]:
        observation_ids = [
            str(observation["observation_id"])
            for observation in self._observations
        ]
        if len(observation_ids) != len(set(observation_ids)):
            raise ValueError("vote shadow observation ids must be unique")
        return {
            "schema_version": VOTE_CALIBRATION_SCHEMA_VERSION,
            "belief_schema_version": BELIEF_SCHEMA_VERSION,
            "mode": VOTE_CALIBRATION_MODE,
            "observation_count": len(self._observations),
            "candidate_evaluation_count": sum(
                len(observation["candidates"])
                for observation in self._observations
            ),
            "observations": list(self._observations),
        }


def build_vote_probability_observation(
    game_state: rules.WolfGameState,
    voter: rules.CharacterState,
    *,
    vote_kind: VoteKind,
    candidate_ids: list[int],
    vote_round: int = 0,
    actor_belief: Optional[dict[str, object]] = None,
) -> dict[str, object]:
    """Build one legal-perspective shadow distribution without mutating state."""

    if voter.is_player or not voter.alive:
        raise ValueError("vote shadow observations require a living NPC voter")
    candidates = _legal_candidates(game_state, voter, candidate_ids)
    if not candidates:
        raise ValueError("vote shadow observation requires a legal candidate")
    if actor_belief is None:
        belief_snapshot = build_belief_snapshot(
            game_state,
            observer_ids=[voter.id],
        )
        actor_belief = belief_snapshot["actors"][0]
    if int(actor_belief.get("actor_id", 0)) != voter.id:
        raise ValueError("vote shadow belief must belong to the voter")
    belief_by_target = {
        int(seat["target_id"]): seat
        for seat in actor_belief.get("seats", [])
    }
    if any(candidate.id not in belief_by_target for candidate in candidates):
        raise ValueError("vote shadow belief must cover every candidate")

    base_components = {
        candidate.id: _build_base_components(
            game_state,
            voter,
            candidate,
            vote_kind,
            belief_by_target[candidate.id],
        )
        for candidate in candidates
    }
    coordination = _build_coordination_utilities(
        game_state,
        voter,
        candidates,
        vote_kind,
        base_components,
    )
    scores: dict[int, float] = {}
    candidate_components: dict[int, dict[str, float]] = {}
    for candidate in candidates:
        components = {
            **base_components[candidate.id],
            "coordination_utility": coordination.get(candidate.id, 0.0),
        }
        rounded_components = {
            name: _round_utility(components[name])
            for name in COMPONENT_NAMES
        }
        total_utility = _round_utility(sum(rounded_components.values()))
        candidate_components[candidate.id] = {
            **rounded_components,
            "total_utility": total_utility,
        }
        scores[candidate.id] = total_utility

    tuning = rules.get_character_strategy_tuning(voter)
    temperature = _vote_temperature(tuning)
    probabilities = rules.build_softmax_vote_probabilities(scores, tuning)
    hard_constraint = ""
    if (
        vote_kind == "exile_vote"
        and game_state.sheriff_id == voter.id
        and game_state.meeting is not None
        and game_state.meeting.nomination_target_id in scores
    ):
        nomination_target_id = int(game_state.meeting.nomination_target_id)
        probabilities = {
            candidate_id: 1.0 if candidate_id == nomination_target_id else 0.0
            for candidate_id in sorted(scores)
        }
        hard_constraint = "sheriff_nomination"

    candidates_payload = [
        VoteCandidateProbabilityV1(
            target_id=candidate_id,
            **candidate_components[candidate_id],
            probability=_round_probability(probabilities[candidate_id]),
        ).model_dump(mode="json")
        for candidate_id in sorted(scores)
    ]
    _normalize_rounded_probabilities(candidates_payload)
    entropy_bits, normalized_entropy, effective_candidate_count = (
        _probability_entropy(
            [float(candidate["probability"]) for candidate in candidates_payload]
        )
    )
    ranked = sorted(
        candidates_payload,
        key=lambda candidate: (
            -float(candidate["probability"]),
            int(candidate["target_id"]),
        ),
    )
    observation = VoteProbabilityObservationV1(
        observation_id=(
            f"vote_shadow:{vote_kind}:{game_state.day}:"
            f"{vote_round}:{voter.id}"
        ),
        day=game_state.day,
        phase=game_state.phase,
        vote_kind=vote_kind,
        vote_round=vote_round,
        voter_id=voter.id,
        temperature=temperature,
        hard_constraint=hard_constraint,
        candidates=candidates_payload,
        entropy_bits=entropy_bits,
        normalized_entropy=normalized_entropy,
        effective_candidate_count=effective_candidate_count,
        top_target_id=int(ranked[0]["target_id"]),
        top_probability=float(ranked[0]["probability"]),
    )
    return observation.model_dump(mode="json")


def attach_actual_vote_target(
    observation: dict[str, object],
    actual_target_id: int,
) -> dict[str, object]:
    candidates = list(observation.get("candidates", []))
    ranked = sorted(
        candidates,
        key=lambda candidate: (
            -float(candidate["probability"]),
            int(candidate["target_id"]),
        ),
    )
    actual_rank = next(
        (
            index
            for index, candidate in enumerate(ranked, start=1)
            if int(candidate["target_id"]) == actual_target_id
        ),
        None,
    )
    if actual_rank is None:
        raise ValueError("actual ballot target is outside the shadow candidates")
    actual_probability = float(ranked[actual_rank - 1]["probability"])
    completed = {
        **observation,
        "actual_target_id": actual_target_id,
        "actual_target_probability": actual_probability,
        "actual_target_rank": actual_rank,
        "actual_matches_top": actual_target_id
        == int(observation["top_target_id"]),
    }
    return VoteProbabilityObservationV1.model_validate(completed).model_dump(
        mode="json"
    )


def aggregate_vote_calibration_traces(
    game_results: list[dict[str, object]],
) -> dict[str, object]:
    """Aggregate shadow distributions and post-game-only camp alignment."""

    if not game_results:
        raise ValueError("vote calibration summary requires completed games")
    observations: list[tuple[dict[str, object], dict[int, str]]] = []
    for game in game_results:
        trace = game.get("vote_calibration_trace")
        if not isinstance(trace, dict):
            raise ValueError("vote calibration trace is missing")
        if trace.get("schema_version") != VOTE_CALIBRATION_SCHEMA_VERSION:
            raise ValueError("vote calibration trace version mismatch")
        camp_by_id = {
            int(role["character_id"]): str(role["camp"])
            for role in game.get("roles", [])
        }
        for observation in trace.get("observations", []):
            observations.append((observation, camp_by_id))

    by_kind = {
        vote_kind: _summarize_observation_group(
            [
                observation
                for observation, _camps in observations
                if observation["vote_kind"] == vote_kind
            ]
        )
        for vote_kind in ("sheriff_vote", "exile_vote")
    }
    by_voter_camp: dict[str, dict[str, object]] = {}
    for camp in ("good", "werewolf"):
        camp_observations = [
            observation
            for observation, camps in observations
            if camps.get(int(observation["voter_id"])) == camp
        ]
        by_voter_camp[camp] = _summarize_observation_group(
            camp_observations
        )
    by_kind_and_voter_camp = {
        vote_kind: {
            camp: _summarize_observation_group(
                [
                    observation
                    for observation, camps in observations
                    if observation["vote_kind"] == vote_kind
                    and camps.get(int(observation["voter_id"])) == camp
                ]
            )
            for camp in ("good", "werewolf")
        }
        for vote_kind in ("sheriff_vote", "exile_vote")
    }

    good_exile_observations = [
        (observation, camps)
        for observation, camps in observations
        if observation["vote_kind"] == "exile_vote"
        and camps.get(int(observation["voter_id"])) == "good"
    ]
    good_mass_on_wolves = sum(
        float(candidate["probability"])
        for observation, camps in good_exile_observations
        for candidate in observation["candidates"]
        if camps.get(int(candidate["target_id"])) == "werewolf"
    )
    good_mass_on_good = sum(
        float(candidate["probability"])
        for observation, camps in good_exile_observations
        for candidate in observation["candidates"]
        if camps.get(int(candidate["target_id"])) == "good"
    )
    good_observation_count = len(good_exile_observations)
    probability_mass_total = good_mass_on_wolves + good_mass_on_good
    if not math.isclose(
        probability_mass_total,
        float(good_observation_count),
        rel_tol=0.0,
        abs_tol=0.00002,
    ):
        raise ValueError("good exile probability mass must conserve observations")

    return {
        "schema_version": VOTE_CALIBRATION_SUMMARY_VERSION,
        "trace_schema_version": VOTE_CALIBRATION_SCHEMA_VERSION,
        "belief_schema_version": BELIEF_SCHEMA_VERSION,
        "mode": VOTE_CALIBRATION_MODE,
        "game_count": len(game_results),
        "observation_count": len(observations),
        "candidate_evaluation_count": sum(
            len(observation["candidates"])
            for observation, _camps in observations
        ),
        "by_kind": by_kind,
        "by_voter_camp": by_voter_camp,
        "by_kind_and_voter_camp": by_kind_and_voter_camp,
        "good_exile_probability_alignment": {
            "observation_count": good_observation_count,
            "probability_mass_on_wolves": _round_metric(
                good_mass_on_wolves
            ),
            "probability_mass_on_good": _round_metric(good_mass_on_good),
            "mean_probability_mass_on_wolves": _mean_or_none(
                [
                    sum(
                        float(candidate["probability"])
                        for candidate in observation["candidates"]
                        if camps.get(int(candidate["target_id"]))
                        == "werewolf"
                    )
                    for observation, camps in good_exile_observations
                ]
            ),
            "mean_probability_mass_on_good": _mean_or_none(
                [
                    sum(
                        float(candidate["probability"])
                        for candidate in observation["candidates"]
                        if camps.get(int(candidate["target_id"])) == "good"
                    )
                    for observation, camps in good_exile_observations
                ]
            ),
        },
    }


def _current_vote_context(
    game_state: rules.WolfGameState,
) -> Optional[tuple[VoteKind, int, list[int], list[int]]]:
    if game_state.phase in {"SHERIFF_VOTE", "SHERIFF_RUNOFF_VOTE"}:
        election = game_state.sheriff_election
        if election is None:
            raise ValueError("sheriff shadow capture requires an election")
        participant_ids = set(election.candidates)
        voter_ids = sorted(
            character.id
            for character in game_state.characters
            if character.alive
            and not character.is_player
            and character.id not in participant_ids
        )
        return (
            "sheriff_vote",
            election.runoff_round,
            voter_ids,
            rules.get_active_sheriff_candidates(game_state),
        )
    if game_state.phase == "VOTE":
        voter_ids = sorted(
            character.id
            for character in game_state.characters
            if character.alive and not character.is_player
        )
        candidate_ids = sorted(
            character.id
            for character in game_state.characters
            if character.alive
        )
        return "exile_vote", 0, voter_ids, candidate_ids
    return None


def _actual_vote_targets(
    game_state: rules.WolfGameState,
    pending: PendingVoteCapture,
) -> dict[int, int]:
    if pending.vote_kind == "sheriff_vote":
        context = f"round:{pending.vote_round}"
        return {
            int(event.actor_id): int(event.target_id)
            for event in game_state.sheriff_events
            if event.event_type == "sheriff_vote"
            and event.day == pending.day
            and event.context == context
            and event.actor_id is not None
            and event.target_id is not None
            and not rules.get_character(game_state, int(event.actor_id)).is_player
        }
    return {
        vote.voter_id: vote.target_id
        for vote in game_state.votes
        if vote.day == pending.day
        and not rules.get_character(game_state, vote.voter_id).is_player
    }


def _legal_candidates(
    game_state: rules.WolfGameState,
    voter: rules.CharacterState,
    candidate_ids: list[int],
) -> list[rules.CharacterState]:
    requested_ids = sorted(set(int(candidate_id) for candidate_id in candidate_ids))
    candidates = [
        rules.get_character(game_state, candidate_id)
        for candidate_id in requested_ids
        if candidate_id != voter.id
        and rules.get_character(game_state, candidate_id).alive
    ]
    return sorted(candidates, key=lambda candidate: candidate.id)


def _build_base_components(
    game_state: rules.WolfGameState,
    voter: rules.CharacterState,
    candidate: rules.CharacterState,
    vote_kind: VoteKind,
    seat_belief: dict[str, object],
) -> dict[str, float]:
    tuning = rules.get_character_strategy_tuning(voter)
    suspicion = float(seat_belief["suspicion_score"])
    confidence = float(seat_belief["confidence"])
    belief_strength = (
        0.38 + tuning.reasoning_skill * 0.22
    ) * (0.58 + confidence * 0.42)
    belief_utility = suspicion * belief_strength
    if vote_kind == "sheriff_vote":
        belief_utility *= -0.72

    position = rules.get_latest_public_position(
        game_state,
        voter.id,
        current_day_only=True,
    )
    public_utility = 0.0
    if vote_kind == "sheriff_vote":
        public_utility += (
            rules.get_public_persuasion_strength(game_state, candidate) * 24.0
        )
        if position is not None:
            if candidate.id in position.trusted_target_ids:
                public_utility += 8.0 * tuning.plan_consistency
            if candidate.id in position.suspected_target_ids:
                public_utility -= 8.0 * tuning.plan_consistency
    else:
        nomination_target_id = (
            game_state.meeting.nomination_target_id
            if game_state.meeting is not None
            else None
        )
        if candidate.id == nomination_target_id:
            public_utility += 6.0 + 12.0 * tuning.social_susceptibility
        if position is not None:
            confidence_factor = 0.45 + 0.55 * (
                position.confidence / 100.0
            )
            if candidate.id == position.provisional_vote_target_id:
                public_utility += (
                    22.0
                    * tuning.plan_consistency
                    * confidence_factor
                )
            if candidate.id in position.suspected_target_ids:
                public_utility += 5.0 * tuning.plan_consistency
            if candidate.id in position.trusted_target_ids:
                public_utility -= 7.0 * tuning.plan_consistency

    target_trust = float(
        voter.relationships.get(str(candidate.id), {}).get("trust", 0.5)
    )
    social_utility = (
        (target_trust - 0.5) * 28.0
        if vote_kind == "sheriff_vote"
        else (0.5 - target_trust) * 18.0
    )
    if (
        vote_kind == "exile_vote"
        and game_state.sheriff_id is not None
        and game_state.meeting is not None
        and candidate.id == game_state.meeting.nomination_target_id
    ):
        sheriff_trust = float(
            voter.relationships.get(
                str(game_state.sheriff_id),
                {},
            ).get("trust", 0.5)
        )
        social_utility += (
            (sheriff_trust - 0.5)
            * 18.0
            * tuning.social_susceptibility
        )

    variance_span = (
        2.0
        + tuning.decision_variance * 10.0
        + tuning.social_susceptibility * 2.0
    )
    centered_roll = (
        rules.deterministic_strategy_roll(
            game_state,
            voter,
            f"m15a_shadow:{vote_kind}:{candidate.id}",
        )
        - 0.5
    ) * 2.0
    return {
        "belief_utility": belief_utility,
        "public_influence_utility": public_utility,
        "social_utility": social_utility,
        "variance_utility": centered_roll * variance_span,
    }


def _build_coordination_utilities(
    game_state: rules.WolfGameState,
    voter: rules.CharacterState,
    candidates: list[rules.CharacterState],
    vote_kind: VoteKind,
    base_components: dict[int, dict[str, float]],
) -> dict[int, float]:
    if voter.role != "werewolf":
        return {candidate.id: 0.0 for candidate in candidates}
    base_scores = {
        candidate.id: sum(base_components[candidate.id].values())
        for candidate in candidates
    }
    if vote_kind == "sheriff_vote":
        strategy = rules.choose_wolf_team_vote_strategy(
            game_state,
            "sheriff",
            [candidate.id for candidate in candidates],
        )
        utilities = {
            candidate.id: rules.get_wolf_sheriff_strategy_adjustment(
                game_state,
                voter,
                candidate,
                candidates,
                strategy,
            )
            for candidate in candidates
        }
        forbidden_story_ids = set(
            rules.get_wolf_teammate_black_check_sources(
                game_state,
                voter.id,
            )
        ) | set(
            rules.get_wolf_teammate_black_check_targets(
                game_state,
                voter.id,
            )
        )
        for target_id in forbidden_story_ids:
            if target_id in utilities:
                utilities[target_id] -= 80.0
        return utilities

    strategy = rules.choose_wolf_team_vote_strategy(game_state, "exile")
    utilities = {
        candidate.id: rules.get_wolf_exile_strategy_adjustment(
            game_state,
            voter,
            candidate,
            candidates,
            strategy,
        )
        for candidate in candidates
    }
    story_source_ids = set(
        rules.get_wolf_teammate_black_check_sources(game_state, voter.id)
    )
    story_target_ids = set(
        rules.get_wolf_teammate_black_check_targets(game_state, voter.id)
    )
    story_ids = story_source_ids | story_target_ids
    if story_ids:
        preferred_story_id = max(
            (target_id for target_id in story_ids if target_id in base_scores),
            key=lambda target_id: (base_scores[target_id], -target_id),
            default=None,
        )
        if preferred_story_id is not None:
            utilities[preferred_story_id] += 80.0
    return utilities


def _summarize_observation_group(
    observations: list[dict[str, object]],
) -> dict[str, object]:
    component_values: dict[str, list[float]] = defaultdict(list)
    for observation in observations:
        for candidate in observation["candidates"]:
            for component_name in COMPONENT_NAMES:
                component_values[component_name].append(
                    abs(float(candidate[component_name]))
                )
    top_match_count = sum(
        1 for observation in observations if observation["actual_matches_top"]
    )
    return {
        "observation_count": len(observations),
        "candidate_evaluation_count": sum(
            len(observation["candidates"])
            for observation in observations
        ),
        "hard_constraint_count": sum(
            1 for observation in observations if observation["hard_constraint"]
        ),
        "mean_normalized_entropy": _mean_or_none(
            [float(observation["normalized_entropy"]) for observation in observations]
        ),
        "mean_top_probability": _mean_or_none(
            [float(observation["top_probability"]) for observation in observations]
        ),
        "actual_top_match_count": top_match_count,
        "actual_top_match_rate": (
            _round_metric(top_match_count / len(observations))
            if observations
            else None
        ),
        "mean_actual_target_probability": _mean_or_none(
            [
                float(observation["actual_target_probability"])
                for observation in observations
            ]
        ),
        "mean_actual_target_rank": _mean_or_none(
            [float(observation["actual_target_rank"]) for observation in observations]
        ),
        "mean_absolute_component_utility": {
            component_name: _mean_or_none(component_values[component_name])
            for component_name in COMPONENT_NAMES
        },
    }


def _vote_temperature(tuning: object) -> float:
    return round(
        max(
            3.0,
            min(
                18.0,
                4.0
                + float(tuning.decision_variance) * 12.0
                + float(tuning.deception_susceptibility) * 4.0
                + float(tuning.social_susceptibility) * 2.0
                - float(tuning.reasoning_skill) * 3.0,
            ),
        ),
        6,
    )


def _probability_entropy(
    probabilities: list[float],
) -> tuple[float, float, float]:
    entropy_bits = -sum(
        probability * math.log2(probability)
        for probability in probabilities
        if probability > 0.0
    )
    normalized_entropy = (
        entropy_bits / math.log2(len(probabilities))
        if len(probabilities) > 1
        else 0.0
    )
    return (
        _round_metric(entropy_bits),
        _round_metric(normalized_entropy),
        _round_metric(2**entropy_bits),
    )


def _normalize_rounded_probabilities(
    candidates: list[dict[str, object]],
) -> None:
    if not candidates:
        return
    difference = round(
        1.0 - sum(float(candidate["probability"]) for candidate in candidates),
        9,
    )
    if difference:
        highest = min(
            candidates,
            key=lambda candidate: (
                -float(candidate["probability"]),
                int(candidate["target_id"]),
            ),
        )
        highest["probability"] = _round_probability(
            float(highest["probability"]) + difference
        )


def _round_utility(value: float) -> float:
    return round(float(value), 4)


def _round_probability(value: float) -> float:
    return round(float(value), 9)


def _round_metric(value: float) -> float:
    return round(float(value), 6)


def _mean_or_none(values: list[float]) -> Optional[float]:
    return _round_metric(sum(values) / len(values)) if values else None


__all__ = [
    "COMPONENT_NAMES",
    "VOTE_CALIBRATION_MODE",
    "VOTE_CALIBRATION_SCHEMA_VERSION",
    "VOTE_CALIBRATION_SUMMARY_VERSION",
    "VoteCalibrationTraceRecorder",
    "VoteCandidateProbabilityV1",
    "VoteProbabilityObservationV1",
    "aggregate_vote_calibration_traces",
    "attach_actual_vote_target",
    "build_vote_probability_observation",
]
