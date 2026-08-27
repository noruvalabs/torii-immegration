"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import { Search, ChevronDown, Check, X } from "lucide-react";
import { ALL_COUNTRIES, matchCountry, type Country } from "@/lib/countries";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type CountrySelectorProps = {
  value?: string | null;
  onChange: (value: string, country: Country) => void;
  valueType?: "name" | "code";
  mode?: "combobox" | "grid";
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  gridMaxHeightClass?: string;
  gridColsClass?: string;
  id?: string;
  autoFocus?: boolean;
  autoFillSearch?: boolean;
};

export function CountrySelector({
  value,
  onChange,
  valueType = "name",
  mode = "combobox",
  placeholder = "Select country...",
  disabled = false,
  className,
  gridMaxHeightClass = "max-h-56",
  gridColsClass = "sm:grid-cols-2",
  id,
  autoFillSearch = false,
}: CountrySelectorProps) {
  const selectedCountry = useMemo(() => {
    if (!value) return null;
    return matchCountry(value);
  }, [value]);

  const [search, setSearch] = useState(() => {
    if (autoFillSearch && value) {
      const matched = matchCountry(value);
      return matched ? matched.name : "";
    }
    return "";
  });
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Sync search input when value prop changes
  const prevValueRef = useRef(value);
  useEffect(() => {
    if (value !== prevValueRef.current) {
      prevValueRef.current = value;
      if (autoFillSearch && value) {
        const matched = matchCountry(value);
        if (matched) {
          setSearch(matched.name);
        }
      }
    }
  }, [value, autoFillSearch]);

  const filteredCountries = useMemo(() => {
    if (!search.trim()) {
      if (selectedCountry) {
        return [
          selectedCountry,
          ...ALL_COUNTRIES.filter((c) => c.code !== selectedCountry.code),
        ];
      }
      return ALL_COUNTRIES;
    }
    const q = search.trim().toLowerCase();
    const matches = ALL_COUNTRIES.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.code.toLowerCase() === q ||
        (c.currency && c.currency.toLowerCase().includes(q)),
    );

    return matches.sort((a, b) => {
      const aExact = a.name.toLowerCase() === q || a.code.toLowerCase() === q;
      const bExact = b.name.toLowerCase() === q || b.code.toLowerCase() === q;
      if (aExact && !bExact) return -1;
      if (!aExact && bExact) return 1;
      const aStarts = a.name.toLowerCase().startsWith(q);
      const bStarts = b.name.toLowerCase().startsWith(q);
      if (aStarts && !bStarts) return -1;
      if (!aStarts && bStarts) return 1;
      return 0;
    });
  }, [search, selectedCountry]);

  // Close dropdown on outside click
  useEffect(() => {
    if (mode !== "combobox" || !isOpen) return;
    function handleClickOutside(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, mode]);

  useEffect(() => {
    if (isOpen && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isOpen]);

  function handleSelect(country: Country) {
    const val = valueType === "code" ? country.code : country.name;
    onChange(val, country);
    setIsOpen(false);
    if (autoFillSearch) {
      setSearch(country.name);
    } else {
      setSearch("");
    }
  }

  /* Grid mode rendering (used for large interactive selection steps) */
  if (mode === "grid") {
    return (
      <div className={cn("space-y-3", className)}>
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onFocus={(e) => e.target.select()}
            placeholder="Search all 240+ countries..."
            className="h-9 w-full rounded-[var(--radius)] border bg-background pl-9 pr-8 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          {search && (
            <button
              type="button"
              onClick={() => setSearch("")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground p-0.5 rounded hover:bg-muted"
              aria-label="Clear search"
            >
              <X className="size-3.5" />
            </button>
          )}
        </div>

        {filteredCountries.length === 0 ? (
          <div className="py-6 text-center text-xs text-muted-foreground space-y-2">
            <p>No country matches &ldquo;{search}&rdquo;</p>
            <button
              type="button"
              onClick={() => setSearch("")}
              className="text-xs text-primary font-medium hover:underline"
            >
              View all 240+ countries
            </button>
          </div>
        ) : (
          <div
            className={cn(
              "grid gap-2 overflow-y-auto pr-1",
              gridColsClass,
              gridMaxHeightClass,
            )}
          >
            {filteredCountries.map((c) => {
              const isSelected =
                valueType === "code"
                  ? selectedCountry?.code === c.code
                  : selectedCountry?.name.toLowerCase() === c.name.toLowerCase();

              return (
                <button
                  key={c.code}
                  type="button"
                  onClick={() => handleSelect(c)}
                  className={cn(
                    "flex items-center gap-3 rounded-[var(--radius)] border p-2.5 text-left text-sm transition-colors",
                    isSelected
                      ? "border-primary bg-primary/10 font-semibold text-primary shadow-sm ring-1 ring-primary/30"
                      : "bg-card hover:bg-accent text-foreground",
                  )}
                >
                  <span
                    className="inline-flex size-7 shrink-0 items-center justify-center rounded bg-muted/60 text-xs font-semibold"
                    aria-hidden
                  >
                    {c.flag}
                  </span>
                  <span className="min-w-0 flex-1 truncate font-medium">
                    {c.name}
                  </span>
                  {isSelected && (
                    <Badge tone="success" className="text-[10px] py-0 px-1.5 shrink-0">
                      Selected
                    </Badge>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  /* Combobox / Dropdown mode (used in standard forms like profile) */
  return (
    <div ref={containerRef} className={cn("relative w-full", className)}>
      <button
        id={id}
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen((prev) => !prev)}
        className={cn(
          "flex h-10 w-full items-center justify-between rounded-[var(--radius)] border border-input bg-background px-3 py-2 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-50",
          isOpen && "ring-2 ring-primary border-primary",
        )}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <span className="flex items-center gap-2.5 truncate">
          {selectedCountry ? (
            <>
              <span
                className="inline-flex size-6 shrink-0 items-center justify-center rounded bg-muted/70 text-xs font-semibold"
                aria-hidden
              >
                {selectedCountry.flag}
              </span>
              <span className="font-medium text-foreground">
                {selectedCountry.name}
              </span>
              <span className="rounded bg-muted/80 px-1 py-0.5 font-mono text-[10px] text-muted-foreground">
                {selectedCountry.code}
              </span>
            </>
          ) : (
            <span className="text-muted-foreground">{placeholder}</span>
          )}
        </span>
        <ChevronDown
          className={cn(
            "size-4 shrink-0 text-muted-foreground transition-transform duration-200",
            isOpen && "rotate-180",
          )}
        />
      </button>

      {isOpen && (
        <div className="absolute left-0 top-full z-50 mt-1.5 flex max-h-72 w-full flex-col overflow-hidden rounded-[var(--radius)] border border-border bg-card text-card-foreground shadow-2xl animate-in fade-in-0 zoom-in-95">
          <div className="border-b border-border bg-card p-2">
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
              <input
                ref={searchInputRef}
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search country..."
                className="h-8 w-full rounded-md border border-border bg-background pl-8 pr-7 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
              {search && (
                <button
                  type="button"
                  onClick={() => setSearch("")}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  <X className="size-3" />
                </button>
              )}
            </div>
          </div>

          <div
            className="max-h-56 flex-1 overflow-y-auto bg-card p-1.5 space-y-0.5"
            role="listbox"
          >
            {filteredCountries.length === 0 ? (
              <p className="py-6 text-center text-xs text-muted-foreground">
                No country found.
              </p>
            ) : (
              filteredCountries.map((c) => {
                const isSelected =
                  valueType === "code"
                    ? selectedCountry?.code === c.code
                    : selectedCountry?.name.toLowerCase() ===
                      c.name.toLowerCase();

                return (
                  <button
                    key={c.code}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => handleSelect(c)}
                    className={cn(
                      "flex w-full items-center gap-2.5 rounded-[var(--radius)] px-2.5 py-1.5 text-left text-xs transition-colors",
                      isSelected
                        ? "bg-primary text-primary-foreground font-semibold"
                        : "hover:bg-accent hover:text-accent-foreground text-foreground",
                    )}
                  >
                    <span
                      className={cn(
                        "inline-flex size-6 shrink-0 items-center justify-center rounded text-xs font-semibold",
                        isSelected
                          ? "bg-primary-foreground/20 text-primary-foreground"
                          : "bg-muted/70 text-foreground",
                      )}
                      aria-hidden
                    >
                      {c.flag}
                    </span>
                    <span className="min-w-0 flex-1 truncate">{c.name}</span>
                    <span
                      className={cn(
                        "rounded px-1 py-0.5 font-mono text-[10px]",
                        isSelected
                          ? "bg-primary-foreground/20 text-primary-foreground"
                          : "bg-muted/80 text-muted-foreground",
                      )}
                    >
                      {c.code}
                    </span>
                    {isSelected && <Check className="size-3.5 shrink-0 ml-1" />}
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
