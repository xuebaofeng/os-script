import os
import shutil
import csv
from fontTools.ttLib import TTFont, TTCollection

# ================= 配置 =================
SOURCE_DIR = r"C:\fang\fonts"         # 字体源目录
TARGET_DIR = r"C:\Windows\Fonts"
FONT_EXTS = (".ttf", ".otf", ".ttc")

LOG_CSV = "font_install_log.csv"
ROLLBACK_TXT = "font_rollback_list.txt"

# ================= 工具函数 =================
def get_font_names(path):
    """返回字体真实名称集合"""
    names = set()
    try:
        if path.lower().endswith(".ttc"):
            ttc = TTCollection(path)
            for font in ttc.fonts:
                for rec in font["name"].names:
                    if rec.nameID in (1, 4):
                        try:
                            names.add(rec.toUnicode())
                        except:
                            pass
        else:
            font = TTFont(path)
            for rec in font["name"].names:
                if rec.nameID in (1, 4):
                    try:
                        names.add(rec.toUnicode())
                    except:
                        pass
            font.close()
    except Exception as e:
        print(f"⚠ 解析失败 {os.path.basename(path)}: {e}")
    return names

# ================= 已安装自定义字体文件 =================
installed_files = set(fn.lower() for fn in os.listdir(TARGET_DIR) if fn.lower().endswith(FONT_EXTS))
rollback_files = []   # 本次安装记录
log_rows = []         # CSV日志

# ================= 扫描源字体 =================
source_fonts = [
    os.path.join(root, f)
    for root, _, files in os.walk(SOURCE_DIR)
    for f in files
    if f.lower().endswith(FONT_EXTS)
]

fonts_to_install = []
for font_path in source_fonts:
    fname = os.path.basename(font_path).lower()
    if fname in installed_files:
        log_rows.append([font_path, "SKIP", "已安装过"])
        continue
    fonts_to_install.append(font_path)
    installed_files.add(fname)

print(f"准备安装 {len(fonts_to_install)} 个字体")

# ================= 一次性安装 =================
for font in fonts_to_install:
    try:
        shutil.copy2(font, TARGET_DIR)
        rollback_files.append(os.path.join(TARGET_DIR, os.path.basename(font)))
        names = get_font_names(font)
        names_str = ", ".join(names) if names else ""
        log_rows.append([font, "INSTALLED", names_str])
        print(f"✅ 安装: {os.path.basename(font)} ({names_str})")
    except Exception as e:
        log_rows.append([font, "FAIL", str(e)])
        print(f"❌ 失败: {os.path.basename(font)} {e}")

# ================= 写日志 =================
with open(LOG_CSV, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["Font File", "Action", "Note"])
    writer.writerows(log_rows)

# ================= 写回滚列表 =================
with open(ROLLBACK_TXT, "w", encoding="utf-8") as f:
    for p in rollback_files:
        f.write(p + "\n")

print("🎉 字体安装完成")
print(f"📄 安装日志：{LOG_CSV}")
print(f"🧯 回滚清单：{ROLLBACK_TXT}")
print("👉 请【重启 Windows】刷新字体缓存")

# ================= 卸载功能 =================
def uninstall_fonts(rollback_file=ROLLBACK_TXT):
    """卸载本次安装的字体"""
    if not os.path.exists(rollback_file):
        print("⚠ 回滚文件不存在，无法卸载")
        return
    with open(rollback_file, "r", encoding="utf-8") as f:
        paths = [line.strip() for line in f.readlines()]
    for p in paths:
        if os.path.exists(p):
            try:
                os.remove(p)
                print(f"🗑 卸载: {os.path.basename(p)}")
            except Exception as e:
                print(f"⚠ 卸载失败: {os.path.basename(p)} {e}")
        else:
            print(f"⚠ 文件不存在: {os.path.basename(p)}")
    print("🧹 卸载完成，请【重启 Windows】刷新字体缓存")

# 调用卸载示例：
# uninstall_fonts()
