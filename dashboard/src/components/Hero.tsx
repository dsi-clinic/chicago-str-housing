export interface HeroPill { value: string; label: string; sub?: string }

export default function Hero({ pills }: { pills: HeroPill[] }) {
  return (
    <header className="border-b border-gray-100 pt-9 pb-6">
      {/* max-w-5xl mx-auto px-14 matches the <main> container width */}
      <div className="max-w-5xl mx-auto px-14">
        <div className="flex justify-between items-start mb-7">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-widest text-maroon mb-2">
              Analysis Report · Data Science Clinic · University of Chicago
            </p>
            <h1 className="text-2xl font-extrabold tracking-tight leading-tight max-w-lg">
              Impact of STR Prohibitions on Chicago Rental Prices
            </h1>
            <p className="mt-2 text-sm text-gray-500 leading-relaxed">
              Staggered Difference-in-Differences · Census Tract Level Analysis
            </p>
          </div>
          <div className="text-right text-sm text-gray-500 border-l border-gray-100 pl-6 whitespace-nowrap ml-8">
            <strong className="block text-[15px] font-bold text-gray-900 mb-1">Andrés F. Camacho</strong>
            University of Chicago<br />Data Science Clinic<br />2025
          </div>
        </div>

        <div className="flex gap-3 flex-wrap">
          {pills.map(p => (
            <div key={p.label} className="border border-maroon/20 rounded-xl px-6 py-3 text-center min-w-[110px] shadow-sm">
              <span className="block text-2xl font-extrabold text-maroon leading-none tracking-tight">
                {p.value}
              </span>
              <span className="block text-[10px] uppercase tracking-wider text-gray-400 mt-1 font-medium">
                {p.label}
              </span>
              {p.sub && (
                <span className="block text-[9px] text-gray-300 mt-0.5">{p.sub}</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </header>
  )
}
