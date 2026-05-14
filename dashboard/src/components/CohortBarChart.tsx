import { loadCohortStats } from '@/lib/data'

const W = 760
const H = 240
const PAD = { top: 16, right: 16, bottom: 72, left: 40 }
const CHART_W = W - PAD.left - PAD.right
const CHART_H = H - PAD.top  - PAD.bottom

type Dir = 'binary' | 'threshold'

export default function CohortBarChart({ dir = 'binary' }: { dir?: Dir }) {
  const cohorts = loadCohortStats(dir)
  if (cohorts.length === 0) return null

  const maxN = Math.max(...cohorts.map(c => c.n_tracts))
  const barW = Math.max(4, Math.floor(CHART_W / cohorts.length) - 2)

  const yScale = (n: number) => CHART_H - (n / maxN) * CHART_H

  // Y-axis ticks
  const yTicks = [0, Math.round(maxN * 0.25), Math.round(maxN * 0.5), Math.round(maxN * 0.75), maxN]

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="w-full"
      style={{ fontFamily: 'inherit' }}
      role="img"
      aria-label="Prohibition cohort sizes"
    >
      <g transform={`translate(${PAD.left},${PAD.top})`}>
        {/* Grid lines + Y axis */}
        {yTicks.map(t => (
          <g key={t}>
            <line
              x1={0} y1={yScale(t)}
              x2={CHART_W} y2={yScale(t)}
              stroke="#f0f0f0" strokeWidth={1}
            />
            <text x={-6} y={yScale(t) + 4} textAnchor="end"
              fontSize={9} fill="#aaa">
              {t}
            </text>
          </g>
        ))}

        {/* Bars */}
        {cohorts.map((c, i) => {
          const x = i * (CHART_W / cohorts.length) + (CHART_W / cohorts.length - barW) / 2
          const y = yScale(c.n_tracts)
          const bh = CHART_H - y
          return (
            <g key={c.first_prohibition_month}>
              <rect
                x={x} y={y} width={barW} height={bh}
                fill={dir === 'binary' ? '#8B0000' : '#0D9488'}
                opacity={0.75}
                rx={2}
              />
              {/* X label — show year only on Jan or first appearance of that year */}
              {(c.first_prohibition_month.endsWith('-01') ||
                c.first_prohibition_month.endsWith('-01-01') ||
                c.first_prohibition_month.slice(0, 4) !==
                  cohorts[i - 1]?.first_prohibition_month.slice(0, 4)) && (
                <text
                  x={x + barW / 2}
                  y={CHART_H + 14}
                  textAnchor="middle"
                  fontSize={9}
                  fill="#888"
                >
                  {c.first_prohibition_month.slice(0, 7)}
                </text>
              )}
            </g>
          )
        })}

        {/* Axes */}
        <line x1={0} y1={0} x2={0} y2={CHART_H} stroke="#e5e7eb" strokeWidth={1} />
        <line x1={0} y1={CHART_H} x2={CHART_W} y2={CHART_H} stroke="#e5e7eb" strokeWidth={1} />

        {/* Y-axis label */}
        <text
          transform={`translate(-30,${CHART_H / 2}) rotate(-90)`}
          textAnchor="middle"
          fontSize={9}
          fill="#aaa"
        >
          Tracts newly treated
        </text>
      </g>
    </svg>
  )
}
