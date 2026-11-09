import { writeFile, readFile, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { wikitext, api } from './wiki.mjs';
import { htmlToText, extractContent } from './html-text.mjs';

// Викитека: страница автора + два списочных раздела (стихи по годам, публицистика).
const AUTHOR = 'Автор:Владимир Владимирович Маяковский';
const LIST_POEMS = 'Стихотворения Маяковского';
const LIST_PUB = 'Публицистика Маяковского';
const CACHE = 'data/raw-cache.json';
const HTML_CACHE = 'data/raw-html.json';

// Разделы страницы автора: заголовок → жанр словаря сайта.
const SECTION_GENRES = {
  'Поэмы': 'Поэма',
  'Пьесы, Трагедии': 'Пьеса',
  'Очерки': 'Очерк',
  'Автобиографические произведения': 'Автобиография',
};

const SLEEP = (ms) => new Promise((r) => setTimeout(r, ms));

// Текст на Викитеке часто лежит внутри {{Poemx|…}} или под шапкой {{Отексте}}.
// Просто вырезать шаблоны нельзя: вместе с ними исчезает и сам текст поэмы.
// Верхнеуровневые параметры шаблона: {{poemx|заголовок|текст|<год>}} → 3 строки.
function templateParams(raw, name) {
  const m = raw.match(new RegExp('\\{\\{\\s*' + name + '\\s*\\|', 'i'));
  if (!m) return null;
  const start = m.index;
  let depth = 0;
  let i = start + 2 + name.length;
  const params = [];
  let cur = '';
  while (i < raw.length) {
    if (raw.startsWith('{{', i)) { depth++; cur += '{{'; i += 2; continue; }
    if (raw.startsWith('}}', i)) {
      if (depth === 0) { params.push(cur); return params; }
      depth--; cur += '}}'; i += 2; continue;
    }
    if (depth === 0 && raw[i] === '|') { params.push(cur); cur = ''; i++; continue; }
    cur += raw[i];
    i++;
  }
  return null;
}

function extractBody(raw) {
  for (const name of ['Poemx', 'poemx', 'Poem', 'poem', 'Poemx1']) {
    const params = templateParams(raw, name);
    if (!params) continue;
    // Самый длинный параметр — сам текст; остальные это заголовок, год и служебные поля.
    const body = params.map((x) => x.trim()).sort((a, b) => b.length - a.length)[0] || '';
    if (body) return body;
  }
  return raw.replace(/\{\{\s*Отексте[\s\S]*?\n\}\}/i, '');
}

function cleanWiki(raw) {
  let t = raw;
  t = t.replace(/<!--[\s\S]*?-->/g, '');
  t = t.replace(/<ref[^>]*\/>/g, '');
  t = t.replace(/<ref[^>]*>[\s\S]*?<\/ref>/g, '');
  let prev;
  do { prev = t; t = t.replace(/\{\{[^{}]*\}\}/g, ''); } while (t !== prev);
  t = t.replace(/\[\[(?:Категория|Файл|Image|Изображение):[^\]]*\]\]/gi, '');
  t = t.replace(/\[\[([^\]|]+)\|([^\]]+)\]\]/g, '$2');
  t = t.replace(/\[\[([^\]]+)\]\]/g, '$1');
  t = t.replace(/\[https?:\/\/[^\s\]]+\s+([^\]]+)\]/g, '$1');
  t = t.replace(/\[https?:\/\/[^\]]+\]/g, '');
  t = t.replace(/'''?/g, '');
  t = t.replace(/<\/?poem[^>]*>/gi, '');
  t = t.replace(/<br\s*\/?>/gi, '\n');
  t = t.replace(/<\/(?:center|div|span|small|big|p|i|b|u|sup|sub|blockquote)>/gi, '\n');
  t = t.replace(/<(?:center|div|span|small|big|p|i|b|u|sup|sub|blockquote)[^>]*>/gi, '');
  t = t.replace(/^__[A-Z]+__$/gm, '');
  t = t.replace(/&nbsp;/g, ' ').replace(/&mdash;/g, '—').replace(/&ndash;/g, '–')
       .replace(/&quot;/g, '"').replace(/&laquo;/g, '«').replace(/&raquo;/g, '»')
       .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
  t = t.split('\n').map((l) => l.replace(/[ \t]+$/g, '')).join('\n');
  t = t.replace(/\n{3,}/g, '\n\n');
  return t.trim();
}

function templateField(raw, name) {
  const m = raw.match(new RegExp(`\\|\\s*${name}\\s*=\\s*([^\\n|]*)`, 'i'));
  return m ? m[1].trim() : '';
}

function slugify(s) {
  return s.toLowerCase().replace(/ё/g, 'е')
    .replace(/[^a-zа-я0-9]+/gi, '-')
    .replace(/^-|-$/g, '').slice(0, 90);
}

function bullets(line) {
  const items = [];
  let m;
  const re2 = /\{\{2О\|([^|}]+)\|([^|}]+)\}\}/g;
  while ((m = re2.exec(line))) items.push({ target: m[1].trim(), label: m[2].trim() });
  const re = /\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]*))?\]\]/g;
  while ((m = re.exec(line))) {
    const target = m[1].trim();
    if (/^(Категория|Файл|Image|Изображение):/i.test(target)) continue;
    if (target.startsWith(':')) continue;
    items.push({ target, label: (m[2] || target).replace(/'''?/g, '').trim() });
  }
  return items;
}

// Год из хвоста строки: «(1913)», «(1914—1915)», «(1929—1930)».
function yearFrom(line) {
  const m = line.match(/\((\d{4})(?:\s*[—–-]\s*(\d{4}))?\)\s*(?:''\s*)?$/);
  if (!m) return { year: null, yearNote: null };
  const a = Number(m[1]);
  const b = m[2] ? Number(m[2]) : null;
  return b ? { year: b, yearNote: `${a}—${b}` } : { year: a, yearNote: null };
}

async function fetchPages(titles, cache) {
  const missing = titles.filter((t) => !cache[t]);
  console.log(`к загрузке: ${missing.length} из ${titles.length}`);
  for (let i = 0; i < missing.length; i += 5) {
    const chunk = missing.slice(i, i + 5);
    let ok = false;
    for (let attempt = 0; attempt < 3 && !ok; attempt++) {
      try {
        const data = await api({
          action: 'query', prop: 'revisions', rvslots: 'main', rvprop: 'content',
          titles: chunk.join('|'), redirects: '1',
        });
        const redirects = data.query?.redirects || [];
        const norm = data.query?.normalized || [];
        const byTitle = new Map(data.query?.pages?.map((p) => [p.title, p]) || []);
        for (const t of chunk) {
          let key = t;
          const n = norm.find((x) => x.from === t); if (n) key = n.to;
          const r = redirects.find((x) => x.from === key); if (r) key = r.to;
          const p = byTitle.get(key);
          const content = p?.revisions?.[0]?.slots?.main?.content;
          if (content) cache[t] = content;
        }
        ok = true;
      } catch (e) {
        console.warn('повтор пачки', i, e.message);
        await SLEEP(3000 * (attempt + 1));
      }
    }
    await SLEEP(1600);
    if ((i / 5) % 10 === 0) console.log(`${i + chunk.length}/${missing.length}`);
  }
}

// Рендер страницы: action=render отдаёт только тело статьи (без шапки Викитеки),
// и, в отличие от action=parse, не упирается в жёсткий лимит запросов.
async function fetchHtml(titles, html, cacheFile) {
  const missing = titles.filter((t) => !html[t]);
  console.log(`html к загрузке: ${missing.length}`);
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  let done = 0;
  for (const title of missing) {
    const url = 'https://ru.wikisource.org/w/index.php?action=render&title='
      + encodeURIComponent(title.replace(/ /g, '_'));
    for (let attempt = 0; attempt < 6; attempt++) {
      try {
        const res = await fetch(url, { headers: { 'User-Agent': 'MayakovskySite/1.0 (author site; local)' } });
        if (res.status === 404) { console.log('404', title); break; }
        if (!res.ok) { await sleep(1500 * (attempt + 1)); continue; }
        const body = await res.text();
        if (body.trim()) { html[title] = body; }
        break;
      } catch (e) {
        await sleep(1500 * (attempt + 1));
      }
    }
    done++;
    if (done % 25 === 0) {
      console.log(`html ${done}/${missing.length}`);
      await writeFile(cacheFile, JSON.stringify(html), 'utf8');
    }
    await sleep(350);
  }
}

// Редакционные приложения Викитеки (варианты, примечания, наброски) в корпус
// не идут: читателю нужен текст произведения, а не аппарат издания.
const APPENDIX = /^(?:ВАРИАНТЫ|ПРИМЕЧАНИЯ|КОММЕНТАРИИ|ПРИЛОЖЕНИЕ|БИБЛИОГРАФИЯ|СПИСОК ИЛЛЮСТРАЦИЙ|ИСТОЧНИКИ)[\s,:.—-]/im;

function tidy(text) {
  let t = text;
  // Строки выравниваем до поиска приложений: в рендерере заголовки с отступом.
  t = t.split('\n').map((l) => l.replace(/^[ \t]+/, '').replace(/[ \t]{2,}/g, ' ').replace(/[ \t]+$/, '')).join('\n');
  const hit = t.match(APPENDIX);
  if (hit && hit.index > 500) t = t.slice(0, hit.index);
  // Викитека иногда не рендерит шаблон и печатает его как текст: {{poem, {{№|12
  t = t.replace(/\{\{[^{}\n]*/g, '').replace(/\}\}/g, '');
  t = t.replace(/<[^>]+>/g, '');
  t = t.replace(/__[A-Z]+__/g, '');
  t = t.replace(/\|\s*$/gm, '');
  t = t.replace(/^\s*-{3,}\s*$/gm, '');
  // Магические слова MediaWiki (__NOTOC__ и подобные) — служебный мусор.
  t = t.replace(/__[A-Z]+__/g, '');
  t = t.replace(/\n{3,}/g, '\n\n').trim();
  return t;
}

async function main() {
  await mkdir('data', { recursive: true });
  let cache = {};
  if (existsSync(CACHE)) {
    cache = JSON.parse(await readFile(CACHE, 'utf8'));
    console.log('в кэше:', Object.keys(cache).length);
  }

  const entries = new Map();
  const add = (target, meta) => { if (!entries.has(target)) entries.set(target, meta); };

  // 1. Страница автора: поэмы, пьесы, очерки, автобиография.
  const author = await wikitext(AUTHOR);
  let h2 = '';
  for (const line of author.split('\n')) {
    // разделы страницы автора бывают и второго, и третьего уровня
    const m2 = line.match(/^(={2,4})\s*([^=]+?)\s*\1\s*$/);
    if (m2) { h2 = m2[2]; continue; }
    const genre = SECTION_GENRES[h2];
    if (!genre || !line.startsWith('*')) continue;
    const { year, yearNote } = yearFrom(line);
    for (const { target, label } of bullets(line)) {
      if (!/\(Маяковский\)$/.test(target)) continue;
      add(target, { title: label, genre, year, yearNote });
    }
  }
  console.log('поэмы/пьесы/очерки/автобиография:', entries.size);

  // 2. Стихотворения: список по годам между маркерами section.
  const poems = await wikitext(LIST_POEMS);
  let year = null;
  let inList = false;
  for (const line of poems.split('\n')) {
    if (/<section begin="список"/.test(line)) inList = true;
    if (/<section end="список"/.test(line)) inList = false;
    if (!inList) continue;
    const y = line.match(/^={3,5}\s*(\d{4})\s*={3,5}$/);
    if (y) { year = Number(y[1]); continue; }
    if (!line.startsWith('*')) continue;
    for (const { target, label } of bullets(line)) {
      if (!/\(Маяковский\)$/.test(target)) continue;
      add(target, { title: label, genre: 'Стихотворение', year, yearNote: null });
    }
  }
  console.log('после списка стихотворений:', entries.size);

  // 3. Публицистика: статьи, год в курсиве.
  const pub = await wikitext(LIST_PUB);
  for (const line of pub.split('\n')) {
    if (!line.startsWith('*')) continue;
    const y = line.match(/''\((\d{4})\)''/);
    const { yearNote } = yearFrom(line);
    for (const { target, label } of bullets(line)) {
      if (!/\(Маяковский\)$/.test(target)) continue;
      add(target, { title: label, genre: 'Статья', year: y ? Number(y[1]) : null, yearNote });
    }
  }
  console.log('итого записей:', entries.size);

  const titles = [...entries.keys()];
  if (!process.env.SKIP_WIKI) await fetchPages(titles, cache);
  await writeFile(CACHE, JSON.stringify(cache), 'utf8');
  console.log('в кэше:', Object.keys(cache).length);

  let html = {};
  if (existsSync(HTML_CACHE)) html = JSON.parse(await readFile(HTML_CACHE, 'utf8'));
  await fetchHtml(titles, html, HTML_CACHE);
  await writeFile(HTML_CACHE, JSON.stringify(html), 'utf8');

  const works = [];
  const missed = [];
  for (const [title, meta] of entries) {
    const raw = cache[title];
    if (!raw) { missed.push(title); continue; }
    const page = html[title];
    const text = page ? tidy(htmlToText(extractContent(page))) : '';
    if (text.length < 40) { missed.push(title); continue; }
    const created = templateField(raw, 'ДАТАСОЗДАНИЯ').match(/(1[89]\d\d|19\d\d)/);
    works.push({
      title: meta.title,
      slug: slugify(meta.title),
      genre: meta.genre,
      year: meta.year || (created ? Number(created[1]) : null),
      yearNote: meta.yearNote,
      published: templateField(raw, 'ДАТАПУБЛИКАЦИИ') || null,
      text,
      chars: text.length,
      sourceUrl: `https://ru.wikisource.org/wiki/${encodeURIComponent(title.replace(/ /g, '_'))}`,
      source: templateField(raw, 'ИСТОЧНИК') || null,
    });
  }

  const seen = new Set();
  const unique = works.filter((w) => { if (seen.has(w.slug)) return false; seen.add(w.slug); return true; });
  unique.sort((a, b) => (a.year || 9999) - (b.year || 9999) || a.title.localeCompare(b.title, 'ru'));

  await writeFile('data/works.json', JSON.stringify(unique, null, 1), 'utf8');
  const byGenre = {};
  unique.forEach((w) => (byGenre[w.genre] = (byGenre[w.genre] || 0) + 1));
  console.log('записано:', unique.length, byGenre);
  if (missed.length) console.log('БЕЗ ТЕКСТА:', missed.length, missed.slice(0, 15));
}

main().catch((e) => { console.error(e); process.exit(1); });
