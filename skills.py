"""
Skill 管理。

第一版的 Skill 就是 Markdown prompt。
加载后会作为 system message 注入给模型。
"""

from __future__ import annotations

from config import SKILLS_DIR


def ensure_skills_dir() -> None:
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)


def list_skills() -> list[str]:
    ensure_skills_dir()
    return sorted([p.stem for p in SKILLS_DIR.glob("*.md")])


def load_skill(name: str) -> str:
    ensure_skills_dir()

    clean_name = name.strip()

    if not clean_name:
        raise ValueError("Skill 名称不能为空")

    if clean_name.endswith(".md"):
        filename = clean_name
    else:
        filename = f"{clean_name}.md"

    # 只允许加载 skills 目录下的一级 markdown 文件
    if "/" in filename or "\\" in filename:
        raise ValueError("Skill 名称不能包含路径分隔符")

    path = SKILLS_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"Skill 不存在: {clean_name}")

    return path.read_text(encoding="utf-8")
