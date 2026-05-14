import FigureSlot from '@/components/FigureSlot'
import InfoBlock from '@/components/InfoBlock'
import { loadParallelTrendsTest, loadHonestPretrends } from '@/lib/data'

export default function PretrendsPage() {
  const ptB = loadParallelTrendsTest('binary')
  const ptT = loadParallelTrendsTest('threshold')
  const hpB = loadHonestPretrends('binary')
  const hpT = loadHonestPretrends('threshold')

  return (
    <div>
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">
        Assumption Checks — Parallel Trends &amp; SUTVA
      </h2>
      <p className="text-[15px] text-gray-500 mb-6 max-w-2xl leading-relaxed">
        Two assumptions must hold for our DiD estimates to be valid. This tab tests both —
        honestly, including where the evidence is imperfect.
      </p>

      {/* ── What the assumptions are ── */}
      <div className="grid grid-cols-2 gap-5 mb-10">
        <div className="border border-gray-100 rounded-xl p-6">
          <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-3">Assumption 1: Parallel trends</p>
          <p className="text-[13px] text-gray-600 leading-relaxed">
            Without the prohibition, rents in treated and never-treated neighborhoods would
            have moved in <strong>parallel</strong> — growing at the same rate, even if from
            different starting levels. We can never test this directly (we can&apos;t observe
            the counterfactual), but we can check whether rents were <em>already diverging</em>
            before the ban.
          </p>
          <p className="text-[12px] text-gray-500 mt-3">
            <strong>If violated:</strong> Our ATT estimate would partially reflect pre-existing
            rent trends, not just the policy effect. The residualized CS addresses this partially
            by removing linear pre-trends, but at the cost of comparability.
          </p>
        </div>
        <div className="border border-gray-100 rounded-xl p-6">
          <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-3">Assumption 2: SUTVA (no spillovers)</p>
          <p className="text-[13px] text-gray-600 leading-relaxed">
            We assume one neighborhood&apos;s STR prohibition doesn&apos;t affect its
            neighbor&apos;s rents. If a prohibition in one area simply pushes STR demand to
            adjacent streets — raising those neighbors&apos; rents — we might mistake
            demand displacement for a genuine policy effect.
          </p>
          <p className="text-[12px] text-gray-500 mt-3">
            <strong>If violated:</strong> Our control group would be contaminated (controls
            near treated tracts would have inflated rents), biasing estimates downward.
          </p>
        </div>
      </div>

      {/* ── Parallel trends regression test ── */}
      <h3 className="text-lg font-bold mb-1">1. Parallel Trends — Regression Test</h3>
      <p className="text-[13px] text-gray-500 mb-5 max-w-2xl leading-relaxed">
        Regresses rent on a treatment×pre-period interaction term. A significant interaction
        (p &lt; 0.05) would indicate that treated and control rents were already diverging
        before the ban — evidence against parallel trends. Neither definition rejects this test.
      </p>

      <div className="grid grid-cols-2 gap-6 mb-4">
        <InfoBlock
          title="Binary indicator"
          rows={[
            { label: 'Interaction coefficient',  value: `${ptB.interaction_coef.toFixed(2)} $/mo` },
            { label: 'Standard error',           value: `(${(ptB.p_value < 0.001 ? '< 0.001' : ptB.p_value.toFixed(4))})` },
            { label: 'p-value',                  value: ptB.p_value.toFixed(4) },
            {
              label: 'Significant at 5%?',
              value: ptB.significant ? 'Yes ✗' : 'No ✓',
              valueClass: ptB.significant ? 'text-maroon' : 'text-teal-600',
            },
            { label: 'Verdict', value: ptB.interpretation },
          ]}
        />
        <InfoBlock
          title="Threshold indicator"
          rows={[
            { label: 'Interaction coefficient',  value: `${ptT.interaction_coef.toFixed(2)} $/mo` },
            { label: 'Standard error',           value: `(${(ptT.p_value < 0.001 ? '< 0.001' : ptT.p_value.toFixed(4))})` },
            { label: 'p-value',                  value: ptT.p_value.toFixed(4) },
            {
              label: 'Significant at 5%?',
              value: ptT.significant ? 'Yes ✗' : 'No ✓',
              valueClass: ptT.significant ? 'text-maroon' : 'text-teal-600',
            },
            { label: 'Verdict', value: ptT.interpretation },
          ]}
        />
      </div>

      <div className="border border-gray-200 rounded-xl px-5 py-4 mb-8 grid grid-cols-2 gap-4">
        <div className="bg-teal-50 border border-teal-200/60 rounded-xl px-4 py-3">
          <p className="text-[12px] text-gray-700 leading-relaxed">
            <strong className="text-teal-700">✓ Formal test does not reject:</strong> The interaction
            term is not statistically significant (binary p = {ptB.p_value.toFixed(2)},
            threshold p = {ptT.p_value.toFixed(2)}). We cannot reject null parallel trends.
          </p>
        </div>
        <div className="bg-amber-50 border border-amber-200/60 rounded-xl px-4 py-3">
          <p className="text-[12px] text-gray-700 leading-relaxed">
            <strong className="text-amber-700">⚠ Visual evidence is imperfect:</strong> The
            full-panel and matched CS event studies show <strong>sizable pre-period deviations</strong>.
            Residualized CS (Models Spec ③) looks better near treatment but still not perfectly flat.
            Do not interpret this as &ldquo;parallel trends proved.&rdquo;
          </p>
        </div>
      </div>
      <div className="bg-gray-50 border border-gray-200 rounded-xl px-5 py-4 mb-8">
        <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">Correct framing for this evidence</p>
        <p className="text-[12px] text-gray-700 leading-relaxed">
          The formal regression test supports parallel trends (p &gt; 0.20). Visual event-study
          inspection shows non-trivial pre-period movement. Residualization of pre-trend differences
          partially addresses this but does not eliminate it. <strong>Recommended language: </strong>
          &ldquo;Parallel trends is plausible based on formal testing, but meaningful pre-period
          deviations remain in the event studies. Results should be interpreted with sensitivity
          to this limitation.&rdquo;
        </p>
      </div>

      {/* ── Honest pre-trends (TWFE pre-period coefficients) ── */}
      <h3 className="text-lg font-bold mb-1">2. Pre-period TWFE Coefficients — Visual Check</h3>
      <p className="text-[13px] text-gray-500 mb-5 max-w-2xl leading-relaxed">
        The event study plots show TWFE estimates for <em>each pre-ban period</em> separately.
        If parallel trends holds, pre-ban estimates should be near zero with no clear trend.
        A systematic drift in one direction before the ban is a warning sign.
      </p>

      <div className="grid grid-cols-2 gap-6 mb-4">
        <InfoBlock
          title="Binary — pre-period TWFE summary"
          rows={[
            { label: 'Pre-periods checked',       value: hpB.n_pre_periods.toString() },
            { label: 'Max |pre-period coef|',     value: `$${hpB.max_abs_twfe_coef_pre.toFixed(1)}` },
            { label: 'Sign restriction violated', value: hpB.violates_sign_restriction ? 'Yes ✗' : 'No ✓', valueClass: hpB.violates_sign_restriction ? 'text-maroon' : 'text-teal-600' },
          ]}
        />
        <InfoBlock
          title="Threshold — pre-period TWFE summary"
          rows={[
            { label: 'Pre-periods checked',       value: hpT.n_pre_periods.toString() },
            { label: 'Max |pre-period coef|',     value: `$${hpT.max_abs_twfe_coef_pre.toFixed(1)}` },
            { label: 'Sign restriction violated', value: hpT.violates_sign_restriction ? 'Yes ✗' : 'No ✓', valueClass: hpT.violates_sign_restriction ? 'text-maroon' : 'text-teal-600' },
          ]}
        />
      </div>

      <div className="border border-amber-200 bg-amber-50 rounded-xl px-5 py-4 mb-8">
        <p className="text-[11px] font-bold uppercase tracking-wider text-amber-700 mb-2">Honest assessment</p>
        <p className="text-[12px] text-gray-700 leading-relaxed">
          The pre-period coefficients do not show a monotone drift (sign restriction not violated),
          which is reassuring. However, the maximum pre-period coefficient is non-trivial:
          <strong> ${hpB.max_abs_twfe_coef_pre.toFixed(0)}/mo for binary</strong> and{' '}
          <strong>${hpT.max_abs_twfe_coef_pre.toFixed(0)}/mo for threshold</strong> — roughly half
          the full-panel ATT in each case. The pre-trends are not perfectly flat. This means
          parallel trends is <em>plausible</em> but not airtight. The residualized CS specification
          (Models tab, Spec ③) addresses this by removing linear pre-trends before estimation.
        </p>
      </div>

      <FigureSlot
        src="/data/binary/did_parallel_trends.png"
        alt="Pre-treatment rent trends — treated vs matched control"
        label="Pre-treatment average rent — treated vs never-treated (binary, matched sample)"
        className="mb-10"
      />

      {/* ── SUTVA ── */}
      <h3 className="text-lg font-bold mb-1">3. SUTVA — Spatial Spillover Tests</h3>
      <p className="text-[13px] text-gray-500 mb-5 max-w-2xl leading-relaxed">
        Two complementary tests check whether prohibitions in one tract spill over into
        neighboring tracts&apos; rents. If they do, our never-treated &ldquo;control&rdquo;
        tracts near treated ones are contaminated.
      </p>

      <div className="grid grid-cols-2 gap-5 mb-6">
        <div className="border border-gray-100 rounded-xl p-5">
          <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">Donut test</p>
          <p className="text-[12px] text-gray-600 leading-relaxed">
            Compares ATT estimates that <em>exclude</em> control tracts within a short geographic
            radius of treated tracts (the &ldquo;donut hole&rdquo;). If spillovers bias the
            estimate, excluding close neighbors should change the ATT meaningfully.
          </p>
        </div>
        <div className="border border-gray-100 rounded-xl p-5">
          <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">Dose-response test</p>
          <p className="text-[12px] text-gray-600 leading-relaxed">
            Checks whether the treatment effect is larger in tracts with a higher <em>density</em>
            of prohibited buildings. Under SUTVA, treated tracts with more prohibitions should
            not systematically differ in effect size from those with fewer.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6 mb-6">
        <FigureSlot src="/data/binary/sutva_donut.png"
          alt="SUTVA donut test — binary" label="Donut test — binary indicator" />
        <FigureSlot src="/data/binary/sutva_dose_response.png"
          alt="SUTVA dose-response — binary" label="Dose-response — binary indicator" />
      </div>

      <div className="grid grid-cols-2 gap-6 mb-10">
        <FigureSlot src="/data/threshold/sutva_donut.png"
          alt="SUTVA donut test — threshold" label="Donut test — threshold indicator" />
        <FigureSlot src="/data/threshold/sutva_dose_response.png"
          alt="SUTVA dose-response — threshold" label="Dose-response — threshold indicator" />
      </div>

      {/* ── Diagnostic ── */}
      <h3 className="text-lg font-bold mb-1">4. General Diagnostics</h3>
      <p className="text-[13px] text-gray-500 mb-5 max-w-2xl leading-relaxed">
        A broader set of diagnostic checks on the panel structure, coverage, and
        pre-treatment balance.
      </p>
      <div className="grid grid-cols-2 gap-6">
        <FigureSlot src="/data/binary/did_diagnostic_analysis.png"
          alt="DiD diagnostics — binary" label="Diagnostic summary — binary" />
        <FigureSlot src="/data/threshold/did_diagnostic_analysis.png"
          alt="DiD diagnostics — threshold" label="Diagnostic summary — threshold" />
      </div>
    </div>
  )
}
