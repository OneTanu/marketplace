"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { authRequest } from "@/lib/auth";
import { getCurrentUser } from "@/lib/platform";

export function AuthActions() {
  const router = useRouter();
  const [authenticated, setAuthenticated] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;
    getCurrentUser().then((user) => {
      if (active) { setAuthenticated(Boolean(user)); setReady(true); }
    }).catch(() => active && setReady(true));
    return () => { active = false; };
  }, []);

  async function logout() {
    const { response } = await authRequest("auth/session", { method: "DELETE" });
    if (response.ok) { setAuthenticated(false); router.push("/"); router.refresh(); }
  }

  if (!ready) return <div className="h-10 w-28 animate-pulse rounded-full bg-foreground/5" aria-hidden="true" />;
  if (authenticated) return <div className="flex items-center gap-2"><Link href="/profile" className="hidden rounded-full px-4 py-2 text-sm font-semibold text-foreground/70 hover:text-foreground sm:block">Profile</Link><button onClick={logout} className="rounded-full bg-foreground px-4 py-2.5 text-sm font-bold text-white transition hover:bg-forest">Log out</button></div>;
  return <div className="flex items-center gap-2"><Link href="/account/login" className="hidden rounded-full px-4 py-2 text-sm font-semibold text-foreground/70 transition hover:text-foreground sm:block">Log in</Link><Link href="/account/signup" className="rounded-full bg-foreground px-4 py-2.5 text-sm font-bold text-white shadow-sm transition hover:-translate-y-0.5 hover:bg-forest">Join Tanu</Link></div>;
}
