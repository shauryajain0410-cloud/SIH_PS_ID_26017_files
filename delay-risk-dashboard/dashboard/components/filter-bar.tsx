"use client";

import React from "react";
import { Search, Filter, RotateCcw } from "lucide-react";

interface FilterBarProps {
  regions: string[];
  sectors: string[];
  region: string;
  sector: string;
  risk: string;
  dataCompleteness: string;
  search: string;
  onRegionChange: (v: string) => void;
  onSectorChange: (v: string) => void;
  onRiskChange: (v: string) => void;
  onDataCompletenessChange: (v: string) => void;
  onSearchChange: (v: string) => void;
  onReset: () => void;
}

export function FilterBar({
  regions,
  sectors,
  region,
  sector,
  risk,
  dataCompleteness,
  search,
  onRegionChange,
  onSectorChange,
  onRiskChange,
  onDataCompletenessChange,
  onSearchChange,
  onReset,
}: FilterBarProps) {
  return (
    <div className="bg-surface dark:bg-[#141D26] border border-line dark:border-[#2A3742] p-3.5 rounded-lg flex flex-wrap items-center gap-2.5 text-xs">
      <div className="flex items-center gap-1.5 text-ink/60 dark:text-[#8A9086] font-semibold uppercase tracking-wider text-[10px] mr-1">
        <Filter size={13} />
        Filters:
      </div>

      {/* Region Filter */}
      <select
        value={region}
        onChange={(e) => onRegionChange(e.target.value)}
        className="border border-line dark:border-[#2A3742] rounded bg-paper dark:bg-slate-800 text-ink dark:text-gray-200 px-2.5 py-1.5 focus:outline-none focus:border-teal"
      >
        <option value="All">All Regions</option>

        {regions.map((r) => (
          <option key={r} value={r}>
            {r}
          </option>
        ))}
      </select>

      {/* Sector Filter */}
      <select
        value={sector}
        onChange={(e) => onSectorChange(e.target.value)}
        className="border border-line dark:border-[#2A3742] rounded bg-paper dark:bg-slate-800 text-ink dark:text-gray-200 px-2.5 py-1.5 focus:outline-none focus:border-teal max-w-[200px]"
      >
        <option value="All">All Sectors</option>

        {sectors.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>

      {/* Risk Category Filter */}
      <select
        value={risk}
        onChange={(e) => onRiskChange(e.target.value)}
        className="border border-line dark:border-[#2A3742] rounded bg-paper dark:bg-slate-800 text-ink dark:text-gray-200 px-2.5 py-1.5 focus:outline-none focus:border-teal"
      >
        <option value="All">All Risk Tiers</option>
        <option value="High">High Risk (&gt;65%)</option>
        <option value="Medium">Medium Risk (35–65%)</option>
        <option value="Low">Low Risk (&lt;35%)</option>
      </select>

      {/* Data Completeness Filter */}
      <select
        value={dataCompleteness}
        onChange={(e) => onDataCompletenessChange(e.target.value)}
        className="border border-line dark:border-[#2A3742] rounded bg-paper dark:bg-slate-800 text-ink dark:text-gray-200 px-2.5 py-1.5 focus:outline-none focus:border-teal"
      >
        <option value="All">All Data Completeness</option>
        <option value="Complete Data">Complete Data</option>
        <option value="Partial Data">Partial Data</option>
        <option value="Sparse Data">Sparse Data</option>
      </select>

      {/* Search Input */}
      <div className="relative flex-1 min-w-[170px]">
        <Search
          size={14}
          className="absolute left-2.5 top-2 text-ink/40"
        />

        <input
          type="text"
          placeholder="Search project ID or keyword..."
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full border border-line dark:border-[#2A3742] rounded bg-paper dark:bg-slate-800 text-ink dark:text-gray-200 pl-8 pr-2.5 py-1.5 focus:outline-none focus:border-teal"
        />
      </div>

      {/* Reset Filters */}
      {(
        region !== "All" ||
        sector !== "All" ||
        risk !== "All" ||
        dataCompleteness !== "All" ||
        search
      ) && (
        <button
          onClick={onReset}
          className="flex items-center gap-1 text-[11px] text-ink/60 hover:text-ink dark:text-gray-400 dark:hover:text-white px-2 py-1.5"
          title="Reset all filters"
        >
          <RotateCcw size={12} />
          Reset
        </button>
      )}
    </div>
  );
}