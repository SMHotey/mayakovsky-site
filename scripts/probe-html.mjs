import { api } from './wiki.mjs';
import { htmlToText, extractContent } from './html-text.mjs';
for (const t of process.argv.slice(2)) {
  const d = await api({ action: 'parse', page: t, prop: 'text', redirects: '1' });
  const txt = htmlToText(extractContent(d.parse.text));
  console.log('=====', t, txt.length);
  console.log(txt.slice(0, 700));
  console.log('   ...хвост:', JSON.stringify(txt.slice(-200)));
}
