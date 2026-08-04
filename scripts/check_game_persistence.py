#!/usr/bin/env python3
"""Exercise V4.3 persistence and command idempotency without services."""

from __future__ import annotations

import asyncio
import copy
import json
import os
import stat
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))


def expect_http_error(
    call: Callable[[], object],
    *,
    status_code: int,
    label: str,
    http_exception_type: type[Exception],
) -> Exception:
    try:
        call()
    except http_exception_type as exc:
        if getattr(exc, "status_code", None) != status_code:
            raise AssertionError(
                f"{label} returned {getattr(exc, 'status_code', None)}, "
                f"expected {status_code}"
            ) from exc
        return exc
    raise AssertionError(f"{label} should have returned HTTP {status_code}")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    os.environ["AGENT_TOWN_DISABLE_VECTOR_RAG"] = "1"

    with TemporaryDirectory(prefix="agent-town-v4-persistence-") as temp_dir:
        temp_root = Path(temp_dir)
        initial_save_root = temp_root / "initial-games"
        os.environ["AGENT_TOWN_GAME_SAVE_DIR"] = str(initial_save_root)

        from app import game_persistence as persistence
        from app import main as rules
        from app.event_log import (
            GAME_RULESET_VERSION,
            append_game_rule_event,
            begin_game_command,
            canonical_payload_digest,
            normalized_rule_state_payload,
            rule_state_digest,
        )
        from app import simulation as simulation_rules
        from app.simulation import run_rule_simulation

        if (
            persistence.GAME_SAVE_SCHEMA_VERSION != "game_save.v1"
            or persistence.GAME_SAVE_RESPONSE_SCHEMA_VERSION
            != "game_save_response.v1"
            or persistence.GAME_RESTORE_SCHEMA_VERSION != "game_restore.v1"
            or persistence.GAME_RECOVERY_SCHEMA_VERSION != "game_recovery.v1"
            or persistence.RECOVERY_CONFIG_FINGERPRINT_VERSION
            != "recovery_config_fingerprint.v1"
        ):
            raise AssertionError("V4.3-A persistence schemas must stay explicit")
        if (
            rules.GAME_COMMAND_IDEMPOTENCY_VERSION
            != "game_command_idempotency.v1"
            or rules.GAME_COMMAND_RESULT_SCHEMA_VERSION
            != "game_command_result.v1"
        ):
            raise AssertionError("V4.3-B idempotency schemas must stay explicit")
        if rules.GAME_PERSISTENCE_ACTIVE:
            raise AssertionError("direct app import must leave persistence disabled")
        if initial_save_root.exists():
            raise AssertionError("direct app import must not create the save directory")

        async def check_lifespan_switch() -> None:
            async with rules.app_lifespan(rules.app):
                if not rules.GAME_PERSISTENCE_ACTIVE:
                    raise AssertionError("FastAPI lifespan must activate persistence")

        asyncio.run(check_lifespan_switch())
        if rules.GAME_PERSISTENCE_ACTIVE:
            raise AssertionError("FastAPI lifespan shutdown must disable persistence")

        rules.GAME_STORE.clear()
        rules.PERSISTED_GAME_IDS.clear()
        recovery = rules.activate_game_persistence()
        if recovery.failure_count or recovery.scanned_count:
            raise AssertionError("an empty save directory must recover cleanly")

        original_replace = persistence.os.replace

        def fail_initial_replace(_source: object, _target: object) -> None:
            raise OSError("injected creation replace failure")

        persistence.os.replace = fail_initial_replace
        try:
            expect_http_error(
                lambda: rules.start_wolf_game(
                    rules.GameStartRequest(player_role="villager")
                ),
                status_code=503,
                label="game creation with an unavailable save target",
                http_exception_type=rules.HTTPException,
            )
        finally:
            persistence.os.replace = original_replace
        if rules.GAME_STORE or list(initial_save_root.glob("*.json")):
            raise AssertionError("a failed creation save must not publish the game")
        if list(initial_save_root.glob(".*.tmp")):
            raise AssertionError("a failed creation save left a temporary file")

        started = rules.start_wolf_game(
            rules.GameStartRequest(
                player_name="持久化测试玩家",
                player_role="villager",
                enable_llm=False,
                enable_rag=False,
            )
        )
        game_id = started.game_id
        save_path = initial_save_root / f"{game_id}.json"
        if not save_path.is_file():
            raise AssertionError("a real-lifespan game must be saved at creation")
        if stat.S_IMODE(initial_save_root.stat().st_mode) != 0o700:
            raise AssertionError("the private save directory must use mode 0700")
        if stat.S_IMODE(save_path.stat().st_mode) != 0o600:
            raise AssertionError("a private game save must use mode 0600")
        if list(initial_save_root.glob(".*.tmp")):
            raise AssertionError("a successful atomic save left a temporary file")

        state = rules.GAME_STORE[game_id]
        envelope = rules.GAME_SAVE_STORE.load(game_id)
        state_payload = state.model_dump(mode="json")
        if (
            envelope.schema_version != persistence.GAME_SAVE_SCHEMA_VERSION
            or envelope.ruleset_version != GAME_RULESET_VERSION
            or envelope.saved_event_sequence != 1
            or envelope.saved_event_digest != state.rule_events[-1].event_digest
            or envelope.state_digest != rule_state_digest(state)
            or envelope.snapshot_digest != canonical_payload_digest(state_payload)
            or envelope.config_fingerprint
            != state.recovery_config_fingerprint
            or state.rule_events[0].command.get("recovery_config_fingerprint")
            != state.recovery_config_fingerprint
        ):
            raise AssertionError("the creation save is not fully sealed")
        if envelope.state["characters"][0]["role"] != "villager":
            raise AssertionError("the private save must contain the complete rule state")

        creation_bytes = save_path.read_bytes()
        rules.submit_night_action(
            rules.NightActionRequest(
                game_id=game_id,
                character_id=1,
                action_type="none",
            )
        )
        if save_path.read_bytes() == creation_bytes:
            raise AssertionError("a successful rule command must advance the save")
        if rules.GAME_SAVE_STORE.load(game_id).saved_event_sequence != 2:
            raise AssertionError("the saved event sequence did not advance")

        expect_http_error(
            rules.reload_config,
            status_code=409,
            label="config reload with an unfinished persisted game",
            http_exception_type=rules.HTTPException,
        )

        state_before_failure = rules.GAME_STORE[game_id].model_dump(mode="json")
        disk_before_failure = save_path.read_bytes()
        original_replace = persistence.os.replace

        def fail_replace(_source: object, _target: object) -> None:
            raise OSError("injected atomic replace failure")

        persistence.os.replace = fail_replace
        try:
            expect_http_error(
                lambda: rules.submit_night_action(
                    rules.NightActionRequest(
                        game_id=game_id,
                        character_id=1,
                        action_type="none",
                    )
                ),
                status_code=503,
                label="rule command with an unavailable save target",
                http_exception_type=rules.HTTPException,
            )
        finally:
            persistence.os.replace = original_replace

        if (
            rules.GAME_STORE[game_id].model_dump(mode="json")
            != state_before_failure
        ):
            raise AssertionError("a failed atomic write must roll memory back exactly")
        if save_path.read_bytes() != disk_before_failure:
            raise AssertionError("a failed atomic write must preserve the old save")
        if list(initial_save_root.glob(".*.tmp")):
            raise AssertionError("a failed atomic write left a temporary file")

        rules.submit_night_action(
            rules.NightActionRequest(
                game_id=game_id,
                character_id=1,
                action_type="none",
            )
        )
        if rules.GAME_SAVE_STORE.load(game_id).saved_event_sequence != 3:
            raise AssertionError("the rolled-back command must be retryable")

        expected_after_restart = rules.GAME_STORE[game_id].model_dump(mode="json")
        rules.deactivate_game_persistence()
        rules.GAME_STORE.clear()
        rules.PERSISTED_GAME_IDS.clear()
        recovery = rules.activate_game_persistence()
        if recovery.restored_game_ids != [game_id] or recovery.failure_count:
            raise AssertionError("startup recovery did not restore the unfinished game")
        if rules.GAME_STORE[game_id].model_dump(mode="json") != expected_after_restart:
            raise AssertionError("startup recovery must restore the exact snapshot")

        rules.submit_night_action(
            rules.NightActionRequest(
                game_id=game_id,
                character_id=1,
                action_type="none",
            )
        )
        restored_again = rules.restore_saved_game(game_id)
        if restored_again.restored or not restored_again.already_cached:
            raise AssertionError("repeated restore must report the cached exact snapshot")

        exact_cached_payload = rules.GAME_STORE[game_id].model_dump(mode="json")
        rules.GAME_STORE[game_id].updated_at = "conflicting-wall-clock"
        expect_http_error(
            lambda: rules.restore_saved_game(game_id),
            status_code=409,
            label="restore over a divergent cache entry",
            http_exception_type=rules.HTTPException,
        )
        rules.GAME_STORE[game_id] = rules.WolfGameState.model_validate(
            exact_cached_payload
        )

        disk_only_state = rules.create_wolf_game_state(
            rules.GameStartRequest(player_role="villager"),
            game_id="game_002",
            random_seed=20260721,
        )
        rules.persist_game_state(disk_only_state)
        memory_only_state = rules.create_wolf_game_state(
            rules.GameStartRequest(player_role="villager"),
            game_id="game_003",
            random_seed=20260722,
        )
        rules.GAME_STORE[memory_only_state.game_id] = memory_only_state
        if rules.build_game_id() != "game_004":
            raise AssertionError("game IDs must avoid both disk and memory collisions")
        rules.GAME_STORE.pop(memory_only_state.game_id, None)

        files_before_simulation = {
            path.name: path.read_bytes()
            for path in initial_save_root.glob("*.json")
        }
        simulation = run_rule_simulation(
            20260719,
            capture_beliefs=False,
            capture_stances=False,
            capture_vote_calibration=False,
            capture_event_log=True,
        )
        files_after_simulation = {
            path.name: path.read_bytes()
            for path in initial_save_root.glob("*.json")
        }
        if (
            not simulation["replay"]["verified"]
            or files_after_simulation != files_before_simulation
            or any(
                game_id.startswith(("simulation_", "replay_"))
                for game_id in rules.PERSISTED_GAME_IDS
            )
        ):
            raise AssertionError("simulation and isolated replay must remain disk-free")

        openapi = rules.app.openapi()
        required_paths = {
            "/api/game/{game_id}/save",
            "/api/game/{game_id}/restore",
            "/api/game/recovery-status",
        }
        if not required_paths.issubset(openapi["paths"]):
            raise AssertionError("the V4.3-A persistence endpoints are missing")
        schema_names = set(openapi["components"]["schemas"])
        if not {
            "GameSaveResponseV1",
            "GameRestoreResponseV1",
            "GameRecoveryReportV1",
            "GameRecoveryFailureV1",
        }.issubset(schema_names):
            raise AssertionError("the V4.3-A API schemas are missing from OpenAPI")
        idempotent_request_schemas = {
            "NightActionRequest",
            "NightResolveRequest",
            "HunterShotRequest",
            "PlayerSpeechRequest",
            "SheriffSignupRequest",
            "SheriffSpeechRequest",
            "SheriffWithdrawalRequest",
            "SheriffVoteRequest",
            "SheriffMeetingOrderRequest",
            "SheriffNominationRequest",
            "BadgeTransferRequest",
            "NpcSpeechesRequest",
            "NpcSpeechRequest",
            "EndFreeActivityRequest",
            "PrivateChatRequest",
            "NpcVoteDecisionsRequest",
            "PlayerVoteRequest",
            "VoteResolveRequest",
        }
        for schema_name in idempotent_request_schemas:
            properties = openapi["components"]["schemas"][schema_name].get(
                "properties", {}
            )
            if "idempotency_key" not in properties:
                raise AssertionError(
                    f"{schema_name} is missing the optional idempotency key"
                )
        if "idempotency_key" in openapi["components"]["schemas"][
            "GameStartRequest"
        ].get("properties", {}):
            raise AssertionError("game creation is outside the V4.3-B key scope")
        if "idempotency_key" in openapi["components"]["schemas"][
            "PlayerSpeechPreviewRequest"
        ].get("properties", {}):
            raise AssertionError("speech preview must remain read-only and unkeyed")
        expected_idempotent_endpoints = {
            "submit_night_action",
            "resolve_night",
            "resolve_hunter_shot",
            "submit_sheriff_signup",
            "submit_player_sheriff_speech",
            "generate_npc_sheriff_campaign_speech",
            "submit_sheriff_withdrawal",
            "submit_and_resolve_sheriff_vote",
            "submit_sheriff_meeting_order",
            "submit_sheriff_nomination",
            "submit_badge_transfer",
            "submit_player_speech",
            "generate_npc_speech",
            "generate_npc_speeches",
            "end_free_activity",
            "private_chat",
            "generate_npc_vote_decisions",
            "submit_player_vote",
            "resolve_vote",
            "submit_and_resolve_all_votes",
        }
        if (
            set(rules.IDEMPOTENT_ENDPOINT_RESPONSE_MODELS)
            != expected_idempotent_endpoints
        ):
            raise AssertionError("V4.3-B must guard the exact 20 commands")

        rules.deactivate_game_persistence()
        rules.GAME_STORE.clear()
        rules.PERSISTED_GAME_IDS.clear()

        idempotency_store = persistence.GameSaveStore(
            temp_root / "idempotency"
        )
        rules.GAME_SAVE_STORE = idempotency_store
        idempotency_recovery = rules.activate_game_persistence()
        if idempotency_recovery.scanned_count or idempotency_recovery.failure_count:
            raise AssertionError("the idempotency fixture store must start empty")

        for invalid_key in ("short", "key with spaces"):
            try:
                rules.NightActionRequest(
                    game_id="validation_only",
                    character_id=1,
                    action_type="none",
                    idempotency_key=invalid_key,
                )
            except rules.ValidationError:
                pass
            else:
                raise AssertionError("invalid idempotency keys must be rejected")

        idempotency_started = rules.start_wolf_game(
            rules.GameStartRequest(
                player_name="幂等测试玩家",
                player_role="villager",
                enable_llm=False,
                enable_rag=False,
            )
        )
        idempotency_game_id = idempotency_started.game_id
        idempotency_creation_projection = normalized_rule_state_payload(
            rules.GAME_STORE[idempotency_game_id]
        )
        idempotency_save_path = idempotency_store.save_path(
            idempotency_game_id
        )
        first_key = "night-action-key-0001"
        first_request = rules.NightActionRequest(
            game_id=idempotency_game_id,
            character_id=idempotency_started.player_character_id,
            action_type="none",
            idempotency_key=first_key,
        )
        first_response = rules.submit_night_action(first_request)
        first_state = rules.GAME_STORE[idempotency_game_id]
        first_state_payload = first_state.model_dump(mode="json")
        first_disk_payload = idempotency_save_path.read_bytes()
        first_event_count = len(first_state.rule_events)
        first_result = first_state.command_results.get(first_key)
        if (
            first_result is None
            or first_result.schema_version != "game_command_result.v1"
            or first_result.idempotency_contract_version
            != "game_command_idempotency.v1"
            or first_result.endpoint != "submit_night_action"
            or first_result.event_sequence != first_event_count
            or first_state.rule_events[-1].command.get("idempotency_key")
            != first_key
            or first_result.request_digest
            != rules.build_idempotency_request_digest(first_request)
            or first_result.response_digest
            != canonical_payload_digest(first_response.model_dump(mode="json"))
        ):
            raise AssertionError("the first keyed command was not fully sealed")

        duplicate_response = rules.submit_night_action(first_request)
        if duplicate_response.model_dump(mode="json") != first_response.model_dump(
            mode="json"
        ):
            raise AssertionError("an exact duplicate must return the first response")
        if (
            rules.GAME_STORE[idempotency_game_id].model_dump(mode="json")
            != first_state_payload
            or idempotency_save_path.read_bytes() != first_disk_payload
        ):
            raise AssertionError("an exact duplicate must not mutate or rewrite")

        expect_http_error(
            lambda: rules.submit_night_action(
                rules.NightActionRequest(
                    game_id=idempotency_game_id,
                    character_id=idempotency_started.player_character_id,
                    action_type="none",
                    target_id=2,
                    idempotency_key=first_key,
                )
            ),
            status_code=409,
            label="same key with a different payload",
            http_exception_type=rules.HTTPException,
        )
        expect_http_error(
            lambda: rules.resolve_night(
                rules.NightResolveRequest(
                    game_id=idempotency_game_id,
                    idempotency_key=first_key,
                )
            ),
            status_code=409,
            label="same key on a different endpoint",
            http_exception_type=rules.HTTPException,
        )
        if (
            rules.GAME_STORE[idempotency_game_id].model_dump(mode="json")
            != first_state_payload
            or idempotency_save_path.read_bytes() != first_disk_payload
        ):
            raise AssertionError("idempotency conflicts must be mutation-free")

        concurrent_key = "concurrent-key-0001"
        concurrent_event_count = len(
            rules.GAME_STORE[idempotency_game_id].rule_events
        )

        def submit_concurrent_duplicate() -> dict[str, object]:
            response = rules.submit_night_action(
                rules.NightActionRequest(
                    game_id=idempotency_game_id,
                    character_id=idempotency_started.player_character_id,
                    action_type="none",
                    idempotency_key=concurrent_key,
                )
            )
            return response.model_dump(mode="json")

        with ThreadPoolExecutor(max_workers=2) as executor:
            concurrent_responses = list(
                executor.map(lambda _index: submit_concurrent_duplicate(), range(2))
            )
        concurrent_state = rules.GAME_STORE[idempotency_game_id]
        if (
            concurrent_responses[0] != concurrent_responses[1]
            or len(concurrent_state.rule_events) != concurrent_event_count + 1
            or concurrent_key not in concurrent_state.command_results
        ):
            raise AssertionError("concurrent duplicates must commit exactly once")

        failed_key = "atomic-failure-key-0001"
        failed_request = rules.NightActionRequest(
            game_id=idempotency_game_id,
            character_id=idempotency_started.player_character_id,
            action_type="none",
            idempotency_key=failed_key,
        )
        before_keyed_failure = rules.GAME_STORE[
            idempotency_game_id
        ].model_dump(mode="json")
        before_keyed_failure_disk = idempotency_save_path.read_bytes()
        original_replace = persistence.os.replace
        persistence.os.replace = fail_replace
        try:
            expect_http_error(
                lambda: rules.submit_night_action(failed_request),
                status_code=503,
                label="keyed command with an unavailable save target",
                http_exception_type=rules.HTTPException,
            )
        finally:
            persistence.os.replace = original_replace
        failed_state = rules.GAME_STORE[idempotency_game_id]
        if (
            failed_state.model_dump(mode="json") != before_keyed_failure
            or failed_key in failed_state.command_results
            or idempotency_save_path.read_bytes() != before_keyed_failure_disk
            or list(idempotency_store.root_dir.glob(".*.tmp"))
        ):
            raise AssertionError(
                "a failed keyed commit must roll back state, result, and disk"
            )
        rules.submit_night_action(failed_request)
        if failed_key not in rules.GAME_STORE[idempotency_game_id].command_results:
            raise AssertionError("a rolled-back keyed command must be retryable")

        legacy_result_count = len(
            rules.GAME_STORE[idempotency_game_id].command_results
        )
        legacy_event_count = len(rules.GAME_STORE[idempotency_game_id].rule_events)
        rules.submit_night_action(
            rules.NightActionRequest(
                game_id=idempotency_game_id,
                character_id=idempotency_started.player_character_id,
                action_type="none",
            )
        )
        legacy_state = rules.GAME_STORE[idempotency_game_id]
        if (
            len(legacy_state.rule_events) != legacy_event_count + 1
            or len(legacy_state.command_results) != legacy_result_count
            or "idempotency_key" in legacy_state.rule_events[-1].command
        ):
            raise AssertionError("unkeyed V4.2 clients must remain compatible")

        resolve_key = "night-resolve-key-0001"
        resolve_request = rules.NightResolveRequest(
            game_id=idempotency_game_id,
            idempotency_key=resolve_key,
        )
        lost_response = rules.resolve_night(resolve_request)
        lost_response_payload = lost_response.model_dump(mode="json")
        state_after_lost_response = rules.GAME_STORE[idempotency_game_id]
        if (
            state_after_lost_response.phase == "NIGHT"
            or resolve_key not in state_after_lost_response.command_results
        ):
            raise AssertionError("the response-loss fixture did not advance phase")

        rules.deactivate_game_persistence()
        rules.GAME_STORE.clear()
        rules.PERSISTED_GAME_IDS.clear()
        restart_recovery = rules.activate_game_persistence()
        if (
            restart_recovery.restored_game_ids != [idempotency_game_id]
            or restart_recovery.failure_count
        ):
            raise AssertionError("the keyed response ledger did not recover")
        recovered_state = rules.GAME_STORE[idempotency_game_id]
        recovered_event_count = len(recovered_state.rule_events)
        recovered_disk_payload = idempotency_save_path.read_bytes()
        recovered_response = rules.resolve_night(resolve_request)
        if recovered_response.model_dump(mode="json") != lost_response_payload:
            raise AssertionError(
                "a retry after response loss must return the committed response"
            )
        if (
            len(rules.GAME_STORE[idempotency_game_id].rule_events)
            != recovered_event_count
            or idempotency_save_path.read_bytes() != recovered_disk_payload
        ):
            raise AssertionError(
                "a recovered duplicate must bypass phase checks without rewriting"
            )

        keyed_events = [
            rules.GameRuleEventV1.model_validate(event.model_dump(mode="json"))
            for event in recovered_state.rule_events
        ]
        replay_start_command = keyed_events[0].command
        recreated_initial_state = rules.create_wolf_game_state(
            rules.GameStartRequest.model_validate(
                replay_start_command["start_request"]
            ),
            game_id="idempotency_replay_probe",
            random_seed=replay_start_command["random_seed"],
        )
        recreated_projection = normalized_rule_state_payload(
            recreated_initial_state
        )
        if recreated_projection != idempotency_creation_projection:
            differing_keys = sorted(
                key
                for key in idempotency_creation_projection
                if idempotency_creation_projection[key]
                != recreated_projection.get(key)
            )
            raise AssertionError(
                "keyed creation replay probe drifted in: "
                + ", ".join(differing_keys)
                + f"; original_seed={idempotency_creation_projection['random_seed']}"
                + f"; event_seed={replay_start_command['random_seed']}"
                + "; original_roles="
                + str(
                    [
                        item["role"]
                        for item in idempotency_creation_projection["characters"]
                    ]
                )
                + "; replay_roles="
                + str([item["role"] for item in recreated_projection["characters"]])
            )
        files_before_keyed_replay = {
            path.name: path.read_bytes()
            for path in idempotency_store.root_dir.glob("*.json")
        }
        keyed_replay = rules.replay_game_rule_events(
            game_id=idempotency_game_id,
            events=keyed_events,
            expected_projection=rules.build_rule_replay_projection(
                recovered_state
            ),
        )
        files_after_keyed_replay = {
            path.name: path.read_bytes()
            for path in idempotency_store.root_dir.glob("*.json")
        }
        if (
            not keyed_replay.verified
            or keyed_replay.checked_event_count != len(keyed_events)
            or files_after_keyed_replay != files_before_keyed_replay
            or any(
                game_id.startswith("replay_")
                for game_id in rules.PERSISTED_GAME_IDS
            )
        ):
            raise AssertionError(
                "keyed events must remain deterministic and replay disk-free: "
                f"{keyed_replay.model_dump(mode='json')}"
            )

        keyed_envelope_payload = idempotency_store.load(
            idempotency_game_id
        ).model_dump(mode="json")
        rules.deactivate_game_persistence()
        rules.GAME_STORE.clear()
        rules.PERSISTED_GAME_IDS.clear()

        terminal_idempotency_store = persistence.GameSaveStore(
            temp_root / "terminal-idempotency"
        )
        rules.GAME_SAVE_STORE = terminal_idempotency_store
        rules.activate_game_persistence()
        terminal_state = rules.create_wolf_game_state(
            rules.GameStartRequest(
                player_name="终局幂等测试玩家",
                player_role="villager",
                enable_llm=False,
                enable_rag=False,
            ),
            game_id="terminal_idempotency",
            random_seed=20260719,
        )
        rules.persist_game_state(terminal_state)
        rules.GAME_STORE[terminal_state.game_id] = terminal_state
        rules.PERSISTED_GAME_IDS.add(terminal_state.game_id)

        simulation_handler_names = (
            "submit_night_action",
            "resolve_night",
            "resolve_hunter_shot",
            "submit_sheriff_signup",
            "submit_player_sheriff_speech",
            "generate_npc_sheriff_campaign_speech",
            "submit_sheriff_withdrawal",
            "submit_and_resolve_sheriff_vote",
            "submit_sheriff_meeting_order",
            "submit_sheriff_nomination",
            "submit_badge_transfer",
            "submit_player_speech",
            "generate_npc_speech",
            "end_free_activity",
            "private_chat",
            "submit_and_resolve_all_votes",
        )
        original_simulation_handlers = {
            name: getattr(rules, name) for name in simulation_handler_names
        }
        keyed_command_count = 0
        last_terminal_call: dict[str, object] = {}

        def build_keying_wrapper(
            handler_name: str,
            handler: Callable[[object], object],
        ) -> Callable[[object], object]:
            def call_with_key(request: object) -> object:
                nonlocal keyed_command_count
                keyed_command_count += 1
                request_payload = request.model_dump(mode="json")
                request_payload["idempotency_key"] = (
                    f"terminal:{keyed_command_count:04d}:{handler_name}"
                )
                keyed_request = request.__class__.model_validate(
                    request_payload
                )
                response = handler(keyed_request)
                last_terminal_call.clear()
                last_terminal_call.update(
                    {
                        "handler_name": handler_name,
                        "request": keyed_request,
                        "response_payload": response.model_dump(mode="json"),
                    }
                )
                return response

            return call_with_key

        for handler_name, original_handler in original_simulation_handlers.items():
            setattr(
                rules,
                handler_name,
                build_keying_wrapper(handler_name, original_handler),
            )
        private_chat_exercised = False
        try:
            for _step in range(500):
                if terminal_state.phase == "GAME_OVER":
                    break
                if (
                    terminal_state.phase == "FREE_ACTIVITY"
                    and not private_chat_exercised
                ):
                    private_target = next(
                        character
                        for character in terminal_state.characters
                        if not character.is_player and character.alive
                    )
                    rules.private_chat(
                        rules.PrivateChatRequest(
                            game_id=terminal_state.game_id,
                            npc_character_id=private_target.id,
                            question="我应该重点复盘哪位仍在场的角色？",
                        )
                    )
                    private_chat_exercised = True
                simulation_rules._advance_one_phase(
                    terminal_state,
                    simulation_rules.DEFAULT_PLAYER_STRATEGY,
                )
            else:
                raise AssertionError("terminal idempotency fixture did not finish")
        finally:
            for handler_name, original_handler in (
                original_simulation_handlers.items()
            ):
                setattr(rules, handler_name, original_handler)

        if (
            terminal_state.phase != "GAME_OVER"
            or not last_terminal_call
            or not private_chat_exercised
            or len(terminal_state.command_results)
            != len(terminal_state.rule_events) - 1
            or any(
                "idempotency_key" not in event.command
                for event in terminal_state.rule_events[1:]
            )
        ):
            raise AssertionError(
                "the all-keyed terminal fixture did not seal every command"
            )
        terminal_game_id = terminal_state.game_id
        terminal_save_path = terminal_idempotency_store.save_path(
            terminal_game_id
        )
        terminal_save_bytes = terminal_save_path.read_bytes()
        terminal_handler_name = str(last_terminal_call["handler_name"])
        terminal_request = last_terminal_call["request"]
        terminal_response_payload = last_terminal_call["response_payload"]

        rules.deactivate_game_persistence()
        rules.GAME_STORE.clear()
        rules.PERSISTED_GAME_IDS.clear()
        terminal_restart = rules.activate_game_persistence()
        if (
            terminal_restart.skipped_terminal_count != 1
            or terminal_restart.restored_count
            or terminal_restart.failure_count
            or terminal_game_id in rules.GAME_STORE
        ):
            raise AssertionError("terminal startup recovery must stay archive-only")

        terminal_duplicate = getattr(rules, terminal_handler_name)(
            terminal_request
        )
        if (
            terminal_duplicate.model_dump(mode="json")
            != terminal_response_payload
            or terminal_game_id in rules.GAME_STORE
            or terminal_save_path.read_bytes() != terminal_save_bytes
        ):
            raise AssertionError(
                "a skipped terminal archive must serve its exact keyed response"
            )

        terminal_key = str(terminal_request.idempotency_key)
        if terminal_handler_name == "resolve_night":
            conflicting_terminal_call = lambda: rules.submit_night_action(
                rules.NightActionRequest(
                    game_id=terminal_game_id,
                    character_id=1,
                    action_type="none",
                    idempotency_key=terminal_key,
                )
            )
        else:
            conflicting_terminal_call = lambda: rules.resolve_night(
                rules.NightResolveRequest(
                    game_id=terminal_game_id,
                    idempotency_key=terminal_key,
                )
            )
        expect_http_error(
            conflicting_terminal_call,
            status_code=409,
            label="terminal archive cross-endpoint key reuse",
            http_exception_type=rules.HTTPException,
        )
        if (
            terminal_game_id in rules.GAME_STORE
            or terminal_save_path.read_bytes() != terminal_save_bytes
        ):
            raise AssertionError("terminal result conflicts must remain read-only")
        rules.deactivate_game_persistence()
        rules.GAME_STORE.clear()
        rules.PERSISTED_GAME_IDS.clear()

        legacy_store = persistence.GameSaveStore(
            temp_root / "legacy-empty-command-results"
        )
        legacy_state = rules.create_wolf_game_state(
            rules.GameStartRequest(player_role="villager"),
            game_id="legacy_empty_command_results",
            random_seed=20260729,
        )
        legacy_payload = rules.build_game_save_envelope(
            legacy_state
        ).model_dump(mode="json")
        legacy_payload["state"].pop("command_results")
        legacy_payload["snapshot_digest"] = canonical_payload_digest(
            legacy_payload["state"]
        )
        legacy_path = legacy_store.save_path(legacy_state.game_id)
        write_json(legacy_path, legacy_payload)
        legacy_bytes = legacy_path.read_bytes()
        rules.GAME_SAVE_STORE = legacy_store
        normalized_envelope, normalized_legacy_state = (
            rules.load_validated_saved_game(legacy_state.game_id)
        )
        if (
            normalized_legacy_state.command_results
            or normalized_envelope.state.get("command_results") != {}
            or normalized_envelope.snapshot_digest
            != canonical_payload_digest(normalized_envelope.state)
            or legacy_path.read_bytes() != legacy_bytes
        ):
            raise AssertionError(
                "legacy empty command-results migration must normalize in memory only"
            )
        rules.GAME_STORE.clear()
        rules.PERSISTED_GAME_IDS.clear()
        legacy_recovery = rules.activate_game_persistence()
        if (
            legacy_recovery.restored_game_ids != [legacy_state.game_id]
            or legacy_recovery.failure_count
            or rules.GAME_STORE[legacy_state.game_id].command_results
            or legacy_path.read_bytes() != legacy_bytes
        ):
            raise AssertionError(
                "startup recovery must accept the one exact legacy omission"
            )
        rules.persist_game_state(rules.GAME_STORE[legacy_state.game_id])
        if "command_results" not in legacy_store.load(
            legacy_state.game_id
        ).state:
            raise AssertionError(
                "the next explicit save must upgrade the legacy snapshot"
            )
        rules.deactivate_game_persistence()
        rules.GAME_STORE.clear()
        rules.PERSISTED_GAME_IDS.clear()

        legacy_claim_store = persistence.GameSaveStore(
            temp_root / "legacy-public-claim-provenance"
        )
        original_config_fingerprint_builder = (
            rules.build_game_config_fingerprint
        )
        rules.build_game_config_fingerprint = (
            lambda **_kwargs: rules.build_legacy_v4_game_config_fingerprint()
        )
        try:
            legacy_claim_state = rules.create_wolf_game_state(
                rules.GameStartRequest(
                    player_role="villager",
                    npc_policy_mode="rule",
                ),
                game_id="legacy_public_claim_provenance",
                random_seed=20260742,
            )
        finally:
            rules.build_game_config_fingerprint = (
                original_config_fingerprint_builder
            )
        claim_checkpoint = begin_game_command(legacy_claim_state)
        legacy_claim_state.public_claims.append(
            rules.PublicClaimState(
                day=1,
                character_id=2,
                claim_type="role",
                claimed_role="seer",
            )
        )
        append_game_rule_event(
            legacy_claim_state,
            event_type="npc_day_speech_generated",
            visibility="public",
            command={"game_id": legacy_claim_state.game_id},
            checkpoint=claim_checkpoint,
            actor_id=2,
        )
        legacy_claim_payload = rules.build_game_save_envelope(
            legacy_claim_state
        ).model_dump(mode="json")
        for field in (
            "npc_policy_mode",
            "npc_policy_descriptors",
            "npc_reasoning_states",
        ):
            legacy_claim_payload["state"].pop(field)
        for claim in legacy_claim_payload["state"]["public_claims"]:
            claim.pop("phase")
            claim.pop("window_day")
            claim.pop("event_sequence")
        legacy_claim_payload["snapshot_digest"] = canonical_payload_digest(
            legacy_claim_payload["state"]
        )
        legacy_claim_path = legacy_claim_store.save_path(
            legacy_claim_state.game_id
        )
        write_json(legacy_claim_path, legacy_claim_payload)
        legacy_claim_bytes = legacy_claim_path.read_bytes()
        rules.GAME_SAVE_STORE = legacy_claim_store
        normalized_claim_envelope, normalized_claim_state = (
            rules.load_validated_saved_game(legacy_claim_state.game_id)
        )
        normalized_claim = normalized_claim_state.public_claims[0]
        if (
            normalized_claim.phase != ""
            or normalized_claim.window_day is not None
            or normalized_claim.event_sequence != 0
            or normalized_claim_envelope.state_digest
            != rule_state_digest(normalized_claim_state)
            or legacy_claim_path.read_bytes() != legacy_claim_bytes
        ):
            raise AssertionError(
                "legacy public-claim provenance must normalize in memory only"
            )
        rules.GAME_STORE.clear()
        rules.PERSISTED_GAME_IDS.clear()
        legacy_claim_recovery = rules.activate_game_persistence()
        if (
            legacy_claim_recovery.restored_game_ids
            != [legacy_claim_state.game_id]
            or legacy_claim_recovery.failure_count
            or legacy_claim_path.read_bytes() != legacy_claim_bytes
        ):
            raise AssertionError(
                "startup recovery must accept exact legacy claim defaults"
            )
        rules.persist_game_state(
            rules.GAME_STORE[legacy_claim_state.game_id]
        )
        upgraded_claim = legacy_claim_store.load(
            legacy_claim_state.game_id
        ).state["public_claims"][0]
        if any(
            field not in upgraded_claim
            for field in ("phase", "window_day", "event_sequence")
        ):
            raise AssertionError(
                "the next explicit save must write claim provenance defaults"
            )
        rules.deactivate_game_persistence()
        rules.GAME_STORE.clear()
        rules.PERSISTED_GAME_IDS.clear()

        corruption_root = temp_root / "corruption"

        def assert_corrupt_save_rejected(
            case_name: str,
            mutate: Callable[[dict[str, object]], None],
            *,
            requested_game_id: str | None = None,
        ) -> None:
            case_root = corruption_root / case_name
            case_store = persistence.GameSaveStore(case_root)
            source_game_id = f"corrupt_{case_name}"
            source_state = rules.create_wolf_game_state(
                rules.GameStartRequest(player_role="villager"),
                game_id=source_game_id,
                random_seed=20260730,
            )
            payload = rules.build_game_save_envelope(source_state).model_dump(
                mode="json"
            )
            mutate(payload)
            lookup_id = requested_game_id or source_game_id
            write_json(case_store.save_path(lookup_id), payload)
            rules.GAME_SAVE_STORE = case_store
            rules.GAME_STORE.clear()
            rules.PERSISTED_GAME_IDS.clear()
            expect_http_error(
                lambda: rules.restore_saved_game(lookup_id),
                status_code=409,
                label=f"corrupt save case {case_name}",
                http_exception_type=rules.HTTPException,
            )
            if lookup_id in rules.GAME_STORE:
                raise AssertionError(
                    f"corrupt save case {case_name} entered the active cache"
                )

        assert_corrupt_save_rejected(
            "extra_envelope",
            lambda payload: payload.__setitem__("unexpected", True),
        )
        assert_corrupt_save_rejected(
            "unknown_schema",
            lambda payload: payload.__setitem__("schema_version", "game_save.v999"),
        )
        assert_corrupt_save_rejected(
            "snapshot",
            lambda payload: payload["state"].__setitem__(
                "updated_at", "tampered-without-new-digest"
            ),
        )

        def add_unknown_state_field(payload: dict[str, object]) -> None:
            state_payload = payload["state"]
            state_payload["unexpected_state_field"] = True
            payload["snapshot_digest"] = canonical_payload_digest(state_payload)

        assert_corrupt_save_rejected("unknown_state", add_unknown_state_field)

        def tamper_event_chain(payload: dict[str, object]) -> None:
            state_payload = payload["state"]
            state_payload["rule_events"][-1]["phase_after"] = "TAMPERED"
            payload["snapshot_digest"] = canonical_payload_digest(state_payload)

        assert_corrupt_save_rejected("event_chain", tamper_event_chain)
        assert_corrupt_save_rejected(
            "event_sequence",
            lambda payload: payload.__setitem__("saved_event_sequence", 99),
        )

        def tamper_state_config(payload: dict[str, object]) -> None:
            state_payload = payload["state"]
            state_payload["recovery_config_fingerprint"] = "a" * 64
            payload["snapshot_digest"] = canonical_payload_digest(state_payload)

        assert_corrupt_save_rejected("state_config", tamper_state_config)
        assert_corrupt_save_rejected(
            "filename_id",
            lambda _payload: None,
            requested_game_id="different_game_id",
        )

        def assert_corrupt_command_result_rejected(
            case_name: str,
            mutate: Callable[[dict[str, object]], None],
        ) -> None:
            case_store = persistence.GameSaveStore(
                corruption_root / f"command_result_{case_name}"
            )
            payload = copy.deepcopy(keyed_envelope_payload)
            state_payload = payload["state"]
            mutate(state_payload)
            payload["snapshot_digest"] = canonical_payload_digest(state_payload)
            case_game_id = str(payload["game_id"])
            write_json(case_store.save_path(case_game_id), payload)
            rules.GAME_SAVE_STORE = case_store
            rules.GAME_STORE.clear()
            rules.PERSISTED_GAME_IDS.clear()
            expect_http_error(
                lambda: rules.restore_saved_game(case_game_id),
                status_code=409,
                label=f"corrupt command result case {case_name}",
                http_exception_type=rules.HTTPException,
            )
            if case_game_id in rules.GAME_STORE:
                raise AssertionError(
                    f"corrupt command result case {case_name} entered cache"
                )

        def first_command_result(
            state_payload: dict[str, object],
        ) -> dict[str, object]:
            command_results = state_payload["command_results"]
            return next(iter(command_results.values()))

        assert_corrupt_command_result_rejected(
            "missing_ledger",
            lambda state_payload: state_payload.pop("command_results"),
        )

        def tamper_result_response(state_payload: dict[str, object]) -> None:
            result_payload = first_command_result(state_payload)
            result_payload["response_payload"]["tampered"] = True

        def tamper_result_event_sequence(state_payload: dict[str, object]) -> None:
            result_payload = first_command_result(state_payload)
            result_payload["event_sequence"] = len(state_payload["rule_events"]) + 1

        def tamper_result_request_digest(state_payload: dict[str, object]) -> None:
            result_payload = first_command_result(state_payload)
            result_payload["request_digest"] = "f" * 64

        def tamper_result_event_digest(state_payload: dict[str, object]) -> None:
            result_payload = first_command_result(state_payload)
            result_payload["event_digest"] = "f" * 64

        def tamper_result_endpoint(state_payload: dict[str, object]) -> None:
            result_payload = first_command_result(state_payload)
            result_payload["endpoint"] = "unknown_endpoint"

        def remap_result_key(state_payload: dict[str, object]) -> None:
            command_results = state_payload["command_results"]
            original_key = next(iter(command_results))
            command_results["remapped-key-0001"] = command_results.pop(
                original_key
            )

        assert_corrupt_command_result_rejected(
            "response_digest", tamper_result_response
        )
        assert_corrupt_command_result_rejected(
            "event_sequence", tamper_result_event_sequence
        )
        assert_corrupt_command_result_rejected(
            "request_digest", tamper_result_request_digest
        )
        assert_corrupt_command_result_rejected(
            "event_digest", tamper_result_event_digest
        )
        assert_corrupt_command_result_rejected(
            "unknown_endpoint", tamper_result_endpoint
        )
        assert_corrupt_command_result_rejected(
            "mapping_key", remap_result_key
        )

        invalid_json_store = persistence.GameSaveStore(
            corruption_root / "invalid_json"
        )
        invalid_json_path = invalid_json_store.save_path("invalid_json")
        invalid_json_path.parent.mkdir(parents=True, exist_ok=True)
        invalid_json_path.write_text("{not-json", encoding="utf-8")
        rules.GAME_SAVE_STORE = invalid_json_store
        expect_http_error(
            lambda: rules.restore_saved_game("invalid_json"),
            status_code=409,
            label="invalid JSON save",
            http_exception_type=rules.HTTPException,
        )

        config_drift_store = persistence.GameSaveStore(
            corruption_root / "config_drift"
        )
        config_drift_state = rules.create_wolf_game_state(
            rules.GameStartRequest(player_role="villager"),
            game_id="config_drift",
            random_seed=20260731,
        )
        rules.GAME_SAVE_STORE = config_drift_store
        rules.persist_game_state(config_drift_state)
        frozen_fingerprint = config_drift_state.recovery_config_fingerprint
        original_fingerprint_builder = rules.build_game_config_fingerprint
        drifted_fingerprint = (
            "f" * 64 if frozen_fingerprint != "f" * 64 else "e" * 64
        )
        rules.build_game_config_fingerprint = (
            lambda **_kwargs: drifted_fingerprint
        )
        try:
            frozen_envelope = rules.build_game_save_envelope(config_drift_state)
            if frozen_envelope.config_fingerprint != frozen_fingerprint:
                raise AssertionError("an active game must retain its creation fingerprint")
            expect_http_error(
                lambda: rules.restore_saved_game(config_drift_state.game_id),
                status_code=409,
                label="non-terminal config drift",
                http_exception_type=rules.HTTPException,
            )
        finally:
            rules.build_game_config_fingerprint = original_fingerprint_builder

        fail_closed_store = persistence.GameSaveStore(temp_root / "fail-closed")
        rules.GAME_SAVE_STORE = fail_closed_store
        valid_startup_state = rules.create_wolf_game_state(
            rules.GameStartRequest(player_role="villager"),
            game_id="startup_valid",
            random_seed=20260740,
        )
        rules.persist_game_state(valid_startup_state)
        bad_startup_path = fail_closed_store.save_path("startup_invalid")
        bad_startup_path.write_text("{invalid", encoding="utf-8")
        rules.GAME_STORE.clear()
        rules.PERSISTED_GAME_IDS.clear()
        try:
            rules.activate_game_persistence()
        except RuntimeError:
            pass
        else:
            raise AssertionError("startup recovery must fail closed on one bad save")
        if (
            rules.GAME_PERSISTENCE_ACTIVE
            or "startup_valid" in rules.GAME_STORE
            or rules.LAST_GAME_RECOVERY_REPORT.failure_count != 1
        ):
            raise AssertionError("fail-closed recovery partially activated state")
        bad_startup_path.unlink()
        recovered = rules.activate_game_persistence()
        if recovered.restored_game_ids != ["startup_valid"]:
            raise AssertionError("valid startup recovery failed after corruption removal")
        rules.deactivate_game_persistence()

        terminal_store = persistence.GameSaveStore(temp_root / "terminal")
        rules.GAME_SAVE_STORE = terminal_store
        terminal_state = rules.create_wolf_game_state(
            rules.GameStartRequest(player_role="villager"),
            game_id="terminal_archive",
            random_seed=20260741,
        )
        terminal_checkpoint = begin_game_command(terminal_state)
        terminal_state.phase = "GAME_OVER"
        terminal_state.winner = "good"
        terminal_state.winner_reason = "persistence terminal fixture"
        append_game_rule_event(
            terminal_state,
            event_type="night_resolved",
            visibility="public",
            command={"game_id": terminal_state.game_id},
            checkpoint=terminal_checkpoint,
        )
        rules.persist_game_state(terminal_state)
        rules.GAME_STORE.clear()
        rules.PERSISTED_GAME_IDS.clear()
        original_fingerprint_builder = rules.build_game_config_fingerprint
        rules.build_game_config_fingerprint = lambda **_kwargs: "d" * 64
        try:
            terminal_recovery = rules.recover_unfinished_games_from_disk()
            if (
                terminal_recovery.skipped_terminal_count != 1
                or terminal_recovery.failure_count
                or terminal_state.game_id in rules.GAME_STORE
            ):
                raise AssertionError("startup recovery must skip a terminal archive")
            terminal_restore = rules.restore_saved_game(terminal_state.game_id)
            if not terminal_restore.restored:
                raise AssertionError("a skipped terminal archive must remain restorable")
        finally:
            rules.build_game_config_fingerprint = original_fingerprint_builder

        vote_state = rules.create_wolf_game_state(
            rules.GameStartRequest(player_role="villager"),
            game_id="invalid_vote_transaction",
            random_seed=20260742,
        )
        vote_state.phase = "VOTE"
        vote_state.votes = [
            rules.VoteState(
                day=vote_state.day,
                voter_id=2,
                target_id=3,
                reason="existing ballot",
            )
        ]
        rules.GAME_STORE[vote_state.game_id] = vote_state
        before_invalid_vote = vote_state.model_dump(mode="json")
        expect_http_error(
            lambda: rules.submit_and_resolve_all_votes(
                rules.PlayerVoteRequest(
                    game_id=vote_state.game_id,
                    character_id=vote_state.player_character_id,
                    target_id=None,
                )
            ),
            status_code=400,
            label="invalid combined vote",
            http_exception_type=rules.HTTPException,
        )
        if vote_state.model_dump(mode="json") != before_invalid_vote:
            raise AssertionError("a rejected combined vote must not mutate state")

        helper_failure_state = rules.create_wolf_game_state(
            rules.GameStartRequest(player_role="werewolf"),
            game_id="helper_failure_transaction",
            random_seed=20260743,
        )
        helper_target = next(
            character
            for character in helper_failure_state.characters
            if character.camp == "good"
        )
        rules.GAME_STORE[helper_failure_state.game_id] = helper_failure_state
        before_helper_failure = helper_failure_state.model_dump(mode="json")
        original_witch_refresh = rules.refresh_npc_witch_action

        def fail_after_night_action(_game_state: object) -> None:
            raise RuntimeError("injected post-mutation helper failure")

        rules.refresh_npc_witch_action = fail_after_night_action
        try:
            try:
                rules.submit_night_action(
                    rules.NightActionRequest(
                        game_id=helper_failure_state.game_id,
                        character_id=helper_failure_state.player_character_id,
                        action_type="werewolf_kill",
                        target_id=helper_target.id,
                    )
                )
            except RuntimeError as exc:
                if "injected post-mutation" not in str(exc):
                    raise
            else:
                raise AssertionError("the injected helper failure was not raised")
        finally:
            rules.refresh_npc_witch_action = original_witch_refresh
        if (
            rules.GAME_STORE[helper_failure_state.game_id].model_dump(mode="json")
            != before_helper_failure
        ):
            raise AssertionError(
                "a pre-commit helper failure must restore the command checkpoint"
            )

        rules.deactivate_game_persistence()
        print("V4.3-A/B persistence and idempotency checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
