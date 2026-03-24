"""
fetch_data.py – ESPN API → data.json
Futtatás: python3 fetch_data.py
"""

import warnings
warnings.filterwarnings("ignore")

import json
from datetime import datetime, date, timedelta
from espn_api.basketball import League
from espn_api.basketball.constant import PRO_TEAM_MAP
from config import (
    LEAGUE_ID, YEAR, ESPN_S2, SWID,
    MY_TEAM_NAME, OPP_TEAM_NAME, MATCHUP_PERIOD,
    WEEK_START, WEEK_END
)

# ── Konstansok ────────────────────────────────────────────
UTC_OFFSET   = timedelta(hours=7)           # PDT = UTC-7 (késő esti PT meccsek miatt: DEN, PHO, LAL, GSW, etc.)
WEEK_START_D = date.fromisoformat(WEEK_START)
WEEK_END_D   = date.fromisoformat(WEEK_END)
WEEK_DAYS    = [WEEK_START_D + timedelta(days=i)
                for i in range((WEEK_END_D - WEEK_START_D).days + 1)]
BENCH_SLOTS  = {"BE", "IR"}
TODAY        = date.today()
REMAINING    = [d for d in WEEK_DAYS if d >= TODAY]

# PRO_TEAM_MAP: {int_id: "ABB"} → invert to {"ABB": int_id}
PRO_TEAM_ID  = {abbr: tid for tid, abbr in PRO_TEAM_MAP.items()}

# ── Helper függvények ─────────────────────────────────────

def et_date(utc_dt):
    """UTC datetime → Eastern date (EDT, UTC-4)."""
    return (utc_dt - UTC_OFFSET).date()

def games_in_range(player, days):
    """Visszaadja azokat a (date, opponent) párokat, amikor a játékos játszik a megadott napokon."""
    result = []
    for game_info in player.schedule.values():
        d = et_date(game_info["date"])
        if d in days:
            result.append({"date": d.isoformat(), "opponent": game_info.get("team", "?")})
    return sorted(result, key=lambda x: x["date"])

def games_remaining(player):
    return games_in_range(player, set(REMAINING))

def games_this_week(player):
    return games_in_range(player, set(WEEK_DAYS))

def plays_on(player, day):
    return any(g["date"] == day.isoformat() for g in games_in_range(player, {day}))

# pro_schedule-alapú game lookup szabad ügynökökhöz
_pro_schedule_cache = None

def get_pro_schedule():
    global _pro_schedule_cache
    return _pro_schedule_cache

def fa_games_in_range(pro_team_abbr, days):
    """Pro schedule alapján adja vissza a FA játékos meccsnap dátumait."""
    ps = get_pro_schedule()
    if not ps:
        return []
    team_id = PRO_TEAM_ID.get(pro_team_abbr)
    if team_id is None or team_id not in ps:
        return []
    days_set = set(days)
    result = []
    for games_list in ps[team_id].values():
        for g in (games_list if isinstance(games_list, list) else [games_list]):
            raw_ms = g.get("date")
            if not raw_ms:
                continue
            utc_dt = datetime.utcfromtimestamp(raw_ms / 1000)
            et_d   = (utc_dt - UTC_OFFSET).date()
            if et_d in days_set:
                result.append(et_d.isoformat())
    return sorted(set(result))

def player_dict(p, include_schedule=True):
    """Játékos adatait dict-be csomagolja."""
    rem_games = games_remaining(p) if include_schedule else []
    week_games = games_this_week(p) if include_schedule else []
    return {
        "name":             p.name,
        "slot":             p.lineupSlot,
        "position":         p.position,
        "injury":           p.injuryStatus or "ACTIVE",
        "plays_today":      plays_on(p, TODAY),
        "games_remaining":  rem_games,
        "games_this_week":  week_games,
        "rem_count":        len(rem_games),
        "week_count":       len(week_games),
        "avg_points":       round(p.avg_points or 0, 1),
        "total_points":     round(p.total_points or 0, 1),
    }

def lineup_status(p_dict):
    """
    ok           – aktív slot, játszik ma, egészséges
    warning      – DTD az aktív slotban
    alert        – aktív slotban de NEM játszik ma / OUT / IR
    bench_plays  – padon van, de játszik ma
    bench_idle   – padon van, nem játszik ma
    """
    slot   = p_dict["slot"]
    inj    = p_dict["injury"]
    today  = p_dict["plays_today"]
    bench  = slot in BENCH_SLOTS

    if bench:
        return "bench_plays" if today else "bench_idle"
    if inj in ("OUT", "IR", "SUSPENSION"):
        return "alert"
    if inj in ("DAY_TO_DAY", "DTD", "QUESTIONABLE"):
        return "warning"
    if not today:
        return "alert"
    return "ok"

# ── ESPN kapcsolat ────────────────────────────────────────
print("📡 ESPN API kapcsolódás...", flush=True)
league = League(league_id=LEAGUE_ID, year=YEAR, espn_s2=ESPN_S2, swid=SWID)

my_team  = next(t for t in league.teams if t.team_name == MY_TEAM_NAME)
opp_team = next(t for t in league.teams if t.team_name == OPP_TEAM_NAME)
_pro_schedule_cache = league.pro_schedule

# Box score → pontállás
box_scores = league.box_scores(MATCHUP_PERIOD)
my_box = next(
    b for b in box_scores
    if b.home_team.team_name == MY_TEAM_NAME or b.away_team.team_name == MY_TEAM_NAME
)
if my_box.home_team.team_name == MY_TEAM_NAME:
    my_score, opp_score = my_box.home_score, my_box.away_score
else:
    my_score, opp_score = my_box.away_score, my_box.home_score

print(f"   Állás: {MY_TEAM_NAME} {my_score:.0f} – {opp_score:.0f} {OPP_TEAM_NAME}")

# ── Rosterek ─────────────────────────────────────────────
print("👥 Rosterek feldolgozása...", flush=True)

my_roster  = [player_dict(p) for p in my_team.roster]
opp_roster = [player_dict(p) for p in opp_team.roster]

for p in my_roster:
    p["status"] = lineup_status(p)
for p in opp_roster:
    p["status"] = lineup_status(p)

my_active  = [p for p in my_roster  if p["slot"] not in BENCH_SLOTS]
my_bench   = [p for p in my_roster  if p["slot"] in BENCH_SLOTS and p["slot"] != "IR"]
opp_active = [p for p in opp_roster if p["slot"] not in BENCH_SLOTS]

# ── Napi játékosszám ──────────────────────────────────────
# A player_dict-ben tárolt games_this_week lista alapján számolunk
daily_counts = []
for day in WEEK_DAYS:
    day_iso = day.isoformat()
    mc = sum(1 for p in my_active  if any(g["date"] == day_iso for g in p["games_this_week"]))
    oc = sum(1 for p in opp_active if any(g["date"] == day_iso for g in p["games_this_week"]))
    daily_counts.append({
        "date":     day.isoformat(),
        "label":    day.strftime("%m.%d %a"),
        "my_count": mc,
        "opp_count": oc,
        "diff":     mc - oc,
        "is_today": day == TODAY,
        "is_past":  day < TODAY,
    })

rem_my  = sum(d["my_count"]  for d in daily_counts if not d["is_past"])
rem_opp = sum(d["opp_count"] for d in daily_counts if not d["is_past"])

# ── Lineup javaslatok ─────────────────────────────────────
lineup_actions = []

for p in my_active:
    status = p["status"]

    if status == "alert" and p["injury"] in ("OUT", "IR", "SUSPENSION"):
        # Csak valódi kiesés esetén kell csere
        candidates = sorted(
            [b for b in my_bench
             if b["injury"] == "ACTIVE" and b["rem_count"] > 0],
            key=lambda x: (-x["plays_today"], -x["rem_count"], -x["avg_points"])
        )
        if candidates:
            best = candidates[0]
            lineup_actions.append({
                "type":       "swap_required",
                "player_out": p["name"],
                "slot":       p["slot"],
                "player_in":  best["name"],
                "reason":     (
                    best["name"] + " (pad) " +
                    ("játszik ma" if best["plays_today"] else f"{best['rem_count']} meccs van még") +
                    f", avg: {best['avg_points']:.1f} pts"
                ),
                "injury_out": p["injury"],
            })
        else:
            lineup_actions.append({
                "type":       "no_replacement",
                "player_out": p["name"],
                "slot":       p["slot"],
                "reason":     "Nincs elérhető csere a paddról",
                "injury_out": p["injury"],
            })

    elif status == "warning":
        lineup_actions.append({
            "type":   "dtd_watch",
            "player": p["name"],
            "slot":   p["slot"],
            "reason": "DTD – ellenőrizd az ESPN-en meccsnap reggelén!",
        })

# Pad: játszik ma de bent ül → bench_opportunity
bench_playing_today = [p for p in my_bench if p["plays_today"] and p["injury"] == "ACTIVE"]
active_not_playing  = [a for a in my_active if not a["plays_today"] and a["status"] == "alert"]

for p in bench_playing_today:
    swap_target = active_not_playing[0]["name"] if active_not_playing else None
    lineup_actions.append({
        "type":       "bench_opportunity",
        "player":     p["name"],
        "avg_points": p["avg_points"],
        "rem_count":  p["rem_count"],
        "reason":     (
            f"{p['name']} ma játszik (avg {p['avg_points']:.1f} pts, {p['rem_count']} meccs hátra) de a padon ül"
            + (f" – felválthatja: {swap_target}" if swap_target else "")
        ),
    })

# ── Alertek ───────────────────────────────────────────────
alerts = []

# Piros: aktív slotban OUT/IR/SUSPENSION játékos
out_active = [p for p in my_active if p["injury"] in ("OUT", "IR", "SUSPENSION")]
if out_active:
    names = ", ".join(p["name"] for p in out_active)
    alerts.append({"level": "red", "message": f"Aktív slotban kiesett játékos: {names} – azonnali csere!"})

# Narancs: DTD aktív slotban
dtd_active = [p for p in my_active if p["status"] == "warning"]
if dtd_active:
    names = ", ".join(p["name"] for p in dtd_active)
    alerts.append({"level": "orange", "message": f"DTD az aktív lineup-ban: {names} – döntés szükséges!"})

# Piros: az ellenfélnek több aktív játékosa van ma
today_my  = sum(1 for p in my_active  if p["plays_today"])
today_opp = sum(1 for p in opp_active if p["plays_today"])
if today_opp > today_my:
    alerts.append({"level": "red",
                   "message": f"Ma az ellenfélnek több aktív játékosa van: {today_opp} vs {today_my} – töltsd be a lyukat!"})

# Narancs: pad játékos játszik ma
bench_plays_today = [p for p in my_bench if p["plays_today"] and p["injury"] == "ACTIVE"]
if bench_plays_today:
    names = ", ".join(p["name"] for p in bench_plays_today)
    alerts.append({"level": "orange", "message": f"Padon ül, de ma játszik: {names}"})

# ── Free Agent elemzés ────────────────────────────────────
print("🔍 Free agent elemzés...", flush=True)

fa_data = {"add_now": [], "one_day": [], "skip": []}

try:
    free_agents = league.free_agents(size=40)

    # Leggyengébb pad játékos (legkevesebb hátralévő meccs, nem-IR)
    droppable_bench = sorted(my_bench, key=lambda x: (x["rem_count"], x["avg_points"]))

    for fa in free_agents:
        fa_rem_dates = fa_games_in_range(fa.proTeam, REMAINING)
        fa_rem_count = len(fa_rem_dates)
        fa_today = TODAY.isoformat() in fa_rem_dates

        if fa_rem_count == 0:
            continue

        # Legjobb drop jelölt: legkevesebb hátralévő meccs a padról
        drop = droppable_bench[0] if droppable_bench else None
        drop_rem_count = drop["rem_count"] if drop else 0
        net = fa_rem_count - drop_rem_count

        entry = {
            "name":          fa.name,
            "position":      fa.position,
            "pro_team":      fa.proTeam,
            "avg_points":    round(fa.avg_points or 0, 1),
            "injury":        fa.injuryStatus or "ACTIVE",
            "plays_today":   fa_today,
            "games_remaining": fa_rem_count,
            "rem_game_dates": fa_rem_dates,
            "drop_player":   drop["name"] if drop else "–",
            "drop_rem_count": drop_rem_count,
            "net_games":     net,
            "reasoning":     "",
        }

        if fa.injuryStatus in ("OUT", "IR"):
            continue

        if net > 0:
            entry["decision"] = "AZONNAL"
            entry["reasoning"] = (
                f"{fa.name} – {fa_rem_count} meccs hátra vs. ejtendő "
                f"{drop['name'] if drop else '–'} {drop_rem_count} meccse. "
                f"NET: +{net} games. Avg: {entry['avg_points']:.1f} pts."
            )
            fa_data["add_now"].append(entry)

        elif fa_today and net >= 0:
            entry["decision"] = "CSAK MA"
            entry["reasoning"] = (
                f"{fa.name} – csak ma játszik, töltse be a lyukat. "
                f"Holnap ejtheted. Avg: {entry['avg_points']:.1f} pts."
            )
            fa_data["one_day"].append(entry)

        elif net < 0 and fa_rem_count >= 2:
            drop_name = drop["name"] if drop else "–"
            entry["decision"] = "NEM"
            entry["reasoning"] = (
                f"{fa.name} – {fa_rem_count} meccs vs. ejtendő "
                f"{drop_name} {drop_rem_count} meccse. "
                f"NET: {net} games. Nem éri meg."
            )
            fa_data["skip"].append(entry)

    # Rendezés: avg_points csökkenő
    fa_data["add_now"]  = sorted(fa_data["add_now"],  key=lambda x: -x["avg_points"])[:8]
    fa_data["one_day"]  = sorted(fa_data["one_day"],  key=lambda x: -x["avg_points"])[:5]
    fa_data["skip"]     = sorted(fa_data["skip"],     key=lambda x: -x["avg_points"])[:5]

    print(f"   FA: {len(fa_data['add_now'])} azonnal, {len(fa_data['one_day'])} csak ma, {len(fa_data['skip'])} nem érdemes")

except Exception as e:
    print(f"   ⚠️ Free agent lekérés sikertelen: {e}")
    fa_data = {"add_now": [], "one_day": [], "skip": [], "error": str(e)}

# ── Predikció modul (6A–6C) ───────────────────────────────
diff      = my_score - opp_score
days_left = len([d for d in WEEK_DAYS if d > TODAY])

# 6B: Játékos-szintű projekció
def player_projections(players):
    return sorted([
        {
            "name":       p["name"],
            "slot":       p["slot"],
            "avg_points": p["avg_points"],
            "rem_count":  p["rem_count"],
            "projected":  round(p["avg_points"] * p["rem_count"], 1),
            "is_dtd":     p["injury"] in ("DAY_TO_DAY", "DTD", "QUESTIONABLE"),
        }
        for p in players
    ], key=lambda x: -x["projected"])

my_proj  = player_projections(my_active)
opp_proj = player_projections(opp_active)

my_proj_total  = round(sum(p["projected"] for p in my_proj),  1)
opp_proj_total = round(sum(p["projected"] for p in opp_proj), 1)
my_dtd_loss    = round(sum(p["projected"] for p in my_proj  if p["is_dtd"]), 1)
opp_dtd_loss   = round(sum(p["projected"] for p in opp_proj if p["is_dtd"]), 1)

# 6C: Három szcenárió
# Best:     én teli játszik, ők DTD-jei kiesnek
# Worst:    az én DTD-jeim kiesnek, ők teli játszanak
# Expected: DTD 50% súly
best_diff     = round(diff + my_proj_total               - (opp_proj_total - opp_dtd_loss), 1)
worst_diff    = round(diff + (my_proj_total - my_dtd_loss) - opp_proj_total,                 1)
expected_diff = round(diff + (my_proj_total - 0.5 * my_dtd_loss)
                           - (opp_proj_total - 0.5 * opp_dtd_loss),                          1)

def scenario_label(d):
    if d > 30:  return "GYŐZELEM"
    if d >= 0:  return "SZOROS"
    return "VESZÉLY"

# 6A: Buffer
safety        = round(diff / max(days_left, 1), 1) if days_left > 0 else diff
buffer_level  = "green" if safety >= 15 else ("yellow" if safety >= 0 else "red")

prediction = {
    "buffer": {
        "value":       safety,
        "level":       buffer_level,
        "days_left":   days_left,
        "current_lead": round(diff, 1),
        "interpretation": (
            f"Az ellenfél naponta {abs(safety):.1f} ponttal termelhet "
            + ("többet és te még mindig nyersz." if safety >= 0 else "– te már veszítesz!")
        ),
    },
    "my_projections":  my_proj,
    "opp_projections": opp_proj,
    "team_totals": {
        "my_proj_remaining":  my_proj_total,
        "opp_proj_remaining": opp_proj_total,
        "my_dtd_loss":        my_dtd_loss,
        "opp_dtd_loss":       opp_dtd_loss,
        "proj_diff":          round(my_proj_total - opp_proj_total, 1),
    },
    "scenarios": {
        "best":     {"diff": best_diff,     "label": scenario_label(best_diff)},
        "expected": {"diff": expected_diff, "label": scenario_label(expected_diff)},
        "worst":    {"diff": worst_diff,    "label": scenario_label(worst_diff)},
    },
    "current_lead": round(diff, 1),
}

# ── Összeállítás ──────────────────────────────────────────
data = {
    "generated_at":   datetime.now().strftime("%Y.%m.%d %H:%M"),
    "today":          TODAY.isoformat(),
    "week_start":     WEEK_START,
    "week_end":       WEEK_END,
    "days_left":      days_left,
    "matchup_period": MATCHUP_PERIOD,

    "scoreboard": {
        "my_team":      MY_TEAM_NAME,
        "opp_team":     OPP_TEAM_NAME,
        "my_score":     my_score,
        "opp_score":    opp_score,
        "diff":         round(diff, 1),
        "leading":      diff > 0,
        "safety_buffer": safety,
        "today_my_players":  today_my,
        "today_opp_players": today_opp,
    },

    "prediction": prediction,

    "alerts": alerts,

    "my_roster": {
        "active": sorted(my_active,  key=lambda x: x["slot"]),
        "bench":  sorted(my_bench,   key=lambda x: (-x["plays_today"], -x["rem_count"])),
    },
    "opp_roster": {
        "active": sorted(opp_active, key=lambda x: x["slot"]),
    },

    "daily_counts": daily_counts,
    "remaining_totals": {
        "my_total":  rem_my,
        "opp_total": rem_opp,
        "diff":      rem_my - rem_opp,
    },

    "lineup_actions": lineup_actions,
    "free_agents":    fa_data,
}

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✅ data.json mentve – {len(alerts)} alert, {len(lineup_actions)} lineup akció")
