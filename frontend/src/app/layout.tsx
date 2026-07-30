import type { Metadata } from 'next';
import './globals.css';
import Sidebar from '@/components/Layout/Sidebar';
import Header from '@/components/Layout/Header';

export const metadata: Metadata = {
  title: 'Análise de Termos de Referência | SEI',
  description:
    'Sistema especialista para análise e revisão de Termos de Referência de licitações públicas usando Inteligência Artificial.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body className="flex min-h-screen">
        {/* Sidebar fixa */}
        <Sidebar />

        {/* Área principal */}
        <div className="flex-1 flex flex-col ml-64">
          <Header />
          <main className="flex-1 p-6 lg:p-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
