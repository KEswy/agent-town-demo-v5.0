"""Legal-perspective shadow beliefs for Agent Town V3.

The V3.1-D implementation remains observational. It adds auditable public
soft-evidence decay and structured actor-private chat evidence, but no live
speech, action, or vote reads these scores yet.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from . import main as rules


BELIEF_SCHEMA_VERSION = "belief_state.v2"
BELIEF_EVIDENCE_SCHEMA_VERSION = "belief_evidence.v1"
BELIEF_MODE = "shadow"
PUBLIC_SOFT_EVIDENCE_DAILY_DECAY = 0.75
SOFT_PUBLIC_EVIDENCE_KINDS = frozenset(
    {
        "public_role_claim",
        "public_seer_black_check",
        "public_seer_good_check",
        "public_position_suspect",
        "public_position_trust",
        "public_position_provisional_vote",
        "public_position_seer_support",
        "public_position_seer_oppose",
        "public_low_information_speech",
    }
)


class StrictBeliefModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BeliefEvidenceV1(StrictBeliefModel):
    schema_version: Literal["belief_evidence.v1"] = BELIEF_EVIDENCE_SCHEMA_VERSION
    evidence_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    visibility: Literal["public", "actor_private", "wolf_team"]
    observer_ids: list[int] = Field(default_factory=list)
    day: int = Field(ge=1)
    phase: str = Field(min_length=1)
    source_actor_id: Optional[int] = Field(default=None, gt=0)
    target_id: int = Field(gt=0)
    result: str = ""
    summary: str = Field(min_length=1)


class BeliefContributionV1(StrictBeliefModel):
    evidence_id: str = Field(min_length=1)
    weight: int = Field(ge=-100, le=100)


class SeatBeliefV1(StrictBeliefModel):
    target_id: int = Field(gt=0)
    suspicion_score: int = Field(ge=-100, le=100)
    confidence: float = Field(ge=0.0, le=1.0)
    stance: Literal["trusted", "uncertain", "suspected"]
    contributions: list[BeliefContributionV1] = Field(default_factory=list)


class ActorBeliefStateV1(StrictBeliefModel):
    actor_id: int = Field(gt=0)
    actor_name: str = Field(min_length=1)
    alive: bool
    day: int = Field(ge=1)
    phase: str = Field(min_length=1)
    seats: list[SeatBeliefV1] = Field(default_factory=list)


class BeliefChangeV1(StrictBeliefModel):
    capture_index: int = Field(ge=1)
    day: int = Field(ge=1)
    phase: str = Field(min_length=1)
    actor_id: int = Field(gt=0)
    target_id: int = Field(gt=0)
    previous_score: int = Field(ge=-100, le=100)
    suspicion_score: int = Field(ge=-100, le=100)
    delta: int = Field(ge=-200, le=200)
    confidence: float = Field(ge=0.0, le=1.0)
    added_contributions: list[BeliefContributionV1] = Field(default_factory=list)
    updated_contributions: list[BeliefContributionV1] = Field(default_factory=list)
    removed_evidence_ids: list[str] = Field(default_factory=list)


def build_belief_snapshot(
    game_state: rules.WolfGameState,
    *,
    observer_ids: Optional[Iterable[int]] = None,
) -> dict[str, object]:
    """Build one actor-scoped snapshot without mutating rule state."""

    requested_ids = (
        {int(observer_id) for observer_id in observer_ids}
        if observer_ids is not None
        else {
            character.id
            for character in game_state.characters
            if not character.is_player
        }
    )
    observers = [
        character
        for character in game_state.characters
        if not character.is_player and character.id in requested_ids
    ]
    if len(observers) != len(requested_ids):
        raise ValueError("belief observers must be existing NPC character ids")

    evidence = _build_evidence_ledger(game_state, requested_ids)
    actor_states = [
        _build_actor_belief_state(game_state, observer, evidence)
        for observer in sorted(observers, key=lambda character: character.id)
    ]
    return {
        "schema_version": BELIEF_SCHEMA_VERSION,
        "mode": BELIEF_MODE,
        "day": game_state.day,
        "phase": game_state.phase,
        "evidence_ledger": [
            item.model_dump(mode="json")
            for item in sorted(evidence, key=lambda item: item.evidence_id)
        ],
        "actors": [
            actor_state.model_dump(mode="json")
            for actor_state in actor_states
        ],
    }


class BeliefTraceRecorder:
    """Capture only belief changes while retaining a deduplicated ledger."""

    def __init__(self) -> None:
        self.capture_count = 0
        self._evidence_by_id: dict[str, dict[str, object]] = {}
        self._last_seats: dict[tuple[int, int], dict[str, object]] = {}
        self._final_actor_states: dict[int, dict[str, object]] = {}
        self._changes: list[dict[str, object]] = []

    def capture(self, game_state: rules.WolfGameState) -> None:
        active_observer_ids = [
            character.id
            for character in game_state.characters
            if not character.is_player and character.alive
        ]
        if not active_observer_ids:
            return
        snapshot = build_belief_snapshot(
            game_state,
            observer_ids=active_observer_ids,
        )
        self.capture_count += 1
        for evidence in snapshot["evidence_ledger"]:
            evidence_id = str(evidence["evidence_id"])
            previous = self._evidence_by_id.get(evidence_id)
            if previous is not None and previous != evidence:
                raise ValueError(f"belief evidence id changed meaning: {evidence_id}")
            self._evidence_by_id[evidence_id] = evidence

        for actor_state in snapshot["actors"]:
            actor_id = int(actor_state["actor_id"])
            self._final_actor_states[actor_id] = actor_state
            for seat in actor_state["seats"]:
                target_id = int(seat["target_id"])
                key = (actor_id, target_id)
                previous = self._last_seats.get(key)
                if previous != seat:
                    change = self._build_change(
                        actor_state,
                        seat,
                        previous,
                    )
                    if change is not None:
                        self._changes.append(change)
                self._last_seats[key] = seat
        for character in game_state.characters:
            if character.is_player or character.alive:
                continue
            frozen_state = self._final_actor_states.get(character.id)
            if frozen_state is not None and bool(frozen_state["alive"]):
                frozen_state = dict(frozen_state)
                frozen_state["alive"] = False
                self._final_actor_states[character.id] = frozen_state

    def _build_change(
        self,
        actor_state: dict[str, object],
        seat: dict[str, object],
        previous: Optional[dict[str, object]],
    ) -> Optional[dict[str, object]]:
        previous_score = int(previous["suspicion_score"]) if previous else 0
        previous_contributions = {
            str(item["evidence_id"]): item
            for item in (previous or {}).get("contributions", [])
        }
        current_contributions = {
            str(item["evidence_id"]): item
            for item in seat["contributions"]
        }
        added = [
            current_contributions[evidence_id]
            for evidence_id in sorted(
                set(current_contributions) - set(previous_contributions)
            )
        ]
        removed = sorted(
            set(previous_contributions) - set(current_contributions)
        )
        updated = [
            current_contributions[evidence_id]
            for evidence_id in sorted(
                set(current_contributions) & set(previous_contributions)
            )
            if current_contributions[evidence_id]
            != previous_contributions[evidence_id]
        ]
        if (
            previous is None
            and not added
            and int(seat["suspicion_score"]) == 0
        ):
            return None
        change = BeliefChangeV1(
            capture_index=self.capture_count,
            day=int(actor_state["day"]),
            phase=str(actor_state["phase"]),
            actor_id=int(actor_state["actor_id"]),
            target_id=int(seat["target_id"]),
            previous_score=previous_score,
            suspicion_score=int(seat["suspicion_score"]),
            delta=int(seat["suspicion_score"]) - previous_score,
            confidence=float(seat["confidence"]),
            added_contributions=[
                BeliefContributionV1.model_validate(item)
                for item in added
            ],
            updated_contributions=[
                BeliefContributionV1.model_validate(item)
                for item in updated
            ],
            removed_evidence_ids=removed,
        )
        return change.model_dump(mode="json")

    def build_result(self) -> dict[str, object]:
        evidence = [
            self._evidence_by_id[evidence_id]
            for evidence_id in sorted(self._evidence_by_id)
        ]
        final_states = [
            self._final_actor_states[actor_id]
            for actor_id in sorted(self._final_actor_states)
        ]
        return {
            "schema_version": BELIEF_SCHEMA_VERSION,
            "mode": BELIEF_MODE,
            "capture_count": self.capture_count,
            "evidence_ledger": evidence,
            "changes": list(self._changes),
            "final_states": final_states,
        }


def aggregate_belief_traces(
    game_results: list[dict[str, object]],
) -> dict[str, object]:
    if not game_results:
        raise ValueError("belief aggregation requires at least one game")
    visibility_counts: Counter[str] = Counter()
    kind_counts: Counter[str] = Counter()
    total_evidence = 0
    total_changes = 0
    confidence_values: list[float] = []
    for game in game_results:
        trace = game.get("belief_trace")
        if not isinstance(trace, dict):
            raise ValueError("simulation result is missing a belief trace")
        if trace.get("schema_version") != BELIEF_SCHEMA_VERSION:
            raise ValueError("simulation result uses an incompatible belief schema")
        ledger = trace["evidence_ledger"]
        total_evidence += len(ledger)
        total_changes += len(trace["changes"])
        for evidence in ledger:
            visibility_counts[str(evidence["visibility"])] += 1
            kind_counts[str(evidence["kind"])] += 1
        for actor_state in trace["final_states"]:
            for seat in actor_state["seats"]:
                confidence_values.append(float(seat["confidence"]))
    game_count = len(game_results)
    return {
        "schema_version": BELIEF_SCHEMA_VERSION,
        "mode": BELIEF_MODE,
        "game_count": game_count,
        "evidence_count": total_evidence,
        "change_count": total_changes,
        "average_evidence_per_game": _round_value(total_evidence / game_count),
        "average_changes_per_game": _round_value(total_changes / game_count),
        "average_final_confidence": (
            _round_value(sum(confidence_values) / len(confidence_values))
            if confidence_values
            else None
        ),
        "visibility_counts": {
            visibility: visibility_counts.get(visibility, 0)
            for visibility in ("public", "actor_private", "wolf_team")
        },
        "kind_counts": {
            kind: kind_counts[kind]
            for kind in sorted(kind_counts)
        },
    }


def _build_evidence_ledger(
    game_state: rules.WolfGameState,
    observer_ids: set[int],
) -> list[BeliefEvidenceV1]:
    evidence: list[BeliefEvidenceV1] = []
    evidence.extend(_build_public_claim_evidence(game_state))
    evidence.extend(_build_public_speech_evidence(game_state))
    evidence.extend(_build_sheriff_evidence(game_state))
    evidence.extend(_build_exile_vote_evidence(game_state))
    evidence.extend(_build_private_chat_evidence(game_state, observer_ids))
    evidence.extend(_build_private_role_evidence(game_state, observer_ids))
    evidence_by_id: dict[str, BeliefEvidenceV1] = {}
    for item in evidence:
        previous = evidence_by_id.get(item.evidence_id)
        if previous is not None and previous != item:
            raise ValueError(f"duplicate belief evidence id: {item.evidence_id}")
        evidence_by_id[item.evidence_id] = item
    return list(evidence_by_id.values())


def _build_public_claim_evidence(
    game_state: rules.WolfGameState,
) -> list[BeliefEvidenceV1]:
    evidence = []
    for index, claim in enumerate(game_state.public_claims, start=1):
        if claim.claim_type == "seer_check" and claim.target_id is not None:
            kind = (
                "public_seer_black_check"
                if claim.result == "werewolf"
                else "public_seer_good_check"
            )
            result_label = "查杀" if claim.result == "werewolf" else "金水"
            evidence.append(
                _evidence(
                    evidence_id=(
                        f"belief:claim:{index}:{claim.day}:{claim.character_id}:"
                        f"{claim.target_id}:{claim.result}"
                    ),
                    kind=kind,
                    visibility="public",
                    day=claim.day,
                    phase="PUBLIC_CLAIM",
                    source_actor_id=claim.character_id,
                    target_id=claim.target_id,
                    result=claim.result,
                    summary=(
                        f"{claim.character_id}号公开称验{claim.target_id}号为"
                        f"{result_label}；该说法未由规则验真。"
                    ),
                )
            )
        elif claim.claim_type == "role" and claim.claimed_role:
            evidence.append(
                _evidence(
                    evidence_id=(
                        f"belief:role_claim:{index}:{claim.day}:"
                        f"{claim.character_id}:{claim.claimed_role}"
                    ),
                    kind="public_role_claim",
                    visibility="public",
                    day=claim.day,
                    phase="PUBLIC_CLAIM",
                    source_actor_id=claim.character_id,
                    target_id=claim.character_id,
                    result=claim.claimed_role,
                    summary=(
                        f"{claim.character_id}号公开自称"
                        f"{rules.ROLE_LABELS.get(claim.claimed_role, claim.claimed_role)}。"
                    ),
                )
            )
    return evidence


def _build_public_speech_evidence(
    game_state: rules.WolfGameState,
) -> list[BeliefEvidenceV1]:
    evidence = []
    for speech_index, speech in enumerate(game_state.speeches, start=1):
        position = speech.public_position
        if position is not None:
            position_items = []
            position_items.extend(
                ("public_position_suspect", target_id, "怀疑")
                for target_id in position.suspected_target_ids
            )
            position_items.extend(
                ("public_position_trust", target_id, "信任")
                for target_id in position.trusted_target_ids
            )
            if position.provisional_vote_target_id is not None:
                position_items.append(
                    (
                        "public_position_provisional_vote",
                        position.provisional_vote_target_id,
                        "暂定票",
                    )
                )
            if position.seer_support_id is not None:
                position_items.append(
                    ("public_position_seer_support", position.seer_support_id, "支持预言家")
                )
            if position.seer_oppose_id is not None:
                position_items.append(
                    ("public_position_seer_oppose", position.seer_oppose_id, "反对预言家")
                )
            for item_index, (kind, target_id, label) in enumerate(
                position_items,
                start=1,
            ):
                evidence.append(
                    _evidence(
                        evidence_id=(
                            f"belief:position:{speech_index}:{item_index}:"
                            f"{speech.day}:{speech.character_id}:{target_id}:{kind}"
                        ),
                        kind=kind,
                        visibility="public",
                        day=speech.day,
                        phase=speech.phase,
                        source_actor_id=speech.character_id,
                        target_id=target_id,
                        result=label,
                        summary=(
                            f"{speech.character_id}号的公开立场对"
                            f"{target_id}号记录为“{label}”。"
                        ),
                    )
                )
        if rules.is_low_information_public_speech(game_state, speech):
            evidence.append(
                _evidence(
                    evidence_id=(
                        f"belief:low_information:{speech_index}:"
                        f"{speech.day}:{speech.character_id}"
                    ),
                    kind="public_low_information_speech",
                    visibility="public",
                    day=speech.day,
                    phase=speech.phase,
                    source_actor_id=speech.character_id,
                    target_id=speech.character_id,
                    result="low_information",
                    summary=f"{speech.character_id}号的公开发言被规则保守标记为信息量较低。",
                )
            )
    return evidence


def _build_sheriff_evidence(
    game_state: rules.WolfGameState,
) -> list[BeliefEvidenceV1]:
    supported_event_types = {
        "sheriff_vote": "public_sheriff_vote",
        "withdraw": "public_sheriff_withdraw",
        "elected": "public_sheriff_elected",
        "nomination": "public_sheriff_nomination",
        "badge_transfer": "public_badge_transfer",
    }
    evidence = []
    for index, event in enumerate(game_state.sheriff_events, start=1):
        kind = supported_event_types.get(event.event_type)
        if kind is None:
            continue
        target_id = event.target_id
        if event.event_type in {"withdraw", "elected"}:
            target_id = event.actor_id
        if target_id is None:
            continue
        public_context = (
            event.context
            if event.event_type == "sheriff_vote"
            and event.context.startswith("round:")
            else ""
        )
        evidence.append(
            _evidence(
                evidence_id=(
                    f"belief:sheriff:{index}:{event.day}:{event.event_type}:"
                    f"{event.actor_id or 0}:{target_id}:{public_context or 'none'}"
                ),
                kind=kind,
                visibility="public",
                day=event.day,
                phase="SHERIFF_EVENT",
                source_actor_id=event.actor_id,
                target_id=target_id,
                result=public_context,
                summary=_sheriff_evidence_summary(event, target_id),
            )
        )
    return evidence


def _build_exile_vote_evidence(
    game_state: rules.WolfGameState,
) -> list[BeliefEvidenceV1]:
    if game_state.phase == "VOTE":
        visible_votes = [
            vote for vote in game_state.votes if vote.day < game_state.day
        ]
    else:
        visible_votes = list(game_state.votes)
    return [
        _evidence(
            evidence_id=(
                f"belief:exile_vote:{index}:{vote.day}:"
                f"{vote.voter_id}:{vote.target_id}"
            ),
            kind="public_exile_vote",
            visibility="public",
            day=vote.day,
            phase="VOTE_RESULT",
            source_actor_id=vote.voter_id,
            target_id=vote.target_id,
            result="vote",
            summary=f"第{vote.day}天，{vote.voter_id}号公开投给{vote.target_id}号。",
        )
        for index, vote in enumerate(visible_votes, start=1)
    ]


def _build_private_role_evidence(
    game_state: rules.WolfGameState,
    observer_ids: set[int],
) -> list[BeliefEvidenceV1]:
    evidence = []
    characters = {character.id: character for character in game_state.characters}
    for observer_id in sorted(observer_ids):
        observer = characters[observer_id]
        if observer.role == "werewolf":
            for teammate in game_state.characters:
                if teammate.id == observer.id or teammate.role != "werewolf":
                    continue
                evidence.append(
                    _evidence(
                        evidence_id=f"belief:wolf_team:{observer.id}:{teammate.id}",
                        kind="private_wolf_teammate",
                        visibility="wolf_team",
                        observer_ids=[observer.id],
                        day=1,
                        phase="ROLE_KNOWLEDGE",
                        source_actor_id=observer.id,
                        target_id=teammate.id,
                        result="werewolf_teammate",
                        summary=f"{teammate.id}号是该狼人依法知晓的狼队友。",
                    )
                )
        if observer.role == "seer":
            for day, target_id, result in rules.get_character_seer_checks(
                game_state,
                observer.id,
            ):
                evidence.append(
                    _evidence(
                        evidence_id=(
                            f"belief:private_seer:{day}:{observer.id}:"
                            f"{target_id}:{result}"
                        ),
                        kind="private_seer_check",
                        visibility="actor_private",
                        observer_ids=[observer.id],
                        day=day,
                        phase="NIGHT",
                        source_actor_id=observer.id,
                        target_id=target_id,
                        result=result,
                        summary=(
                            f"该预言家第{day}夜依法得知{target_id}号的查验结果为"
                            f"{'狼人' if result == 'werewolf' else '好人'}。"
                        ),
                    )
                )
        if observer.role == "witch":
            for resolution in game_state.night_resolutions:
                if resolution.attacked_target_id is None:
                    continue
                evidence.append(
                    _evidence(
                        evidence_id=(
                            f"belief:witch_attack:{resolution.day}:{observer.id}:"
                            f"{resolution.attacked_target_id}"
                        ),
                        kind="private_witch_attack_target",
                        visibility="actor_private",
                        observer_ids=[observer.id],
                        day=resolution.day,
                        phase="NIGHT",
                        source_actor_id=observer.id,
                        target_id=resolution.attacked_target_id,
                        result="attacked",
                        summary=(
                            f"该女巫第{resolution.day}夜依法得知"
                            f"{resolution.attacked_target_id}号是当夜刀口。"
                        ),
                    )
                )
    return evidence


def _build_private_chat_evidence(
    game_state: rules.WolfGameState,
    observer_ids: set[int],
) -> list[BeliefEvidenceV1]:
    evidence = []
    valid_character_ids = {
        character.id
        for character in game_state.characters
    }
    for conversation in game_state.private_conversations:
        if (
            not conversation.effective
            or conversation.npc_character_id not in observer_ids
        ):
            continue
        for influence in conversation.belief_influences:
            if influence.target_id not in valid_character_ids:
                raise ValueError(
                    "private-chat belief target must be an existing character"
                )
            label = "怀疑" if influence.direction == "suspect" else "信任"
            evidence.append(
                _evidence(
                    evidence_id=influence.evidence_id,
                    kind=f"private_chat_{influence.direction}",
                    visibility="actor_private",
                    observer_ids=[conversation.npc_character_id],
                    day=conversation.day,
                    phase="FREE_ACTIVITY",
                    source_actor_id=game_state.player_character_id,
                    target_id=influence.target_id,
                    result=influence.direction,
                    summary=(
                        f"玩家第{conversation.day}天私下向该 NPC 明确表达对"
                        f"{influence.target_id}号的{label}；仅该 NPC 可见。"
                    ),
                )
            )
    return evidence


def _build_actor_belief_state(
    game_state: rules.WolfGameState,
    observer: rules.CharacterState,
    evidence: list[BeliefEvidenceV1],
) -> ActorBeliefStateV1:
    contributions_by_target: dict[int, list[BeliefContributionV1]] = {
        character.id: []
        for character in game_state.characters
        if character.id != observer.id
    }
    for item in evidence:
        if item.visibility != "public" and observer.id not in item.observer_ids:
            continue
        contribution = _interpret_evidence(game_state, observer, item)
        if contribution is None:
            continue
        target_id, weight = contribution
        weight = _apply_public_soft_evidence_decay(
            game_state,
            observer,
            item,
            weight,
        )
        if target_id == observer.id or target_id not in contributions_by_target:
            continue
        contributions_by_target[target_id].append(
            BeliefContributionV1(
                evidence_id=item.evidence_id,
                weight=weight,
            )
        )

    seats = []
    for target_id in sorted(contributions_by_target):
        contributions = sorted(
            contributions_by_target[target_id],
            key=lambda item: item.evidence_id,
        )
        raw_score = sum(item.weight for item in contributions)
        score = max(-100, min(100, raw_score))
        confidence = min(
            1.0,
            sum(abs(item.weight) for item in contributions) / 100,
        )
        stance: Literal["trusted", "uncertain", "suspected"] = "uncertain"
        if score >= 20:
            stance = "suspected"
        elif score <= -15:
            stance = "trusted"
        seats.append(
            SeatBeliefV1(
                target_id=target_id,
                suspicion_score=score,
                confidence=_round_value(confidence),
                stance=stance,
                contributions=contributions,
            )
        )
    return ActorBeliefStateV1(
        actor_id=observer.id,
        actor_name=observer.name,
        alive=observer.alive,
        day=game_state.day,
        phase=game_state.phase,
        seats=seats,
    )


def _interpret_evidence(
    game_state: rules.WolfGameState,
    observer: rules.CharacterState,
    evidence: BeliefEvidenceV1,
) -> Optional[tuple[int, int]]:
    if evidence.kind == "private_wolf_teammate":
        return evidence.target_id, -100
    if evidence.kind == "private_seer_check":
        return evidence.target_id, 100 if evidence.result == "werewolf" else -100
    if evidence.kind == "private_witch_attack_target":
        return evidence.target_id, -18
    if evidence.kind == "private_chat_suspect":
        return evidence.target_id, 12
    if evidence.kind == "private_chat_trust":
        return evidence.target_id, -8

    target_id = evidence.target_id
    if evidence.kind == "public_role_claim":
        competing_count = sum(
            1
            for claim in game_state.public_claims
            if claim.claim_type == "role"
            and claim.claimed_role == evidence.result
            and claim.character_id != evidence.target_id
        )
        if observer.role == evidence.result:
            return target_id, 36
        if competing_count:
            return target_id, _public_weight(observer, 6, "claim")
        return None
    if evidence.kind == "public_seer_black_check":
        if target_id == observer.id and evidence.source_actor_id is not None:
            return evidence.source_actor_id, _public_weight(observer, 20, "claim")
        return target_id, _public_weight(observer, 28, "claim")
    if evidence.kind == "public_seer_good_check":
        if target_id == observer.id and evidence.source_actor_id is not None:
            return evidence.source_actor_id, _public_weight(observer, -6, "claim")
        return target_id, _public_weight(observer, -12, "claim")

    base_weights = {
        "public_position_suspect": 10,
        "public_position_trust": -8,
        "public_position_provisional_vote": 5,
        "public_position_seer_support": -8,
        "public_position_seer_oppose": 12,
        "public_low_information_speech": 4,
        "public_sheriff_vote": -4,
        "public_sheriff_withdraw": 3,
        "public_sheriff_elected": -4,
        "public_sheriff_nomination": 10,
        "public_badge_transfer": -3,
        "public_exile_vote": 7,
    }
    base_weight = base_weights.get(evidence.kind)
    if base_weight is None:
        return None
    return target_id, _public_weight(observer, base_weight, "social")


def _apply_public_soft_evidence_decay(
    game_state: rules.WolfGameState,
    observer: rules.CharacterState,
    evidence: BeliefEvidenceV1,
    weight: int,
) -> int:
    if (
        evidence.visibility != "public"
        or evidence.kind not in SOFT_PUBLIC_EVIDENCE_KINDS
    ):
        return weight
    if evidence.kind == "public_role_claim" and observer.role == evidence.result:
        return weight
    age_days = max(0, game_state.day - evidence.day)
    if age_days == 0:
        return weight
    decayed = int(
        round(weight * (PUBLIC_SOFT_EVIDENCE_DAILY_DECAY ** age_days))
    )
    return max(-100, min(100, decayed))


def _public_weight(
    observer: rules.CharacterState,
    base_weight: int,
    category: str,
) -> int:
    tuning = rules.get_character_strategy_tuning(observer)
    if category == "claim":
        factor = (
            0.65
            + tuning.deception_susceptibility * 0.55
            + tuning.social_susceptibility * 0.20
            - tuning.reasoning_skill * 0.15
        )
    else:
        factor = (
            0.72
            + tuning.social_susceptibility * 0.42
            + tuning.decision_variance * 0.10
            - tuning.reasoning_skill * 0.08
        )
    factor = max(0.40, min(1.40, factor))
    weight = int(round(base_weight * factor))
    if weight == 0 and base_weight != 0:
        return 1 if base_weight > 0 else -1
    return max(-100, min(100, weight))


def _evidence(
    *,
    evidence_id: str,
    kind: str,
    visibility: Literal["public", "actor_private", "wolf_team"],
    day: int,
    phase: str,
    target_id: int,
    summary: str,
    source_actor_id: Optional[int] = None,
    result: str = "",
    observer_ids: Optional[list[int]] = None,
) -> BeliefEvidenceV1:
    return BeliefEvidenceV1(
        evidence_id=evidence_id,
        kind=kind,
        visibility=visibility,
        observer_ids=observer_ids or [],
        day=day,
        phase=phase,
        source_actor_id=source_actor_id,
        target_id=target_id,
        result=result,
        summary=summary,
    )


def _sheriff_evidence_summary(
    event: rules.SheriffEventState,
    target_id: int,
) -> str:
    if event.event_type == "sheriff_vote":
        return f"第{event.day}天，{event.actor_id}号公开投给{target_id}号竞选警长。"
    if event.event_type == "withdraw":
        return f"第{event.day}天，{target_id}号公开退出警长竞选。"
    if event.event_type == "elected":
        return f"第{event.day}天，{target_id}号公开当选警长。"
    if event.event_type == "nomination":
        return f"第{event.day}天，警长公开归票给{target_id}号。"
    return f"第{event.day}天，警徽被公开移交给{target_id}号。"


def _round_value(value: float) -> float:
    return round(float(value), 6)


__all__ = [
    "BELIEF_EVIDENCE_SCHEMA_VERSION",
    "BELIEF_MODE",
    "BELIEF_SCHEMA_VERSION",
    "PUBLIC_SOFT_EVIDENCE_DAILY_DECAY",
    "SOFT_PUBLIC_EVIDENCE_KINDS",
    "ActorBeliefStateV1",
    "BeliefChangeV1",
    "BeliefContributionV1",
    "BeliefEvidenceV1",
    "BeliefTraceRecorder",
    "SeatBeliefV1",
    "aggregate_belief_traces",
    "build_belief_snapshot",
]
