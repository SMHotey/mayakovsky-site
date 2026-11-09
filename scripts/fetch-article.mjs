// Сохраняет полный текст статьи Википедии в файл для сверки фактов.
// Запуск: node scripts/fetch-article.mjs "Статья" out.txt
import { writeFile } from 'node:fs/promises';

const [title, out] = process.argv.slice(2);
const url = 'https://ru.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1'
  + '&format=json&formatversion=2&redirects=1&titles=' + encodeURIComponent(title);
const res = await fetch(url, { headers: { 'User-Agent': 'MayakovskySite/1.0 (author site)' } });
const data = await res.json();
const page = data.query.pages[0];
const text = page.extract || '';
await writeFile(out, text, 'utf8');
console.log(out, text.length, 'символов');
