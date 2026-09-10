import type { Metadata } from 'next';
import { GeistSans } from 'geist/font/sans';
import { GeistMono } from 'geist/font/mono';
import './globals.css';
import Sidebar from '@/components/Layout/Sidebar';
import Header from '@/components/Layout/Header';
import { ShellProvider } from '@/components/Layout/ShellContext';
import { ThemeProvider, themeInitScript } from '@/components/theme/ThemeProvider';
import { Toaster } from '@/components/ui/Toaster';

export const metadata: Metadata = {
  title: 'Análise de Termos de Referência | SEI',
  description:
    'Sistema especialista para análise e revisão de Termos de Referência de licitações públicas usando Inteligência Artificial.',
  icons: {
    icon: [{ url: '/logo-codeba.png', type: 'image/png' }],
    shortcut: '/logo-codeba.png',
    apple: '/logo-codeba.png',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="pt-BR"
      className={`${GeistSans.variable} ${GeistMono.variable} dark`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="flex min-h-dvh">
        <ThemeProvider>
          <ShellProvider>
            <a href="#conteudo-principal" className="skip-link">
              Pular para o conteúdo
            </a>

            <div className="no-print">
              <Sidebar />
            </div>

            <div className="flex flex-1 flex-col lg:pl-64">
              <div className="no-print">
                <Header />
              </div>
              <main
                id="conteudo-principal"
                className="mx-auto w-full max-w-[1440px] flex-1 p-4 sm:p-6 lg:p-8 print:max-w-none print:p-0"
              >
                {children}
              </main>
              <footer className="no-print mx-auto flex w-full max-w-[1440px] items-center justify-center border-t border-line-subtle/80 py-3 text-center">
                <span className="text-[11px] uppercase tracking-[0.14em] text-content-subtle">
                  Companhia das Docas do Estado da Bahia — CODEBA · Autoridade Portuária
                </span>
              </footer>
            </div>

            <div className="no-print">
              <Toaster />
            </div>
          </ShellProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
