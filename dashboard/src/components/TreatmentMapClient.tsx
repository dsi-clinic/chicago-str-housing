'use client'
import { useEffect, useRef } from 'react'
import type { Map as LeafletMap } from 'leaflet'

const CHICAGO_CENTER: [number, number] = [41.845, -87.65]
const CHICAGO_ZOOM = 10

const ROLE_COLOR: Record<string, string> = {
  matched_treated: '#8B0000',
  ever_treated:    '#8B0000',
  matched_control: '#2563EB',
  never_treated:   '#2563EB',
  not_in_sample:   '#D1D5DB',
}
const ROLE_OPACITY: Record<string, number> = {
  matched_treated: 0.80,
  ever_treated:    0.55,
  matched_control: 0.65,
  never_treated:   0.40,
  not_in_sample:   0.15,
}
const ROLE_LABEL: Record<string, string> = {
  matched_treated: 'Treated (matched)',
  ever_treated:    'Treated (not matched)',
  matched_control: 'Control (matched)',
  never_treated:   'Never-treated',
  not_in_sample:   'Outside sample',
}

export interface TreatmentMapClientProps {
  geojsonUrl: string
  title: string
  subtitle?: string
}

export default function TreatmentMapClient({ geojsonUrl, title, subtitle }: TreatmentMapClientProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef       = useRef<LeafletMap | null>(null)

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    import('leaflet').then(L => {
      // Clear stale Leaflet state (React Strict Mode double-invoke)
      const el = containerRef.current as HTMLDivElement & { _leaflet_id?: number }
      if (el._leaflet_id) delete el._leaflet_id

      const map = L.default.map(el, {
        center:          CHICAGO_CENTER,
        zoom:            CHICAGO_ZOOM,
        zoomControl:     false,      // we add our own positioned control below
        scrollWheelZoom: true,
        dragging:        true,
        doubleClickZoom: true,
      })

      // Basemap — light, no labels (so tract colours read cleanly)
      L.default.tileLayer(
        'https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png',
        { attribution: '© OpenStreetMap © CartoDB', subdomains: 'abcd', maxZoom: 19 }
      ).addTo(map)

      // Zoom control — bottom-right to keep top-left clear for home btn
      L.default.control.zoom({ position: 'bottomright' }).addTo(map)

      // Home button — reset to initial Chicago extent
      const HomeControl = L.default.Control.extend({
        onAdd() {
          const btn = L.default.DomUtil.create('button', 'leaflet-bar leaflet-control') as HTMLButtonElement
          btn.title     = 'Reset to full Chicago view'
          btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>'
          Object.assign(btn.style, {
            width: '30px', height: '30px', cursor: 'pointer',
            background: 'white', border: 'none',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#555',
          })
          L.default.DomEvent.on(btn, 'click', (e) => {
            L.default.DomEvent.stopPropagation(e)
            map.setView(CHICAGO_CENTER, CHICAGO_ZOOM)
          })
          return btn
        },
        onRemove() {},
      })
      new HomeControl({ position: 'topleft' }).addTo(map)

      fetch(geojsonUrl)
        .then(r => r.json())
        .then((data: GeoJSON.FeatureCollection) => {
          // ── Tract fill layer ──
          L.default.geoJSON(data, {
            style: feat => {
              const role = (feat?.properties?.role as string) ?? 'not_in_sample'
              return {
                fillColor:   ROLE_COLOR[role]   ?? '#D1D5DB',
                fillOpacity: ROLE_OPACITY[role] ?? 0.15,
                color:       '#ffffff',
                weight:      0.5,
              }
            },
            onEachFeature: (feat, lyr) => {
              const role  = (feat?.properties?.role as string) ?? 'not_in_sample'
              const units = (feat?.properties?.prohibition_units as number) ?? 0
              lyr.bindTooltip(
                `<strong>Tract ${feat?.properties?.tract_id}</strong><br/>${ROLE_LABEL[role] ?? role}` +
                (units > 0 ? `<br/><span style="color:#8B0000">${units} prohibited units</span>` : ''),
                { sticky: true }
              )
            },
          }).addTo(map)

          // ── Prohibition-unit circle overlay ──
          // Small semi-transparent circles at each tract centroid,
          // visible only for tracts with prohibited units.
          data.features.forEach(feat => {
            const units = (feat?.properties?.prohibition_units as number) ?? 0
            const lat   = feat?.properties?.centroid_lat as number
            const lng   = feat?.properties?.centroid_lng as number
            if (!units || !lat || !lng) return

            // Radius scales from 3px (1 unit) to ~18px (300+ units), log-ish
            const radius = Math.min(3 + Math.log1p(units) * 2.2, 18)
            L.default.circleMarker([lat, lng], {
              radius,
              color:       '#8B0000',
              weight:      0,
              fillColor:   '#8B0000',
              fillOpacity: 0.30,
            }).addTo(map).bindTooltip(
              `${units} prohibited unit${units !== 1 ? 's' : ''}`,
              { sticky: true }
            )
          })
        })

      mapRef.current = map
    })

    return () => {
      mapRef.current?.remove()
      mapRef.current = null
    }
  }, [geojsonUrl])

  return (
    <div>
      <p className="text-[13px] font-bold text-gray-800 mb-0.5">{title}</p>
      {subtitle && <p className="text-[11px] text-gray-400 mb-2">{subtitle}</p>}
      <div ref={containerRef} className="h-[380px] rounded-xl border border-gray-100 overflow-hidden" />
      <div className="flex gap-4 mt-2 text-[10px] text-gray-400 flex-wrap">
        <span><span className="inline-block w-3 h-3 rounded-sm mr-1" style={{background:'#8B0000',opacity:0.8}}/>Treated</span>
        <span><span className="inline-block w-3 h-3 rounded-sm mr-1" style={{background:'#2563EB',opacity:0.6}}/>Never-treated</span>
        <span><span className="inline-block w-3 h-3 rounded-sm mr-1" style={{background:'#D1D5DB',opacity:0.5}}/>Outside sample</span>
        <span><span className="inline-block w-3 h-3 rounded-full mr-1" style={{background:'#8B0000',opacity:0.35}}/>Prohibited units</span>
      </div>
    </div>
  )
}
