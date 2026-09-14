import type { Metadata } from 'next';
import { GeistSans } from 'geist/font/sans';
import { GeistMono } from 'geist/font/mono';
import './globals.css';
import { AppShell } from '@/components/Layout/AppShell';
import { ShellProvider } from '@/components/Layout/ShellContext';
import { ThemeProvider, themeInitScript } from '@/components/theme/ThemeProvider';

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
            <AppShell>{children}</AppShell>
          </ShellProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
