type Accent = 'maroon' | 'teal' | 'blue' | 'amber' | 'slate'

const TOP: Record<Accent, string> = {
  maroon: 'border-t-maroon',
  teal:   'border-t-teal-600',
  blue:   'border-t-blue-600',
  amber:  'border-t-amber-600',
  slate:  'border-t-slate-500',
}
const VAL: Record<Accent, string> = {
  maroon: 'text-maroon',
  teal:   'text-teal-600',
  blue:   'text-blue-600',
  amber:  'text-amber-600',
  slate:  'text-slate-500',
}

export default function DataCard({
  value, label, sub, accent = 'maroon',
}: {
  value: string
  label: string
  sub?: string
  accent?: Accent
}) {
  return (
    <div className={`bg-white rounded-xl border border-gray-100 border-t-[3px] ${TOP[accent]}
      px-5 py-7 text-center shadow-sm hover:-translate-y-0.5 hover:shadow-md transition-all
      flex-[0_0_180px] min-w-[160px]`}>
      <span className={`block text-4xl font-extrabold tracking-tight leading-none ${VAL[accent]}`}>
        {value}
      </span>
      <span className="block text-[13px] font-semibold text-gray-500 mt-2">{label}</span>
      {sub && <span className="block text-xs text-gray-300 mt-1">{sub}</span>}
    </div>
  )
}
