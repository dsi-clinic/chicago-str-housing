import DataCard from '@/components/DataCard'
import InfoBlock from '@/components/InfoBlock'
import TreatmentMap from '@/components/TreatmentMap'
import { loadSampleLineage, loadGroupStats } from '@/lib/data'

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
  // Binary lineage
  const lineage  = loadSampleLineage('binary')
  const stageA   = lineage.find(s => s.stage_code === 'A')
  const stageC   = lineage.find(s => s.stage_code === 'C')
  const stageDbin = lineage.find(s => s.stage_code === 'D')
  const stageFbin = lineage.find(s => s.stage_code === 'F')

  const nAll      = stageA?.n_tracts       ?? 1332
  const nPanel    = stageC?.n_tracts       ?? 842
  const nMonths   = stageC?.n_months       ?? 128
  const nTreated  = stageDbin?.treated     ?? 373
  const nPool     = stageDbin?.never_treated ?? 469
  const nMatched  = stageFbin?.n_tracts    ?? 556
  const nControls = nMatched - nTreated

  // Threshold lineage — exact counts for the threshold indicator box
  const lineageT   = loadSampleLineage('threshold')
  const stageDthr  = lineageT.find(s => s.stage_code === 'D')
  const stageFthr  = lineageT.find(s => s.stage_code === 'F')
  const nTreatedT  = stageDthr?.treated      ?? 274
  const nPoolT     = stageDthr?.never_treated ?? 568
  const nMatchedT  = stageFthr?.n_tracts     ?? 453
  const nControlsT = nMatchedT - nTreatedT

  // Group stats for rent balance info block (from matched binary sample)
  const gs       = loadGroupStats('binary')
  const treated  = gs.find(g => g.group.includes('Eventually')) ?? { mean_rent: 0, std_dev: 0, n_tracts: nTreated }
  const control  = gs.find(g => g.group.includes('Never'))     ?? { mean_rent: 0, std_dev: 0, n_tracts: nControls }

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
                <span className="block text-xl font-extrabold text-blue-600">{nTreated.toLocaleString()}</span>
                <span className="block text-[10px] text-gray-500">Treated tracts</span>
              </div>
              <div className="bg-blue-100 rounded-lg px-4 py-2 text-center">
                <span className="block text-xl font-extrabold text-blue-600">{nPool.toLocaleString()}</span>
                <span className="block text-[10px] text-gray-500">Control pool (pre-match)</span>
              </div>
              <div className="bg-blue-100 rounded-lg px-4 py-2 text-center">
                <span className="block text-xl font-extrabold text-blue-600">{nControls.toLocaleString()}</span>
                <span className="block text-[10px] text-gray-500">Matched controls</span>
              </div>
            </div>
          </div>
          <div className="bg-teal-50 border border-teal-200/70 rounded-xl p-5">
            <p className="text-[11px] font-bold uppercase tracking-wider text-teal-600 mb-3">Threshold Indicator</p>
            <p className="text-[13px] text-gray-600 leading-relaxed">
              A tract is treated only when the share of prohibited STR units exceeds a minimum
              threshold of occupied housing units — stricter, fewer treated tracts.
            </p>
            <div className="flex gap-3 mt-4">
              <div className="bg-teal-100 rounded-lg px-4 py-2 text-center">
                <span className="block text-xl font-extrabold text-teal-600">{nTreatedT.toLocaleString()}</span>
                <span className="block text-[10px] text-gray-500">Treated tracts</span>
              </div>
              <div className="bg-teal-100 rounded-lg px-4 py-2 text-center">
                <span className="block text-xl font-extrabold text-teal-600">{nPoolT.toLocaleString()}</span>
                <span className="block text-[10px] text-gray-500">Control pool (pre-match)</span>
              </div>
              <div className="bg-teal-100 rounded-lg px-4 py-2 text-center">
                <span className="block text-xl font-extrabold text-teal-600">{nControlsT.toLocaleString()}</span>
                <span className="block text-[10px] text-gray-500">Matched controls</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Interactive treatment indicator maps */}
      <div className="mb-10">
        <h3 className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-1">
          Treatment indicators at census-tract level
        </h3>
        <p className="text-[13px] text-gray-500 mb-5 leading-relaxed max-w-2xl">
          The two maps below show the same Chicago tracts coloured by treatment status under
          each indicator. <span className="font-semibold text-maroon">Red</span> = treated,{' '}
          <span className="font-semibold text-blue-600">blue</span> = never-treated controls,
          grey = outside the rent-panel sample. Hover a tract to see its role.
        </p>
        <div className="grid grid-cols-2 gap-6">
          <TreatmentMap
            geojsonUrl="/data/binary/tracts_treatment.geojson"
            title="Binary indicator"
            subtitle={`${nTreated.toLocaleString()} treated · ${nPool.toLocaleString()} control pool · ${nMatched.toLocaleString()} matched sample`}
          />
          <TreatmentMap
            geojsonUrl="/data/threshold/tracts_treatment.geojson"
            title="Threshold indicator"
            subtitle={`${nTreatedT.toLocaleString()} treated · ${nPoolT.toLocaleString()} control pool · ${nMatchedT.toLocaleString()} matched sample`}
          />
        </div>
      </div>

      {/* Data cards — centered, showing the full audit funnel story */}
      <p className="text-[11px] font-bold uppercase tracking-wider text-gray-300 mb-4 text-center">
        Sample construction at a glance
      </p>
      <div className="flex flex-wrap gap-4 justify-center mb-10">
        <DataCard value={nAll.toLocaleString()}     label="All Chicago Tracts"   sub="starting universe"     accent="slate" />
        <DataCard value={nPanel.toLocaleString()}   label="Rent-panel Tracts"    sub="with ZORI coverage"    accent="blue" />
        <DataCard value={nMonths.toLocaleString()}  label="Panel Months"         sub="2015 – 2022"           accent="teal" />
        <DataCard value={nTreated.toLocaleString()} label="Treated Tracts"       sub="binary, pre-match"     accent="maroon" />
        <DataCard value={nMatched.toLocaleString()} label="Analysis Sample"      sub={`${nTreated}T + ${nControls}C`} accent="amber" />
      </div>

      {/* Two-col info blocks */}
      <div className="grid grid-cols-2 gap-5">
        <InfoBlock
          title="Pre-treatment Rent — Treated vs Matched Controls"
          rows={[
            { label: 'Mean rent · treated tracts',  value: `$${treated.mean_rent.toFixed(0)} / mo` },
            { label: 'Mean rent · matched controls', value: `$${control.mean_rent.toFixed(0)} / mo` },
            { label: 'Std dev · treated',           value: `$${treated.std_dev.toFixed(0)}` },
            { label: 'Std dev · matched controls',  value: `$${control.std_dev.toFixed(0)}` },
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
            { label: 'Total tract-month cells (panel)',   value: (nPanel * nMonths).toLocaleString() },
            { label: 'Total tract-month cells (matched)', value: (nMatched * nMonths).toLocaleString() },
            { label: 'Missing rent obs.',                 value: '0.0%',        valueClass: 'text-teal-600' },
            { label: 'Outcome variable',                  value: 'ZORI ($/mo)' },
            { label: 'Treatment timing',                  value: 'Staggered'   },
          ]}
        />
      </div>
    </div>
  )
}
