#!/usr/bin/env python3
"""
U9 tournament rotation generator — KP13 Akademi.

Format : 5-a-side, 1-3-1 formation, 15-minute games played in one stretch.
         In possession the keeper steps out as a build-up defender, side by side
         with the central defender (CB). So the five pitch roles are:
             GK  -> build-up defender when we have the ball
             CB  -> central / defending player
             LW  -> left wing
             CM  -> central
             RW  -> right wing
Each 15-min game is split into 3 x 5-min slots so we can roll subs without
stopping the game.

Run:  python team/rotation_algorithm.py
It (re)writes  team/sessions/2026-06-07_tournament_rotation_u9.md
Change NUM_GAMES / gk_sched / squad and re-run to regenerate.
"""
import random
from pathlib import Path

# --------------------------------------------------------------------------- #
# 1. INPUTS — squad, what each player can play, and who keeps which game.
# --------------------------------------------------------------------------- #
POS = ["CB", "LW", "CM", "RW"]            # outfield roles (GK handled apart)

# Eligibility per player. GK only matters for the keeper schedule below.
elig = {
    "Felix":  {"GK", "CB", "CM", "LW", "RW"},  # great tech; today our defender (CB)
    "Louie":  {"GK", "LW", "RW"},              # physical; keeper ~3 games, else wing
    "Filip":  {"GK", "CB", "CM", "LW", "RW"},  # great tech; CB or winger
    "Oskar":  {"GK", "CM", "LW", "RW"},        # great; central or wings
    "Victor": {"CM", "LW", "RW"},              # wing mostly, can do central
    "Ozzy":   {"CM", "LW", "RW"},              # tech; most minutes on wing, can central
    "Philip": {"LW", "RW"},                    # wing only; weakest link, keep minutes ~equal
}
players = list(elig)

# Keeper per game. Louie keeps 3; the other two games need a defender-capable
# keeper, so Filip and Felix cover them (they are the only other CB players).
gk_sched = ["Louie", "Louie", "Louie", "Filip", "Felix"]
NUM_GAMES = len(gk_sched)
SLOTS = 3                                  # 3 x 5-min slots per game
SLOT_MIN = 5

# --------------------------------------------------------------------------- #
# 2. CORE — assign 4 on-field players to the 4 outfield positions.
# --------------------------------------------------------------------------- #
def assign_positions(onfield):
    """Backtracking fill of CB/LW/CM/RW respecting eligibility. None if impossible."""
    onfield = sorted(onfield, key=lambda p: len(elig[p] & set(POS)))  # tightest first
    res = [None]
    def bt(i, used, m):
        if i == len(onfield):
            res[0] = dict(m); return True
        p = onfield[i]
        for pos in [x for x in POS if x in elig[p] and x not in used]:
            m[p] = pos
            if bt(i + 1, used | {pos}, m):
                return True
            del m[p]
        return False
    return res[0] if bt(0, set(), {}) else None


def game_plan(g, seed, cur_mins):
    """
    Build one game.

    MODE A (keeper is Louie): both Felix & Filip are free outfield, so all six
        outfielders rest EXACTLY one slot -> everyone plays 10 min. CB is never
        left empty because Felix/Filip are never benched in the same slot.

    MODE B (keeper is Felix or Filip): only ONE CB-capable player is left, so he
        ANCHORS CB for the full 15 min. The other five share LW/CM/RW; four play
        10 min, one plays 5 min. The 5-min short stint is handed to whoever has
        the MOST minutes so far -> totals stay level across the tournament.
    """
    gk = gk_sched[g]
    outs = [p for p in players if p != gk]
    cb_cap = [p for p in outs if "CB" in elig[p]]
    rng = random.Random(seed)
    best, best_score = None, -1

    if len(cb_cap) >= 2:                                    # ---- MODE A ----
        for _ in range(8000):
            order = outs[:]; rng.shuffle(order)
            rest = [order[0:2], order[2:4], order[4:6]]     # each rests once
            ok, slots, seen = True, [], {p: set() for p in outs}
            for s in range(SLOTS):
                field = [p for p in outs if p not in rest[s]]
                if not any("CB" in elig[p] for p in field):
                    ok = False; break
                m = assign_positions(field)
                if m is None:
                    ok = False; break
                slots.append(m)
                for p, pos in m.items():
                    seen[p].add(pos)
            if not ok:
                continue
            score = sum(len(v) for v in seen.values()) + rng.random()  # reward variety
            if score > best_score:
                best_score, best = score, (gk, rest, slots, None)
        return best

    # ---- MODE B ----
    anchor = cb_cap[0]
    movers = [p for p in outs if p != anchor]
    short = max(movers, key=lambda p: (cur_mins[p], p))     # most-rested gets short stint
    for _ in range(8000):
        pool = [short, short] + [p for p in movers if p != short]   # 6 rest-stints
        rng.shuffle(pool)
        rest_slots, ok = [[], [], []], True
        for p in pool:
            cand = [s for s in range(SLOTS) if len(rest_slots[s]) < 2 and p not in rest_slots[s]]
            if not cand:
                ok = False; break
            rng.shuffle(cand); rest_slots[cand[0]].append(p)
        if not ok or any(len(r) != 2 for r in rest_slots):
            continue
        slots, seen, good = [], {p: set() for p in movers}, True
        for s in range(SLOTS):
            field = [p for p in movers if p not in rest_slots[s]]
            m = assign_positions([anchor] + field)
            if m is None or m.get(anchor) != "CB":
                good = False; break
            slots.append(m)
            for p in field:
                seen[p].add(m[p])
        if not good:
            continue
        score = sum(len(v) for v in seen.values()) + rng.random()
        if score > best_score:
            best_score, best = score, (gk, rest_slots, slots, anchor)
    return best


# --------------------------------------------------------------------------- #
# 3. BUILD the whole tournament + tally minutes.
# --------------------------------------------------------------------------- #
mins = {p: 0 for p in players}
plans = []
for g in range(NUM_GAMES):
    res = game_plan(g, seed=100 + g, cur_mins=mins)
    if res is None:
        raise SystemExit(f"No valid plan for game {g + 1} — check eligibility/keeper schedule")
    gk, rest, slots, anchor = res
    mins[gk] += SLOTS * SLOT_MIN
    for p in [x for x in players if x != gk]:
        mins[p] += sum(1 for s in slots if p in s) * SLOT_MIN
    plans.append(res)


# --------------------------------------------------------------------------- #
# 4. RENDER markdown.
# --------------------------------------------------------------------------- #
ICON = {"GK": "🧤 Keeper", "CB": "🛡️ Defender", "LW": "🏃 Wing L",
        "CM": "🎯 Central", "RW": "🏃 Wing R"}

def md():
    L = []
    L.append("# 🏆 Tournament Rotation — U9")
    L.append("### KP13 Akademi | 2026-06-07")
    L.append("")
    L.append("> **Format:** 5-a-side · **1-3-1** · 15-min games played in one stretch · "
             f"{NUM_GAMES} games · 3 × 5-min slots per game")
    L.append("> **In possession** the 🧤 keeper steps out as a **build-up defender** "
             "next to the 🛡️ central defender. Out of possession he drops back into goal.")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 👥 Squad & where they can play")
    L.append("")
    L.append("| Player | 🧤 GK | 🛡️ CB | 🎯 Central | 🏃 Wing |")
    L.append("|---|:--:|:--:|:--:|:--:|")
    for p in players:
        e = elig[p]
        row = (f"| {p} | {'✅' if 'GK' in e else ''} | {'✅' if 'CB' in e else ''} | "
               f"{'✅' if 'CM' in e else ''} | {'✅' if ('LW' in e or 'RW' in e) else ''} |")
        L.append(row)
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 🧠 The rotation algorithm")
    L.append("")
    L.append("The plan below is **generated**, not eyeballed, by "
             "[`team/rotation_algorithm.py`](../rotation_algorithm.py). "
             "Re-run it any time the squad, number of games or keeper plan changes.")
    L.append("")
    L.append("**Rules it follows, in order:**")
    L.append("")
    L.append("1. **Keeper plays the whole game (15 min).** A U9 keeper that "
             "doubles as build-up defender needs continuity — we don't swap him mid-game.")
    L.append("2. **Keeper schedule is fixed up front:** Louie keeps **3** games; "
             "the other two games are kept by **Filip** and **Felix** (our only other "
             "defender-capable players).")
    L.append("3. **Two scheduling modes**, picked automatically per game:")
    L.append("   - **Mode A — Louie in goal.** Both Felix *and* Filip are free outfield, "
             "so all **six** outfielders rest **exactly one** 5-min slot → everyone plays "
             "**10 min**. The defender slot is never left empty because Felix and Filip are "
             "never benched in the same slot.")
    L.append("   - **Mode B — Felix or Filip in goal.** Only **one** defender-capable "
             "player is left, so he **anchors CB for the full 15 min**. The other five "
             "share the wings + central; four play 10 min and one plays 5 min. The 5-min "
             "**short stint is given to whoever has the most minutes so far**, which keeps "
             "everyone's running total level.")
    L.append("4. **Position rules respected every slot:** Philip plays **wing only**; "
             "Louie plays **wing only** when he's outfield; the 🛡️ defender slot is always "
             "filled by Felix or Filip.")
    L.append("5. **Variety:** among legal line-ups the generator prefers the one that gives "
             "players the most *different* positions across the day.")
    L.append("")
    L.append("> Philip lands on the **same minutes as the other regular outfielders** — "
             "he is never the one parked on the bench.")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## ⏱️ Minutes per player")
    L.append("")
    L.append(f"_Total pitch-minutes available = {NUM_GAMES} games × 75 = "
             f"{NUM_GAMES*75}; fair share ≈ {NUM_GAMES*75/7:.0f} min each._")
    L.append("")
    L.append("| Player | Total min | Keeper games |")
    L.append("|---|:--:|:--:|")
    for p in sorted(mins, key=lambda x: -mins[x]):
        kg = gk_sched.count(p)
        L.append(f"| {p} | **{mins[p]}** | {kg if kg else '—'} |")
    L.append("")
    L.append("> Felix & Filip top the list because each not only keeps a game but also "
             "**anchors the defence for the full 15 min** in the other's keeper game — "
             "that's the cost of only having two defenders. Louie sits at 55 (3 full keeper "
             "games + short rests after). Everyone else is level at 50.")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 🔄 Game-by-game plan")
    L.append("")
    for g, (gk, rest, slots, anchor) in enumerate(plans, 1):
        mode = "A — all rotate" if anchor is None else f"B — {anchor} anchors 🛡️ all game"
        L.append(f"### ⚽ GAME {g}")
        L.append("")
        L.append(f"**🧤 Keeper (full 15 min): {gk}**  ·  _mode {mode}_")
        L.append("")
        L.append("| Slot | 🛡️ Defender | 🏃 Wing L | 🎯 Central | 🏃 Wing R | 😴 Resting |")
        L.append("|---|---|---|---|---|---|")
        for s in range(SLOTS):
            inv = {v: k for k, v in slots[s].items()}
            resters = [p for p in players if p != gk and p not in slots[s]]
            L.append(f"| {s*SLOT_MIN}–{s*SLOT_MIN+SLOT_MIN} min | {inv['CB']} | "
                     f"{inv['LW']} | {inv['CM']} | {inv['RW']} | {', '.join(resters)} |")
        L.append("")
    L.append("---")
    L.append("")
    L.append("## 📋 Coach notes")
    L.append("")
    L.append("- **Subs at each 5-min mark** — call the two resters off, send the two "
             "waiting players straight to their listed spots. Keep it quick (~20 s).")
    L.append("- **Build-up trigger:** when we win the ball the keeper pushes up beside the "
             "defender to make a back-two — make the central + wings spread to give passing "
             "angles. When we lose it, keeper recovers to goal.")
    L.append("- **If a game is shorter/longer or a player is missing:** edit `gk_sched`, "
             "`elig` or `NUM_GAMES` at the top of "
             "[`rotation_algorithm.py`](../rotation_algorithm.py) and re-run — the whole "
             "sheet regenerates and stays fair.")
    L.append("- **Quality over everything:** rotation is the scaffold; the coaching during "
             "each slot is the point.")
    L.append("")
    return "\n".join(L)


out = Path(__file__).parent / "sessions" / "2026-06-07_tournament_rotation_u9.md"
out.write_text(md(), encoding="utf-8")
print(f"Wrote {out}")
print("Minutes:", {p: mins[p] for p in sorted(mins, key=lambda x: -mins[x])})
