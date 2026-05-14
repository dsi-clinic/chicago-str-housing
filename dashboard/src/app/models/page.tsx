import FigureSlot from '@/components/FigureSlot'
import StatTable from '@/components/StatTable'

/* ATT summary — from docs/DID_RESULTS_STORY.md (post-refactor run) */
const SPEC_TABLE = [
  ['CS full-panel (primary)',              '+56.0', '(0.45)', '+48.8', '(0.53)', 'Primary'],
  ['CS matched sample',                   '+14.7', '(0.49)', '+26.1', '(0.62)', 'Robustness'],
  ['CS residualized (ACS + tract trends)', '−89.6', '(0.54)', '−70.8', '(0.61)', 'Robustness†'],
]

export default function ModelsPage() {
  return (
    <div>
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">Models & Specifications</h2>
      <p className="text-[15px] text-gray-500 mb-10 max-w-2xl leading-relaxed">
        Three ways of estimating the same causal question — each stricter than the last.
        The full-panel result is the headline; the others show how sensitive it is to the
        choice of comparison group and adjustment method.
      </p>

      {/* ── Concept: The core question ── */}
      <div className="grid grid-cols-2 gap-5 mb-10">
        <div className="border border-gray-100 rounded-xl p-6">
          <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-3">The core question</p>
          <p className="text-[13px] text-gray-600 leading-relaxed">
            We can&apos;t observe what rents <em>would have been</em> in a neighborhood if it had
            never gotten an STR prohibition. So we compare neighborhoods that got prohibitions to
            similar ones that didn&apos;t. The difference in how rents changed is our estimate of
            the policy&apos;s effect.
          </p>
          <p className="text-[12px] text-gray-500 mt-3 leading-relaxed">
            The key challenge: treated neighborhoods (higher income, more educated, already
            higher rents) are systematically different from control neighborhoods. Our three
            specifications deal with this problem in progressively stronger ways.
          </p>
        </div>
        <div className="border border-gray-100 rounded-xl p-6">
          <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-3">Why a special estimator for staggered timing?</p>
          <p className="text-[13px] text-gray-600 leading-relaxed">
            STR prohibitions rolled out at different times across neighborhoods. The classical
            regression approach (TWFE) can accidentally use <em>already-prohibited</em> neighborhoods
            as comparison groups for <em>recently-prohibited</em> ones — corrupting the estimate.
          </p>
          <p className="text-[12px] text-gray-500 mt-3 leading-relaxed">
            Callaway &amp; Sant&apos;Anna (CS) avoids this by only comparing each newly-treated
            cohort to <em>never-treated</em> or <em>not-yet-treated</em> neighborhoods.
            This is more work but produces unbiased group-time estimates.
          </p>
        </div>
      </div>

      {/* ── How to read event study charts ── */}
      <div className="bg-gray-50 border border-gray-100 rounded-xl px-6 py-5 mb-10">
        <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-3">How to read the event study charts below</p>
        <div className="grid grid-cols-3 gap-6 text-[12px] text-gray-600">
          <div>
            <span className="font-bold block mb-1">X-axis: Months relative to the ban</span>
            Negative numbers = before the prohibition. Zero = the month the ban took effect.
            Positive = after.
          </div>
          <div>
            <span className="font-bold block mb-1">Y-axis: Estimated rent effect ($/mo)</span>
            How much higher or lower monthly rent was in treated neighborhoods compared
            to similar untreated ones, accounting for baseline differences.
          </div>
          <div>
            <span className="font-bold block mb-1">What to look for</span>
            <span className="text-teal-600 font-medium">Pre-ban period (left)</span> should be flat near zero — if the lines were already diverging before the ban, the parallel trends assumption is violated.
            <span className="text-maroon font-medium"> Post-ban period (right)</span> shows the actual estimated effect.
          </div>
        </div>
      </div>

      {/* ── ATT Summary Table ── */}
      <div className="mb-10">
        <h3 className="text-lg font-bold mb-1">Summary of estimates</h3>
        <p className="text-[13px] text-gray-500 mb-4 max-w-2xl leading-relaxed">
          Each row is a different specification. Read them as: &ldquo;after the prohibition,
          monthly rent in treated tracts was X $/month higher (or lower) than it would have been
          without the prohibition, compared to our control group.&rdquo;
        </p>
        <StatTable
          headers={['Specification', 'Threshold ATT', 'SE', 'Binary ATT', 'SE', 'Role']}
          rows={SPEC_TABLE}
        />
        <p className="text-[11px] text-gray-400 mt-2">
          ATT = average treatment effect on the treated, in $/month (index-scale).
          † Residualized estimate measures deviation from pre-trend, not rent level — not directly comparable to rows above.
          Source: <code className="bg-gray-100 px-1 rounded text-[10px]">docs/DID_RESULTS_STORY.md</code> (post-refactor run).
        </p>
      </div>

      {/* ══════════════════════════════════════════════════
          SPEC 1: Full-panel CS (Primary)
      ══════════════════════════════════════════════════ */}
      <div className="border-l-4 border-maroon bg-maroon/5 rounded-r-xl overflow-hidden mb-8">
        <div className="px-6 pt-5 pb-4">
          <div className="flex items-baseline gap-3 mb-3">
            <span className="text-[11px] font-bold uppercase tracking-wider text-maroon bg-maroon/10 px-2 py-0.5 rounded">① Primary estimate</span>
            <span className="text-[15px] font-bold text-gray-900">Full-panel Callaway &amp; Sant&apos;Anna</span>
          </div>

          <div className="grid grid-cols-2 gap-6 mb-5">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">What this model does</p>
              <p className="text-[13px] text-gray-600 leading-relaxed">
                Compares rent changes in <strong>every neighborhood that got a prohibition</strong> to
                all neighborhoods that never got one (or hadn&apos;t yet). No filtering, no hand-picking
                — the broadest, most transparent comparison group possible.
              </p>
              <p className="text-[13px] text-gray-600 leading-relaxed mt-2">
                Each prohibited neighborhood (cohort) is compared to the pool of never-treated
                neighborhoods that had <em>no ban at all</em> during the study period. The CS
                estimator then aggregates these cohort-level comparisons with correct weights.
              </p>
            </div>
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">Why this is the headline</p>
              <p className="text-[13px] text-gray-600 leading-relaxed">
                This estimate uses the <strong>most comparison neighborhoods</strong> and makes
                the fewest additional assumptions. It doesn&apos;t restrict the sample to
                &ldquo;similar&rdquo; neighborhoods (we show what happens when you do that in
                Specification ②). As long as rents in treated and control neighborhoods would have
                moved in parallel without the ban, this is unbiased.
              </p>
            </div>
          </div>

          <div className="flex gap-8 mb-1">
            <div>
              <span className="text-[10px] uppercase tracking-wider text-gray-400 block mb-0.5">Threshold indicator</span>
              <span className="text-3xl font-extrabold text-maroon tracking-tight">+56.0</span>
              <span className="text-sm text-gray-400 ml-1">(SE 0.45)</span>
              <span className="text-xs text-gray-400 ml-1">$/mo</span>
            </div>
            <div>
              <span className="text-[10px] uppercase tracking-wider text-gray-400 block mb-0.5">Binary indicator</span>
              <span className="text-3xl font-extrabold text-maroon tracking-tight">+48.8</span>
              <span className="text-sm text-gray-400 ml-1">(SE 0.53)</span>
              <span className="text-xs text-gray-400 ml-1">$/mo</span>
            </div>
            <div className="flex-1 bg-white/60 border border-maroon/10 rounded-xl px-4 py-2 text-[12px] text-gray-600 max-w-xs">
              <strong>Interpretation:</strong> In the average post-prohibition month, rents in
              prohibited neighborhoods were roughly <strong>$49–56/month higher</strong> than
              they would have been without the prohibition, compared to never-treated neighborhoods.
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4 px-6 pb-5">
          <FigureSlot src="/data/threshold/did_callaway_santanna_event_study_full_panel.png"
            alt="CS full-panel event study — threshold" label="Threshold indicator" />
          <FigureSlot src="/data/binary/did_callaway_santanna_event_study_full_panel.png"
            alt="CS full-panel event study — binary"    label="Binary indicator" />
        </div>
      </div>

      {/* ══════════════════════════════════════════════════
          SPEC 2: Matched CS (Robustness)
      ══════════════════════════════════════════════════ */}
      <div className="border-l-4 border-blue-500 bg-blue-50 rounded-r-xl overflow-hidden mb-8">
        <div className="px-6 pt-5 pb-4">
          <div className="flex items-baseline gap-3 mb-3">
            <span className="text-[11px] font-bold uppercase tracking-wider text-blue-600 bg-blue-100 px-2 py-0.5 rounded">② Robustness check</span>
            <span className="text-[15px] font-bold text-gray-900">CS on trend-matched sample</span>
          </div>

          <div className="grid grid-cols-2 gap-6 mb-5">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">What this model does</p>
              <p className="text-[13px] text-gray-600 leading-relaxed">
                Before running the same CS estimator, we first <strong>narrow the comparison
                group</strong>: each prohibited neighborhood is matched to its 3 most similar
                never-treated neighborhoods based on:
              </p>
              <ul className="text-[12px] text-gray-600 mt-2 ml-3 space-y-1 list-disc list-inside">
                <li><strong>Pre-ban rent slope</strong> — was rent rising faster or slower?</li>
                <li><strong>Average pre-ban rent level</strong> — was it a high- or low-rent area?</li>
              </ul>
              <p className="text-[13px] text-gray-600 leading-relaxed mt-2">
                Matching is <em>standardized</em> (both features scaled to same units before
                comparing) and uses nearest-neighbor matching with k=3.
                This is the <strong>updated matching method</strong> — the previous version only
                used rent slope, leaving large level differences unaddressed.
              </p>
            </div>
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">What we learn from this</p>
              <p className="text-[13px] text-gray-600 leading-relaxed">
                The effect shrinks substantially — from +$56 down to +$15 (threshold) — when we
                restrict to comparison neighborhoods that looked more like the treated ones
                before the ban. The effect stays positive, but the size depends a lot on
                who we compare against.
              </p>
              <p className="text-[13px] text-gray-600 leading-relaxed mt-2">
                <strong>Important caveat:</strong> Matching does <em>not</em> solve the
                selection problem — treated neighborhoods are still systematically richer and
                more educated (see Audit tab). It just makes the comparison group more similar
                on rent dynamics specifically. Present as robustness, not as the headline.
              </p>
            </div>
          </div>

          <div className="flex gap-8 mb-1">
            <div>
              <span className="text-[10px] uppercase tracking-wider text-gray-400 block mb-0.5">Threshold indicator</span>
              <span className="text-3xl font-extrabold text-blue-700 tracking-tight">+14.7</span>
              <span className="text-sm text-gray-400 ml-1">(SE 0.49)</span>
              <span className="text-xs text-gray-400 ml-1">$/mo</span>
            </div>
            <div>
              <span className="text-[10px] uppercase tracking-wider text-gray-400 block mb-0.5">Binary indicator</span>
              <span className="text-3xl font-extrabold text-blue-700 tracking-tight">+26.1</span>
              <span className="text-sm text-gray-400 ml-1">(SE 0.62)</span>
              <span className="text-xs text-gray-400 ml-1">$/mo</span>
            </div>
            <div className="flex-1 bg-white/60 border border-blue-200/50 rounded-xl px-4 py-2 text-[12px] text-gray-600 max-w-xs">
              <strong>Interpretation:</strong> After restricting to matched comparison
              neighborhoods, the effect is still positive but smaller — roughly
              <strong> $15–26/month</strong>. The sign is robust; the size is sensitive
              to the comparison group.
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4 px-6 pb-5">
          <FigureSlot src="/data/threshold/did_callaway_santanna_event_study.png"
            alt="CS matched event study — threshold" label="Threshold indicator" />
          <FigureSlot src="/data/binary/did_callaway_santanna_event_study.png"
            alt="CS matched event study — binary"    label="Binary indicator" />
        </div>
      </div>

      {/* ══════════════════════════════════════════════════
          Residualization explainer (before spec 3)
      ══════════════════════════════════════════════════ */}
      <div className="border border-amber-200 bg-amber-50 rounded-xl px-6 py-5 mb-6">
        <p className="text-[11px] font-bold uppercase tracking-wider text-amber-700 mb-3">Understanding residualization — what Specification ③ actually measures</p>
        <div className="grid grid-cols-2 gap-6 text-[13px] text-gray-700 leading-relaxed">
          <div>
            <p className="font-semibold mb-2">The intuition: comparing to where you were headed</p>
            <p>
              Imagine a neighborhood where rents were already rising <strong>$40/month</strong>
              every month before the prohibition. After the ban, they rise $20/month.
            </p>
            <p className="mt-2">
              In raw terms: rents still went up (+$20). But compared to the
              pre-ban trajectory: they rose <strong>$20 less</strong> than the trend predicted
              (-$20 below trend). That gap between &ldquo;what happened&rdquo; and
              &ldquo;what was expected to happen&rdquo; is what residualization measures.
            </p>
          </div>
          <div>
            <p className="font-semibold mb-2">How it works technically</p>
            <ol className="ml-4 space-y-1.5 list-decimal list-outside">
              <li>For each tract, fit a linear rent trend using <em>pre-treatment data only</em></li>
              <li>Subtract that trend from each rent observation (this is &ldquo;residualizing&rdquo;)</li>
              <li>Also remove variation explained by ACS characteristics (income, education, occupancy)</li>
              <li>Run CS on these <em>residuals</em> — the part of rent not explained by trends or observables</li>
            </ol>
            <p className="mt-2 text-[12px] text-amber-800 font-medium">
              ⚠ The −$90/month result is NOT in original $/month units.
              It means: after the ban, treated tracts fell $90 below their pre-ban
              trend — but that trend was already positive. This is not directly
              comparable to the +$56 primary estimate.
            </p>
          </div>
        </div>
        <div className="mt-4 pt-4 border-t border-amber-200 text-[12px] text-gray-600">
          <strong>Why does it flip negative?</strong> Treated tracts were on systematically steeper
          rent growth paths before 2016 (higher income, more gentrification pressure). Once you
          subtract those pre-existing trends, rents in treated tracts appear to have grown
          <em> less</em> than their own trajectory predicted — even if raw rents still went up.
          The residualized estimate captures trend deviation, not level change.
        </div>
      </div>

      {/* ══════════════════════════════════════════════════
          SPEC 3: Residualized CS (Robustness†)
      ══════════════════════════════════════════════════ */}
      <div className="border-l-4 border-amber-500 bg-amber-50 rounded-r-xl overflow-hidden mb-10">
        <div className="px-6 pt-5 pb-4">
          <div className="flex items-baseline gap-3 mb-3">
            <span className="text-[11px] font-bold uppercase tracking-wider text-amber-700 bg-amber-100 px-2 py-0.5 rounded">③ Robustness† (not directly comparable)</span>
            <span className="text-[15px] font-bold text-gray-900">CS with ACS covariates + tract-specific linear trends</span>
          </div>

          <div className="grid grid-cols-2 gap-6 mb-5">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">What this model does</p>
              <p className="text-[13px] text-gray-600 leading-relaxed">
                The most demanding adjustment layer. Before running CS, it removes from each
                tract&apos;s rent:
              </p>
              <ul className="text-[12px] text-gray-600 mt-2 ml-3 space-y-1 list-disc list-inside">
                <li>Variation explained by ACS characteristics (median income, education, occupancy, age)</li>
                <li>Each tract&apos;s own linear pre-ban rent trend (fitted on pre-treatment data only)</li>
              </ul>
              <p className="text-[13px] text-gray-600 leading-relaxed mt-2">
                This is the &ldquo;doubly-robust&rdquo; version — consistent if either the
                propensity score model or the outcome model is correctly specified.
              </p>
            </div>
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">What the negative sign tells us</p>
              <p className="text-[13px] text-gray-600 leading-relaxed">
                The negative estimate means treated tracts&apos; rents grew <em>less</em> than
                their own pre-ban trajectory predicted. This is a sign that the ban may have
                slowed the rent growth that was already underway — not that rents fell.
              </p>
              <p className="text-[13px] text-gray-600 leading-relaxed mt-2">
                It also reveals that treated neighborhoods were structurally different: once
                you account for their steeper pre-ban rent trajectories, the &ldquo;effect&rdquo;
                all but disappears or reverses. This is useful evidence on heterogeneity — not
                a replacement for the primary estimate.
              </p>
            </div>
          </div>

          <div className="flex gap-8 mb-1">
            <div>
              <span className="text-[10px] uppercase tracking-wider text-gray-400 block mb-0.5">Threshold indicator</span>
              <span className="text-3xl font-extrabold text-amber-700 tracking-tight">−89.6</span>
              <span className="text-sm text-gray-400 ml-1">(SE 0.54)</span>
              <span className="text-xs text-gray-400 ml-1">residualized units†</span>
            </div>
            <div>
              <span className="text-[10px] uppercase tracking-wider text-gray-400 block mb-0.5">Binary indicator</span>
              <span className="text-3xl font-extrabold text-amber-700 tracking-tight">−70.8</span>
              <span className="text-sm text-gray-400 ml-1">(SE 0.61)</span>
              <span className="text-xs text-gray-400 ml-1">residualized units†</span>
            </div>
            <div className="flex-1 bg-white/60 border border-amber-200/60 rounded-xl px-4 py-2 text-[12px] text-gray-600 max-w-xs">
              <strong>Interpretation (†):</strong> After removing pre-ban trends and observable
              differences, treated tracts&apos; rents grew about $70–90/month <em>below
              their own predicted trend</em>. This is deviation-from-trend, not raw rent change.
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4 px-6 pb-5">
          <FigureSlot src="/data/threshold/did_callaway_santanna_event_study_with_controls.png"
            alt="CS residualized event study — threshold" label="Threshold indicator" />
          <FigureSlot src="/data/binary/did_callaway_santanna_event_study_with_controls.png"
            alt="CS residualized event study — binary"    label="Binary indicator" />
        </div>
      </div>

      {/* ══════════════════════════════════════════════════
          Appendix: TWFE comparison
      ══════════════════════════════════════════════════ */}
      <div className="border border-gray-100 rounded-xl p-6">
        <h3 className="text-[14px] font-bold text-gray-700 mb-1">Appendix: Why not use a simple regression? (TWFE vs CS)</h3>
        <p className="text-[13px] text-gray-500 mb-4 max-w-3xl leading-relaxed">
          The standard approach for panel data — two-way fixed effects (TWFE) regression — works well
          when all neighborhoods get treated at the same time. With staggered timing, TWFE can
          accidentally treat <em>already-prohibited</em> neighborhoods as controls for new prohibitions,
          assigning them <strong>negative implicit weights</strong>. This can flip or compress estimates
          even when the true effect is positive. The plots below show where TWFE and CS agree and
          where they diverge — the gap diagnoses this bias.
        </p>
        <div className="grid grid-cols-2 gap-6">
          <FigureSlot src="/data/binary/did_twfe_vs_cs_comparison.png"
            alt="TWFE vs CS comparison" label="TWFE vs CS overlay (binary)" />
          <FigureSlot src="/data/binary/did_cs_twfe_difference.png"
            alt="CS minus TWFE difference" label="CS − TWFE gap — where bias is concentrated (binary)" />
        </div>
      </div>
    </div>
  )
}
