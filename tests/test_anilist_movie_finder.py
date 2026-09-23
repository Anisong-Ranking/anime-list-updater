"""anilist_movie_finder の純粋関数(ネットワーク不要)の回帰テスト。"""
import datetime as dt

from src.anilist_movie_finder import _best_title, _to_fuzzy_int, season_label_for


def test_season_label_for_covers_all_quarters():
    assert season_label_for(2026, 1) == "2026冬アニメ"
    assert season_label_for(2026, 3) == "2026冬アニメ"
    assert season_label_for(2026, 4) == "2026春アニメ"
    assert season_label_for(2026, 6) == "2026春アニメ"
    assert season_label_for(2026, 7) == "2026夏アニメ"
    assert season_label_for(2026, 9) == "2026夏アニメ"
    assert season_label_for(2026, 10) == "2026秋アニメ"
    assert season_label_for(2026, 12) == "2026秋アニメ"


def test_season_label_matches_known_registry_examples():
    # 実際に台帳へ登録済みの劇場版の公開日から逆算した既存の書式と一致すること。
    assert season_label_for(2022, 12) == "2022秋アニメ"   # THE FIRST SLAM DUNK (2022-12-03)
    assert season_label_for(2019, 7) == "2019夏アニメ"    # 天気の子 (2019-07-19)


def test_to_fuzzy_int():
    assert _to_fuzzy_int(dt.date(2026, 9, 23)) == 20260923
    assert _to_fuzzy_int(dt.date(2026, 1, 5)) == 20260105


def test_best_title_prefers_native_then_romaji_then_english():
    assert _best_title({"native": "呪術廻戦 0", "romaji": "Jujutsu Kaisen 0", "english": "JJK0"}) == "呪術廻戦 0"
    assert _best_title({"native": "", "romaji": "Jujutsu Kaisen 0", "english": "JJK0"}) == "Jujutsu Kaisen 0"
    assert _best_title({"native": None, "romaji": None, "english": "JJK0"}) == "JJK0"
    assert _best_title({}) == ""
