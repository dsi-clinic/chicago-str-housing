import FigureSlot from '@/components/FigureSlot'
import InfoBlock from '@/components/InfoBlock'
import StatTable from '@/components/StatTable'
import CohortBarChart from '@/components/CohortBarChart'
import { loadSampleLineage, loadGroupStats, loadCohortStats, loadCovariateBalance } from '@/lib/data'

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
  const linB = loadSampleLineage('binary')
  const linT = loadSampleLineage('threshold')
  const gsB  = loadGroupStats('binary')
  const gsT  = loadGroupStats('threshold')
  const cohorts = loadCohortStats('binary').slice(0, 10)
  const balance = loadCovariateBalance('binary')
    .filter(b => b.covariate in COVARIATE_LABELS)
    .sort((a, b) => b.cohens_d - a.cohens_d)

  const stageDbin = linB.find(s => s.stage_code === 'D')
  const stageFbin = linB.find(s => s.stage_code === 'F')
  const stageDthr = linT.find(s => s.stage_code === 'D')
  const stageFthr = linT.find(s => s.stage_code === 'F')

  const treatedB = gsB.find(g => g.group.includes('Eventually')) ?? { mean_rent: 0, std_dev: 0 }
  const controlB = gsB.find(g => g.group.includes('Never'))      ?? { mean_rent: 0, std_dev: 0 }
  const treatedT = gsT.find(g => g.group.includes('Eventually')) ?? { mean_rent: 0, std_dev: 0 }
  const controlT = gsT.find(g => g.group.includes('Never'))      ?? { mean_rent: 0, std_dev: 0 }

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
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">Treatment Characterization</h2>
      <p className="text-[15px] text-gray-500 mb-10 max-w-2xl leading-relaxed">
        Who got treated, when, and how the two treatment definitions differ — before asking
        whether the effect is causal.
      </p>

      {/* ── 1. Treatment counts by indicator ── */}
      <h3 className="text-lg font-bold mb-1">Treatment counts by indicator</h3>
      <p className="text-[13px] text-gray-500 mb-5 max-w-2xl leading-relaxed">
        The binary indicator counts any prohibition in a tract. The threshold indicator
        requires the share of prohibited units to cross a minimum. The two definitions
        agree on never-treated tracts but disagree on which tracts cross the threshold.
      </p>
      <div className="grid grid-cols-2 gap-6 mb-10">
        <InfoBlock
          title="Binary indicator"
          rows={[
            { label: 'Treated tracts (pre-match)',       value: (stageDbin?.treated ?? 373).toLocaleString(),        valueClass: 'text-maroon' },
            { label: 'Never-treated pool',               value: (stageDbin?.never_treated ?? 469).toLocaleString() },
            { label: 'Matched analysis sample',          value: (stageFbin?.n_tracts ?? 556).toLocaleString(),       valueClass: 'text-blue-600' },
            { label: 'Mean rent · treated (matched)',    value: `$${treatedB.mean_rent.toFixed(0)} / mo` },
            { label: 'Mean rent · controls (matched)',   value: `$${controlB.mean_rent.toFixed(0)} / mo` },
          ]}
        />
        <InfoBlock
          title="Threshold indicator"
          rows={[
            { label: 'Treated tracts (pre-match)',       value: (stageDthr?.treated ?? 274).toLocaleString(),        valueClass: 'text-teal-600' },
            { label: 'Never-treated pool',               value: (stageDthr?.never_treated ?? 568).toLocaleString() },
            { label: 'Matched analysis sample',          value: (stageFthr?.n_tracts ?? 453).toLocaleString(),       valueClass: 'text-teal-600' },
            { label: 'Mean rent · treated (matched)',    value: `$${treatedT.mean_rent.toFixed(0)} / mo` },
            { label: 'Mean rent · controls (matched)',   value: `$${controlT.mean_rent.toFixed(0)} / mo` },
          ]}
        />
      </div>

      {/* ── 2. When did prohibitions arrive? ── */}
      <h3 className="text-lg font-bold mb-1">When did prohibitions arrive?</h3>
      <p className="text-[13px] text-gray-500 mb-5 max-w-2xl leading-relaxed">
        Prohibitions rolled out in waves from mid-2016 onward. The July and August 2016
        cohorts account for the largest share of treated tracts under both definitions.
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

      {/* ── 3. Pre-treatment rent distributions ── */}
      <h3 className="text-lg font-bold mb-1">Pre-treatment rent distributions</h3>
      <p className="text-[13px] text-gray-500 mb-5 max-w-2xl leading-relaxed">
        Even before any prohibition, treated tracts had substantially higher rents than
        never-treated ones. This level gap is one reason the comparison is difficult and
        motivates the use of CS rather than a simple before-after design.
      </p>
      <FigureSlot
        src="/data/binary/did_story_pre_rent_violin.png"
        alt="Pre-treatment rent distribution by group"
        label="Pre-treatment rent — never-treated vs ever-treated (binary, matched sample)"
        className="mb-10"
      />

      {/* ── 4. Are treated and control tracts comparable? ── */}
      <h3 className="text-lg font-bold mb-1">Are treated and control tracts comparable?</h3>
      <p className="text-[13px] text-gray-500 mb-5 max-w-2xl leading-relaxed">
        On every measured covariate, treated tracts are significantly different from the
        never-treated pool before any matching. The education gap is the largest
        (Cohen's d ≈ 1.08). This does not disqualify a causal estimate, but it means the
        comparison group choice matters — and the full-panel CS result should be accompanied
        by sensitivity checks on the comparison group (see Robustness tab).
      </p>

      <FigureSlot
        src="/data/binary/did_story_matching_love.png"
        alt="SMD before and after matching on pre-trend features"
        label="Pre-treatment balance — SMD before matching (grey) and after k-NN matching (maroon)"
        className="mb-6"
      />

      <StatTable
        className="mb-0"
        headers={['Covariate', 'Treated Mean', 'Control Mean', '% Diff', "Cohen's d", 'Imbalanced']}
        rows={balanceRows}
      />
    </div>
  )
}
