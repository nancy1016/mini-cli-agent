from jobhunt.status import (
    STATUS_ALIASES,
    SUPPORTED_STATUSES,
    is_supported_status,
    normalize_status,
)


def test_supported_statuses_include_v1_values():
    assert "已投递" in SUPPORTED_STATUSES
    assert "一面通过" in SUPPORTED_STATUSES
    assert "二面通过" in SUPPORTED_STATUSES
    assert "offer" in SUPPORTED_STATUSES
    assert "待补充" in SUPPORTED_STATUSES


def test_status_aliases_normalize_simple_natural_language_values():
    assert STATUS_ALIASES["挂了"] == "未通过"
    assert normalize_status("挂了") == "未通过"
    assert normalize_status("没过") == "未通过"
    assert normalize_status("拿到 offer 了") == "offer"
    assert normalize_status("一面过了") == "一面通过"
    assert normalize_status("二面过了") == "二面通过"


def test_supported_status_keeps_stable():
    assert normalize_status(" 已投递 ") == "已投递"
    assert normalize_status("一面通过") == "一面通过"
    assert is_supported_status("一面过了") is True


def test_unknown_status_returns_cleaned_original_text():
    assert normalize_status("  等结果中  ") == "等结果中"
    assert is_supported_status("等结果中") is False
