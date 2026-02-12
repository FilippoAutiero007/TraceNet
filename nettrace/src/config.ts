import { z } from 'zod';

const EnvSchema = z.object({
  VITE_API_URL: z.string().url().optional(),
});

const parsedEnv = EnvSchema.safeParse(import.meta.env);

if (!parsedEnv.success) {
  console.warn('Invalid env configuration, using defaults', parsedEnv.error.flatten().fieldErrors);
}

const defaultApiUrl = import.meta.env.DEV ? 'http://localhost:8000' : 'https://tracenet-api.onrender.com';

export const API_BASE_URL = parsedEnv.success && parsedEnv.data.VITE_API_URL
  ? parsedEnv.data.VITE_API_URL
  : defaultApiUrl;
