import FigureSlot from '@/components/FigureSlot'
import StatTable from '@/components/StatTable'

/* ATT values — docs/DID_RESULTS_STORY.md (post-refactor run) */
const ATT_TABLE = [
  ['Full-panel CS (primary)',              '+56.0', '(0.45)', '+48.8', '(0.53)', 'Primary'],
  ['Matched CS',                           '+14.7', '(0.49)', '+26.1', '(0.62)', 'Robustness'],
  ['Residualized CS (ACS + tract trends)', '−89.6', '(0.54)', '−70.8', '(0.61)', 'Robustness†'],
]

export default function ModelsPage() {
  return (
    <div>
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">Models & Results</h2>
      <p className="text-[15px] text-gray-500 mb-10 max-w-2xl leading-relaxed">
        Why Callaway & Sant&apos;Anna instead of standard regression, what each specification
        assumes, and the causal estimates — from the most transparent design to the most demanding.
      </p>

      {/* ── Why CS, not TWFE ── */}
      <div className="grid grid-cols-2 gap-5 mb-10">
        <div className="border border-gray-100 rounded-xl p-6">
          <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-3">The counterfactual problem</p>
          <p className="text-[13px] text-gray-600 leading-relaxed">
            We can&apos;t observe what rents would have been without the prohibition.
            So we compare neighborhoods that got prohibitions to similar ones that didn&apos;t.
            The difference in how rents changed — after accounting for pre-existing differences —
            is our estimate of the causal effect.
          </p>
        </div>
        <div className="border border-gray-100 rounded-xl p-6">
          <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-3">Why not standard regression?</p>
          <p className="text-[13px] text-gray-600 leading-relaxed">
            When bans roll out at different times, the standard TWFE regression accidentally
            uses already-prohibited neighborhoods as controls for newly-prohibited ones —
            assigning them negative implicit weights and biasing results. CS avoids this by
            comparing each cohort only to never-treated or not-yet-treated tracts.
          </p>
        </div>
      </div>

      {/* ── How to read the event studies ── */}
      <div className="bg-gray-50 border border-gray-100 rounded-xl px-6 py-5 mb-10">
        <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-3">How to read the event study charts</p>
        <div className="grid grid-cols-3 gap-6 text-[12px] text-gray-600">
          <div><strong className="block mb-1">X-axis: months relative to the ban</strong>
            Negative = before the prohibition. Zero = first ban month. Positive = after.</div>
          <div><strong className="block mb-1">Y-axis: estimated rent effect ($/mo)</strong>
            How much higher or lower rents were in treated tracts vs similar untreated ones.</div>
          <div><strong className="block mb-1">What to look for</strong>
            <span className="text-teal-600 font-medium">Pre-ban period</span> should be flat near zero.
            <span className="text-maroon font-medium"> Post-ban period</span> shows the effect.</div>
        </div>
      </div>

      {/* ══════════════════════════════════════════════
          SPEC 1: Full-panel CS (Primary)
      ══════════════════════════════════════════════ */}
      <div className="border-l-4 border-maroon bg-maroon/5 rounded-r-xl overflow-hidden mb-8">
        <div className="px-6 pt-5 pb-4">
          <div className="flex items-baseline gap-3 mb-3">
            <span className="text-[11px] font-bold uppercase tracking-wider text-maroon bg-maroon/10 px-2 py-0.5 rounded">① Primary</span>
            <span className="text-[15px] font-bold text-gray-900">Full-panel Callaway & Sant&apos;Anna</span>
          </div>
          <div className="grid grid-cols-2 gap-6 mb-5">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">What this model does</p>
              <p className="text-[13px] text-gray-600 leading-relaxed">
                Compares rent changes in every prohibited neighborhood to all neighborhoods
                that never got a ban. No filtering or hand-picking — the broadest, most
                transparent comparison group. Each cohort is compared separately to the
                never-treated pool, then aggregated with correct weights.
              </p>
            </div>
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">Why this is the headline</p>
              <p className="text-[13px] text-gray-600 leading-relaxed">
                Fewest additional assumptions. Doesn&apos;t restrict the comparison group.
                As long as pre-ban trends were parallel (tested in Analysis), this estimate
                is unbiased. The other two specifications add restrictions and show sensitivity.
              </p>
            </div>
          </div>
          <div className="flex gap-8">
            <div>
              <span className="text-[10px] uppercase tracking-wider text-gray-400 block mb-0.5">Threshold ATT</span>
              <span className="text-3xl font-extrabold text-maroon tracking-tight">+56.0</span>
              <span className="text-sm text-gray-400 ml-1">(SE 0.45) $/mo</span>
            </div>
            <div>
              <span className="text-[10px] uppercase tracking-wider text-gray-400 block mb-0.5">Binary ATT</span>
              <span className="text-3xl font-extrabold text-maroon tracking-tight">+48.8</span>
              <span className="text-sm text-gray-400 ml-1">(SE 0.53) $/mo</span>
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4 px-6 pb-5">
          <FigureSlot src="/data/threshold/did_callaway_santanna_event_study_full_panel.png"
            alt="Full-panel CS — threshold" label="Threshold indicator" />
          <FigureSlot src="/data/binary/did_callaway_santanna_event_study_full_panel.png"
            alt="Full-panel CS — binary"    label="Binary indicator" />
        </div>
      </div>

      {/* ══════════════════════════════════════════════
          SPEC 2: Matched CS
      ══════════════════════════════════════════════ */}
      <div className="border-l-4 border-blue-500 bg-blue-50 rounded-r-xl overflow-hidden mb-8">
        <div className="px-6 pt-5 pb-4">
          <div className="flex items-baseline gap-3 mb-3">
            <span className="text-[11px] font-bold uppercase tracking-wider text-blue-600 bg-blue-100 px-2 py-0.5 rounded">② Robustness</span>
            <span className="text-[15px] font-bold text-gray-900">CS on trend-matched sample</span>
          </div>
          <div className="grid grid-cols-2 gap-6 mb-5">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">What this model does</p>
              <p className="text-[13px] text-gray-600 leading-relaxed">
                Before running CS, each prohibited tract is matched to its 3 nearest
                never-treated neighbors based on pre-ban rent slope and average pre-ban
                rent level (standardized, k=3 NN). The same CS estimator then runs on
                this narrower sample. No caliper was applied.
              </p>
            </div>
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">What we learn</p>
              <p className="text-[13px] text-gray-600 leading-relaxed">
                The effect shrinks — from +$56 to +$15 (threshold) — when the comparison
                group is restricted to tracts with similar rent dynamics. The sign holds,
                but the size is sensitive to comparison group choice. Matching should be
                read as a robustness restriction, not a stronger identification claim.
              </p>
            </div>
          </div>
          <div className="flex gap-8">
            <div>
              <span className="text-[10px] uppercase tracking-wider text-gray-400 block mb-0.5">Threshold ATT</span>
              <span className="text-3xl font-extrabold text-blue-700 tracking-tight">+14.7</span>
              <span className="text-sm text-gray-400 ml-1">(SE 0.49) $/mo</span>
            </div>
            <div>
              <span className="text-[10px] uppercase tracking-wider text-gray-400 block mb-0.5">Binary ATT</span>
              <span className="text-3xl font-extrabold text-blue-700 tracking-tight">+26.1</span>
              <span className="text-sm text-gray-400 ml-1">(SE 0.62) $/mo</span>
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4 px-6 pb-5">
          <FigureSlot src="/data/threshold/did_callaway_santanna_event_study.png"
            alt="Matched CS — threshold" label="Threshold indicator" />
          <FigureSlot src="/data/binary/did_callaway_santanna_event_study.png"
            alt="Matched CS — binary"    label="Binary indicator" />
        </div>
      </div>

      {/* ── Residualization explainer ── */}
      <div className="border border-amber-200 bg-amber-50 rounded-xl px-6 py-5 mb-6">
        <p className="text-[11px] font-bold uppercase tracking-wider text-amber-700 mb-3">Before reading Specification ③ — understanding residualization</p>
        <div className="grid grid-cols-2 gap-6 text-[13px] text-gray-700 leading-relaxed">
          <div>
            <p className="font-semibold mb-2">Comparing to where you were headed</p>
            <p>Suppose a neighborhood&apos;s rents were rising $40/month before the ban.
            After the ban, they rise $20/month. In raw terms, rents still went up.
            But compared to the pre-ban trajectory, they rose $20 less than expected.</p>
            <p className="mt-2">Residualization measures that gap — the deviation from the
            pre-existing trend — not the level change.</p>
          </div>
          <div>
            <p className="font-semibold mb-2">Why the estimate flips negative</p>
            <p>Treated tracts were already on steeper rent growth paths before 2016.
            Once those pre-ban trajectories are removed, rents in treated tracts look like
            they grew less than predicted — even if raw rents still increased.</p>
            <p className="mt-2 text-amber-800 font-medium">
              The −$90 figure is not in original $/month units. It is deviation-from-trend,
              not directly comparable to the +$56 primary estimate.
            </p>
          </div>
        </div>
      </div>

      {/* ══════════════════════════════════════════════
          SPEC 3: Residualized CS
      ══════════════════════════════════════════════ */}
      <div className="border-l-4 border-amber-500 bg-amber-50 rounded-r-xl overflow-hidden mb-10">
        <div className="px-6 pt-5 pb-4">
          <div className="flex items-baseline gap-3 mb-3">
            <span className="text-[11px] font-bold uppercase tracking-wider text-amber-700 bg-amber-100 px-2 py-0.5 rounded">③ Robustness† (not comparable)</span>
            <span className="text-[15px] font-bold text-gray-900">CS with ACS covariates + tract-specific trends</span>
          </div>
          <div className="grid grid-cols-2 gap-6 mb-5">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">What this model does</p>
              <p className="text-[13px] text-gray-600 leading-relaxed">
                Before running CS, removes from each tract&apos;s rent: (1) variation
                explained by ACS characteristics (income, education, occupancy), and
                (2) each tract&apos;s own linear pre-ban rent trend (fitted on
                pre-treatment months only). Runs CS on these residuals.
              </p>
            </div>
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">What the negative sign tells us</p>
              <p className="text-[13px] text-gray-600 leading-relaxed">
                After accounting for pre-existing rent trajectories, treated tracts grew
                less than their own trend predicted. This is evidence that treated
                neighborhoods were structurally different — on steeper rent growth paths
                before the ban. The negative sign is not a contradiction; it measures
                something different from the primary estimate.
              </p>
            </div>
          </div>
          <div className="flex gap-8">
            <div>
              <span className="text-[10px] uppercase tracking-wider text-gray-400 block mb-0.5">Threshold ATT†</span>
              <span className="text-3xl font-extrabold text-amber-700 tracking-tight">−89.6</span>
              <span className="text-sm text-gray-400 ml-1">(SE 0.54) residualized units</span>
            </div>
            <div>
              <span className="text-[10px] uppercase tracking-wider text-gray-400 block mb-0.5">Binary ATT†</span>
              <span className="text-3xl font-extrabold text-amber-700 tracking-tight">−70.8</span>
              <span className="text-sm text-gray-400 ml-1">(SE 0.61) residualized units</span>
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4 px-6 pb-5">
          <FigureSlot src="/data/threshold/did_callaway_santanna_event_study_with_controls.png"
            alt="Residualized CS — threshold" label="Threshold indicator" />
          <FigureSlot src="/data/binary/did_callaway_santanna_event_study_with_controls.png"
            alt="Residualized CS — binary"    label="Binary indicator" />
        </div>
      </div>

      {/* ── Cohort dynamics ── */}
      <h3 className="text-lg font-bold mb-1">Cohort-level effects</h3>
      <p className="text-[13px] text-gray-500 mb-5 max-w-2xl leading-relaxed">
        Group-time ATTs by prohibition cohort. The 2016 cohorts drive most of the
        aggregate effect. Later cohorts are smaller and noisier.
      </p>
      <div className="grid grid-cols-2 gap-6 mb-6">
        <FigureSlot src="/data/threshold/did_cohort_dynamics_full_panel.png"
          alt="Cohort dynamics — threshold" label="Threshold — cohort ATTs (full panel)" />
        <FigureSlot src="/data/binary/did_cohort_dynamics_full_panel.png"
          alt="Cohort dynamics — binary"    label="Binary — cohort ATTs (full panel)" />
      </div>
      <FigureSlot
        src="/data/binary/cohort_dynamics_explainer.png"
        alt="Cohort dynamics explainer"
        label="Cohort ATTs — annotated by prohibition wave"
        className="mb-10"
      />

      {/* ── Summary ATT table ── */}
      <h3 className="text-lg font-bold mb-1">Summary of all estimates</h3>
      <p className="text-[13px] text-gray-500 mb-4 max-w-2xl leading-relaxed">
        The full-panel result (+$56/+$49) is the headline. The range +$15 to +$56
        (threshold) and +$26 to +$49 (binary) represents honest uncertainty about
        effect size across comparison-group choices. The residualized estimate (−$90/−$71)
        is not in original $/month units.
      </p>
      <StatTable
        className="mb-10"
        headers={['Specification', 'Threshold ATT', 'SE', 'Binary ATT', 'SE', 'Role']}
        rows={ATT_TABLE}
      />

      {/* ── TWFE comparison ── */}
      <div className="border border-gray-100 rounded-xl p-6">
        <h3 className="text-[14px] font-bold text-gray-700 mb-1">Appendix: TWFE vs CS comparison</h3>
        <p className="text-[13px] text-gray-500 mb-5 max-w-2xl leading-relaxed">
          With staggered adoption, TWFE can assign negative implicit weights to some
          comparisons. The gap between TWFE and CS diagnoses the extent of this bias
          in our setting.
        </p>
        <div className="grid grid-cols-2 gap-6">
          <FigureSlot src="/data/binary/did_twfe_vs_cs_comparison.png"
            alt="TWFE vs CS overlay" label="TWFE vs CS overlay (binary)" />
          <FigureSlot src="/data/binary/did_cs_twfe_difference.png"
            alt="CS minus TWFE gap" label="CS minus TWFE — bias concentration (binary)" />
        </div>
      </div>
    </div>
  )
}
