import FigureSlot from '@/components/FigureSlot'
import StatTable from '@/components/StatTable'

/* ATT summary from docs/DID_RESULTS_STORY.md — update when pipeline reruns */
const SPEC_TABLE = [
  ['CS full-panel',                        '56.0', '(0.45)', '48.8', '(0.53)', 'Primary'],
  ['CS matched sample',                    '14.7', '(0.49)', '26.1', '(0.62)', 'Robustness'],
  ['CS matched + ACS + tract trends',     '−89.6', '(0.54)', '−70.8', '(0.61)', 'Robustness†'],
]

const SPEC_STACK = [
  {
    tier:     '① Primary',
    color:    'border-maroon',
    bg:       'bg-maroon/5',
    label:    'Full-panel Callaway & Sant\'Anna',
    attT:     '+56.0',
    seT:      '(0.45)',
    attB:     '+48.8',
    seB:      '(0.53)',
    figB:     '/data/binary/did_callaway_santanna_event_study_full_panel.png',
    figT:     '/data/threshold/did_callaway_santanna_event_study_full_panel.png',
    figAlt:   'CS full-panel event study',
    prose: `The heterogeneity-robust CS estimator on the full rent panel, before any sample restriction.
            Not-yet-treated and never-treated tracts are used as controls. This is the most defensible
            primary estimate — it does not discard most controls and is robust to staggered adoption.`,
  },
  {
    tier:     '② Robustness',
    color:    'border-blue-500',
    bg:       'bg-blue-50',
    label:    'CS on matched sample (k=3 NN on slope + pre-rent)',
    attT:     '+14.7',
    seT:      '(0.49)',
    attB:     '+26.1',
    seB:      '(0.62)',
    figB:     '/data/binary/did_callaway_santanna_event_study.png',
    figT:     '/data/threshold/did_callaway_santanna_event_study.png',
    figAlt:   'CS matched-sample event study',
    prose: `Same CS estimator but restricted to the trend-matched sample (treated tracts matched to
            k=3 never-treated neighbours by pre-treatment slope and rent level). The effect shrinks
            materially — especially under threshold — but the sign remains positive.
            Matching should be read as a comparison-group restriction, not as full identification.`,
  },
  {
    tier:     '③ Robustness†',
    color:    'border-amber-500',
    bg:       'bg-amber-50',
    label:    'CS matched + ACS covariates + tract-specific linear trends',
    attT:     '−89.6',
    seT:      '(0.54)',
    attB:     '−70.8',
    seB:      '(0.61)',
    figB:     '/data/binary/did_callaway_santanna_event_study_with_controls.png',
    figT:     '/data/threshold/did_callaway_santanna_event_study_with_controls.png',
    figAlt:   'CS residualized event study',
    prose: `Residualizes rent on ACS covariates (income, education, occupancy) and a tract-specific
            linear pre-trend before running CS. The estimate flips strongly negative — suggesting that
            treated tracts were already on systematically higher rent trajectories once observables and
            linear trends are partialled out. † Not directly comparable to the raw-rent ATT above;
            the outcome is residualized, not in original $/mo units.`,
  },
]

export default function ModelsPage() {
  return (
    <div>
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">Estimators & Specification Stack</h2>
      <p className="text-[15px] text-gray-500 mb-10 max-w-2xl leading-relaxed">
        Three CS designs in order of econometric strength. Read them from top to bottom:
        each layer adds a restriction or adjustment. The full-panel result is the headline;
        the others show sensitivity.
      </p>

      {/* ── Results narrative callout ── */}
      <div className="border-l-4 border-maroon bg-maroon/5 rounded-r-xl px-6 py-5 mb-10">
        <p className="text-[10px] font-bold uppercase tracking-widest text-maroon mb-2">Key narrative</p>
        <p className="text-[14px] text-gray-700 leading-relaxed">
          The primary specification uses the full rent panel and the CS estimator, which is robust
          to heterogeneous treatment timing. Both treatment definitions yield <strong>positive full-panel
          ATTs</strong>. Matching reduces the effect size but does not reverse the sign. The residualized
          specification flips negative — treated tracts differ meaningfully in observables and baseline
          trends. Full-panel CS is the headline; matched and residualized are robustness checks.
        </p>
      </div>

      {/* ── ATT Summary Table ── */}
      <div className="mb-10">
        <h3 className="text-lg font-bold mb-3">Aggregate ATT by specification</h3>
        <StatTable
          headers={['Specification', 'Threshold ATT', 'Threshold SE', 'Binary ATT', 'Binary SE', 'Role']}
          rows={SPEC_TABLE}
        />
        <p className="text-[11px] text-gray-400 mt-2">
          † Residualized estimate not in original $/mo units — not directly comparable to rows above.
          Values from <code className="bg-gray-100 px-1 rounded text-[10px]">docs/DID_RESULTS_STORY.md</code>.
        </p>
      </div>

      {/* ── Specification cards ── */}
      {SPEC_STACK.map(s => (
        <div key={s.tier} className={`border-l-4 ${s.color} ${s.bg} rounded-r-xl p-0 mb-8 overflow-hidden`}>
          {/* Header */}
          <div className="px-6 pt-5 pb-4">
            <div className="flex items-baseline gap-3 mb-1">
              <span className="text-[11px] font-bold uppercase tracking-wider text-gray-500">{s.tier}</span>
              <span className="text-[15px] font-bold text-gray-900">{s.label}</span>
            </div>
            <p className="text-[13px] text-gray-600 leading-relaxed max-w-3xl mb-4">{s.prose}</p>
            {/* ATT pills */}
            <div className="flex gap-6">
              <div>
                <span className="text-[10px] uppercase tracking-wider text-gray-400 block mb-0.5">Threshold ATT</span>
                <span className="text-2xl font-extrabold text-gray-900 tracking-tight">{s.attT}</span>
                <span className="text-sm text-gray-400 ml-1">{s.seT}</span>
                <span className="text-xs text-gray-400 ml-1">$/mo</span>
              </div>
              <div>
                <span className="text-[10px] uppercase tracking-wider text-gray-400 block mb-0.5">Binary ATT</span>
                <span className="text-2xl font-extrabold text-gray-900 tracking-tight">{s.attB}</span>
                <span className="text-sm text-gray-400 ml-1">{s.seB}</span>
                <span className="text-xs text-gray-400 ml-1">$/mo</span>
              </div>
            </div>
          </div>
          {/* Event study figures */}
          <div className="grid grid-cols-2 gap-4 px-6 pb-5">
            <FigureSlot src={s.figT} alt={`${s.figAlt} — threshold`} label="Threshold indicator" />
            <FigureSlot src={s.figB} alt={`${s.figAlt} — binary`}    label="Binary indicator" />
          </div>
        </div>
      ))}

      {/* ── TWFE comparison (secondary) ── */}
      <div className="border border-gray-100 rounded-xl p-6">
        <h3 className="text-[14px] font-bold text-gray-700 mb-1">Appendix: TWFE vs CS comparison</h3>
        <p className="text-[13px] text-gray-500 mb-5 leading-relaxed max-w-2xl">
          TWFE with staggered adoption can use already-treated units as controls, producing
          negative implicit weights and biased estimates. The gap between TWFE and CS diagnoses
          the extent of heterogeneous-treatment-effects bias.
        </p>
        <div className="grid grid-cols-2 gap-6">
          <FigureSlot src="/data/binary/did_twfe_vs_cs_comparison.png"
            alt="TWFE vs CS comparison" label="TWFE vs CS overlay (binary)" />
          <FigureSlot src="/data/binary/did_cs_twfe_difference.png"
            alt="CS minus TWFE difference" label="CS − TWFE bias (binary)" />
        </div>
      </div>
    </div>
  )
}
