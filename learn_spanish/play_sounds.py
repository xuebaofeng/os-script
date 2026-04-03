import os
import time
import subprocess
from gtts import gTTS

# ----------------------------
# 配置
# ----------------------------
words_file = "words.txt"
output_folder = "spanish_audio"
repeat_times = 1   # 每个单词播放次数
repeat_gap = 1     # 每次播放间隔（秒）
write_gap = 1     # 播放完写字间隔（秒）

# ----------------------------
# 读取单词列表
# ----------------------------
words = []
with open(words_file, "r", encoding="utf-8") as f:
    for line in f:
        word = line.strip()
        if word:
            words.append(word)

# ----------------------------
# 生成 mp3（如果不存在）
# ----------------------------
os.makedirs(output_folder, exist_ok=True)
for word in words:
    filename = word.replace(" ", "_").replace("/", "-") + ".mp3"
    filepath = os.path.join(output_folder, filename)
    if not os.path.exists(filepath):
        tts = gTTS(text=word, lang='es')
        tts.save(filepath)
        print(f"Saved: {filepath}")
    else:
        print(f"Skipped (exists): {filepath}")

# ----------------------------
# 播放音频
# ----------------------------
learned_or_skipped = {}  # 可用于记录已学单词

for word in words:
    if word in learned_or_skipped:
        print(f"Skipped (already learned): {word}")
        continue

    filename = word.replace(" ", "_").replace("/", "-") + ".mp3"
    filepath = os.path.join(output_folder, filename)

    print(f"\nPlaying: {word}")

    for _ in range(repeat_times):
        subprocess.run(["ffplay", "-nodisp", "-autoexit", filepath])
        time.sleep(repeat_gap)

    print("Write now...")
    time.sleep(write_gap)

# ----------------------------
# 播放完成提示音（中文）
# ----------------------------
done_audio_path = os.path.join(output_folder, "done.mp3")
if not os.path.exists(done_audio_path):
    tts = gTTS(text="完成！", lang='zh-cn')  # 中文提示
    tts.save(done_audio_path)

print("\n✅ 所有单词播放完成！播放完成提示音...")
subprocess.run(["ffplay", "-nodisp", "-autoexit", done_audio_path])