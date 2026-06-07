# 🏆 Tournament Rotation — U9
### KP13 Akademi | 2026-06-07

> **Format:** 5-a-side · **1-3-1** · 15-min games played in one stretch · 5 games · 3 × 5-min slots per game
> **In possession** the 🧤 keeper steps out as a **build-up defender** next to the 🛡️ central defender. Out of possession he drops back into goal.

---

## 👥 Squad & where they can play

| Player | 🧤 GK | 🛡️ CB | 🎯 Central | 🏃 Wing |
|---|:--:|:--:|:--:|:--:|
| Felix | ✅ | ✅ | ✅ | ✅ |
| Louie | ✅ |  |  | ✅ |
| Filip | ✅ | ✅ | ✅ | ✅ |
| Oskar | ✅ |  | ✅ | ✅ |
| Victor |  |  | ✅ | ✅ |
| Ozzy |  |  | ✅ | ✅ |
| Philip |  |  |  | ✅ |

---

## 🧠 The rotation algorithm

The plan below is **generated**, not eyeballed, by [`team/rotation_algorithm.py`](../rotation_algorithm.py). Re-run it any time the squad, number of games or keeper plan changes.

**Rules it follows, in order:**

1. **Keeper plays the whole game (15 min).** A U9 keeper that doubles as build-up defender needs continuity — we don't swap him mid-game.
2. **Keeper schedule is fixed up front:** Louie keeps **3** games; the other two games are kept by **Filip** and **Felix** (our only other defender-capable players).
3. **Two scheduling modes**, picked automatically per game:
   - **Mode A — Louie in goal.** Both Felix *and* Filip are free outfield, so all **six** outfielders rest **exactly one** 5-min slot → everyone plays **10 min**. The defender slot is never left empty because Felix and Filip are never benched in the same slot.
   - **Mode B — Felix or Filip in goal.** Only **one** defender-capable player is left, so he **anchors CB for the full 15 min**. The other five share the wings + central; four play 10 min and one plays 5 min. The 5-min **short stint is given to whoever has the most minutes so far**, which keeps everyone's running total level.
4. **Position rules respected every slot:** Philip plays **wing only**; Louie plays **wing only** when he's outfield; the 🛡️ defender slot is always filled by Felix or Filip.
5. **Variety:** among legal line-ups the generator prefers the one that gives players the most *different* positions across the day.

> Philip lands on the **same minutes as the other regular outfielders** — he is never the one parked on the bench.

---

## ⏱️ Minutes per player

_Total pitch-minutes available = 5 games × 75 = 375; fair share ≈ 54 min each._

| Player | Total min | Keeper games |
|---|:--:|:--:|
| Felix | **60** | 1 |
| Filip | **60** | 1 |
| Louie | **55** | 3 |
| Oskar | **50** | — |
| Victor | **50** | — |
| Ozzy | **50** | — |
| Philip | **50** | — |

> Felix & Filip top the list because each not only keeps a game but also **anchors the defence for the full 15 min** in the other's keeper game — that's the cost of only having two defenders. Louie sits at 55 (3 full keeper games + short rests after). Everyone else is level at 50.

---

## 🔄 Game-by-game plan

### ⚽ GAME 1

**🧤 Keeper (full 15 min): Louie**  ·  _mode A — all rotate_

| Slot | 🛡️ Defender | 🏃 Wing L | 🎯 Central | 🏃 Wing R | 😴 Resting |
|---|---|---|---|---|---|
| 0–5 min | Filip | Philip | Victor | Ozzy | Felix, Oskar |
| 5–10 min | Felix | Philip | Oskar | Victor | Filip, Ozzy |
| 10–15 min | Felix | Oskar | Ozzy | Filip | Victor, Philip |

### ⚽ GAME 2

**🧤 Keeper (full 15 min): Louie**  ·  _mode A — all rotate_

| Slot | 🛡️ Defender | 🏃 Wing L | 🎯 Central | 🏃 Wing R | 😴 Resting |
|---|---|---|---|---|---|
| 0–5 min | Felix | Oskar | Victor | Ozzy | Filip, Philip |
| 5–10 min | Felix | Philip | Ozzy | Filip | Oskar, Victor |
| 10–15 min | Filip | Philip | Oskar | Victor | Felix, Ozzy |

### ⚽ GAME 3

**🧤 Keeper (full 15 min): Louie**  ·  _mode A — all rotate_

| Slot | 🛡️ Defender | 🏃 Wing L | 🎯 Central | 🏃 Wing R | 😴 Resting |
|---|---|---|---|---|---|
| 0–5 min | Felix | Oskar | Ozzy | Filip | Victor, Philip |
| 5–10 min | Filip | Philip | Oskar | Victor | Felix, Ozzy |
| 10–15 min | Felix | Philip | Victor | Ozzy | Filip, Oskar |

### ⚽ GAME 4

**🧤 Keeper (full 15 min): Filip**  ·  _mode B — Felix anchors 🛡️ all game_

| Slot | 🛡️ Defender | 🏃 Wing L | 🎯 Central | 🏃 Wing R | 😴 Resting |
|---|---|---|---|---|---|
| 0–5 min | Felix | Oskar | Victor | Ozzy | Louie, Philip |
| 5–10 min | Felix | Louie | Ozzy | Philip | Oskar, Victor |
| 10–15 min | Felix | Philip | Oskar | Victor | Louie, Ozzy |

### ⚽ GAME 5

**🧤 Keeper (full 15 min): Felix**  ·  _mode B — Filip anchors 🛡️ all game_

| Slot | 🛡️ Defender | 🏃 Wing L | 🎯 Central | 🏃 Wing R | 😴 Resting |
|---|---|---|---|---|---|
| 0–5 min | Filip | Oskar | Victor | Ozzy | Louie, Philip |
| 5–10 min | Filip | Philip | Oskar | Victor | Louie, Ozzy |
| 10–15 min | Filip | Louie | Ozzy | Philip | Oskar, Victor |

---

## 📋 Coach notes

- **Subs at each 5-min mark** — call the two resters off, send the two waiting players straight to their listed spots. Keep it quick (~20 s).
- **Build-up trigger:** when we win the ball the keeper pushes up beside the defender to make a back-two — make the central + wings spread to give passing angles. When we lose it, keeper recovers to goal.
- **If a game is shorter/longer or a player is missing:** edit `gk_sched`, `elig` or `NUM_GAMES` at the top of [`rotation_algorithm.py`](../rotation_algorithm.py) and re-run — the whole sheet regenerates and stays fair.
- **Quality over everything:** rotation is the scaffold; the coaching during each slot is the point.
