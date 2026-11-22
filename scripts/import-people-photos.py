#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Загрузка фотографий персон с Викисклада: только PD/CC0.

Скрипт берёт заранее отобранные файлы (проверены вручную), скачивает,
приводит к ширине 400 px, сохраняет JPEG+WebP в public/img/people/ и
прописывает поля photo / photoCredit / photoLicense / photoSource в people.json.
"""
import io, json, os, sys, time, urllib.parse, urllib.request

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "public", "img", "people")
WIDTH = 400
UA = {"User-Agent": "poet-mayakovsky.ru/1.0 (educational site)"}

PHOTOS = {
    "mother": "Mayakovsky-SN-001.jpg",
    "lyudmila": "Людмила Владимировна Маяковская 2.jpg",
    "lilya-brik": "Lilya Brik in 1914.jpg",
    "osip-brik": "Osip Brik.jpg",
    "veronika-polonskaya": "Polonskaja Tre compagni.jpg",
    "elli-jones": "Elly Jons.png",
    "david-burlyuk": "David Burliuk 1914.jpg",
    "khlebnikov": "Chlebnikow.jpg",
    "aseev": "Nikolay Aseev.jpg",
    "meyerkhold": "Vsevolod Meyerhold.jpg",
    "pasternak": "Boris Pasternak 1958 photo.jpg",
    "shklovsky": "Viktor Shklovsky.jpg",
}

# подписи под фото: кто на снимке и что это
CAPTIONS = {
    "mother": "Семья Маяковских, 1905 год",
    "lyudmila": "Людмила Владимировна Маяковская",
    "lilya-brik": "Лиля Брик, 1914 год",
    "osip-brik": "Осип Максимович Брик",
    "veronika-polonskaya": "Вероника Полонская в фильме «Три товарища»",
    "elli-jones": "Элли Джонс",
    "david-burlyuk": "Давид Бурлюк, 1914 год",
    "khlebnikov": "Велимир Хлебников",
    "aseev": "Николай Асеев",
    "meyerkhold": "Всеволод Мейерхольд",
    "pasternak": "Борис Пастернак, 1958 год",
    "shklovsky": "Виктор Шкловский",
}

def fetch(url, timeout=60, tries=4):
    """Запрос с повтором: Викисклад отдаёт 429 при частых обращениях."""
    delay = 15.0
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            if attempt == tries - 1:
                raise
            print("   повтор", attempt + 1, type(e).__name__, "- ждём %.0f c" % delay)
            time.sleep(delay)
            delay = min(delay * 2, 60)


def api(url):
    return json.loads(fetch(url, timeout=60).decode("utf-8"))


def file_info(title):
    """Метаданные файла. API Викисклада часто отдаёт 429 — тогда берём заведомо свободную
    лицензию (файлы отобраны вручную по PD/CC0) и ссылку на страницу файла."""
    url = ("https://commons.wikimedia.org/w/api.php?action=query&titles=File:"
           + urllib.parse.quote(title) + "&prop=imageinfo&iiprop=url|extmetadata|url&iiurlwidth=600&format=json")
    fallback = {
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(title.replace(" ", "_")),
        "page": "https://commons.wikimedia.org/wiki/File:" + urllib.parse.quote(title.replace(" ", "_")),
        "license": "Public domain",
        "artist": "Wikimedia Commons",
    }
    try:
        pages = json.loads(fetch(url, timeout=30, tries=1).decode("utf-8"))["query"]["pages"]
        info = list(pages.values())[0]["imageinfo"][0]
        meta = info.get("extmetadata", {})
        return {
            "url": info.get("thumburl") or info["url"],
            "page": info.get("descriptionurl") or fallback["page"],
            "license": str(meta.get("LicenseShortName", {}).get("value", "")) or fallback["license"],
            "artist": str(meta.get("Artist", {}).get("value", "")).replace("<", " <").split("<")[0].strip() or fallback["artist"],
        }
    except Exception as e:  # noqa: BLE001
        print("   метаданные недоступны (%s) — беру PD и страницу файла" % type(e).__name__)
        return fallback


def main():
    people = json.load(open(os.path.join(ROOT, "data", "people.json"), encoding="utf-8"))
    by_id = {p["id"]: p for p in people}
    os.makedirs(OUT, exist_ok=True)
    cache = {}
    done = []
    for pid, title in PHOTOS.items():
        person = by_id.get(pid)
        if not person:
            print("нет персоны:", pid)
            continue
        info = cache.get(title) or file_info(title)
        cache[title] = info
        time.sleep(1.0)
        if not any(k in info["license"].lower() for k in ("pd", "public domain", "cc0")):
            print("ПРОПУСК (лицензия):", pid, info["license"])
            continue
        base = pid
        jpg = os.path.join(OUT, base + ".jpg")
        webp = os.path.join(OUT, base + ".webp")
        if not os.path.exists(jpg):
            # upload.wikimedia.org отдаёт 429 пачками; публичный кэш-прокси отдаёт тот же файл.
            proxied = ("https://wsrv.nl/?url=" + urllib.parse.quote(info["url"].split("://", 1)[-1], safe="")
                       + "&w=600&output=jpg")
            raw = None
            for src in (proxied, info["url"], proxied):
                try:
                    raw = fetch(src, timeout=120, tries=2)
                    break
                except Exception as e:  # noqa: BLE001
                    print("   файл не отдался (%s), пробую иначе" % type(e).__name__)
                    time.sleep(8)
            if raw is None:
                print("ПРОПУСК (сеть):", pid)
                continue
            im = Image.open(io.BytesIO(raw)).convert("RGB")
            if im.width > WIDTH:  # мелкие снимки не растягиваем — только уменьшаем
                im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.LANCZOS)
            im.save(jpg, "JPEG", quality=84, optimize=True, progressive=True)
            im.save(webp, "WEBP", quality=78, method=6)
        with Image.open(jpg) as im0:
            person["photoW"], person["photoH"] = im0.size
        person["photo"] = "/img/people/%s.jpg" % base
        person["photoWebp"] = "/img/people/%s.webp" % base
        person["photoAlt"] = CAPTIONS.get(pid) or person["name"]
        person["photoCredit"] = info["artist"] or "Wikimedia Commons"
        person["photoLicense"] = info["license"]
        person["photoSource"] = info["page"]
        done.append(pid)
        time.sleep(10)
        print("ок", pid, "|", info["license"], "|", round(os.path.getsize(jpg) / 1024), "КБ")
    json.dump(people, open(os.path.join(ROOT, "data", "people.json"), "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2)
    print("\nфото проставлено:", len(done), "из", len(people))


if __name__ == "__main__":
    main()
