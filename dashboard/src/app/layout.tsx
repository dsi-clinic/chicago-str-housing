import './globals.css'
import Hero from '@/components/Hero'
import TabNav from '@/components/TabNav'
import { loadSampleLineage } from '@/lib/data'

export const metadata = { title: 'Chicago STR Analysis · Andrés F. Camacho' }

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const lineage = loadSampleLineage('binary')
  const stageA  = lineage.find(s => s.stage_code === 'A')
  const stageC  = lineage.find(s => s.stage_code === 'C')
  const stageD  = lineage.find(s => s.stage_code === 'D')
  const stageF  = lineage.find(s => s.stage_code === 'F')

  const nPanel    = stageC?.n_tracts   ?? 842
  const nMonths   = stageC?.n_months   ?? 128
  const nTreated  = stageD?.treated    ?? 373
  const nMatched  = stageF?.n_tracts   ?? 556

  // matched controls = total matched minus matched treated
  const nMatchedControls = nMatched - (nTreated ?? 0)

  const pills = [
    { value: (stageA?.n_tracts ?? 1332).toLocaleString(), label: 'Chicago Tracts',    sub: 'all tracts, Cook Co.' },
    { value: nPanel.toLocaleString(),                      label: 'Rent-panel Tracts', sub: 'with ZORI coverage' },
    { value: nMonths.toLocaleString(),                     label: 'Panel Months',      sub: '2015 – 2022' },
    { value: (nTreated ?? 0).toLocaleString(),             label: 'Treated Tracts',    sub: 'binary, pre-match' },
    { value: nMatched.toLocaleString(),                    label: 'Analysis Sample',   sub: `${nTreated ?? 0}T + ${nMatchedControls}C` },
  ]

  return (
    <html lang="en">
      <body className="bg-white min-h-screen">
        <Hero pills={pills} />
        <TabNav />
        <main className="max-w-5xl mx-auto px-14 py-11">
          {children}
        </main>
      </body>
    </html>
  )
}
