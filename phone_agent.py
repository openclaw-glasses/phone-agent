#!/usr/bin/env python3
"""
Phone Agent - OpenClaw 手机控制代理
功能：让 OpenClaw 通过 HTTP 控制 Android 手机
"""

import os
import sys
import json
import time
import subprocess
import threading
from datetime import datetime
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# 配置
CONFIG_FILE = "config.json"

def load_config():
    """加载配置"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        "server": {"host": "0.0.0.0", "port": 8080},
        "adb": {"enabled": True, "wireless_ip": None},
        "autojs": {"enabled": False, "url": "http://127.0.0.1:8088"},
        "openclaw": {"gateway_url": None}
    }

def save_config(config):
    """保存配置"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def run_cmd(cmd, timeout=10):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {"success": True, "stdout": result.stdout, "stderr": result.stderr}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def adb_cmd(cmd):
    """执行 ADB 命令"""
    config = load_config()
    adb_prefix = "adb "
    
    if config['adb']['wireless_ip']:
        adb_prefix = f"adb -s {config['adb']['wireless_ip']} "
    
    return run_cmd(f"{adb_prefix}{cmd}")

# ==================== API 端点 ====================

@app.route('/')
def index():
    return jsonify({
        "name": "Phone Agent",
        "version": "1.0.0",
        "status": "running",
        "endpoints": ["/api/status", "/api/battery", "/api/sms/list", 
                      "/api/adb/tap", "/api/adb/screenshot", "/api/update"]
    })

@app.route('/api/status')
def api_status():
    """设备状态"""
    return jsonify({
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "uptime": time.time()
    })

@app.route('/api/version')
def api_version():
    """版本信息"""
    return jsonify({
        "version": "1.0.0",
        "last_update": datetime.now().isoformat()
    })

# ==================== 系统信息 ====================

@app.route('/api/battery')
def api_battery():
    """电池信息"""
    result = run_cmd("termux-battery-status")
    if result['success']:
        return jsonify(json.loads(result['stdout']))
    return jsonify({"error": result['error']})

@app.route('/api/cpu')
def api_cpu():
    """CPU 信息"""
    result = run_cmd("cat /proc/cpuinfo | head -5")
    return jsonify({"cpu": result['stdout']})

# ==================== termux-api ====================

@app.route('/api/sms/list')
def api_sms_list():
    """列出短信"""
    result = run_cmd("termux-sms-list")
    if result['success']:
        try:
            return jsonify(json.loads(result['stdout']))
        except:
            return jsonify([])
    return jsonify({"error": result['error']})

@app.route('/api/sms/send', methods=['POST'])
def api_sms_send():
    """发送短信"""
    data = request.json
    number = data.get('number', '')
    message = data.get('message', '')
    
    result = run_cmd(f'termux-sms-send -n "{number}" "{message}"')
    return jsonify(result)

@app.route('/api/location')
def api_location():
    """获取位置"""
    result = run_cmd("termux-location")
    if result['success']:
        try:
            return jsonify(json.loads(result['stdout']))
        except:
            return jsonify({"error": "Parse error"})
    return jsonify({"error": result['error']})

@app.route('/api/camera/photo')
def api_camera_photo():
    """拍照"""
    camera = request.args.get('camera', '0')
    output = f"/sdcard/photo_{int(time.time())}.jpg"
    result = run_cmd(f"termux-camera-photo -c {camera} {output}")
    
    return jsonify({
        "success": result['success'],
        "path": output,
        "error": result.get('error')
    })

# ==================== ADB 控制 ====================

@app.route('/api/adb/tap', methods=['POST'])
def api_adb_tap():
    """点击坐标"""
    data = request.json
    x = data.get('x', 0)
    y = data.get('y', 0)
    
    result = adb_cmd(f"shell input tap {x} {y}")
    return jsonify(result)

@app.route('/api/adb/swipe', methods=['POST'])
def api_adb_swipe():
    """滑动"""
    data = request.json
    x1 = data.get('x1', 0)
    y1 = data.get('y1', 0)
    x2 = data.get('x2', 0)
    y2 = data.get('y2', 0)
    duration = data.get('duration', 300)
    
    result = adb_cmd(f"shell input swipe {x1} {y1} {x2} {y2} {duration}")
    return jsonify(result)

@app.route('/api/adb/input', methods=['POST'])
def api_adb_input():
    """输入文字"""
    data = request.json
    text = data.get('text', '')
    # 处理特殊字符
    text = text.replace(' ', '%s').replace('"', '\\"')
    
    result = adb_cmd(f"shell input text \"{text}\"")
    return jsonify(result)

@app.route('/api/adb/key', methods=['POST'])
def api_adb_key():
    """按键"""
    data = request.json
    key = data.get('key', 'ENTER')
    
    key_map = {
        'ENTER': '66',
        'BACK': '4',
        'HOME': '3',
        'MENU': '82',
        'VOLUME_UP': '24',
        'VOLUME_DOWN': '25'
    }
    
    key_code = key_map.get(key, key)
    result = adb_cmd(f"shell input keyevent {key_code}")
    return jsonify(result)

@app.route('/api/adb/screenshot')
def api_adb_screenshot():
    """截图"""
    output = f"/sdcard/screen_{int(time.time())}.png"
    result = adb_cmd(f"shell screencap -p {output}")
    
    if result['success']:
        return jsonify({"success": True, "path": output})
    return jsonify({"error": result['error']})

@app.route('/api/adb/dump', methods=['GET'])
def api_adb_dump():
    """获取 UI 层级"""
    result = adb_cmd("shell uiautomator dump")
    result2 = adb_cmd("pull /sdcard/window_dump.xml /tmp/")
    
    return jsonify({
        "success": result['success'] and result2['success'],
        "xml_path": "/tmp/window_dump.xml"
    })

# ==================== AutoJS ====================

@app.route('/api/autojs/exec', methods=['POST'])
def api_autojs_exec():
    """执行 AutoJS 脚本"""
    config = load_config()
    if not config['autojs']['enabled']:
        return jsonify({"error": "AutoJS not enabled"})
    
    data = request.json
    script = data.get('script', '')
    url = config['autojs']['url']
    
    try:
        response = requests.post(f"{url}/rpc", json={"script": script})
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/autojs/nodes')
def api_autojs_nodes():
    """获取 UI 节点"""
    # 使用 uiautomator2 获取节点
    result = adb_cmd("shell uiautomator dump")
    result2 = adb_cmd("shell cat /sdcard/window_dump.xml")
    
    return jsonify({
        "success": result['success'],
        "xml": result2['stdout']
    })

# ==================== Git 更新 ====================

@app.route('/api/update', methods=['POST'])
def api_update():
    """更新代码"""
    result = run_cmd("git pull origin main")
    return jsonify(result)

@app.route('/api/update/schedule', methods=['POST'])
def api_update_schedule():
    """定时更新配置"""
    data = request.json
    interval = data.get('interval', 3600)  # 默认1小时
    
    # 保存配置
    config = load_config()
    config['update_interval'] = interval
    save_config(config)
    
    return jsonify({"success": True, "interval": interval})

# ==================== 启动 ====================

def start_http_server(config):
    """启动 HTTP 服务器"""
    host = config['server']['host']
    port = config['server']['port']
    
    print(f"🚀 Phone Agent 启动中...")
    print(f"📡 服务器: http://{host}:{port}")
    print(f"🔗 状态页: http://{host}:{port}/")
    
    app.run(host=host, port=port, debug=False)

def auto_update_thread():
    """自动更新线程"""
    config = load_config()
    interval = config.get('update_interval', 3600)
    
    while True:
        time.sleep(interval)
        run_cmd("git pull origin main")

if __name__ == '__main__':
    # 加载配置
    config = load_config()
    
    # 启动自动更新线程
    if config.get('update_interval'):
        t = threading.Thread(target=auto_update_thread)
        t.daemon = True
        t.start()
    
    # 启动服务器
    start_http_server(config)
