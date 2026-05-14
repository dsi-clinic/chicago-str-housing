import PipelineStepper from '@/components/PipelineStepper'
import FigureSlot from '@/components/FigureSlot'
import { loadPanelOverview, loadGroupStats } from '@/lib/data'

export default function DescriptivePage() {
  const ov      = loadPanelOverview('binary')
  const gs      = loadGroupStats('binary')
  const treated = gs.find(g => g.group.includes('Eventually')) ?? { n_tracts: 373 }
  const control = gs.find(g => g.group.includes('Never'))     ?? { n_tracts: 114 }

  return (
    <div>
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">Sample Construction Pipeline</h2>
      <p className="text-[15px] text-gray-500 mb-10 max-w-2xl leading-relaxed">
        From 1,332 raw Chicago census tracts to the final matched DiD sample —
        click any step to see what changed, how many units were retained, and why.
      </p>

      <PipelineStepper
        nTracts={ov.n_tracts}
        nTreated={treated.n_tracts}
        nControl={control.n_tracts}
      />

      <div className="grid grid-cols-2 gap-6 mt-10">
        <FigureSlot src="/data/binary/did_adoption_curve.png"
          alt="Cumulative prohibition adoption over time" label="Adoption curve" />
        <FigureSlot src="/data/binary/did_parallel_trends.png"
          alt="Average rent trends treated vs control" label="Pre-treatment rent trends" />
      </div>
      <div className="mt-6">
        <FigureSlot src="/data/binary/data_funnel.png"
          alt="Tract count funnel across pipeline stages" label="Sample construction funnel" />
      </div>
    </div>
  )
}
