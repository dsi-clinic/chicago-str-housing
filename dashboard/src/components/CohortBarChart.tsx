import { loadCohortStats } from '@/lib/data'

const W = 760
const H = 240
const PAD = { top: 16, right: 16, bottom: 52, left: 44 }
const CHART_W = W - PAD.left - PAD.right
const CHART_H = H - PAD.top  - PAD.bottom

type Dir = 'binary' | 'threshold'

export default function CohortBarChart({ dir = 'binary' }: { dir?: Dir }) {
  const cohorts = loadCohortStats(dir)
  if (cohorts.length === 0) return null

  const maxN = Math.max(...cohorts.map(c => c.n_tracts))
  const slotW = CHART_W / cohorts.length
  const barW  = Math.max(3, Math.floor(slotW * 0.7))

  const yScale = (n: number) => CHART_H - (n / maxN) * CHART_H

  // Nice round ticks
  const tickStep = maxN <= 20 ? 5 : maxN <= 50 ? 10 : maxN <= 100 ? 25 : 50
  const yTicks: number[] = []
  for (let t = 0; t <= maxN; t += tickStep) yTicks.push(t)
  if (yTicks[yTicks.length - 1] < maxN) yTicks.push(maxN)

  const barColor = dir === 'binary' ? '#8B0000' : '#0D9488'

  // Only label when the year changes
  const xLabels = cohorts.map((c, i) => {
    const year = c.first_prohibition_month.slice(0, 4)
    const prevYear = cohorts[i - 1]?.first_prohibition_month.slice(0, 4)
    return year !== prevYear ? { x: i, label: year } : null
  }).filter(Boolean) as { x: number; label: string }[]

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="w-full"
      style={{ fontFamily: 'inherit', display: 'block' }}
      role="img"
      aria-label="Prohibition cohort sizes"
    >
      <g transform={`translate(${PAD.left},${PAD.top})`}>

        {/* ── Grid lines (drawn first → behind bars) ── */}
        {yTicks.map(t => (
          <line
            key={`grid-${t}`}
            x1={0} y1={yScale(t)} x2={CHART_W} y2={yScale(t)}
            stroke="#f3f4f6" strokeWidth={1}
            shapeRendering="crispEdges"
          />
        ))}

        {/* ── Bars (drawn second → in front of grid) ── */}
        {cohorts.map((c, i) => {
          const x  = i * slotW + (slotW - barW) / 2
          const y  = yScale(c.n_tracts)
          const bh = CHART_H - y
          return (
            <rect
              key={c.first_prohibition_month}
              x={x} y={y} width={barW} height={bh}
              fill={barColor}
              opacity={0.80}
              rx={2}
            />
          )
        })}

        {/* ── X-axis labels (year only on change) ── */}
        {xLabels.map(({ x, label }) => (
          <text
            key={label}
            x={x * slotW + slotW / 2}
            y={CHART_H + 16}
            textAnchor="middle"
            fontSize={10}
            fill="#9ca3af"
          >
            {label}
          </text>
        ))}

        {/* ── Y-axis ticks + labels ── */}
        {yTicks.map(t => (
          <text
            key={`ytick-${t}`}
            x={-6} y={yScale(t) + 4}
            textAnchor="end"
            fontSize={9}
            fill="#d1d5db"
          >
            {t}
          </text>
        ))}

        {/* ── Axis lines ── */}
        <line x1={0} y1={0}        x2={0}        y2={CHART_H} stroke="#e5e7eb" strokeWidth={1} />
        <line x1={0} y1={CHART_H}  x2={CHART_W}  y2={CHART_H} stroke="#e5e7eb" strokeWidth={1} />

        {/* ── Y-axis label ── */}
        <text
          transform={`translate(-34,${CHART_H / 2}) rotate(-90)`}
          textAnchor="middle"
          fontSize={9}
          fill="#9ca3af"
        >
          tracts newly treated
        </text>

      </g>
    </svg>
  )
}
