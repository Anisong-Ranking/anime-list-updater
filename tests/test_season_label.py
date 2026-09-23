from src.season_label import season_label_for


def test_covers_all_quarters():
    assert season_label_for(2026, 1) == "2026冬アニメ"
    assert season_label_for(2026, 4) == "2026春アニメ"
    assert season_label_for(2026, 7) == "2026夏アニメ"
    assert season_label_for(2026, 10) == "2026秋アニメ"
