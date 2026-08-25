export default function Loading() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-8 w-48 rounded bg-white/[0.06]" />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 rounded-xl border border-line-subtle bg-elevated" />
          ))}
        </div>
        <div className="lg:col-span-2 h-96 rounded-xl border border-line-subtle bg-elevated" />
      </div>
    </div>
  );
}
