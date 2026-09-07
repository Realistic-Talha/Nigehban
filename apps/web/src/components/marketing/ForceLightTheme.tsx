"use client";

import { useEffect } from "react";
import { useTheme } from "next-themes";

/** Marketing always renders Flow cream — never follow system dark. */
export function ForceLightTheme({ children }: { children: React.ReactNode }) {
  const { setTheme } = useTheme();

  useEffect(() => {
    setTheme("light");
    document.documentElement.setAttribute("data-theme", "light");
    document.documentElement.classList.remove("dark");
  }, [setTheme]);

  return (
    <div
      data-theme="light"
      className="min-h-dvh bg-[#fdfcf0] text-[#141414]"
      style={{
        colorScheme: "light",
        background: "#fdfcf0",
        color: "#141414",
      }}
    >
      {children}
    </div>
  );
}
