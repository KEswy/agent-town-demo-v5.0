"""Offline Texas Hold'em engine for the Agent Town poker hall.

The engine is pure Python and deterministic when a seed is provided, matching
the project's offline-testability rules.  Real games use a fresh system-seeded
shuffle; the player never sees hidden NPC cards or the RNG stream.

Rules implemented: standard no-limit Hold'em with small/big blinds, preflop /
flop / turn / river, fold / check / call / raise / all-in, correct side-pot
settlement at showdown, and personality-driven NPC betting.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional


SUITS = ("s", "h", "d", "c")
RANK_NAMES = {
    2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7",
    8: "8", 9: "9", 10: "10", 11: "J", 12: "Q", 13: "K", 14: "A",
}

# Hand categories, higher is better.
CATEGORY_NAMES = {
    0: "高牌",
    1: "一对",
    2: "两对",
    3: "三条",
    4: "顺子",
    5: "同花",
    6: "葫芦",
    7: "四条",
    8: "同花顺",
}


def build_deck() -> list[tuple[int, str]]:
    return [(rank, suit) for rank in range(2, 15) for suit in SUITS]


def card_label(card: tuple[int, str]) -> str:
    rank, suit = card
    suit_symbol = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}[suit]
    return f"{RANK_NAMES[rank]}{suit_symbol}"


def evaluate_hand(cards: list[tuple[int, str]]) -> tuple[int, tuple[int, ...]]:
    """Return (category, tiebreak) for the best five-card hand from ``cards``."""

    if len(cards) < 5:
        raise ValueError("hand evaluation requires at least five cards")
    ranks = sorted((rank for rank, _suit in cards), reverse=True)
    suits = [suit for _rank, suit in cards]
    flush_suit = next(
        (suit for suit in SUITS if suits.count(suit) >= 5),
        None,
    )
    is_flush = flush_suit is not None

    unique_ranks = sorted(set(ranks), reverse=True)
    is_straight = False
    straight_high = 0
    straight_ranks: set[int] = set()
    if len(unique_ranks) >= 5:
        for start_index in range(len(unique_ranks) - 4):
            window = unique_ranks[start_index:start_index + 5]
            if window[0] - window[4] == 4 and len(set(window)) == 5:
                is_straight = True
                straight_high = window[0]
                straight_ranks = set(window)
                break
        # Wheel: A-2-3-4-5
        if not is_straight and 14 in unique_ranks and {2, 3, 4, 5}.issubset(
            set(unique_ranks)
        ):
            is_straight = True
            straight_high = 5
            straight_ranks = {14, 2, 3, 4, 5}

    if is_flush and is_straight:
        flush_suit_ranks = {
            rank for rank, suit in cards if suit == flush_suit
        }
        if straight_ranks.issubset(flush_suit_ranks):
            return (8, (straight_high,))

    counts: dict[int, int] = {}
    for rank in ranks:
        counts[rank] = counts.get(rank, 0) + 1
    by_count: dict[int, list[int]] = {}
    for rank, count in counts.items():
        by_count.setdefault(count, []).append(rank)

    if 4 in by_count:
        quad_rank = max(by_count[4])
        kicker = max(rank for rank in ranks if rank != quad_rank)
        return (7, (quad_rank, kicker))
    if 3 in by_count and 2 in by_count:
        trips_rank = max(by_count[3])
        pair_rank = max(by_count[2])
        return (6, (trips_rank, pair_rank))
    if is_flush:
        flush_ranks = sorted(
            (rank for rank, suit in cards if suit == flush_suit),
            reverse=True,
        )
        return (5, tuple(flush_ranks[:5]))
    if is_straight:
        return (4, (straight_high,))
    if 3 in by_count:
        trips_rank = max(by_count[3])
        kickers = sorted(
            (rank for rank in ranks if rank != trips_rank),
            reverse=True,
        )
        return (3, (trips_rank, *kickers[:2]))
    pairs = sorted(by_count.get(2, []), reverse=True)
    if len(pairs) >= 2:
        kicker = max(
            rank for rank in ranks if rank not in pairs[:2]
        )
        return (2, (pairs[0], pairs[1], kicker))
    if pairs:
        pair_rank = pairs[0]
        kickers = sorted(
            (rank for rank in ranks if rank != pair_rank),
            reverse=True,
        )
        return (1, (pair_rank, *kickers[:3]))
    return (0, tuple(unique_ranks[:5]))


def compare_hands(
    hand_a: tuple[int, tuple[int, ...]],
    hand_b: tuple[int, tuple[int, ...]],
) -> int:
    """Return -1 / 0 / 1 comparing two evaluated hands."""

    if hand_a == hand_b:
        return 0
    return -1 if hand_a < hand_b else 1


@dataclass
class PokerPlayer:
    seat: int
    name: str
    is_player: bool = False
    stack: int = 1000
    hole_cards: list[tuple[int, str]] | None = None
    folded: bool = False
    all_in: bool = False
    street_bet: int = 0
    total_bet: int = 0
    personality: dict[str, float] | None = None
    won_this_hand: bool = False

    @property
    def active(self) -> bool:
        return not self.folded and not self.all_in and self.stack > 0


class PokerTable:
    """One poker table.  Mutating methods advance the hand state machine."""

    def __init__(
        self,
        *,
        table_id: str,
        players: list[PokerPlayer],
        small_blind: int = 10,
        big_blind: int = 20,
        seed: Optional[int] = None,
    ) -> None:
        self.table_id = table_id
        self.players = players
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.seed = seed
        self.rng = random.Random(seed)
        self.dealer_seat = 0
        self.community: list[tuple[int, str]] = []
        self.phase = "waiting"  # waiting | preflop | flop | turn | river | showdown | finished
        self.current_actor: Optional[int] = None
        self.current_bet = 0
        self.min_raise = big_blind
        self.last_aggressor: Optional[int] = None
        self.pot = 0
        self.hand_number = 0
        self.winner_seat: Optional[int] = None
        self.result_message = ""
        self.hand_history: list[str] = []
        self.hand_start_stacks: dict[int, int] = {}
        self.last_showdown: Optional[dict[str, object]] = None
        self.street_raise_count = 0
        self.last_raise_seat: Optional[int] = None

    def _deck(self) -> list[tuple[int, str]]:
        deck = build_deck()
        self.rng.shuffle(deck)
        return deck

    def start_hand(self) -> None:
        """Deal a fresh hand: rotate the button, post blinds, deal hole cards."""

        self.hand_number += 1
        # Busted players are permanently out of the game.
        for player in self.players:
            if player.stack <= 0:
                player.folded = True
        self.last_showdown = None
        self.street_raise_count = 0
        self.last_raise_seat = None
        self.hand_start_stacks = {
            player.seat: player.stack for player in self.players
        }
        self.community = []
        self.pot = 0
        self.phase = "preflop"
        self.winner_seat = None
        self.result_message = ""
        for player in self.players:
            player.hole_cards = None
            player.folded = False
            player.all_in = False
            player.street_bet = 0
            player.total_bet = 0
            player.won_this_hand = False

        self.dealer_seat = (self.dealer_seat + 1) % len(self.players)
        active_seats = [player.seat for player in self.players if player.stack > 0]
        player = self.players[0] if self.players else None
        if player is not None and player.stack <= 0:
            self.phase = "finished"
            self.result_message = "你已输光筹码，扑克对局结束。"
            self.current_actor = None
            return
        if len(active_seats) < 2:
            self.phase = "finished"
            self.result_message = (
                "🎉 你横扫全场，赢光了所有 NPC！"
                if player is not None and player.stack > 0
                else "牌桌不足两人，对局结束。"
            )
            return

        deck = self._deck()
        for _round in range(2):
            for player in self.players:
                if player.stack <= 0:
                    continue
                if player.hole_cards is None:
                    player.hole_cards = []
                player.hole_cards.append(deck.pop())

        small_index = (self.dealer_seat + 1) % len(self.players)
        big_index = (self.dealer_seat + 2) % len(self.players)
        self._post_blind(small_index, self.small_blind)
        self._post_blind(big_index, self.big_blind)
        self.pot = self.small_blind + self.big_blind
        self.current_bet = self.big_blind
        self.min_raise = self.big_blind
        self.last_aggressor = big_index

        # Preflop the first actor is the player left of the big blind (UTG),
        # which is also the small blind in heads-up play.
        self.current_actor = big_index
        self._advance_to_next_actor()
        self._sync_history("新一局开始，盲注 " + str(self.small_blind) + "/" + str(self.big_blind))

    def _post_blind(self, seat_index: int, amount: int) -> None:
        player = self.players[seat_index]
        real_amount = min(amount, player.stack)
        player.stack -= real_amount
        player.street_bet += real_amount
        player.total_bet += real_amount
        if player.stack == 0:
            player.all_in = True

    def _next_seat(self, seat_index: int) -> int:
        return (seat_index + 1) % len(self.players)

    def _advance_to_next_actor(self) -> None:
        if self.phase in {"showdown", "finished"}:
            self.current_actor = None
            return
        if self.current_actor is None:
            return
        cursor = self.current_actor
        for _ in range(len(self.players)):
            cursor = self._next_seat(cursor)
            player = self.players[cursor]
            if player.active:
                self.current_actor = cursor
                return
        self.current_actor = None

    def _street_actions_complete(self) -> bool:
        active_players = [p for p in self.players if not p.folded]
        if len(active_players) <= 1:
            return True
        for player in active_players:
            if player.active and player.street_bet != self.current_bet:
                return False
        return True

    def _deal_street(self, count: int) -> None:
        deck = self._deck()
        if self.phase == "preflop":
            self.community.extend(deck[:3])
            self.phase = "flop"
        elif self.phase == "flop":
            self.community.append(deck[0])
            self.phase = "turn"
        elif self.phase == "turn":
            self.community.append(deck[0])
            self.phase = "river"
        else:
            raise ValueError("cannot deal beyond the river")

    def _start_showdown(self) -> None:
        self.phase = "showdown"
        self.current_actor = None
        self._settle_side_pots()

    def _settle_side_pots(self) -> None:
        remaining = [
            player
            for player in self.players
            if not player.folded and player.total_bet > 0
        ]
        if not remaining:
            self.result_message = "所有玩家都弃牌，底池无人认领。"
            return
        if len(remaining) == 1:
            winner = remaining[0]
            winner.stack += self.pot
            winner.won_this_hand = True
            self.winner_seat = winner.seat
            self.result_message = f"{winner.name} 赢得底池 {self.pot}（其余玩家弃牌）。"
            self.pot = 0
            self.last_showdown = self._build_showdown_record()
            return

        # Side-pot settlement: build contribution tiers from every player who
        # put chips in this hand (folded players' bets stay in the pot), then
        # award each tier only to non-folded contenders with the best hand.
        pots: list[tuple[list[PokerPlayer], int]] = []
        contributors = [
            player
            for player in self.players
            if player.total_bet > 0
        ]
        while contributors:
            min_bet = min(player.total_bet for player in contributors)
            pot_size = 0
            eligible: list[PokerPlayer] = []
            for player in list(contributors):
                contribution = min(player.total_bet, min_bet)
                pot_size += contribution
                player.total_bet -= contribution
                if contribution > 0:
                    eligible.append(player)
                if player.total_bet == 0:
                    contributors.remove(player)
            pots.append((eligible, pot_size))

        for eligible, pot_size in pots:
            contenders = [player for player in eligible if not player.folded]
            if not contenders:
                continue
            best = max(
                contenders,
                key=lambda player: evaluate_hand(
                    list(player.hole_cards or []) + list(self.community)
                ),
            )
            # Split ties by equally dividing chips among equal best hands.
            best_hand = evaluate_hand(list(best.hole_cards or []) + list(self.community))
            tied = [
                player
                for player in contenders
                if evaluate_hand(list(player.hole_cards or []) + list(self.community))
                == best_hand
            ]
            share = pot_size // len(tied)
            remainder = pot_size % len(tied)
            for player in tied:
                player.stack += share
                player.won_this_hand = True
            tied[0].stack += remainder
            self.winner_seat = best.seat
            self.result_message += (
                f"{best.name} 赢得底池 {pot_size}（" + CATEGORY_NAMES[best_hand[0]] + "）。"
            )
        self.pot = 0
        self.last_showdown = self._build_showdown_record()

    def _build_showdown_record(self) -> dict[str, object]:
        player = self.players[0] if self.players else None
        start_stack = self.hand_start_stacks.get(0, 0)
        player_net = (player.stack - start_stack) if player is not None else 0
        category = -1
        player_category = -1
        if self.phase == "showdown" and self.winner_seat is not None:
            winner = self.players[self.winner_seat]
            category = evaluate_hand(
                list(winner.hole_cards or []) + list(self.community)
            )[0]
        if player is not None and not player.folded and player.hole_cards:
            combined = list(player.hole_cards or []) + list(self.community)
            if len(combined) >= 5:
                player_category = evaluate_hand(combined)[0]
        return {
            "winner_seat": self.winner_seat,
            "category": category,
            "player_won": bool(player is not None and self.winner_seat == 0),
            "player_net": player_net,
            "player_category": player_category,
        }

    def player_can_act(self, seat: int) -> bool:
        return (
            self.phase not in {"waiting", "showdown", "finished"}
            and self.current_actor == seat
            and self.players[seat].active
        )

    def act(
        self,
        seat: int,
        action: str,
        amount: int = 0,
    ) -> None:
        """Apply one legal action; the caller is responsible for the current actor."""

        if not self.player_can_act(seat):
            raise ValueError(f"座位 {seat} 当前不能行动")
        player = self.players[seat]
        to_call = self.current_bet - player.street_bet

        if action == "fold":
            player.folded = True
            self._sync_history(f"{player.name} 弃牌。")
        elif action == "check":
            if to_call > 0:
                raise ValueError("需要跟注时不能过牌")
            self._sync_history(f"{player.name} 过牌。")
        elif action == "call":
            real_call = min(to_call, player.stack)
            player.stack -= real_call
            player.street_bet += real_call
            player.total_bet += real_call
            self.pot += real_call
            if player.stack == 0:
                player.all_in = True
            self._sync_history(f"{player.name} 跟注 {real_call}。")
        elif action == "raise":
            previous_bet = self.current_bet
            total_commit = max(amount, to_call)
            if total_commit > player.stack + player.street_bet:
                raise ValueError("筹码不足")
            raise_size = total_commit - previous_bet
            is_all_in = total_commit >= player.stack + player.street_bet
            if raise_size < self.min_raise and not is_all_in:
                raise ValueError(
                    f"加注不能低于最小加注幅度 {self.min_raise}"
                )
            additional = total_commit - player.street_bet
            player.stack -= additional
            player.street_bet = total_commit
            player.total_bet += additional
            self.pot += additional
            if total_commit > previous_bet:
                self.current_bet = total_commit
                self.min_raise = max(self.min_raise, raise_size)
                self.last_aggressor = seat
                self.street_raise_count += 1
                self.last_raise_seat = seat
            if player.stack == 0:
                player.all_in = True
            self._sync_history(
                f"{player.name} 加注到 {total_commit}（本街）。"
            )
        else:
            raise ValueError(f"未知行动：{action}")

        self._advance_street_or_actor()

    def _advance_street_or_actor(self) -> None:
        remaining = [player for player in self.players if not player.folded]
        if len(remaining) <= 1:
            # Everyone else folded; award the pot without showdown.
            winner = remaining[0]
            winner.stack += self.pot
            winner.won_this_hand = True
            self.winner_seat = winner.seat
            self.result_message = f"{winner.name} 赢得底池 {self.pot}（其余玩家弃牌）。"
            self.pot = 0
            self.phase = "finished"
            self.current_actor = None
            self.last_showdown = self._build_showdown_record()
            return

        if self._street_actions_complete():
            for player in self.players:
                player.street_bet = 0
            self.street_raise_count = 0
            self.last_raise_seat = None
            if self.phase == "preflop":
                self._deal_street(3)
                self.current_bet = 0
                self.min_raise = self.big_blind
                self._sync_history("翻牌：" + " ".join(card_label(c) for c in self.community))
            elif self.phase == "flop":
                self._deal_street(1)
                self.current_bet = 0
                self.min_raise = self.big_blind
                self._sync_history("转牌：" + card_label(self.community[-1]))
            elif self.phase == "turn":
                self._deal_street(1)
                self.current_bet = 0
                self.min_raise = self.big_blind
                self._sync_history("河牌：" + card_label(self.community[-1]))
            elif self.phase == "river":
                self._start_showdown()
                return
            # Postflop the first actor is the first active player left of the
            # dealer button.
            self.current_actor = self.dealer_seat
            self._advance_to_next_actor()
            return

        self._advance_to_next_actor()
        if self.current_actor is None:
            self._start_showdown()

    def _sync_history(self, line: str) -> None:
        self.hand_history.append(line)
        if len(self.hand_history) > 60:
            self.hand_history = self.hand_history[-60:]

    def public_state(self) -> dict[str, object]:
        """Serialize the table without exposing hidden NPC hole cards."""

        return {
            "table_id": self.table_id,
            "hand_number": self.hand_number,
            "phase": self.phase,
            "dealer_seat": self.dealer_seat,
            "small_blind": self.small_blind,
            "big_blind": self.big_blind,
            "community": [card_label(card) for card in self.community],
            "pot": self.pot,
            "current_bet": self.current_bet,
            "min_raise": self.min_raise,
            "current_actor": self.current_actor,
            "street_raise_count": self.street_raise_count,
            "last_raise_seat": self.last_raise_seat,
            "winner_seat": self.winner_seat,
            "result_message": self.result_message,
            "hand_history": list(self.hand_history),
            "last_showdown": self.last_showdown,
            "players": [
                {
                    "seat": player.seat,
                    "name": player.name,
                    "is_player": player.is_player,
                    "stack": player.stack,
                    "folded": player.folded,
                    "all_in": player.all_in,
                    "street_bet": player.street_bet,
                    "hole_cards": (
                        [card_label(card) for card in player.hole_cards]
                        if player.is_player and player.hole_cards
                        else []
                    ),
                    "won_this_hand": player.won_this_hand,
                }
                for player in self.players
            ],
        }


def build_ai_decision(
    table: PokerTable,
    seat: int,
) -> tuple[str, int]:
    """Return the NPC's (action, amount) using personality, position, and
    street raise history (two-round raise reads)."""

    player = table.players[seat]
    personality = player.personality or {}
    aggressiveness = float(personality.get("aggressiveness", 0.5))
    cautiousness = float(personality.get("cautiousness", 0.5))
    deception = float(personality.get("deception", 0.5))
    variance = float(personality.get("decision_variance", 0.3))

    hole = player.hole_cards or []
    board = table.community
    all_cards = list(hole) + list(board)
    to_call = table.current_bet - player.street_bet
    pot_odds = (to_call / (table.pot + to_call)) if (table.pot + to_call) > 0 else 0.0
    position_distance = (seat - table.dealer_seat) % len(table.players)
    player_count = len(table.players)
    street_raises = table.street_raise_count
    aggressor_aggression = 0.5
    if table.last_raise_seat is not None and table.last_raise_seat != seat:
        aggressor_personality = (
            table.players[table.last_raise_seat].personality or {}
        )
        aggressor_aggression = float(
            aggressor_personality.get("aggressiveness", 0.5)
        )

    if len(all_cards) >= 5:
        strength = evaluate_hand(all_cards)[0] / 8.0
    else:
        # Preflop starting-hand heuristic adjusted by table position.
        strength = _preflop_strength(hole, position_distance, player_count)

    # Draw potential: count flush and open-ended straight outs on the turn/river.
    draw_bonus = _draw_bonus(hole, board)
    effective = min(1.0, strength * 0.82 + draw_bonus * 0.25)

    tightness = 1.0 - cautiousness
    looseness = 1.0 - tightness
    aggression = 0.35 + aggressiveness * 0.55
    bluff_chance = 0.04 + deception * 0.10
    noise = (table.rng.random() - 0.5) * variance * 0.18
    score = effective + noise + looseness * 0.05
    # Raise reads: a re-raise (or 3-bet) forces weak hands out, and facing an
    # aggressive aggressor tightens the call range further.
    raise_pressure = min(1.0, street_raises * 0.5)
    fold_floor = (
        0.32
        + raise_pressure * 0.06
        + (0.04 if aggressor_aggression > 0.62 else 0.0)
    )

    # Fold weak hands facing a meaningful bet unless the pot is very cheap.
    if to_call > 0 and score < fold_floor and to_call > table.big_blind:
        if table.rng.random() > bluff_chance:
            return ("fold", 0)

    if to_call == 0:
        # Late position (button/small blind in heads-up) can steal a cheap pot.
        late_steal = (
            position_distance <= 2
            and score < 0.62
            and table.rng.random() < 0.35 * aggression
        )
        if (
            score > 0.58 + (1.0 - aggression) * 0.12
            or late_steal
        ):
            return ("raise", _choose_raise(table, player, seat, score, aggression))
        return ("check", 0)

    # Facing a bet: call if pot odds or hand justify it.
    if score > pot_odds + 0.18:
        strong_raise = (
            0.66
            + (1.0 - aggression) * 0.10
            + raise_pressure * 0.06
        )
        if street_raises >= 2:
            # Re-raise pressure: medium hands just call; only strong hands
            # 4-bet, and a conservative aggressor makes the 4-bet more likely.
            strong_raise = 0.74 + raise_pressure * 0.10
            if aggressor_aggression < 0.42:
                strong_raise -= 0.06
        if score > strong_raise or table.rng.random() < bluff_chance:
            return ("raise", _choose_raise(table, player, seat, score, aggression))
        return ("call", 0)
    if table.rng.random() < bluff_chance:
        return ("raise", _choose_raise(table, player, seat, score + 0.08, aggression))
    return ("fold", 0)


def _preflop_strength(
    hole: list[tuple[int, str]],
    position_distance: int,
    player_count: int,
) -> float:
    if len(hole) != 2:
        return 0.3
    r1, s1 = hole[0]
    r2, s2 = hole[1]
    high = max(r1, r2)
    low = min(r1, r2)
    score = 0.18 + (high - 2) / 12.0 * 0.28
    if r1 == r2:
        score += 0.32
    if high - low <= 2:
        score += 0.08
    if s1 == s2:
        score += 0.05
    if player_count == 2:
        score += 0.10
    elif position_distance == 0:
        score += 0.08  # button
    elif position_distance >= player_count - 2:
        score += 0.05  # late positions (CO/HJ)
    elif position_distance == 2:
        score -= 0.02  # big blind defends a bit wider
    elif position_distance == 1:
        score -= 0.05  # small blind out of position
    return min(1.0, max(0.0, score))


def _draw_bonus(
    hole: list[tuple[int, str]],
    board: list[tuple[int, str]],
) -> float:
    if len(board) < 3:
        return 0.0
    suits = [suit for _rank, suit in hole + board]
    flush_outs = 0
    for suit in SUITS:
        flush_outs = max(flush_outs, suits.count(suit))
    flush_bonus = 0.12 if flush_outs == 4 else 0.0
    ranks = sorted({rank for rank, _suit in hole + board})
    straight_bonus = 0.0
    if len(ranks) >= 4:
        for start in range(2, 12):
            window = set(range(start, start + 5))
            overlap = len(window & set(ranks))
            if overlap == 4:
                straight_bonus = 0.10
                break
    return flush_bonus + straight_bonus


def _choose_raise(
    table: PokerTable,
    player: PokerPlayer,
    seat: int,
    score: float,
    aggression: float,
) -> int:
    to_call = table.current_bet - player.street_bet
    raise_size = max(
        table.min_raise,
        int((2.0 + aggression * 2.0 + score * 1.6) * table.big_blind),
    )
    total = player.street_bet + to_call + raise_size
    if total >= player.stack + player.street_bet:
        return player.stack + player.street_bet
    return total
