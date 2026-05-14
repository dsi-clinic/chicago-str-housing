import FigureSlot from '@/components/FigureSlot'
import StatTable from '@/components/StatTable'
import { loadParallelTrendsTest } from '@/lib/data'

/* ATT range from docs/DID_RESULTS_STORY.md (post-refactor) */
const FULL_PANEL_T = 56.0
const FULL_PANEL_B = 48.8
const MATCHED_T    = 14.7
const MATCHED_B    = 26.1

const CONCLUSIONS = [
  {
    number: '01',
    heading: 'The primary evidence points to a positive rent effect',
    body: 'Across both treatment definitions, the full-panel CS estimate is positive: +$56/mo (threshold) and +$49/mo (binary). This is the headline result — it uses the broadest comparison group and is robust to staggered timing and heterogeneous treatment effects.',
    color: 'border-maroon',
  },
  {
    number: '02',
    heading: 'Effect size is sensitive to the comparison group',
    body: 'When we restrict to trend-matched controls, the ATT shrinks substantially to +$15/mo (threshold) and +$26/mo (binary). This sensitivity means the size of the effect depends on how similar we require the comparison neighborhoods to be — not just whether the effect exists.',
    color: 'border-blue-500',
  },
  {
    number: '03',
    heading: 'Pre-existing trends complicate the interpretation',
    body: 'The residualized CS — which removes each tract\'s linear pre-ban rent trend — flips negative for both definitions. This reveals that treated tracts were already on steeper rent growth paths before the ban. Once those trajectories are accounted for, rents grew less than predicted. This is not a contradiction; it means the raw ATT partly reflects pre-existing gentrification dynamics.',
    color: 'border-amber-500',
  },
  {
    number: '04',
    heading: 'TWFE would have given a misleading answer',
    body: 'The classical TWFE regression produces estimates that differ substantially from CS, consistent with negative-weights bias from staggered adoption. Using TWFE alone would have misstated both the sign and magnitude. The CS estimator was necessary here.',
    color: 'border-gray-300',
  },
  {
    number: '05',
    heading: 'Parallel trends is plausible but not proven',
    body: 'The formal regression test does not reject parallel trends (binary p=0.20, threshold p=0.35). However, the event studies show non-trivial pre-period deviations. Results should be accompanied by sensitivity language — the analysis is suggestive, not conclusive.',
    color: 'border-gray-300',
  },
  {
    number: '06',
    heading: 'Policy implication: effect exists, but heterogeneous',
    body: 'The 2016 prohibition wave (the largest) drives most of the aggregate ATT. Early-cohort neighborhoods were higher-rent, higher-income areas. Policymakers should not assume uniform affordability gains from blanket prohibition — the effect likely concentrates in already-expensive neighborhoods.',
    color: 'border-gray-300',
  },
]

export default function PolicyPage() {
  const ptB = loadParallelTrendsTest('binary')
  const ptT = loadParallelTrendsTest('threshold')

  const SENSITIVITY_TABLE = [
    ['Full-panel CS',         `+$${FULL_PANEL_T}`,  `+$${FULL_PANEL_B}`,  'Primary — broadest comparison group'],
    ['Matched-sample CS',     `+$${MATCHED_T}`,     `+$${MATCHED_B}`,     'Robustness — trend-matched controls'],
    ['Residualized CS',       '−$90',               '−$71',               'Trend-deviation only — not comparable†'],
  ]

  return (
    <div>
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">Policy Conclusions</h2>
      <p className="text-[15px] text-gray-500 mb-6 max-w-2xl leading-relaxed">
        What the analysis says, how confident we should be, and what it means for housing policy.
        Presented with the sensitivity range — because the effect size depends on design choices.
      </p>

      {/* ── Headline result with honest range ── */}
      <div className="border-l-4 border-maroon bg-maroon/5 rounded-r-xl px-6 py-5 mb-6">
        <p className="text-[10px] font-bold uppercase tracking-widest text-maroon mb-2">Headline finding</p>
        <p className="text-[15px] text-gray-700 leading-relaxed">
          STR prohibitions in Chicago are associated with a <strong className="text-maroon">positive
          effect on monthly rents</strong> in prohibited tracts — ranging from{' '}
          <strong>+${MATCHED_T}–${FULL_PANEL_T}/month</strong> (threshold) and{' '}
          <strong>+${MATCHED_B}–${FULL_PANEL_B}/month</strong> (binary), depending on
          the comparison group. The full-panel estimate is the primary result; the lower bound
          comes from the most conservative matched-sample design.
        </p>
      </div>

      {/* ── Recommended sensitivity framing ── */}
      <div className="bg-gray-50 border border-gray-100 rounded-xl px-6 py-5 mb-10">
        <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-3">Recommended sensitivity framing (from DID_RESULTS_STORY.md)</p>
        <p className="text-[13px] text-gray-700 leading-relaxed italic mb-4">
          &ldquo;Our primary specification uses the full tract-month rent panel and a
          Callaway-Sant&apos;Anna staggered DiD estimator. Across both treatment definitions,
          the baseline full-panel estimates are positive. Restricting the analysis to matched
          treated and control tracts reduces the size of the estimated effect but does not
          reverse its sign. A more demanding residualized specification yields negative
          residualized effects, indicating that treated tracts differ meaningfully from
          controls in observable characteristics and baseline trend structure. We interpret the
          full-panel CS estimates as the primary results and the matched and residualized
          specifications as robustness checks.&rdquo;
        </p>
        <p className="text-[12px] text-gray-500">
          Parallel trends: formal test does not reject (binary p={ptB.p_value.toFixed(2)},
          threshold p={ptT.p_value.toFixed(2)}), but event studies show non-trivial
          pre-period deviations. Results should be presented with this caveat.
        </p>
      </div>

      {/* ── Sensitivity table ── */}
      <h3 className="text-lg font-bold mb-1">Effect size range by specification</h3>
      <p className="text-[13px] text-gray-500 mb-4 max-w-2xl">
        The table below summarises the ATT estimate under each specification. Read the range
        as the honest uncertainty around the headline number — not as contradictory results.
      </p>
      <StatTable
        className="mb-10"
        headers={['Specification', 'Threshold ATT ($/mo)', 'Binary ATT ($/mo)', 'Role & notes']}
        rows={SENSITIVITY_TABLE}
      />

      {/* ── Conclusion cards ── */}
      <div className="grid grid-cols-2 gap-5 mb-10">
        {CONCLUSIONS.map(c => (
          <div key={c.number} className={`border-l-4 ${c.color} border border-gray-100 rounded-xl p-5`}>
            <span className="text-3xl font-extrabold text-gray-100 leading-none block mb-2">{c.number}</span>
            <h3 className="text-[14px] font-bold text-gray-800 mb-2 leading-snug">{c.heading}</h3>
            <p className="text-[12px] text-gray-500 leading-relaxed">{c.body}</p>
          </div>
        ))}
      </div>

      {/* ── Cohort explainer ── */}
      <FigureSlot
        src="/data/binary/cohort_dynamics_explainer.png"
        alt="Cohort dynamics explainer"
        label="Cohort-level ATT — effect varies by when the prohibition arrived"
        className="mb-8"
      />

      {/* ── Limitations & next steps ── */}
      <div className="border border-dashed border-gray-200 rounded-xl p-6">
        <h3 className="text-[13px] font-bold text-gray-700 mb-4">Limitations &amp; recommended next steps</h3>
        <div className="grid grid-cols-2 gap-6">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">Current limitations</p>
            <ul className="space-y-2 text-[12px] text-gray-500 leading-relaxed list-disc list-inside">
              <li>ZORI from ZIP codes — tract rents are interpolated, not measured directly.</li>
              <li>Threshold definition sensitive to ACS occupied-unit denominator.</li>
              <li>Matching still shows non-trivial SMD after refactor; controls can be reused heavily.</li>
              <li>Pre-period event study deviations are non-trivial in the raw CS designs.</li>
              <li>SUTVA partially tested but not fully ruled out (see Pre-trends tab).</li>
            </ul>
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">Recommended next steps</p>
            <ul className="space-y-2 text-[12px] text-gray-500 leading-relaxed list-disc list-inside">
              <li>Add caliper to matching to exclude poor-quality matches.</li>
              <li>Use richer pre-treatment outcome histories (not just slope + mean).</li>
              <li>Add geographic or submarket restrictions to limit reuse.</li>
              <li>Explore Synthetic DiD for a placebo-style robustness layer.</li>
              <li>Strengthen sensitivity language around parallel trends in final paper.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
