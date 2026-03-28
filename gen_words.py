from gtts import gTTS
# pip install gTTS
import os

# 分组单词
sets = {
    "Basic_Conversation": [
        "Bienvenidos",
        "Comprensible",
        "Entrevista",
        "Hispano-hablantes",
    ],
    "The_Acting_World": [
        # "Actriz",
        # "Actuación",
        "Alfombras rojas",
        # "Celebridad",
        # "Extra",
        # "Figurante",
        "Libreto",
        # "Papel",
        # "Papel secundario",
        "Puesto en un pedestal",
        # "Rol"
    ],
    "The_Industry": [
        # "Audicionando",
        # "Casting",
        # "Castings",
        "Darse a conocer",
        "Hacer cola",
        # "Industria",
        # "Inestable",
        # "Perfil",
        "Persuadir",
        "Rechazo"
    ],
    "Money_and_Career": [
        "Ahorrador",
        "Contrato fijo",
        "Estar en quiebra",
        "Finanzas",
        # "Salario",
        "Sueldo",
        # "Sobrevivir",
        "Valer la pena"
    ],
    "Emotions_and_Mindset": [
        "Ensayando",
        "Luchando",
        "Tocar fondo",
        "Tomárselo personal"
    ],
    "wrong": [
        "Alemania"
    ]
}

output_folder = "spanish_audio"
os.makedirs(output_folder, exist_ok=True)

for set_name, words in sets.items():
    set_folder = os.path.join(output_folder, set_name)
    os.makedirs(set_folder, exist_ok=True)
    for word in words:
        # 替换特殊字符以便文件名合法
        filename = word.replace(" ", "_").replace("/", "-") + ".mp3"
        filepath = os.path.join(set_folder, filename)

        # 如果文件已存在，跳过
        if os.path.exists(filepath):
            print(f"Skipped (exists): {filepath}")
            continue

        tts = gTTS(text=word, lang='es')  # 'es' = 西班牙语
        tts.save(filepath)
        print(f"Saved: {filepath}")

print("✅ 所有音频生成完成！")