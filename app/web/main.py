"""FastAPI web application — mobile-first player experience for KP13 Akademi."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

# Path setup so core/ is importable
_APP_DIR = Path(__file__).resolve().parent.parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

import jinja2

from core import database as db
from core.epm import (
    get_player_profile,
    identify_gaps,
    identify_strengths,
    DIM_BY_KEY,
    CATEGORIES,
    CATEGORY_DIMS,
)
from core.agents.session_designer import design_week, load_schedule, save_schedule
from core.models import WeeklySchedule

# ---------------------------------------------------------------------------

app = FastAPI(title="KP13 Akademi", docs_url=None, redoc_url=None)

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=jinja2.select_autoescape(["html"]),
    auto_reload=True,
)

_STATIC_DIR = Path(__file__).parent / "static"
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


def _render(template_name: str, **context) -> HTMLResponse:
    template = _env.get_template(template_name)
    return HTMLResponse(template.render(**context))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _monday(d: date) -> date:
    """Return the Monday of the week containing *d*."""
    return d - timedelta(days=d.weekday())


def _score_to_stage(score: float) -> tuple[str, str]:
    """Return (stage_label, tailwind_color_class) for a score."""
    if score >= 9.0:
        return "Elite", "text-red-400"
    if score >= 7.5:
        return "Advanced", "text-amber-400"
    if score >= 5.5:
        return "Confident", "text-green-400"
    if score >= 3.0:
        return "Developing", "text-blue-400"
    return "Discovering", "text-gray-400"


def _stage_bg(score: float) -> str:
    if score >= 9.0:
        return "bg-red-500/20"
    if score >= 7.5:
        return "bg-amber-500/20"
    if score >= 5.5:
        return "bg-green-500/20"
    if score >= 3.0:
        return "bg-blue-500/20"
    return "bg-gray-500/20"


def _bar_color(score: float) -> str:
    if score >= 9.0:
        return "bg-red-500"
    if score >= 7.5:
        return "bg-amber-500"
    if score >= 5.5:
        return "bg-green-500"
    if score >= 3.0:
        return "bg-blue-500"
    return "bg-gray-500"


def _verify(token: str) -> dict[str, Any]:
    info = db.verify_access_token(token)
    if not info:
        raise HTTPException(status_code=404, detail="Link not found")
    return info


def _get_or_generate_schedule(player_id: str, week_start: str) -> WeeklySchedule | None:
    """Return schedule from DB or generate via the session_designer agent and save."""
    existing = load_schedule(player_id, week_start)
    if existing is not None:
        return existing

    try:
        schedule = design_week(player_id, week_start)
        save_schedule(player_id, week_start, schedule)
        return schedule
    except Exception:
        import traceback
        traceback.print_exc()
        return None


# ---------------------------------------------------------------------------
# startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup():
    db.init_db()


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    """Liveness/readiness probe with lightweight DB check."""
    try:
        with db.get_db() as conn:
            conn.execute("SELECT 1").fetchone()
        return {"status": "ok", "db": "ok"}
    except Exception:
        raise HTTPException(status_code=503, detail="unhealthy")


# ---------------------------------------------------------------------------
# player routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/welcome")


@app.get("/welcome", response_class=HTMLResponse)
async def welcome(request: Request):
    return _render("welcome.html")


@app.get("/p/{token}", response_class=HTMLResponse)
async def player_home(request: Request, token: str):
    info = _verify(token)
    player_id = info["player_id"]
    player = db.get_player(player_id)
    if not player:
        raise HTTPException(404)

    today = date.today()
    week_start = _monday(today).isoformat()

    schedule = _get_or_generate_schedule(player_id, week_start)
    completions = db.get_completions(player_id, week_start)

    today_name = today.strftime("%A")
    today_session = None
    if schedule and schedule.sessions:
        today_session = next(
            (s for s in schedule.sessions if s.day == today_name), None
        )

    first_name = player["name"].split()[0]

    return _render("home.html",
        token=token,
        player=player,
        first_name=first_name,
        schedule=schedule,
        today_session=today_session,
        today_name=today_name,
        completions=completions,
        active="home",
    )


@app.get("/p/{token}/session/{day}", response_class=HTMLResponse)
async def player_session(request: Request, token: str, day: str):
    info = _verify(token)
    player_id = info["player_id"]
    player = db.get_player(player_id)
    if not player:
        raise HTTPException(404)

    week_start = _monday(date.today()).isoformat()
    schedule = load_schedule(player_id, week_start)
    if not schedule:
        return RedirectResponse(url=f"/p/{token}")

    session = next((s for s in schedule.sessions if s.day == day), None)
    if not session:
        raise HTTPException(404, detail="Session not found")

    completions = db.get_completions(player_id, week_start)

    return _render("session.html",
        token=token,
        player=player,
        session=session,
        day=day,
        completed=day in completions,
        active="home",
    )


@app.post("/p/{token}/complete/{day}")
async def complete_session(request: Request, token: str, day: str):
    info = _verify(token)
    player_id = info["player_id"]
    week_start = _monday(date.today()).isoformat()

    form = await request.form()
    feedback = str(form.get("feedback", ""))
    db.mark_session_complete(player_id, week_start, day, feedback)

    schedule = load_schedule(player_id, week_start)
    if schedule:
        session = next((s for s in schedule.sessions if s.day == day), None)
        if session:
            by_id = {
                ex.exercise_id: ex
                for group in (session.warm_up, session.main, session.cool_down)
                for ex in group
            }
            for key, raw in form.items():
                if not key.startswith("result_"):
                    continue
                value = str(raw).strip().replace(",", ".")
                if not value:
                    continue
                try:
                    result_value = float(value)
                except ValueError:
                    continue
                exercise_id = key[len("result_"):]
                ex = by_id.get(exercise_id)
                if ex is None:
                    continue
                db.save_exercise_result(
                    player_id=player_id,
                    week_start=week_start,
                    day=day,
                    exercise_id=exercise_id,
                    exercise_name=ex.name,
                    target=ex.target,
                    result_value=result_value,
                )

    return RedirectResponse(url=f"/p/{token}", status_code=303)


@app.get("/p/{token}/development", response_class=HTMLResponse)
async def player_development(request: Request, token: str):
    info = _verify(token)
    player_id = info["player_id"]
    player = db.get_player(player_id)
    if not player:
        raise HTTPException(404)

    profile = get_player_profile(player_id)
    gaps = identify_gaps(player_id, top_n=3)
    strengths = identify_strengths(player_id, top_n=3)
    scores = profile.get("scores", {})

    # Build dimension data with stages for template
    categories_data = []
    for cat in CATEGORIES:
        dims = CATEGORY_DIMS.get(cat, [])
        dim_data = []
        for d in dims:
            s = scores.get(d.key, {})
            score = s.get("score", 5.0)
            stage_label, stage_color = _score_to_stage(score)
            dim_data.append({
                "key": d.key,
                "name": d.name,
                "score": score,
                "stage_label": stage_label,
                "stage_color": stage_color,
                "bar_color": _bar_color(score),
                "bar_width": score * 10,
            })
        categories_data.append({
            "name": cat.title(),
            "dimensions": dim_data,
        })

    return _render("development.html",
        token=token,
        player=player,
        first_name=player["name"].split()[0],
        categories=categories_data,
        gaps=gaps,
        strengths=strengths,
        score_to_stage=_score_to_stage,
        bar_color=_bar_color,
        active="development",
    )


# ---------------------------------------------------------------------------
# coach routes (minimal — log session from any browser)
# ---------------------------------------------------------------------------

@app.get("/coach", response_class=HTMLResponse)
async def coach_dashboard(request: Request):
    players = db.get_players()
    for p in players:
        p["token"] = db.get_player_token(p["id"])
    return _render("coach.html",
        players=players,
    )
