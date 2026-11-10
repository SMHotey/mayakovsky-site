#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Миниатюры для хронологии: квадратные превью 200×200 из уже имеющихся фотографий.

Событие в списке — одна строка, поэтому крупные снимки там не нужны: скрипт режет
квадрат по центру, сохраняет JPEG+WebP в public/img/thumbs/ и прописывает
photo / photoWebp / photoAlt в data/timeline.json. Новых загрузок нет.
Запуск: python scripts/import-timeline-photos.py
"""
import json, os

from PIL import Image, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "public", "img", "thumbs")
SIZE = 200

# Событие (по заголовку из data/timeline.json) → (файл в public/, подпись).
# Ключ — заголовок, а не дата: в хронологии есть по два события на 1918 и 1930 год.
EVENTS = {
    "Рождение в Багдади": ("/img/places/baghdati-house.jpg", "Багдати. Дом, в котором родился поэт"),
    "Кутаисская гимназия": ("/img/places/kutaisi-gymnasium.jpg", "Кутаиси, начало 1900-х. Гимназия"),
    "Смерть отца": ("/img/places/baghdati-house.jpg", "Багдати, дом лесничего"),
    "Переезд в Москву": ("/img/era/1910-portrait.jpg", "Владимир Маяковский, около 1910 года"),
    "Исключение из гимназии": ("/img/era/1910-portrait.jpg", "Владимир Маяковский, около 1910 года"),
    "Бутырская тюрьма": ("/img/era/1910-portrait.jpg", "Владимир Маяковский, около 1910 года"),
    "Училище живописи, ваяния и зодчества": ("/img/era/1912-futurists.jpg", "Футуристы, 1912 год"),
    "«Бродячая собака»": ("/img/era/1912-futurists.jpg", "Футуристы, 1912 год"),
    "Сборник «Я» и трагедия": ("/img/era/1914-portrait.jpg", "Владимир Маяковский, 1914 год"),
    "Исключение из училища": ("/img/era/1914-portrait.jpg", "Владимир Маяковский, 1914 год"),
    "Знакомство с Бриками": ("/img/era/1915-brik.jpg", "Маяковский и Лиля Брик, 1915 год"),
    "«Облако в штанах» напечатано": ("/img/era/1915-brik.jpg", "Маяковский и Лиля Брик, 1915 год"),
    "«Простое как мычание»": ("/img/era/1914-portrait.jpg", "Владимир Маяковский, 1914 год"),
    "Арест генерала Секретёва": ("/img/era/1920-portrait.jpg", "Владимир Маяковский, около 1920 года"),
    "«Мистерия-буфф»": ("/img/era/1920-portrait.jpg", "Владимир Маяковский, около 1920 года"),
    "Переезд в Москву и РОСТА": ("/img/era/1920-portrait.jpg", "Время работы в окнах РОСТА"),
    "«150 000 000»": ("/img/era/1920-portrait.jpg", "Владимир Маяковский, около 1920 года"),
    "«Про это» и первые заграничные поездки": ("/img/era/1920-portrait.jpg", "Владимир Маяковский, около 1920 года"),
    "ЛЕФ и журнал": ("/img/era/1927-bulla.jpg", "Владимир Маяковский, 1927 год. Снимок Виктора Буллы"),
    "«Владимир Ильич Ленин»": ("/img/era/1927-bulla.jpg", "Владимир Маяковский, 1927 год"),
    "Поездка в Америку": ("/img/era/1925-mexico.jpg", "Мехико, 1925 год. Снимок Тины Модотти"),
    "Поездки по Союзу": ("/img/era/1927-bulla.jpg", "Владимир Маяковский, 1927 год"),
    "«Хорошо!»": ("/img/era/1927-bulla.jpg", "Владимир Маяковский, 1927 год"),
    "Берлин и Париж": ("/img/era/1927-bulla.jpg", "Владимир Маяковский, 1927 год"),
    "«Клоп» и «Баня»": ("/img/era/1929-worker-cap.jpg", "Владимир Маяковский, 1929 год"),
    "Смерть": ("/img/places/studenetsky-flat.jpg", "Москва, Студенецкий переулок. Мемориальная квартира"),
    "Музей": ("/img/places/moscow-museum.jpg", "Государственный музей В. В. Маяковского"),
}


def square(im):
    im = ImageOps.exif_transpose(im)
    if im.mode != "RGB":
        im = im.convert("RGB")
    # верхняя треть важнее для портретов: режем от верха, а не от центра
    side = min(im.width, im.height)
    left = (im.width - side) // 2
    top = 0 if im.height > im.width else (im.height - side) // 2
    return im.crop((left, top, left + side, top + side)).resize((SIZE, SIZE), Image.Resampling.LANCZOS)


def main():
    os.makedirs(OUT, exist_ok=True)
    data = json.load(open(os.path.join(ROOT, "data", "timeline.json"), encoding="utf-8"))
    done, missing = 0, []
    for event in data:
        spec = EVENTS.get(event["title"])
        if not spec:
            continue
        src, alt = spec
        full = os.path.join(ROOT, "public", src.lstrip("/"))
        if not os.path.exists(full):
            missing.append(src)
            continue
        name = "tl-" + event["date"] + "-" + str(done + 1).zfill(2)
        jpg = os.path.join(OUT, name + ".jpg")
        webp = os.path.join(OUT, name + ".webp")
        with Image.open(full) as im:
            square(im).save(jpg, "JPEG", quality=82, optimize=True, progressive=True)
        with Image.open(jpg) as im:
            im.save(webp, "WEBP", quality=78, method=6)
        event["photo"] = "/img/thumbs/%s.jpg" % name
        event["photoWebp"] = "/img/thumbs/%s.webp" % name
        event["photoAlt"] = alt
        done += 1
    json.dump(data, open(os.path.join(ROOT, "data", "timeline.json"), "w", encoding="utf-8", newline="\n"),
              ensure_ascii=False, indent=2)
    print("миниатюр:", done, "из", len(data), "событий")
    if missing:
        print("НЕТ ФАЙЛОВ:", *missing, sep="\n  ")


if __name__ == "__main__":
    main()
