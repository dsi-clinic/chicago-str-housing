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
