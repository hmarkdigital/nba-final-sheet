from espn_api.basketball import League

LEAGUE_ID = 720354916
YEAR = 2026
ESPN_S2 = "AEAup6laSabczFo%2Fdz2ss0bkputxJFJOF3oN1N8WoLODWipOBG%2BjekKymxgF0T8DJfC%2FSEQ%2F9C2gtTYcfHLuLvcWm6gAHsClsn5xHaSNL16VryIN6LDUcAGeajecLM4nD2BAGAxATJE8Fx%2Fx3g2e0xckWqobgqtqRKh34ddEfHD9%2FAooycyYSR9qQJxtAg%2BCnKHeM9YhLBeAZoQjJeWkYUTK2dd71%2Fa10yqOKKVbvas5MBaDuGUiBuz7QoaEIv%2BVw5YwyOQD%2F%2FDbxuDEH9bFNwzA%2Bu5hTFyS1bMG%2BsevkMUURA%3D%3D"
SWID = "{4C9B1C82-F799-4C15-8D5A-B9012CF2C6C0}"

league = League(league_id=LEAGUE_ID, year=YEAR, espn_s2=ESPN_S2, swid=SWID)

print(f"Liga neve: {league.settings.name}")
print(f"Csapatok száma: {len(league.teams)}")
print()
print("Csapatok:")
for team in league.teams:
    print(f"  {team.team_name} | {team.wins}W-{team.losses}L | {team.points_for:.1f} pts")
