import FigureSlot from '@/components/FigureSlot'
import InfoBlock from '@/components/InfoBlock'
import StatTable from '@/components/StatTable'
import CohortBarChart from '@/components/CohortBarChart'
import { loadCohortStats, loadCovariateBalance,
         loadParallelTrendsTest, loadHonestPretrends } from '@/lib/data'

const COVARIATE_LABELS: Record<string, string> = {
  median_income:      'Median income',
  median_house_value: 'Median house value',
  baseline_rent:      'Baseline rent (ZORI)',
  pct_bachelor:       '% bachelor degree',
  pct_rented:         '% renter-occupied',
  median_age:         'Median age',
  total_population:   'Total population',
}

export default function AnalysisPage() {
  const cohorts = loadCohortStats('binary').slice(0, 10)
  const balance = loadCovariateBalance('binary')
    .filter(b => b.covariate in COVARIATE_LABELS)
    .sort((a, b) => b.cohens_d - a.cohens_d)
  const ptB = loadParallelTrendsTest('binary')
  const ptT = loadParallelTrendsTest('threshold')
  const hpB = loadHonestPretrends('binary')
  const hpT = loadHonestPretrends('threshold')

  const cohortRows = cohorts.map(c => [
    c.first_prohibition_month,
    c.n_tracts.toLocaleString(),
    `${(c.share_of_treated_tracts * 100).toFixed(1)}%`,
    `$${c.mean_baseline_rent.toFixed(0)}`,
    `$${(c.mean_median_income / 1000).toFixed(0)}k`,
  ])

  const balanceRows = balance.map(b => [
    COVARIATE_LABELS[b.covariate] ?? b.covariate,
    `$${b.treated_mean.toFixed(0)}`,
    `$${b.control_mean.toFixed(0)}`,
    `${b.pct_diff.toFixed(1)}%`,
    b.cohens_d.toFixed(2),
    b.significant ? '✗ Yes' : '✓ No',
  ])

  return (
    <div>
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">Analysis</h2>
      <p className="text-[15px] text-gray-500 mb-10 max-w-2xl leading-relaxed">
        When did prohibitions arrive, how similar are treated and control neighborhoods,
        and does the parallel trends assumption hold?
      </p>

      {/* ── 1. Cohort adoption timeline ── */}
      <h3 className="text-lg font-bold mb-1">When did prohibitions arrive?</h3>
      <p className="text-[13px] text-gray-500 mb-5 max-w-2xl leading-relaxed">
        Prohibitions rolled out in waves from mid-2016 onward. The July and August 2016
        cohorts account for the largest share under both definitions.
        Early cohorts tend to be higher-rent neighborhoods.
      </p>
      <div className="grid grid-cols-2 gap-5 mb-6">
        <div className="border border-gray-100 rounded-xl p-5">
          <p className="text-[11px] font-bold uppercase tracking-wider text-maroon mb-3">Binary</p>
          <CohortBarChart dir="binary" />
        </div>
        <div className="border border-gray-100 rounded-xl p-5">
          <p className="text-[11px] font-bold uppercase tracking-wider text-teal-600 mb-3">Threshold</p>
          <CohortBarChart dir="threshold" />
        </div>
      </div>
      <StatTable
        className="mb-10"
        headers={['First Prohibition Month', 'Tracts', 'Share of Treated', 'Mean Baseline Rent', 'Mean Income']}
        rows={cohortRows}
      />

      {/* ── 3. Pre-treatment comparability ── */}
      <h3 className="text-lg font-bold mb-1">Are treated and control tracts comparable?</h3>
      <p className="text-[13px] text-gray-500 mb-5 max-w-2xl leading-relaxed">
        On every measured covariate, treated tracts differ significantly from the
        never-treated pool before any ban. The education gap is largest (Cohen's d ≈ 1.08).
        This motivates the use of never-treated controls rather than a simple before-after
        comparison, and matching as a robustness check.
      </p>
      <StatTable
        className="mb-6"
        headers={['Covariate', 'Treated Mean', 'Control Mean', '% Diff', "Cohen's d", 'Imbalanced']}
        rows={balanceRows}
      />
      <FigureSlot
        src="/data/binary/did_story_pre_rent_violin.png"
        alt="Pre-treatment rent distribution"
        label="Pre-treatment rent distribution — never-treated vs ever-treated (binary, matched sample)"
        className="mb-10"
      />

      {/* ── 4. Parallel trends assumption ── */}
      <h3 className="text-lg font-bold mb-1">The identifying assumption: parallel trends</h3>
      <p className="text-[13px] text-gray-500 mb-5 max-w-2xl leading-relaxed">
        For a DiD estimate to be causal, treated and control neighborhoods must have moved
        in parallel before the ban. We cannot prove this, but we can test whether pre-ban
        rent trends already diverged.
      </p>

      <div className="grid grid-cols-2 gap-6 mb-4">
        <InfoBlock
          title="Formal regression test"
          rows={[
            { label: 'Binary p-value',      value: ptB.p_value.toFixed(3), valueClass: ptB.significant ? 'text-maroon' : 'text-teal-600' },
            { label: 'Threshold p-value',   value: ptT.p_value.toFixed(3), valueClass: ptT.significant ? 'text-maroon' : 'text-teal-600' },
            { label: 'Binary verdict',      value: ptB.significant ? 'Rejects at 5% ✗' : 'Does not reject ✓', valueClass: ptB.significant ? 'text-maroon' : 'text-teal-600' },
            { label: 'Threshold verdict',   value: ptT.significant ? 'Rejects at 5% ✗' : 'Does not reject ✓', valueClass: ptT.significant ? 'text-maroon' : 'text-teal-600' },
          ]}
        />
        <InfoBlock
          title="Pre-period TWFE coefficients"
          rows={[
            { label: 'Binary max |pre-coef|',    value: `$${hpB.max_abs_twfe_coef_pre.toFixed(1)} / mo` },
            { label: 'Threshold max |pre-coef|', value: `$${hpT.max_abs_twfe_coef_pre.toFixed(1)} / mo` },
            { label: 'Sign restriction violated', value: hpB.violates_sign_restriction ? 'Yes ✗' : 'No ✓', valueClass: hpB.violates_sign_restriction ? 'text-maroon' : 'text-teal-600' },
            { label: 'Pre-periods checked',       value: `${hpB.n_pre_periods}` },
          ]}
        />
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-teal-50 border border-teal-200/60 rounded-xl px-4 py-3 text-[12px] text-gray-700">
          <strong className="text-teal-700 block mb-1">Formal test does not reject.</strong>
          Neither binary (p={ptB.p_value.toFixed(2)}) nor threshold (p={ptT.p_value.toFixed(2)})
          shows a statistically significant pre-trend difference.
        </div>
        <div className="bg-amber-50 border border-amber-200/60 rounded-xl px-4 py-3 text-[12px] text-gray-700">
          <strong className="text-amber-700 block mb-1">Visual evidence is imperfect.</strong>
          Max pre-period coefficients (~${hpB.max_abs_twfe_coef_pre.toFixed(0)} binary, ${hpT.max_abs_twfe_coef_pre.toFixed(0)} threshold)
          are roughly half the full-panel ATT. Plausible — not proven.
        </div>
      </div>

      <FigureSlot
        src="/data/binary/did_parallel_trends.png"
        alt="Pre-treatment rent trends"
        label="Average rent — treated vs never-treated before the ban (binary, matched sample)"
      />
    </div>
  )
}
