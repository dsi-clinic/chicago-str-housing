import FigureSlot from '@/components/FigureSlot'
import { loadComparisonRows, loadParallelTrendsTest } from '@/lib/data'

const CONCLUSIONS = [
  {
    number: '01',
    heading: 'STR prohibitions are associated with measurable rent changes',
    body: 'Our CS estimates show statistically detectable effects on monthly rents in prohibited tracts during the post-treatment window. The direction and magnitude vary by cohort, suggesting the effect is not homogeneous across the city.',
  },
  {
    number: '02',
    heading: 'TWFE substantially biases estimates under staggered adoption',
    body: "The difference between TWFE and CS estimates is non-trivial, consistent with the heterogeneous-treatment-effects bias documented by Callaway & Sant'Anna (2021). Relying on TWFE alone would misstate both the sign and size of policy effects.",
  },
  {
    number: '03',
    heading: 'Parallel pre-trends are plausible',
    body: 'Formal regression tests and visual inspection of pre-period rent trajectories support the parallel trends assumption for our matched sample. The honest pre-trends analysis confirms pre-period coefficients are small in magnitude.',
  },
  {
    number: '04',
    heading: 'Policy implications for housing regulation',
    body: 'The evidence suggests STR restrictions affect the local rental market. Policymakers should consider the heterogeneous impact across cohorts — early vs late adopting neighborhoods — before assuming uniform affordability gains from blanket prohibition.',
  },
]

export default function PolicyPage() {
  const rows = loadComparisonRows('binary').filter(r => r.rel_time >= 0)
  const pt   = loadParallelTrendsTest('binary')
  const avgPostATT = rows.length
    ? (rows.reduce((s, r) => s + r.cs_att, 0) / rows.length).toFixed(2)
    : '—'

  return (
    <div>
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">Policy Conclusions</h2>
      <p className="text-[15px] text-gray-500 mb-10 max-w-2xl leading-relaxed">
        What the evidence says, its limits, and what it means for housing policy in Chicago.
      </p>

      <div className="border-l-4 border-maroon bg-maroon/5 rounded-r-xl px-6 py-5 mb-10">
        <p className="text-[10px] font-bold uppercase tracking-widest text-maroon mb-2">Key Estimate</p>
        <p className="text-[15px] text-gray-700 leading-relaxed">
          Average post-treatment CS ATT across all post-treatment periods:{' '}
          <strong className="text-maroon">${avgPostATT} / month</strong> (binary indicator).
          Parallel trends test p-value: <strong>{pt.p_value.toFixed(4)}</strong> —
          {pt.significant ? ' significant pre-trend detected (see Pre-trends tab).' : ' no significant pre-trend.'}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-5 mb-10">
        {CONCLUSIONS.map(c => (
          <div key={c.number} className="border border-gray-100 rounded-xl p-6">
            <span className="text-4xl font-extrabold text-gray-100 leading-none block mb-3">{c.number}</span>
            <h3 className="text-[14px] font-bold text-gray-800 mb-2 leading-snug">{c.heading}</h3>
            <p className="text-[13px] text-gray-500 leading-relaxed">{c.body}</p>
          </div>
        ))}
      </div>

      <FigureSlot
        src="/data/binary/cohort_dynamics_explainer.png"
        alt="Cohort dynamics explainer"
        label="Cohort dynamics — ATT by prohibition wave"
        className="mb-8"
      />

      <div className="border border-dashed border-gray-200 rounded-xl p-6">
        <h3 className="text-[13px] font-bold text-gray-700 mb-3">Limitations &amp; Next Steps</h3>
        <ul className="space-y-2 text-[13px] text-gray-500 leading-relaxed list-disc list-inside">
          <li>ZORI interpolation from ZIP codes introduces measurement error in the rent variable.</li>
          <li>The threshold indicator&apos;s exact value is sensitive to the ACS occupied-unit denominator.</li>
          <li>SUTVA may be violated if STR supply shifts across tract boundaries (tested in Pre-trends tab).</li>
          <li>Possible extensions: Synthetic DiD, double ML, synthetic control for placebo validation.</li>
        </ul>
      </div>
    </div>
  )
}
