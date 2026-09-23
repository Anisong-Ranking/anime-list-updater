"""AniList GraphQL(無料・APIキー不要)で日本の劇場版アニメを取得する。

アニメイトタイムズの季アニメタグページはTV放送シリーズだけを掲載しており、
劇場版(呪術廻戦0、チェンソーマン レゼ篇 等)は対象外(2026-09-23 実測で確認)。
本モジュールはその穴を埋めるため、AniListから直近〜今後の日本産劇場版を
別途取得し、既存のTV一覧と同じ Anime データクラスへ変換する。

season_id は既存のアニメイトタイムズ タグID(正の整数, 数千番台)と衝突しない
よう、AniListのメディアIDを負数にして使う。
"""

from __future__ import annotations

import datetime as dt
from typing import Iterable

import requests

from .anime_scraper import Anime
from .season_label import season_label_for

ANILIST_URL = "https://graphql.anilist.co"
USER_AGENT = "anisong-ranking-anime-list-updater/1.0 (+https://anisong-ranking.com)"

_QUERY = """
query ($from: FuzzyDateInt, $to: FuzzyDateInt, $page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    pageInfo { hasNextPage }
    media(
      type: ANIME
      format: MOVIE
      countryOfOrigin: "JP"
      startDate_greater: $from
      startDate_lesser: $to
      sort: START_DATE
      isAdult: false
    ) {
      id
      title { romaji native english }
      startDate { year month day }
      studios(isMain: true) { nodes { name } }
      siteUrl
    }
  }
}
"""

def _to_fuzzy_int(d: dt.date) -> int:
    return d.year * 10000 + d.month * 100 + d.day


def _best_title(title_obj: dict) -> str:
    return (title_obj.get("native") or title_obj.get("romaji") or title_obj.get("english") or "").strip()


def fetch_movies(*, days_back: int = 60, days_forward: int = 200,
                  today: dt.date | None = None, timeout: int = 30) -> list[Anime]:
    """直近days_back日〜今後days_forward日に公開される日本産劇場版アニメを取得する。"""
    today = today or dt.date.today()
    date_from = _to_fuzzy_int(today - dt.timedelta(days=days_back))
    date_to = _to_fuzzy_int(today + dt.timedelta(days=days_forward))

    animes: list[Anime] = []
    page = 1
    while True:
        resp = requests.post(
            ANILIST_URL,
            json={"query": _QUERY, "variables": {
                "from": date_from, "to": date_to, "page": page, "perPage": 50,
            }},
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
        )
        resp.raise_for_status()
        payload = resp.json()
        page_data = payload["data"]["Page"]
        for m in page_data["media"]:
            title = _best_title(m["title"])
            if not title:
                continue
            start = m.get("startDate") or {}
            year, month = start.get("year"), start.get("month")
            if not year or not month:
                continue  # 公開日未確定のものは季節ラベルを付けられないので後日再取得に任せる
            studios = ", ".join(n["name"] for n in (m.get("studios") or {}).get("nodes", []) if n.get("name"))
            animes.append(Anime(
                season_id=-int(m["id"]),
                season_label=season_label_for(year, month),
                order=0,
                title=title,
                detail_url=m.get("siteUrl") or "",
                is_rerun=False,
                broadcast_start=f"{year}年{month}月" + (f"{start['day']}日" if start.get("day") else ""),
                broadcast_format="劇場版",
                animation_studio=studios,
                songs=[],
            ))
        if not page_data["pageInfo"]["hasNextPage"]:
            break
        page += 1
    return animes


def dedupe_against(animes: Iterable[Anime], existing_titles: set[str]) -> list[Anime]:
    """既存のタイトル集合(TV一覧など)と重複するものを除く(同名OVA等の混入防止に使う想定)。"""
    return [a for a in animes if a.title not in existing_titles]
