import PipelineStepper from '@/components/PipelineStepper'
import FigureSlot from '@/components/FigureSlot'
import InfoBlock from '@/components/InfoBlock'
import { loadSampleLineage, loadGroupStats } from '@/lib/data'

export default function DataProcessingPage() {
  const linB = loadSampleLineage('binary')
  const linT = loadSampleLineage('threshold')

  const stageC    = linB.find(s => s.stage_code === 'C')
  const stageDbin = linB.find(s => s.stage_code === 'D')
  const stageFbin = linB.find(s => s.stage_code === 'F')
  const stageDthr = linT.find(s => s.stage_code === 'D')
  const stageFthr = linT.find(s => s.stage_code === 'F')

  const nPanel      = stageC?.n_tracts         ?? 842
  const nMonths     = stageC?.n_months          ?? 128
  const nTreatedBin = stageDbin?.treated        ?? 373
  const nPoolBin    = stageDbin?.never_treated  ?? 469
  const nMatchedBin = stageFbin?.n_tracts       ?? 556
  const nControlBin = nMatchedBin - nTreatedBin
  const nTreatedThr = stageDthr?.treated        ?? 274
  const nPoolThr    = stageDthr?.never_treated  ?? 568
  const nMatchedThr = stageFthr?.n_tracts       ?? 453
  const nControlThr = nMatchedThr - nTreatedThr

  const gs  = loadGroupStats('binary')
  const gsT = loadGroupStats('threshold')
  const treated  = gs.find(g => g.group.includes('Eventually'))  ?? { mean_rent: 0 }
  const control  = gs.find(g => g.group.includes('Never'))       ?? { mean_rent: 0 }
  const treatedT = gsT.find(g => g.group.includes('Eventually')) ?? { mean_rent: 0 }
  const controlT = gsT.find(g => g.group.includes('Never'))      ?? { mean_rent: 0 }

  return (
    <div>
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">Data Processing Pipeline</h2>
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

      <div className="mt-10 mb-10">
        <FigureSlot
          src="/data/binary/did_story_sample_lineage.png"
          alt="Sample construction funnel"
          label="Sample funnel — how the tract count narrows at each stage"
        />
      </div>

      <h3 className="text-lg font-bold mb-1">Treatment Group Distributions</h3>
      <p className="text-[14px] text-gray-500 mb-6 max-w-2xl leading-relaxed">
        Treated and never-treated tracts under each indicator. The threshold definition
        is stricter — fewer treated tracts, higher average rents.
      </p>
      <div className="grid grid-cols-2 gap-5">
        <InfoBlock
          title="Binary indicator"
          rows={[
            { label: 'Treated (pre-match)',      value: nTreatedBin.toLocaleString(), valueClass: 'text-maroon' },
            { label: 'Control pool (pre-match)', value: nPoolBin.toLocaleString() },
            { label: 'Matched sample',           value: nMatchedBin.toLocaleString(), valueClass: 'text-blue-600' },
            { label: 'Mean rent · treated',      value: `$${treated.mean_rent.toFixed(0)} / mo` },
            { label: 'Mean rent · control',      value: `$${control.mean_rent.toFixed(0)} / mo` },
          ]}
        />
        <InfoBlock
          title="Threshold indicator"
          rows={[
            { label: 'Treated (pre-match)',      value: nTreatedThr.toLocaleString(), valueClass: 'text-teal-600' },
            { label: 'Control pool (pre-match)', value: nPoolThr.toLocaleString() },
            { label: 'Matched sample',           value: nMatchedThr.toLocaleString(), valueClass: 'text-teal-600' },
            { label: 'Mean rent · treated',      value: `$${treatedT.mean_rent.toFixed(0)} / mo` },
            { label: 'Mean rent · control',      value: `$${controlT.mean_rent.toFixed(0)} / mo` },
          ]}
        />
      </div>
    </div>
  )
}
