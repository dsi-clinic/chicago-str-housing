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
