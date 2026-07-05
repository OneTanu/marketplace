import type { NextConfig } from "next";

// Where the Django API runs. The browser only ever talks to this Next.js server,
// which forwards /api and /media to Django, so cookies are same-origin. Django trusts the
// web app's Origin for CSRF via CSRF_TRUSTED_ORIGINS (backend settings).
const API_URL = process.env.API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // Django URLs end in "/". Without this, Next strips the slash and Django redirects
  // back to add it, which loops.
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return [
      // ":path*" drops a trailing slash, so match the slash form first and keep it.
      { source: "/api/:path*/", destination: `${API_URL}/api/:path*/` },
      { source: "/api/:path*", destination: `${API_URL}/api/:path*` },
      { source: "/media/:path*", destination: `${API_URL}/media/:path*` },
    ];
  },
};

export default nextConfig;
