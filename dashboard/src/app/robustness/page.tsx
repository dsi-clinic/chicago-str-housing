import FigureSlot from '@/components/FigureSlot'
import InfoBlock from '@/components/InfoBlock'
import StatTable from '@/components/StatTable'
import { loadSampleLineage, loadGroupStats } from '@/lib/data'

/* ATT values from docs/DID_RESULTS_STORY.md (post-refactor run) */
const ATT_COMPARISON = [
  ['Full-panel CS (primary)',   '+56.0', '(0.45)', '+48.8', '(0.53)'],
  ['Matched-sample CS',        '+14.7', '(0.49)', '+26.1', '(0.62)'],
  ['Residualized CS (matched)', '−89.6', '(0.54)', '−70.8', '(0.61)'],
]

export default function RobustnessPage() {
  // Use sample lineage for correct pre-match counts
  const linB = loadSampleLineage('binary')
  const linT = loadSampleLineage('threshold')
  const gsB  = loadGroupStats('binary')
  const gsT  = loadGroupStats('threshold')

  const stageDbin = linB.find(s => s.stage_code === 'D')
  const stageFbin = linB.find(s => s.stage_code === 'F')
  const stageDthr = linT.find(s => s.stage_code === 'D')
  const stageFthr = linT.find(s => s.stage_code === 'F')

  const treatedB = gsB.find(g => g.group.includes('Eventually')) ?? { mean_rent: 0 }
  const treatedT = gsT.find(g => g.group.includes('Eventually')) ?? { mean_rent: 0 }
  const controlB = gsB.find(g => g.group.includes('Never'))      ?? { mean_rent: 0 }
  const controlT = gsT.find(g => g.group.includes('Never'))      ?? { mean_rent: 0 }

  return (
    <div>
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">
        Robustness — Treatment Definition Sensitivity
      </h2>
      <p className="text-[15px] text-gray-500 mb-6 max-w-2xl leading-relaxed">
        Does the sign and direction of the effect survive when we change <em>which</em> tracts
        count as treated? Both definitions yield positive full-panel ATTs. This tab documents
        what changes — and what stays the same — across definitions.
      </p>

      {/* ── What robustness means here ── */}
      <div className="bg-gray-50 border border-gray-100 rounded-xl px-6 py-5 mb-10">
        <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-3">What this tab is testing</p>
        <div className="grid grid-cols-2 gap-6 text-[13px] text-gray-600 leading-relaxed">
          <div>
            <strong className="block mb-1">Binary indicator</strong>
            A tract counts as treated as soon as <em>any</em> STR prohibition takes effect —
            the broadest definition. More tracts are treated ({stageDbin?.treated?.toLocaleString() ?? 373}),
            smaller control pool ({stageDbin?.never_treated?.toLocaleString() ?? 469}).
          </div>
          <div>
            <strong className="block mb-1">Threshold indicator</strong>
            A tract counts as treated only when prohibited units cross a share threshold —
            stricter. Fewer treated tracts ({stageDthr?.treated?.toLocaleString() ?? 274}),
            larger control pool ({stageDthr?.never_treated?.toLocaleString() ?? 568}).
          </div>
        </div>
        <p className="text-[12px] text-gray-500 mt-4">
          <strong>Key question:</strong> Is the positive effect an artifact of how we define
          treatment, or does it hold under both definitions? Both should yield similar signs if
          the prohibition genuinely affects rents. If they diverge sharply, we need to understand why.
        </p>
      </div>

      {/* ── Sample comparison ── */}
      <h3 className="text-lg font-bold mb-3">Sample comparison (pre-match)</h3>
      <div className="grid grid-cols-2 gap-6 mb-10">
        <InfoBlock
          title="Binary indicator — pre-match sample"
          rows={[
            { label: 'Treated tracts (pre-match)',       value: (stageDbin?.treated ?? 373).toLocaleString(),        valueClass: 'text-maroon' },
            { label: 'Control pool (pre-match)',         value: (stageDbin?.never_treated ?? 469).toLocaleString() },
            { label: 'Matched analysis sample',          value: (stageFbin?.n_tracts ?? 556).toLocaleString(),       valueClass: 'text-blue-600' },
            { label: 'Mean rent · treated (matched)',    value: `$${treatedB.mean_rent.toFixed(0)} / mo` },
            { label: 'Mean rent · controls (matched)',   value: `$${controlB.mean_rent.toFixed(0)} / mo` },
          ]}
        />
        <InfoBlock
          title="Threshold indicator — pre-match sample"
          rows={[
            { label: 'Treated tracts (pre-match)',       value: (stageDthr?.treated ?? 274).toLocaleString(),        valueClass: 'text-teal-600' },
            { label: 'Control pool (pre-match)',         value: (stageDthr?.never_treated ?? 568).toLocaleString() },
            { label: 'Matched analysis sample',          value: (stageFthr?.n_tracts ?? 453).toLocaleString(),       valueClass: 'text-teal-600' },
            { label: 'Mean rent · treated (matched)',    value: `$${treatedT.mean_rent.toFixed(0)} / mo` },
            { label: 'Mean rent · controls (matched)',   value: `$${controlT.mean_rent.toFixed(0)} / mo` },
          ]}
        />
      </div>

      {/* ── ATT comparison across all specs ── */}
      <h3 className="text-lg font-bold mb-1">ATT estimates across all specifications</h3>
      <p className="text-[13px] text-gray-500 mb-4 max-w-2xl leading-relaxed">
        Both definitions deliver positive full-panel and matched-sample ATTs.
        The threshold indicator yields a larger full-panel effect (+56 vs +49) but a smaller
        matched effect (+15 vs +26). The residualized estimates flip negative for both —
        reflecting pre-existing rent trend differences, not a reversal of the effect.
      </p>
      <StatTable
        className="mb-10"
        headers={['Specification', 'Threshold ATT', 'Threshold SE', 'Binary ATT', 'Binary SE']}
        rows={ATT_COMPARISON}
      />

      {/* ── Full-panel CS: the primary comparison ── */}
      <h3 className="text-lg font-bold mb-1">Full-panel CS — primary estimate (binary vs threshold)</h3>
      <p className="text-[13px] text-gray-500 mb-5 max-w-2xl leading-relaxed">
        The headline result: both definitions show a <strong>positive post-ban effect</strong> that
        is largely absent in the pre-ban period. The threshold estimate is somewhat larger,
        consistent with threshold tracts being higher-rent areas where a prohibition has more
        bite on the short-term rental market.
      </p>
      <div className="grid grid-cols-2 gap-6 mb-10">
        <FigureSlot src="/data/threshold/did_callaway_santanna_event_study_full_panel.png"
          alt="CS full-panel event study — threshold" label="Threshold indicator (+56.0 $/mo)" />
        <FigureSlot src="/data/binary/did_callaway_santanna_event_study_full_panel.png"
          alt="CS full-panel event study — binary"    label="Binary indicator (+48.8 $/mo)" />
      </div>

      {/* ── Matched CS: secondary comparison ── */}
      <h3 className="text-lg font-bold mb-1">Matched-sample CS — robustness check</h3>
      <p className="text-[13px] text-gray-500 mb-5 max-w-2xl leading-relaxed">
        After restricting to trend-matched controls (k=3 NN on slope + pre-rent level),
        both definitions still show positive effects — smaller but directionally consistent.
        The threshold matched effect is notably smaller (+15 vs +56) because the threshold
        treated tracts are more unusual and harder to match well.
      </p>
      <div className="grid grid-cols-2 gap-6 mb-10">
        <FigureSlot src="/data/threshold/did_callaway_santanna_event_study.png"
          alt="CS matched event study — threshold" label="Threshold indicator (+14.7 $/mo)" />
        <FigureSlot src="/data/binary/did_callaway_santanna_event_study.png"
          alt="CS matched event study — binary"    label="Binary indicator (+26.1 $/mo)" />
      </div>

      {/* ── Cohort dynamics ── */}
      <h3 className="text-lg font-bold mb-1">Cohort dynamics — binary vs threshold</h3>
      <p className="text-[13px] text-gray-500 mb-5 max-w-2xl leading-relaxed">
        How effects vary by <em>when</em> a neighborhood first got a prohibition.
        Both definitions show cohort heterogeneity — the 2016 cohorts (the largest wave) drive
        much of the aggregate ATT.
      </p>
      <div className="grid grid-cols-2 gap-6 mb-10">
        <FigureSlot src="/data/threshold/did_cohort_dynamics.png"
          alt="Cohort dynamics — threshold" label="Threshold indicator" />
        <FigureSlot src="/data/binary/did_cohort_dynamics.png"
          alt="Cohort dynamics — binary"    label="Binary indicator" />
      </div>

      {/* ── TWFE vs CS ── */}
      <h3 className="text-lg font-bold mb-1">TWFE vs CS bias — binary vs threshold</h3>
      <p className="text-[13px] text-gray-500 mb-5 max-w-2xl leading-relaxed">
        The staggered-adoption bias in TWFE is present under both definitions. CS corrects
        for this regardless of which indicator is used.
      </p>
      <div className="grid grid-cols-2 gap-6 mb-10">
        <FigureSlot src="/data/threshold/did_twfe_vs_cs_comparison.png"
          alt="TWFE vs CS — threshold" label="Threshold indicator" />
        <FigureSlot src="/data/binary/did_twfe_vs_cs_comparison.png"
          alt="TWFE vs CS — binary"    label="Binary indicator" />
      </div>

      {/* ── SUTVA ── */}
      <h3 className="text-lg font-bold mb-1">SUTVA — spatial spillover checks</h3>
      <p className="text-[13px] text-gray-500 mb-5 max-w-2xl leading-relaxed">
        Two tests check whether prohibitions in one tract affect neighboring tracts&apos; rents.
        The donut test excludes control tracts within a short radius to detect spatial contamination.
        The dose-response checks whether the effect scales with prohibition density.
        If spillovers bias results, excluding nearby neighbors should shift the ATT meaningfully.
      </p>
      <div className="grid grid-cols-2 gap-6 mb-6">
        <FigureSlot src="/data/binary/sutva_donut.png"
          alt="SUTVA donut — binary" label="Donut test (binary)" />
        <FigureSlot src="/data/binary/sutva_dose_response.png"
          alt="SUTVA dose-response — binary" label="Dose-response (binary)" />
      </div>
      <div className="grid grid-cols-2 gap-6">
        <FigureSlot src="/data/threshold/sutva_donut.png"
          alt="SUTVA donut — threshold" label="Donut test (threshold)" />
        <FigureSlot src="/data/threshold/sutva_dose_response.png"
          alt="SUTVA dose-response — threshold" label="Dose-response (threshold)" />
      </div>
    </div>
  )
}
