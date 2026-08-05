"""REST surface for the in-town Texas Hold'em hall.

Tables are single-session and in-memory for now (one player + NPCs, no
persistence).  The player submits an action and the backend auto-advances every
NPC until it is the player's turn again or the hand finishes, so the client can
render the returned snapshot directly.
"""

from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .config import NPC_NAMES, NPC_PERSONALITIES
from .poker_engine import PokerPlayer, PokerTable, build_ai_decision


router = APIRouter(prefix="/api/poker", tags=["poker"])

POKER_TABLES: dict[str, PokerTable] = {}
POKER_TABLE_SEQ = 0


class PokerCreateRequest(BaseModel):
    player_name: str = "玩家"
    npc_count: int = Field(default=5, ge=2, le=10)
    buy_in: int = Field(default=1000, ge=100, le=100000)
    small_blind: int = Field(default=10, ge=1)
    big_blind: int = Field(default=20, ge=2)
    seed: Optional[int] = None


class PokerActionRequest(BaseModel):
    action: Literal["fold", "check", "call", "raise"]
    amount: int = Field(default=0, ge=0)


def _build_npc_players(count: int, buy_in: int) -> list[PokerPlayer]:
    selected = NPC_NAMES[:count]
    return [
        PokerPlayer(
            seat=index + 1,
            name=name,
            stack=buy_in,
            personality=dict(NPC_PERSONALITIES.get(name, {})),
        )
        for index, name in enumerate(selected)
    ]


def _advance_npcs(table: PokerTable) -> None:
    while (
        table.phase not in {"showdown", "finished"}
        and table.current_actor is not None
    ):
        actor_seat = table.current_actor
        actor = table.players[actor_seat]
        if actor.is_player:
            return
        action, amount = build_ai_decision(table, actor_seat)
        try:
            table.act(actor_seat, action, amount)
        except ValueError:
            try:
                table.act(
                    actor_seat,
                    "call" if table.current_bet > actor.street_bet else "check",
                    0,
                )
            except ValueError:
                table.act(actor_seat, "fold", 0)


def _table_or_404(table_id: str) -> PokerTable:
    table = POKER_TABLES.get(table_id)
    if table is None:
        raise HTTPException(status_code=404, detail="未找到这桌德州扑克。")
    return table


@router.post("/table", response_model=dict)
def create_poker_table(request: PokerCreateRequest) -> dict[str, object]:
    global POKER_TABLE_SEQ
    POKER_TABLE_SEQ += 1
    table_id = f"poker_{POKER_TABLE_SEQ:04d}"
    npc_players = _build_npc_players(request.npc_count, request.buy_in)
    players = [
        PokerPlayer(
            seat=0,
            name=request.player_name.strip() or "玩家",
            is_player=True,
            stack=request.buy_in,
        )
    ] + npc_players
    table = PokerTable(
        table_id=table_id,
        players=players,
        small_blind=request.small_blind,
        big_blind=request.big_blind,
        seed=request.seed,
    )
    POKER_TABLES[table_id] = table
    table.start_hand()
    _advance_npcs(table)
    return {"table_id": table_id, "state": table.public_state()}


@router.get("/table/{table_id}", response_model=dict)
def get_poker_table(table_id: str) -> dict[str, object]:
    table = _table_or_404(table_id)
    return table.public_state()


@router.post("/table/{table_id}/act", response_model=dict)
def act_on_poker_table(
    table_id: str,
    request: PokerActionRequest,
) -> dict[str, object]:
    table = _table_or_404(table_id)
    player = next(
        (item for item in table.players if item.is_player),
        None,
    )
    if player is None or not table.player_can_act(player.seat):
        raise HTTPException(
            status_code=400,
            detail="当前不是你的回合，或本手牌已经结束。",
        )
    try:
        table.act(player.seat, request.action, request.amount)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _advance_npcs(table)
    return table.public_state()


@router.post("/table/{table_id}/next-hand", response_model=dict)
def start_next_poker_hand(table_id: str) -> dict[str, object]:
    table = _table_or_404(table_id)
    if table.phase not in {"showdown", "finished"}:
        raise HTTPException(status_code=400, detail="本手牌还没结束。")
    table.start_hand()
    _advance_npcs(table)
    return table.public_state()
