'use client'
import { useState } from 'react'
import FigureSlot from './FigureSlot'

interface StepCounts { nTracts: number; nTreated: number; nControl: number }

interface StepDef {
  id: number
  label: string
  count: string
  badge: string
  title: string
  pillValue: string
  pillSub: string
  leftLabel: string
  leftText: string
  chips: { val: string; label: string; color: string }[]
  rightLabel: string
  rightText: string
  retention: { pct: number; label: string; color: 'teal' | 'amber' }
  figFile: string | null
  figAlt: string | null
  isTreatmentStep?: true
}

function buildSteps(c: StepCounts): StepDef[] {
  return [
    {
      id: 1, label: 'All Chicago\nTracts', count: '1,332',
      badge: 'Step 1 of 6', title: 'All Chicago Census Tracts',
      pillValue: '1,332', pillSub: 'Census Tracts',
      leftLabel: 'Data Source',
      leftText: 'The analysis begins with all <b>1,332 census tracts</b> in Chicago from the 2023 TIGER/Line shapefile (Cook County, IL). These define the geographic units of observation — each tract covers roughly 1,200–8,000 residents.',
      chips: [
        { val: '1,332', label: 'Total tracts', color: 'maroon' },
        { val: '2023', label: 'TIGER vintage', color: 'blue' },
      ],
      rightLabel: 'Starting Point',
      rightText: 'This is the starting universe — no tracts have been dropped yet. All subsequent steps apply filters that reduce this number.',
      retention: { pct: 100, label: 'Starting universe', color: 'teal' },
      figFile: null, figAlt: null,
    },
    {
      id: 2, label: 'ZIP→Tract\nCrosswalk', count: 'crosswalk built',
      badge: 'Step 2 of 6', title: 'ZIP Code → Census Tract Crosswalk',
      pillValue: 'built', pillSub: 'Crosswalk',
      leftLabel: 'What Happens Here',
      leftText: 'ZORI (Zillow Observed Rent Index) provides monthly rent data at the <b>ZIP code level</b>, but our unit of analysis is <b>census tracts</b>. <code>ZipTractCrosswalkProcessor</code> uses spatial overlay to map each ZIP code to the census tracts it intersects, weighted by area overlap.',
      chips: [
        { val: 'ZIP', label: 'Input unit', color: 'blue' },
        { val: 'Tract', label: 'Output unit', color: 'teal' },
      ],
      rightLabel: 'Retention',
      rightText: 'No tracts are dropped at this step — the crosswalk only builds the mapping. Tracts are dropped in the next step when rent data is unavailable for their ZIP codes.',
      retention: { pct: 100, label: 'No tracts dropped — crosswalk only', color: 'teal' },
      figFile: null, figAlt: null,
    },
    {
      id: 3, label: 'Rent Panel\nMatch', count: `${c.nTracts.toLocaleString()} tracts`,
      badge: 'Step 3 of 6', title: 'ZIP→Tract Rent Panel (ZORI)',
      pillValue: c.nTracts.toLocaleString(), pillSub: 'Tracts Retained',
      leftLabel: 'What Happens Here',
      leftText: `<code>TimeSeriesZipToTractProcessor</code> assigns monthly ZORI rent values to each census tract via the crosswalk. Only tracts matched to at least one ZORI-covered ZIP code enter the panel.<br/><b>${c.nTracts.toLocaleString()} tracts × 128 months = 62,336 tract-month observations.</b>`,
      chips: [
        { val: c.nTracts.toLocaleString(), label: 'Tracts in panel', color: 'teal' },
        { val: '128', label: 'Panel months', color: 'blue' },
        { val: '62,336', label: 'Observations', color: 'maroon' },
      ],
      rightLabel: 'Retention from Step 1',
      rightText: '845 of the original 1,332 tracts are dropped — they fall in areas not covered by any ZORI ZIP code (industrial zones, O\'Hare, sparse suburban edges).',
      retention: { pct: 37, label: `${c.nTracts.toLocaleString()} / 1,332 tracts (36.6%)`, color: 'amber' },
      figFile: '/data/binary/data_funnel.png', figAlt: 'Data funnel showing tract counts at each pipeline stage',
    },
    {
      id: 4, label: 'STR Prohibition\nDates → Tract', count: 'dates assigned',
      badge: 'Step 4 of 6', title: 'STR Prohibition Dates Aggregated to Tract',
      pillValue: c.nTracts.toLocaleString(), pillSub: 'All Retained',
      leftLabel: 'What Happens Here',
      leftText: '<code>TractProhibitionDatesProcessor</code> aggregates building-level STR prohibition records to the census tract level. For each tract, it finds the <b>first month any STR prohibition took effect</b> — the treatment timing variable used in all DiD models.',
      chips: [
        { val: c.nTreated.toLocaleString(), label: 'Tracts with prohibition', color: 'maroon' },
        { val: c.nControl.toLocaleString(), label: 'No prohibition', color: 'teal' },
      ],
      rightLabel: 'Retention',
      rightText: 'All rent-panel tracts are retained. Prohibition dates are assigned where available — tracts with no prohibition remain as never-treated controls.',
      retention: { pct: 100, label: '100% of rent-panel tracts retained', color: 'teal' },
      figFile: '/data/binary/did_story_map.png', figAlt: 'Map of ever-treated vs never-treated tracts',
    },
    {
      id: 5, label: 'Treatment\nAssignment', count: `${c.nTreated}+${c.nControl}`,
      badge: 'Step 5 of 6', title: 'Treatment Assignment',
      pillValue: `${c.nTreated}+${c.nControl}`, pillSub: 'Treated + Control',
      leftLabel: 'Treatment Definition',
      leftText: '', chips: [],
      rightLabel: 'Retention',
      rightText: 'All rent-panel tracts are retained — treatment assignment <i>labels</i> tracts, it does not remove them. Only the threshold of what counts as treated changes between the two definitions.',
      retention: { pct: 100, label: '100% retained — only labels change', color: 'teal' },
      figFile: '/data/binary/did_adoption_curve.png', figAlt: 'Cumulative treated tracts over time',
      isTreatmentStep: true,
    },
    {
      id: 6, label: 'Trend Matching\n& Pre-trend Filter', count: 'final sample',
      badge: 'Step 6 of 6', title: 'Trend Matching & Pre-treatment Filter',
      pillValue: 'matched', pillSub: 'DiD Sample',
      leftLabel: 'What Happens Here',
      leftText: '<code>TrendMatchingProcessor</code> applies two filters: (1) keeps only tracts with at least <b>6 months of pre-treatment data</b> before the first treated month, and (2) matches each ever-treated tract to its <b>k nearest never-treated neighbors</b> by pre-treatment rent slope. This is the final estimand sample for all TWFE and CS models.',
      chips: [
        { val: '≥6', label: 'Pre-periods required', color: 'blue' },
        { val: 'k', label: 'Matched controls', color: 'teal' },
      ],
      rightLabel: 'Retention',
      rightText: 'Some tracts are dropped: treated tracts lacking enough pre-treatment months, and never-treated tracts not selected as matches. Exact count depends on k and the panel window.',
      retention: { pct: 75, label: 'Varies — depends on k and panel window', color: 'amber' },
      figFile: '/data/binary/did_parallel_trends.png', figAlt: 'Pre-treatment rent trends: treated vs matched controls',
    },
  ]
}

const RET_BAR: Record<'teal' | 'amber', string> = {
  teal:  'bg-gradient-to-r from-teal-500 to-blue-500',
  amber: 'bg-gradient-to-r from-amber-500 to-yellow-400',
}
const RET_TEXT: Record<'teal' | 'amber', string> = {
  teal:  'text-teal-600',
  amber: 'text-amber-600',
}
const CHIP_BG: Record<string, string> = {
  maroon: 'bg-maroon/10 text-maroon',
  teal:   'bg-teal-50 text-teal-600',
  blue:   'bg-blue-50 text-blue-600',
  amber:  'bg-amber-50 text-amber-600',
}

export default function PipelineStepper({ nTracts, nTreated, nControl }: StepCounts) {
  const [active, setActive] = useState(1)
  const [treatMode, setTreatMode] = useState<'binary' | 'threshold'>('binary')
  const steps = buildSteps({ nTracts, nTreated, nControl })
  const s = steps[active - 1]

  return (
    <div>
      {/* Step circles */}
      <div className="flex items-start mb-8 relative">
        {steps.map((step, i) => {
          const done     = i + 1 < active
          const isActive = i + 1 === active
          return (
            <div
              key={step.id}
              className="flex-1 flex flex-col items-center relative cursor-pointer group"
              onClick={() => setActive(step.id)}
            >
              {i < steps.length - 1 && (
                <div className={`absolute left-1/2 right-[-50%] top-[22px] h-0.5 z-0 ${done ? 'bg-teal-500' : 'bg-gray-200'}`} />
              )}
              <div className={[
                'w-11 h-11 rounded-full z-10 flex items-center justify-center text-[15px] font-bold transition-all',
                done      ? 'bg-teal-500 text-white border-2 border-teal-500'
                : isActive ? 'bg-maroon text-white border-2 border-maroon ring-4 ring-maroon/10'
                : 'bg-white text-gray-300 border-2 border-gray-200 group-hover:border-maroon group-hover:text-maroon',
              ].join(' ')}>
                {done ? '✓' : step.id}
              </div>
              <p className={`text-[10px] font-semibold text-center mt-2 leading-tight max-w-[88px] ${
                done ? 'text-teal-600' : isActive ? 'text-maroon font-bold' : 'text-gray-400'
              }`}>
                {step.label.split('\n').map((l, j) => <span key={j} className="block">{l}</span>)}
              </p>
              <p className={`text-[10px] font-semibold mt-0.5 text-center ${
                done ? 'text-teal-500' : isActive ? 'text-maroon' : 'text-gray-300'
              }`}>
                {step.count}
              </p>
            </div>
          )
        })}
      </div>

      {/* Detail panel */}
      <div className="border border-gray-100 rounded-2xl overflow-hidden shadow-lg">
        <div className="flex items-start justify-between px-8 py-5 border-b border-gray-100 bg-gradient-to-br from-maroon/5 to-white">
          <div>
            <span className="inline-block bg-maroon/10 text-maroon text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded mb-2">
              {s.badge}
            </span>
            <h3 className="text-lg font-extrabold text-gray-900 tracking-tight">{s.title}</h3>
          </div>
          <div className="bg-maroon text-white rounded-xl px-5 py-3 text-center flex-shrink-0 ml-4">
            <span className="block text-xl font-extrabold tracking-tight">{s.pillValue}</span>
            <span className="block text-[9px] uppercase tracking-widest opacity-70 mt-0.5">{s.pillSub}</span>
          </div>
        </div>

        <div className="grid grid-cols-2">
          {/* Left */}
          <div className="p-7 border-r border-gray-50">
            <p className="text-[10px] font-bold uppercase tracking-wider text-gray-300 mb-3">{s.leftLabel}</p>
            {s.isTreatmentStep ? (
              <TreatmentToggle treatMode={treatMode} setTreatMode={setTreatMode} nTreated={nTreated} nControl={nControl} />
            ) : (
              <>
                <p className="text-sm text-gray-600 leading-relaxed" dangerouslySetInnerHTML={{ __html: s.leftText }} />
                {s.chips.length > 0 && (
                  <div className="flex gap-3 flex-wrap mt-5">
                    {s.chips.map(c => (
                      <div key={c.label} className={`rounded-xl px-4 py-2 text-center ${CHIP_BG[c.color] ?? ''}`}>
                        <span className="block text-xl font-extrabold">{c.val}</span>
                        <span className="block text-[10px] text-gray-500 mt-0.5">{c.label}</span>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>

          {/* Right */}
          <div className="p-7">
            <p className="text-[10px] font-bold uppercase tracking-wider text-gray-300 mb-3">{s.rightLabel}</p>
            <p className="text-sm text-gray-600 leading-relaxed" dangerouslySetInnerHTML={{ __html: s.rightText }} />
            <div className="mt-5">
              <div className="flex justify-between text-[12px] mb-1.5">
                <span className="text-gray-500">Retention from previous step</span>
                <span className={`font-bold ${RET_TEXT[s.retention.color]}`}>{s.retention.pct}%</span>
              </div>
              <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${RET_BAR[s.retention.color]}`}
                  style={{ width: `${s.retention.pct}%` }}
                />
              </div>
              <p className="text-[10px] text-gray-300 mt-1.5">{s.retention.label}</p>
            </div>
            {s.figFile && (
              <FigureSlot src={s.figFile} alt={s.figAlt ?? ''} label="Figure" className="mt-5" />
            )}
          </div>
        </div>

        {/* Footer nav */}
        <div className="flex justify-between items-center px-8 py-3.5 border-t border-gray-100 bg-gray-50">
          <button
            onClick={() => setActive(a => Math.max(1, a - 1))}
            disabled={active === 1}
            className="text-[13px] font-semibold text-maroon border border-maroon/20 rounded-lg px-4 py-2 bg-white hover:bg-maroon/5 transition disabled:text-gray-300 disabled:border-gray-100 disabled:cursor-default"
          >
            ← {active > 1 ? `Step ${active - 1}: ${steps[active - 2].label.replace('\n', ' ')}` : 'Previous'}
          </button>
          <span className="text-[11px] text-gray-400">Step {active} of {steps.length}</span>
          <button
            onClick={() => setActive(a => Math.min(steps.length, a + 1))}
            disabled={active === steps.length}
            className="text-[13px] font-semibold text-maroon border border-maroon/20 rounded-lg px-4 py-2 bg-white hover:bg-maroon/5 transition disabled:text-gray-300 disabled:border-gray-100 disabled:cursor-default"
          >
            {active < steps.length ? `Step ${active + 1}: ${steps[active].label.replace('\n', ' ')} →` : 'Next →'}
          </button>
        </div>
      </div>
    </div>
  )
}

function TreatmentToggle({
  treatMode, setTreatMode, nTreated, nControl,
}: {
  treatMode: 'binary' | 'threshold'
  setTreatMode: (m: 'binary' | 'threshold') => void
  nTreated: number
  nControl: number
}) {
  return (
    <div>
      <div className="flex border border-gray-200 rounded-lg overflow-hidden w-fit mb-4">
        {(['binary', 'threshold'] as const).map(m => (
          <button
            key={m}
            onClick={() => setTreatMode(m)}
            className={[
              'px-5 py-2 text-[13px] font-semibold transition capitalize',
              m === 'binary'    && treatMode === 'binary'    ? 'bg-blue-50 text-blue-600' : '',
              m === 'threshold' && treatMode === 'threshold' ? 'bg-teal-50 text-teal-600' : '',
              treatMode !== m ? 'text-gray-400 hover:text-gray-600' : '',
            ].join(' ')}
          >
            {m === 'binary' ? 'Binary' : 'Threshold'}
          </button>
        ))}
      </div>

      {treatMode === 'binary' ? (
        <div className="bg-blue-50 border border-blue-200/70 rounded-xl p-5">
          <p className="text-[13px] text-gray-600 leading-relaxed">
            A tract is <strong>treated</strong> as soon as <em>any</em> STR prohibition takes effect
            within its boundaries — regardless of how many units are affected.
          </p>
          <div className="flex gap-3 mt-4">
            {[
              { val: nTreated.toLocaleString(), label: 'Treated tracts' },
              { val: nControl.toLocaleString(), label: 'Never-treated' },
              { val: `${((nTreated / (nTreated + nControl)) * 100).toFixed(1)}%`, label: 'Share treated' },
            ].map(c => (
              <div key={c.label} className="bg-blue-100 rounded-lg px-4 py-2 text-center">
                <span className="block text-xl font-extrabold text-blue-600">{c.val}</span>
                <span className="block text-[10px] text-gray-500">{c.label}</span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="bg-teal-50 border border-teal-200/70 rounded-xl p-5">
          <p className="text-[13px] text-gray-600 leading-relaxed">
            A tract is treated only when the share of prohibited STR units exceeds a minimum
            threshold of occupied housing units — a stricter definition with <em>fewer treated tracts</em>.
          </p>
          <div className="flex gap-3 mt-4">
            {[
              { val: `< ${nTreated}`, label: 'Treated tracts' },
              { val: `> ${nControl}`, label: 'Never-treated' },
              { val: 'stricter', label: 'Definition' },
            ].map(c => (
              <div key={c.label} className="bg-teal-100 rounded-lg px-4 py-2 text-center">
                <span className="block text-xl font-extrabold text-teal-600">{c.val}</span>
                <span className="block text-[10px] text-gray-500">{c.label}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      <p className="text-[11px] text-gray-300 italic mt-3">
        Both definitions compared side-by-side in the <strong>Robustness</strong> tab.
      </p>
    </div>
  )
}
