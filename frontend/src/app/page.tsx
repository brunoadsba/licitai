import DashboardClient from './DashboardClient';

export const dynamic = 'force-dynamic';

async function getInitialDocuments() {
  const base = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
  try {
    const res = await fetch(`${base}/api/v1/documents/`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return { documents: data.documents ?? [], error: null as string | null };
  } catch {
    return { documents: [], error: 'Erro ao carregar documentos. Verifique se o backend está rodando.' };
  }
}

export default async function DashboardPage() {
  const { documents, error } = await getInitialDocuments();
  return <DashboardClient initialDocuments={documents} initialError={error} />;
}
