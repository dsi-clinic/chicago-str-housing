import FigureSlot from '@/components/FigureSlot'
import StatTable from '@/components/StatTable'
import { loadCohortStats } from '@/lib/data'

export default function AnalysisPage() {
  const cohorts = loadCohortStats('binary').slice(0, 10)
  const tableRows = cohorts.map(c => [
    c.first_prohibition_month,
    c.n_tracts.toLocaleString(),
    `${(c.share_of_treated_tracts * 100).toFixed(1)}%`,
    `$${c.mean_baseline_rent.toFixed(0)}`,
    `$${(c.mean_median_income / 1000).toFixed(0)}k`,
  ])

  return (
    <div>
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">Spatial & Descriptive Analysis</h2>
      <p className="text-[15px] text-gray-500 mb-10 max-w-2xl leading-relaxed">
        Geography of treatment, cohort composition, and pre-treatment rent dynamics.
      </p>

      <div className="grid grid-cols-3 gap-5 mb-10">
        <FigureSlot src="/data/binary/did_story_map.png"
          alt="STR prohibition status by tract" label="Treatment status map" />
        <FigureSlot src="/data/binary/did_spatial_sample_ever_treated.png"
          alt="Ever-treated tracts in sample" label="Ever-treated tracts" />
        <FigureSlot src="/data/binary/did_story_map_cohort.png"
          alt="Prohibition cohort by tract" label="Cohort map" />
      </div>

      <h3 className="text-[15px] font-bold mb-3">Prohibition Cohorts</h3>
      <StatTable
        className="mb-10"
        headers={['First Prohibition Month', 'Tracts', 'Share of Treated', 'Mean Baseline Rent', 'Mean Income']}
        rows={tableRows}
      />

      <div className="grid grid-cols-2 gap-6">
        <FigureSlot src="/data/binary/event_study_plot.png"
          alt="TWFE event study coefficients" label="TWFE event study" />
        <FigureSlot src="/data/binary/did_cohort_dynamics.png"
          alt="Cohort-specific dynamic treatment effects" label="Cohort dynamics" />
      </div>
    </div>
  )
}
