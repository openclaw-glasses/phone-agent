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
CURRENT_VERSION = "v2.0.0"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        "server": {"host": "0.0.0.0", "port": 50001},
        "adb": {"enabled": True, "wireless_ip": None},
        "autojs": {"enabled": False, "url": "http://127.0.0.1:8088"},
        "update_interval": None
    }

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def run_cmd(cmd, timeout=10):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return {"success": True, "stdout": result.stdout, "stderr": result.stderr}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def adb_cmd(cmd):
    config = load_config()
    adb_prefix = "adb "
    if config['adb']['wireless_ip']:
        adb_prefix = f"adb -s {config['adb']['wireless_ip']} "
    return run_cmd(f"{adb_prefix}{cmd}")

# ==================== 首页 ====================

@app.route('/')
def index():
    return jsonify({
        "name": "Phone Agent",
        "version": CURRENT_VERSION,
        "status": "running",
        "endpoints": ["/api/status", "/api/termux", "/api/exec", "/api/adb/*", "/api/update/*"]
    })

# ==================== 状态 ====================

@app.route('/api/status')
def api_status():
    return jsonify({
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "version": CURRENT_VERSION
    })

# ==================== 通用 termux-api 接口 ====================

@app.route('/api/termux', methods=['POST'])
def api_termux():
    """通用 termux-api 接口"""
    data = request.json or {}
    command = data.get('command', '')
    args = data.get('args', [])
    timeout = data.get('timeout', 30)
    
    if not command:
        return jsonify({"error": "No command specified"})
    
    # 直接拼接，不加引号
    full_command = command
    for arg in args:
        full_command += f' {arg}'
    
    result = run_cmd(full_command, timeout)
    
    # 尝试解析 JSON
    parsed = None
    stdout = result.get('stdout', '')
    if result.get('success') and stdout:
        try:
            parsed = json.loads(stdout)
        except:
            pass
    
    return jsonify({
        "success": result.get('success', False),
        "stdout": stdout,
        "stderr": result.get('stderr', ''),
        "parsed": parsed,
        "command": full_command
    })
        "success": result.get('success', False),
        "stdout": result.get('stdout', ''),
        "stderr": result.get('stderr', ''),
        "parsed": parsed,
        "command": full_command
    })

# ==================== 传感器专用接口 ====================

@app.route('/api/sensor', methods=['POST'])
def api_sensor():
    """
    传感器数据获取
    使用 timeout 命令限制运行时间
    
    请求格式：
    {
        "sensor": "lsm6dsoq_acc",
        "seconds": 2
    }
    """
    data = request.json or {}
    sensor = data.get('sensor', 'lsm6dsoq_acc')
    seconds = data.get('seconds', 2)
    
    # 使用 timeout 限制运行时间
    cmd = f"timeout {seconds} termux-sensor -s {sensor}"
    result = run_cmd(cmd, seconds + 5)
    
    # 解析多行 JSON 输出
    stdout = result.get('stdout', '')
    readings = []
    for line in stdout.strip().split('\n'):
        line = line.strip()
        if line.startswith('{') and line.endswith('}'):
            try:
                readings.append(json.loads(line))
            except:
                pass
    
    return jsonify({
        "success": result.get('success', False),
        "sensor": sensor,
        "readings": readings,
        "count": len(readings)
    })

# ==================== 通用 Shell 执行 ====================

@app.route('/api/exec', methods=['POST'])
def api_exec():
    """
    通用 Shell 命令执行（谨慎使用）
    """
    data = request.json or {}
    command = data.get('command', '')
    args = data.get('args', [])
    shell_mode = data.get('shell', False)
    timeout = data.get('timeout', 30)
    workdir = data.get('workdir', '/data/data/com.termux/files/home')

    if not command:
        return jsonify({"error": "No command specified"})

    # 直接构建命令，不拆分 args
    full_command = command
    for arg in args:
        arg = str(arg).replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
        full_command += f' {arg}'

    if shell_mode:
        full_command = f'cd "{workdir}" && {full_command}'

    result = run_cmd(full_command, timeout)

    # 解析 JSON
    parsed = None
    stdout = result.get('stdout', '')
    if result.get('success') and stdout:
        try:
            parsed = json.loads(stdout)
        except:
            pass

    return jsonify({
        "success": result.get('success', False),
        "stdout": stdout,
        "stderr": result.get('stderr', ''),
        "parsed": parsed,
        "command": full_command
    })

# ==================== ADB 控制 ====================

@app.route('/api/adb', methods=['POST'])
def api_adb():
    """通用 ADB 接口"""
    data = request.json or {}
    subcommand = data.get('subcommand', '')
    args = data.get('args', [])
    
    full_cmd = f"shell {subcommand}"
    for arg in args:
        full_cmd += f" {arg}"
    
    result = adb_cmd(full_cmd)
    return jsonify({
        "success": result.get('success', False),
        "stdout": result.get('stdout', ''),
        "stderr": result.get('stderr', ''),
        "command": f"adb {full_cmd}"
    })

@app.route('/api/adb/tap', methods=['POST'])
def api_adb_tap():
    """ADB 点击"""
    data = request.json
    x, y = data.get('x', 0), data.get('y', 0)
    return jsonify(adb_cmd(f"shell input tap {x} {y}"))

@app.route('/api/adb/swipe', methods=['POST'])
def api_adb_swipe():
    """ADB 滑动"""
    data = request.json
    x1, y1 = data.get('x1', 0), data.get('y1', 0)
    x2, y2 = data.get('x2', 0), data.get('y2', 0)
    duration = data.get('duration', 300)
    return jsonify(adb_cmd(f"shell input swipe {x1} {y1} {x2} {y2} {duration}"))

@app.route('/api/adb/input', methods=['POST'])
def api_adb_input():
    """ADB 输入"""
    data = request.json
    text = data.get('text', '').replace(' ', '%s').replace('"', '\\"')
    return jsonify(adb_cmd(f'shell input text "{text}"'))

@app.route('/api/adb/key', methods=['POST'])
def api_adb_key():
    """ADB 按键"""
    data = request.json
    key = data.get('key', 'ENTER')
    keys = {'ENTER': '66', 'BACK': '4', 'HOME': '3', 'MENU': '82', 'POWER': '26'}
    return jsonify(adb_cmd(f"shell input keyevent {keys.get(key, key)}"))

@app.route('/api/adb/screenshot')
def api_adb_screenshot():
    """ADB 截图"""
    output = f"/sdcard/screen_{int(time.time())}.png"
    result = adb_cmd(f"shell screencap -p {output}")
    return jsonify({"success": result.get('success', False), "path": output})

@app.route('/api/adb/dump')
def api_adb_dump():
    """ADB UI 层级"""
    adb_cmd("shell uiautomator dump")
    result = adb_cmd("shell cat /sdcard/window_dump.xml")
    return jsonify({
        "success": result.get('success', False),
        "xml": result.get('stdout', '')
    })

@app.route('/api/adb/start', methods=['POST'])
def api_adb_start():
    """ADB 启动 App"""
    data = request.json
    package = data.get('package', '')
    activity = data.get('activity', '')
    result = adb_cmd(f"shell am start -n {package}/{activity}")
    return jsonify(result)

# ==================== 更新 ====================

@app.route('/api/version')
def api_version():
    return jsonify({
        "version": CURRENT_VERSION,
        "repo": GITHUB_REPO
    })

@app.route('/api/update/check')
def api_update_check():
    """检查更新"""
    try:
        import urllib.request
        url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/README.md"
        response = urllib.request.urlopen(url, timeout=10)
        content = response.read().decode('utf-8')
        
        import re
        v_match = re.search(r'version:?.*?v(\d+\.\d+\.\d+)', content, re.IGNORECASE)
        latest = v_match.group(1) if v_match else CURRENT_VERSION
        
        curr = [int(x) for x in CURRENT_VERSION.replace('v', '').split('.')]
        latest_v = [int(x) for x in latest.split('.')]
        
        return jsonify({
            "current_version": CURRENT_VERSION,
            "latest_version": f"v{latest}",
            "update_available": latest_v > curr,
            "changelog": f"https://github.com/{GITHUB_REPO}/commits/main"
        })
    except Exception as e:
        return jsonify({"error": str(e), "current_version": CURRENT_VERSION})

@app.route('/api/update', methods=['POST'])
def api_update():
    """更新代码"""
    result = run_cmd("git pull origin main")
    return jsonify(result)

@app.route('/api/update/auto', methods=['POST'])
def api_auto_update():
    """自动升级"""
    try:
        import urllib.request, zipfile, io, shutil
        
        # 创建升级脚本
        script = f'''#!/bin/bash
sleep 2
cd /data/data/com.termux/files/home
mv phone-agent phone-agent-old
wget -q https://github.com/{GITHUB_REPO}/archive/refs/heads/main.zip -O phone-agent.zip
unzip -q phone-agent.zip
mv phone-agent-main phone-agent
cd phone-agent
nohup python phone_agent.py > /dev/null 2>&1 &
'''
        script_path = "/data/data/com.termux/files/home/phone-agent-upgrade.sh"
        with open(script_path, 'w') as f:
            f.write(script)
        os.chmod(script_path, 0o755)
        
        subprocess.Popen(["sh", script_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        return jsonify({
            "success": True,
            "message": "Upgrade started. Service will restart.",
            "log": "/data/data/com.termux/files/home/phone-agent-upgrade.log"
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/restart', methods=['POST'])
def api_restart():
    """重启服务"""
    try:
        script = '''#!/bin/bash
sleep 1
cd /data/data/com.termux/files/home/phone-agent
nohup python phone_agent.py > /dev/null 2>&1 &
'''
        script_path = "/data/data/com.termux/files/home/phone-agent-restart.sh"
        with open(script_path, 'w') as f:
            f.write(script)
        os.chmod(script_path, 0o755)
        
        subprocess.Popen(["sh", script_path])
        return jsonify({"success": True, "message": "Restarting..."})
    except Exception as e:
        return jsonify({"error": str(e)})

# ==================== 启动 ====================

def acquire_wakelock():
    """获取唤醒锁，防止后台被杀"""
    try:
        # 创建 wake-lock 脚本
        script = '''#!/bin/bash
termux-wake-lock
'''
        script_path = "/data/data/com.termux/files/home/phone-agent-wakelock.sh"
        with open(script_path, 'w') as f:
            f.write(script)
        os.chmod(script_path, 0o755)

        # 尝试获取 wake-lock
        result = run_cmd("termux-wake-lock")
        if result.get('success'):
            print("✅ Wake lock acquired")
        else:
            print("⚠️ Wake lock failed (may need root)")
    except Exception as e:
        print(f"⚠️ Wake lock error: {e}")

def start_http_server(config):
    print(f"🚀 Phone Agent {CURRENT_VERSION} 启动中...")
    print(f"📱 PID: {os.getpid()}")

    # 获取唤醒锁
    acquire_wakelock()

    # 检查是否在 Termux 环境
    if os.path.exists("/data/data/com.termux/files/home"):
        print("📱 Termux 环境检测: 是")
    else:
        print("📱 Termux 环境检测: 否")
    print(f"📡 http://{config['server']['host']}:{config['server']['port']}")
    app.run(host=config['server']['host'], port=config['server']['port'], debug=False)

if __name__ == '__main__':
    config = load_config()
    start_http_server(config)
