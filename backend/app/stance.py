"""Versioned shadow stance summaries and continuity observations for V3.1-E.

This module consumes only legal-perspective belief snapshots and structured
public positions. It observes decisions after they happen and never feeds a
target back into live speech, sheriff voting, exile voting, or rule state.
"""

from __future__ import annotations

from collections import Counter
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import main as rules
from .belief import BELIEF_SCHEMA_VERSION, build_belief_snapshot


STANCE_SCHEMA_VERSION = "stance_summary.v1"
STANCE_MODE = "shadow"
STANCE_SUSPECT_SCORE_MIN = 1
STANCE_TRUST_SCORE_MAX = -1


class StrictStanceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ActorStanceSummaryV1(StrictStanceModel):
    actor_id: int = Field(gt=0)
    actor_name: str = Field(min_length=1)
    alive: bool
    day: int = Field(ge=1)
    phase: str = Field(min_length=1)
    trusted_target_ids: list[int] = Field(default_factory=list, max_length=2)
    primary_suspect_id: Optional[int] = Field(default=None, gt=0)
    secondary_suspect_id: Optional[int] = Field(default=None, gt=0)
    provisional_vote_target_id: Optional[int] = Field(default=None, gt=0)
    verification_target_id: Optional[int] = Field(default=None, gt=0)
    verification_condition: Optional[str] = Field(default=None, min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    basis_evidence_ids: list[str] = Field(default_factory=list)

    @field_validator("trusted_target_ids")
    @classmethod
    def validate_trusted_targets(cls, value: list[int]) -> list[int]:
        if any(target_id <= 0 for target_id in value):
            raise ValueError("trusted stance targets must be positive")
        if len(value) != len(set(value)):
            raise ValueError("trusted stance targets must not repeat")
        return value

    @field_validator("basis_evidence_ids")
    @classmethod
    def validate_basis_evidence_ids(cls, value: list[str]) -> list[str]:
        if any(not evidence_id for evidence_id in value):
            raise ValueError("stance basis evidence ids must not be empty")
        if value != sorted(set(value)):
            raise ValueError("stance basis evidence ids must be sorted and unique")
        return value


class StanceChangeV1(StrictStanceModel):
    capture_index: int = Field(ge=1)
    day: int = Field(ge=1)
    phase: str = Field(min_length=1)
    actor_id: int = Field(gt=0)
    changed_fields: list[str] = Field(min_length=1)
    previous_primary_suspect_id: Optional[int] = Field(default=None, gt=0)
    primary_suspect_id: Optional[int] = Field(default=None, gt=0)
    previous_secondary_suspect_id: Optional[int] = Field(default=None, gt=0)
    secondary_suspect_id: Optional[int] = Field(default=None, gt=0)
    previous_trusted_target_ids: list[int] = Field(default_factory=list)
    trusted_target_ids: list[int] = Field(default_factory=list)
    previous_provisional_vote_target_id: Optional[int] = Field(
        default=None,
        gt=0,
    )
    provisional_vote_target_id: Optional[int] = Field(default=None, gt=0)
    previous_verification_target_id: Optional[int] = Field(default=None, gt=0)
    verification_target_id: Optional[int] = Field(default=None, gt=0)
    previous_verification_condition: Optional[str] = None
    verification_condition: Optional[str] = None
    previous_confidence: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    added_evidence_ids: list[str] = Field(default_factory=list)
    removed_evidence_ids: list[str] = Field(default_factory=list)


class StanceObservationV1(StrictStanceModel):
    observation_id: str = Field(min_length=1)
    capture_index: int = Field(ge=1)
    day: int = Field(ge=1)
    phase: str = Field(min_length=1)
    kind: Literal["public_speech", "sheriff_vote", "exile_vote"]
    commitment: Literal[
        "provisional_vote",
        "suspect",
        "trust",
        "support",
        "vote",
        "none",
    ]
    actor_id: int = Field(gt=0)
    actual_target_id: Optional[int] = Field(default=None, gt=0)
    expected_target_ids: list[int] = Field(default_factory=list)
    alignment: Literal[
        "aligned",
        "explained_change",
        "unexplained_change",
        "unscored",
    ]
    new_evidence_ids: list[str] = Field(default_factory=list)
    previous_observation_id: Optional[str] = None


def build_stance_snapshot(
    game_state: rules.WolfGameState,
    *,
    belief_snapshot: Optional[dict[str, object]] = None,
) -> dict[str, object]:
    """Build actor-local stance cards without mutating rule or belief state."""

    if belief_snapshot is None:
        belief_snapshot = build_belief_snapshot(game_state)
    if belief_snapshot.get("schema_version") != BELIEF_SCHEMA_VERSION:
        raise ValueError("stance summary requires the active belief schema")
    if (
        int(belief_snapshot.get("day", 0)) != game_state.day
        or str(belief_snapshot.get("phase", "")) != game_state.phase
    ):
        raise ValueError("stance summary requires a current belief snapshot")

    characters = {
        character.id: character
        for character in game_state.characters
    }
    summaries = [
        _build_actor_stance_summary(game_state, characters, actor_state)
        for actor_state in belief_snapshot["actors"]
    ]
    return {
        "schema_version": STANCE_SCHEMA_VERSION,
        "belief_schema_version": BELIEF_SCHEMA_VERSION,
        "mode": STANCE_MODE,
        "day": game_state.day,
        "phase": game_state.phase,
        "actors": [
            summary.model_dump(mode="json")
            for summary in sorted(summaries, key=lambda item: item.actor_id)
        ],
    }


class StanceTraceRecorder:
    """Record stance changes and compare decisions with their prior card."""

    def __init__(self) -> None:
        self.capture_count = 0
        self._last_summaries: dict[int, dict[str, object]] = {}
        self._final_summaries: dict[int, dict[str, object]] = {}
        self._changes: list[dict[str, object]] = []
        self._observations: list[dict[str, object]] = []
        self._speech_count = 0
        self._sheriff_event_count = 0
        self._seen_votes: set[tuple[int, int, int]] = set()
        self._last_decision_basis: dict[int, set[str]] = {}
        self._last_observation_id: dict[int, str] = {}

    def capture(
        self,
        game_state: rules.WolfGameState,
        belief_snapshot: dict[str, object],
    ) -> None:
        stance_snapshot = build_stance_snapshot(
            game_state,
            belief_snapshot=belief_snapshot,
        )
        self.capture_count += 1
        current_summaries = {
            int(summary["actor_id"]): summary
            for summary in stance_snapshot["actors"]
        }

        self._capture_new_observations(game_state, current_summaries)

        for actor_id in sorted(current_summaries):
            current = current_summaries[actor_id]
            previous = self._last_summaries.get(actor_id)
            change = self._build_change(current, previous)
            if change is not None:
                self._changes.append(change)
            self._last_summaries[actor_id] = current
            self._final_summaries[actor_id] = current

        for character in game_state.characters:
            if character.is_player or character.alive:
                continue
            frozen = self._final_summaries.get(character.id)
            if frozen is not None and bool(frozen["alive"]):
                frozen = dict(frozen)
                frozen["alive"] = False
                self._final_summaries[character.id] = frozen

    def _capture_new_observations(
        self,
        game_state: rules.WolfGameState,
        current_summaries: dict[int, dict[str, object]],
    ) -> None:
        new_speeches = game_state.speeches[self._speech_count :]
        for offset, speech in enumerate(new_speeches, start=self._speech_count + 1):
            if speech.is_player or speech.public_position is None:
                continue
            position = speech.public_position
            commitment: str = "none"
            target_id: Optional[int] = None
            expected_field = "none"
            if position.provisional_vote_target_id is not None:
                commitment = "provisional_vote"
                target_id = position.provisional_vote_target_id
                expected_field = "vote"
            elif position.suspected_target_ids:
                commitment = "suspect"
                target_id = position.suspected_target_ids[0]
                expected_field = "suspect"
            elif position.trusted_target_ids:
                commitment = "trust"
                target_id = position.trusted_target_ids[0]
                expected_field = "trust"
            self._append_observation(
                observation_id=f"stance:speech:{offset}",
                day=speech.day,
                phase=speech.phase,
                kind="public_speech",
                commitment=commitment,
                actor_id=speech.character_id,
                actual_target_id=target_id,
                expected_field=expected_field,
                post_decision_summary=current_summaries.get(speech.character_id),
            )
        self._speech_count = len(game_state.speeches)

        new_sheriff_events = game_state.sheriff_events[
            self._sheriff_event_count :
        ]
        for offset, event in enumerate(
            new_sheriff_events,
            start=self._sheriff_event_count + 1,
        ):
            if (
                event.event_type != "sheriff_vote"
                or event.actor_id is None
                or event.target_id is None
            ):
                continue
            actor = rules.get_character(game_state, event.actor_id)
            if actor.is_player:
                continue
            self._append_observation(
                observation_id=f"stance:sheriff_vote:{offset}",
                day=event.day,
                phase="SHERIFF_VOTE",
                kind="sheriff_vote",
                commitment="support",
                actor_id=event.actor_id,
                actual_target_id=event.target_id,
                expected_field="trust",
                post_decision_summary=current_summaries.get(event.actor_id),
                allowed_target_ids=_sheriff_event_candidate_ids(
                    game_state,
                    event,
                ),
            )
        self._sheriff_event_count = len(game_state.sheriff_events)

        for vote in game_state.votes:
            vote_key = (vote.day, vote.voter_id, vote.target_id)
            if vote_key in self._seen_votes:
                continue
            self._seen_votes.add(vote_key)
            actor = rules.get_character(game_state, vote.voter_id)
            if actor.is_player:
                continue
            self._append_observation(
                observation_id=(
                    f"stance:exile_vote:{vote.day}:"
                    f"{vote.voter_id}:{vote.target_id}"
                ),
                day=vote.day,
                phase="VOTE_RESULT",
                kind="exile_vote",
                commitment="vote",
                actor_id=vote.voter_id,
                actual_target_id=vote.target_id,
                expected_field="vote",
                post_decision_summary=current_summaries.get(vote.voter_id),
            )

    def _append_observation(
        self,
        *,
        observation_id: str,
        day: int,
        phase: str,
        kind: Literal["public_speech", "sheriff_vote", "exile_vote"],
        commitment: str,
        actor_id: int,
        actual_target_id: Optional[int],
        expected_field: str,
        post_decision_summary: Optional[dict[str, object]],
        allowed_target_ids: Optional[set[int]] = None,
    ) -> None:
        previous = self._last_summaries.get(actor_id)
        expected_target_ids = _expected_targets(previous, expected_field)
        if allowed_target_ids is not None:
            expected_target_ids = [
                target_id
                for target_id in expected_target_ids
                if target_id in allowed_target_ids
            ]
        previous_basis = set(
            str(evidence_id)
            for evidence_id in (previous or {}).get("basis_evidence_ids", [])
        )
        decision_baseline = self._last_decision_basis.get(actor_id)
        new_evidence_ids = (
            sorted(previous_basis - decision_baseline)
            if decision_baseline is not None
            else []
        )
        if actual_target_id is None or not expected_target_ids:
            alignment = "unscored"
        elif actual_target_id in expected_target_ids:
            alignment = "aligned"
        elif new_evidence_ids:
            alignment = "explained_change"
        else:
            alignment = "unexplained_change"

        observation = StanceObservationV1(
            observation_id=observation_id,
            capture_index=self.capture_count,
            day=day,
            phase=phase,
            kind=kind,
            commitment=commitment,
            actor_id=actor_id,
            actual_target_id=actual_target_id,
            expected_target_ids=expected_target_ids,
            alignment=alignment,
            new_evidence_ids=new_evidence_ids,
            previous_observation_id=self._last_observation_id.get(actor_id),
        )
        self._observations.append(observation.model_dump(mode="json"))
        self._last_decision_basis[actor_id] = {
            str(evidence_id)
            for evidence_id in (post_decision_summary or {}).get(
                "basis_evidence_ids",
                [],
            )
        }
        self._last_observation_id[actor_id] = observation_id

    def _build_change(
        self,
        current: dict[str, object],
        previous: Optional[dict[str, object]],
    ) -> Optional[dict[str, object]]:
        tracked_fields = (
            "trusted_target_ids",
            "primary_suspect_id",
            "secondary_suspect_id",
            "provisional_vote_target_id",
            "verification_target_id",
            "verification_condition",
            "confidence",
            "basis_evidence_ids",
        )
        empty_defaults: dict[str, object] = {
            "trusted_target_ids": [],
            "primary_suspect_id": None,
            "secondary_suspect_id": None,
            "provisional_vote_target_id": None,
            "verification_target_id": None,
            "verification_condition": None,
            "confidence": 0.0,
            "basis_evidence_ids": [],
        }
        changed_fields = [
            field
            for field in tracked_fields
            if current[field]
            != (previous[field] if previous is not None else empty_defaults[field])
        ]
        if not changed_fields:
            return None

        previous_basis = set(
            str(item)
            for item in (previous or empty_defaults)["basis_evidence_ids"]
        )
        current_basis = set(str(item) for item in current["basis_evidence_ids"])
        change = StanceChangeV1(
            capture_index=self.capture_count,
            day=int(current["day"]),
            phase=str(current["phase"]),
            actor_id=int(current["actor_id"]),
            changed_fields=list(changed_fields),
            previous_primary_suspect_id=(
                previous.get("primary_suspect_id") if previous else None
            ),
            primary_suspect_id=current.get("primary_suspect_id"),
            previous_secondary_suspect_id=(
                previous.get("secondary_suspect_id") if previous else None
            ),
            secondary_suspect_id=current.get("secondary_suspect_id"),
            previous_trusted_target_ids=list(
                (previous or empty_defaults)["trusted_target_ids"]
            ),
            trusted_target_ids=list(current["trusted_target_ids"]),
            previous_provisional_vote_target_id=(
                previous.get("provisional_vote_target_id") if previous else None
            ),
            provisional_vote_target_id=current.get("provisional_vote_target_id"),
            previous_verification_target_id=(
                previous.get("verification_target_id") if previous else None
            ),
            verification_target_id=current.get("verification_target_id"),
            previous_verification_condition=(
                previous.get("verification_condition") if previous else None
            ),
            verification_condition=current.get("verification_condition"),
            previous_confidence=float(
                (previous or empty_defaults)["confidence"]
            ),
            confidence=float(current["confidence"]),
            added_evidence_ids=sorted(current_basis - previous_basis),
            removed_evidence_ids=sorted(previous_basis - current_basis),
        )
        return change.model_dump(mode="json")

    def build_result(self) -> dict[str, object]:
        return {
            "schema_version": STANCE_SCHEMA_VERSION,
            "belief_schema_version": BELIEF_SCHEMA_VERSION,
            "mode": STANCE_MODE,
            "capture_count": self.capture_count,
            "changes": list(self._changes),
            "observations": list(self._observations),
            "final_states": [
                self._final_summaries[actor_id]
                for actor_id in sorted(self._final_summaries)
            ],
        }


def aggregate_stance_traces(
    game_results: list[dict[str, object]],
) -> dict[str, object]:
    alignment_counts: Counter[str] = Counter()
    kind_counts: dict[str, Counter[str]] = {}
    total_changes = 0
    total_observations = 0

    for game_result in game_results:
        trace = game_result.get("stance_trace")
        if not isinstance(trace, dict):
            raise ValueError("stance aggregation requires detailed traces")
        if trace.get("schema_version") != STANCE_SCHEMA_VERSION:
            raise ValueError("stance trace schema mismatch")
        changes = trace["changes"]
        observations = trace["observations"]
        total_changes += len(changes)
        total_observations += len(observations)
        for observation in observations:
            alignment = str(observation["alignment"])
            kind = str(observation["kind"])
            alignment_counts[alignment] += 1
            kind_counts.setdefault(kind, Counter())[alignment] += 1

    scored_count = (
        alignment_counts["aligned"]
        + alignment_counts["explained_change"]
        + alignment_counts["unexplained_change"]
    )
    game_count = len(game_results)
    return {
        "schema_version": STANCE_SCHEMA_VERSION,
        "mode": STANCE_MODE,
        "game_count": game_count,
        "observation_count": total_observations,
        "change_count": total_changes,
        "average_changes_per_game": _round_value(
            total_changes / game_count if game_count else 0.0
        ),
        "alignment_counts": {
            alignment: alignment_counts[alignment]
            for alignment in (
                "aligned",
                "explained_change",
                "unexplained_change",
                "unscored",
            )
        },
        "scored_observation_count": scored_count,
        "alignment_rate": _optional_rate(
            alignment_counts["aligned"],
            scored_count,
        ),
        "unexplained_change_rate": _optional_rate(
            alignment_counts["unexplained_change"],
            scored_count,
        ),
        "by_kind": {
            kind: {
                alignment: counts[alignment]
                for alignment in (
                    "aligned",
                    "explained_change",
                    "unexplained_change",
                    "unscored",
                )
            }
            for kind, counts in (
                (kind, kind_counts.get(kind, Counter()))
                for kind in (
                    "public_speech",
                    "sheriff_vote",
                    "exile_vote",
                )
            )
        },
    }


def _build_actor_stance_summary(
    game_state: rules.WolfGameState,
    characters: dict[int, rules.CharacterState],
    actor_state: dict[str, object],
) -> ActorStanceSummaryV1:
    actor_id = int(actor_state["actor_id"])
    actor = characters.get(actor_id)
    if actor is None or actor.is_player:
        raise ValueError("stance actor must be an existing NPC")

    alive_target_ids = {
        character.id
        for character in game_state.characters
        if character.alive and character.id != actor_id
    }
    seats = [
        seat
        for seat in actor_state["seats"]
        if int(seat["target_id"]) in alive_target_ids
    ]
    suspected = sorted(
        (
            seat
            for seat in seats
            if int(seat["suspicion_score"]) >= STANCE_SUSPECT_SCORE_MIN
        ),
        key=lambda seat: (
            -int(seat["suspicion_score"]),
            -float(seat["confidence"]),
            int(seat["target_id"]),
        ),
    )
    trusted = sorted(
        (
            seat
            for seat in seats
            if int(seat["suspicion_score"]) <= STANCE_TRUST_SCORE_MAX
        ),
        key=lambda seat: (
            int(seat["suspicion_score"]),
            -float(seat["confidence"]),
            int(seat["target_id"]),
        ),
    )

    primary_suspect_id = (
        int(suspected[0]["target_id"])
        if suspected
        else None
    )
    secondary_suspect_id = (
        int(suspected[1]["target_id"])
        if len(suspected) > 1
        else None
    )
    trusted_target_ids = [
        int(seat["target_id"])
        for seat in trusted[:2]
    ]

    latest_position = _latest_current_day_position(game_state, actor_id)
    provisional_vote_target_id = primary_suspect_id
    verification_target_id: Optional[int] = None
    verification_condition: Optional[str] = None
    if latest_position is not None:
        declared_vote = latest_position.provisional_vote_target_id
        if declared_vote in alive_target_ids:
            provisional_vote_target_id = declared_vote
        declared_verification = latest_position.change_condition_target_id
        if declared_verification in alive_target_ids:
            verification_target_id = declared_verification
            if latest_position.change_condition is not None:
                verification_condition = latest_position.change_condition.value

    seat_by_target = {
        int(seat["target_id"]): seat
        for seat in seats
    }
    basis_target_ids = {
        target_id
        for target_id in (
            trusted_target_ids
            + [
                primary_suspect_id,
                secondary_suspect_id,
                provisional_vote_target_id,
                verification_target_id,
            ]
        )
        if target_id is not None
    }
    basis_evidence_ids = sorted(
        {
            str(contribution["evidence_id"])
            for target_id in basis_target_ids
            for contribution in seat_by_target.get(target_id, {}).get(
                "contributions",
                [],
            )
        }
    )
    selected_confidences = [
        float(seat_by_target[target_id]["confidence"])
        for target_id in basis_target_ids
        if target_id in seat_by_target
    ]

    return ActorStanceSummaryV1(
        actor_id=actor_id,
        actor_name=str(actor_state["actor_name"]),
        alive=bool(actor_state["alive"]),
        day=int(actor_state["day"]),
        phase=str(actor_state["phase"]),
        trusted_target_ids=trusted_target_ids,
        primary_suspect_id=primary_suspect_id,
        secondary_suspect_id=secondary_suspect_id,
        provisional_vote_target_id=provisional_vote_target_id,
        verification_target_id=verification_target_id,
        verification_condition=verification_condition,
        confidence=_round_value(
            max(selected_confidences) if selected_confidences else 0.0
        ),
        basis_evidence_ids=basis_evidence_ids,
    )


def _latest_current_day_position(
    game_state: rules.WolfGameState,
    actor_id: int,
) -> Optional[rules.PublicPositionV1]:
    for speech in reversed(game_state.speeches):
        if (
            speech.day == game_state.day
            and speech.character_id == actor_id
            and speech.public_position is not None
        ):
            return speech.public_position
    return None


def _expected_targets(
    summary: Optional[dict[str, object]],
    expected_field: str,
) -> list[int]:
    if summary is None:
        return []
    if expected_field == "vote":
        target_id = (
            summary.get("provisional_vote_target_id")
            or summary.get("primary_suspect_id")
        )
        return [int(target_id)] if target_id is not None else []
    if expected_field == "suspect":
        return [
            int(target_id)
            for target_id in (
                summary.get("primary_suspect_id"),
                summary.get("secondary_suspect_id"),
            )
            if target_id is not None
        ]
    if expected_field == "trust":
        return [
            int(target_id)
            for target_id in summary.get("trusted_target_ids", [])
        ]
    return []


def _sheriff_event_candidate_ids(
    game_state: rules.WolfGameState,
    event: rules.SheriffEventState,
) -> set[int]:
    election = game_state.sheriff_election
    if election is None:
        return set()
    vote_round = 0
    if event.context.startswith("round:"):
        try:
            vote_round = max(0, int(event.context.split(":", 1)[1]))
        except ValueError:
            vote_round = 0
    candidate_ids = (
        election.runoff_candidates
        if vote_round > 0 and election.runoff_candidates
        else election.candidates
    )
    return {
        candidate_id
        for candidate_id in candidate_ids
        if candidate_id not in election.withdrawn
        and rules.get_character(game_state, candidate_id).alive
    }


def _optional_rate(numerator: int, denominator: int) -> Optional[float]:
    if denominator == 0:
        return None
    return _round_value(numerator / denominator)


def _round_value(value: float) -> float:
    return round(float(value), 6)


__all__ = [
    "STANCE_MODE",
    "STANCE_SCHEMA_VERSION",
    "ActorStanceSummaryV1",
    "StanceChangeV1",
    "StanceObservationV1",
    "StanceTraceRecorder",
    "aggregate_stance_traces",
    "build_stance_snapshot",
]
