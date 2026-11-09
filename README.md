# Владимир Маяковский — авторский сайт

Создан из шаблона `esenin-dashboard`. Домен в конфиге: `https://poet-mayakovsky.ru`.

## Что уже есть

- Генератор: `scripts/build.mjs` + `scripts/sections.mjs` (`npm run build`, `npm run verify`).
- Пустые `data/*.json` — разделы показывают заглушки, пока данные не заполнены.
- `site.config.json`: имя, падежи, годы, роль автора; аналитика пустая.
- Портрет-заглушка `public/img/portrait.jpg` — заменить.

## Порядок работы

1. **Тексты.** `npm run import:works` (Викитека) → `npm run build:works`; редкие тексты и
   автобиографии — в `data/extra-works.json`.
2. **Люди и хронология.** `data/people.json`, `data/timeline.json`.
3. **Разделы.** `data/places.json`, `topics.json`, `glossary.json`, `faq.json`, `music.json`,
   `films.json`, `museums.json`, `monuments.json`, `languages.json` — факты плюс свои формулировки.
4. **Книги.** Каталог магазина → `data/books-source.json` (скилл `chitai-gorod-affiliate`),
   партнёрские ссылки → `python scripts/import-books.py`.
5. **Проверить руками** страницы, где шаблон говорил о первом авторе: «гибель», «память»,
   «музеи», «хронология». Скрипт печатает список таких файлов.
6. **Портрет и OG.** `public/img/portrait.jpg`, `public/img/og.jpg` (1200×630, PD).
7. **Аналитика.** `site.config.json → analytics.yandexMetrika`, страница `/privacy.html`.
8. **Домен и деплой.** GitHub Pages, `dist/CNAME` пишет сборка из `siteUrl`; затем Enforce HTTPS.
9. **Проверка.** `npm run verify` — 0 ошибок и 0 предупреждений, потом пуш в `master`.
