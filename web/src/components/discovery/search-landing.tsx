"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { getCurrentUser, getSchools } from "@/lib/platform";

export function SearchLanding() {
  const router = useRouter();

  useEffect(() => {
    Promise.all([getCurrentUser().catch(() => null), getSchools().catch(() => [])]).then(
      ([user, schools]) => {
        const school = user?.school ?? schools.find((item) => item.marketplace_status === "open");
        router.replace(school ? `/schools/${school.slug}?focus=search` : "/");
      },
    );
  }, [router]);

  return <main className="mx-auto min-h-[70vh] max-w-6xl animate-pulse px-4 py-10 sm:px-6"><div className="h-12 max-w-xl rounded-2xl bg-foreground/5" /><div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-4">{Array.from({ length: 8 }).map((_, index) => <div key={index} className="aspect-square rounded-2xl bg-foreground/5" />)}</div></main>;
}
