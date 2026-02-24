#!/usr/bin/env python3
"""
Phone Agent - OpenClaw 手机控制代理
版本：v2.0.0 - 精简版，只保留通用接口
"""

import os
import sys
import json
import time
import subprocess
import threading
import base64
from datetime import datetime
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# 配置
CONFIG_FILE = "config.json"
GITHUB_REPO = "openclaw-glasses/phone-agent"
CURRENT_VERSION = "v2.0.1"


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "server": {"host": "0.0.0.0", "port": 50001},
        "adb": {"enabled": True, "wireless_ip": None},
        "autojs": {"enabled": False, "url": "http://127.0.0.1:8088"},
        "update_interval": None,
    }


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def run_cmd(cmd, timeout=10):
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return {"success": True, "stdout": result.stdout, "stderr": result.stderr}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def adb_cmd(cmd):
    config = load_config()
    adb_prefix = "adb "
    if config["adb"]["wireless_ip"]:
        adb_prefix = f"adb -s {config['adb']['wireless_ip']} "
    return run_cmd(f"{adb_prefix}{cmd}")


# ==================== 首页 ====================


@app.route("/")
def index():
    return jsonify(
        {
            "name": "Phone Agent",
            "version": CURRENT_VERSION,
            "status": "running",
            "endpoints": [
                "/api/status",
                "/api/termux",
                "/api/exec",
                "/api/adb/*",
                "/api/update/*",
            ],
        }
    )


# ==================== 状态 ====================


@app.route("/api/status")
def api_status():
    return jsonify(
        {
            "status": "online",
            "timestamp": datetime.now().isoformat(),
            "version": CURRENT_VERSION,
        }
    )


# ==================== 通用 termux-api 接口 ====================


@app.route("/api/termux", methods=["POST"])
def api_termux():
    """通用 termux-api 接口"""
    data = request.json or {}
    command = data.get("command", "")
    args = data.get("args", [])
    timeout = data.get("timeout", 30)

    if not command:
        return jsonify({"error": "No command specified"})

    # 预处理 args：合并 `--xxx` 和下一个参数
    processed_args = []
    i = 0
    while i < len(args):
        arg = str(args[i])
        if arg.startswith("--") and i + 1 < len(args):
            next_arg = str(args[i + 1])
            if not next_arg.startswith("--") and not next_arg.startswith("-"):
                # 合并为 --xxx="value" 格式
                processed_args.append(f'{arg}="{next_arg}"')
                i += 2
                continue
        processed_args.append(arg)
        i += 1

    # 构建命令
    full_command = command
    for arg in processed_args:
        full_command += f" {arg}"

    result = run_cmd(full_command, timeout)

    # 尝试解析 JSON
    parsed = None
    if result.get("success") and result.get("stdout"):
        try:
            parsed = json.loads(result["stdout"])
        except:
            pass

    return jsonify(
        {
            "success": result.get("success", False),
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "parsed": parsed,
            "command": full_command,
        }
    )


# ==================== 通用 Shell 执行# ==================== 通用 Shell 执行 ====================


@app.route("/api/exec", methods=["POST"])
def api_exec():
    """
    通用 Shell 命令执行（谨慎使用）

    请求格式：
    {
        "command": "export",
        "args": ["MY_VAR=hello"],
        "shell": true  // 是否作为 shell 脚本执行
    }
    """
    data = request.json or {}
    command = data.get("command", "")
    args = data.get("args", [])
    shell_mode = data.get("shell", False)
    timeout = data.get("timeout", 30)
    workdir = data.get("workdir", "/data/data/com.termux/files/home")

    if not command:
        return jsonify({"error": "No command specified"})

    # 构建完整命令
    full_command = command
    for arg in args:
        # 转义特殊字符
        arg = str(arg).replace('"', '\\"').replace("$", "\\$").replace("`", "\\`")
        full_command += f' "{arg}"'

    # 如果是 shell 模式，添加工作目录
    if shell_mode:
        full_command = f'cd "{workdir}" && {full_command}'

    result = run_cmd(full_command, timeout)

    return jsonify(
        {
            "success": result.get("success", False),
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "command": full_command,
        }
    )


# ==================== ADB 控制 ====================


@app.route("/api/adb", methods=["POST"])
def api_adb():
    """通用 ADB 接口"""
    data = request.json or {}
    subcommand = data.get("subcommand", "")
    args = data.get("args", [])

    full_cmd = f"shell {subcommand}"
    for arg in args:
        full_cmd += f" {arg}"

    result = adb_cmd(full_cmd)
    return jsonify(
        {
            "success": result.get("success", False),
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "command": f"adb {full_cmd}",
        }
    )


@app.route("/api/adb/tap", methods=["POST"])
def api_adb_tap():
    """ADB 点击"""
    data = request.json
    x, y = data.get("x", 0), data.get("y", 0)
    return jsonify(adb_cmd(f"shell input tap {x} {y}"))


@app.route("/api/adb/swipe", methods=["POST"])
def api_adb_swipe():
    """ADB 滑动"""
    data = request.json
    x1, y1 = data.get("x1", 0), data.get("y1", 0)
    x2, y2 = data.get("x2", 0), data.get("y2", 0)
    duration = data.get("duration", 300)
    return jsonify(adb_cmd(f"shell input swipe {x1} {y1} {x2} {y2} {duration}"))


@app.route("/api/adb/input", methods=["POST"])
def api_adb_input():
    """ADB 输入"""
    data = request.json
    text = data.get("text", "").replace(" ", "%s").replace('"', '\\"')
    return jsonify(adb_cmd(f'shell input text "{text}"'))


@app.route("/api/adb/key", methods=["POST"])
def api_adb_key():
    """ADB 按键"""
    data = request.json
    key = data.get("key", "ENTER")
    keys = {"ENTER": "66", "BACK": "4", "HOME": "3", "MENU": "82", "POWER": "26"}
    return jsonify(adb_cmd(f"shell input keyevent {keys.get(key, key)}"))


@app.route("/api/adb/screenshot")
def api_adb_screenshot():
    """ADB 截图"""
    output = f"/sdcard/screen_{int(time.time())}.png"
    result = adb_cmd(f"shell screencap -p {output}")
    return jsonify({"success": result.get("success", False), "path": output})


@app.route("/api/adb/dump")
def api_adb_dump():
    """ADB UI 层级"""
    adb_cmd("shell uiautomator dump")
    result = adb_cmd("shell cat /sdcard/window_dump.xml")
    return jsonify(
        {"success": result.get("success", False), "xml": result.get("stdout", "")}
    )


@app.route("/api/adb/start", methods=["POST"])
def api_adb_start():
    """ADB 启动 App"""
    data = request.json
    package = data.get("package", "")
    activity = data.get("activity", "")
    result = adb_cmd(f"shell am start -n {package}/{activity}")
    return jsonify(result)


# ==================== 文件传输（通用） ====================

# 允许读写的路径前缀（尽量收敛到常用目录；需要更多再加）
ALLOWED_PATH_PREFIXES = [
    "/sdcard/",
    "/storage/emulated/0/",
    "/data/data/com.termux/files/home/",
]


def _is_allowed_path(path: str) -> bool:
    if not path or not path.startswith("/"):
        return False
    # 基础防护：禁止路径穿越
    if ".." in path.split("/"):
        return False
    return any(path.startswith(p) for p in ALLOWED_PATH_PREFIXES)


@app.route("/api/file/stat", methods=["POST"])
def api_file_stat():
    data = request.json or {}
    path = data.get("path")
    if not _is_allowed_path(path):
        return jsonify({"success": False, "error": "Path not allowed"}), 400

    try:
        st = os.stat(path)
        return jsonify(
            {
                "success": True,
                "path": path,
                "size": st.st_size,
                "mtime": st.st_mtime,
                "mode": st.st_mode,
            }
        )
    except FileNotFoundError:
        return jsonify({"success": False, "error": "Not found", "path": path}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "path": path}), 500


@app.route("/api/file/read", methods=["POST"])
def api_file_read():
    """读取文件并以 base64 返回（通用拉取方式）"""
    data = request.json or {}
    path = data.get("path")
    max_bytes = int(data.get("maxBytes", 10 * 1024 * 1024))  # 默认 10MB

    if not _is_allowed_path(path):
        return jsonify({"success": False, "error": "Path not allowed"}), 400

    try:
        st = os.stat(path)
        if st.st_size > max_bytes:
            return jsonify(
                {
                    "success": False,
                    "error": "Too large",
                    "size": st.st_size,
                    "maxBytes": max_bytes,
                }
            ), 413

        with open(path, "rb") as f:
            raw = f.read()
        b64 = base64.b64encode(raw).decode("ascii")
        return jsonify({"success": True, "path": path, "size": len(raw), "base64": b64})
    except FileNotFoundError:
        return jsonify({"success": False, "error": "Not found", "path": path}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "path": path}), 500


@app.route("/api/file/write", methods=["POST"])
def api_file_write():
    """写入文件（base64 输入）。mode=overwrite|append"""
    data = request.json or {}
    path = data.get("path")
    b64 = data.get("base64")
    mode = data.get("mode", "overwrite")
    mkdirs = bool(data.get("mkdirs", True))

    if not _is_allowed_path(path):
        return jsonify({"success": False, "error": "Path not allowed"}), 400
    if not b64:
        return jsonify({"success": False, "error": "Missing base64"}), 400

    try:
        raw = base64.b64decode(b64.encode("ascii"), validate=False)
        if mkdirs:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        write_mode = "ab" if mode == "append" else "wb"
        with open(path, write_mode) as f:
            f.write(raw)
        return jsonify({"success": True, "path": path, "bytes": len(raw), "mode": mode})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "path": path}), 500


# ==================== 更新 ====================


@app.route("/api/version")
def api_version():
    return jsonify({"version": CURRENT_VERSION, "repo": GITHUB_REPO})


@app.route("/api/update/check")
def api_update_check():
    """检查更新 - 使用 GitHub API"""
    try:
        import urllib.request

        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "Python"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            latest = data.get("tag_name", "").lstrip("v")
            body = data.get("body", "")[:500]

        curr = [int(x) for x in CURRENT_VERSION.replace("v", "").split(".")]
        latest_v = (
            [int(x) for x in latest.split(".")]
            if latest.replace(".", "").isdigit()
            else curr
        )

        return jsonify(
            {
                "current_version": CURRENT_VERSION,
                "latest_version": f"v{latest}" if latest else CURRENT_VERSION,
                "update_available": latest_v > curr,
                "changelog": data.get(
                    "html_url", f"https://github.com/{GITHUB_REPO}/releases"
                ),
                "release_body": body,
                "published_at": data.get("published_at", ""),
            }
        )
    except Exception as e:
        return jsonify(
            {
                "error": str(e),
                "current_version": CURRENT_VERSION,
                "update_available": False,
                "hint": "网络或 API 错误，可尝试手动更新",
            }
        )


@app.route("/api/update/git", methods=["POST"])
def api_update_git():
    """使用 git pull 更新"""
    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        result = run_cmd(
            "git fetch origin main && git reset --hard origin/main", timeout=30
        )
        return jsonify(
            {
                "success": result.get("success", False),
                "method": "git_pull",
                "message": "更新成功，请重启服务"
                if result.get("success")
                else result.get("error", "更新失败"),
                "stdout": result.get("stdout", "")[:500],
                "stderr": result.get("stderr", "")[:500],
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/update/download", methods=["POST"])
def api_update_download():
    """手动下载更新（备用方案）"""
    try:
        import urllib.request, zipfile, io, shutil

        os.chdir("/data/data/com.termux/files/home")

        script = f"""#!/bin/bash
cd /data/data/com.termux/files/home

# 备份旧版本
[ -d "phone-agent-old" ] && rm -rf phone-agent-old
mv phone-agent phone-agent-old

# 下载新版本
wget -q https://github.com/{GITHUB_REPO}/archive/refs/heads/main.zip -O phone-agent.zip
unzip -q phone-agent.zip
mv phone-agent-main phone-agent
rm -f phone-agent.zip

# 恢复配置
cp phone-agent-old/config.json phone-agent/

# 启动
cd phone-agent
nohup python phone_agent.py > /dev/null 2>&1 &
"""
        script_path = "/data/data/com.termux/files/home/phone-agent-upgrade.sh"
        with open(script_path, "w") as f:
            f.write(script)
        os.chmod(script_path, 0o755)

        subprocess.Popen(
            ["sh", script_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        return jsonify(
            {
                "success": True,
                "method": "download",
                "message": "开始下载更新，服务将自动重启",
                "hint": "如失败，请手动执行: cd /data/data/com.termux/files/home && git clone https://github.com/openclaw-glasses/phone-agent.git",
            }
        )
    except Exception as e:
        return jsonify(
            {
                "success": False,
                "error": str(e),
                "hint": "请手动更新: git clone https://github.com/openclaw-glasses/phone-agent.git",
            }
        )


@app.route("/api/update/auto", methods=["POST"])
def api_auto_update():
    """自动升级 - 优先 git pull，失败则下载"""
    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        fetch_result = run_cmd("git fetch origin main", timeout=15)
        if fetch_result.get("success"):
            reset_result = run_cmd("git reset --hard origin/main", timeout=15)
            if reset_result.get("success"):
                return jsonify(
                    {
                        "success": True,
                        "method": "git",
                        "message": "更新成功，请手动重启服务",
                        "restart_url": "/api/restart",
                    }
                )

        return api_update_download()
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/restart", methods=["POST"])
def api_restart():
    """重启服务"""
    try:
        script = """#!/bin/bash
sleep 1
cd /data/data/com.termux/files/home/phone-agent
nohup python phone_agent.py > /dev/null 2>&1 &
"""
        script_path = "/data/data/com.termux/files/home/phone-agent-restart.sh"
        with open(script_path, "w") as f:
            f.write(script)
        os.chmod(script_path, 0o755)

        subprocess.Popen(["sh", script_path])
        return jsonify({"success": True, "message": "Restarting..."})
    except Exception as e:
        return jsonify({"error": str(e)})


# ==================== 启动 ====================


def start_http_server(config):
    print(f"🚀 Phone Agent {CURRENT_VERSION} 启动中...")
    print(f"📡 http://{config['server']['host']}:{config['server']['port']}")
    app.run(host=config["server"]["host"], port=config["server"]["port"], debug=False)


if __name__ == "__main__":
    config = load_config()
    start_http_server(config)
