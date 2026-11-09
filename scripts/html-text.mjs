// Превращает HTML-рендер страницы Викитеки в плоский текст.
// Зачем свой парсер: на Викитеке стихи свёрстаны десятком шаблонов
// ({{poemx}}, {{Лесенка}}, {{v}}, таблицы действующих лиц), и разбирать
// wikitext под каждый шаблон — тупик. Рендер уже даёт готовые строки.

const VOID = new Set(['br', 'hr', 'img', 'meta', 'link', 'input', 'wbr', 'col', 'area', 'source']);
const BLOCK = new Set(['p', 'div', 'li', 'ul', 'ol', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'blockquote', 'dd', 'dt', 'table', 'section', 'figure', 'figcaption', 'pre']);
// Служебные обёртки Викитеки, которые в текст не идут.
const DROP_CLASS = /(ws-noexport|tocline|references-small|navbox|metadata|mw-editsection|sistersitebox|header&amp;#95;|noprint|ws-summary|linenum)/i;
const DROP_ID = /^(headertemplate|sub_?nav|toc)$/i;

const ENTITIES = {
  nbsp: ' ', amp: '&', lt: '<', gt: '>', quot: '"', apos: "'",
  mdash: '—', ndash: '–', laquo: '«', raquo: '»', hellip: '…', shy: '',
  thinsp: ' ', ensp: ' ', emsp: ' ', copy: '©', deg: '°', times: '×',
};

function decode(s) {
  return s
    .replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(Number(d)))
    .replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCodePoint(parseInt(h, 16)))
    .replace(/&([a-z]+);/gi, (m, name) => (name.toLowerCase() in ENTITIES ? ENTITIES[name.toLowerCase()] : m));
}

/** Отрезает служебную шапку Викитеки: оставляем только тело произведения. */
export function extractContent(html) {
  let h = html;
  const m = h.match(/<div class="(?:poetry|drama|text|prose|poem)[^"]*"/i);
  if (m && m.index !== undefined) h = h.slice(m.index);
  h = h.replace(/<div[^>]*class="[^"]*references-small[^"]*"[\s\S]*$/i, '');
  h = h.replace(/<ol[^>]*class="[^"]*references[^"]*"[\s\S]*$/i, '');
  h = h.replace(/<!--[\s\S]*?-->/g, '');
  h = h.replace(/<style[\s\S]*?<\/style>/gi, '');
  h = h.replace(/<script[\s\S]*?<\/script>/gi, '');
  return h;
}

export function htmlToText(html) {
  const stack = [];
  let dropDepth = 0;
  let text = '';
  let cell = null;
  let row = null;

  const push = (s) => {
    if (dropDepth) return;
    if (cell !== null) cell += s;
    else text += s;
  };

  const tagRe = /<\/?([a-zA-Z][a-zA-Z0-9]*)\b([^>]*)>/g;
  let last = 0;
  let m;
  while ((m = tagRe.exec(html))) {
    push(html.slice(last, m.index));
    last = tagRe.lastIndex;
    const closing = m[0][1] === '/';
    const tag = m[1].toLowerCase();
    const attrs = m[2] || '';
    const selfClosing = /\/>$/.test(m[0]) || VOID.has(tag);

    if (closing) {
      // снимаем верхний несовпавший? Для наших страниц разметка валидная.
      const idx = stack.map((x) => x.tag).lastIndexOf(tag);
      if (idx < 0) continue;
      while (stack.length > idx) {
        const top = stack.pop();
        if (top.drop) dropDepth--;
      }
      if (tag === 'sup' && /reference/.test(attrs)) { /* уже снят */ }
      if (tag === 'td' || tag === 'th') {
        // Ячейки разбираем уже без HTML-сущностей: пустая ячейка — это &#160;.
        const value = cell === null ? '' : decode(cell).replace(/\u00a0/g, ' ').trim();
        if (row && value) row.push(value);
        cell = null;
      } else if (tag === 'tr') {
        if (row) {
          const cells = row.filter(Boolean);
          if (cells.length) push(cells.join(' — ') + '\u0001');
        }
        row = null;
      } else if (BLOCK.has(tag)) {
        push('\u0002');
      }
      continue;
    }

    if (selfClosing) {
      if (tag === 'br') push('\u0001');
      continue;
    }

    const classAttr = (attrs.match(/class="([^"]*)"/i) || [])[1] || '';
    const idAttr = (attrs.match(/id="([^"]*)"/i) || [])[1] || '';
    const styleAttr = (attrs.match(/style="([^"]*)"/i) || [])[1] || '';
    const drop = /visibility:\s*hidden|display:\s*none/i.test(styleAttr)
      || DROP_CLASS.test(classAttr)
      || DROP_ID.test(decode(idAttr))
      || (tag === 'sup' && /reference/i.test(classAttr))
      || (tag === 'table' && /headertemplate/i.test(classAttr));
    stack.push({ tag, drop });
    if (drop) dropDepth++;

    if (tag === 'tr') row = [];
    if (tag === 'td' || tag === 'th') cell = '';
    if (tag === 'p' || tag === 'div' || tag === 'li' || /^h[1-6]$/.test(tag)) push('\u0002');
  }
  push(html.slice(last));

  const flat = decode(text).replace(/\r/g, '').replace(/[ \t\u00a0]+/g, ' ');
  return flat
    .split('\u0002')
    .map((chunk) => chunk
      .split('\u0001')
      .map((line) => line.trim())
      .filter((line) => line !== '')
      .join('\n'))
    .filter((chunk) => chunk.trim() !== '')
    .join('\n\n')
    .trim();
}
