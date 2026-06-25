#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0
"""
GitHub 下载 — 从远程仓库拉取并覆盖本地工作区。

⚠️ 危险操作：会丢弃本地未提交更改与未跟踪文件。

用法:
    python github_download.py
    python github_download.py --yes       # 跳过确认（慎用）
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent

DEFAULT_REMOTE_SSH = "git@github.com:wxhwwla/my-token.git"
DEFAULT_BRANCH = "main"

# 须完整输入该词才会执行 reset --hard / clean -fd
CONFIRM_PHRASE = "覆盖本地"

_MAX_LISTED_CHANGES = 30


def run_git(
    args: list[str],
    *,
    check: bool = True,
    capture_output: bool = False,
    timeout: int | None = None,
) -> tuple[int, str, str]:
    """执行 git 命令并返回 (returncode, stdout, stderr)。"""
    try:
        if capture_output:
            proc = subprocess.run(
                ["git", *args],
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                check=check,
                timeout=timeout,
            )
            return proc.returncode, proc.stdout or "", proc.stderr or ""

        proc = subprocess.run(["git", *args], check=check, timeout=timeout)
        return proc.returncode, "", ""

    except subprocess.CalledProcessError:
        print(f"[错误] Git 命令失败: git {' '.join(args)}")
        raise

    except FileNotFoundError:
        print("[错误] 未找到 git")
        sys.exit(1)


def setup_git_repo() -> None:
    """初始化/检查 git 仓库，配置 remote 和分支。"""
    os.chdir(_REPO_ROOT)

    if not os.path.isdir(".git"):
        print("[信息] 初始化 Git 仓库")
        run_git(["init"])
        run_git(["checkout", "-b", DEFAULT_BRANCH])

    _, stdout, _ = run_git(["remote", "-v"], capture_output=True)

    if "origin" not in stdout:
        run_git(["remote", "add", "origin", DEFAULT_REMOTE_SSH])
    else:
        run_git(["remote", "set-url", "origin", DEFAULT_REMOTE_SSH])

    _, cur, _ = run_git(["branch", "--show-current"], capture_output=True)
    if cur.strip() != DEFAULT_BRANCH:
        code, _, _ = run_git(["checkout", DEFAULT_BRANCH], check=False, capture_output=True)
        if code != 0:
            run_git(["checkout", "-b", DEFAULT_BRANCH])


def _print_pending_changes(porcelain: str) -> None:
    """打印工作区中未提交的变更列表。"""
    lines = [ln for ln in porcelain.splitlines() if ln.strip()]
    if not lines:
        print("[信息] 工作区无已跟踪文件的修改（仍将执行 clean -fd 删除未跟踪文件）")
        return

    print(f"[警告] 检测到 {len(lines)} 项本地变更（未提交或将丢失）：")
    for line in lines[:_MAX_LISTED_CHANGES]:
        print(f"  {line}")
    if len(lines) > _MAX_LISTED_CHANGES:
        print(f"  ... 另有 {len(lines) - _MAX_LISTED_CHANGES} 项未列出")


def require_user_confirm(*, skip: bool = False) -> bool:
    """要求用户输入 CONFIRM_PHRASE 后才允许继续。"""
    if skip:
        print("[警告] 已使用 --yes，跳过人工确认")
        return True

    os.chdir(_REPO_ROOT)

    _, porcelain, _ = run_git(
        ["-c", "core.quotepath=false", "status", "--porcelain"],
        capture_output=True,
    )

    print("=" * 60)
    print("  [危险] 本操作将：")
    print("    1. git fetch origin")
    print(f"    2. git reset --hard origin/{DEFAULT_BRANCH}")
    print("    3. git clean -fd（删除未跟踪的文件与目录）")
    print("  本地未推送的提交、未提交修改、未跟踪文件均可能丢失。")
    print("=" * 60)

    _print_pending_changes(porcelain)

    print()
    print(f"  若确定继续，请完整输入: {CONFIRM_PHRASE}")
    print("  直接回车或输入其他内容将取消。")

    try:
        typed = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  [已取消]")
        return False

    if typed != CONFIRM_PHRASE:
        print(f"  [已取消] 未输入「{CONFIRM_PHRASE}」，本地未改动。")
        return False

    print("  [信息] 确认通过，开始与远程对齐…")
    return True


def force_pull() -> bool:
    """执行 git fetch + reset --hard + clean -fd 与远程对齐。"""
    os.chdir(_REPO_ROOT)
    print("[信息] 强制与远程 main 对齐（本地未提交更改将丢失）")

    run_git(["fetch", "origin"], timeout=300)

    code, _, stderr = run_git(
        ["reset", "--hard", f"origin/{DEFAULT_BRANCH}"],
        check=False,
        capture_output=True,
    )
    if code != 0:
        print(f"[错误] reset 失败: {stderr.strip()}")
        return False

    run_git(["clean", "-fd"], check=False)
    print("[成功] 已与远程 main 一致")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="从 GitHub 拉取并覆盖本地（危险操作，须确认）",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help=f"跳过确认（慎用）；默认须输入「{CONFIRM_PHRASE}」",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  GitHub 下载脚本（SSH，覆盖本地）")
    print("=" * 60)

    try:
        setup_git_repo()

        if not require_user_confirm(skip=args.yes):
            sys.exit(0)

        if not force_pull():
            sys.exit(1)

        print("=" * 60)
        print("  [完成] 本地已与远程同步")
        print("=" * 60)

    except Exception as e:
        print(f"\n[错误] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
