import os
import time
import subprocess

base_folder = "spanish_audio"
repeat_gap = 1
write_gap = 1

learned_or_skipped = {
    "Estabilidad económica",

    "Romantizado",
    "Idealizada",
    "La esperanza",
    "De la noche a la mañana",
    "Autoestima",
    "Esperando",
    "Comprensible",
    "Invitada"

    "Actriz",
    "Actuación",
    "Celebridad",
    "Extra",
    "Figurante",
    "Papel",
    "Papel secundario",
    "Rol",
    "Audicionando",
    "Casting",
    "Castings",
    "Industria",
    "Inestable",
    "Perfil",
    "Salario",
    "Sobrevivir"
}

for set_name in sorted(os.listdir(base_folder)):
    set_path = os.path.join(base_folder, set_name)
    if not os.path.isdir(set_path):
        continue

    print(f"\n=== Dictation Set: {set_name} ===")

    for filename in sorted(os.listdir(set_path)):
        filepath = os.path.join(set_path, filename)
        print(f"\nPlaying {set_name} - {filename}")

        # 如果单词已经学过，跳过
        word = os.path.splitext(filename)[0].replace("_", " ").replace("-", "/")
        if word in learned_or_skipped:
            print(f"Skipped (already learned): {word}")
            continue

        # 播放两遍
        subprocess.run(["ffplay", "-nodisp", "-autoexit", filepath])
        time.sleep(repeat_gap)
        subprocess.run(["ffplay", "-nodisp", "-autoexit", filepath])

        print("Write now...")
        time.sleep(write_gap)