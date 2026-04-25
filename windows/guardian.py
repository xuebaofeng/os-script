import os
import subprocess
import time
from datetime import datetime, timedelta
import shutil
import psutil
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
import threading

# ---------------- 配置 ----------------

WEB_PASSWORD = "shuangjiaoE#3"


PRIVOXY_ACTIONS = r"C:\Program Files (x86)\Privoxy\user.action"
PRIVOXY_BLOCK_LEARNING_START = "# GUARDIAN_BLOCK_LEARNING_START"
PRIVOXY_BLOCK_LEARNING_END = "# GUARDIAN_BLOCK_LEARNING_END"
PRIVOXY_BLOCK_ENTERTAINMENT_START = "# GUARDIAN_BLOCK_ENTERTAINMENT_START"
PRIVOXY_BLOCK_ENTERTAINMENT_END = "# GUARDIAN_BLOCK_ENTERTAINMENT_END"

DEFAULT_TIME = 30
LOG_FILE = r"guardian.log"

# ---------------- Edge / Roblox ----------------
EDGE_EXE = "msedge.exe"
ROBLOX_EXE = "RobloxPlayerBeta.exe"

# ---------------- 域名分类 ----------------
PRIVOXY_DOMAINS_LEARNING = [
    ".youtube.com",
    ".googlevideo.com",
    ".youtu.be",
]

PRIVOXY_DOMAINS_ENTERTAINMENT = [

    ".roblox.com",
    ".poki.com",
    ".gg",
    ".io",
    ".game",
    ".elftoon.com"
]


# ---------------- 工具 ----------------
def check_password(q):
    return q.get("pwd", [""])[0] == WEB_PASSWORD

def log(msg):
    t = datetime.now().strftime("%H:%M:%S")
    line = f"[{t}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(cmd):
    print(">>>", cmd)
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print("OUT:", r.stdout)
    print("ERR:", r.stderr)


def firewall_exists(name):
    r = subprocess.run(
        f'netsh advfirewall firewall show rule name="{name}"',
        shell=True,
        capture_output=True,
        text=True
    )
    out = r.stdout
    return not ("No rules match" in out or "没有与指定条件匹配的规则" in out)


# ---------------- 防火墙 ----------------
def firewall_on():
    run("netsh advfirewall set allprofiles state on")
    log("🔴 防火墙开启")


def firewall_off():
    run("netsh advfirewall set allprofiles state off")
    log("🟢 防火墙关闭")


# ---------------- Privoxy ----------------
def modify_privoxy(unblock=False, unblock_learning=False, unblock_entertainment=False):
    if not os.path.exists(PRIVOXY_ACTIONS):
        log(f"❌ Privoxy 配置文件不存在: {PRIVOXY_ACTIONS}")
        return

    shutil.copy2(PRIVOXY_ACTIONS, PRIVOXY_ACTIONS + ".bak")

    with open(PRIVOXY_ACTIONS, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    in_learning = False
    in_entertainment = False
    for line in lines:
        s = line.strip()
        if s == PRIVOXY_BLOCK_LEARNING_START:
            in_learning = True
            continue
        if s == PRIVOXY_BLOCK_LEARNING_END:
            in_learning = False
            continue
        if s == PRIVOXY_BLOCK_ENTERTAINMENT_START:
            in_entertainment = True
            continue
        if s == PRIVOXY_BLOCK_ENTERTAINMENT_END:
            in_entertainment = False
            continue
        if not in_learning and not in_entertainment:
            new_lines.append(line)

    # 娱乐域名
    if not unblock or (unblock and not unblock_entertainment):
        new_lines.append(PRIVOXY_BLOCK_ENTERTAINMENT_START + "\n")
        new_lines.append("{+block}\n")
        for d in PRIVOXY_DOMAINS_ENTERTAINMENT:
            new_lines.append(d + "\n")
        new_lines.append(PRIVOXY_BLOCK_ENTERTAINMENT_END + "\n")
        log("🔴 Privoxy 封锁娱乐域名")
    else:
        log("🟢 Privoxy 解封娱乐域名")

    # 学习域名
    if not unblock or (unblock and not unblock_learning):
        new_lines.append(PRIVOXY_BLOCK_LEARNING_START + "\n")
        new_lines.append("{+block}\n")
        for d in PRIVOXY_DOMAINS_LEARNING:
            new_lines.append(d + "\n")
        new_lines.append(PRIVOXY_BLOCK_LEARNING_END + "\n")
        log("🔴 Privoxy 封锁学习域名")
    else:
        log("🟢 Privoxy 解封学习域名")

    with open(PRIVOXY_ACTIONS, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    log("✅ Privoxy 配置已更新")


# ---------------- 查找 Roblox ----------------
def find_roblox():
    paths = []
    base = r"C:\Users"
    for user in os.listdir(base):
        user_path = os.path.join(base, user)
        if not os.path.isdir(user_path):
            continue
        roblox_dir = os.path.join(user_path, r"AppData\Local\Roblox\Versions")
        if not os.path.exists(roblox_dir):
            continue
        for ver in os.listdir(roblox_dir):
            exe_path = os.path.join(roblox_dir, ver, ROBLOX_EXE)
            if os.path.exists(exe_path):
                paths.append(exe_path)
    return paths


# ---------------- 封锁 ----------------

def find_edge():
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def block_edge():
    path = find_edge()
    if not path:
        log("❌ 未找到 Edge")
        return

    run('netsh advfirewall firewall delete rule name="Allow Edge Privoxy"')
    run('netsh advfirewall firewall delete rule name="Block Edge All"')

    run(f'netsh advfirewall firewall add rule name="Allow Edge Privoxy" dir=out action=allow program="{path}" protocol=TCP remoteip=127.0.0.1 remoteport=8118')

    run(f'netsh advfirewall firewall add rule name="Block Edge All" dir=out action=block program="{path}" protocol=ANY')

    log("🔒 Edge 只允许走 Privoxy")


# ---------------- Process Management ----------------
def kill_roblox_processes():
    """Kill all Roblox-related processes"""
    killed_count = 0
    roblox_processes = []

    # Common Roblox process names
    roblox_names = [
        "RobloxPlayerBeta.exe",
        "RobloxPlayerLauncher.exe",
        "RobloxStudioBeta.exe",
        "RobloxStudioLauncher.exe",
        "RobloxCrashHandler.exe"
    ]

    for proc in psutil.process_iter(['pid', 'name']):
        try:
            process_name = proc.info['name']
            if process_name in roblox_names:
                roblox_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    # Kill found Roblox processes
    for proc in roblox_processes:
        try:
            proc.terminate()
            killed_count += 1
            log(f" Killed Roblox process: {proc.info['name']} (PID: {proc.pid})")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            try:
                proc.kill()
                killed_count += 1
                log(f" Force killed Roblox process: {proc.info['name']} (PID: {proc.pid})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                log(f" Failed to kill Roblox process: {proc.info['name']} (PID: {proc.pid})")

    if killed_count == 0:
        log(" No Roblox processes found running")
    else:
        log(f" Killed {killed_count} Roblox process(es)")

    return killed_count


def block_roblox(unblock=False):
    paths = find_roblox()
    rule = "Block Roblox All"
    if not paths:
        log(f"❌ 未找到 {ROBLOX_EXE}")
        return
    if unblock:
        if firewall_exists(rule):
            run(f'netsh advfirewall firewall delete rule name="{rule}"')
        log("🟢 Roblox 已解封")
    else:
        if not firewall_exists(rule):
            for p in paths:
                run(f'netsh advfirewall firewall add rule name="{rule}" dir=out action=block program="{p}" protocol=ANY')
        kill_roblox_processes()
        log("❌ Roblox 封锁（所有网络）")


# ---------------- 统一封锁/解封 ----------------
def apply_block(unblock=False, unblock_type=None):
    firewall_on()
    block_edge()
    if unblock_type == "all":
        block_roblox(unblock=True)
        modify_privoxy(unblock=True, unblock_learning=True, unblock_entertainment=True)
    elif unblock_type == "learning":
        block_roblox(unblock=False)
        modify_privoxy(unblock=True, unblock_learning=True, unblock_entertainment=False)
    else:
        block_roblox(unblock=False)
        modify_privoxy(unblock=False)


def immediate_lockdown():
    """立即封锁所有访问"""
    global unblock_end_time, unblock_type
    unblock_end_time = None
    unblock_type = None
    apply_block(unblock=False)
    log("🚨 立即封锁所有访问")


# ---------------- Web ----------------
unblock_end_time = None
unblock_type = None



class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global unblock_end_time, unblock_type
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            html_content = '''
            <html>
                <head><meta charset="utf-8"><title>Guardian Control</title></head>
                <body>
                    <h1>Guardian Web Control</h1>
                    <form method="get" action="/unblock">
                        <label>解封类型:</label>
                        <select name="type">
                            <option value="learning">学习域名</option>
                            <option value="all">全部</option>
                        </select>
                        <label>分钟数:</label>
                        <input type="number" name="time" value="30" min="1" max="180">
                        <button type="submit">解封</button>
                    </form>
                    <br>
                    <form method="get" action="/lockdown">
                        <button type="submit" style="background-color: red; color: white; padding: 10px 20px; border: none; border-radius: 5px;">🚨 立即封锁</button>
                    </form>
                    <p>查看 <a href="/status">状态</a></p>
                </body>
            </html>
            '''
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html_content.encode("utf-8"))
        elif parsed.path == "/unblock":
            q = urllib.parse.parse_qs(parsed.query)
            if not check_password(q):
                self.send_response(403)
                self.end_headers()
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.wfile.write("❌ 密码错误".encode())
                return
            t = q.get("type", ["learning"])[0]
            m = int(q.get("time", [30])[0])
            unblock_end_time = datetime.now() + timedelta(minutes=m)
            unblock_type = t
            apply_block(unblock=True, unblock_type=t)
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"✅ 已解封 {t} {m} 分钟".encode("utf-8"))
        elif parsed.path == "/lockdown":
            immediate_lockdown()
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("🚨 已立即封锁所有访问".encode("utf-8"))
        elif parsed.path == "/status":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            now = datetime.now()
            if unblock_end_time:
                remaining = max(0, int((unblock_end_time - now).total_seconds() / 60))
                self.wfile.write(f"剩余解封时间: {remaining} 分钟, 类型: {unblock_type}".encode("utf-8"))
            else:
                self.wfile.write("当前全封锁状态".encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def run_web():
    server = HTTPServer(("0.0.0.0", 8090), Handler)
    log("🌐 Web control running on port 8090")
    server.serve_forever()


# ---------------- 主循环 ----------------
def loop():
    global unblock_end_time, unblock_type
    apply_block(unblock=False)
    threading.Thread(target=run_web, daemon=True).start()
    while True:
        now = datetime.now()
        if unblock_end_time and now >= unblock_end_time:
            unblock_end_time = None
            unblock_type = None
            apply_block(unblock=False)
            log("🔴 恢复全封锁状态")
        time.sleep(60)



# ---------------- 启动 ----------------
if __name__ == "__main__":
    try:
        loop()
    except Exception as e:
        print("FATAL ERROR:", e)
        input("Press Enter to exit...")
