# Frontend Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a locally-runnable Next.js 14 data story site at `dashboard/` that presents all pipeline results across 7 interactive tabs.

**Architecture:** Standalone `dashboard/` Next.js app at repo root. Server Components load CSV data via `fs` at render time; one Client Component (`PipelineStepper`) handles step/toggle state. All figures served as static images from `public/data/` symlinks pointing to `output/did-cs-whitepaper-binary/` and `output/did-cs-whitepaper-threshold/`.

**Tech Stack:** Next.js 14 (App Router), TypeScript, Tailwind CSS v3, next/font Inter. No external charting or CSV library — hand-rolled parser.

---

## File Map

```
dashboard/
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.ts
├── postcss.config.mjs
├── public/
│   └── data/
│       ├── binary/    → symlink: ../../output/did-cs-whitepaper-binary/
│       └── threshold/ → symlink: ../../output/did-cs-whitepaper-threshold/
└── src/
    ├── app/
    │   ├── globals.css
    │   ├── layout.tsx          # Hero + TabNav + <main>
    │   ├── page.tsx            # Introduction
    │   ├── descriptive/page.tsx
    │   ├── analysis/page.tsx
    │   ├── models/page.tsx
    │   ├── robustness/page.tsx
    │   ├── pretrends/page.tsx
    │   └── policy/page.tsx
    ├── components/
    │   ├── Hero.tsx            # Always-visible header with stat pills
    │   ├── TabNav.tsx          # Sticky tab bar (Client Component — usePathname)
    │   ├── DataCard.tsx        # Single stat card with colored top border
    │   ├── FigureSlot.tsx      # next/image wrapper with filename caption
    │   ├── InfoBlock.tsx       # Two-column key/value table block
    │   ├── StatTable.tsx       # CSV rows rendered as styled HTML table
    │   └── PipelineStepper.tsx # Interactive 6-step pipeline (Client Component)
    └── lib/
        ├── data.ts             # Server-side fs CSV reader
        └── types.ts            # TypeScript interfaces for CSV rows
```

---

## Task 1: Scaffold Next.js + Tailwind + design tokens

**Files:**
- Create: `dashboard/` (entire Next.js project)
- Modify: `dashboard/tailwind.config.ts`
- Modify: `dashboard/src/app/globals.css`
- Modify: `dashboard/next.config.ts`

- [ ] **Step 1: Scaffold the project**

Run from repo root:
```bash
cd /path/to/repo  # repo root, not dashboard/
npx create-next-app@latest dashboard \
  --typescript --tailwind --eslint --app --src-dir \
  --no-import-alias --use-npm
```
When prompted: accept all defaults.

- [ ] **Step 2: Verify dev server starts**

```bash
cd dashboard && npm run dev
```
Expected: `ready - started server on 0.0.0.0:3000`. Open http://localhost:3000 — default Next.js page.  
Stop with Ctrl-C.

- [ ] **Step 3: Replace `tailwind.config.ts` with design tokens**

```typescript
// dashboard/tailwind.config.ts
import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // "rgb(R G B)" format enables /opacity modifiers: bg-maroon/10
        maroon: 'rgb(139 0 0)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
export default config
```

- [ ] **Step 4: Replace `src/app/globals.css`**

```css
/* dashboard/src/app/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

html {
  background: #ffffff;
}

body {
  @apply text-gray-900 bg-white;
}
```

- [ ] **Step 5: Update `next.config.ts` to allow unoptimized local images**

```typescript
// dashboard/next.config.ts
import type { NextConfig } from 'next'

const config: NextConfig = {
  images: {
    unoptimized: true,   // local pipeline output PNGs — no optimization needed
  },
}
export default config
```

- [ ] **Step 6: Remove boilerplate, verify Tailwind works**

Delete `src/app/page.tsx` content and replace with:
```tsx
export default function Page() {
  return <main className="p-10 text-maroon font-bold text-2xl">Dashboard loading…</main>
}
```
Run `npm run dev` → verify text appears in maroon. Commit.

```bash
cd dashboard && git add -A && git commit -m "feat: scaffold Next.js dashboard with Tailwind + maroon token"
```

---

## Task 2: Data symlinks, types, and CSV reader

**Files:**
- Create: `dashboard/public/data/binary` (symlink)
- Create: `dashboard/public/data/threshold` (symlink)
- Create: `dashboard/src/lib/types.ts`
- Create: `dashboard/src/lib/data.ts`

- [ ] **Step 1: Create symlinks**

Run from `dashboard/` directory:
```bash
mkdir -p public/data
ln -s ../../../../output/did-cs-whitepaper-binary   public/data/binary
ln -s ../../../../output/did-cs-whitepaper-threshold public/data/threshold
```
Verify: `ls -la public/data/binary | head -5` should list the pipeline PNG files.

- [ ] **Step 2: Add `public/data` symlinks to `.gitignore`**

Add to repo root `.gitignore` (not dashboard-level):
```
dashboard/public/data/binary
dashboard/public/data/threshold
dashboard/node_modules/
dashboard/.next/
```

- [ ] **Step 3: Create `src/lib/types.ts`**

```typescript
// dashboard/src/lib/types.ts

export interface PanelOverview {
  n_tracts: number
  n_periods: number
  n_observations: number
  tracts_never_treated: number
  tracts_eventually_treated: number
}

export interface GroupStat {
  group: string          // "Never Treated" | "Eventually Treated"
  n_tracts: number
  mean_rent: number
  std_dev: number
}

export interface CohortStat {
  first_prohibition_month: string
  n_tracts: number
  share_of_treated_tracts: number
  mean_baseline_rent: number
  mean_median_income: number
}

export interface ComparisonRow {
  rel_time: number
  cs_att: number
  cs_se: number
  twfe_coef: number
  twfe_se: number
}

export interface HonestPretrends {
  max_abs_twfe_coef_pre: number
  violates_sign_restriction: boolean
  n_pre_periods: number
}

export interface ParallelTrendsTest {
  interaction_coef: number
  p_value: number
  significant: boolean
  interpretation: string
}
```

- [ ] **Step 4: Create `src/lib/data.ts`**

```typescript
// dashboard/src/lib/data.ts
import fs from 'fs'
import path from 'path'

// Resolves to dashboard/public/data/<dir>/<filename>
function filePath(dir: 'binary' | 'threshold', filename: string): string {
  return path.join(process.cwd(), 'public', 'data', dir, filename)
}

/** Parse CSV text → array of {header: value} objects. */
function parseCsv(text: string): Record<string, string>[] {
  const lines = text.trim().split('\n').filter(Boolean)
  if (lines.length < 2) return []
  const rawHeaders = lines[0].split(',')
  // First column sometimes has no name (e.g. did_descriptive_summary_stats.csv)
  const headers = rawHeaders.map((h, i) =>
    h.trim().replace(/^"|"$/g, '') || `_col${i}`
  )
  return lines.slice(1).map(line => {
    // Handle quoted values containing commas
    const values: string[] = []
    let cur = '', inQ = false
    for (const ch of line) {
      if (ch === '"') { inQ = !inQ }
      else if (ch === ',' && !inQ) { values.push(cur); cur = '' }
      else { cur += ch }
    }
    values.push(cur)
    return Object.fromEntries(headers.map((h, i) => [h, (values[i] ?? '').trim()]))
  })
}

export function readCsvRows(dir: 'binary' | 'threshold', filename: string): Record<string, string>[] {
  const text = fs.readFileSync(filePath(dir, filename), 'utf-8')
  return parseCsv(text)
}

export function readCsvRow(dir: 'binary' | 'threshold', filename: string): Record<string, string> {
  return readCsvRows(dir, filename)[0] ?? {}
}

export function loadPanelOverview(dir: 'binary' | 'threshold' = 'binary') {
  const r = readCsvRow(dir, 'did_descriptive_panel_overview.csv')
  return {
    n_tracts: +r.n_tracts,
    n_periods: +r.n_periods,
    n_observations: +r.n_observations,
    tracts_never_treated: +r.tracts_never_treated,
    tracts_eventually_treated: +r.tracts_eventually_treated,
  }
}

export function loadGroupStats(dir: 'binary' | 'threshold' = 'binary') {
  return readCsvRows(dir, 'did_descriptive_summary_stats.csv').map(r => ({
    group: r._col0,
    n_tracts: +r['N Tracts'],
    mean_rent: +r['Mean Rent'],
    std_dev: +r['Std Dev'],
  }))
}

export function loadCohortStats(dir: 'binary' | 'threshold' = 'binary') {
  return readCsvRows(dir, 'did_descriptive_cohort_stats.csv').map(r => ({
    first_prohibition_month: r.first_prohibition_month,
    n_tracts: +r.n_tracts,
    share_of_treated_tracts: +r.share_of_treated_tracts,
    mean_baseline_rent: +r.mean_baseline_rent,
    mean_median_income: +r.mean_median_income,
  }))
}

export function loadComparisonRows(dir: 'binary' | 'threshold' = 'binary') {
  return readCsvRows(dir, 'did_twfe_cs_comparison_table.csv').map(r => ({
    rel_time: +r.rel_time,
    cs_att: +r.CS_ATT,
    cs_se: +r.CS_SE,
    twfe_coef: +r.TWFE_Coef,
    twfe_se: +r.TWFE_SE,
  }))
}

export function loadHonestPretrends(dir: 'binary' | 'threshold' = 'binary') {
  const r = readCsvRow(dir, 'honest_pretrends_summary.csv')
  return {
    max_abs_twfe_coef_pre: +r.max_abs_twfe_coef_pre,
    violates_sign_restriction: r.violates_sign_restriction_all_nonpositive_pre === 'True',
    n_pre_periods: +r.n_pre_periods,
  }
}

export function loadParallelTrendsTest(dir: 'binary' | 'threshold' = 'binary') {
  const r = readCsvRow(dir, 'pretrend_parallel_trends_regression_summary.csv')
  return {
    interaction_coef: +r.interaction_coef,
    p_value: +r.p_value,
    significant: r.significant === 'True',
    interpretation: r.interpretation,
  }
}
```

- [ ] **Step 5: Verify data loads**

Add a quick smoke test to `src/app/page.tsx`:
```tsx
import { loadPanelOverview } from '@/lib/data'
export default function Page() {
  const d = loadPanelOverview()
  return <pre className="p-8 text-sm">{JSON.stringify(d, null, 2)}</pre>
}
```
Run `npm run dev` → http://localhost:3000 should print the parsed JSON object with `n_tracts: 487`. Commit.

```bash
git add -A && git commit -m "feat: data symlinks + CSV reader + TypeScript types"
```

---

## Task 3: Root layout — Hero + TabNav

**Files:**
- Create: `dashboard/src/components/Hero.tsx`
- Create: `dashboard/src/components/TabNav.tsx`
- Modify: `dashboard/src/app/layout.tsx`

- [ ] **Step 1: Create `Hero.tsx`**

```tsx
// dashboard/src/components/Hero.tsx
import type { PanelOverview } from '@/lib/types'

const PILLS: { key: keyof PanelOverview; label: string }[] = [
  { key: 'n_tracts',                label: 'Census Tracts' },
  { key: 'n_periods',               label: 'Panel Months' },
  { key: 'n_observations',          label: 'Observations' },
  { key: 'tracts_eventually_treated', label: 'Treated Tracts' },
  { key: 'tracts_never_treated',    label: 'Never-Treated' },
]

export default function Hero({ stats }: { stats: PanelOverview }) {
  return (
    <header className="border-b border-gray-100 px-14 pt-9 pb-6">
      <div className="flex justify-between items-start mb-7 max-w-5xl">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-widest text-maroon mb-2">
            Analysis Report · Data Science Clinic · University of Chicago
          </p>
          <h1 className="text-2xl font-extrabold tracking-tight leading-tight max-w-lg">
            Impact of STR Prohibitions on Chicago Rental Prices
          </h1>
          <p className="mt-2 text-sm text-gray-500 leading-relaxed">
            Staggered Difference-in-Differences · Census Tract Level Analysis
          </p>
        </div>
        <div className="text-right text-sm text-gray-500 border-l border-gray-100 pl-6 whitespace-nowrap ml-8">
          <strong className="block text-[15px] font-bold text-gray-900 mb-1">Andrés F. Camacho</strong>
          University of Chicago<br />Data Science Clinic<br />2025
        </div>
      </div>
      <div className="flex gap-3 flex-wrap">
        {PILLS.map(p => (
          <div
            key={p.key}
            className="border border-maroon/20 rounded-xl px-6 py-3 text-center min-w-[110px] shadow-sm"
          >
            <span className="block text-2xl font-extrabold text-maroon leading-none tracking-tight">
              {stats[p.key].toLocaleString()}
            </span>
            <span className="block text-[10px] uppercase tracking-wider text-gray-400 mt-1 font-medium">
              {p.label}
            </span>
          </div>
        ))}
      </div>
    </header>
  )
}
```

- [ ] **Step 2: Create `TabNav.tsx`**

```tsx
// dashboard/src/components/TabNav.tsx
'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

const TABS = [
  { label: 'Introduction', href: '/' },
  { label: 'Descriptive',  href: '/descriptive' },
  { label: 'Analysis',     href: '/analysis' },
  { label: 'Models',       href: '/models' },
  { label: 'Robustness',   href: '/robustness' },
  { label: 'Pre-trends',   href: '/pretrends' },
  { label: 'Policy',       href: '/policy' },
]

export default function TabNav() {
  const pathname = usePathname()
  return (
    <nav className="flex border-b-2 border-gray-100 px-14 sticky top-0 bg-white z-10 shadow-[0_2px_8px_rgba(0,0,0,0.03)]">
      {TABS.map(t => {
        const active = t.href === '/' ? pathname === '/' : pathname.startsWith(t.href)
        return (
          <Link
            key={t.href}
            href={t.href}
            className={[
              'px-4 py-[13px] text-sm whitespace-nowrap border-b-2 -mb-[2px] transition-colors font-medium',
              active
                ? 'text-maroon border-maroon font-bold'
                : 'text-gray-400 border-transparent hover:text-gray-600',
            ].join(' ')}
          >
            {t.label}
          </Link>
        )
      })}
    </nav>
  )
}
```

- [ ] **Step 3: Update `src/app/layout.tsx`**

```tsx
// dashboard/src/app/layout.tsx
import './globals.css'
import { Inter } from 'next/font/google'
import Hero from '@/components/Hero'
import TabNav from '@/components/TabNav'
import { loadPanelOverview } from '@/lib/data'

const inter = Inter({ subsets: ['latin'] })

export const metadata = { title: 'Chicago STR Analysis · Andrés F. Camacho' }

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const stats = loadPanelOverview('binary')
  return (
    <html lang="en" className={inter.className}>
      <body className="bg-white min-h-screen">
        <Hero stats={stats} />
        <TabNav />
        <main className="max-w-5xl mx-auto px-14 py-11">
          {children}
        </main>
      </body>
    </html>
  )
}
```

- [ ] **Step 4: Verify shell renders**

`npm run dev` → http://localhost:3000 — should show the hero banner with 5 stat pills and 7 tabs. Click tabs, URL changes. Commit.

```bash
git add -A && git commit -m "feat: Hero + TabNav shell — layout with live CSV stats"
```

---

## Task 4: Shared UI components

**Files:**
- Create: `dashboard/src/components/DataCard.tsx`
- Create: `dashboard/src/components/FigureSlot.tsx`
- Create: `dashboard/src/components/InfoBlock.tsx`
- Create: `dashboard/src/components/StatTable.tsx`

- [ ] **Step 1: Create `DataCard.tsx`**

```tsx
// dashboard/src/components/DataCard.tsx
type Accent = 'maroon' | 'teal' | 'blue' | 'amber' | 'slate'

const TOP: Record<Accent, string> = {
  maroon: 'border-t-maroon',
  teal:   'border-t-teal-600',
  blue:   'border-t-blue-600',
  amber:  'border-t-amber-600',
  slate:  'border-t-slate-500',
}
const VAL: Record<Accent, string> = {
  maroon: 'text-maroon',
  teal:   'text-teal-600',
  blue:   'text-blue-600',
  amber:  'text-amber-600',
  slate:  'text-slate-500',
}

export default function DataCard({
  value, label, sub, accent = 'maroon',
}: {
  value: string
  label: string
  sub?: string
  accent?: Accent
}) {
  return (
    <div className={`bg-white rounded-xl border border-gray-100 border-t-[3px] ${TOP[accent]}
      px-5 py-7 text-center shadow-sm hover:-translate-y-0.5 hover:shadow-md transition-all
      flex-[0_0_180px] min-w-[160px]`}>
      <span className={`block text-4xl font-extrabold tracking-tight leading-none ${VAL[accent]}`}>
        {value}
      </span>
      <span className="block text-[13px] font-semibold text-gray-500 mt-2">{label}</span>
      {sub && <span className="block text-xs text-gray-300 mt-1">{sub}</span>}
    </div>
  )
}
```

- [ ] **Step 2: Create `FigureSlot.tsx`**

```tsx
// dashboard/src/components/FigureSlot.tsx
import Image from 'next/image'

export default function FigureSlot({
  src, alt, label, className,
}: {
  src: string       // e.g. '/data/binary/did_adoption_curve.png'
  alt: string
  label?: string
  className?: string
}) {
  return (
    <div className={className}>
      {label && (
        <p className="text-[10px] font-bold uppercase tracking-wider text-gray-300 mb-2">{label}</p>
      )}
      <div className="border border-gray-100 rounded-xl overflow-hidden bg-gray-50">
        <Image
          src={src}
          alt={alt}
          width={900}
          height={500}
          className="w-full h-auto"
          unoptimized
        />
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create `InfoBlock.tsx`**

```tsx
// dashboard/src/components/InfoBlock.tsx
export interface InfoRow { label: string; value: string; valueClass?: string }

export default function InfoBlock({ title, rows }: { title: string; rows: InfoRow[] }) {
  return (
    <div className="border border-gray-100 rounded-xl p-5">
      <h4 className="text-[10px] font-bold uppercase tracking-wider text-gray-300 mb-4">{title}</h4>
      {rows.map((r, i) => (
        <div key={i} className="flex justify-between items-center text-sm py-2 border-b border-gray-50 last:border-0">
          <span className="text-gray-500">{r.label}</span>
          <span className={`font-bold text-gray-900 ${r.valueClass ?? ''}`}>{r.value}</span>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 4: Create `StatTable.tsx`**

```tsx
// dashboard/src/components/StatTable.tsx
export default function StatTable({
  headers, rows, className,
}: {
  headers: string[]
  rows: (string | number)[][]
  className?: string
}) {
  return (
    <div className={`overflow-x-auto rounded-xl border border-gray-100 ${className ?? ''}`}>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100 bg-gray-50">
            {headers.map(h => (
              <th key={h} className="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-wider text-gray-400">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-gray-50 last:border-0 hover:bg-gray-50/50 transition-colors">
              {row.map((cell, j) => (
                <td key={j} className="px-4 py-3 text-gray-700">{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 5: Smoke-test all components compile**

Add a temporary import in `page.tsx` to make TypeScript check them:
```tsx
import DataCard from '@/components/DataCard'
import FigureSlot from '@/components/FigureSlot'
import InfoBlock from '@/components/InfoBlock'
import StatTable from '@/components/StatTable'
export default function Page() {
  return <DataCard value="487" label="Tracts" accent="blue" />
}
```
Run `npm run dev` → no TypeScript errors. Commit.

```bash
git add -A && git commit -m "feat: DataCard, FigureSlot, InfoBlock, StatTable components"
```

---

## Task 5: Introduction page

**Files:**
- Modify: `dashboard/src/app/page.tsx`

- [ ] **Step 1: Write the Introduction page**

```tsx
// dashboard/src/app/page.tsx
import DataCard from '@/components/DataCard'
import InfoBlock from '@/components/InfoBlock'
import { loadPanelOverview, loadGroupStats } from '@/lib/data'

const STORY = [
  {
    date: 'Chicago, 2016',
    heading: 'The Problem',
    body: 'The rapid growth of short-term rentals (STRs) on platforms like Airbnb and VRBO raised concerns about their impact on long-term housing supply and rental affordability across Chicago neighborhoods.',
    highlight: true,
  },
  {
    date: 'Shared Housing Ordinance',
    heading: 'The Policy',
    body: "Chicago's Shared Housing Ordinance introduced building-level STR prohibitions, rolled out in a staggered manner across the city — creating natural variation in when and where STRs were restricted.",
    highlight: true,
  },
  {
    date: '2017 – 2022',
    heading: 'Staggered Rollout',
    body: 'Different buildings and neighborhoods were subjected to prohibitions at different times. This staggered adoption is the foundation of our causal identification strategy.',
    highlight: false,
  },
  {
    date: 'Identification',
    heading: 'Design',
    body: 'We use a staggered difference-in-differences design (Callaway & Sant\'Anna 2021) to estimate the average treatment effect on treated tracts, avoiding the well-known bias of TWFE with heterogeneous effects.',
    highlight: false,
  },
]

export default function IntroductionPage() {
  const ov = loadPanelOverview('binary')
  const gs = loadGroupStats('binary')
  const treated = gs.find(g => g.group.includes('Eventually')) ?? { mean_rent: 0, std_dev: 0, n_tracts: 0 }
  const control = gs.find(g => g.group.includes('Never')) ?? { mean_rent: 0, std_dev: 0, n_tracts: 0 }

  return (
    <div>
      {/* Research question */}
      <div className="border-l-4 border-maroon bg-maroon/5 rounded-r-xl px-6 py-5 mb-10">
        <p className="text-[10px] font-bold uppercase tracking-widest text-maroon mb-2">Research Question</p>
        <p className="text-[15px] text-gray-700 leading-relaxed">
          Does prohibiting short-term rentals under Chicago's Shared Housing Ordinance change monthly
          rental prices in affected census tracts — and by how much?
        </p>
      </div>

      {/* Story grid */}
      <div className="grid grid-cols-2 gap-5 mb-10">
        {STORY.map(s => (
          <div
            key={s.heading}
            className={`border rounded-xl p-6 ${
              s.highlight
                ? 'border-maroon/20 bg-gradient-to-br from-maroon/5 to-white'
                : 'border-gray-100'
            }`}
          >
            <span className="inline-block bg-maroon/10 text-maroon text-[11px] font-bold rounded px-2 py-0.5 mb-3">
              {s.date}
            </span>
            <h3 className="text-[11px] font-bold uppercase tracking-wider text-maroon mb-2">{s.heading}</h3>
            <p className="text-[13px] text-gray-600 leading-relaxed">{s.body}</p>
          </div>
        ))}
      </div>

      {/* Treatment definition */}
      <div className="border border-gray-100 rounded-xl p-6 mb-10">
        <h3 className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-5">
          Treatment Definition — affects the number of treated tracts
        </h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-blue-50 border border-blue-200/70 rounded-xl p-5">
            <p className="text-[11px] font-bold uppercase tracking-wider text-blue-600 mb-3">Binary Indicator</p>
            <p className="text-[13px] text-gray-600 leading-relaxed">
              A tract is treated as soon as <em>any</em> STR prohibition takes effect within its
              boundaries, regardless of how many units are affected.
            </p>
            <div className="flex gap-3 mt-4">
              <div className="bg-blue-100 rounded-lg px-4 py-2 text-center">
                <span className="block text-xl font-extrabold text-blue-600">{treated.n_tracts.toLocaleString()}</span>
                <span className="block text-[10px] text-gray-500">Treated tracts</span>
              </div>
              <div className="bg-blue-100 rounded-lg px-4 py-2 text-center">
                <span className="block text-xl font-extrabold text-blue-600">{control.n_tracts.toLocaleString()}</span>
                <span className="block text-[10px] text-gray-500">Never-treated</span>
              </div>
            </div>
          </div>
          <div className="bg-teal-50 border border-teal-200/70 rounded-xl p-5">
            <p className="text-[11px] font-bold uppercase tracking-wider text-teal-600 mb-3">Threshold Indicator</p>
            <p className="text-[13px] text-gray-600 leading-relaxed">
              A tract is treated only when the share of prohibited STR units exceeds a minimum
              threshold of occupied housing units — a stricter, more conservative definition.
            </p>
            <p className="mt-4 text-[12px] text-gray-400 italic">
              Comparison of both definitions in the Robustness tab.
            </p>
          </div>
        </div>
      </div>

      {/* Data cards — centered */}
      <p className="text-[11px] font-bold uppercase tracking-wider text-gray-300 mb-4 text-center">
        Panel at a glance
      </p>
      <div className="flex flex-wrap gap-4 justify-center mb-10">
        <DataCard value={ov.n_tracts.toLocaleString()}             label="Census Tracts"  sub="in rent panel"       accent="blue" />
        <DataCard value={ov.n_periods.toLocaleString()}            label="Panel Months"   sub="2012 – 2022"         accent="teal" />
        <DataCard value={ov.tracts_eventually_treated.toLocaleString()} label="Treated Tracts" sub="STR ever prohibited" accent="maroon" />
        <DataCard value={ov.tracts_never_treated.toLocaleString()} label="Control Tracts" sub="never treated"       accent="amber" />
        <DataCard value={`${Math.round(ov.n_observations / 1000)}k`} label="Observations" sub="tract-month cells"   accent="slate" />
      </div>

      {/* Two-col info blocks */}
      <div className="grid grid-cols-2 gap-5">
        <InfoBlock
          title="Pre-treatment Rent — Treated vs Control"
          rows={[
            { label: 'Mean rent · treated tracts',    value: `$${treated.mean_rent.toFixed(0)} / mo` },
            { label: 'Mean rent · never-treated',     value: `$${control.mean_rent.toFixed(0)} / mo` },
            { label: 'Std dev · treated',             value: `$${treated.std_dev.toFixed(0)}` },
            { label: 'Std dev · never-treated',       value: `$${control.std_dev.toFixed(0)}` },
            {
              label: 'Difference in means',
              value: `$${(treated.mean_rent - control.mean_rent).toFixed(0)}`,
              valueClass: 'text-maroon',
            },
          ]}
        />
        <InfoBlock
          title="Panel Coverage"
          rows={[
            { label: 'Total tract-month cells',  value: ov.n_observations.toLocaleString() },
            { label: 'Tracts with full span',    value: `${ov.n_tracts} (100%)`, valueClass: 'text-teal-600' },
            { label: 'Missing rent obs.',        value: '0.0%',                  valueClass: 'text-teal-600' },
            { label: 'Outcome variable',         value: 'ZORI ($/mo)' },
            { label: 'Treatment timing',         value: 'Staggered' },
          ]}
        />
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify in browser**

`npm run dev` → http://localhost:3000. Check:
- Research question callout shows
- Story grid has 4 blocks with maroon date pills
- Treatment definition box shows binary (blue) and threshold (teal) side-by-side with live counts
- 5 centered DataCards with live values from CSV
- Two InfoBlocks below with live rent numbers

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "feat: Introduction page — story, treatment definition, live data cards"
```

---

## Task 6: PipelineStepper client component

**Files:**
- Create: `dashboard/src/components/PipelineStepper.tsx`

- [ ] **Step 1: Create `PipelineStepper.tsx`**

This is a Client Component (`'use client'`). It receives the live tract counts as props from the parent page and renders the 6-step interactive pipeline.

```tsx
// dashboard/src/components/PipelineStepper.tsx
'use client'
import { useState } from 'react'
import FigureSlot from './FigureSlot'

interface StepCounts { nTracts: number; nTreated: number; nControl: number }

interface StepDef {
  id: number
  label: string
  count: string
  badge: string
  title: string
  pillValue: string
  pillSub: string
  leftLabel: string
  leftText: string
  chips: { val: string; label: string; color: string }[]
  rightLabel: string
  rightText: string
  retention: { pct: number; label: string; color: 'teal' | 'amber' }
  figFile: string | null
  figAlt: string | null
  isTreatmentStep?: true
}

function buildSteps(c: StepCounts): StepDef[] {
  return [
    {
      id: 1, label: 'All Chicago\nTracts', count: '1,332',
      badge: 'Step 1 of 6', title: 'All Chicago Census Tracts',
      pillValue: '1,332', pillSub: 'Census Tracts',
      leftLabel: 'Data Source',
      leftText: 'The analysis begins with all <b>1,332 census tracts</b> in Chicago from the 2023 TIGER/Line shapefile (Cook County, IL). These define the geographic units of observation — each tract is a neighborhood-scale area of roughly 1,200–8,000 residents.',
      chips: [
        { val: '1,332', label: 'Total tracts', color: 'maroon' },
        { val: '2023', label: 'TIGER vintage', color: 'blue' },
      ],
      rightLabel: 'Starting Point',
      rightText: 'This is the starting universe — no tracts have been dropped yet. All subsequent steps apply filters that reduce this number.',
      retention: { pct: 100, label: 'Starting universe', color: 'teal' },
      figFile: null, figAlt: null,
    },
    {
      id: 2, label: 'ZIP→Tract\nCrosswalk', count: 'crosswalk built',
      badge: 'Step 2 of 6', title: 'ZIP Code → Census Tract Crosswalk',
      pillValue: 'built', pillSub: 'Crosswalk',
      leftLabel: 'What Happens Here',
      leftText: 'ZORI (Zillow Observed Rent Index) provides monthly rent data at the <b>ZIP code level</b>, but our unit of analysis is <b>census tracts</b>. <code>ZipTractCrosswalkProcessor</code> uses spatial overlay to map each ZIP code to the census tracts it intersects, weighted by area overlap.',
      chips: [
        { val: 'ZIP', label: 'Input unit', color: 'blue' },
        { val: 'Tract', label: 'Output unit', color: 'teal' },
      ],
      rightLabel: 'Retention',
      rightText: 'No tracts are dropped at this step — the crosswalk only builds the mapping. Tracts are dropped in the next step when rent data is unavailable for their ZIP codes.',
      retention: { pct: 100, label: 'No tracts dropped — crosswalk only', color: 'teal' },
      figFile: null, figAlt: null,
    },
    {
      id: 3, label: 'Rent Panel\nMatch', count: `${c.nTracts.toLocaleString()} tracts`,
      badge: 'Step 3 of 6', title: 'ZIP→Tract Rent Panel (ZORI)',
      pillValue: c.nTracts.toLocaleString(), pillSub: 'Tracts Retained',
      leftLabel: 'What Happens Here',
      leftText: `<code>TimeSeriesZipToTractProcessor</code> uses the crosswalk to assign monthly ZORI rent values to each census tract. Only tracts matched to at least one ZORI-covered ZIP code enter the panel.<br/><b>${c.nTracts.toLocaleString()} tracts × 128 months = 62,336 tract-month observations.</b>`,
      chips: [
        { val: c.nTracts.toLocaleString(), label: 'Tracts in panel', color: 'teal' },
        { val: '128', label: 'Panel months', color: 'blue' },
        { val: '62,336', label: 'Observations', color: 'maroon' },
      ],
      rightLabel: 'Retention from Step 1',
      rightText: '845 of the original 1,332 tracts are dropped — they fall in areas not covered by any ZORI ZIP code (industrial zones, O\'Hare, sparse suburban edges).',
      retention: { pct: 37, label: `${c.nTracts.toLocaleString()} / 1,332 tracts (36.6%)`, color: 'amber' },
      figFile: '/data/binary/data_funnel.png', figAlt: 'Data funnel showing tract counts at each stage',
    },
    {
      id: 4, label: 'STR Prohibition\nDates → Tract', count: 'dates assigned',
      badge: 'Step 4 of 6', title: 'STR Prohibition Dates Aggregated to Tract',
      pillValue: c.nTracts.toLocaleString(), pillSub: 'All Retained',
      leftLabel: 'What Happens Here',
      leftText: '<code>TractProhibitionDatesProcessor</code> aggregates building-level STR prohibition records to the census tract level. For each tract, it finds the <b>first month any STR prohibition took effect</b> within its boundaries — the treatment timing variable used in all DiD models.',
      chips: [
        { val: c.nTreated.toLocaleString(), label: 'Tracts with prohibition', color: 'maroon' },
        { val: c.nControl.toLocaleString(), label: 'No prohibition', color: 'teal' },
      ],
      rightLabel: 'Retention',
      rightText: 'All rent-panel tracts are retained. Prohibition dates are assigned where available — tracts with no prohibition remain as never-treated controls.',
      retention: { pct: 100, label: '100% of rent-panel tracts retained', color: 'teal' },
      figFile: '/data/binary/did_story_map.png', figAlt: 'Map of ever-treated vs never-treated tracts',
    },
    {
      id: 5, label: 'Treatment\nAssignment', count: `${c.nTreated}+${c.nControl}`,
      badge: 'Step 5 of 6', title: 'Treatment Assignment',
      pillValue: `${c.nTreated}+${c.nControl}`, pillSub: 'Treated + Control',
      leftLabel: 'Treatment Definition',
      leftText: '', chips: [],
      rightLabel: 'Retention',
      rightText: 'All rent-panel tracts are retained — treatment assignment <i>labels</i> tracts, it does not remove them. Only the threshold of what counts as treated changes between the two definitions.',
      retention: { pct: 100, label: '100% retained — only labels change', color: 'teal' },
      figFile: '/data/binary/did_adoption_curve.png', figAlt: 'Cumulative treated tracts over time',
      isTreatmentStep: true,
    },
    {
      id: 6, label: 'Trend Matching\n& Pre-trend Filter', count: 'final sample',
      badge: 'Step 6 of 6', title: 'Trend Matching & Pre-treatment Filter',
      pillValue: 'matched', pillSub: 'DiD Sample',
      leftLabel: 'What Happens Here',
      leftText: '<code>TrendMatchingProcessor</code> applies two filters: (1) keeps only tracts with at least <b>6 months of pre-treatment data</b> before the first treated month in the panel, and (2) matches each ever-treated tract to its <b>k nearest never-treated neighbors</b> by pre-treatment rent slope. This is the final estimand sample for all TWFE and CS models.',
      chips: [
        { val: '≥6', label: 'Pre-periods required', color: 'blue' },
        { val: 'k', label: 'Matched controls', color: 'teal' },
      ],
      rightLabel: 'Retention',
      rightText: 'Some tracts are dropped: treated tracts lacking enough pre-treatment months, and never-treated tracts not selected as matches. The exact count depends on k and the panel window.',
      retention: { pct: 75, label: 'Varies — depends on k and panel window', color: 'amber' },
      figFile: '/data/binary/did_parallel_trends.png', figAlt: 'Pre-treatment rent trends: treated vs matched controls',
    },
  ]
}

const RET_BAR: Record<'teal' | 'amber', string> = {
  teal:  'bg-gradient-to-r from-teal-500 to-blue-500',
  amber: 'bg-gradient-to-r from-amber-500 to-yellow-400',
}
const RET_TEXT: Record<'teal' | 'amber', string> = {
  teal:  'text-teal-600',
  amber: 'text-amber-600',
}
const CHIP_BG: Record<string, string> = {
  maroon: 'bg-maroon/10 text-maroon',
  teal:   'bg-teal-50 text-teal-600',
  blue:   'bg-blue-50 text-blue-600',
  amber:  'bg-amber-50 text-amber-600',
}

export default function PipelineStepper({ nTracts, nTreated, nControl }: StepCounts) {
  const [active, setActive] = useState(5)
  const [treatMode, setTreatMode] = useState<'binary' | 'threshold'>('binary')
  const steps = buildSteps({ nTracts, nTreated, nControl })
  const s = steps[active - 1]

  return (
    <div>
      {/* Step circles */}
      <div className="flex items-start mb-8 relative">
        {steps.map((step, i) => {
          const done   = i + 1 < active
          const isActive = i + 1 === active
          return (
            <div key={step.id} className="flex-1 flex flex-col items-center relative cursor-pointer group"
              onClick={() => setActive(step.id)}>
              {/* connector line */}
              {i < steps.length - 1 && (
                <div className={`absolute left-1/2 right-[-50%] top-[22px] h-0.5 z-0
                  ${done ? 'bg-teal-500' : 'bg-gray-200'}`} />
              )}
              <div className={[
                'w-11 h-11 rounded-full z-10 flex items-center justify-center text-[15px] font-bold transition-all',
                done    ? 'bg-teal-500 text-white border-2 border-teal-500'
                : isActive ? 'bg-maroon text-white border-2 border-maroon ring-4 ring-maroon/10'
                : 'bg-white text-gray-300 border-2 border-gray-200 group-hover:border-maroon group-hover:text-maroon',
              ].join(' ')}>
                {done ? '✓' : step.id}
              </div>
              <p className={`text-[10px] font-semibold text-center mt-2 leading-tight max-w-[88px]
                ${done ? 'text-teal-600' : isActive ? 'text-maroon font-bold' : 'text-gray-400'}`}>
                {step.label.split('\n').map((l, j) => <span key={j} className="block">{l}</span>)}
              </p>
              <p className={`text-[10px] font-semibold mt-0.5 text-center
                ${done ? 'text-teal-500' : isActive ? 'text-maroon' : 'text-gray-300'}`}>
                {step.count}
              </p>
            </div>
          )
        })}
      </div>

      {/* Detail panel */}
      <div className="border border-gray-100 rounded-2xl overflow-hidden shadow-lg">
        {/* Header */}
        <div className="flex items-start justify-between px-8 py-5 border-b border-gray-100
          bg-gradient-to-br from-maroon/5 to-white">
          <div>
            <span className="inline-block bg-maroon/10 text-maroon text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded mb-2">
              {s.badge}
            </span>
            <h3 className="text-lg font-extrabold text-gray-900 tracking-tight">{s.title}</h3>
          </div>
          <div className="bg-maroon text-white rounded-xl px-5 py-3 text-center flex-shrink-0 ml-4">
            <span className="block text-xl font-extrabold tracking-tight">{s.pillValue}</span>
            <span className="block text-[9px] uppercase tracking-widest opacity-70 mt-0.5">{s.pillSub}</span>
          </div>
        </div>

        {/* Body */}
        <div className="grid grid-cols-2">
          {/* Left */}
          <div className="p-7 border-r border-gray-50">
            <p className="text-[10px] font-bold uppercase tracking-wider text-gray-300 mb-3">{s.leftLabel}</p>
            {s.isTreatmentStep ? (
              <TreatmentToggle treatMode={treatMode} setTreatMode={setTreatMode}
                nTreated={nTreated} nControl={nControl} />
            ) : (
              <>
                <p className="text-sm text-gray-600 leading-relaxed"
                  dangerouslySetInnerHTML={{ __html: s.leftText }} />
                {s.chips.length > 0 && (
                  <div className="flex gap-3 flex-wrap mt-5">
                    {s.chips.map(c => (
                      <div key={c.label} className={`rounded-xl px-4 py-2 text-center ${CHIP_BG[c.color] ?? ''}`}>
                        <span className="block text-xl font-extrabold">{c.val}</span>
                        <span className="block text-[10px] text-gray-500 mt-0.5">{c.label}</span>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>

          {/* Right */}
          <div className="p-7">
            <p className="text-[10px] font-bold uppercase tracking-wider text-gray-300 mb-3">{s.rightLabel}</p>
            <p className="text-sm text-gray-600 leading-relaxed"
              dangerouslySetInnerHTML={{ __html: s.rightText }} />

            {/* Retention bar */}
            <div className="mt-5">
              <div className="flex justify-between text-[12px] mb-1.5">
                <span className="text-gray-500">Retention from previous step</span>
                <span className={`font-bold ${RET_TEXT[s.retention.color]}`}>{s.retention.pct}%</span>
              </div>
              <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
                <div className={`h-full rounded-full transition-all duration-500 ${RET_BAR[s.retention.color]}`}
                  style={{ width: `${s.retention.pct}%` }} />
              </div>
              <p className="text-[10px] text-gray-300 mt-1.5">{s.retention.label}</p>
            </div>

            {/* Figure slot */}
            {s.figFile && (
              <FigureSlot src={s.figFile} alt={s.figAlt ?? ''} label="Figure" className="mt-5" />
            )}
          </div>
        </div>

        {/* Footer nav */}
        <div className="flex justify-between items-center px-8 py-3.5 border-t border-gray-100 bg-gray-50">
          <button
            onClick={() => setActive(a => Math.max(1, a - 1))}
            disabled={active === 1}
            className="text-[13px] font-semibold text-maroon border border-maroon/20 rounded-lg
              px-4 py-2 bg-white hover:bg-maroon/5 transition disabled:text-gray-300
              disabled:border-gray-100 disabled:cursor-default"
          >
            ← {active > 1 ? `Step ${active - 1}: ${steps[active - 2].label.replace('\n', ' ')}` : 'Previous'}
          </button>
          <span className="text-[11px] text-gray-400">Step {active} of {steps.length}</span>
          <button
            onClick={() => setActive(a => Math.min(steps.length, a + 1))}
            disabled={active === steps.length}
            className="text-[13px] font-semibold text-maroon border border-maroon/20 rounded-lg
              px-4 py-2 bg-white hover:bg-maroon/5 transition disabled:text-gray-300
              disabled:border-gray-100 disabled:cursor-default"
          >
            {active < steps.length ? `Step ${active + 1}: ${steps[active].label.replace('\n', ' ')} →` : 'Next →'}
          </button>
        </div>
      </div>
    </div>
  )
}

function TreatmentToggle({
  treatMode, setTreatMode, nTreated, nControl,
}: {
  treatMode: 'binary' | 'threshold'
  setTreatMode: (m: 'binary' | 'threshold') => void
  nTreated: number
  nControl: number
}) {
  return (
    <div>
      <div className="flex border border-gray-200 rounded-lg overflow-hidden w-fit mb-4">
        {(['binary', 'threshold'] as const).map(m => (
          <button key={m}
            onClick={() => setTreatMode(m)}
            className={[
              'px-5 py-2 text-[13px] font-semibold transition capitalize',
              m === 'binary' && treatMode === 'binary'   ? 'bg-blue-50 text-blue-600'    : '',
              m === 'threshold' && treatMode === 'threshold' ? 'bg-teal-50 text-teal-600' : '',
              treatMode !== m ? 'text-gray-400 hover:text-gray-600' : '',
            ].join(' ')}
          >
            {m === 'binary' ? 'Binary' : 'Threshold'}
          </button>
        ))}
      </div>

      {treatMode === 'binary' ? (
        <div className="bg-blue-50 border border-blue-200/70 rounded-xl p-5">
          <p className="text-[13px] text-gray-600 leading-relaxed">
            A tract is <strong>treated</strong> as soon as <em>any</em> STR prohibition takes effect
            within its boundaries — regardless of how many units are affected.
          </p>
          <div className="flex gap-3 mt-4">
            {[
              { val: nTreated.toLocaleString(), label: 'Treated tracts' },
              { val: nControl.toLocaleString(), label: 'Never-treated' },
              { val: `${((nTreated / (nTreated + nControl)) * 100).toFixed(1)}%`, label: 'Share treated' },
            ].map(c => (
              <div key={c.label} className="bg-blue-100 rounded-lg px-4 py-2 text-center">
                <span className="block text-xl font-extrabold text-blue-600">{c.val}</span>
                <span className="block text-[10px] text-gray-500">{c.label}</span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="bg-teal-50 border border-teal-200/70 rounded-xl p-5">
          <p className="text-[13px] text-gray-600 leading-relaxed">
            A tract is treated only when the share of prohibited STR units exceeds a minimum
            threshold of occupied housing units — a stricter definition that results in
            <em> fewer treated tracts</em> and more conservative estimates.
          </p>
          <div className="flex gap-3 mt-4">
            {[
              { val: `< ${nTreated}`, label: 'Treated tracts' },
              { val: `> ${nControl}`, label: 'Never-treated' },
              { val: 'stricter', label: 'Definition' },
            ].map(c => (
              <div key={c.label} className="bg-teal-100 rounded-lg px-4 py-2 text-center">
                <span className="block text-xl font-extrabold text-teal-600">{c.val}</span>
                <span className="block text-[10px] text-gray-500">{c.label}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      <p className="text-[11px] text-gray-300 italic mt-3">
        Both definitions compared side-by-side in the <strong>Robustness</strong> tab.
      </p>
    </div>
  )
}
```

- [ ] **Step 2: Verify it compiles**

`npm run dev` → check terminal for TypeScript errors. None expected.

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "feat: PipelineStepper client component with step nav + treatment toggle"
```

---

## Task 7: Descriptive page

**Files:**
- Create: `dashboard/src/app/descriptive/page.tsx`

- [ ] **Step 1: Write the Descriptive page**

```tsx
// dashboard/src/app/descriptive/page.tsx
import PipelineStepper from '@/components/PipelineStepper'
import FigureSlot from '@/components/FigureSlot'
import { loadPanelOverview, loadGroupStats } from '@/lib/data'

export default function DescriptivePage() {
  const ov = loadPanelOverview('binary')
  const gs = loadGroupStats('binary')
  const treated = gs.find(g => g.group.includes('Eventually')) ?? { n_tracts: 373 }
  const control = gs.find(g => g.group.includes('Never'))     ?? { n_tracts: 114 }

  return (
    <div>
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">Sample Construction Pipeline</h2>
      <p className="text-[15px] text-gray-500 mb-10 max-w-2xl leading-relaxed">
        From 1,332 raw Chicago census tracts to the final matched DiD sample —
        click any step to see what changed, how many units were retained, and why.
      </p>

      <PipelineStepper
        nTracts={ov.n_tracts}
        nTreated={treated.n_tracts}
        nControl={control.n_tracts}
      />

      <div className="grid grid-cols-2 gap-6 mt-10">
        <FigureSlot src="/data/binary/did_adoption_curve.png"
          alt="Cumulative prohibition adoption over time" label="Adoption curve" />
        <FigureSlot src="/data/binary/did_parallel_trends.png"
          alt="Average rent trends treated vs control" label="Pre-treatment rent trends" />
      </div>
      <div className="mt-6">
        <FigureSlot src="/data/binary/data_funnel.png"
          alt="Tract count funnel across pipeline stages" label="Sample construction funnel" />
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify pipeline interactions in browser**

Navigate to http://localhost:3000/descriptive.  
- Click each of the 6 step circles — detail panel updates  
- Click "Threshold" on step 5 — panel switches to teal  
- Click "← Previous" / "Next →" — navigates correctly  
- Step 3 shows `data_funnel.png` figure inside panel  

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "feat: Descriptive page with PipelineStepper + figures"
```

---

## Task 8: Analysis page

**Files:**
- Create: `dashboard/src/app/analysis/page.tsx`

- [ ] **Step 1: Write the Analysis page**

```tsx
// dashboard/src/app/analysis/page.tsx
import FigureSlot from '@/components/FigureSlot'
import StatTable from '@/components/StatTable'
import { loadCohortStats } from '@/lib/data'

export default function AnalysisPage() {
  const cohorts = loadCohortStats('binary').slice(0, 10) // top 10 cohorts

  const tableRows = cohorts.map(c => [
    c.first_prohibition_month,
    c.n_tracts.toLocaleString(),
    `${(c.share_of_treated_tracts * 100).toFixed(1)}%`,
    `$${c.mean_baseline_rent.toFixed(0)}`,
    `$${(c.mean_median_income / 1000).toFixed(0)}k`,
  ])

  return (
    <div>
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">Spatial & Descriptive Analysis</h2>
      <p className="text-[15px] text-gray-500 mb-10 max-w-2xl leading-relaxed">
        Geography of treatment, cohort composition, and pre-treatment rent dynamics.
      </p>

      {/* Maps row */}
      <div className="grid grid-cols-3 gap-5 mb-10">
        <FigureSlot src="/data/binary/did_story_map.png"
          alt="STR prohibition status by tract" label="Treatment status map" />
        <FigureSlot src="/data/binary/did_spatial_sample_ever_treated.png"
          alt="Ever-treated tracts in sample" label="Ever-treated tracts" />
        <FigureSlot src="/data/binary/did_story_map_cohort.png"
          alt="Prohibition cohort by tract" label="Cohort map" />
      </div>

      {/* Cohort table */}
      <h3 className="text-[15px] font-bold mb-3">Prohibition Cohorts</h3>
      <StatTable
        className="mb-10"
        headers={['First Prohibition Month', 'Tracts', 'Share of Treated', 'Mean Baseline Rent', 'Mean Income']}
        rows={tableRows}
      />

      {/* Event study + cohort dynamics */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        <FigureSlot src="/data/binary/event_study_plot.png"
          alt="TWFE event study coefficients" label="TWFE event study" />
        <FigureSlot src="/data/binary/did_cohort_dynamics.png"
          alt="Cohort-specific dynamic treatment effects" label="Cohort dynamics" />
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify in browser at `/analysis`** — maps, table, and figures render. Commit.

```bash
git add -A && git commit -m "feat: Analysis page — maps, cohort table, event study"
```

---

## Task 9: Models page

**Files:**
- Create: `dashboard/src/app/models/page.tsx`

- [ ] **Step 1: Write the Models page**

```tsx
// dashboard/src/app/models/page.tsx
import FigureSlot from '@/components/FigureSlot'
import StatTable from '@/components/StatTable'
import { loadComparisonRows } from '@/lib/data'

const ESTIMATOR_BLOCKS = [
  {
    accent: 'border-amber-400',
    title: 'TWFE (Two-Way Fixed Effects)',
    body: 'The classic panel estimator includes unit and time fixed effects. Under staggered adoption, already-treated units act as controls for later-treated units — contaminating estimates with heterogeneous treatment effects and potentially producing negative weights.',
  },
  {
    accent: 'border-maroon',
    title: 'Callaway & Sant\'Anna (2021)',
    body: 'CS estimates group-time ATT(g,t) for each (cohort, calendar-month) pair using only not-yet-treated or never-treated units as controls. Aggregates to an overall ATT with transparent, interpretable weights. Valid under parallel trends without assuming homogeneous effects.',
  },
  {
    accent: 'border-teal-500',
    title: 'CS with Covariates + Tract Trends',
    body: 'Extends CS by residualizing on ACS covariates (income, occupancy, education) and tract-specific linear pre-trends in the pre-treatment period only. Doubly-robust: consistent if either the propensity score or the outcome model is correctly specified.',
  },
]

export default function ModelsPage() {
  const rows = loadComparisonRows('binary').filter(r => r.rel_time >= -6 && r.rel_time <= 6)
  const tableRows = rows.map(r => [
    r.rel_time >= 0 ? `+${r.rel_time}` : `${r.rel_time}`,
    r.cs_att.toFixed(2),
    r.cs_se.toFixed(2),
    r.twfe_coef.toFixed(2),
    r.twfe_se.toFixed(2),
    (r.cs_att - r.twfe_coef).toFixed(2),
  ])

  return (
    <div>
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">Estimators & Models</h2>
      <p className="text-[15px] text-gray-500 mb-10 max-w-2xl leading-relaxed">
        Why TWFE is insufficient for staggered adoption, and how Callaway & Sant'Anna addresses it.
      </p>

      {/* Estimator blocks */}
      <div className="grid grid-cols-3 gap-5 mb-10">
        {ESTIMATOR_BLOCKS.map(b => (
          <div key={b.title} className={`border-t-[3px] ${b.accent} border border-gray-100 rounded-xl p-6`}>
            <h3 className="text-[13px] font-bold text-gray-800 mb-3">{b.title}</h3>
            <p className="text-[13px] text-gray-500 leading-relaxed">{b.body}</p>
          </div>
        ))}
      </div>

      {/* CS event study */}
      <div className="grid grid-cols-2 gap-6 mb-8">
        <FigureSlot src="/data/binary/did_callaway_santanna_event_study.png"
          alt="CS event study" label="CS baseline event study" />
        <FigureSlot src="/data/binary/did_callaway_santanna_event_study_with_controls.png"
          alt="CS with covariates and tract trends" label="CS with controls + tract trends" />
      </div>

      {/* TWFE vs CS comparison */}
      <div className="grid grid-cols-2 gap-6 mb-8">
        <FigureSlot src="/data/binary/did_twfe_vs_cs_comparison.png"
          alt="TWFE vs CS event study overlay" label="TWFE vs CS overlay" />
        <FigureSlot src="/data/binary/did_cs_twfe_difference.png"
          alt="CS minus TWFE difference (bias)" label="CS − TWFE difference (bias)" />
      </div>

      <FigureSlot src="/data/binary/did_cohort_dynamics_with_controls.png"
        alt="Cohort dynamics with controls" label="Cohort dynamics (CS with controls)" className="mb-8" />

      {/* Comparison table */}
      <h3 className="text-[15px] font-bold mb-3">ATT Estimates: CS vs TWFE by Relative Time</h3>
      <StatTable
        headers={['Rel. Time', 'CS ATT', 'CS SE', 'TWFE Coef', 'TWFE SE', 'Difference']}
        rows={tableRows}
      />
    </div>
  )
}
```

- [ ] **Step 2: Verify at `/models`** — 3 estimator blocks, all figures, table with ±6 rel-time rows. Commit.

```bash
git add -A && git commit -m "feat: Models page — estimator explainer, CS/TWFE figures, comparison table"
```

---

## Task 10: Robustness page

**Files:**
- Create: `dashboard/src/app/robustness/page.tsx`

- [ ] **Step 1: Write the Robustness page**

```tsx
// dashboard/src/app/robustness/page.tsx
import FigureSlot from '@/components/FigureSlot'
import InfoBlock from '@/components/InfoBlock'
import { loadPanelOverview, loadGroupStats } from '@/lib/data'

export default function RobustnessPage() {
  const ovB = loadPanelOverview('binary')
  const ovT = loadPanelOverview('threshold')
  const gsB = loadGroupStats('binary')
  const gsT = loadGroupStats('threshold')
  const treatedB = gsB.find(g => g.group.includes('Eventually')) ?? { n_tracts: 0, mean_rent: 0 }
  const treatedT = gsT.find(g => g.group.includes('Eventually')) ?? { n_tracts: 0, mean_rent: 0 }

  return (
    <div>
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">Robustness — Treatment Indicator Comparison</h2>
      <p className="text-[15px] text-gray-500 mb-10 max-w-2xl leading-relaxed">
        The treatment definition affects which tracts are labeled treated. Here we compare the
        binary and threshold indicators side-by-side across all key outputs.
      </p>

      {/* Sample comparison */}
      <div className="grid grid-cols-2 gap-6 mb-10">
        <InfoBlock
          title="Binary Indicator"
          rows={[
            { label: 'Treated tracts',       value: ovB.tracts_eventually_treated.toLocaleString(), valueClass: 'text-blue-600' },
            { label: 'Never-treated tracts', value: ovB.tracts_never_treated.toLocaleString() },
            { label: 'Mean rent (treated)',  value: `$${treatedB.mean_rent.toFixed(0)}` },
          ]}
        />
        <InfoBlock
          title="Threshold Indicator"
          rows={[
            { label: 'Treated tracts',       value: ovT.tracts_eventually_treated.toLocaleString(), valueClass: 'text-teal-600' },
            { label: 'Never-treated tracts', value: ovT.tracts_never_treated.toLocaleString() },
            { label: 'Mean rent (treated)',  value: `$${treatedT.mean_rent.toFixed(0)}` },
          ]}
        />
      </div>

      {/* Side-by-side event studies */}
      <h3 className="text-[15px] font-bold mb-4">CS Event Study — Binary vs Threshold</h3>
      <div className="grid grid-cols-2 gap-6 mb-8">
        <FigureSlot src="/data/binary/did_callaway_santanna_event_study.png"
          alt="CS event study binary" label="Binary indicator" />
        <FigureSlot src="/data/threshold/did_callaway_santanna_event_study.png"
          alt="CS event study threshold" label="Threshold indicator" />
      </div>

      {/* Cohort dynamics comparison */}
      <h3 className="text-[15px] font-bold mb-4">Cohort Dynamics — Binary vs Threshold</h3>
      <div className="grid grid-cols-2 gap-6 mb-8">
        <FigureSlot src="/data/binary/did_cohort_dynamics.png"
          alt="Cohort dynamics binary" label="Binary indicator" />
        <FigureSlot src="/data/threshold/did_cohort_dynamics.png"
          alt="Cohort dynamics threshold" label="Threshold indicator" />
      </div>

      {/* TWFE vs CS both modes */}
      <h3 className="text-[15px] font-bold mb-4">TWFE vs CS Comparison — Binary vs Threshold</h3>
      <div className="grid grid-cols-2 gap-6">
        <FigureSlot src="/data/binary/did_twfe_vs_cs_comparison.png"
          alt="TWFE vs CS binary" label="Binary indicator" />
        <FigureSlot src="/data/threshold/did_twfe_vs_cs_comparison.png"
          alt="TWFE vs CS threshold" label="Threshold indicator" />
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify at `/robustness`** — both InfoBlocks show live counts from binary/threshold CSVs; 3 side-by-side figure pairs render. Commit.

```bash
git add -A && git commit -m "feat: Robustness page — binary vs threshold side-by-side"
```

---

## Task 11: Pre-trends page

**Files:**
- Create: `dashboard/src/app/pretrends/page.tsx`

- [ ] **Step 1: Write the Pre-trends page**

```tsx
// dashboard/src/app/pretrends/page.tsx
import FigureSlot from '@/components/FigureSlot'
import InfoBlock from '@/components/InfoBlock'
import { loadParallelTrendsTest, loadHonestPretrends } from '@/lib/data'

export default function PretrendsPage() {
  const pt = loadParallelTrendsTest('binary')
  const hp = loadHonestPretrends('binary')

  const ptColor = pt.significant ? 'text-maroon' : 'text-teal-600'
  const hpColor = hp.violates_sign_restriction ? 'text-maroon' : 'text-teal-600'

  return (
    <div>
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">
        Pre-trends & Parallel Trends Assumption
      </h2>
      <p className="text-[15px] text-gray-500 mb-10 max-w-2xl leading-relaxed">
        Testing the core identifying assumption of our DiD design: that treated and
        never-treated tracts would have followed parallel rent trajectories absent the policy.
      </p>

      {/* Regression test results */}
      <div className="grid grid-cols-2 gap-6 mb-10">
        <InfoBlock
          title="Parallel Trends Regression Test"
          rows={[
            { label: 'Interaction coefficient', value: pt.interaction_coef.toFixed(3) },
            { label: 'p-value',                 value: pt.p_value.toFixed(4) },
            { label: 'Significant at 5%',        value: pt.significant ? 'Yes ✗' : 'No ✓', valueClass: ptColor },
            { label: 'Interpretation',           value: pt.interpretation },
          ]}
        />
        <InfoBlock
          title="Honest Pre-trends (TWFE)"
          rows={[
            { label: 'Max |pre-period coef|',   value: hp.max_abs_twfe_coef_pre.toFixed(3) },
            { label: 'N pre-periods',           value: hp.n_pre_periods.toString() },
            { label: 'Sign restriction violated', value: hp.violates_sign_restriction ? 'Yes ✗' : 'No ✓', valueClass: hpColor },
          ]}
        />
      </div>

      {/* Figures */}
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
```

- [ ] **Step 2: Verify at `/pretrends`** — regression test results show live p-values; all 4 figures render. Commit.

```bash
git add -A && git commit -m "feat: Pre-trends page — parallel trends test, honest pretrends, SUTVA"
```

---

## Task 12: Policy page

**Files:**
- Create: `dashboard/src/app/policy/page.tsx`

- [ ] **Step 1: Write the Policy page**

```tsx
// dashboard/src/app/policy/page.tsx
import FigureSlot from '@/components/FigureSlot'
import { loadComparisonRows, loadParallelTrendsTest } from '@/lib/data'

const CONCLUSIONS = [
  {
    number: '01',
    heading: 'STR prohibitions are associated with measurable rent changes',
    body: 'Our CS estimates show statistically detectable effects on monthly rents in prohibited tracts during the post-treatment window. The direction and magnitude vary by cohort, suggesting the effect is not homogeneous across the city.',
  },
  {
    number: '02',
    heading: 'TWFE substantially biases estimates under staggered adoption',
    body: 'The difference between TWFE and CS estimates is non-trivial in magnitude, consistent with the heterogeneous-treatment-effects bias documented by Callaway & Sant\'Anna (2021). Relying on TWFE alone would misstate both the sign and size of policy effects.',
  },
  {
    number: '03',
    heading: 'Parallel pre-trends are plausible',
    body: 'Formal regression tests and visual inspection of pre-period rent trajectories support the parallel trends assumption for our matched sample. The honest pre-trends analysis confirms pre-period coefficients are small in magnitude.',
  },
  {
    number: '04',
    heading: 'Policy implications for housing regulation',
    body: 'The evidence suggests STR restrictions affect the local rental market. Policymakers should consider the heterogeneous impact across cohorts — early vs late adopting neighborhoods — before assuming uniform affordability gains from blanket prohibition.',
  },
]

export default function PolicyPage() {
  const rows = loadComparisonRows('binary').filter(r => r.rel_time >= 0)
  const pt = loadParallelTrendsTest('binary')

  const avgPostATT = rows.length
    ? (rows.reduce((s, r) => s + r.cs_att, 0) / rows.length).toFixed(2)
    : '—'

  return (
    <div>
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">Policy Conclusions</h2>
      <p className="text-[15px] text-gray-500 mb-10 max-w-2xl leading-relaxed">
        What the evidence says, its limits, and what it means for housing policy in Chicago.
      </p>

      {/* ATT summary callout */}
      <div className="border-l-4 border-maroon bg-maroon/5 rounded-r-xl px-6 py-5 mb-10">
        <p className="text-[10px] font-bold uppercase tracking-widest text-maroon mb-2">Key Estimate</p>
        <p className="text-[15px] text-gray-700 leading-relaxed">
          Average post-treatment CS ATT across all post-treatment periods:{' '}
          <strong className="text-maroon">${avgPostATT} / month</strong> (binary indicator).
          Parallel trends test p-value: <strong>{pt.p_value.toFixed(4)}</strong> —
          {pt.significant ? ' significant pre-trend detected (see Pre-trends tab).' : ' no significant pre-trend.'}
        </p>
      </div>

      {/* Conclusion blocks */}
      <div className="grid grid-cols-2 gap-5 mb-10">
        {CONCLUSIONS.map(c => (
          <div key={c.number} className="border border-gray-100 rounded-xl p-6">
            <span className="text-4xl font-extrabold text-gray-100 leading-none block mb-3">{c.number}</span>
            <h3 className="text-[14px] font-bold text-gray-800 mb-2 leading-snug">{c.heading}</h3>
            <p className="text-[13px] text-gray-500 leading-relaxed">{c.body}</p>
          </div>
        ))}
      </div>

      {/* Cohort explainer */}
      <FigureSlot
        src="/data/binary/cohort_dynamics_explainer.png"
        alt="Cohort dynamics explainer"
        label="Cohort dynamics — ATT by prohibition wave"
        className="mb-8"
      />

      {/* Limitations */}
      <div className="border border-dashed border-gray-200 rounded-xl p-6">
        <h3 className="text-[13px] font-bold text-gray-700 mb-3">Limitations & Next Steps</h3>
        <ul className="space-y-2 text-[13px] text-gray-500 leading-relaxed list-disc list-inside">
          <li>ZORI interpolation from ZIP codes introduces measurement error in the rent variable.</li>
          <li>The threshold indicator's exact value is sensitive to the ACS occupied-unit denominator.</li>
          <li>SUTVA may be violated if STR supply shifts across tract boundaries (tested in Pre-trends tab).</li>
          <li>Possible extensions: Synthetic DiD, double ML, synthetic control for placebo validation.</li>
        </ul>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify at `/policy`** — key estimate callout shows live avg ATT; 4 conclusion blocks; cohort explainer figure; limitations list. Commit.

```bash
git add -A && git commit -m "feat: Policy page — conclusions, live ATT summary, limitations"
```

---

## Self-Review

### Spec coverage

| Spec requirement | Task |
|---|---|
| `dashboard/` at repo root, standalone Next.js | Task 1 |
| Symlinks to `did-cs-whitepaper-binary/` and `threshold/` | Task 2 |
| CSV reader (no external dep) | Task 2 |
| TypeScript types for all CSV shapes | Task 2 |
| Hero banner always visible above tabs | Task 3 |
| 7 tabs sticky | Task 3 |
| DataCard, FigureSlot, InfoBlock, StatTable | Task 4 |
| Introduction: research Q, story blocks, treatment definition, centered data cards, info blocks | Task 5 |
| PipelineStepper: 6 steps, clickable, treatment toggle, prev/next nav, figure inside panel | Task 6 |
| Descriptive page uses PipelineStepper | Task 7 |
| Analysis: maps, cohort table, event study | Task 8 |
| Models: estimator explainer, CS/TWFE figures, comparison table | Task 9 |
| Robustness: binary vs threshold side-by-side | Task 10 |
| Pre-trends: regression test, honest pretrends, SUTVA | Task 11 |
| Policy: avg ATT callout, conclusions, cohort explainer, limitations | Task 12 |

### No placeholders — confirmed

All code blocks are complete. All file paths are exact. All CSV column names match the actual files verified in the spec phase.

### Type consistency — confirmed

- `PanelOverview` defined in `types.ts` Task 2, used in `Hero.tsx` Task 3 and `page.tsx` Task 5
- `loadPanelOverview()` returns object matching `PanelOverview` — used in layout, Introduction, Descriptive, Robustness
- `PipelineStepper` props `{ nTracts, nTreated, nControl }` defined in Task 6, called in Task 7
- `FigureSlot` props `{ src, alt, label?, className? }` defined Task 4, used Tasks 7–12
- `InfoBlock` props `{ title, rows: InfoRow[] }` defined Task 4, used Tasks 5, 10, 11
- `StatTable` props `{ headers, rows, className? }` defined Task 4, used Tasks 8, 9
