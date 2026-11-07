"use client";

import React, { useState, useEffect } from "react";
import {
  MapPin,
  Navigation,
  Clock,
  Phone,
  ExternalLink,
  Copy,
  Check,
  LocateFixed,
  Building,
  Loader2,
  ChevronDown,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import {
  getCorridorCenters,
  findNearestCenter,
  type ApplicationCenter,
} from "@/lib/application-centers";

interface NearestCenterLocatorProps {
  jurisdictionCode?: string | null;
  className?: string;
  defaultExpanded?: boolean;
}

export function NearestCenterLocator({
  jurisdictionCode,
  className = "",
  defaultExpanded = true,
}: NearestCenterLocatorProps) {
  const corridor = getCorridorCenters(jurisdictionCode);
  const centers = corridor.centers;

  const storageKey = `torii_center_${corridor.jurisdictionCode}`;

  const [selectedCenterId, setSelectedCenterId] = useState<string>(corridor.defaultCenterId);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved && centers.some((c) => c.id === saved)) {
        setSelectedCenterId(saved);
      }
    } catch {
      // ignore
    }
  }, [storageKey, centers]);

  const [isDetecting, setIsDetecting] = useState(false);
  const [detectedDistance, setDetectedDistance] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const activeCenter: ApplicationCenter =
    centers.find((c) => c.id === selectedCenterId) || centers[0];

  const handleSelect = (centerId: string, distance?: number | null) => {
    setSelectedCenterId(centerId);
    setDetectedDistance(distance ?? null);
    if (typeof window !== "undefined") {
      localStorage.setItem(storageKey, centerId);
    }
  };

  const handleDetectLocation = () => {
    if (typeof window === "undefined" || !navigator.geolocation) {
      toast.error("Geolocation is not supported by your browser. Please pick your city below.");
      return;
    }

    setIsDetecting(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setIsDetecting(false);
        const { latitude, longitude } = position.coords;
        const result = findNearestCenter(latitude, longitude, centers);
        handleSelect(result.center.id, result.distanceKm);
        toast.success(
          `Nearest center detected: ${result.center.shortName} (~${result.distanceKm} km away)`
        );
      },
      (error) => {
        setIsDetecting(false);
        let msg = "Could not detect location. Please choose your city manually.";
        if (error.code === error.PERMISSION_DENIED) {
          msg = "Location permission denied. Please select your city from the options below.";
        }
        toast.error(msg);
      },
      { timeout: 8000, enableHighAccuracy: true }
    );
  };

  const handleCopyAddress = () => {
    if (!activeCenter) return;
    const fullText = `${activeCenter.name}\nAddress: ${activeCenter.address}\nTiming: ${activeCenter.hours}`;
    void navigator.clipboard.writeText(fullText);
    setCopied(true);
    toast.success("Center address and timings copied to clipboard");
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={`rounded-xl border border-border/70 bg-card/75 dark:bg-card/40 p-3.5 sm:p-4 text-xs transition-all shadow-2xs ${className}`}
    >
      {/* Header bar: Title + City Chips / Detect Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-3 border-b border-border/50">
        <div className="flex items-center gap-2">
          <div className="flex size-6 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
            <MapPin className="size-3.5" />
          </div>
          <div>
            <span className="font-bold text-foreground text-xs block">
              Where to Submit: Nearest Application Center
            </span>
            <span className="text-[11px] text-muted-foreground">
              Select your current location to get exact branch address, timings, and map route
            </span>
          </div>
        </div>

        {/* GPS Detect Button */}
        <div className="flex items-center gap-1.5 self-start sm:self-auto shrink-0">
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={handleDetectLocation}
            disabled={isDetecting}
            className="h-7 text-[11px] font-semibold gap-1 px-2.5 border-dashed border-primary/40 hover:bg-primary/10 text-primary cursor-pointer"
          >
            {isDetecting ? (
              <>
                <Loader2 className="size-3 animate-spin" />
                <span>Locating…</span>
              </>
            ) : (
              <>
                <LocateFixed className="size-3 text-primary" />
                <span>Detect Nearest (GPS)</span>
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Quick City Selection Chips */}
      <div className="flex flex-wrap items-center gap-1.5 pt-3 pb-2.5">
        <span className="text-[11px] font-medium text-muted-foreground mr-1">
          Your Location:
        </span>
        {centers.map((center) => {
          const isSelected = center.id === selectedCenterId;
          return (
            <button
              key={center.id}
              type="button"
              onClick={() => handleSelect(center.id)}
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                isSelected
                  ? "bg-primary text-primary-foreground shadow-xs ring-1 ring-primary"
                  : "bg-muted/70 text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              <MapPin className={`size-3 ${isSelected ? "text-primary-foreground" : "text-muted-foreground"}`} />
              <span>{center.city}</span>
            </button>
          );
        })}
      </div>

      {/* Active Center Card */}
      <div className="mt-1 rounded-lg border border-border/80 bg-background/90 p-3 sm:p-3.5 space-y-2.5">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
          <div className="space-y-0.5">
            <div className="flex flex-wrap items-center gap-1.5">
              <h4 className="font-bold text-foreground text-xs sm:text-sm">
                {activeCenter.name}
              </h4>
              <Badge tone="default" className="text-[10px] font-semibold py-0">
                Official Center
              </Badge>
              {detectedDistance !== null && (
                <Badge tone="success" className="text-[10px] font-bold py-0">
                  ~{detectedDistance} km away
                </Badge>
              )}
            </div>
            <p className="text-[11px] text-muted-foreground flex items-start gap-1 mt-1 leading-snug">
              <span className="font-semibold text-foreground shrink-0">Address:</span>
              <span>{activeCenter.address}</span>
            </p>
          </div>

          {/* Action Links: Google Maps & Copy Address */}
          <div className="flex items-center gap-1.5 shrink-0 pt-1 sm:pt-0">
            <a
              href={activeCenter.mapsUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-1 rounded-md bg-emerald-600 hover:bg-emerald-700 text-white px-2.5 py-1.5 text-[11px] font-bold transition-colors shadow-2xs cursor-pointer"
            >
              <Navigation className="size-3" />
              <span>Get Directions</span>
              <ExternalLink className="size-2.5 opacity-70 ml-0.5" />
            </a>

            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleCopyAddress}
              className="h-7 text-[11px] px-2 gap-1 text-muted-foreground hover:text-foreground cursor-pointer"
              title="Copy Address"
            >
              {copied ? (
                <>
                  <Check className="size-3 text-emerald-500" />
                  <span className="text-emerald-600 dark:text-emerald-400 font-semibold">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="size-3" />
                  <span>Copy</span>
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Operating Hours & Notes */}
        <div className="pt-2 border-t border-border/50 flex flex-wrap items-center justify-between gap-y-1.5 gap-x-4 text-[11px] text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <Clock className="size-3 text-amber-500 shrink-0" />
            <span>
              <strong className="text-foreground">Working Hours:</strong> {activeCenter.hours}
            </span>
          </div>

          {activeCenter.submissionHours && (
            <div className="flex items-center gap-1 text-muted-foreground">
              <span>{activeCenter.submissionHours}</span>
            </div>
          )}

          {activeCenter.phone && (
            <div className="flex items-center gap-1">
              <Phone className="size-3 text-primary shrink-0" />
              <span>{activeCenter.phone}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
