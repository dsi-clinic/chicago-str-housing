// dashboard/next.config.ts
import type { NextConfig } from 'next'

const config: NextConfig = {
  images: {
    unoptimized: true,   // local pipeline output PNGs — no optimization needed
  },
}

export default config
