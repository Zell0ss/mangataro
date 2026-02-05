import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';
import alpinejs from '@astrojs/alpinejs';
import node from '@astrojs/node';

export default defineConfig({
  integrations: [tailwind(), alpinejs()],
  output: 'server',
  adapter: node({
    mode: 'standalone'
  }),
  server: {
    port: 4343,
    allowedHosts: ['seb01'],
  },
});
