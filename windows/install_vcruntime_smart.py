import os
import subprocess
from pathlib import Path
from datetime import datetime
import winreg

# -----------------------------
CACHE_DIR = Path(r"C:\shared\os\VCppCache")
LOG_FILE = CACHE_DIR / "install_log.txt"

# VC++ Runtime 包列表，包括低版本用于测试
VC_PACKAGES = [
    {"winget": "Microsoft.VCRedist.2015+.x64", "name": "vc_redist_2015_2022_x64.exe", "pattern": "*v14*X64*.exe", "version": "14.50"},
    {"winget": "Microsoft.VCRedist.2015+.x86", "name": "vc_redist_2015_2022_x86.exe", "pattern": "*v14*X86*.exe", "version": "14.50"},
    {"winget": "Microsoft.VCRedist.2013.x64", "name": "vc_redist_2013_x64.exe", "pattern": "*2013*X64*.exe", "version": "12.0"},
    {"winget": "Microsoft.VCRedist.2013.x86", "name": "vc_redist_2013_x86.exe", "pattern": "*2013*X86*.exe", "version": "12.0"},
    {"winget": "Microsoft.VCRedist.2012.x64", "name": "vc_redist_2012_x64.exe", "pattern": "*2012*X64*.exe", "version": "11.0"},
    {"winget": "Microsoft.VCRedist.2012.x86", "name": "vc_redist_2012_x86.exe", "pattern": "*2012*X86*.exe", "version": "11.0"},
    # ---------- 新增低版本用于测试 ----------
    {"winget": "Microsoft.VCRedist.2010.x64", "name": "vc_redist_2010_x64.exe", "pattern": "*2010*X64*.exe", "version": "10.0"},
    {"winget": "Microsoft.VCRedist.2010.x86", "name": "vc_redist_2010_x86.exe", "pattern": "*2010*X86*.exe", "version": "10.0"},
    {"winget": "Microsoft.VCRedist.2008.x64", "name": "vc_redist_2008_x64.exe", "pattern": "*2008*X64*.exe", "version": "9.0"},
    {"winget": "Microsoft.VCRedist.2008.x86", "name": "vc_redist_2008_x86.exe", "pattern": "*2008*X86*.exe", "version": "9.0"},
]

# -----------------------------
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] {msg}"
    print(full_msg)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(full_msg + "\n")

# -----------------------------
def is_vc_installed(version, arch):
    uninstall_keys = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
    ]
    for root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
        for key_path in uninstall_keys:
            try:
                with winreg.OpenKey(root, key_path) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        subkey_name = winreg.EnumKey(key, i)
                        try:
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                display_version = winreg.QueryValueEx(subkey, "DisplayVersion")[0]
                                if version in display_name or version in display_version:
                                    if arch == "x64" and "x64" in display_name:
                                        return True
                                    if arch == "x86" and "x86" in display_name:
                                        return True
                        except FileNotFoundError:
                            continue
            except FileNotFoundError:
                continue
    return False

# -----------------------------
def download_and_rename(winget_id, safe_name, pattern):
    target_path = CACHE_DIR / safe_name
    if target_path.exists():
        log(f"{safe_name} already exists. Skipping download.")
        return
    log(f"Downloading {safe_name} ...")
    subprocess.run(["winget", "download", winget_id, "-d", str(CACHE_DIR)], check=True)
    files = list(CACHE_DIR.glob(pattern))
    if files:
        latest_file = max(files, key=lambda f: f.stat().st_mtime)
        latest_file.rename(target_path)
        log(f"Renamed {latest_file.name} -> {safe_name}")
    else:
        log(f"No downloaded file found for pattern {pattern}")

# -----------------------------
def install_exe(exe_name):
    path = CACHE_DIR / exe_name
    if path.exists():
        log(f"Installing {exe_name} ...")
        subprocess.run([str(path), "/install", "/quiet", "/norestart"], check=True)
    else:
        log(f"{exe_name} not found, skipping.")

# -----------------------------
def main():
    log("=== START VC++ Runtime Smart Deployment with Low Versions ===")
    for pkg in VC_PACKAGES:
        arch = "x64" if "x64" in pkg["name"] else "x86"
        if is_vc_installed(pkg["version"], arch):
            log(f"{pkg['name']} already installed, skipping.")
            continue
        download_and_rename(pkg["winget"], pkg["name"], pkg["pattern"])
        install_exe(pkg["name"])
    log("=== ALL DONE ===")
    log(f"Log file: {LOG_FILE}")
    print(f"Installation complete. See log: {LOG_FILE}")

if __name__ == "__main__":
    main()