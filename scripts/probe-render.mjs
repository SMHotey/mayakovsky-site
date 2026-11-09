// Проверка скорости и отдачи action=render: сколько страниц в минуту.
const titles = [
  'Ночь (Маяковский)', 'Утро (Маяковский)', 'Порт (Маяковский)', 'Нате! (Маяковский)',
  'Послушайте! (Маяковский)', 'Лиличка! (Маяковский)', 'Вам! (Маяковский)',
  'Облако в штанах (Маяковский)', 'Флейта-позвоночник (Маяковский)', 'Клоп (Маяковский)',
];
const t0 = Date.now();
for (const t of titles) {
  const url = 'https://ru.wikisource.org/w/index.php?action=render&title=' + encodeURIComponent(t.replace(/ /g, '_'));
  const r = await fetch(url, { headers: { 'User-Agent': 'MayakovskySite/1.0' } });
  const b = await r.text();
  console.log(r.status, b.length, t);
  await new Promise((res) => setTimeout(res, 400));
}
console.log('секунд на', titles.length, Math.round((Date.now() - t0) / 1000));
