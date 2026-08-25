export default function Loading() {
  return (
    <div className="mx-auto max-w-4xl space-y-6 animate-pulse">
      <div className="h-8 w-64 rounded bg-white/[0.06]" />
      <div className="grid grid-cols-3 gap-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 rounded-xl border border-line-subtle bg-elevated" />
        ))}
      </div>
      <div className="h-80 rounded-xl border border-line-subtle bg-elevated" />
    </div>
  );
}
