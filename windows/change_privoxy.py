import shutil
import re

config_path = r"C:\Program Files (x86)\Privoxy\config.txt"
log_path = r"D:\github\os-script\windows\privoxy.log"

backup_path = config_path + ".bak"

# 1. 备份
shutil.copy2(config_path, backup_path)

with open(config_path, "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

new_lines = []

for line in lines:

    # ① 修改 logfile
    if re.match(r"^\s*logfile\s+", line):
        new_lines.append(f"logfile {log_path}\n")
        continue

    # ② 修改 debug 行（去掉开头 #）
    if re.match(r"^\s*#\s*debug\s+1024", line):
        # 保留后半段说明文字
        line = re.sub(r"^\s*#\s*", "", line)

    new_lines.append(line)

with open(config_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("✅ 修改完成")
print(f"备份文件: {backup_path}")