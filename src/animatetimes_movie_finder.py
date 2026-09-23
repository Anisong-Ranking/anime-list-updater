"""アニメイトタイムズの劇場版アニメ一覧ページ(/tag/details.php?id=MOVIE_TAG_ID)から
劇場版アニメ+主題歌を抽出する。

このページはTV季アニメタグページと全く同じテーブル構造(作品名/放送形態/スケジュール/
スタッフ/主題歌)を使っているため、既存の anime_scraper.parse_anime_list() を
そのまま再利用できる(2026-09-23確認: 148件中、判明済みの主題歌も正しく取れる)。

ページ自体には「2026春アニメ」のような季節ラベルが無いので、各作品のスケジュール
欄から日付を読み取り、季節ラベルはこちらで組み立てる。リバイバル上映・周年記念上映は
タイトル/スケジュールに専用の語が入るため、それを is_rerun として扱う
(TV側の「(再放送)」検出と同じ役割)。
"""

from __future__ import annotations

import re
import zlib

from .anime_scraper import Anime, fetch_tag_page, parse_anime_list
from .season_label import season_label_for

MOVIE_TAG_ID = 4105  # https://www.animatetimes.com/tag/details.php?id=4105 「アニメ映画一覧」

_DATE_RE = re.compile(r"(\d{4})年(\d{1,2})月")
# 「先行上映」は新作の前倒し公開なので対象外(=リストに残す)。それ以外の
# 「過去作を改めて上映」系の語はここに追加する(2026-09-23: アンコール上映・
# 4Kリマスター上映で旧作のマクロス/ヤマトが残リストに混入したため追加)。
_RERUN_RE = re.compile(
    r"リバイバル|再上映|周年記念上映|公開\d+周年|アンコール上映|"
    r"\dK(リマスター|レストア)|デジタルリマスター|再上映会"
)


def _latest_date(text: str) -> tuple[int, int] | None:
    """スケジュール欄の中から一番新しい(年,月)を拾う(前編/後編・リバイバル併記対策)。"""
    matches = [(int(y), int(m)) for y, m in _DATE_RE.findall(text)]
    return max(matches) if matches else None


def _stable_movie_id(title: str) -> int:
    """AniList側(-1〜-200000程度)と衝突しない負数の疑似season_idを作る。"""
    return -1_000_000 - (zlib.crc32(title.encode("utf-8")) % 900_000)


def fetch_movies(*, timeout: int = 30) -> list[Anime]:
    html = fetch_tag_page(MOVIE_TAG_ID, timeout=timeout)
    _, raw_animes = parse_anime_list(html, MOVIE_TAG_ID)

    movies: list[Anime] = []
    for a in raw_animes:
        ym = _latest_date(a.broadcast_start)
        if ym is None:
            continue  # 日付が読み取れない(未定)ものは季節ラベルを付けられないので今回は見送り
        year, month = ym
        is_rerun = a.is_rerun or bool(_RERUN_RE.search(a.title)) or bool(_RERUN_RE.search(a.broadcast_start))
        movies.append(Anime(
            season_id=_stable_movie_id(a.title),
            season_label=season_label_for(year, month),
            order=a.order,
            title=a.title,
            detail_url=a.detail_url,
            is_rerun=is_rerun,
            broadcast_start=a.broadcast_start,
            broadcast_format=a.broadcast_format or "劇場版アニメ",
            animation_studio=a.animation_studio,
            songs=a.songs,
        ))
    return movies


if __name__ == "__main__":
    movies = fetch_movies()
    print(f"count: {len(movies)}")
    for m in movies[:10]:
        songs = ", ".join(f"{s.kind}:{s.title}/{s.artist}" for s in m.songs)
        print(f"- [{m.season_label}] {m.title} rerun={m.is_rerun} songs=[{songs}]")
