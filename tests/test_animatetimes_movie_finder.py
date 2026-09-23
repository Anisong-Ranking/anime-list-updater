"""animatetimes_movie_finder の純粋関数(ネットワーク不要)の回帰テスト。"""
from src.animatetimes_movie_finder import _latest_date, _RERUN_RE, _stable_movie_id


def test_latest_date_picks_max_of_multiple_dates():
    # 前編/後編・リバイバル併記のスケジュール欄から一番新しい年月を拾う
    assert _latest_date("前編：2026年4月24日（金） 後編：2026年9月11日（金）") == (2026, 9)
    assert _latest_date("1993年6月5日（土） 【リバイバル上映】 2026年9月4日（金） 2週間限定") == (2026, 9)
    assert _latest_date("2026年9月4日（金）") == (2026, 9)
    assert _latest_date("公開日未定") is None


def test_rerun_regex_catches_movie_specific_rerun_phrases():
    assert _RERUN_RE.search("カーズ 公開20周年記念上映")
    assert _RERUN_RE.search("獣兵衛忍風帖 リバイバル上映")
    assert _RERUN_RE.search("アイカツ！ 10th STORY ～未来への STARWAY～ アンコール上映")
    assert _RERUN_RE.search("マクロスプラス MOVIE EDITION 4Kリマスター上映")
    assert not _RERUN_RE.search("SEKIRO: NO DEFEAT")
    # 「先行上映」は新作の前倒し公開であって旧作の再上映ではないので対象外のまま
    assert not _RERUN_RE.search("左ききのエレン 1週間限定先行上映")


def test_stable_movie_id_is_negative_and_deterministic_and_avoids_anilist_range():
    id1 = _stable_movie_id("薬屋のひとりごと 亡妃の秘宝")
    id2 = _stable_movie_id("薬屋のひとりごと 亡妃の秘宝")
    assert id1 == id2
    # AniListの疑似season_id(-1 〜 -200000程度)と重ならない帯域に入っている
    assert id1 <= -1_000_000
