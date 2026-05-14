import FigureSlot from '@/components/FigureSlot'
import StatTable from '@/components/StatTable'
import { loadCohortStats, loadCovariateBalance } from '@/lib/data'

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

  const cohortRows = cohorts.map(c => [
    c.first_prohibition_month,
    c.n_tracts.toLocaleString(),
    `${(c.share_of_treated_tracts * 100).toFixed(1)}%`,
    `$${c.mean_baseline_rent.toFixed(0)}`,
    `$${(c.mean_median_income / 1000).toFixed(0)}k`,
  ])

  const balanceRows = balance.map(b => [
    COVARIATE_LABELS[b.covariate],
    `$${b.treated_mean.toFixed(0)}`,
    `$${b.control_mean.toFixed(0)}`,
    `${b.pct_diff.toFixed(1)}%`,
    b.cohens_d.toFixed(2),
    b.significant ? '✗ Yes' : '✓ No',
  ])

  return (
    <div>
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">Descriptive Analysis</h2>
      <p className="text-[15px] text-gray-500 mb-10 max-w-2xl leading-relaxed">
        Pre-treatment covariate balance, cohort composition, and treatment effect estimates.
      </p>

      {/* ── Covariate balance ── */}
      <h3 className="text-lg font-bold mb-1">Pre-treatment Covariate Balance</h3>
      <p className="text-[14px] text-gray-500 mb-4 max-w-2xl leading-relaxed">
        All seven covariates are significantly imbalanced before matching. Treated tracts
        are higher-income, higher-education, and higher-rent. The education gap is the
        largest (Cohen&apos;s d ≈ 1.08). This pattern motivates matching as a design-stage
        restriction, though it does not fully eliminate selection concerns.
      </p>

      <div className="border-l-4 border-teal-600 bg-teal-50/50 rounded-r-xl px-5 py-4 mb-4 max-w-2xl">
        <p className="text-[13px] text-gray-700 leading-relaxed">
          The Love-style figure below uses the <strong>post-refactor</strong> matcher (standardized{' '}
          <code className="text-xs bg-white/80 px-1 rounded">pre_trend_slope</code> +{' '}
          <code className="text-xs bg-white/80 px-1 rounded">avg_pre_rent</code>, <em>k</em>-NN).{' '}
          <strong>Before</strong> = treated vs all never-treated tracts in the pre-trend pool;{' '}
          <strong>after</strong> = treated vs matched controls only. It is not the residualized
          Callaway–Sant&apos;Anna-with-controls step (see Methodology Audit for the full explainer).
        </p>
      </div>

      <FigureSlot
        src="/data/binary/did_story_matching_love.png"
        alt="Love plot: standardized mean differences before and after matching"
        label="Love plot — SMD before vs after matching (post-refactor matching)"
        className="mb-6"
      />

      <StatTable
        className="mb-10"
        headers={['Covariate', 'Treated Mean', 'Control Mean', '% Diff', "Cohen's d", 'Significant']}
        rows={balanceRows}
      />

      {/* ── Cohort composition ── */}
      <h3 className="text-lg font-bold mb-1">Prohibition Cohorts</h3>
      <p className="text-[14px] text-gray-500 mb-4 max-w-2xl leading-relaxed">
        The 2016 cohort dominates. Early cohorts (Jul–Aug 2016) are notably
        higher-rent and higher-income than later cohorts, which trend toward
        lower-income neighborhoods.
      </p>
      <StatTable
        className="mb-10"
        headers={['First Prohibition Month', 'Tracts', 'Share of Treated', 'Mean Baseline Rent', 'Mean Income']}
        rows={cohortRows}
      />

      {/* ── Event study + cohort dynamics ── */}
      <h3 className="text-lg font-bold mb-4">Treatment Effect Estimates</h3>
      <div className="grid grid-cols-2 gap-6">
        <FigureSlot src="/data/binary/event_study_plot.png"
          alt="TWFE event study coefficients" label="TWFE event study" />
        <FigureSlot src="/data/binary/did_cohort_dynamics.png"
          alt="Cohort-specific dynamic treatment effects" label="Cohort dynamics (CS)" />
      </div>
    </div>
  )
}
