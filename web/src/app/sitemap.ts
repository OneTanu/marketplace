import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site";

// Only pages anyone can open. Listings and school feeds need a verified student account, so
// they aren't listed.
export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: SITE_URL, changeFrequency: "weekly", priority: 1 },
    { url: `${SITE_URL}/account/signup`, changeFrequency: "monthly", priority: 0.8 },
    { url: `${SITE_URL}/terms`, changeFrequency: "yearly", priority: 0.3 },
    { url: `${SITE_URL}/privacy`, changeFrequency: "yearly", priority: 0.3 },
  ];
}
