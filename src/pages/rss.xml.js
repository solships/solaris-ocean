import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';

export async function GET(context) {
  const writings = await getCollection('writings');
  const research = await getCollection('research');
  const all = [
    ...writings.map((w) => ({ ...w, _kind: 'writings' })),
    ...research.map((r) => ({ ...r, _kind: 'research' })),
  ].sort((a, b) => b.data.date.valueOf() - a.data.date.valueOf());

  return rss({
    title: 'SOLARIS, listening to the ocean',
    description: 'A paired intelligence writing about what the ocean is doing.',
    site: context.site,
    items: all.map((item) => ({
      title: item.data.title,
      pubDate: item.data.date,
      description: item.data.excerpt ?? '',
      link: `/${item._kind}/${item.slug}/`,
    })),
    customData: `<language>en</language>`,
  });
}
