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

  if (!ready) return <div className="h-9 w-28 animate-pulse rounded-[0.625rem] bg-surface" aria-hidden="true" />;
  if (authenticated) return <div className="flex items-center gap-1"><button onClick={logout} className="btn btn-quiet btn-sm">Log out</button><Link href="/sell" className="btn btn-primary btn-sm hidden desktop:inline-flex">Sell an item</Link></div>;
  return <div className="flex items-center gap-1"><Link href="/account/login" className="btn btn-quiet btn-sm hidden sm:inline-flex">Log in</Link><Link href="/account/signup" className="btn btn-primary btn-sm">Join Tanu</Link></div>;
}
