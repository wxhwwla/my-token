#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0
"""
GitHub 上传 — 提交本地改动并推送到远程仓库。

用法:
    python github_upload.py
    python github_upload.py --message "自定义提交信息"
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys  # type: ignore  # Pyright 对 stubPath 中 stdlib 模块的误报，忽略
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent

DEFAULT_REMOTE_SSH = "git@github.com:wxhwwla/my-token.git"
DEFAULT_BRANCH = "main"


def run_git(
    args: list[str],
    *,
    check: bool = True,
    capture_output: bool = False,
    timeout: int | None = 30,
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

    except subprocess.CalledProcessError as e:
        print(f"[错误] Git 命令失败: git {' '.join(args)}")
        raise e

    except FileNotFoundError:
        print("[错误] 未找到 git，请安装 Git 并加入 PATH")
        sys.exit(1)

    except subprocess.TimeoutExpired:
        print(f"[错误] Git 命令超时 ({timeout}s): git {' '.join(args)}")
        raise


def setup_git_repo() -> str:
    """初始化/检查 git 仓库，配置 remote 和分支。"""
    os.chdir(_REPO_ROOT)

    if not os.path.isdir(".git"):
        print("[信息] 初始化 Git 仓库")
        run_git(["init"])
        run_git(["checkout", "-b", DEFAULT_BRANCH])

    # 检查 origin
    _, stdout, _ = run_git(["remote", "-v"], capture_output=True)
    if "origin" not in stdout:
        print(f"[信息] 添加 remote origin → {DEFAULT_REMOTE_SSH}")
        run_git(["remote", "add", "origin", DEFAULT_REMOTE_SSH])
    else:
        # 确保 remote 地址正确
        run_git(["remote", "set-url", "origin", DEFAULT_REMOTE_SSH])

    # 确保在正确分支
    _, cur, _ = run_git(["branch", "--show-current"], capture_output=True)
    if cur.strip() != DEFAULT_BRANCH:
        code, _, _ = run_git(["checkout", DEFAULT_BRANCH], check=False, capture_output=True)
        if code != 0:
            run_git(["checkout", "-b", DEFAULT_BRANCH])

    # 检查 SSH 连通性
    probe_code, _, probe_err = run_git(
        ["ls-remote", DEFAULT_REMOTE_SSH, "HEAD"],
        check=False,
        capture_output=True,
        timeout=15,
    )
    if probe_code != 0:
        hint = (probe_err or "").strip() or f"exit {probe_code}"
        print(f"[警告] SSH 连通性未确认（{hint}），推送可能失败")

    return DEFAULT_REMOTE_SSH


def check_status() -> list[str]:
    """检查工作区状态，返回变更文件列表。"""
    _, porcelain, _ = run_git(
        ["-c", "core.quotepath=false", "status", "--porcelain"],
        capture_output=True,
    )
    lines = [ln for ln in porcelain.splitlines() if ln.strip()]
    return lines


def commit_and_push(message: str | None = None) -> None:
    """暂存所有改动、提交、推送。"""
    # 1. git add
    print("[信息] 暂存所有改动...")
    run_git(["add", "."])

    # 2. 检查是否有东西可提交
    _, staged, _ = run_git(
        ["-c", "core.quotepath=false", "diff", "--cached", "--name-only"],
        capture_output=True,
    )
    if not staged.strip():
        print("[信息] 无新更改，无需提交")
        return

    # 3. 提交
    if message:
        commit_msg = message
    else:
        # 自动生成提交信息
        files = [ln.strip() for ln in staged.splitlines() if ln.strip()]
        if len(files) <= 3:
            commit_msg = f"更新: {', '.join(files)}"
        else:
            commit_msg = f"更新 {len(files)} 处文件"

    print(f"[信息] git commit: {commit_msg}")
    run_git(["commit", "-m", commit_msg])

    # 4. 推送
    print("[信息] git push...")
    try:
        run_git(["push", "-u", "origin", DEFAULT_BRANCH], timeout=120)
        print("[成功] 推送完成")
    except subprocess.CalledProcessError:
        print("[信息] 推送失败，尝试拉取后重试...")
        run_git(["fetch", "origin"], timeout=60)
        run_git(["pull", "--rebase", "origin", DEFAULT_BRANCH], timeout=60)
        run_git(["push", "-u", "origin", DEFAULT_BRANCH], timeout=120)
        print("[成功] 推送完成")


def main() -> None:
    parser = argparse.ArgumentParser(description="推送本仓库到 GitHub（SSH）")
    parser.add_argument(
        "--message", "-m",
        type=str,
        help="自定义提交信息（默认自动生成）",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  GitHub 上传脚本")
    print("=" * 60)

    try:
        setup_git_repo()

        changes = check_status()
        if changes:
            print(f"[信息] 检测到 {len(changes)} 项变更")
            for line in changes:
                print(f"  {line}")
        else:
            print("[信息] 工作区干净，无未提交更改")

        commit_and_push(message=args.message)

        print("=" * 60)
        print("  [完成]")
        print("=" * 60)

    except Exception as e:
        print(f"\n[错误] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
