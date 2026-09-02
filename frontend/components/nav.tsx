"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { Activity, ArrowLeftRight, BookOpen, FolderTree, Globe2, LayoutDashboard, MessageSquare, Wifi, WifiOff } from "lucide-react";

import { apiFetch, getApiUrl } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import { LanguageSwitcher } from "@/components/language-switcher";
import type { DossierSummary } from "@/lib/types";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export function Nav() {
  const pathname = usePathname();
  const { dossierId } = useParams<{ dossierId?: string }>();
  const [isBackendOnline, setIsBackendOnline] = useState<boolean | null>(null);
  const [dossierName, setDossierName] = useState<string | null>(null);
  const { t } = useLanguage();

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

  useEffect(() => {
    if (!dossierId) {
      setDossierName(null);
      return;
    }
    apiFetch<DossierSummary>(`/api/v1/dossiers/${dossierId}`)
      .then((d) => setDossierName(d.name))
      .catch(() => setDossierName(null));
  }, [dossierId]);

  const links = dossierId
    ? [
        { href: `/d/${dossierId}`, label: t.nav.dashboard, icon: LayoutDashboard },
        { href: `/d/${dossierId}/structure`, label: t.nav.structure, icon: FolderTree },
        { href: `/d/${dossierId}/pv`, label: t.nav.pv, icon: Activity },
        { href: `/d/${dossierId}/regintel`, label: t.nav.regintel, icon: Globe2 },
        { href: `/d/${dossierId}/literature`, label: t.nav.literature, icon: BookOpen },
        { href: `/d/${dossierId}/chat`, label: t.nav.chat, icon: MessageSquare },
      ]
    : [];

  return (
    <TooltipProvider delay={200}>
      <nav className="sticky top-0 z-40 w-full border-b border-slate-200/60 bg-[#fdfbf7]/90 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center gap-3">
          <div className="flex items-center gap-3 min-w-0 shrink-0">
            <Link href="/" className="font-serif text-lg font-bold text-slate-900 tracking-tight shrink-0 whitespace-nowrap">
              Feyti
            </Link>
            {dossierName && (
              <>
                <span className="text-slate-300 hidden sm:inline">/</span>
                <span className="text-sm text-slate-600 truncate hidden sm:inline">{dossierName}</span>
              </>
            )}
          </div>

          {links.length > 0 && (
            <div className="flex-1 min-w-0 overflow-x-auto scrollbar-thin">
              <div className="flex items-center gap-0.5 w-max rounded-full bg-slate-100/70 p-0.5">
                {links.map(({ href, label, icon: Icon }) => {
                  // The dashboard link (bare /d/{id}) must match exactly, or it would
                  // also light up on /d/{id}/structure and /d/{id}/chat.
                  const active = href === `/d/${dossierId}` ? pathname === href : pathname.startsWith(href);
                  return (
                    <Tooltip key={href}>
                      <TooltipTrigger
                        render={<Link href={href} />}
                        className={`flex items-center gap-1.5 px-2.5 lg:px-3 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wider whitespace-nowrap shrink-0 transition-colors ${
                          active
                            ? "bg-white text-indigo-800 shadow-sm"
                            : "text-slate-500 hover:bg-white/70 hover:text-slate-800"
                        }`}
                      >
                        <Icon className="w-3.5 h-3.5" />
                        <span className="hidden lg:inline">{label}</span>
                      </TooltipTrigger>
                      <TooltipContent side="bottom" className="lg:hidden bg-slate-800 text-white border-none shadow-xl">
                        {label}
                      </TooltipContent>
                    </Tooltip>
                  );
                })}
              </div>
            </div>
          )}

          <div className="flex items-center gap-2 shrink-0 pl-2 sm:border-l sm:border-slate-200/60">
            {dossierId && (
              <Tooltip>
                <TooltipTrigger
                  render={<Link href="/" />}
                  className="flex items-center justify-center w-7 h-7 rounded-full text-slate-500 hover:bg-slate-100 hover:text-slate-800 transition-colors"
                >
                  <ArrowLeftRight className="w-3.5 h-3.5" />
                </TooltipTrigger>
                <TooltipContent side="bottom" className="bg-slate-800 text-white border-none shadow-xl">
                  {t.nav.switch}
                </TooltipContent>
              </Tooltip>
            )}

            <LanguageSwitcher />

            {isBackendOnline !== null && (
              <Tooltip>
                <TooltipTrigger
                  className={
                    "flex items-center justify-center w-7 h-7 rounded-full border shadow-sm transition-colors outline-none cursor-pointer shrink-0 " +
                    (isBackendOnline
                      ? "bg-emerald-50 border-emerald-200 text-emerald-700 hover:bg-emerald-100"
                      : "bg-red-50 border-red-200 text-red-700 hover:bg-red-100")
                  }
                >
                  {isBackendOnline ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
                </TooltipTrigger>
                <TooltipContent side="bottom" className="bg-slate-800 text-white border-none shadow-xl max-w-xs text-center">
                  {isBackendOnline ? t.nav.systemOnlineTooltip : t.nav.systemOfflineTooltip}
                </TooltipContent>
              </Tooltip>
            )}
          </div>
        </div>
      </nav>
    </TooltipProvider>
  );
}
