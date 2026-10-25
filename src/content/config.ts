import { defineCollection, z } from 'astro:content';

const bulletins = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    date: z.date(),
    excerpt: z.string().optional(),
    tags: z.array(z.string()).optional(),
  }),
});

const writings = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    date: z.date(),
    excerpt: z.string().optional(),
    kind: z.enum(['poem', 'meditation', 'essay', 'fragment']).default('essay'),
    tags: z.array(z.string()).optional(),
  }),
});

const research = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    date: z.date(),
    excerpt: z.string().optional(),
    subject: z.string().optional(),
    sources: z.array(z.string()).optional(),
    tags: z.array(z.string()).optional(),
  }),
});

const gallery = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    date: z.date(),
    image: z.string(),
    image_alt: z.string(),
    medium: z.string(),
    excerpt: z.string().optional(),
    tags: z.array(z.string()).optional(),
  }),
});

export const collections = { bulletins, writings, research, gallery };
