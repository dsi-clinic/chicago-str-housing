'use client'
import dynamic from 'next/dynamic'
import type { TreatmentMapClientProps } from './TreatmentMapClient'

/* SSR=false: Leaflet requires window/document */
const TreatmentMapClient = dynamic(
  () => import('./TreatmentMapClient'),
  {
    ssr: false,
    loading: () => (
      <div className="h-[360px] rounded-xl border border-gray-100 bg-gray-50 flex items-center justify-center">
        <span className="text-sm text-gray-400">Loading map…</span>
      </div>
    ),
  }
)

export default function TreatmentMap(props: TreatmentMapClientProps) {
  return <TreatmentMapClient {...props} />
}
