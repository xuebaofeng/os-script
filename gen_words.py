from gtts import gTTS
# pip install gTTS
import os

# 分组单词
sets = {
    "Basic_Conversation": ["Bienvenidos", "Hispano-hablantes", "Comprensible", "Invitada", "Entrevista"],
    "The_Acting_World": ["Actriz", "Actuación", "Alfombras rojas", "Celebridad", "Puesto en un pedestal", "Papel / Rol", "Libreto"],
    "The_Industry": ["Inestable", "Audicionando", "Castings", "Rechazo", "Perfil", "Industria"],
    "Money_and_Career": ["Estabilidad económica", "Contrato fijo", "Ahorrador", "Finanzas", "Sueldo / Salario"],
    "Emotions_and_Mindset": ["Idealizada", "Romantizado", "Tomárselo personal", "Autoestima"]
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
        tts = gTTS(text=word, lang='es')  # 'es' = 西班牙语
        tts.save(filepath)
        print(f"Saved: {filepath}")

print("✅ 所有音频生成完成！")