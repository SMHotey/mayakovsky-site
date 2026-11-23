# HANDOFF: сайт о Владимире Маяковском

Проект: `mayakovsky-site` (рабочий каталог `C:\Users\malik\mayakovsky-site`), пакет автора — `C:\Users\malik\author-materials\mayakovsky`.
Домен: `https://poet-mayakovsky.ru` — работает с 22–23.11.2026: NS Cloudflare, 4×A на 185.199.108–111.153, HTTPS-сертификат GitHub approved (до 21.02.2027), `https_enforced=true`, http→https 301, www→apex 301.
Состояние: содержание и функции на уровне остальных сайтов серии; Pages включён (source = GitHub Actions), деплой-воркфлоу проходит, Метрика № 114509180 вписана, домен и HTTPS настроены. Осталось: подтверждение в Google Search Console и Яндекс.Вебмастере, IndexNow-обход.

## Что уже сделано

- Каркас: сгенерирован через `wr new` (skill `writer-site-factory`), затем переписан под Маяковского. В генераторе `new_author_site.py` исправлены падежи адъективных фамилий («Маяковского», «Маяковскому»), творительный падеж для фамилий на «-ой», `adjective_stem`.
- Библиотека: 390 текстов из Викитеки (329 стихотворений, 14 поэм, 10 пьес, 32 статьи, 4 очерка, автобиография «Я сам»). Импорт — `scripts/import-works.mjs` + `scripts/html-text.mjs`, кэши `data/raw-cache.json` (wikitext) и `data/raw-html.json` (HTML), офлайн-повтор `SKIP_WIKI=1`.
- 273 записи из списка Викитеки отсутствуют: сервер отдаёт 404, страниц с такими названиями нет. Это в основном статьи Маяковского о собственных пьесах, подписи к окнам РОСТА, заметки из «Нового Лефа».
- Данные: `timeline.json` (27 дат), `people.json` (16), `places.json` (13 с фото), `museums.json` (с фото), `monuments.json`, `sources.json`, `death.json`, `versions.json` (7 спорных вопросов со статусами), `research.json` (10 работ), `glossary.json` (15 терминов), `faq.json` (10 ответов со ссылками), `music.json` (14), `films.json` (14), `languages.json` (9), `topics.json` (6 тем с фото).
- Тексты сайта: 5 очерков биографии (`content/*.md`) + 3 разбора (`content/publications/`), два выпущены, один запланирован на 27.11.2026.
- Аудиокниги: 33 записи ЛитРеса с обложками и партнёрскими ссылками AdvCake (`erid`) — `scripts/import-audiobooks.py`, обложки в `public/img/audiobooks/`.
- Персоны: фото у 12 из 16 (PD с Викисклада, подписи и лицензии в `people.json`), досье на всех 16 (`data/dossiers.json`), по 4+ факта со ссылками.
- Медиа: портрет 600×800 и 14 фото из Викисклада (8 эпохи, 6 мест), у каждого автор и лицензия в `data/media.json`; скрипт — `scripts/import-media.py`.
- Книги: 94 издания с обложками и партнёрскими ссылками (`scripts/scrape-books.py` + `scripts/import-books.py`, категории и аннотации переписаны под Маяковского). Партнёрских ссылок нет — см. блокеры.

## Проверки

`npm run verify` → 0 ошибок сборки и аудита; красным остаётся только гейт Метрики (`analytics.yandexMetrika` пуст). Одно предупреждение: запас журнала 6 будних дней из 14.

Правки в общих скриптах, сделанные здесь (перенести в `esenin-dashboard`, `bunin-site`, `chekhov-site`):
- `verify.mjs`: маркировка «Реклама. Рекламодатель…» требуется только если на странице книг реально есть ссылки с `erid`; предупреждение о метках — только для магазинов с `tagParam`.
- `build.mjs`: то же условие для предупреждения о метках.
- `import-books.py`: категории и аннотации были есенинские/бунинские.
- `build.mjs` + `site.config.json`: плашки главной (`home.featuredPlaces`, а также `featuredWorks/People/keyEvents`) читаются из конфига; жёсткие id прежнего автора после клонирования молча отфильтровывались.
- `verify.mjs`: новый гейт — `featuredWorks/featuredPeople/featuredPlaces/keyEvents` должны ссылаться на существующие записи (он нашёл мёртвый id `benislavskaya` в конфиге Есенина).
- `import-audiobooks.py`: выдача ЛитРеса теперь в React Flight (`instance` внутри блоба), парсер переписан; поиск стал устойчив к 502.
- `import-people-photos.py`: загрузка через прокси при 429 от upload.wikimedia; метаданные с запасным вариантом лицензии. Перенесено в Есенин, Бунин, Чехов (там же починен декабрь в массиве месяцев и места на главной).

## Блокеры (нужен владелец)

1. Домен `poet-mayakovsky.ru` настроен (23.11.2026): NS Cloudflare, A 185.199.108–111.153, CNAME www → `smhotey.github.io`, сертификат approved, Enforce HTTPS включён. Если сертификат отвалится — снять и заново поставить cname (`-f cname=""`, затем `-f cname=poet-mayakovsky.ru`) — так выпуск сертификата перезапускается.
   Project-URL `https://smhotey.github.io/mayakovsky-site/` по-прежнему ломает корневые пути (`/assets/...`) — это ожидаемо, рабочий адрес — домен.
2. Партнёрские ссылки «Читай-города»: 94 из 94 книг со ссылками `chitai-gorod.ru/r/…?erid=…`, кабинет партнёрки вход выполнен, пароль сохранён в хранилище Hermes (владелец ввёл заново через защищённый запрос). На странице книг стоит маркировка «Реклама. Рекламодатель ООО «ГРАМОТА», ОГРН 1037706012376».
3. Яндекс.Метрика: счётчик 114509180 вписан в `site.config.json` и в `src/book/book.js`; верификатор целей проходит.
4. Google Search Console / Яндекс.Вебмастер: подтверждение домена после покупки; IndexNow-ключ уже в `public/`.

## Полезное

- Сборка: `npm run build` (462 страницы). Проверка: `npm run verify`, строгая — `npm run verify:strict`.
- Глубина контента: 31 страница T1–T4 (норма ≥ 30) — биография 5, места 13, разборы 3, досье людей 9, версии и источники по 1. Досье лежат в `data/dossiers.json`, формат: `facts[{claim,source}]`, `relations[{date,event,source}]`, `sources[{label,url}]`, не меньше четырёх фактов.
- Локальный просмотр: `npm run serve`.
- Тексты: `content/*.md` (биография), `content/publications/*.md` (журнал, дата в будущем = отложенная публикация).
- Правило серии: любая правка и любой найденный баг — сразу во все сайты серии (Есенин, Бунин, Чехов, Маяковский).

## 2026-11-23 — редиректы и проверка домена
- Домен poet-mayakovsky.ru резолвится (185.199.108-111.153), HTTPS включён, сертификат approved до 2027-02-21, www → 301 на основной.
- Найден баг: в  остались скопированные при клонировании правила  в . Теперь домен берётся из  (как в bunin-site). Тот же баг исправлен в chekhov-site.
- 
> author-site@1.0.0 verify
> npm run build && npm run check && node scripts/text-audit.mjs && node scripts/verify.mjs && node scripts/content-coverage.mjs --gate && node scripts/links-orphans.mjs && node scripts/metrika-goals.mjs


> author-site@1.0.0 prebuild
> node scripts/last-updated.mjs

Даты разделов (data/updated.json): structure: 2026-11-23, works: 2026-11-10, people: 2026-11-22, timeline: 2026-11-22, biography: 2026-11-10, publications: 2026-11-10, places: 2026-11-10, legacy: 2026-11-10, books: 2026-11-22, research: 2026-11-10, versions: 2026-11-10, sources: 2026-11-10, faq: 2026-11-10, topics: 2026-11-10

> author-site@1.0.0 build
> node scripts/build.mjs

  запланировано, ещё не выпущено: 1 (2026-11-27 — 2026-11-27)
built pages: 462
works: 389 people: 16 books: 94 research: 10
book: 53 текстов, 0 расхождений
book: блоков размечено 9243
book: кнопка у 53 текстов

> author-site@1.0.0 check
> node scripts/check-links.mjs

html files: 464 internal links: 22226 missing: 0
external links: 71 unique, checked 71, ok 71, errors 0, warnings 0
Проверено текстов: 3 (выпущено 2, запланировано 1)

Ошибок нет.
ПРЕДУПРЕЖДЕНИЯ:
  ! очередь журнала: готовых статей на 5 будних дней вперёд из 14 — пора писать

Проверено: фото персон: 12 из 16; главная: произведений 6, персон 8, мест 3, дат 8; досье: 16 персон; страниц с датой «Обновлено»: 462; аудиокниг проверено: 33; произведений проверено: 389; book: 53 текстов, 9243 абзацев; book: StPageFlip 45565 байт; book: счётчик Метрики совпадает с конфигом; IndexNow: ключ на месте; Вебмастер: файл подтверждения на месте; Google: файл подтверждения на месте; страниц: 462, файлов: 899; размер dist: 31.8 МБ
ПРОВЕРКА ПРОЙДЕНА: ошибок нет, предупреждений 1
Контент-покрытие https://poet-mayakovsky.ru — 2026-11-23

  URL в sitemap:        461
  T1–T4:                38 (54,3% описательных, 8,2% всех)
  works:                391 (84,8% sitemap; стоп-правило ≤ 70,0%)
  описательных всего:   70 (хабы 11, персоны без досье 3, прочее 18)
  тонких (<200 слов):   130, из них works 118
  из них короткие тексты произведений (<400 знаков): 30, прочих тонких works (текст есть, страница короткая): 88

  Норма: T1–T4 ≥ 30 страниц и ≥ 15,0% описательных.
  Итог: PASS
  Структура: works занимают 84,8% — сайт в фазе контент-программы, ссылки и переоптимизация не в приоритете.

  Разделы:
    works           391  из них T1–T4   0
    people           20  из них T1–T4  16
    places           14  из них T1–T4  13
    topics            7  из них T1–T4   0
    biography         6  из них T1–T4   5
    legacy            6  из них T1–T4   0
    life              4  из них T1–T4   0
    publications      3  из них T1–T4   2
    (главная)         1  из них T1–T4   0
    books             1  из них T1–T4   0
    audiobooks        1  из них T1–T4   0
    research          1  из них T1–T4   0
    versions          1  из них T1–T4   1
    sources           1  из них T1–T4   1
    about             1  из них T1–T4   0
    faq               1  из них T1–T4   0
    glossary          1  из них T1–T4   0
    privacy           1  из них T1–T4   0
Граф ссылок https://poet-mayakovsky.ru — 2026-11-23

  HTML в dist: 464, URL в sitemap: 461
  страниц без входящих ссылок: 0
  тупиков без исходящих ссылок: 0
  только из футера/меню (справочно): 1 — privacy.html
  Итог: PASS
Цели Метрики https://poet-mayakovsky.ru — счётчик 114509180

  PASS  book_click       клик по ссылке на книгу
  PASS  audiobook_click  клик по аудиокниге
  PASS  scroll_90        дочитывание до 90%
  PASS  print            печать текста

  Код отправки: PASS (ym(..., 'reachGoal', ...))
  data-ym на главной: PASS

  Итог: PASS: 0 ошибок, 1 предупреждение (очередь журнала: 5 будних дней из 14).
