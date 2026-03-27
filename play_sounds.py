import os
import time
import subprocess

base_folder = "spanish_audio"
repeat_gap = 1
write_gap = 4

for set_name in sorted(os.listdir(base_folder)):
    set_path = os.path.join(base_folder, set_name)
    if not os.path.isdir(set_path):
        continue

    print(f"\n=== Dictation Set: {set_name} ===")

    for filename in sorted(os.listdir(set_path)):
        filepath = os.path.join(set_path, filename)
        print(f"\nPlaying {set_name} - {filename}")

        # 播放两遍
        subprocess.run(["ffplay", "-nodisp", "-autoexit", filepath])
        time.sleep(repeat_gap)
        subprocess.run(["ffplay", "-nodisp", "-autoexit", filepath])

        print("Write now...")
        time.sleep(write_gap)