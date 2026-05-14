import FigureSlot from '@/components/FigureSlot'
import InfoBlock from '@/components/InfoBlock'
import { loadParallelTrendsTest, loadHonestPretrends } from '@/lib/data'

export default function PretrendsPage() {
  const pt = loadParallelTrendsTest('binary')
  const hp = loadHonestPretrends('binary')

  return (
    <div>
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">
        Pre-trends &amp; Parallel Trends Assumption
      </h2>
      <p className="text-[15px] text-gray-500 mb-10 max-w-2xl leading-relaxed">
        Testing the core identifying assumption: that treated and never-treated tracts would have
        followed parallel rent trajectories absent the policy.
      </p>

      <div className="grid grid-cols-2 gap-6 mb-10">
        <InfoBlock
          title="Parallel Trends Regression Test"
          rows={[
            { label: 'Interaction coefficient', value: pt.interaction_coef.toFixed(3) },
            { label: 'p-value',                 value: pt.p_value.toFixed(4) },
            {
              label: 'Significant at 5%',
              value: pt.significant ? 'Yes ✗' : 'No ✓',
              valueClass: pt.significant ? 'text-maroon' : 'text-teal-600',
            },
            { label: 'Interpretation', value: pt.interpretation },
          ]}
        />
        <InfoBlock
          title="Honest Pre-trends (TWFE)"
          rows={[
            { label: 'Max |pre-period coef|',     value: hp.max_abs_twfe_coef_pre.toFixed(3) },
            { label: 'N pre-periods',             value: hp.n_pre_periods.toString() },
            {
              label: 'Sign restriction violated',
              value: hp.violates_sign_restriction ? 'Yes ✗' : 'No ✓',
              valueClass: hp.violates_sign_restriction ? 'text-maroon' : 'text-teal-600',
            },
          ]}
        />
      </div>

      <FigureSlot src="/data/binary/did_parallel_trends.png"
        alt="Pre-treatment rent trends" label="Pre-treatment rent trends — treated vs matched control" className="mb-8" />

      <div className="grid grid-cols-2 gap-6 mb-8">
        <FigureSlot src="/data/binary/sutva_donut.png"
          alt="SUTVA donut test — spatial spillovers" label="SUTVA donut test" />
        <FigureSlot src="/data/binary/sutva_dose_response.png"
          alt="SUTVA dose-response curve" label="SUTVA dose-response" />
      </div>

      <FigureSlot src="/data/binary/did_diagnostic_analysis.png"
        alt="DiD diagnostic plots" label="Diagnostic analysis" />
    </div>
  )
}
