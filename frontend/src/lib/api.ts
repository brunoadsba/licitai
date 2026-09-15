/**
 * Barrel do cliente API — re-exporta os módulos por domínio.
 * Importadores existentes (`from '@/lib/api'`) continuam funcionando.
 */
export * from './api/client';
export * from './api/documents';
export * from './api/analysis';
export * from './api/comparison';
export * from './api/generator';
export * from './api/chat';
