export default function Loading() {
  return (
    <div className="mx-auto max-w-2xl space-y-6 animate-pulse">
      <div className="space-y-2">
        <div className="h-7 w-40 rounded bg-white/[0.06]" />
        <div className="h-4 w-80 rounded bg-white/[0.04]" />
      </div>
      <div className="h-64 rounded-xl border border-line-subtle bg-elevated" />
      <div className="h-32 rounded-xl border border-line-subtle bg-elevated" />
    </div>
  );
}
