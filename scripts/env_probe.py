#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TopPPT HTML · 运行环境探测（公共模块 · 被 regression / probe_image_export 等复用）

统一 Node / pptxgenjs / python-pptx 的探测口径，避免各脚本各写一份导致漂移。
**不绑定任何机器的固定路径**：环境变量 > PATH > 常见托管目录（存在才用，不存在不影响）。

解析优先级：
    Node 可执行文件
        TOP_PPT_NODE_EXE > NODE_EXE > NODE
        > PATH 上的 node > 常见托管目录最新版
    含 pptxgenjs 的 node_modules
        TOP_PPT_NODE_PATH > NODE_PATH
        > 仓库内 node_modules > 逐级父目录 node_modules > 常见托管目录 > 全局 npm root
    python-pptx
        子进程 `import pptx` 是否成功（可选第三方裁判；未装则调用方跳过）

自检：
    python scripts/env_probe.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent

NODE_ENV_VARS = ('TOP_PPT_NODE_EXE', 'NODE_EXE', 'NODE')
NODE_PATH_ENV_VARS = ('TOP_PPT_NODE_PATH', 'NODE_PATH')
NODE_BASES = (
    Path.home() / '.local' / 'share' / 'node',
    Path.home() / 'AppData' / 'Local' / 'nvs',
)
MODULE_BASES = (
    Path.home() / 'node_modules',
)
NODE_EXES = ('node.exe', 'bin/node', 'bin/node.exe')
DEFAULT_PKG = 'pptxgenjs'


# ── Node 可执行文件 ───────────────────────────────────────────────────────────

def node_candidates() -> list[str]:
    """按优先级返回候选 node 可执行文件（去重、保序）。"""
    cands: list[str] = []
    for var in NODE_ENV_VARS:
        val = os.environ.get(var)
        if val and Path(val).is_file():
            cands.append(val)
    found = shutil.which('node')
    if found:
        cands.append(found)
    for base in NODE_BASES:
        if not base.is_dir():
            continue
        try:
            for ver in sorted((p for p in base.iterdir() if p.is_dir()), reverse=True):
                for exe in NODE_EXES:
                    p = ver / exe
                    if p.is_file():
                        cands.append(str(p))
                        break
        except OSError:
            pass
    seen, out = set(), []
    for c in cands:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def find_node() -> str | None:
    for c in node_candidates():
        if Path(c).is_file():
            return c
    return None


# ── 含 pptxgenjs 的 node_modules ─────────────────────────────────────────────

def node_modules_candidates() -> list[str]:
    """按优先级返回可能含目标包的 node_modules 目录（去重、保序）。"""
    cands: list[str] = []
    for var in NODE_PATH_ENV_VARS:
        val = os.environ.get(var)
        if val:
            cands.extend(p for p in val.split(os.pathsep) if p)
    cands.append(str(ROOT / 'node_modules'))
    cands.extend(str(p / 'node_modules') for p in list(ROOT.parents)[:3])  # monorepo 场景
    cands.extend(str(b) for b in MODULE_BASES)
    try:
        npm_root = subprocess.run(['npm', 'root', '-g'], capture_output=True, text=True,
                                  encoding='utf-8', timeout=30).stdout.strip()
        if npm_root:
            cands.append(npm_root)
    except Exception:
        pass
    seen, out = set(), []
    for c in cands:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def find_node_modules(pkg: str = DEFAULT_PKG) -> str | None:
    for c in node_modules_candidates():
        if (Path(c) / pkg).is_dir():
            return c
    return None


# ── 组合与提示 ───────────────────────────────────────────────────────────────

def node_env(node_modules: str | None = None) -> dict[str, str]:
    """返回可直接传给 subprocess 的环境（把 NODE_PATH 指到解析出的 node_modules）。"""
    env = dict(os.environ)
    if node_modules:
        env['NODE_PATH'] = node_modules
    return env


def has_python_pptx(python_exe: str | None = None) -> bool:
    exe = python_exe or sys.executable
    try:
        return subprocess.run([exe, '-c', 'import pptx'], capture_output=True).returncode == 0
    except OSError:
        return False


NODE_HINT = ('未找到 Node 可执行文件（PPTX 精导与回归必需）。安装 Node 后重试，'
             '或用环境变量 TOP_PPT_NODE_EXE 指定路径。')
NODE_MODULES_HINT = ('未找到含 pptxgenjs 的 node_modules（PPTX 生成必需）。'
                     '在技能目录执行 `npm install`（依 package.json），'
                     '或用环境变量 TOP_PPT_NODE_PATH 指定 node_modules 路径。')


def resolve(pkg: str = DEFAULT_PKG) -> tuple[str | None, str | None]:
    """一次性返回 (node, node_modules)。"""
    return find_node(), find_node_modules(pkg)


if __name__ == '__main__':
    node, mods = resolve()
    print('环境探测（TopPPT HTML）')
    print(f'  node         : {node or "未找到"}')
    print(f'  node_modules : {mods or "未找到（缺 pptxgenjs）"}')
    print(f'  python-pptx  : {"可用" if has_python_pptx() else "未安装（可选，交叉裁判会跳过）"}')
    sys.exit(0 if (node and mods) else 1)
