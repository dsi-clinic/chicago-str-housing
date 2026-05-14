import FigureSlot from '@/components/FigureSlot'
import StatTable from '@/components/StatTable'
import { loadComparisonRows } from '@/lib/data'

const ESTIMATORS = [
  {
    accent: 'border-t-amber-400',
    title: 'TWFE (Two-Way Fixed Effects)',
    body: 'The classic panel estimator includes unit and time fixed effects. Under staggered adoption, already-treated units act as controls for later-treated units — contaminating estimates with heterogeneous treatment effects and potentially producing negative weights.',
  },
  {
    accent: 'border-t-maroon',
    title: "Callaway & Sant'Anna (2021)",
    body: 'CS estimates group-time ATT(g,t) for each (cohort, calendar-month) pair using only not-yet-treated or never-treated units as controls. Aggregates to an overall ATT with transparent, interpretable weights. Valid under parallel trends without assuming homogeneous effects.',
  },
  {
    accent: 'border-t-teal-500',
    title: 'CS with Covariates + Tract Trends',
    body: 'Extends CS by residualizing on ACS covariates (income, occupancy, education) and tract-specific linear pre-trends in the pre-treatment period only. Doubly-robust: consistent if either the propensity score or the outcome model is correctly specified.',
  },
]

export default function ModelsPage() {
  const rows = loadComparisonRows('binary').filter(r => r.rel_time >= -6 && r.rel_time <= 6)
  const tableRows = rows.map(r => [
    r.rel_time >= 0 ? `+${r.rel_time}` : `${r.rel_time}`,
    r.cs_att.toFixed(2),
    r.cs_se.toFixed(2),
    r.twfe_coef.toFixed(2),
    r.twfe_se.toFixed(2),
    (r.cs_att - r.twfe_coef).toFixed(2),
  ])

  return (
    <div>
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">Estimators & Models</h2>
      <p className="text-[15px] text-gray-500 mb-10 max-w-2xl leading-relaxed">
        Why TWFE is insufficient for staggered adoption, and how Callaway &amp; Sant&apos;Anna addresses it.
      </p>

      <div className="grid grid-cols-3 gap-5 mb-10">
        {ESTIMATORS.map(e => (
          <div key={e.title} className={`border-t-[3px] ${e.accent} border border-gray-100 rounded-xl p-6`}>
            <h3 className="text-[13px] font-bold text-gray-800 mb-3">{e.title}</h3>
            <p className="text-[13px] text-gray-500 leading-relaxed">{e.body}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6 mb-8">
        <FigureSlot src="/data/binary/did_callaway_santanna_event_study.png"
          alt="CS event study" label="CS baseline event study" />
        <FigureSlot src="/data/binary/did_callaway_santanna_event_study_with_controls.png"
          alt="CS with covariates and tract trends" label="CS with controls + tract trends" />
      </div>

      <div className="grid grid-cols-2 gap-6 mb-8">
        <FigureSlot src="/data/binary/did_twfe_vs_cs_comparison.png"
          alt="TWFE vs CS event study overlay" label="TWFE vs CS overlay" />
        <FigureSlot src="/data/binary/did_cs_twfe_difference.png"
          alt="CS minus TWFE difference" label="CS − TWFE difference (bias)" />
      </div>

      <FigureSlot src="/data/binary/did_cohort_dynamics_with_controls.png"
        alt="Cohort dynamics with controls" label="Cohort dynamics (CS with controls)" className="mb-8" />

      <h3 className="text-[15px] font-bold mb-3">ATT Estimates: CS vs TWFE by Relative Time</h3>
      <StatTable
        headers={['Rel. Time', 'CS ATT', 'CS SE', 'TWFE Coef', 'TWFE SE', 'Difference']}
        rows={tableRows}
      />
    </div>
  )
}
