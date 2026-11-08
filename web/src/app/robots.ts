import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site";

// Public pages may be indexed; signed-in and personal areas stay out of search results. (Those
// pages already require an account; this just keeps crawlers from trying.)
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      // The signup page is public and in the sitemap; the more specific rule wins over /account/.
      allow: ["/", "/account/signup"],
      disallow: ["/api/", "/media/", "/account/", "/profile", "/inbox", "/deals", "/notifications", "/sell", "/moderation", "/listings/mine", "/design-lab"],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
