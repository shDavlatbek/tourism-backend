import os
import re

translations = {
    "en": {
        "Vergul bilan ajratilgan faoliyatlarni kiriting (masalan: hiking, swimming)": "Enter comma separated activities (e.g., hiking, swimming)",
        "Vergul bilan ajratilgan SEO taglarni kiriting (masalan: tourism, nature)": "Enter comma separated SEO tags (e.g., tourism, nature)",
        "Ko'rish": "View",
        "Asosiy": "Main",
        "SEO": "SEO",
        "Koordinatalar": "Coordinates",
        "Rasm": "Image",
        "Haqida": "About",
        "Nomi": "Name",
        "Qisqa tavsif": "Short description",
        "Slug": "Slug",
        "Tartib": "Order",
        "Shahar": "City",
        "Shaharlar": "Cities",
        "Tavsif": "Description",
        "Kenglik (lat)": "Latitude (lat)",
        "Uzunlik (long)": "Longitude (long)",
        "SEO taglar": "SEO tags",
        "Faoliyatlar": "Activities",
        "Qishloq": "Village",
        "Qishloqlar": "Villages",
        "Galereya": "Gallery",
        "Izoh": "Comment",
        "To'liq ism": "Full name",
        "Kim (kasbi, qishloq aholisi va h.k.)": "Who (profession, villager, etc.)",
        "Izohlar": "Comments",
        "Haqida sarlavha": "About title",
        "Haqida tavsif": "About description",
        "Fon rasmi": "Background image",
        "Asosiy sozlamalar": "Main settings"
    },
    "ru": {
        "Vergul bilan ajratilgan faoliyatlarni kiriting (masalan: hiking, swimming)": "Введите занятия через запятую (например, hiking, swimming)",
        "Vergul bilan ajratilgan SEO taglarni kiriting (masalan: tourism, nature)": "Введите SEO-теги через запятую (например, tourism, nature)",
        "Ko'rish": "Просмотр",
        "Asosiy": "Основное",
        "SEO": "SEO",
        "Koordinatalar": "Координаты",
        "Rasm": "Изображение",
        "Haqida": "О нас",
        "Nomi": "Название",
        "Qisqa tavsif": "Краткое описание",
        "Slug": "Слаг",
        "Tartib": "Порядок",
        "Shahar": "Город",
        "Shaharlar": "Города",
        "Tavsif": "Описание",
        "Kenglik (lat)": "Широта (lat)",
        "Uzunlik (long)": "Долгота (long)",
        "SEO taglar": "SEO теги",
        "Faoliyatlar": "Активности",
        "Qishloq": "Деревня",
        "Qishloqlar": "Деревни",
        "Galereya": "Галерея",
        "Izoh": "Комментарий",
        "To'liq ism": "Полное имя",
        "Kim (kasbi, qishloq aholisi va h.k.)": "Кто (профессия, житель села и т.д.)",
        "Izohlar": "Комментарии",
        "Haqida sarlavha": "Заголовок о нас",
        "Haqida tavsif": "Описание о нас",
        "Fon rasmi": "Фоновое изображение",
        "Asosiy sozlamalar": "Основные настройки"
    },
    "uz": {}
}

for k in translations["en"].keys():
    translations["uz"][k] = k

def fill_po(file_path, trans_dict):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('msgid '):
            msgid_val = line[len('msgid '):].strip().strip('"')
            orig_msgid_lines = [line]
            
            j = i + 1
            while j < len(lines) and lines[j].startswith('"') and lines[j].strip().endswith('"'):
                msgid_val += lines[j].strip().strip('"')
                orig_msgid_lines.append(lines[j])
                j += 1
                
            if j < len(lines) and lines[j].startswith('msgstr ""'):
                if msgid_val in trans_dict and msgid_val != "":
                    out.extend(orig_msgid_lines)
                    out.append(f'msgstr "{trans_dict[msgid_val]}"\n')
                    i = j + 1
                    continue
        out.append(line)
        i += 1
            
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(out)

base_dir = r"c:\Users\Xensa\Desktop\bmsb-temp\locale"
for lang in ['en', 'ru', 'uz']:
    path = os.path.join(base_dir, lang, "LC_MESSAGES", "django.po")
    fill_po(path, translations[lang])
    print(f"Filled {path}")
