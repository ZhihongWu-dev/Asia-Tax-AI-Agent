// The browser only talks to this Next.js server; /api/* is proxied to the
// local FastAPI service (make run-api), so no CORS setup is needed.
const API_URL = process.env.FSIE_API_URL ?? "http://127.0.0.1:8000"

/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    unoptimized: true,
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*` }]
  },
}

export default nextConfig
