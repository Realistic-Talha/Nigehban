"use client";

import Image from "next/image";
import Link from "next/link";
import { useFeed } from "@/hooks/use-feed";
import { Badge } from "@/components/ui/Badge";
import { Reveal } from "@/components/motion/Reveal";

export function VerdictMarquee() {
  const { data, isLoading } = useFeed();

  return (
    <section className="px-3 py-3 sm:px-5 sm:py-4">
      <Reveal>
        <div className="mx-auto flex max-w-[1120px] flex-col items-stretch gap-6 overflow-hidden rounded-[36px] bg-[#003e29] px-6 py-8 sm:flex-row sm:items-center sm:gap-10 sm:rounded-[40px] sm:px-10 sm:py-10">
          <div className="flex shrink-0 items-center gap-4 sm:max-w-[280px]">
            <div className="relative h-16 w-16 shrink-0 overflow-hidden rounded-full border-2 border-white/20 bg-[#002e1e]">
              <Image
                src="/marketing/avatar1.jpg"
                alt=""
                fill
                className="object-cover"
                sizes="64px"
              />
            </div>
            <p className="font-display text-xl leading-snug text-[#fdfcf0] sm:text-2xl">
              Proudly verifying for Pakistan&apos;s careful sharers.
            </p>
          </div>

          <div className="min-w-0 flex-1 overflow-hidden">
            {isLoading && (
              <div className="flex gap-3">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="h-14 w-52 shrink-0 animate-pulse rounded-2xl bg-white/10" />
                ))}
              </div>
            )}
            {!isLoading && (!data || data.length === 0) && (
              <div className="flex flex-wrap gap-2.5">
                {["SBP patterns", "FIA grounded", "Urdu + EN", "Shareable /v"].map((l) => (
                  <span
                    key={l}
                    className="rounded-full border border-white/20 bg-white/10 px-4 py-2 text-[12px] font-medium text-white/90"
                  >
                    {l}
                  </span>
                ))}
              </div>
            )}
            {data && data.length > 0 && (
              <div className="marquee-track gap-3">
                {[...data, ...data].map((item, i) => (
                  <Link
                    key={`${item.id}-${i}`}
                    href={`/v/${item.id}`}
                    className="flex w-56 shrink-0 items-center gap-3 rounded-2xl border border-white/15 bg-white/10 px-4 py-3 transition hover:bg-white/15"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-[13px] font-medium text-white">{item.title}</p>
                      {item.verdict && (
                        <div className="mt-1">
                          <Badge verdict={item.verdict} />
                        </div>
                      )}
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      </Reveal>
    </section>
  );
}
