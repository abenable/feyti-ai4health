"use client";

import { Languages } from "lucide-react";

import { useLanguage, type Language } from "@/lib/i18n";

const OPTIONS: { value: Language; label: string }[] = [
  { value: "en", label: "English" },
  { value: "fr", label: "Français" },
  { value: "pt", label: "Português" },
  { value: "sw", label: "Kiswahili" },
];

export function LanguageSwitcher() {
  const { language, setLanguage, t } = useLanguage();

  return (
    <label className="flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-600 shadow-sm">
      <Languages className="h-3.5 w-3.5 text-indigo-600" />
      <span className="sr-only">{t.language.switch}</span>
      <select
        value={language}
        onChange={(event) => setLanguage(event.target.value as Language)}
        className="bg-transparent text-xs font-semibold outline-none"
        aria-label={t.language.label}
      >
        {OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
