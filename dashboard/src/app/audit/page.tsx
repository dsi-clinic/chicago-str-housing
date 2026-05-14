import FigureSlot from '@/components/FigureSlot'
import InfoBlock from '@/components/InfoBlock'
import StatTable from '@/components/StatTable'
import {
  loadSampleLineage,
  loadCovariateBalance,
  loadMatchingDiagnostics,
  loadCrosswalkDiagnostics,
} from '@/lib/data'

const COVARIATE_LABELS: Record<string, string> = {
  median_income:      'Median income',
  median_house_value: 'Median house value',
  baseline_rent:      'Baseline rent (ZORI)',
  pct_bachelor:       '% with bachelor degree',
  pct_rented:         '% renter-occupied',
  median_age:         'Median age',
  total_population:   'Total population',
}

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-lg font-bold text-gray-900 mb-1 mt-10 first:mt-0">{children}</h3>
  )
}

function Note({ children }: { children: React.ReactNode }) {
  return (
    <div className="border border-dashed border-amber-200 bg-amber-50/60 rounded-xl px-5 py-4 mt-4">
      <p className="text-[11px] font-bold uppercase tracking-wider text-amber-700 mb-2">Remaining limitation</p>
      <div className="text-[13px] text-gray-600 leading-relaxed">{children}</div>
    </div>
  )
}

function LovePlotNote() {
  return (
    <p className="text-[13px] text-gray-500 mb-5 max-w-2xl leading-relaxed">
      Each row is a matching feature. Grey circles show the standardized mean difference (SMD)
      between treated and <em>all</em> control tracts before matching; maroon diamonds show the
      same difference after k-NN selection. Closer to zero is better. The matching machinery is
      the same for both treatment definitions; only which tracts count as treated changes.
    </p>
  )
}

export default function AuditPage() {
  const lineageBinary   = loadSampleLineage('binary')
  const lineageThreshold = loadSampleLineage('threshold')
  const balance   = loadCovariateBalance('binary')
    .filter(b => b.covariate in COVARIATE_LABELS)
    .sort((a, b) => b.cohens_d - a.cohens_d)
  const matchDiagBinary = loadMatchingDiagnostics('binary')
  const matchDiagThreshold = loadMatchingDiagnostics('threshold')
  const cwDiag    = loadCrosswalkDiagnostics('binary')

  const lineageRows = lineageBinary
    .filter(s => s.n_tracts > 0)
    .map(s => [
      s.stage_code,
      s.n_tracts.toLocaleString(),
      s.delta !== null ? (s.delta < 0 ? `−${Math.abs(s.delta).toLocaleString()}` : '—') : '—',
      s.treated !== null ? s.treated.toLocaleString() : '—',
      s.never_treated !== null ? s.never_treated.toLocaleString() : '—',
      s.reason.length > 80 ? s.reason.slice(0, 80) + '…' : s.reason,
    ])

  const balanceRows = balance.map(b => [
    COVARIATE_LABELS[b.covariate] ?? b.covariate,
    `$${b.treated_mean.toFixed(0)}`,
    `$${b.control_mean.toFixed(0)}`,
    `${b.pct_diff.toFixed(1)}%`,
    b.cohens_d.toFixed(3),
    b.significant ? '✗ Yes' : '✓ No',
  ])

  return (
    <div className="max-w-4xl">
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">Methodology Audit</h2>
      <p className="text-[15px] text-gray-500 mb-8 max-w-2xl leading-relaxed">
        What changed in the most recent pipeline refactor, what the diagnostics say,
        and what it means for interpreting the estimates. Source:{' '}
        <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">docs/methodology-audit/</code>
      </p>

      <div className="grid grid-cols-3 gap-5 mb-10">
        <InfoBlock
          title="Why the rerun"
          rows={[
            { label: 'Old match', value: 'Slope only' },
            { label: 'Problem', value: 'Weak level balance + reuse' },
            { label: 'New match', value: 'Slope + avg pre-rent', valueClass: 'text-teal-600' },
            { label: 'Audit role', value: 'Explain the design change before results' },
          ]}
        />
        <InfoBlock
          title="Threshold rerun"
          rows={[
            { label: 'Matched sample', value: `${(lineageThreshold.find(s => s.stage_code === 'F')?.n_tracts ?? 0).toLocaleString()} tracts`, valueClass: 'text-teal-600' },
            { label: 'Matched controls', value: matchDiagThreshold.matched_controls.toLocaleString() },
            { label: 'Slope SMD after', value: matchDiagThreshold.smd_slope_after.toFixed(3) },
            { label: 'Rent SMD after', value: matchDiagThreshold.smd_rent_after.toFixed(3) },
            { label: 'Max reuse', value: matchDiagThreshold.control_reuse_max.toLocaleString() },
          ]}
        />
        <InfoBlock
          title="Binary rerun"
          rows={[
            { label: 'Matched sample', value: `${(lineageBinary.find(s => s.stage_code === 'F')?.n_tracts ?? 0).toLocaleString()} tracts`, valueClass: 'text-teal-600' },
            { label: 'Matched controls', value: matchDiagBinary.matched_controls.toLocaleString() },
            { label: 'Slope SMD after', value: matchDiagBinary.smd_slope_after.toFixed(3) },
            { label: 'Rent SMD after', value: matchDiagBinary.smd_rent_after.toFixed(3) },
            { label: 'Max reuse', value: matchDiagBinary.control_reuse_max.toLocaleString() },
          ]}
        />
      </div>

      <div className="border-l-4 border-maroon bg-maroon/5 rounded-r-xl px-6 py-5 mb-10">
        <p className="text-[10px] font-bold uppercase tracking-widest text-maroon mb-2">Rerun rationale</p>
        <p className="text-[14px] text-gray-700 leading-relaxed max-w-4xl">
          We reran the pipeline after the crosswalk and matching refactor because the first pass
          was too easy to criticise econometrically: slope-only matching did not balance rent
          levels well enough, and the control pool could be reused many times. The updated match
          uses standardized pre-treatment slope plus average pre-treatment rent, while the full-panel
          Callaway-Sant&apos;Anna estimate remains the headline result and matching stays in the
          robustness section.
        </p>
      </div>

      {/* ── 1. Crosswalk Refactor ── */}
      <SectionHeading>1. ZIP → Tract Crosswalk Refactor</SectionHeading>
      <p className="text-[14px] text-gray-500 mb-4 leading-relaxed max-w-2xl">
        The original crosswalk normalized intersection areas within ZIP codes, which is
        mechanically valid but not the natural weighting for a tract-level outcome. For
        tract-month rents, the more defensible quantity is how much of <em>tract i</em> lies
        in ZIP <em>z</em>, not the reverse. Areas are now computed in a projected CRS.
      </p>

      <div className="grid grid-cols-2 gap-5 mb-6">
        <InfoBlock
          title="What changed"
          rows={[
            { label: 'Old weight',     value: 'zip_area_share (zip-centric)' },
            { label: 'New weight',     value: 'tract_area_share (tract-centric)', valueClass: 'text-teal-600' },
            { label: 'Old CRS',        value: 'EPSG:4326 (degrees)' },
            { label: 'New CRS',        value: 'EPSG:3435 (projected)', valueClass: 'text-teal-600' },
            { label: 'Also computed',  value: 'tract_coverage_share + n_overlapping_zips' },
          ]}
        />
        <InfoBlock
          title="Crosswalk coverage summary"
          rows={[
            { label: 'ZIP codes in crosswalk',        value: cwDiag.n_zip_codes.toLocaleString() },
            { label: 'Tracts with crosswalk entry',   value: cwDiag.n_tracts.toLocaleString() },
            { label: 'Tracts ≥ 95% covered',          value: `${cwDiag.tracts_ge_95pct} (${(cwDiag.tracts_ge_95pct / cwDiag.n_tracts * 100).toFixed(0)}%)`, valueClass: 'text-teal-600' },
            { label: 'Tracts < 50% covered',          value: `${cwDiag.tracts_lt_50pct} (${(cwDiag.tracts_lt_50pct / cwDiag.n_tracts * 100).toFixed(0)}%)`, valueClass: 'text-amber-600' },
            { label: 'Avg ZIP–tract pairs per ZIP',   value: cwDiag.avg_tracts_per_zip.toFixed(1) },
          ]}
        />
      </div>

      <FigureSlot
        src="/data/binary/did_story_crosswalk_coverage.png"
        alt="ZIP to tract crosswalk coverage distribution"
        label="Tract coverage share — how much of each tract is inside a ZORI ZIP"
        className="mb-4"
      />

      <Note>
        The tract panel still depends on ZIP-level ZORI. The refactor improves the mapping
        weights and CRS, but does not eliminate the measurement-error problem of interpolating
        ZIP-level rents to tract boundaries.
      </Note>

      {/* ── 2. Sample Lineage ── */}
      <SectionHeading>2. Sample Construction Lineage</SectionHeading>
      <p className="text-[14px] text-gray-500 mb-4 leading-relaxed max-w-2xl">
        The full tract funnel from 1,332 Chicago tracts to the final matched sample.
        The two biggest drops are the crosswalk coverage filter and the matching step.
      </p>

      <StatTable
        className="mb-6"
        headers={['Stage', 'N Tracts', 'Drop', 'Treated', 'Never-Treated', 'Reason']}
        rows={lineageRows}
      />

      <FigureSlot
        src="/data/binary/did_story_sample_lineage.png"
        alt="Sample construction funnel"
        label="Sample funnel — stages A through G"
        className="mb-4"
      />

      {/* ── 3. Matching Refactor ── */}
      <SectionHeading>3. Trend-Matching Refactor</SectionHeading>
      <p className="text-[14px] text-gray-500 mb-4 leading-relaxed max-w-2xl">
        The original matching used only pre-treatment rent slope, which left balance on rent
        <em>levels</em> weak and made the control pool easier to criticise. The refactor
        matches on two standardized features: <code className="text-xs bg-gray-100 px-1 rounded">pre_trend_slope</code>{' '}
        and <code className="text-xs bg-gray-100 px-1 rounded">avg_pre_rent</code>.
        Diagnostics are now exported to CSV instead of being hidden.
      </p>

      <div className="grid grid-cols-2 gap-5 mb-6">
        <InfoBlock
          title="Matching diagnostics (threshold)"
          rows={[
            { label: 'Treated tracts matched',   value: matchDiagThreshold.matched_treated.toLocaleString() },
            { label: 'Distinct control tracts',  value: matchDiagThreshold.matched_controls.toLocaleString() },
            { label: 'Total matched pairs',      value: matchDiagThreshold.matched_pairs.toLocaleString() },
            { label: 'Mean match distance',      value: matchDiagThreshold.distance_mean.toFixed(3) },
            { label: 'p95 match distance',       value: matchDiagThreshold.distance_p95.toFixed(3) },
            { label: 'Mean control reuse',       value: matchDiagThreshold.control_reuse_mean.toFixed(1) },
            { label: 'Max control reuse',        value: matchDiagThreshold.control_reuse_max.toLocaleString() },
          ]}
        />
        <InfoBlock
          title="Matching diagnostics (binary)"
          rows={[
            { label: 'Treated tracts matched',   value: matchDiagBinary.matched_treated.toLocaleString() },
            { label: 'Distinct control tracts',  value: matchDiagBinary.matched_controls.toLocaleString() },
            { label: 'Total matched pairs',      value: matchDiagBinary.matched_pairs.toLocaleString() },
            { label: 'Mean match distance',      value: matchDiagBinary.distance_mean.toFixed(3) },
            { label: 'p95 match distance',       value: matchDiagBinary.distance_p95.toFixed(3) },
            { label: 'Mean control reuse',       value: matchDiagBinary.control_reuse_mean.toFixed(1) },
            { label: 'Max control reuse',        value: matchDiagBinary.control_reuse_max.toLocaleString() },
          ]}
        />
      </div>

      <div className="grid grid-cols-2 gap-5 mb-6">
        <InfoBlock
          title="Balance improvement (threshold)"
          rows={[
            { label: 'Rent slope SMD — before',  value: matchDiagThreshold.smd_slope_before.toFixed(3), valueClass: 'text-maroon' },
            { label: 'Rent slope SMD — after',   value: matchDiagThreshold.smd_slope_after.toFixed(3),  valueClass: 'text-teal-600' },
            { label: 'Avg rent SMD — before',    value: matchDiagThreshold.smd_rent_before.toFixed(3),  valueClass: 'text-maroon' },
            { label: 'Avg rent SMD — after',     value: matchDiagThreshold.smd_rent_after.toFixed(3),   valueClass: 'text-amber-600' },
            { label: 'Recommendation', value: 'Use as robustness, not primary ID' },
          ]}
        />
        <InfoBlock
          title="Balance improvement (binary)"
          rows={[
            { label: 'Rent slope SMD — before',  value: matchDiagBinary.smd_slope_before.toFixed(3), valueClass: 'text-maroon' },
            { label: 'Rent slope SMD — after',   value: matchDiagBinary.smd_slope_after.toFixed(3),  valueClass: 'text-teal-600' },
            { label: 'Avg rent SMD — before',    value: matchDiagBinary.smd_rent_before.toFixed(3),  valueClass: 'text-maroon' },
            { label: 'Avg rent SMD — after',     value: matchDiagBinary.smd_rent_after.toFixed(3),   valueClass: 'text-amber-600' },
            { label: 'Recommendation', value: 'Use as robustness, not primary ID' },
          ]}
        />
      </div>

      <LovePlotNote />

      <FigureSlot
        src="/data/binary/did_story_matching_love.png"
        alt="SMD before and after matching on pre-trend slope and average pre-rent"
        label="Balance on matching features — before and after k-NN matching (binary indicator)"
        className="mb-6"
      />

      <Note>
        No caliper was applied in this run. The code supports it (<code className="text-xs bg-white/70 px-1 rounded">caliper=None</code> by default),
        but it was not set. Nearest-neighbour matching with replacement allows heavy control reuse
        (max: {matchDiagBinary.control_reuse_max} binary, {matchDiagThreshold.control_reuse_max} threshold).
        Residual imbalance remains on both features after matching.
        This is a robustness restriction, not the primary identification strategy.
      </Note>

      {/* ── 4. Pre-treatment Balance ── */}
      <SectionHeading>4. Pre-treatment Covariate Balance (Before Matching)</SectionHeading>
      <p className="text-[14px] text-gray-500 mb-4 leading-relaxed max-w-2xl">
        All seven covariates are significantly imbalanced before matching. Treated tracts
        are higher-income, higher-education, and higher-rent. The education gap is largest
        (Cohen&apos;s d ≈ 1.08). This motivates matching but also limits how clean the
        comparison can get.
      </p>

      <StatTable
        className="mb-6"
        headers={['Covariate', 'Treated Mean', 'Control Mean', '% Diff', "Cohen's d", 'Significant']}
        rows={balanceRows}
      />
    </div>
  )
}
