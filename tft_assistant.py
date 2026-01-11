import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "comp_recommendations.json")
DEFAULT_REGION = "tw2"
RIOT_API_BASE = "https://{region}.api.riotgames.com"


@dataclass
class SummonerProfile:
    name: str
    puuid: str
    summoner_id: str
    profile_icon_id: int
    summoner_level: int


@dataclass
class RankedEntry:
    tier: str
    rank: str
    league_points: int
    wins: int
    losses: int


class RiotAPIError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Teamfight Tactics 助手 - 連動 Riot 帳號並推薦陣容"
    )
    parser.add_argument("--summoner-name", help="召喚師名稱")
    parser.add_argument("--region", default=DEFAULT_REGION, help="Riot API 區域代碼")
    parser.add_argument("--api-key", help="Riot API 金鑰（或使用 RIOT_API_KEY 環境變數）")
    parser.add_argument(
        "--comps-only",
        action="store_true",
        help="只輸出陣容推薦，不查詢帳號資料",
    )
    parser.add_argument(
        "--category",
        choices=["beginner", "expert", "all"],
        default="all",
        help="陣容分類：新手推薦或高手建議",
    )
    return parser.parse_args()


def load_comp_data(path: str = DATA_PATH) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_version(version: str) -> Tuple[int, ...]:
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        return (0,)


def get_latest_patch(data: Dict[str, Any]) -> Dict[str, Any]:
    patches = data.get("patches", [])
    if not patches:
        raise RiotAPIError("目前沒有可用的陣容資料。")
    return max(patches, key=lambda item: parse_version(item.get("version", "0")))


def format_comps(patch: Dict[str, Any], category: str) -> str:
    sections = []
    version = patch.get("version", "未知")
    sections.append(f"最新版本：{version}")

    def format_list(title: str, comps: List[Dict[str, Any]]) -> None:
        sections.append(f"\n{title}")
        for index, comp in enumerate(comps, start=1):
            sections.append(
                "  {idx}. {name}｜{style}\n"
                "     主C：{carry}\n"
                "     核心棋子：{units}\n"
                "     建議：{notes}".format(
                    idx=index,
                    name=comp.get("name"),
                    style=comp.get("style"),
                    carry=comp.get("carry"),
                    units="、".join(comp.get("core_units", [])),
                    notes=comp.get("notes"),
                )
            )

    if category in ("beginner", "all"):
        format_list("新手推薦", patch.get("beginner", []))
    if category in ("expert", "all"):
        format_list("高手建議", patch.get("expert", []))

    return "\n".join(sections)


def build_headers(api_key: str) -> Dict[str, str]:
    return {"X-Riot-Token": api_key}


def request_riot(endpoint: str, api_key: str, region: str) -> Dict[str, Any]:
    url = f"{RIOT_API_BASE.format(region=region)}{endpoint}"
    response = requests.get(url, headers=build_headers(api_key), timeout=10)
    if response.status_code != 200:
        raise RiotAPIError(
            f"Riot API 呼叫失敗 ({response.status_code}): {response.text}"
        )
    return response.json()


def fetch_summoner_profile(
    summoner_name: str, api_key: str, region: str
) -> SummonerProfile:
    payload = request_riot(
        f"/tft/summoner/v1/summoners/by-name/{summoner_name}", api_key, region
    )
    return SummonerProfile(
        name=payload["name"],
        puuid=payload["puuid"],
        summoner_id=payload["id"],
        profile_icon_id=payload.get("profileIconId", 0),
        summoner_level=payload.get("summonerLevel", 0),
    )


def fetch_ranked_entries(
    summoner_id: str, api_key: str, region: str
) -> List[RankedEntry]:
    payload = request_riot(
        f"/tft/league/v1/entries/by-summoner/{summoner_id}", api_key, region
    )
    entries = []
    for entry in payload:
        entries.append(
            RankedEntry(
                tier=entry.get("tier", "UNRANKED"),
                rank=entry.get("rank", ""),
                league_points=entry.get("leaguePoints", 0),
                wins=entry.get("wins", 0),
                losses=entry.get("losses", 0),
            )
        )
    return entries


def format_profile(profile: SummonerProfile, ranked: List[RankedEntry]) -> str:
    sections = [
        "帳號資訊",
        f"  召喚師名稱：{profile.name}",
        f"  等級：{profile.summoner_level}",
    ]
    if ranked:
        sections.append("  排位：")
        for entry in ranked:
            total = entry.wins + entry.losses
            win_rate = f"{(entry.wins / total * 100):.1f}%" if total else "0%"
            sections.append(
                "    - {tier} {rank} | {lp} LP | 勝率 {win_rate} ({wins}勝/{losses}敗)".format(
                    tier=entry.tier,
                    rank=entry.rank,
                    lp=entry.league_points,
                    win_rate=win_rate,
                    wins=entry.wins,
                    losses=entry.losses,
                )
            )
    else:
        sections.append("  排位：目前沒有資料")

    return "\n".join(sections)


def main() -> None:
    args = parse_args()
    api_key = args.api_key or os.getenv("RIOT_API_KEY")

    comp_data = load_comp_data()
    latest_patch = get_latest_patch(comp_data)
    comp_output = format_comps(latest_patch, args.category)

    if args.comps_only:
        print(comp_output)
        return

    if not args.summoner_name:
        print("請提供 --summoner-name 才能查詢 Riot 帳號。", file=sys.stderr)
        print(comp_output)
        sys.exit(1)

    if not api_key:
        print("缺少 Riot API 金鑰，請設定 --api-key 或 RIOT_API_KEY。", file=sys.stderr)
        print(comp_output)
        sys.exit(1)

    try:
        profile = fetch_summoner_profile(args.summoner_name, api_key, args.region)
        ranked_entries = fetch_ranked_entries(profile.summoner_id, api_key, args.region)
    except RiotAPIError as error:
        print(str(error), file=sys.stderr)
        print(comp_output)
        sys.exit(1)

    print(format_profile(profile, ranked_entries))
    print("\n" + comp_output)
    print(f"\n資料更新時間：{datetime.utcnow().isoformat()}Z")


if __name__ == "__main__":
    main()
