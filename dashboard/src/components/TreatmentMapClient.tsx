'use client'
import { useEffect, useRef } from 'react'
import type { Map as LeafletMap, GeoJSON as GeoJSONLayer } from 'leaflet'

/* Role → fill colour */
const ROLE_COLOR: Record<string, string> = {
  matched_treated:  '#8B0000',
  ever_treated:     '#8B0000',
  matched_control:  '#2563EB',
  never_treated:    '#2563EB',
  not_in_sample:    '#D1D5DB',
}
const ROLE_OPACITY: Record<string, number> = {
  matched_treated:  0.80,
  ever_treated:     0.55,
  matched_control:  0.65,
  never_treated:    0.40,
  not_in_sample:    0.20,
}
const ROLE_LABEL: Record<string, string> = {
  matched_treated:  'Treated (matched)',
  ever_treated:     'Treated (not matched)',
  matched_control:  'Control (matched)',
  never_treated:    'Never-treated',
  not_in_sample:    'Outside sample',
}

export interface TreatmentMapClientProps {
  geojsonUrl: string
  title: string
  subtitle?: string
}

export default function TreatmentMapClient({ geojsonUrl, title, subtitle }: TreatmentMapClientProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef       = useRef<LeafletMap | null>(null)
  const layerRef     = useRef<GeoJSONLayer | null>(null)

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    /* Leaflet must be imported at runtime (no SSR) */
    import('leaflet').then(L => {
      // Clear any stale Leaflet state left by React Strict Mode double-invoke
      const container = containerRef.current as HTMLDivElement & { _leaflet_id?: number }
      if (container._leaflet_id) delete container._leaflet_id
      /* Fix default marker icons broken by webpack */
      // @ts-expect-error leaflet internal
      delete L.default.Icon.Default.prototype._getIconUrl
      L.default.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://unpkg.com/leaflet@1.9/dist/images/marker-icon-2x.png',
        iconUrl:       'https://unpkg.com/leaflet@1.9/dist/images/marker-icon.png',
        shadowUrl:     'https://unpkg.com/leaflet@1.9/dist/images/marker-shadow.png',
      })

      const map = L.default.map(containerRef.current!, {
        center:      [41.845, -87.65],
        zoom:        10,
        zoomControl: true,
        scrollWheelZoom: false,
      })

      L.default.tileLayer(
        'https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png',
        { attribution: '© OpenStreetMap © CartoDB', subdomains: 'abcd', maxZoom: 19 }
      ).addTo(map)

      fetch(geojsonUrl)
        .then(r => r.json())
        .then(data => {
          const layer = L.default.geoJSON(data as GeoJSON.FeatureCollection, {
            style: feat => {
              const role = (feat?.properties?.role as string) ?? 'not_in_sample'
              return {
                fillColor:   ROLE_COLOR[role]   ?? '#D1D5DB',
                fillOpacity: ROLE_OPACITY[role] ?? 0.2,
                color:       '#fff',
                weight:      0.6,
              }
            },
            onEachFeature: (feat, lyr) => {
              const role = (feat?.properties?.role as string) ?? 'not_in_sample'
              lyr.bindTooltip(
                `<strong>Tract ${feat?.properties?.tract_id}</strong><br/>${ROLE_LABEL[role] ?? role}`,
                { sticky: true }
              )
            },
          })
          layer.addTo(map)
          layerRef.current = layer
        })

      mapRef.current = map
    })

    return () => {
      mapRef.current?.remove()
      mapRef.current  = null
      layerRef.current = null
    }
  }, [geojsonUrl])

  return (
    <div>
      <p className="text-[12px] font-bold text-gray-700 mb-1">{title}</p>
      {subtitle && <p className="text-[11px] text-gray-400 mb-2">{subtitle}</p>}
      <div ref={containerRef} className="h-[360px] rounded-xl border border-gray-100 overflow-hidden" />
    </div>
  )
}
