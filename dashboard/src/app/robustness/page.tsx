import FigureSlot from '@/components/FigureSlot'
import InfoBlock from '@/components/InfoBlock'
import { loadPanelOverview, loadGroupStats } from '@/lib/data'

export default function RobustnessPage() {
  const ovB = loadPanelOverview('binary')
  const ovT = loadPanelOverview('threshold')
  const gsB = loadGroupStats('binary')
  const gsT = loadGroupStats('threshold')
  const treatedB = gsB.find(g => g.group.includes('Eventually')) ?? { n_tracts: 0, mean_rent: 0 }
  const treatedT = gsT.find(g => g.group.includes('Eventually')) ?? { n_tracts: 0, mean_rent: 0 }

  return (
    <div>
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">
        Robustness — Treatment Indicator Comparison
      </h2>
      <p className="text-[15px] text-gray-500 mb-10 max-w-2xl leading-relaxed">
        The treatment definition affects which tracts are labeled treated. Binary and threshold
        indicators are compared side-by-side across all key outputs.
      </p>

      <div className="grid grid-cols-2 gap-6 mb-10">
        <InfoBlock
          title="Binary Indicator"
          rows={[
            { label: 'Treated tracts',       value: ovB.tracts_eventually_treated.toLocaleString(), valueClass: 'text-blue-600' },
            { label: 'Never-treated tracts', value: ovB.tracts_never_treated.toLocaleString() },
            { label: 'Mean rent (treated)',  value: `$${treatedB.mean_rent.toFixed(0)}` },
          ]}
        />
        <InfoBlock
          title="Threshold Indicator"
          rows={[
            { label: 'Treated tracts',       value: ovT.tracts_eventually_treated.toLocaleString(), valueClass: 'text-teal-600' },
            { label: 'Never-treated tracts', value: ovT.tracts_never_treated.toLocaleString() },
            { label: 'Mean rent (treated)',  value: `$${treatedT.mean_rent.toFixed(0)}` },
          ]}
        />
      </div>

      <h3 className="text-[15px] font-bold mb-4">CS Event Study — Binary vs Threshold</h3>
      <div className="grid grid-cols-2 gap-6 mb-8">
        <FigureSlot src="/data/binary/did_callaway_santanna_event_study.png"
          alt="CS event study binary" label="Binary indicator" />
        <FigureSlot src="/data/threshold/did_callaway_santanna_event_study.png"
          alt="CS event study threshold" label="Threshold indicator" />
      </div>

      <h3 className="text-[15px] font-bold mb-4">Cohort Dynamics — Binary vs Threshold</h3>
      <div className="grid grid-cols-2 gap-6 mb-8">
        <FigureSlot src="/data/binary/did_cohort_dynamics.png"
          alt="Cohort dynamics binary" label="Binary indicator" />
        <FigureSlot src="/data/threshold/did_cohort_dynamics.png"
          alt="Cohort dynamics threshold" label="Threshold indicator" />
      </div>

      <h3 className="text-[15px] font-bold mb-4">TWFE vs CS — Binary vs Threshold</h3>
      <div className="grid grid-cols-2 gap-6">
        <FigureSlot src="/data/binary/did_twfe_vs_cs_comparison.png"
          alt="TWFE vs CS binary" label="Binary indicator" />
        <FigureSlot src="/data/threshold/did_twfe_vs_cs_comparison.png"
          alt="TWFE vs CS threshold" label="Threshold indicator" />
      </div>
    </div>
  )
}
