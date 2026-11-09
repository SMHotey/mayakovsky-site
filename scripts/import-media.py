# Скачивание портрета и фотографий эпохи/мест с Викисклада для mayakovsky-site.
#   python scripts/import-media.py [--force] [--only era/1910-stroganov]
# Скачивает только свободные лицензии (PD/CC0/CC BY/CC BY-SA), пишет JPEG+WebP,
# собирает data/media.json — манифест с автором, лицензией и ссылкой на файл.
import io, json, os, re, subprocess, sys, time, urllib.parse

from PIL import Image, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "MayakovskySiteBot/1.0 (https://poet-mayakovsky.ru; media import)"
API = "https://commons.wikimedia.org/w/api.php"
FOLDER_WIDTH = {"portrait": 600, "era": 1100, "places": 1600}
FORCE = "--force" in sys.argv
ONLY = ""
if "--only" in sys.argv:
    ONLY = sys.argv[sys.argv.index("--only") + 1]

BAD = ("добросовестное", "fair use", "non-free", "несвобод", "gfdl")
GOOD = ("public domain", "pd", "cc0", "cc by", "cc-by", "attribution")


def curl(url, binary=False, tries=5):
    """urllib на этой машине падает на TLS-перехвате антивируса — качаем curl'ом."""
    delay = 4.0
    for a in range(tries):
        p = subprocess.run(["curl", "-fsSL", "--max-time", "120", "-A", UA, url],
                           capture_output=True)
        if p.returncode == 0 and p.stdout:
            return p.stdout if binary else p.stdout.decode("utf-8")
        if a == tries - 1:
            raise SystemExit("не удалось скачать: " + url + "\n" + p.stderr.decode("utf-8", "replace")[:300])
        print("   повтор", a + 1, "- ждём %.0f c" % delay)
        time.sleep(delay)
        delay = min(delay * 2, 60)


UNKNOWN = ("unknown", "unidentified", "anonimous", "anonymous")


def credit(raw, override=""):
    """«Unknown authorUnknown author» → «Неизвестный фотограф»; остальное — как на Викискладе."""
    if override:
        return override
    s = " ".join((raw or "").split())
    half = len(s) // 2
    if half and s[:half].strip().lower() == s[half:].strip().lower():
        s = s[:half].strip()
    low = s.lower()
    if not s or low.startswith(UNKNOWN):
        return "Неизвестный фотограф"
    if "official website of the government of moscow" in low:
        return "Правительство Москвы (mos.ru)"
    return s


def strip(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


def metadata(title):
    params = {"action": "query", "format": "json", "titles": title,
              "prop": "imageinfo", "iiprop": "url|size|extmetadata"}
    url = API + "?" + urllib.parse.urlencode(params)
    d = None
    for a in range(6):
        try:
            d = json.loads(curl(url))
            break
        except json.JSONDecodeError:
            # на серии запросов Викимедиа отдаёт HTML/пустоту вместо JSON (429) — ждём и повторяем
            wait = min(4 * (a + 1), 40)
            print("   API не JSON, ждём %d c" % wait)
            time.sleep(wait)
    if not d:
        raise SystemExit("API не ответил JSON: " + title)
    page = next(iter(d["query"]["pages"].values()))
    ii = (page.get("imageinfo") or [None])[0]
    if not ii:
        raise SystemExit("нет imageinfo: " + title)
    em = ii.get("extmetadata", {})

    def g(k):
        return strip((em.get(k, {}) or {}).get("value", ""))

    return {
        "url": ii["url"],
        "page": ii.get("descriptionurl") or ii.get("canonicaltitle", ""),
        "license": g("LicenseShortName"),
        "licenseUrl": (em.get("LicenseUrl", {}) or {}).get("value", ""),
        "artist": g("Artist") or "Unknown author",
        "credit": g("Credit"),
        "date": g("DateTimeOriginal"),
        "description": g("ImageDescription"),
        "width": ii["width"], "height": ii["height"],
    }


def check_license(m):
    lic = m["license"].lower()
    if any(b in lic for b in BAD) or not any(g in lic for g in GOOD):
        return False
    return True


# ручной кроп «(left, top, right, bottom)» в долях кадра: убираем машину/дорогу с переднего плана
CROP = {}  # ручной кроп по ключу, если понадобится


def save(im, jpg, webp, width, crop=None):
    im = ImageOps.exif_transpose(im)
    if im.mode != "RGB":
        im = im.convert("RGB")
    if crop and len(crop) == 4:
        im = im.crop(crop)
        if im.width > width:
            im = im.resize((width, round(im.height * width / im.width)), Image.Resampling.LANCZOS)
    elif crop:
        im = ImageOps.fit(im, crop, Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    elif im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.Resampling.LANCZOS)
    im.save(jpg, "JPEG", quality=84, optimize=True, progressive=True)
    im.save(webp, "WEBP", quality=80, method=6)
    return im.size


def grab(key, folder, title, alt, caption="", crop=None):
    # портрет лежит прямо в public/img/portrait.jpg, без подпапки
    sub = "" if folder == "portrait" else folder
    out = os.path.join(ROOT, "public", "img", sub) if sub else os.path.join(ROOT, "public", "img")
    os.makedirs(out, exist_ok=True)
    jpg = os.path.join(out, key + ".jpg")
    webp = os.path.join(out, key + ".webp")
    m = metadata("File:" + title if not title.startswith("File:") else title)
    print("%-34s %s | %s | %s" % (folder + "/" + key, "%sx%s" % (m["width"], m["height"]), m["license"], m["artist"][:40]))
    if not check_license(m):
        print("   ПРОПУСК: несвободная лицензия —", m["license"])
        return None
    width = FOLDER_WIDTH.get(folder, 1600)
    if FORCE or not (os.path.exists(jpg) and os.path.exists(webp)):
        im = None
        for attempt in range(4):
            raw = curl(m["url"], binary=True)
            try:
                im = Image.open(io.BytesIO(raw))
                im.load()
                break
            except Exception:
                # Викимедиа на серии отдаёт HTML-ошибку вместо файла
                wait = min(8 * (attempt + 1), 45)
                print("   файл не картинка (%d байт), ждём %d c" % (len(raw), wait))
                time.sleep(wait)
        if im is None:
            print("   ПРОПУСК: не удалось скачать файл")
            return None
        box = None
        if key in CROP:
            iw, ih = im.size
            l, t, r, b = CROP[key]
            box = (round(iw * l), round(ih * t), round(iw * r), round(ih * b))
        w, h = save(im, jpg, webp, width,
                    crop=(width, round(width * 4 / 3)) if folder == "portrait" else box)
        print("   ->", "%dx%d" % (w, h))
    with Image.open(jpg) as im0:
        w, h = im0.size
    time.sleep(1.2)
    rel = ("/img/%s/%s" % (folder, key)) if folder != "portrait" else ("/img/%s" % key)
    return {
        "file": rel + ".jpg",
        "webp": rel + ".webp",
        "width": w, "height": h,
        "alt": alt,
        "caption": caption,
        "author": credit(m["artist"], AUTHOR_OVERRIDE.get(key, "")),
        "license": m["license"],
        # у PD-шаблонов Викисклада в extmetadata нет LicenseUrl — ставим канонический
        "licenseUrl": m["licenseUrl"] or ("https://creativecommons.org/publicdomain/mark/1.0/"
                                         if re.search(r"public domain|pd", m["license"], re.I) else ""),
        "date": m["date"],
        "commonsTitle": title if title.startswith("File:") else "File:" + title,
        "source": m["page"],
    }


# подписи, которые нельзя взять из extmetadata: там текст шаблона лицензии, а не имя
AUTHOR_OVERRIDE = {"studenetsky-flat": "Правительство Москвы (mos.ru)"}

# ---------- план: фотографии эпохи ----------
ERA = {
    "1910-portrait": ("Mayakovsky-1910.jpg",
        "Владимир Маяковский, около 1910 года",
        "Около 1910 года"),
    "1912-futurists": ("Mayakovsky and Futurists.jpg",
        "Группа футуристов 1912 года: Хлебников, Кузьмин, Долинский, Бурлюки, Маяковский",
        "1912 год. Сидят: Хлебников, Кузьмин, Долинский; стоят: Н. Бурлюк, Д. Бурлюк, Маяковский"),
    "1914-portrait": ("Vladimir Mayakovsky 1914.jpg",
        "Владимир Маяковский, 1914 год",
        "1914 год — год «Облака в штанах» и первых выступлений футуристов"),
    "1915-brik": ("Vladimir mayakovsky and lilya brik.jpg",
        "Владимир Маяковский и Лиля Брик, 1915 год",
        "1915 год. Маяковский и Лиля Брик"),
    "1920-portrait": ("Majakovszkij.jpg",
        "Владимир Маяковский, около 1920 года",
        "Около 1920 года — время работы в окнах РОСТА"),
    "1925-mexico": ("Mayakovsky and Moreno by Modotti 1925.jpg",
        "Владимир Маяковский и Франсиско Морено, Мехико, 1925 год. Фотография Тины Модотти",
        "Мехико, 1925 год. Снимок Тины Модотти"),
    "1927-bulla": ("Vladimir Mayakovsky 1927.jpg",
        "Владимир Маяковский, 1927 год. Фотография Виктора Буллы",
        "1927 год. Снимок Виктора Буллы"),
    "1929-worker-cap": ("Портрет В.В. Маяковского в рабочей кепке.jpg",
        "Владимир Маяковский в рабочей кепке, 1929 год",
        "1929 год. Портрет в рабочей кепке"),
}

# ---------- план: места ----------
PLACES = {
    "baghdati-house": ("Mayakovsky House Museum 2.jpg",
        "Дом в Багдати (Имеретия, Грузия), где родился Владимир Маяковский",
        "Багдати. Дом, в котором родился поэт; ныне музей"),
    "kutaisi-gymnasium": ("Kutaisi gymnasium (early 1900s).jpg",
        "Здание Кутаисской гимназии, начало 1900-х годов",
        "Кутаиси, начало 1900-х. Гимназия, где учился Маяковский"),
    "moscow-museum": ("Mayakovsky2.jpg",
        "Государственный музей В. В. Маяковского на Лубянском проезде в Москве",
        "Москва, Лубянский проезд. Государственный музей В. В. Маяковского"),
    "briks-house": ("Moscow, Mayakovskogo Lane.jpg",
        "Дом Бриков в Маяковском переулке в Москве, где поэт жил в 1920-е годы",
        "Москва, Маяковский переулок. Здесь, у Бриков, Маяковский жил в 1920-е"),
    "pushkino-dacha": ("Russia, Moskovskaja Oblast, Pushkino, Пушкино, Акулова гора, 7 - Здание дачи, которую снимал В. Маяковский (Пушкино) WMID6895795.jpg",
        "Дача на Акуловой горе в Пушкино, которую Маяковский снимал летом",
        "Пушкино, Акулова гора. Дача, которую снимал Маяковский"),
    "studenetsky-flat": ("Мемориальная квартира В. Маяковского в Студенецком переулке.jpg",
        "Мемориальная квартира Маяковских в Студенецком переулке, Москва",
        "Москва, Студенецкий переулок. Мемориальная квартира"),
}

PORTRAIT = ("Mayakovsky Vladimir.jpg",
    "Портрет Владимира Маяковского",
    "Владимир Маяковский. Фотография, до 1930 года")


def main():
    manifest = {"portrait": None, "era": [], "places": [], "generatedBy": "scripts/import-media.py"}
    keep = {}
    path = os.path.join(ROOT, "data", "media.json")
    if os.path.exists(path):
        try:
            keep = json.load(open(path, encoding="utf-8"))
        except Exception:
            keep = {}

    plan = [("portrait", "portrait", PORTRAIT[0], PORTRAIT[1], PORTRAIT[2])]
    plan += [("era", k, v[0], v[1], v[2]) for k, v in ERA.items()]
    plan += [("places", k, v[0], v[1], v[2]) for k, v in PLACES.items()]

    for folder, key, title, alt, caption in plan:
        tag = folder + "/" + key
        if ONLY and ONLY not in (tag, folder, key):
            if folder == "era" and key in ERA:
                continue
            if folder == "places" and key in PLACES:
                continue
            if folder == "portrait":
                continue
        got = grab(key, folder, title, alt, caption)
        if not got:
            continue
        if folder == "portrait":
            manifest["portrait"] = got
        else:
            manifest[folder].append(got)

    if ONLY:
        print("\nскачан только", ONLY, "— data/media.json не перезаписан")
        return

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("\ndata/media.json: портрет + %d эпоха + %d места" % (len(manifest["era"]), len(manifest["places"])))


if __name__ == "__main__":
    main()
