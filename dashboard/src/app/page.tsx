import DataCard from '@/components/DataCard'
import InfoBlock from '@/components/InfoBlock'
import { loadPanelOverview, loadGroupStats } from '@/lib/data'

const STORY = [
  {
    date: 'Chicago, 2016',
    heading: 'The Problem',
    body: 'The rapid growth of short-term rentals (STRs) on platforms like Airbnb and VRBO raised concerns about their impact on long-term housing supply and rental affordability across Chicago neighborhoods.',
    highlight: true,
  },
  {
    date: 'Shared Housing Ordinance',
    heading: 'The Policy',
    body: "Chicago's Shared Housing Ordinance introduced building-level STR prohibitions, rolled out in a staggered manner across the city — creating natural variation in when and where STRs were restricted.",
    highlight: true,
  },
  {
    date: '2017 – 2022',
    heading: 'Staggered Rollout',
    body: 'Different buildings and neighborhoods were subjected to prohibitions at different times. This staggered adoption is the foundation of our causal identification strategy.',
    highlight: false,
  },
  {
    date: 'Identification',
    heading: 'Design',
    body: "We use a staggered difference-in-differences design (Callaway & Sant'Anna 2021) to estimate the average treatment effect on treated tracts, avoiding the well-known bias of TWFE with heterogeneous effects.",
    highlight: false,
  },
]

export default function IntroductionPage() {
  const ov = loadPanelOverview('binary')
  const gs = loadGroupStats('binary')
  const treated = gs.find(g => g.group.includes('Eventually')) ?? { mean_rent: 0, std_dev: 0, n_tracts: 0 }
  const control  = gs.find(g => g.group.includes('Never'))     ?? { mean_rent: 0, std_dev: 0, n_tracts: 0 }

  return (
    <div>
      {/* Research question */}
      <div className="border-l-4 border-maroon bg-maroon/5 rounded-r-xl px-6 py-5 mb-10">
        <p className="text-[10px] font-bold uppercase tracking-widest text-maroon mb-2">Research Question</p>
        <p className="text-[15px] text-gray-700 leading-relaxed">
          Does prohibiting short-term rentals under Chicago&apos;s Shared Housing Ordinance change monthly
          rental prices in affected census tracts — and by how much?
        </p>
      </div>

      {/* Story grid */}
      <div className="grid grid-cols-2 gap-5 mb-10">
        {STORY.map(s => (
          <div
            key={s.heading}
            className={`border rounded-xl p-6 ${
              s.highlight
                ? 'border-maroon/20 bg-gradient-to-br from-maroon/5 to-white'
                : 'border-gray-100'
            }`}
          >
            <span className="inline-block bg-maroon/10 text-maroon text-[11px] font-bold rounded px-2 py-0.5 mb-3">
              {s.date}
            </span>
            <h3 className="text-[11px] font-bold uppercase tracking-wider text-maroon mb-2">{s.heading}</h3>
            <p className="text-[13px] text-gray-600 leading-relaxed">{s.body}</p>
          </div>
        ))}
      </div>

      {/* Treatment definition */}
      <div className="border border-gray-100 rounded-xl p-6 mb-10">
        <h3 className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-5">
          Treatment Definition — affects the number of treated tracts
        </h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-blue-50 border border-blue-200/70 rounded-xl p-5">
            <p className="text-[11px] font-bold uppercase tracking-wider text-blue-600 mb-3">Binary Indicator</p>
            <p className="text-[13px] text-gray-600 leading-relaxed">
              A tract is treated as soon as <em>any</em> STR prohibition takes effect within its
              boundaries, regardless of how many units are affected.
            </p>
            <div className="flex gap-3 mt-4">
              <div className="bg-blue-100 rounded-lg px-4 py-2 text-center">
                <span className="block text-xl font-extrabold text-blue-600">{treated.n_tracts.toLocaleString()}</span>
                <span className="block text-[10px] text-gray-500">Treated tracts</span>
              </div>
              <div className="bg-blue-100 rounded-lg px-4 py-2 text-center">
                <span className="block text-xl font-extrabold text-blue-600">{control.n_tracts.toLocaleString()}</span>
                <span className="block text-[10px] text-gray-500">Never-treated</span>
              </div>
            </div>
          </div>
          <div className="bg-teal-50 border border-teal-200/70 rounded-xl p-5">
            <p className="text-[11px] font-bold uppercase tracking-wider text-teal-600 mb-3">Threshold Indicator</p>
            <p className="text-[13px] text-gray-600 leading-relaxed">
              A tract is treated only when the share of prohibited STR units exceeds a minimum
              threshold of occupied housing units — a stricter, more conservative definition.
            </p>
            <p className="mt-4 text-[12px] text-gray-400 italic">
              Comparison of both definitions in the Robustness tab.
            </p>
          </div>
        </div>
      </div>

      {/* Data cards — centered */}
      <p className="text-[11px] font-bold uppercase tracking-wider text-gray-300 mb-4 text-center">
        Panel at a glance
      </p>
      <div className="flex flex-wrap gap-4 justify-center mb-10">
        <DataCard value={ov.n_tracts.toLocaleString()}                  label="Census Tracts"   sub="in rent panel"        accent="blue" />
        <DataCard value={ov.n_periods.toLocaleString()}                 label="Panel Months"    sub="2012 – 2022"          accent="teal" />
        <DataCard value={ov.tracts_eventually_treated.toLocaleString()} label="Treated Tracts"  sub="STR ever prohibited"  accent="maroon" />
        <DataCard value={ov.tracts_never_treated.toLocaleString()}      label="Control Tracts"  sub="never treated"        accent="amber" />
        <DataCard value={`${Math.round(ov.n_observations / 1000)}k`}   label="Observations"   sub="tract-month cells"    accent="slate" />
      </div>

      {/* Two-col info blocks */}
      <div className="grid grid-cols-2 gap-5">
        <InfoBlock
          title="Pre-treatment Rent — Treated vs Control"
          rows={[
            { label: 'Mean rent · treated tracts',  value: `$${treated.mean_rent.toFixed(0)} / mo` },
            { label: 'Mean rent · never-treated',   value: `$${control.mean_rent.toFixed(0)} / mo` },
            { label: 'Std dev · treated',           value: `$${treated.std_dev.toFixed(0)}` },
            { label: 'Std dev · never-treated',     value: `$${control.std_dev.toFixed(0)}` },
            {
              label: 'Difference in means',
              value: `$${(treated.mean_rent - control.mean_rent).toFixed(0)}`,
              valueClass: 'text-maroon',
            },
          ]}
        />
        <InfoBlock
          title="Panel Coverage"
          rows={[
            { label: 'Total tract-month cells',  value: ov.n_observations.toLocaleString() },
            { label: 'Tracts with full span',    value: `${ov.n_tracts} (100%)`,  valueClass: 'text-teal-600' },
            { label: 'Missing rent obs.',        value: '0.0%',                    valueClass: 'text-teal-600' },
            { label: 'Outcome variable',         value: 'ZORI ($/mo)' },
            { label: 'Treatment timing',         value: 'Staggered' },
          ]}
        />
      </div>
    </div>
  )
}
