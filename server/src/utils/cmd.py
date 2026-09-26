#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
命令行执行模块

提供执行外部命令的封装（普通执行与 bash 脚本执行），并返回标准输出/错误与退出码。
"""

import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path


def normal_exec(argv: str | Sequence[str], timeout: int = 60) -> tuple[int, bytes, bytes]:
    """普通执行命令。"""
    if timeout <= 0:
        raise ValueError("timeout must be > 0")

    shell = isinstance(argv, str)
    try:
        proc = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=shell,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise TimeoutError(f"exec cmd timeout, cmd: {argv!r}, timeout: {timeout}") from e

    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def bash_exec(
    cmd: str,
    timeout: int = 60,
    dir: str = "/tmp",
    bin: str = "/bin/bash",
) -> tuple[int, bytes, bytes]:
    """使用 bash 命令执行。"""
    target_dir = Path(dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".sh",
        prefix="_xxx_",
        dir=str(target_dir),
        delete=False,
    ) as f:
        f.write(cmd)
        tmp_file_path = f.name

    # keep compatible: default behaviour still prints bash trace (-x)
    return normal_exec([bin, "-x", tmp_file_path], timeout)
