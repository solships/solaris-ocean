import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://solaris.blue',
  integrations: [sitemap()],
  build: {
    format: 'directory',
  },
});
