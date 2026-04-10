import os
import time
import subprocess
from gtts import gTTS

# ----------------------------
# 配置
# ----------------------------
words_file = "words.txt"
output_folder = "spanish_audio"
repeat_times = 2   # 每个单词播放次数
repeat_gap = 2     # 每次播放间隔（秒）
write_gap = 5      # 播放完写字间隔（秒）

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
# 创建输出文件夹
# ----------------------------
os.makedirs(output_folder, exist_ok=True)

# ----------------------------
# 播放音频（播放前生成）
# ----------------------------
learned_or_skipped = {}  # 可用于记录已学单词

for word in words:
    if word in learned_or_skipped:
        print(f"Skipped (already learned): {word}")
        continue

    filename = word.replace(" ", "_").replace("/", "-") + ".mp3"
    filepath = os.path.join(output_folder, filename)

    # 如果文件不存在，先生成
    if not os.path.exists(filepath):
        print(f"Generating audio for: {word}")
        tts = gTTS(text=word, lang='es')
        tts.save(filepath)

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