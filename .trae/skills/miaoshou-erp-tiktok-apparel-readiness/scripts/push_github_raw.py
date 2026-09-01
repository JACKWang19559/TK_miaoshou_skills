# -*- coding: utf-8 -*-
"""把本地图片提交到 GitHub 仓库并返回 raw 直链（图床不可达时的兜底）。

catbox / litterbox / telegra.ph 等匿名图床在部分网络/地区会被 Cloudflare
WAF 或出口 IP 拦截（本机实测 412/500/400），而 ``git push`` 到 GitHub 通常
畅通。本脚本把图片复制进指定仓库、``git add/commit/push``，再按远程地址
自动推导 ``raw.githubusercontent.com`` 直链返回。妙手/TikTok 海外服务器
可拉取该直链，发布时平台会转存 CDN，故文件是否长期保留不影响已发布商品。

用法::

    py push_github_raw.py sizechart.png --repo E:\\1\\tiktok\\TK_miaoshou_skills \\
        --rel assets/sizechart.png --branch main --message "chore: add size chart"

依赖：仓库必须已配置好可推送的 ``origin`` 远程与凭证。
"""
import argparse
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


def run_git(repo: Path, args: list) -> str:
    """执行 git 命令并返回 stdout。

    Args:
        repo: 仓库本地路径。
        args: git 子命令参数列表。

    Returns:
        命令 stdout 字符串。

    Raises:
        SystemExit: git 命令执行失败时退出并打印 stderr。
    """
    proc = subprocess.run(["git", "-C", str(repo)] + args,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    if proc.returncode != 0:
        sys.exit(f"git {' '.join(args)} 失败:\n{proc.stderr}")
    return proc.stdout.strip()


def derive_raw_base(repo: Path, branch: str) -> str:
    """由远程 URL 推导 raw 前缀。

    支持两种远程格式：HTTPS（``https://github.com/o/r.git``）与 SSH
    （``git@github.com:o/r.git``），统一转为
    ``https://raw.githubusercontent.com/o/r/<branch>``。

    Args:
        repo: 仓库本地路径。
        branch: 目标分支名。

    Returns:
        raw 前缀（不含文件相对路径）。
    """
    remote = run_git(repo, ["remote", "get-url", "origin"])
    if remote.startswith("git@github.com:"):
        path = remote[len("git@github.com:"):]
    else:
        path = urlparse(remote).path
    path = path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    return f"https://raw.githubusercontent.com/{path}/{branch}"


def main() -> None:
    """命令行入口：复制图片 → git 提交推送 → 打印 raw 直链。"""
    parser = argparse.ArgumentParser(
        description="提交图片到 GitHub 仓库并返回 raw 直链")
    parser.add_argument("file", help="本地图片路径")
    parser.add_argument("--repo", required=True, help="仓库本地路径")
    parser.add_argument("--rel", required=True, help="仓库内相对路径")
    parser.add_argument("--branch", default="main", help="分支名（默认 main）")
    parser.add_argument("--message", default="chore: add image asset",
                        help="提交说明")
    args = parser.parse_args()

    repo = Path(args.repo)
    src = Path(args.file)
    if not src.is_file():
        sys.exit(f"图片不存在: {src}")
    if not (repo / ".git").exists():
        sys.exit(f"不是 git 仓库: {repo}")

    dst = repo / args.rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())

    run_git(repo, ["add", args.rel])
    run_git(repo, ["commit", "-m", args.message])
    run_git(repo, ["push", "origin", args.branch])

    raw_base = derive_raw_base(repo, args.branch)
    print(f"{raw_base}/{args.rel}")


if __name__ == "__main__":
    main()
