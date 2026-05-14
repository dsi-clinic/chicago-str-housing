'use client'
import { useState } from 'react'

export interface PipelineStepperProps {
  // Stage C — full rent panel (before any matching)
  nPanel:       number   // 842
  nMonths:      number   // 128
  // Binary indicator (stage D / F)
  nTreatedBin:  number   // 373
  nPoolBin:     number   // 469
  nMatchedBin:  number   // 556
  nControlBin:  number   // 183
  // Threshold indicator (stage D / F)
  nTreatedThr:  number   // 274
  nPoolThr:     number   // 568
  nMatchedThr:  number   // 453
  nControlThr:  number   // 179
}

interface StepDef {
  id:         number
  label:      string
  count:      string
  badge:      string
  title:      string
  pillValue:  string
  pillSub:    string
  leftLabel:  string
  leftContent: 'text' | 'treatment-def' | 'matching-results'
  leftText:   string
  chips:      { val: string; label: string; color: string }[]
  rightLabel: string
  rightText:  string
  retention:  { pct: number; label: string; color: 'teal' | 'amber' }
}

function buildSteps(p: PipelineStepperProps): StepDef[] {
  const obs = (p.nPanel * p.nMonths).toLocaleString()
  return [
    {
      id: 1, label: 'All Chicago\nTracts', count: '1,332',
      badge: 'Step 1 of 6', title: 'All Chicago Census Tracts',
      pillValue: '1,332', pillSub: 'Census Tracts',
      leftLabel: 'Data source',
      leftContent: 'text',
      leftText: 'The analysis begins with all <b>1,332 census tracts</b> in Chicago from the 2023 TIGER/Line shapefile (Cook County, IL). Each tract covers roughly 1,200–8,000 residents and is the spatial unit of analysis throughout.',
      chips: [
        { val: '1,332', label: 'All tracts', color: 'maroon' },
        { val: '2023', label: 'TIGER vintage', color: 'blue' },
      ],
      rightLabel: 'Starting point',
      rightText: 'This is the starting universe — no tracts have been dropped yet. All subsequent steps apply geographic or data filters.',
      retention: { pct: 100, label: 'Starting universe', color: 'teal' },
    },
    {
      id: 2, label: 'ZIP→Tract\nCrosswalk', count: 'crosswalk built',
      badge: 'Step 2 of 6', title: 'ZIP Code → Census Tract Crosswalk',
      pillValue: 'built', pillSub: 'Crosswalk',
      leftLabel: 'What happens here',
      leftContent: 'text',
      leftText: 'ZORI (Zillow Observed Rent Index) provides monthly rent data at the <b>ZIP code level</b>. <code>ZipTractCrosswalkProcessor</code> uses spatial overlay in a projected CRS (EPSG:3435) to compute tract-area weights — how much of each tract lies within each ZIP. This is the correct weight for a <em>tract-level</em> outcome.',
      chips: [
        { val: 'ZIP', label: 'Input unit', color: 'blue' },
        { val: 'Tract', label: 'Output unit', color: 'teal' },
        { val: '867', label: 'Tracts with crosswalk', color: 'maroon' },
      ],
      rightLabel: 'Retention',
      rightText: 'No tracts are dropped here — the crosswalk only builds the geographic mapping. Tracts without any overlapping ZORI ZIP codes are dropped in the next step.',
      retention: { pct: 100, label: 'No tracts dropped — mapping only', color: 'teal' },
    },
    {
      id: 3, label: 'Rent Panel\nMatch', count: `${p.nPanel.toLocaleString()} tracts`,
      badge: 'Step 3 of 6', title: 'Rent Panel — ZORI matched to census tracts',
      pillValue: p.nPanel.toLocaleString(), pillSub: 'Rent-panel Tracts',
      leftLabel: 'What happens here',
      leftContent: 'text',
      leftText: `<code>TimeSeriesZipToTractProcessor</code> assigns monthly ZORI rent values to each census tract using the area-weighted crosswalk. Only tracts overlapping at least one ZORI-covered ZIP enter the panel.<br/><b>${p.nPanel.toLocaleString()} tracts × ${p.nMonths} months = ${obs} tract-month observations.</b> This is the full panel used for the primary full-panel CS estimate.`,
      chips: [
        { val: p.nPanel.toLocaleString(), label: 'Tracts in panel', color: 'teal' },
        { val: p.nMonths.toLocaleString(), label: 'Panel months', color: 'blue' },
        { val: obs, label: 'Observations', color: 'maroon' },
      ],
      rightLabel: 'Retention from Step 1',
      rightText: `${(1332 - p.nPanel).toLocaleString()} of the original 1,332 tracts are dropped — they fall in areas not covered by any ZORI ZIP code (industrial zones, O'Hare, sparse suburban edges). The remaining ${p.nPanel.toLocaleString()} form the <b>full rent panel</b> used in the primary CS estimation.`,
      retention: { pct: Math.round((p.nPanel / 1332) * 100), label: `${p.nPanel.toLocaleString()} / 1,332 tracts (${((p.nPanel / 1332) * 100).toFixed(0)}%)`, color: 'amber' },
    },
    {
      id: 4, label: 'Treatment\nDefinition', count: '2 indicators',
      badge: 'Step 4 of 6', title: 'Treatment Indicators — Binary vs Threshold',
      pillValue: '2', pillSub: 'Definitions',
      leftLabel: 'Two ways to define treatment',
      leftContent: 'treatment-def',
      leftText: '',
      chips: [],
      rightLabel: 'Retention',
      rightText: 'All rent-panel tracts are retained at this step — treatment assignment only <em>labels</em> tracts as treated or never-treated. The number of tracts differs between definitions because each uses a different threshold for what counts as a prohibited tract.',
      retention: { pct: 100, label: `100% of ${p.nPanel.toLocaleString()} panel tracts retained`, color: 'teal' },
    },
    {
      id: 5, label: 'Full-panel\nCS — Primary', count: 'primary estimate',
      badge: 'Step 5 of 6', title: 'Full-panel Callaway & Sant\'Anna — Primary Estimate',
      pillValue: 'primary', pillSub: 'Full-panel CS',
      leftLabel: 'Why this comes before matching',
      leftContent: 'text',
      leftText: 'The Callaway & Sant\'Anna estimator runs on the <b>full rent panel</b> (all matched rent-panel tracts, not-yet-treated or never-treated as controls). This is the <b>primary estimate</b> because it is robust to staggered adoption and heterogeneous effects without restricting the comparison group. Matching is kept as a robustness check — it does not strengthen identification, it only narrows comparators.',
      chips: [
        { val: '+56.0', label: 'Threshold ATT ($/mo)', color: 'teal' },
        { val: '+48.8', label: 'Binary ATT ($/mo)', color: 'maroon' },
      ],
      rightLabel: 'Primary results',
      rightText: 'Both treatment definitions yield positive full-panel ATT estimates (threshold: +$56/mo, binary: +$49/mo). These are the headline estimates presented in the Results and Models tabs. The matched and residualized specifications are sensitivity checks shown in the Models and Robustness tabs.',
      retention: { pct: 100, label: 'Full panel used — no sample restriction here', color: 'teal' },
    },
    {
      id: 6, label: 'Trend Matching\n(Robustness)', count: 'robustness only',
      badge: 'Step 6 of 6', title: 'Trend Matching — Robustness Restriction',
      pillValue: 'matched', pillSub: 'Robustness Sample',
      leftLabel: 'What the matching does',
      leftContent: 'matching-results',
      leftText: '',
      chips: [],
      rightLabel: 'Why it shrinks the sample',
      rightText: '<code>TrendMatchingProcessor</code> keeps only tracts with ≥ 6 pre-treatment months and matches each ever-treated tract to its k=3 nearest never-treated neighbours on two standardized features: <b>pre-treatment rent slope</b> and <b>average pre-treatment rent level</b>. This improves balance on rent levels (the main weakness of slope-only matching) but makes the comparison group much smaller. Present as robustness, not primary.',
      retention: { pct: Math.round((p.nMatchedThr / p.nPanel) * 100), label: `Binary: ${p.nMatchedBin} matched · Threshold: ${p.nMatchedThr} matched`, color: 'amber' },
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

export default function PipelineStepper(p: PipelineStepperProps) {
  const [active, setActive] = useState(1)
  const steps = buildSteps(p)
  const s = steps[active - 1]

  return (
    <div>
      {/* Step circles + connectors */}
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
              {/* Connector line — inline styles avoid Tailwind v4 arbitrary-value issues */}
              {i < steps.length - 1 && (
                <div style={{
                  position: 'absolute',
                  left: '50%',
                  right: '-50%',
                  top: '22px',
                  height: '2px',
                  zIndex: 0,
                  background: done ? '#14b8a6' : '#e5e7eb',
                }} />
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
        {/* Header */}
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
          {/* Left col */}
          <div className="p-7 border-r border-gray-50">
            <p className="text-[10px] font-bold uppercase tracking-wider text-gray-300 mb-3">{s.leftLabel}</p>

            {s.leftContent === 'treatment-def' && (
              <TreatmentDefPanel p={p} />
            )}
            {s.leftContent === 'matching-results' && (
              <MatchingResultsPanel p={p} />
            )}
            {s.leftContent === 'text' && (
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

          {/* Right col — retention only, no figures */}
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

/* ── Step 4: Treatment Definition side-by-side ── */
function TreatmentDefPanel({ p }: { p: PipelineStepperProps }) {
  return (
    <div className="space-y-3">
      <div className="bg-blue-50 border border-blue-200/60 rounded-xl p-4">
        <p className="text-[11px] font-bold uppercase tracking-wider text-blue-600 mb-2">Binary indicator</p>
        <p className="text-[12px] text-gray-600 leading-relaxed mb-3">
          A tract is treated as soon as <em>any</em> STR prohibition takes effect within its
          boundaries, regardless of how many units are affected.
        </p>
        <div className="flex gap-2">
          {[
            { val: p.nTreatedBin.toLocaleString(), label: 'Treated' },
            { val: p.nPoolBin.toLocaleString(),    label: 'Control pool' },
            { val: `${((p.nTreatedBin / (p.nTreatedBin + p.nPoolBin)) * 100).toFixed(0)}%`, label: 'Share treated' },
          ].map(c => (
            <div key={c.label} className="bg-blue-100 rounded-lg px-3 py-1.5 text-center flex-1">
              <span className="block text-base font-extrabold text-blue-600">{c.val}</span>
              <span className="block text-[9px] text-gray-500">{c.label}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-teal-50 border border-teal-200/60 rounded-xl p-4">
        <p className="text-[11px] font-bold uppercase tracking-wider text-teal-600 mb-2">Threshold indicator</p>
        <p className="text-[12px] text-gray-600 leading-relaxed mb-3">
          A tract is treated only when the share of prohibited STR units exceeds a minimum
          threshold of occupied housing units — stricter, fewer treated tracts.
        </p>
        <div className="flex gap-2">
          {[
            { val: p.nTreatedThr.toLocaleString(), label: 'Treated' },
            { val: p.nPoolThr.toLocaleString(),    label: 'Control pool' },
            { val: `${((p.nTreatedThr / (p.nTreatedThr + p.nPoolThr)) * 100).toFixed(0)}%`, label: 'Share treated' },
          ].map(c => (
            <div key={c.label} className="bg-teal-100 rounded-lg px-3 py-1.5 text-center flex-1">
              <span className="block text-base font-extrabold text-teal-600">{c.val}</span>
              <span className="block text-[9px] text-gray-500">{c.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

/* ── Step 6: Matching results side-by-side ── */
function MatchingResultsPanel({ p }: { p: PipelineStepperProps }) {
  return (
    <div className="space-y-3">
      <p className="text-[12px] text-gray-600 leading-relaxed">
        Nearest-neighbour matching (k=3) on two standardized features:
        <b> pre-treatment rent slope</b> and <b>average pre-treatment rent level</b>.
        The two-feature match improves balance on rent levels vs slope-only matching.
      </p>

      <div className="grid grid-cols-2 gap-3">
        <div className="bg-blue-50 border border-blue-200/60 rounded-xl p-4">
          <p className="text-[10px] font-bold text-blue-600 uppercase tracking-wider mb-2">Binary</p>
          <div className="space-y-1.5">
            {[
              { label: 'Matched sample',     val: p.nMatchedBin.toLocaleString() },
              { label: 'Treated matched',    val: p.nTreatedBin.toLocaleString() },
              { label: 'Control matched',    val: p.nControlBin.toLocaleString() },
            ].map(r => (
              <div key={r.label} className="flex justify-between text-[11px]">
                <span className="text-gray-500">{r.label}</span>
                <span className="font-bold text-blue-700">{r.val}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="bg-teal-50 border border-teal-200/60 rounded-xl p-4">
          <p className="text-[10px] font-bold text-teal-600 uppercase tracking-wider mb-2">Threshold</p>
          <div className="space-y-1.5">
            {[
              { label: 'Matched sample',     val: p.nMatchedThr.toLocaleString() },
              { label: 'Treated matched',    val: p.nTreatedThr.toLocaleString() },
              { label: 'Control matched',    val: p.nControlThr.toLocaleString() },
            ].map(r => (
              <div key={r.label} className="flex justify-between text-[11px]">
                <span className="text-gray-500">{r.label}</span>
                <span className="font-bold text-teal-700">{r.val}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <p className="text-[10px] text-gray-400 italic">
        This matched sample is used only in robustness specifications.
        The primary estimate (Step 5) uses the full panel.
      </p>
    </div>
  )
}
