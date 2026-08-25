import type { Metadata } from 'next';
import { GeistSans } from 'geist/font/sans';
import { GeistMono } from 'geist/font/mono';
import './globals.css';
import Sidebar from '@/components/Layout/Sidebar';
import Header from '@/components/Layout/Header';
import { ShellProvider } from '@/components/Layout/ShellContext';
import { Toaster } from '@/components/ui/Toaster';

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
    <html lang="pt-BR" className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <body className="flex min-h-dvh">
        <ShellProvider>
          <a href="#conteudo-principal" className="skip-link">
            Pular para o conteúdo
          </a>

          {/* Sidebar fixa (desktop) / drawer (mobile — ver Sidebar.tsx) */}
          <Sidebar />

          {/* Área principal */}
          <div className="flex flex-1 flex-col lg:pl-64">
            <Header />
            <main id="conteudo-principal" className="mx-auto w-full max-w-[1440px] flex-1 p-4 sm:p-6 lg:p-8">
              {children}
            </main>
          </div>

          <Toaster />
        </ShellProvider>
      </body>
    </html>
  );
}
