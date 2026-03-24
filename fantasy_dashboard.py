"""
BUG NBA LEAGUE – Fantasy Basketball Dashboard
Los Angyalfold döntős elemzés
"""

import warnings
warnings.filterwarnings("ignore")

from espn_api.basketball import League
from datetime import datetime, date, timedelta

# --- Konfiguráció ---
ESPN_S2 = "AEAup6laSabczFo%2Fdz2ss0bkputxJFJOF3oN1N8WoLODWipOBG%2BjekKymxgF0T8DJfC%2FSEQ%2F9C2gtTYcfHLuLvcWm6gAHsClsn5xHaSNL16VryIN6LDUcAGeajecLM4nD2BAGAxATJE8Fx%2Fx3g2e0xckWqobgqtqRKh34ddEfHD9%2FAooycyYSR9qQJxtAg%2BCnKHeM9YhLBeAZoQjJeWkYUTK2dd71%2Fa10yqOKKVbvas5MBaDuGUiBuz7QoaEIv%2BVw5YwyOQD%2F%2FDbxuDEH9bFNwzA%2Bu5hTFyS1bMG%2BsevkMUURA%3D%3D"
SWID = "{4C9B1C82-F799-4C15-8D5A-B9012CF2C6C0}"
MY_TEAM_NAME = "Los Angyalfold"
OPP_TEAM_NAME = "Team avenGER"
MATCHUP_PERIOD = 22

# Döntős hét (márc. 23–29.), Eastern idő szerint
WEEK_DAYS = [date(2026, 3, 23) + timedelta(days=i) for i in range(7)]
# NBA meccsek US Eastern (EDT = UTC-4)
UTC_OFFSET = timedelta(hours=4)

BENCH_SLOTS = {"BE", "IR"}

# --- Kapcsolat ---
print("Betöltés...", flush=True)
league = League(league_id=720354916, year=2026, espn_s2=ESPN_S2, swid=SWID)

my_team  = next(t for t in league.teams if t.team_name == MY_TEAM_NAME)
opp_team = next(t for t in league.teams if t.team_name == OPP_TEAM_NAME)

# Box score → pontszámok
box_scores = league.box_scores(MATCHUP_PERIOD)
my_box = next(
    b for b in box_scores
    if b.home_team.team_name == MY_TEAM_NAME or b.away_team.team_name == MY_TEAM_NAME
)
if my_box.home_team.team_name == MY_TEAM_NAME:
    my_score, opp_score = my_box.home_score, my_box.away_score
else:
    my_score, opp_score = my_box.away_score, my_box.home_score

# Roster → slot pozíció + sérülés + ütemterv
my_roster  = my_team.roster
opp_roster = opp_team.roster

my_active  = [p for p in my_roster  if p.lineupSlot not in BENCH_SLOTS]
my_bench   = [p for p in my_roster  if p.lineupSlot in BENCH_SLOTS]
opp_active = [p for p in opp_roster if p.lineupSlot not in BENCH_SLOTS]

# --- Helper függvények ---

def et_game_date(utc_dt):
    return (utc_dt - UTC_OFFSET).date()

def games_this_week(player):
    return sorted(
        et_game_date(g["date"])
        for g in player.schedule.values()
        if et_game_date(g["date"]) in WEEK_DAYS
    )

def injury_icon(status):
    return {
        "ACTIVE":       "✅",
        "DAY_TO_DAY":   "⚠️  DTD",
        "DTD":          "⚠️  DTD",
        "OUT":          "🚫 OUT",
        "QUESTIONABLE": "❓  Q",
        "PROBABLE":     "🟡 PROB",
        "IR":           "🏥 IR",
        "SUSPENSION":   "❌  SUSP",
    }.get(status, status or "–")

# ============================================================
today = date.today()

print()
print("=" * 62)
print(f"  🏀 BUG NBA LEAGUE – DÖNTŐ (Matchup Period {MATCHUP_PERIOD})")
print("=" * 62)

# --- 1. ÁLLÁS ---
diff = my_score - opp_score
diff_str = f"+{diff:.1f}" if diff >= 0 else f"{diff:.1f}"
leader = "TE VEZETSZ 🟢" if diff > 0 else ("DÖNTETLEN" if diff == 0 else "ELLENFÉL VEZET 🔴")
print(f"\n📊 JELENLEGI ÁLLÁS")
print(f"  {MY_TEAM_NAME:<28} {my_score:>7.1f} pts")
print(f"  {OPP_TEAM_NAME:<28} {opp_score:>7.1f} pts")
print(f"  Különbség: {diff_str} pont  –  {leader}")

# --- 2. SÉRÜLÉSJELENTÉS ---
print(f"\n🏥 SÉRÜLÉSJELENTÉS – {MY_TEAM_NAME}")
all_injured = [p for p in my_roster if p.injuryStatus not in ("ACTIVE", None)]
if all_injured:
    print(f"  {'Játékos':<26} {'Slot':<6} {'Státusz'}")
    print(f"  {'-'*50}")
    for p in sorted(all_injured, key=lambda x: x.lineupSlot in BENCH_SLOTS):
        bench_tag = " (pad)" if p.lineupSlot in BENCH_SLOTS else " (AKTÍV)"
        print(f"  {p.name:<26} {p.lineupSlot:<6} {injury_icon(p.injuryStatus)}{bench_tag}")
else:
    print("  Mindenki egészséges ✅")

# --- 3. NAPI JÁTÉKOSSZÁM ---
print(f"\n📅 NAPI JÁTÉKOSSZÁM (Eastern idő) – márc. 23–29.")
print(f"  {'Nap':<13} {'Los Angyalfold':>15} {'avenGER':>9} {'Különbség':>11}")
print(f"  {'-'*50}")

weekly_my = 0; weekly_opp = 0
for day in WEEK_DAYS:
    mc  = sum(1 for p in my_active  if day in games_this_week(p))
    oc  = sum(1 for p in opp_active if day in games_this_week(p))
    weekly_my += mc; weekly_opp += oc
    d = mc - oc
    icon   = "✅" if d > 0 else ("❌" if d < 0 else "➡️")
    marker = " ◀ MA" if day == today else (" (lezárult)" if day < today else "")
    print(f"  {day.strftime('%m.%d %a'):<13} {mc:>15} {oc:>9} {d:>+8}  {icon}{marker}")

print(f"  {'-'*50}")
print(f"  {'ÖSSZESEN':<13} {weekly_my:>15} {weekly_opp:>9} {(weekly_my-weekly_opp):>+8}")

# --- 4. MAI LINEUP ---
print(f"\n🏟️  MAI AKTÍV LINEUP ({today.strftime('%m.%d %A')})")

def print_roster(players, label):
    print(f"\n  {label}:")
    active_today = [p for p in players if today in games_this_week(p)]
    inactive_today = [p for p in players if today not in games_this_week(p)]

    print(f"  {'Slot':<5} {'Játékos':<26} {'Státusz':<13} Ma")
    print(f"  {'-'*58}")
    for p in sorted(active_today, key=lambda x: x.lineupSlot) + \
             sorted(inactive_today, key=lambda x: x.lineupSlot):
        plays = today in games_this_week(p)
        game_str = "🟢 JÁTSZIK" if plays else "⬜"
        inj = injury_icon(p.injuryStatus)
        print(f"  {p.lineupSlot:<5} {p.name:<26} {inj:<13} {game_str}")

print_roster(my_active,  MY_TEAM_NAME)
print_roster(opp_active, OPP_TEAM_NAME)

# --- 5. HÁTRALÉVŐ MECCSEK (ma-tól) ---
remaining_days = [d for d in WEEK_DAYS if d >= today]
print(f"\n📆 HÁTRALÉVŐ JÁTÉKOSSZÁM (ma–márc. 29.)")
print(f"  {'Nap':<13} {'Los Angyalfold':>15} {'avenGER':>9} {'Különbség':>11}")
print(f"  {'-'*50}")
rem_my = 0; rem_opp = 0
for day in remaining_days:
    mc = sum(1 for p in my_active  if day in games_this_week(p))
    oc = sum(1 for p in opp_active if day in games_this_week(p))
    rem_my += mc; rem_opp += oc
    d = mc - oc
    icon = "✅" if d > 0 else ("❌" if d < 0 else "➡️")
    marker = " ◀ MA" if day == today else ""
    print(f"  {day.strftime('%m.%d %a'):<13} {mc:>15} {oc:>9} {d:>+8}  {icon}{marker}")
print(f"  {'-'*50}")
print(f"  {'ÖSSZESEN':<13} {rem_my:>15} {rem_opp:>9} {(rem_my-rem_opp):>+8}")

# --- 6. LINEUP JAVASLATOK ---
print(f"\n💡 LINEUP JAVASLATOK")
suggestions = []

for p in my_active:
    status = p.injuryStatus
    if status in ("OUT", "IR", "SUSPENSION"):
        remaining_games = sum(1 for d in remaining_days if d in games_this_week(p))
        candidates = [
            b for b in my_bench
            if b.injuryStatus == "ACTIVE"
            and b.lineupSlot != "IR"
            and any(d in games_this_week(b) for d in remaining_days)
        ]
        if candidates:
            best = max(candidates, key=lambda x: x.avg_points)
            suggestions.append(
                f"  🔄 {p.name} ({p.lineupSlot}) → csere: "
                f"{best.name} ({best.avg_points:.1f} avg, "
                f"{sum(1 for d in remaining_days if d in games_this_week(best))} meccs még)"
            )
        else:
            suggestions.append(f"  ⚠️  {p.name} ({p.lineupSlot}) kiesett, nincs csere")

    elif status in ("DAY_TO_DAY", "DTD"):
        suggestions.append(
            f"  ⚠️  {p.name} ({p.lineupSlot}) DTD – nézd meg meccsnap reggelén az ESPN-en!"
        )

# Padról felülvizsgálható játékosok
for p in my_bench:
    if p.injuryStatus == "ACTIVE" and p.lineupSlot != "IR":
        rem_games = sum(1 for d in remaining_days if d in games_this_week(p))
        if rem_games >= 2:
            suggestions.append(
                f"  🪑 {p.name} (BE) – még {rem_games} meccs a héten ({p.avg_points:.1f} avg)"
            )

if not suggestions:
    print("  Minden rendben, nincs szükséges beavatkozás ✅")
else:
    for s in suggestions:
        print(s)

print()
print("=" * 62)
print(f"  Frissítve: {datetime.now().strftime('%Y.%m.%d %H:%M')}")
print("=" * 62)
