import PipelineStepper from '@/components/PipelineStepper'
import FigureSlot from '@/components/FigureSlot'
import InfoBlock from '@/components/InfoBlock'
import StatTable from '@/components/StatTable'
import { loadPanelOverview, loadGroupStats, loadCohortStats } from '@/lib/data'

export default function DescriptivePage() {
  const ov       = loadPanelOverview('binary')
  const gs       = loadGroupStats('binary')
  const gsT      = loadGroupStats('threshold')
  const cohorts  = loadCohortStats('binary').slice(0, 8)
  const treated  = gs.find(g => g.group.includes('Eventually'))  ?? { n_tracts: 373, mean_rent: 0, std_dev: 0 }
  const control  = gs.find(g => g.group.includes('Never'))       ?? { n_tracts: 183, mean_rent: 0, std_dev: 0 }
  const treatedT = gsT.find(g => g.group.includes('Eventually')) ?? { n_tracts: 274, mean_rent: 0, std_dev: 0 }
  const controlT = gsT.find(g => g.group.includes('Never'))      ?? { n_tracts: 179, mean_rent: 0, std_dev: 0 }

  const cohortRows = cohorts.map(c => [
    c.first_prohibition_month,
    c.n_tracts.toLocaleString(),
    `${(c.share_of_treated_tracts * 100).toFixed(1)}%`,
    `$${c.mean_baseline_rent.toFixed(0)}`,
    `$${(c.mean_median_income / 1000).toFixed(0)}k`,
  ])

  return (
    <div>
      {/* ── Pipeline stepper ── */}
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">Sample Construction Pipeline</h2>
      <p className="text-[15px] text-gray-500 mb-10 max-w-2xl leading-relaxed">
        From 1,332 raw Chicago census tracts to the final matched DiD sample — click any step
        to see what changed, how many units were retained, and why.
      </p>

      <PipelineStepper
        nTracts={ov.n_tracts}
        nTreated={treated.n_tracts}
        nControl={control.n_tracts}
      />

      {/* ── Sample funnel figure ── */}
      <div className="mt-10 mb-10">
        <FigureSlot
          src="/data/binary/did_story_sample_lineage.png"
          alt="Sample construction funnel by pipeline stage"
          label="Sample funnel — how the tract count narrows at each stage"
        />
      </div>

      {/* ── Treatment group distributions ── */}
      <h3 className="text-lg font-bold mb-1">Treatment Group Distributions</h3>
      <p className="text-[14px] text-gray-500 mb-6 max-w-2xl leading-relaxed">
        Treated and never-treated tracts differ under each definition.
        The threshold indicator is stricter, selecting a smaller treated group that tends
        toward even higher baseline rents.
      </p>

      <div className="grid grid-cols-2 gap-5 mb-6">
        <InfoBlock
          title="Binary indicator"
          rows={[
            { label: 'Treated tracts',          value: treated.n_tracts.toLocaleString(),  valueClass: 'text-maroon' },
            { label: 'Never-treated tracts',    value: control.n_tracts.toLocaleString() },
            { label: 'Mean rent · treated',     value: `$${treated.mean_rent.toFixed(0)} / mo` },
            { label: 'Mean rent · control',     value: `$${control.mean_rent.toFixed(0)} / mo` },
          ]}
        />
        <InfoBlock
          title="Threshold indicator"
          rows={[
            { label: 'Treated tracts',          value: treatedT.n_tracts.toLocaleString(), valueClass: 'text-teal-600' },
            { label: 'Never-treated tracts',    value: controlT.n_tracts.toLocaleString() },
            { label: 'Mean rent · treated',     value: `$${treatedT.mean_rent.toFixed(0)} / mo` },
            { label: 'Mean rent · control',     value: `$${controlT.mean_rent.toFixed(0)} / mo` },
          ]}
        />
      </div>

      <FigureSlot
        src="/data/binary/did_story_pre_rent_violin.png"
        alt="Pre-treatment rent distribution by group"
        label="Pre-treatment rent distribution — never-treated vs ever-treated (matched sample)"
        className="mb-10"
      />

      {/* ── Cohort adoption ── */}
      <h3 className="text-lg font-bold mb-1">When Did Prohibitions Hit?</h3>
      <p className="text-[14px] text-gray-500 mb-6 max-w-2xl leading-relaxed">
        The 2016 cohort accounts for the majority of treated tracts. Early adopters
        tend to be higher-rent, higher-income neighborhoods.
      </p>

      <FigureSlot
        src="/data/binary/did_story_cumulative_adoption.png"
        alt="Cumulative STR prohibition adoption"
        label="Cumulative treated-tract adoption over time"
        className="mb-6"
      />

      <h4 className="text-[14px] font-bold mb-3 text-gray-700">Top 8 Prohibition Cohorts (Binary)</h4>
      <StatTable
        className="mb-10"
        headers={['First Prohibition Month', 'Tracts', 'Share of Treated', 'Mean Baseline Rent', 'Mean Income']}
        rows={cohortRows}
      />

      {/* ── Rent trends ── */}
      <h3 className="text-lg font-bold mb-1">Pre-treatment Rent Trajectories</h3>
      <p className="text-[14px] text-gray-500 mb-6 max-w-2xl leading-relaxed">
        Treated tracts had persistently higher rents before 2016. The gap is stable
        pre-treatment — a visual check that supports the parallel trends assumption.
      </p>
      <FigureSlot
        src="/data/binary/did_parallel_trends.png"
        alt="Average rent over time by group"
        label="Pre-treatment rent trends — treated vs never-treated"
      />
    </div>
  )
}
