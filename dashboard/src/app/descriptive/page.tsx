import PipelineStepper from '@/components/PipelineStepper'
import FigureSlot from '@/components/FigureSlot'
import InfoBlock from '@/components/InfoBlock'
import StatTable from '@/components/StatTable'
import { loadSampleLineage, loadGroupStats, loadCohortStats } from '@/lib/data'

export default function DescriptivePage() {
  // Use sample lineage (not panel overview) so numbers reflect the full pipeline audit
  const linB = loadSampleLineage('binary')
  const linT = loadSampleLineage('threshold')

  const stageC   = linB.find(s => s.stage_code === 'C')
  const stageDbin = linB.find(s => s.stage_code === 'D')
  const stageFbin = linB.find(s => s.stage_code === 'F')
  const stageDthr = linT.find(s => s.stage_code === 'D')
  const stageFthr = linT.find(s => s.stage_code === 'F')

  const nPanel   = stageC?.n_tracts   ?? 842
  const nMonths  = stageC?.n_months   ?? 128

  const nTreatedBin = stageDbin?.treated       ?? 373
  const nPoolBin    = stageDbin?.never_treated ?? 469
  const nMatchedBin = stageFbin?.n_tracts      ?? 556
  const nControlBin = nMatchedBin - nTreatedBin

  const nTreatedThr = stageDthr?.treated       ?? 274
  const nPoolThr    = stageDthr?.never_treated ?? 568
  const nMatchedThr = stageFthr?.n_tracts      ?? 453
  const nControlThr = nMatchedThr - nTreatedThr

  // Group stats for rent balance (from matched binary sample)
  const gs       = loadGroupStats('binary')
  const gsT      = loadGroupStats('threshold')
  const treated  = gs.find(g => g.group.includes('Eventually'))  ?? { n_tracts: nTreatedBin, mean_rent: 0, std_dev: 0 }
  const control  = gs.find(g => g.group.includes('Never'))       ?? { n_tracts: nControlBin,  mean_rent: 0, std_dev: 0 }
  const treatedT = gsT.find(g => g.group.includes('Eventually')) ?? { n_tracts: nTreatedThr, mean_rent: 0, std_dev: 0 }
  const controlT = gsT.find(g => g.group.includes('Never'))      ?? { n_tracts: nControlThr,  mean_rent: 0, std_dev: 0 }

  const cohorts = loadCohortStats('binary').slice(0, 8)
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
        nPanel={nPanel}
        nMonths={nMonths}
        nTreatedBin={nTreatedBin}
        nPoolBin={nPoolBin}
        nMatchedBin={nMatchedBin}
        nControlBin={nControlBin}
        nTreatedThr={nTreatedThr}
        nPoolThr={nPoolThr}
        nMatchedThr={nMatchedThr}
        nControlThr={nControlThr}
      />

      {/* ── Sample funnel ── */}
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
        The threshold indicator is stricter — fewer treated tracts, higher average rents.
      </p>

      <div className="grid grid-cols-2 gap-5 mb-6">
        <InfoBlock
          title="Binary indicator"
          rows={[
            { label: 'Treated (pre-match)',       value: nTreatedBin.toLocaleString(),  valueClass: 'text-maroon' },
            { label: 'Control pool (pre-match)',  value: nPoolBin.toLocaleString() },
            { label: 'Matched sample',            value: nMatchedBin.toLocaleString(),  valueClass: 'text-blue-600' },
            { label: 'Mean rent · treated',       value: `$${treated.mean_rent.toFixed(0)} / mo` },
            { label: 'Mean rent · control',       value: `$${control.mean_rent.toFixed(0)} / mo` },
          ]}
        />
        <InfoBlock
          title="Threshold indicator"
          rows={[
            { label: 'Treated (pre-match)',       value: nTreatedThr.toLocaleString(),  valueClass: 'text-teal-600' },
            { label: 'Control pool (pre-match)',  value: nPoolThr.toLocaleString() },
            { label: 'Matched sample',            value: nMatchedThr.toLocaleString(),  valueClass: 'text-teal-600' },
            { label: 'Mean rent · treated',       value: `$${treatedT.mean_rent.toFixed(0)} / mo` },
            { label: 'Mean rent · control',       value: `$${controlT.mean_rent.toFixed(0)} / mo` },
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
        The 2016 cohort accounts for the majority of treated tracts.
        Early adopters tend to be higher-rent, higher-income neighborhoods.
      </p>

      <FigureSlot
        src="/data/binary/did_story_cumulative_adoption.png"
        alt="Cumulative STR prohibition adoption"
        label="Cumulative treated-tract adoption over time (binary)"
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
        Treated tracts had persistently higher rents before 2016. The stable gap
        pre-treatment supports the parallel trends assumption.
      </p>
      <FigureSlot
        src="/data/binary/did_parallel_trends.png"
        alt="Average rent over time by group"
        label="Pre-treatment rent trends — treated vs never-treated"
      />
    </div>
  )
}
