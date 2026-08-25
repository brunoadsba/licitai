export default function Loading() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="space-y-2">
        <div className="h-8 w-48 rounded-lg bg-white/[0.06]" />
        <div className="h-4 w-72 rounded bg-white/[0.04]" />
      </div>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-28 rounded-xl border border-line-subtle bg-elevated p-5">
            <div className="h-3 w-16 rounded bg-white/[0.06]" />
            <div className="mt-4 h-8 w-12 rounded bg-white/[0.08]" />
          </div>
        ))}
      </div>
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-24 rounded-xl border border-line-subtle bg-elevated" />
        ))}
      </div>
    </div>
  );
}
