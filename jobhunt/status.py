"""Status values and normalization helpers for JobHuntLedger."""

from __future__ import annotations


SUPPORTED_STATUSES = [
    "已投递",
    "待测评",
    "测评已完成",
    "待笔试",
    "笔试已完成",
    "一面待进行",
    "一面已完成",
    "一面通过",
    "二面待进行",
    "二面已完成",
    "二面通过",
    "三面待进行",
    "三面已完成",
    "HR面待进行",
    "HR面已完成",
    "offer",
    "未通过",
    "已放弃",
    "待补充",
]


STATUS_ALIASES = {
    "挂了": "未通过",
    "没过": "未通过",
    "未过": "未通过",
    "被拒": "未通过",
    "拒了": "未通过",
    "拿到 offer 了": "offer",
    "拿到offer了": "offer",
    "拿 offer 了": "offer",
    "offer了": "offer",
    "一面过了": "一面通过",
    "一面通过了": "一面通过",
    "二面过了": "二面通过",
    "二面通过了": "二面通过",
}


def normalize_status(text: str) -> str:
    normalized = text.strip()
    if normalized in SUPPORTED_STATUSES:
        return normalized
    return STATUS_ALIASES.get(normalized, normalized)


def is_supported_status(status: str) -> bool:
    return normalize_status(status) in SUPPORTED_STATUSES
