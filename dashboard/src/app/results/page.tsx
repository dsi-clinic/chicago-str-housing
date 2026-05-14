import FigureSlot from '@/components/FigureSlot'
import StatTable from '@/components/StatTable'

/* ATT values from docs/DID_RESULTS_STORY.md (post-refactor run) */
const ATT_TABLE = [
  ['Full-panel CS (primary)',              '+56.0', '(0.45)', '+48.8', '(0.53)', 'Primary'],
  ['Matched CS',                           '+14.7', '(0.49)', '+26.1', '(0.62)', 'Robustness'],
  ['Residualized CS (ACS + tract trends)', '−89.6', '(0.54)', '−70.8', '(0.61)', 'Robustness†'],
]

export default function ResultsPage() {
  return (
    <div>
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">Results</h2>
      <p className="text-[15px] text-gray-500 mb-6 max-w-2xl leading-relaxed">
        The causal estimates. Read the event study charts to verify pre-period flatness,
        then the post-ban effect. The ATT table summarises the range across specifications
        and indicators.
      </p>

      {/* ── ATT summary ── */}
      <div className="border-l-4 border-maroon bg-maroon/5 rounded-r-xl px-6 py-5 mb-10">
        <p className="text-[10px] font-bold uppercase tracking-widest text-maroon mb-2">Headline finding</p>
        <p className="text-[14px] text-gray-700 leading-relaxed">
          STR prohibitions are associated with a <strong>positive post-ban rent effect</strong> under
          the primary full-panel CS specification. The effect ranges from <strong>+$49–56/month</strong>
          across indicators. Restricting to matched controls shrinks but does not reverse the sign.
          The residualized estimate flips negative — reflecting pre-existing trend differences in
          treated neighborhoods, not a contradiction of the primary result.
        </p>
      </div>

      <h3 className="text-lg font-bold mb-3">ATT estimates by specification and indicator</h3>
      <StatTable
        className="mb-10"
        headers={['Specification', 'Threshold ATT', 'SE', 'Binary ATT', 'SE', 'Role']}
        rows={ATT_TABLE}
      />

      {/* ── Primary: Full-panel CS event studies ── */}
      <h3 className="text-lg font-bold mb-1">Full-panel CS — primary event study</h3>
      <p className="text-[13px] text-gray-500 mb-5 max-w-2xl leading-relaxed">
        The headline result. Each prohibited cohort is compared to never-treated tracts
        that had no ban at any point during the study window. The x-axis shows months
        relative to the first ban. Pre-ban estimates should be near zero; post-ban estimates
        show the causal effect. See Models tab for why CS is preferred over TWFE here.
      </p>
      <div className="grid grid-cols-2 gap-6 mb-10">
        <FigureSlot src="/data/threshold/did_callaway_santanna_event_study_full_panel.png"
          alt="Full-panel CS event study — threshold" label="Threshold indicator (+$56.0/mo)" />
        <FigureSlot src="/data/binary/did_callaway_santanna_event_study_full_panel.png"
          alt="Full-panel CS event study — binary"    label="Binary indicator (+$48.8/mo)" />
      </div>

      {/* ── Cohort dynamics ── */}
      <h3 className="text-lg font-bold mb-1">Does the effect vary by cohort?</h3>
      <p className="text-[13px] text-gray-500 mb-5 max-w-2xl leading-relaxed">
        Group-time ATTs broken down by prohibition cohort. The 2016 cohorts dominate
        the aggregate ATT in both indicators. Later cohorts are smaller and noisier.
        Heterogeneity across cohorts is expected and does not invalidate the aggregate estimate.
      </p>
      <div className="grid grid-cols-2 gap-6 mb-10">
        <FigureSlot src="/data/threshold/did_cohort_dynamics_full_panel.png"
          alt="Cohort dynamics full-panel — threshold" label="Threshold — cohort-level ATTs" />
        <FigureSlot src="/data/binary/did_cohort_dynamics_full_panel.png"
          alt="Cohort dynamics full-panel — binary"    label="Binary — cohort-level ATTs" />
      </div>

      {/* ── Cohort explainer ── */}
      <FigureSlot
        src="/data/binary/cohort_dynamics_explainer.png"
        alt="Cohort dynamics explainer"
        label="Cohort dynamics — ATT by prohibition wave, annotated"
        className="mb-10"
      />

      {/* ── Matched CS for comparison ── */}
      <h3 className="text-lg font-bold mb-1">Matched CS — for comparison</h3>
      <p className="text-[13px] text-gray-500 mb-5 max-w-2xl leading-relaxed">
        Same estimator, restricted to trend-matched controls (k=3 NN on pre-slope and
        pre-rent level). The effect shrinks but the sign holds. The pre-period is somewhat
        cleaner in some cohorts — because matching explicitly selected controls with similar
        pre-trends.
      </p>
      <div className="grid grid-cols-2 gap-6">
        <FigureSlot src="/data/threshold/did_callaway_santanna_event_study.png"
          alt="Matched CS — threshold" label="Threshold matched CS (+$14.7/mo)" />
        <FigureSlot src="/data/binary/did_callaway_santanna_event_study.png"
          alt="Matched CS — binary"    label="Binary matched CS (+$26.1/mo)" />
      </div>
    </div>
  )
}
