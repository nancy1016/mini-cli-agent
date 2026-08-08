"""Optional smoke tests for the real LM Studio + CLI + tool-calling path."""

from __future__ import annotations

from collections.abc import Callable
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from jobhunt.repository import create_application


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DB = PROJECT_ROOT / "data" / "jobhunt.db"
HISTORY_DIR = PROJECT_ROOT / "history"


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LMSTUDIO_E2E") != "1",
    reason="set RUN_LMSTUDIO_E2E=1 to run real LM Studio smoke tests",
)


def _require_lmstudio_env() -> None:
    if not os.environ.get("LM_STUDIO_BASE_URL"):
        pytest.skip("LM_STUDIO_BASE_URL is required for LM Studio smoke tests")
    if not os.environ.get("MINI_AGENT_MODEL"):
        pytest.skip("MINI_AGENT_MODEL is required for LM Studio smoke tests")


def _history_files() -> set[Path]:
    if not HISTORY_DIR.exists():
        return set()
    return set(HISTORY_DIR.glob("*.json"))


def _remove_new_history_files(original_history_files: set[Path]) -> None:
    for path in _history_files() - original_history_files:
        path.unlink()


def run_cli_script(
    script: str,
    timeout: int = 90,
    seed: Callable[[], None] | None = None,
) -> str:
    _require_lmstudio_env()

    DATA_DB.parent.mkdir(parents=True, exist_ok=True)
    original_history_files = _history_files()
    backup_path = DATA_DB.with_suffix(".db.smoke.bak")
    had_original_db = DATA_DB.exists()
    if had_original_db:
        shutil.copy2(DATA_DB, backup_path)

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        if DATA_DB.exists():
            DATA_DB.unlink()
        if seed is not None:
            seed()

        try:
            completed = subprocess.run(
                [sys.executable, "-X", "utf8", "main.py"],
                input=script,
                cwd=PROJECT_ROOT,
                env=env,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                check=False,
            )
            output = completed.stdout
        except subprocess.TimeoutExpired as exc:
            output = exc.stdout or ""
            if isinstance(output, bytes):
                output = output.decode("utf-8", errors="replace")
            pytest.fail(
                "LM Studio smoke test timed out. Check that LM Studio is running, "
                "the model is loaded, and the current model can finish this CLI "
                f"scenario.\n{output}"
            )
    finally:
        if DATA_DB.exists():
            DATA_DB.unlink()
        if had_original_db:
            shutil.move(str(backup_path), DATA_DB)
        elif backup_path.exists():
            backup_path.unlink()
        _remove_new_history_files(original_history_files)

    if "无法连接 LM Studio Local Server" in output:
        pytest.fail("LM Studio Local Server is not reachable; start LM Studio first")
    if completed.returncode != 0:
        pytest.fail(f"CLI smoke test failed with code {completed.returncode}\n{output}")
    return output


def _assert_fragments(output: str, fragments: list[str]) -> None:
    for fragment in fragments:
        assert fragment in output


def test_lmstudio_cli_save_official_application_smoke():
    output = run_cli_script(
        """
/load-skill jobhunt_ledger
今天在官网投递了上海百胜软件公司的软件开发岗，地点上海。
确认保存
我现在投了哪些公司？
/exit
""".lstrip()
    )

    _assert_fragments(
        output,
        [
            "已加载 skill：jobhunt_ledger",
            "已保存投递：上海百胜软件公司",
            "当前投递记录：",
            "上海百胜软件公司",
            "软件开发",
            "状态：已投递",
        ],
    )


def test_lmstudio_cli_save_application_with_link_smoke():
    output = run_cli_script(
        """
/load-skill jobhunt_ledger
今天在官网投了上海某科技公司的后端开发岗，链接 https://career.example.com/job/123，地点上海。
确认保存
我现在投了哪些公司？
/exit
""".lstrip()
    )

    _assert_fragments(
        output,
        [
            "已保存投递：上海某科技公司",
            "后端开发",
            "当前投递记录：",
            "上海某科技公司",
            "状态：已投递",
        ],
    )


def test_lmstudio_cli_save_fair_paper_application_smoke():
    output = run_cli_script(
        """
/load-skill jobhunt_ledger
今天在双选会投了陕西某软件公司的软件测试岗，工作地点西安，秋招，纸质简历投递。
确认保存
我现在投了哪些公司？
/exit
""".lstrip()
    )

    _assert_fragments(
        output,
        [
            "已保存投递：陕西某软件公司",
            "软件测试",
            "当前投递记录：",
            "陕西某软件公司",
            "状态：已投递",
        ],
    )


def test_lmstudio_cli_interview_status_and_query_with_seeded_application_smoke():
    def seed() -> None:
        create_application(
            company="西安吉利科技公司",
            position="测试开发",
            location="西安",
            apply_source="官网",
            db_path=DATA_DB,
        )

    output = run_cli_script(
        """
/load-skill jobhunt_ledger
明天下午三点，西安吉利科技公司测试开发岗一面，电话通知的。
确认保存
西安吉利科技公司一面通过了
确认更新
未来3天我有哪些面试？
/exit
""".lstrip(),
        seed=seed,
    )

    _assert_fragments(
        output,
        [
            "已保存面试：西安吉利科技公司",
            "投递状态已更新为：一面待进行",
            "已更新状态：西安吉利科技公司 -> 一面通过",
            "面试记录：",
            "西安吉利科技公司",
            "测试开发",
            "进度：一面通过",
        ],
    )


def test_lmstudio_cli_missing_info_query_with_seeded_data_smoke():
    def seed() -> None:
        create_application(
            company="信息待补充公司",
            position="软件测试",
            location="待补充",
            recruit_type="待补充",
            apply_source="待补充",
            db_path=DATA_DB,
        )

    output = run_cli_script(
        """
/load-skill jobhunt_ledger
帮我看看哪些求职记录信息没填完整。
/exit
""".lstrip(),
        seed=seed,
    )

    _assert_fragments(
        output,
        [
            "缺失信息检查结果",
            "missing",
            "location",
            "apply_source",
        ],
    )


def test_lmstudio_cli_application_status_query_with_seeded_data_smoke():
    def seed() -> None:
        create_application(
            company="西安吉利科技公司",
            position="测试开发",
            status="一面通过",
            db_path=DATA_DB,
        )

    output = run_cli_script(
        """
/load-skill jobhunt_ledger
西安吉利科技公司目前我的面试状态是什么？
/exit
""".lstrip(),
        seed=seed,
    )

    _assert_fragments(
        output,
        [
            "当前状态：",
            "西安吉利科技公司",
            "测试开发",
            "状态：一面通过",
        ],
    )


def test_lmstudio_cli_full_two_company_flow_optional():
    if os.environ.get("RUN_LMSTUDIO_FULL_E2E") != "1":
        pytest.skip("set RUN_LMSTUDIO_FULL_E2E=1 to run the long full-flow smoke")

    output = run_cli_script(
        """
/load-skill jobhunt_ledger
今天在官网投递了上海百胜软件公司的软件开发岗，地点上海。
确认保存
2026年7月18日下午5点，上海百胜软件公司开发岗要一面。
确认保存
今天在官网投递了西安吉利科技公司的测试开发岗，地点西安。
确认保存
明天下午三点，西安吉利科技公司测试开发岗一面，电话通知的。
确认保存
西安吉利科技公司一面通过了
确认更新
未来3天我有哪些面试？
未来一个月我有哪些面试？
/exit
""".lstrip(),
        timeout=240,
    )

    _assert_fragments(
        output,
        [
            "已保存投递：上海百胜软件公司",
            "已保存面试：上海百胜软件公司",
            "已保存投递：西安吉利科技公司",
            "已保存面试：西安吉利科技公司",
            "已更新状态：西安吉利科技公司",
            "面试记录：",
            "进度：一面通过",
            "进度：一面待进行",
        ],
    )
