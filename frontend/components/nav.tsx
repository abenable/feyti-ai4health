"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { FolderTree, LayoutDashboard, MessageSquare, Wifi, WifiOff } from "lucide-react";

import { getApiUrl } from "@/lib/api";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const LINKS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dossier", label: "Dossier", icon: FolderTree },
  { href: "/chat", label: "Chat", icon: MessageSquare },
];

export function Nav() {
  const pathname = usePathname();
  const [isBackendOnline, setIsBackendOnline] = useState<boolean | null>(null);

  useEffect(() => {
    const checkHealth = async () => {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      try {
        const res = await fetch(getApiUrl("/health"), { cache: "no-store", signal: controller.signal });
        setIsBackendOnline(res.ok);
      } catch {
        setIsBackendOnline(false);
      } finally {
        clearTimeout(timeoutId);
      }
    };
    checkHealth();
    const intervalId = setInterval(checkHealth, 60000);
    return () => clearInterval(intervalId);
  }, []);

  return (
    <TooltipProvider delay={200}>
      <nav className="sticky top-0 z-40 w-full border-b border-slate-200/60 bg-[#fdfbf7]/90 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
          <Link href="/" className="font-serif text-lg font-bold text-slate-900 tracking-tight shrink-0">
            Feyti
          </Link>

          <div className="flex items-center gap-1">
            {LINKS.map(({ href, label, icon: Icon }) => {
              const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wider transition-colors ${
                    active
                      ? "bg-indigo-100 text-indigo-800"
                      : "text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">{label}</span>
                </Link>
              );
            })}
          </div>

          {isBackendOnline !== null && (
            <Tooltip>
              <TooltipTrigger
                className={
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wider border shadow-sm transition-colors outline-none cursor-pointer shrink-0 " +
                  (isBackendOnline
                    ? "bg-emerald-50 border-emerald-200 text-emerald-700 hover:bg-emerald-100"
                    : "bg-red-50 border-red-200 text-red-700 hover:bg-red-100")
                }
              >
                {isBackendOnline ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
                <span className="hidden md:inline">{isBackendOnline ? "System Online" : "System Offline"}</span>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="bg-slate-800 text-white border-none shadow-xl max-w-xs text-center">
                {isBackendOnline
                  ? "Backend is connected and ready to process documents."
                  : "Cannot reach the analysis server. Please ensure the backend is running."}
              </TooltipContent>
            </Tooltip>
          )}
        </div>
      </nav>
    </TooltipProvider>
  );
}
