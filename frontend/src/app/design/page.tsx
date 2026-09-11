'use client';

/**
 * Showcase de primitivos — rota dev-only (gate da Fase 1).
 * QA visual: 375 / 768 / 1280px, estados hover/focus/disabled/loading.
 */

import { useState } from 'react';
import { FileText, Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import { Spinner } from '@/components/ui/Spinner';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/Dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/DropdownMenu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="text-[11px] font-medium uppercase tracking-widest text-content-subtle">{title}</h2>
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-line-subtle bg-panel/50 p-5">
        {children}
      </div>
    </section>
  );
}

export default function DesignShowcasePage() {
  const [loading, setLoading] = useState(false);
  const [selectValue, setSelectValue] = useState('');

  function withLoading(fn: () => void) {
    setLoading(true);
    setTimeout(() => {
      fn();
      setLoading(false);
    }, 1200);
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <header>
        <p className="text-[11px] font-medium uppercase tracking-widest text-content-subtle">Dev only</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-content-primary">
          Showcase de Primitivos
        </h1>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-content-muted">
          Contrato visual em <code className="rounded bg-white/[0.06] px-1.5 py-0.5 font-mono text-xs">frontend/DESIGN.md</code>.
          Verifique hover, foco por teclado (Tab), active, disabled e loading.
        </p>
      </header>

      <Section title="Button — variantes × tamanhos × estados">
        <div className="flex w-full flex-col gap-4">
          <div className="flex flex-wrap items-center gap-3">
            <Button>Primary</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="danger">Danger</Button>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button size="sm" variant="secondary"><Plus className="h-3.5 w-3.5" aria-hidden />Small</Button>
            <Button size="md" variant="secondary">Medium</Button>
            <Button size="lg" variant="secondary">Large</Button>
            <Button size="lg" variant="secondary"><Plus className="h-4 w-4" aria-hidden />Com ícone</Button>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button disabled>Disabled</Button>
            <Button
              loading={loading}
              onClick={() => withLoading(() => {})}
            >
              Loading…
            </Button>
          </div>
        </div>
      </Section>

      <Section title="Input / Textarea / Select">
        <div className="grid w-full gap-4 sm:grid-cols-2">
          <Input placeholder="Placeholder padrão" />
          <Input placeholder="Estado de erro" error aria-label="Exemplo com erro" />
          <Textarea rows={2} placeholder="Área de texto…" className="sm:col-span-2" />
          <Select value={selectValue} onValueChange={setSelectValue}>
            <SelectTrigger aria-label="Seleção de exemplo" className="sm:col-span-2">
              <SelectValue placeholder="Selecione uma opção" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="opcao-a">Opção A</SelectItem>
              <SelectItem value="opcao-b">Opção B</SelectItem>
              <SelectItem value="opcao-c">Opção C</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </Section>

      <Section title="Badge — tons semânticos">
        <Badge tone="neutral">Neutro</Badge>
        <Badge tone="info">Info</Badge>
        <Badge tone="low">Baixo</Badge>
        <Badge tone="medium">Médio</Badge>
        <Badge tone="high">Alto</Badge>
        <Badge tone="critical">Crítico</Badge>
        <Badge tone="juridica">Jurídica</Badge>
        <Badge tone="tecnica">Técnica</Badge>
        <Badge tone="redacao">Redação</Badge>
        <Badge tone="estrutural">Estrutura do TR</Badge>
        <Badge tone="accent">Accent</Badge>
      </Section>

      <Section title="Dialog / DropdownMenu / Tooltip">
        <div className="flex flex-wrap items-center gap-3">
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="secondary">Abrir dialog</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Remover documento?</DialogTitle>
                <DialogDescription>
                  Esta ação não pode ser desfeita. O documento e suas análises serão removidos permanentemente.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <DialogClose asChild>
                  <Button variant="secondary">Cancelar</Button>
                </DialogClose>
                <DialogClose asChild>
                  <Button variant="danger">Remover</Button>
                </DialogClose>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost">Menu de contexto</Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuLabel>Ações</DropdownMenuLabel>
              <DropdownMenuItem>Duplicar molde</DropdownMenuItem>
              <DropdownMenuItem>Abrir relatório</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem destructive>Excluir</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </Section>

      <Section title="Tabs">
        <Tabs defaultValue="resumo" className="w-full">
          <TabsList>
            <TabsTrigger value="resumo">Resumo</TabsTrigger>
            <TabsTrigger value="itens">Itens</TabsTrigger>
            <TabsTrigger value="correcoes">Correções</TabsTrigger>
          </TabsList>
          <TabsContent value="resumo" className="text-sm text-content-muted">Conteúdo do resumo.</TabsContent>
          <TabsContent value="itens" className="text-sm text-content-muted">Lista de itens.</TabsContent>
          <TabsContent value="correcoes" className="text-sm text-content-muted">Correções aplicadas.</TabsContent>
        </Tabs>
      </Section>

      <Section title="Card + Skeleton + Spinner + EmptyState">
        <div className="grid w-full gap-4 sm:grid-cols-2">
          <Card interactive>
            <CardHeader>
              <CardTitle>Card interativo</CardTitle>
              <CardDescription>Passe o mouse — luminância sobe um passo.</CardDescription>
            </CardHeader>
            <CardContent className="pt-3 text-sm text-content-secondary">
              TR-2026-042 · <span className="tnum">128 itens</span>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="space-y-3 pt-5">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
              <div className="flex items-center gap-2 pt-1 text-xs text-content-muted">
                <Spinner size="sm" label="Carregando dados" /> carregando…
              </div>
            </CardContent>
          </Card>
          <EmptyState
            icon={FileText}
            title="Nenhum documento"
            description="Envie seu primeiro Termo de Referência para começar."
            action={<Button size="sm"><Plus className="h-4 w-4" aria-hidden />Enviar documento</Button>}
            className="border border-dashed border-line-strong sm:col-span-2"
          />
        </div>
      </Section>

      <Section title="Ícones de referência (Lucide)">
        <Trash2 className="h-4 w-4 text-red-400" aria-hidden />
        <FileText className="h-5 w-5 text-content-muted" aria-hidden />
        <Spinner size="sm" />
      </Section>
    </div>
  );
}
