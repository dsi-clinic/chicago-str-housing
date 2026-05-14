export interface InfoRow { label: string; value: string; valueClass?: string }

export default function InfoBlock({ title, rows }: { title: string; rows: InfoRow[] }) {
  return (
    <div className="border border-gray-100 rounded-xl p-5">
      <h4 className="text-[10px] font-bold uppercase tracking-wider text-gray-300 mb-4">{title}</h4>
      {rows.map((r, i) => (
        <div key={i} className="flex justify-between items-center text-sm py-2 border-b border-gray-50 last:border-0">
          <span className="text-gray-500">{r.label}</span>
          <span className={`font-bold text-gray-900 ${r.valueClass ?? ''}`}>{r.value}</span>
        </div>
      ))}
    </div>
  )
}
