"""Actor-scoped, public-fact reasoning for autonomous NPC beliefs.

This module never imports the live rule engine and never receives unrestricted
game state.  ``main.py`` must first project one NPC's lawful observation into
``NPCReasoningObservationV1``.  The reasoner then maintains fallible private
beliefs and public-story hypotheses without changing any authoritative role or
rule result.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


NPC_REASONING_OBSERVATION_SCHEMA_VERSION = "npc_reasoning_observation.v1"
NPC_BELIEF_STATE_SCHEMA_VERSION = "npc_belief_state.v1"
NPC_REASONING_SIGNAL_SCHEMA_VERSION = "npc_reasoning_signal.v1"
NPC_REASONING_POLICY_VERSION = "actor_scoped_hypotheses.v1"

ROLE_NAMES = ("werewolf", "seer", "witch", "hunter", "guard", "villager", "idiot")
MAX_PERSISTED_POSSIBLE_WORLDS = 24


class StrictReasoningModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        str_strip_whitespace=True,
    )


class ReasoningTuningV1(StrictReasoningModel):
    reasoning_skill: float = Field(ge=0.0, le=1.0)
    social_susceptibility: float = Field(ge=0.0, le=1.0)
    deception_susceptibility: float = Field(ge=0.0, le=1.0)
    plan_consistency: float = Field(ge=0.0, le=1.0)


class ReasoningPlayerV1(StrictReasoningModel):
    character_id: int = Field(gt=0)
    alive: bool
    suspicion: int = Field(ge=0, le=100)
    trust: float = Field(ge=0.0, le=1.0)
    public_pressure: int = Field(ge=0, le=100)
    public_seer_credibility: float = Field(ge=0.0, le=1.0)
    claimed_role: Optional[
        Literal["werewolf", "seer", "witch", "hunter", "guard", "villager", "idiot"]
    ] = None
    sheriff_candidate: bool = False
    withdrew: bool = False
    continued_campaign: bool = False
    known_role: Optional[str] = None
    known_camp: Optional[Literal["good", "werewolf"]] = None

    @model_validator(mode="after")
    def validate_known_role(self) -> "ReasoningPlayerV1":
        if self.known_role is not None and self.known_role not in ROLE_NAMES:
            raise ValueError("known_role is unsupported")
        if self.withdrew and self.continued_campaign:
            raise ValueError("a candidate cannot both withdraw and continue")
        return self


class ReasoningClaimV1(StrictReasoningModel):
    evidence_id: str = Field(min_length=1)
    day: int = Field(ge=1)
    actor_id: int = Field(gt=0)
    claim_type: Literal["role", "seer_check"]
    claimed_role: Optional[
        Literal["werewolf", "seer", "witch", "hunter", "guard", "villager", "idiot"]
    ] = None
    target_id: Optional[int] = Field(default=None, gt=0)
    result: Optional[Literal["good", "werewolf"]] = None
    window_day: Optional[int] = Field(default=None, ge=1)
    observed_event_sequence: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_claim_shape(self) -> "ReasoningClaimV1":
        if self.claim_type == "role":
            if not self.claimed_role:
                raise ValueError("role claim requires claimed_role")
            if self.target_id is not None or self.result is not None:
                raise ValueError("role claim must not include a check result")
        else:
            if self.target_id is None or self.result is None:
                raise ValueError("seer check requires target_id and result")
            if self.claimed_role not in {None, "seer"}:
                raise ValueError("seer check may only carry a seer role claim")
        return self


class ReasoningAssumptionsV1(StrictReasoningModel):
    unique_true_seer: bool = True
    good_fake_seer_must_withdraw: bool = True
    true_seer_persists_against_counterclaim: bool = True
    persistent_seer_set_contains_true_seer: bool = True
    werewolf_count: int = Field(default=4, ge=1, le=8)
    require_counterclaim_for_persistent_seer_constraint: bool = True
    enumerate_possible_worlds: bool = True


class NPCReasoningObservationV1(StrictReasoningModel):
    schema_version: Literal["npc_reasoning_observation.v1"] = (
        NPC_REASONING_OBSERVATION_SCHEMA_VERSION
    )
    policy_version: Literal["actor_scoped_hypotheses.v1"] = (
        NPC_REASONING_POLICY_VERSION
    )
    random_seed_commitment: str = Field(pattern=r"^[0-9a-f]{64}$")
    day: int = Field(ge=1)
    phase: str = Field(min_length=1)
    public_event_sequence: int = Field(ge=0)
    actor_id: int = Field(gt=0)
    actor_role: Literal[
        "werewolf", "seer", "witch", "hunter", "guard", "villager", "idiot"
    ]
    actor_camp: Literal["good", "werewolf"]
    tuning: ReasoningTuningV1
    players: list[ReasoningPlayerV1] = Field(min_length=1)
    claims: list[ReasoningClaimV1] = Field(default_factory=list)
    withdrawal_resolved: bool = False
    sheriff_window_day: Optional[int] = Field(default=None, ge=1)
    sheriff_window_active: bool = False
    assumptions: ReasoningAssumptionsV1 = Field(
        default_factory=ReasoningAssumptionsV1
    )

    @model_validator(mode="after")
    def validate_actor_and_references(self) -> "NPCReasoningObservationV1":
        player_ids = [player.character_id for player in self.players]
        if len(player_ids) != len(set(player_ids)):
            raise ValueError("reasoning player ids must be unique")
        if self.actor_id not in player_ids:
            raise ValueError("reasoning actor is missing from players")
        for claim in self.claims:
            if claim.actor_id not in player_ids:
                raise ValueError("claim actor is outside the observation")
            if claim.target_id is not None and claim.target_id not in player_ids:
                raise ValueError("claim target is outside the observation")
            if claim.day > self.day:
                raise ValueError("claim cannot come from the future")
            if claim.window_day is not None and claim.window_day > claim.day:
                raise ValueError("claim window_day cannot be after claim day")
        if self.sheriff_window_day is not None and self.sheriff_window_day > self.day:
            raise ValueError("sheriff window cannot come from the future")
        if self.sheriff_window_active and self.sheriff_window_day is None:
            raise ValueError("active sheriff window requires sheriff_window_day")
        return self


class NPCReasoningSignalV1(StrictReasoningModel):
    schema_version: Literal["npc_reasoning_signal.v1"] = (
        NPC_REASONING_SIGNAL_SCHEMA_VERSION
    )
    signal_id: str = Field(pattern=r"^reasoning:[a-z_]+:[0-9a-f]{16}$")
    kind: Literal[
        "seer_claim_withdrawn_against_persistent_counterclaim",
        "seer_golded_persistent_counterclaim",
        "seer_check_result_changed",
        "known_role_conflicts_with_seer_claim",
        "sole_consistent_seer_claimant",
    ]
    subject_id: int = Field(gt=0)
    related_actor_id: Optional[int] = Field(default=None, gt=0)
    severity: Literal["information", "soft_conflict", "hard_conflict"]
    hypothesis_status: Literal["supported", "weakened", "inconsistent"]
    reason_code: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)


class SeerHypothesisV1(StrictReasoningModel):
    claimant_id: Optional[int] = Field(default=None, gt=0)
    probability: float = Field(ge=0.0, le=1.0)
    consistent: bool
    reason_codes: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class RoleBeliefV1(StrictReasoningModel):
    target_id: int = Field(gt=0)
    werewolf_probability: float = Field(ge=0.0, le=1.0)
    good_probability: float = Field(ge=0.0, le=1.0)
    seer_probability: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)


class NPCReasoningPlanV1(StrictReasoningModel):
    supported_seer_id: Optional[int] = Field(default=None, gt=0)
    pressure_target_id: Optional[int] = Field(default=None, gt=0)
    provisional_vote_target_id: Optional[int] = Field(default=None, gt=0)


class PossibleWorldV1(StrictReasoningModel):
    """A bounded, actor-scoped possible world.

    Only camp assignments and the identity of a claimed seer are retained.
    Full hidden role permutations never enter the model-facing observation.
    """

    world_id: str = Field(pattern=r"^world:[0-9a-f]{16}$")
    seer_claimant_id: Optional[int] = Field(default=None, gt=0)
    werewolf_ids: list[int] = Field(min_length=1)
    probability: float = Field(ge=0.0, le=1.0)
    satisfied_constraints: list[str] = Field(default_factory=list)
    violated_constraints: list[str] = Field(default_factory=list)


class NPCBeliefStateV1(StrictReasoningModel):
    schema_version: Literal["npc_belief_state.v1"] = (
        NPC_BELIEF_STATE_SCHEMA_VERSION
    )
    policy_version: Literal["actor_scoped_hypotheses.v1"] = (
        NPC_REASONING_POLICY_VERSION
    )
    actor_id: int = Field(gt=0)
    day: int = Field(ge=1)
    phase: str = Field(min_length=1)
    public_event_sequence: int = Field(ge=0)
    observation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    belief_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    role_beliefs: list[RoleBeliefV1]
    seer_hypotheses: list[SeerHypothesisV1]
    reasoning_signals: list[NPCReasoningSignalV1]
    plan: NPCReasoningPlanV1
    possible_worlds: list[PossibleWorldV1] = Field(default_factory=list)
    world_count: int = Field(default=0, ge=0)
    world_entropy: float = Field(default=0.0, ge=0.0)
    unsatisfiable_constraints: bool = False


def canonical_reasoning_digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _signal_id(
    kind: str,
    subject_id: int,
    related_actor_id: Optional[int],
    evidence_ids: list[str],
) -> str:
    digest = canonical_reasoning_digest(
        {
            "kind": kind,
            "subject_id": subject_id,
            "related_actor_id": related_actor_id,
            "evidence_ids": evidence_ids,
        }
    )[:16]
    return f"reasoning:{kind}:{digest}"


def _clamp_probability(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _softmax(scores: dict[Optional[int], float]) -> dict[Optional[int], float]:
    if not scores:
        return {None: 1.0}
    finite_scores = {
        key: score for key, score in scores.items() if math.isfinite(score)
    }
    if not finite_scores:
        return {None: 1.0}
    maximum = max(finite_scores.values())
    weights = {
        key: math.exp(max(-60.0, score - maximum))
        for key, score in finite_scores.items()
    }
    total = sum(weights.values())
    return {key: weight / total for key, weight in weights.items()}


def _enumerate_possible_worlds(
    observation: NPCReasoningObservationV1,
    *,
    claimant_ids: list[int],
    invalid_claimant_ids: set[int],
    persistent_ids: set[int],
    persistent_constraint_active: bool,
    hypothesis_scores: dict[Optional[int], float],
    known_wolf_ids: set[int],
    known_good_ids: set[int],
    player_by_id: dict[int, ReasoningPlayerV1],
) -> tuple[
    list[PossibleWorldV1],
    dict[Optional[int], float],
    dict[int, float],
    int,
    float,
    bool,
]:
    """Enumerate a small camp/seer world space and return marginals.

    Twelve players with four wolves produce at most 495 camp assignments.  A
    handful of public seer claimants multiplies that to a few thousand worlds,
    which is small enough for deterministic offline/runtime reasoning.  The
    complete legal world set is used for marginals; only the persisted display
    list is truncated.  A display cap must never become a hidden hard
    constraint or create seat-order probability bias.
    """

    all_ids = sorted(player_by_id)
    wolf_count = observation.assumptions.werewolf_count
    if len(known_wolf_ids) > wolf_count or known_wolf_ids.intersection(known_good_ids):
        return [], {}, {}, 0, 0.0, True
    unknown_wolf_ids = [
        target_id
        for target_id in all_ids
        if target_id not in known_wolf_ids and target_id not in known_good_ids
    ]
    slots = wolf_count - len(known_wolf_ids)
    if slots < 0 or slots > len(unknown_wolf_ids):
        return [], {}, {}, 0, 0.0, True

    seer_options: list[Optional[int]]
    if observation.actor_role == "seer":
        seer_options = [observation.actor_id]
    else:
        seer_options = [
            claimant_id
            for claimant_id in claimant_ids
            if claimant_id != observation.actor_id
            and claimant_id not in invalid_claimant_ids
        ]
        # ``None`` represents a true seer who has not publicly claimed.
        seer_options.append(None)
    if (
        persistent_constraint_active
        and observation.assumptions.require_counterclaim_for_persistent_seer_constraint
    ):
        seer_options = [
            claimant_id
            for claimant_id in seer_options
            if claimant_id in persistent_ids
        ]
    seer_options = list(dict.fromkeys(seer_options))

    camp_combinations = list(
        itertools.combinations(unknown_wolf_ids, slots)
    )

    raw_worlds: list[tuple[Optional[int], tuple[int, ...], float, list[str]]] = []
    for extra_wolves in camp_combinations:
        wolf_ids = tuple(sorted((*known_wolf_ids, *extra_wolves)))
        for seer_id in seer_options:
            if seer_id is not None and seer_id in wolf_ids:
                continue
            score = hypothesis_scores.get(seer_id, -1.15)
            # Suspicion/trust are soft evidence, never hard permissions.
            for target_id in wolf_ids:
                player = player_by_id[target_id]
                score += (
                    player.suspicion / 100.0 * 0.55
                    + player.public_pressure / 100.0 * 0.16
                    + (0.5 - player.trust) * 0.18
                )
            constraints = ["role_count:wolves"]
            if seer_id is not None and seer_id in persistent_ids:
                constraints.append("persistent_seer_claimant")
            raw_worlds.append((seer_id, wolf_ids, score, constraints))

    if not raw_worlds:
        return [], {}, {}, 0, 0.0, True
    maximum = max(item[2] for item in raw_worlds)
    weights = [
        math.exp(max(-60.0, item[2] - maximum))
        for item in raw_worlds
    ]
    total = sum(weights)
    if not math.isfinite(total) or total <= 0.0:
        return [], {}, {}, 0, 0.0, True
    probabilities = [weight / total for weight in weights]
    seer_marginals: dict[Optional[int], float] = {}
    wolf_marginals: dict[int, float] = {target_id: 0.0 for target_id in all_ids}
    world_rows: list[PossibleWorldV1] = []
    for (seer_id, wolf_ids, _score, constraints), probability in zip(
        raw_worlds,
        probabilities,
    ):
        seer_marginals[seer_id] = seer_marginals.get(seer_id, 0.0) + probability
        for target_id in wolf_ids:
            wolf_marginals[target_id] += probability
        world_digest = canonical_reasoning_digest(
            {
                "seer_claimant_id": seer_id,
                "werewolf_ids": list(wolf_ids),
            }
        )[:16]
        world_rows.append(
            PossibleWorldV1(
                world_id=f"world:{world_digest}",
                seer_claimant_id=seer_id,
                werewolf_ids=list(wolf_ids),
                probability=round(probability, 6),
                satisfied_constraints=constraints,
            )
        )
    entropy = -sum(
        probability * math.log(max(probability, 1e-12))
        for probability in probabilities
    )
    world_rows.sort(key=lambda world: (-world.probability, world.world_id))
    return (
        world_rows[:MAX_PERSISTED_POSSIBLE_WORLDS],
        {
            key: round(value, 6)
            for key, value in seer_marginals.items()
        },
        {
            key: round(value, 6)
            for key, value in wolf_marginals.items()
        },
        len(raw_worlds),
        float(entropy),
        False,
    )


def build_npc_belief_state(
    observation: NPCReasoningObservationV1,
) -> NPCBeliefStateV1:
    """Build one NPC's fallible beliefs from only its lawful observation."""

    observation_payload = observation.model_dump(mode="json")
    observation_digest = canonical_reasoning_digest(observation_payload)
    player_by_id = {
        player.character_id: player for player in observation.players
    }
    # Keep the latest role declaration per actor.  An old "I am seer" claim
    # must not remain active after that actor publicly changes to villager.
    latest_role_claims: dict[int, ReasoningClaimV1] = {}
    for claim in sorted(
        (
            item
            for item in observation.claims
            if item.claim_type == "role" and item.claimed_role is not None
        ),
        key=lambda item: (item.day, item.observed_event_sequence, item.evidence_id),
    ):
        latest_role_claims[claim.actor_id] = claim
    role_claims = {
        actor_id: claim
        for actor_id, claim in latest_role_claims.items()
        if claim.claimed_role == "seer"
    }
    check_claims = [
        claim for claim in observation.claims if claim.claim_type == "seer_check"
    ]
    claimant_ids = sorted(role_claims)
    active_window_day = (
        observation.sheriff_window_day
        if observation.sheriff_window_day is not None
        else None
    )
    window_role_claims: dict[int, ReasoningClaimV1] = {}
    if active_window_day is not None:
        for claim in sorted(
            (
                item
                for item in observation.claims
                if item.claim_type == "role"
                and item.claimed_role is not None
                and item.day == active_window_day
                and item.window_day == active_window_day
            ),
            key=lambda item: (
                item.observed_event_sequence,
                item.evidence_id,
            ),
        ):
            window_role_claims[claim.actor_id] = claim
    window_claimant_ids = set(
        actor_id
        for actor_id, claim in window_role_claims.items()
        if claim.claimed_role == "seer"
    )
    persistent_ids = {
        player.character_id
        for player in observation.players
        if player.character_id in window_claimant_ids
        and player.continued_campaign
        and not player.withdrew
        and active_window_day is not None
    }
    persistent_constraint_active = (
        observation.withdrawal_resolved
        and observation.assumptions.persistent_seer_set_contains_true_seer
        and len(window_claimant_ids) >= 2
        and (
            len(persistent_ids) >= 2
            or (
                len(persistent_ids) >= 1
                and any(
                    player.character_id in window_claimant_ids
                    and player.withdrew
                    for player in observation.players
                )
            )
        )
    )
    signals: list[NPCReasoningSignalV1] = []
    hypothesis_reasons: dict[int, list[str]] = {
        claimant_id: [] for claimant_id in claimant_ids
    }
    hypothesis_evidence: dict[int, list[str]] = {
        claimant_id: [role_claims[claimant_id].evidence_id]
        for claimant_id in claimant_ids
    }

    for claimant_id in claimant_ids:
        claimant = player_by_id[claimant_id]
        competing_persistent_ids = persistent_ids - {claimant_id}
        if (
            persistent_constraint_active
            and claimant.withdrew
            and competing_persistent_ids
            and observation.assumptions.true_seer_persists_against_counterclaim
            and (
                active_window_day is None
                or (
                    claimant_id in window_role_claims
                    and window_role_claims[claimant_id].day
                    == active_window_day
                )
            )
        ):
            reasons = ["true_seer_withdrew_against_persistent_counterclaim"]
            evidence_ids = [role_claims[claimant_id].evidence_id]
            hypothesis_reasons[claimant_id].extend(reasons)
            hypothesis_evidence[claimant_id].extend(evidence_ids)
            kind = "seer_claim_withdrawn_against_persistent_counterclaim"
            signals.append(
                NPCReasoningSignalV1(
                    signal_id=_signal_id(
                        kind,
                        claimant_id,
                        min(competing_persistent_ids),
                        evidence_ids,
                    ),
                    kind=kind,
                    subject_id=claimant_id,
                    related_actor_id=min(competing_persistent_ids),
                    severity="hard_conflict",
                    hypothesis_status="inconsistent",
                    reason_code=reasons[0],
                    evidence_ids=evidence_ids,
                )
            )

        known_role = claimant.known_role
        if known_role is not None and known_role != "seer":
            reason = "actor_lawfully_knows_claimant_is_not_seer"
            evidence_ids = [role_claims[claimant_id].evidence_id]
            hypothesis_reasons[claimant_id].append(reason)
            hypothesis_evidence[claimant_id].extend(evidence_ids)
            kind = "known_role_conflicts_with_seer_claim"
            signals.append(
                NPCReasoningSignalV1(
                    signal_id=_signal_id(
                        kind,
                        claimant_id,
                        observation.actor_id,
                        evidence_ids,
                    ),
                    kind=kind,
                    subject_id=claimant_id,
                    related_actor_id=observation.actor_id,
                    severity="hard_conflict",
                    hypothesis_status="inconsistent",
                    reason_code=reason,
                    evidence_ids=evidence_ids,
                )
            )

    checks_by_actor_target: dict[tuple[int, int], list[ReasoningClaimV1]] = {}
    for claim in check_claims:
        checks_by_actor_target.setdefault(
            (claim.actor_id, int(claim.target_id)),
            [],
        ).append(claim)

    for (claimant_id, target_id), claims in checks_by_actor_target.items():
        results = {claim.result for claim in claims}
        if len(results) > 1 and claimant_id in hypothesis_reasons:
            evidence_ids = [claim.evidence_id for claim in claims]
            reason = "claimant_changed_check_result_for_same_target"
            hypothesis_reasons[claimant_id].append(reason)
            hypothesis_evidence[claimant_id].extend(evidence_ids)
            kind = "seer_check_result_changed"
            signals.append(
                NPCReasoningSignalV1(
                    signal_id=_signal_id(
                        kind,
                        claimant_id,
                        target_id,
                        evidence_ids,
                    ),
                    kind=kind,
                    subject_id=claimant_id,
                    related_actor_id=target_id,
                    severity="hard_conflict",
                    hypothesis_status="inconsistent",
                    reason_code=reason,
                    evidence_ids=evidence_ids,
                )
            )

        window_good_claim = next(
            (
                claim
                for claim in claims
                if claim.result == "good"
                and claim.window_day == active_window_day
            ),
            None,
        )
        if (
            window_good_claim is None
            or claimant_id not in persistent_ids
            or target_id not in window_claimant_ids
            or target_id == claimant_id
            or not persistent_constraint_active
            or not observation.assumptions.good_fake_seer_must_withdraw
            or claimant_id not in hypothesis_reasons
        ):
            continue
        target_role_claim = window_role_claims.get(target_id)
        if (
            target_role_claim is None
            or claimant_id not in window_role_claims
            or target_role_claim.day
            != window_role_claims[claimant_id].day
            or window_good_claim.day
            != window_role_claims[claimant_id].day
            or (
                active_window_day is not None
                and window_role_claims[claimant_id].day != active_window_day
            )
        ):
            continue
        evidence_ids = [
            role_claims[claimant_id].evidence_id,
            target_role_claim.evidence_id,
            window_good_claim.evidence_id,
            f"public:sheriff_continue:{active_window_day}:{claimant_id}",
            f"public:sheriff_continue:{active_window_day}:{target_id}",
        ]
        reason = "gold_target_is_persistent_competing_seer_claimant"
        hypothesis_reasons[claimant_id].append(reason)
        hypothesis_evidence[claimant_id].extend(evidence_ids)
        kind = "seer_golded_persistent_counterclaim"
        signals.append(
            NPCReasoningSignalV1(
                signal_id=_signal_id(
                    kind,
                    claimant_id,
                    target_id,
                    evidence_ids,
                ),
                kind=kind,
                subject_id=claimant_id,
                related_actor_id=target_id,
                severity="hard_conflict",
                hypothesis_status="inconsistent",
                reason_code=reason,
                evidence_ids=evidence_ids,
            )
        )

    if persistent_constraint_active:
        # Every seer declaration made inside the completed window is part of
        # the finite counterclaim set.  A third claimant that did not persist
        # cannot silently remain a "consistent" hypothesis merely because it
        # was appended after the first two were compared.
        for claimant_id in sorted(window_claimant_ids):
            if claimant_id in persistent_ids:
                continue
            if "true_seer_withdrew_against_persistent_counterclaim" in (
                hypothesis_reasons[claimant_id]
            ):
                continue
            reason = "claimant_did_not_persist_in_completed_window"
            hypothesis_reasons[claimant_id].append(reason)
            hypothesis_evidence[claimant_id].append(
                window_role_claims[claimant_id].evidence_id
            )

    hypothesis_scores: dict[Optional[int], float] = {}
    for claimant_id in claimant_ids:
        player = player_by_id[claimant_id]
        if hypothesis_reasons[claimant_id]:
            continue
        credibility = max(0.02, player.public_seer_credibility)
        reasoning_scale = 0.65 + observation.tuning.reasoning_skill * 0.7
        social_noise = (
            observation.tuning.social_susceptibility
            + observation.tuning.deception_susceptibility
        ) * 0.18
        hypothesis_scores[claimant_id] = (
            math.log(credibility) * reasoning_scale
            + player.trust * 0.45
            - player.suspicion / 100.0 * 0.55
            + social_noise
        )

    # A single claimant is never enough to eliminate the unclaimed-true-seer
    # world.  The hard persistence constraint only activates for a completed
    # same-window counterclaim with at least two candidates.
    hidden_consistent = not persistent_constraint_active
    if hidden_consistent:
        hypothesis_scores[None] = -1.15

    if observation.actor_role == "seer":
        hypothesis_scores = {observation.actor_id: 0.0}
        for claimant_id in claimant_ids:
            if claimant_id != observation.actor_id:
                hypothesis_reasons[claimant_id].append(
                    "actor_privately_knows_own_unique_seer_role"
                )
        if observation.actor_id in hypothesis_reasons and hypothesis_reasons[
            observation.actor_id
        ]:
            hypothesis_reasons[observation.actor_id].append(
                "public_conflict_retained_alongside_private_role_fact"
            )
    elif observation.actor_role != "seer" and observation.actor_id in claimant_ids:
        hypothesis_scores.pop(observation.actor_id, None)
        hypothesis_reasons[observation.actor_id].append(
            "actor_privately_knows_self_is_not_seer"
        )

    probabilities = _softmax(hypothesis_scores)
    hypotheses = [
        SeerHypothesisV1(
            claimant_id=claimant_id,
            probability=round(probabilities.get(claimant_id, 0.0), 6),
            consistent=claimant_id in hypothesis_scores,
            reason_codes=list(dict.fromkeys(hypothesis_reasons[claimant_id])),
            evidence_ids=list(dict.fromkeys(hypothesis_evidence[claimant_id])),
        )
        for claimant_id in claimant_ids
    ]
    if hidden_consistent or None in probabilities:
        hypotheses.append(
            SeerHypothesisV1(
                claimant_id=None,
                probability=round(probabilities.get(None, 0.0), 6),
                consistent=hidden_consistent,
                reason_codes=[] if hidden_consistent else [
                    "persistent_claimant_set_must_contain_true_seer"
                ],
                evidence_ids=[],
            )
        )

    sole_candidate_ids = (
        window_claimant_ids if persistent_constraint_active else set(claimant_ids)
    )
    consistent_claimants = [
        hypothesis.claimant_id
        for hypothesis in hypotheses
        if hypothesis.claimant_id is not None
        and hypothesis.claimant_id in sole_candidate_ids
        and hypothesis.consistent
    ]
    sole_consistent_id = (
        consistent_claimants[0]
        if len(consistent_claimants) == 1
        and persistent_constraint_active
        else None
    )
    if sole_consistent_id is not None:
        evidence_ids = list(
            dict.fromkeys(
                evidence_id
                for signal in signals
                if signal.hypothesis_status == "inconsistent"
                for evidence_id in signal.evidence_ids
            )
        )
        kind = "sole_consistent_seer_claimant"
        signals.append(
            NPCReasoningSignalV1(
                signal_id=_signal_id(
                    kind,
                    sole_consistent_id,
                    None,
                    evidence_ids,
                ),
                kind=kind,
                subject_id=sole_consistent_id,
                severity="information",
                hypothesis_status="supported",
                reason_code="all_competing_seer_hypotheses_inconsistent",
                evidence_ids=evidence_ids,
            )
        )

    invalid_claimant_ids = {
        hypothesis.claimant_id
        for hypothesis in hypotheses
        if hypothesis.claimant_id is not None and not hypothesis.consistent
    }
    known_wolf_ids = {
        player.character_id
        for player in observation.players
        if player.known_camp == "werewolf"
    }
    known_good_ids = {
        player.character_id
        for player in observation.players
        if player.known_camp == "good"
    }
    if observation.assumptions.enumerate_possible_worlds:
        (
            possible_worlds,
            world_seer_marginals,
            world_wolf_marginals,
            world_count,
            world_entropy,
            unsatisfiable_constraints,
        ) = _enumerate_possible_worlds(
            observation,
            claimant_ids=claimant_ids,
            invalid_claimant_ids=invalid_claimant_ids,
            persistent_ids=persistent_ids,
            persistent_constraint_active=persistent_constraint_active,
            hypothesis_scores=hypothesis_scores,
            known_wolf_ids=known_wolf_ids,
            known_good_ids=known_good_ids,
            player_by_id=player_by_id,
        )
    else:
        possible_worlds = []
        world_seer_marginals = {}
        world_wolf_marginals = {}
        world_count = 0
        world_entropy = 0.0
        unsatisfiable_constraints = False
    if not unsatisfiable_constraints and world_seer_marginals:
        # Replace heuristic claimant probabilities with marginals from the
        # bounded world set.  The reasons/constraints remain attached to each
        # hypothesis for explanations.
        for hypothesis in hypotheses:
            hypothesis.probability = round(
                world_seer_marginals.get(hypothesis.claimant_id, 0.0),
                6,
            )
        if None in world_seer_marginals and not any(
            hypothesis.claimant_id is None for hypothesis in hypotheses
        ):
            hypotheses.append(
                SeerHypothesisV1(
                    claimant_id=None,
                    probability=round(world_seer_marginals[None], 6),
                    consistent=hidden_consistent,
                    reason_codes=[] if hidden_consistent else [
                        "persistent_claimant_set_must_contain_true_seer"
                    ],
                    evidence_ids=[],
                )
            )
    raw_wolf_probabilities: dict[int, float] = {}
    for player in observation.players:
        if player.character_id in known_wolf_ids:
            raw = 1.0
        elif player.character_id in known_good_ids:
            raw = 0.0
        elif not unsatisfiable_constraints and player.character_id in world_wolf_marginals:
            raw = world_wolf_marginals[player.character_id]
        else:
            raw = (
                0.18
                + player.suspicion / 100.0 * 0.52
                + player.public_pressure / 100.0 * 0.18
                + (0.5 - player.trust) * 0.18
            )
            if player.character_id in invalid_claimant_ids:
                raw += 0.25
            if player.character_id == sole_consistent_id:
                raw -= 0.35
        raw_wolf_probabilities[player.character_id] = _clamp_probability(raw)

    unknown_ids = [
        player.character_id
        for player in observation.players
        if player.character_id not in known_wolf_ids
        and player.character_id not in known_good_ids
    ]
    expected_unknown_wolves = max(
        0.0,
        float(observation.assumptions.werewolf_count - len(known_wolf_ids)),
    )
    unknown_total = sum(raw_wolf_probabilities[target_id] for target_id in unknown_ids)
    if unsatisfiable_constraints and unknown_ids and unknown_total > 0.0:
        scale = expected_unknown_wolves / unknown_total
        for target_id in unknown_ids:
            raw_wolf_probabilities[target_id] = _clamp_probability(
                raw_wolf_probabilities[target_id] * scale
            )

    seer_probability_by_id = {
        int(hypothesis.claimant_id): hypothesis.probability
        for hypothesis in hypotheses
        if hypothesis.claimant_id is not None
    }
    role_beliefs = []
    for player in observation.players:
        wolf_probability = raw_wolf_probabilities[player.character_id]
        if player.known_role == "seer":
            seer_probability = 1.0
        elif player.known_role is not None:
            seer_probability = 0.0
        else:
            seer_probability = seer_probability_by_id.get(
                player.character_id,
                0.0,
            )
        evidence_strength = max(
            wolf_probability,
            1.0 - wolf_probability,
            seer_probability,
        )
        confidence = (
            0.35
            + observation.tuning.reasoning_skill * 0.35
            + (evidence_strength - 0.5) * 0.45
        )
        role_beliefs.append(
            RoleBeliefV1(
                target_id=player.character_id,
                werewolf_probability=round(wolf_probability, 6),
                good_probability=round(1.0 - wolf_probability, 6),
                seer_probability=round(_clamp_probability(seer_probability), 6),
                confidence=round(_clamp_probability(confidence), 6),
            )
        )

    supported_seer_id = max(
        (
            belief.target_id
            for belief in role_beliefs
            if belief.seer_probability > 0.0
        ),
        key=lambda target_id: (
            seer_probability_by_id.get(target_id, 0.0),
            -target_id,
        ),
        default=None,
    )
    pressure_candidates = [
        belief
        for belief in role_beliefs
        if belief.target_id != observation.actor_id
        and player_by_id[belief.target_id].alive
    ]
    pressure_target_id = max(
        pressure_candidates,
        key=lambda belief: (
            belief.werewolf_probability,
            player_by_id[belief.target_id].suspicion,
            -belief.target_id,
        ),
        default=None,
    )
    plan = NPCReasoningPlanV1(
        supported_seer_id=supported_seer_id,
        pressure_target_id=(
            pressure_target_id.target_id
            if pressure_target_id is not None
            else None
        ),
        provisional_vote_target_id=(
            pressure_target_id.target_id
            if pressure_target_id is not None
            else None
        ),
    )

    state_payload = {
        "schema_version": NPC_BELIEF_STATE_SCHEMA_VERSION,
        "policy_version": NPC_REASONING_POLICY_VERSION,
        "actor_id": observation.actor_id,
        "day": observation.day,
        "phase": observation.phase,
        "public_event_sequence": observation.public_event_sequence,
        "observation_digest": observation_digest,
        "role_beliefs": [
            belief.model_dump(mode="json") for belief in role_beliefs
        ],
        "seer_hypotheses": [
            hypothesis.model_dump(mode="json") for hypothesis in hypotheses
        ],
        "reasoning_signals": [
            signal.model_dump(mode="json") for signal in signals
        ],
        "plan": plan.model_dump(mode="json"),
        "possible_worlds": [
            world.model_dump(mode="json") for world in possible_worlds
        ],
        "world_count": world_count,
        "world_entropy": round(world_entropy, 6),
        "unsatisfiable_constraints": unsatisfiable_constraints,
    }
    belief_digest = canonical_reasoning_digest(state_payload)
    return NPCBeliefStateV1(
        **state_payload,
        belief_digest=belief_digest,
    )


def get_role_belief(
    state: NPCBeliefStateV1,
    target_id: int,
) -> RoleBeliefV1:
    for belief in state.role_beliefs:
        if belief.target_id == target_id:
            return belief
    raise LookupError(f"reasoning state has no target {target_id}")


__all__ = [
    "NPC_BELIEF_STATE_SCHEMA_VERSION",
    "NPC_REASONING_OBSERVATION_SCHEMA_VERSION",
    "NPC_REASONING_POLICY_VERSION",
    "NPC_REASONING_SIGNAL_SCHEMA_VERSION",
    "NPCBeliefStateV1",
    "NPCReasoningObservationV1",
    "NPCReasoningPlanV1",
    "NPCReasoningSignalV1",
    "PossibleWorldV1",
    "ROLE_NAMES",
    "ReasoningAssumptionsV1",
    "ReasoningClaimV1",
    "ReasoningPlayerV1",
    "ReasoningTuningV1",
    "RoleBeliefV1",
    "SeerHypothesisV1",
    "build_npc_belief_state",
    "canonical_reasoning_digest",
    "get_role_belief",
]
