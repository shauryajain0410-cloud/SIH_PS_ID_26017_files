"use client";

import React, { useState } from "react";
import { ProjectListItem, RiskCategory } from "@/lib/types";
import { formatCrore, formatPct, RISK_COLORS, RISK_BG } from "@/lib/format";
import { ArrowUpDown, AlertCircle, ChevronLeft, ChevronRight, Search, SlidersHorizontal } from "lucide-react";

interface ProjectsTableProps {
  projects: ProjectListItem[];
  totalCount: number;
  page: number;
  totalPages: number;
  pageSize: number;
  onPageChange: (newPage: number) => void;
  onSortChange: (column: string) => void;
  sortBy: string;
  sortOrder: string;
  onSelectProject: (projectId: string) => void;
  userRole?: string;
}

export function ProjectsTable({
  projects,
  totalCount,
  page,
  totalPages,
  pageSize,
  onPageChange,
  onSortChange,
  sortBy,
  sortOrder,
  onSelectProject,
  userRole,
}: ProjectsTableProps) {
  const isPolicymaker = userRole === "policymaker";

  return (
    <div className="space-y-4">
      {/* Table Container */}
      <div className="overflow-x-auto rounded-lg border border-line dark:border-[#2A3742] bg-surface dark:bg-[#141D26]">
        <table className="w-full text-xs text-left border-collapse">
          <thead>
            <tr className="border-b border-line dark:border-[#2A3742] bg-slate-50/80 dark:bg-slate-900/60 font-semibold text-ink/70 dark:text-[#8A9086]">
              <th
                onClick={() => onSortChange("project_id")}
                className="py-3 px-3.5 cursor-pointer hover:text-ink select-none"
              >
                <div className="flex items-center gap-1">
                  Project ID
                  <ArrowUpDown size={12} />
                </div>
              </th>
              <th className="py-3 px-3">Sector &amp; Region</th>
              <th
                onClick={() => onSortChange("predicted_delay_probability")}
                className="py-3 px-3 text-center cursor-pointer hover:text-ink select-none"
              >
                <div className="flex items-center justify-center gap-1">
                  Predicted Delay %
                  <ArrowUpDown size={12} />
                </div>
              </th>
              <th className="py-3 px-3 text-center">Risk Tier</th>
              <th className="py-3 px-3">Top Delay Drivers</th>
              <th className="py-3 px-3">Data Completeness</th>
              <th className="py-3 px-3 text-right">Physical Progress</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line/60 dark:divide-[#2A3742]/60">
            {projects.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-ink/50 dark:text-[#8A9086]">
                  No matching projects found in the inference register.
                </td>
              </tr>
            ) : (
              projects.map((p) => (
                <tr
                  key={p.project_id}
                  onClick={() => {
                    if (!isPolicymaker) {
                      onSelectProject(p.project_id);
                    }
                  }}
                  className={`transition-colors ${
                    isPolicymaker
                      ? "cursor-default opacity-90"
                      : "cursor-pointer hover:bg-slate-50/80 dark:hover:bg-slate-900/40"
                  }`}
                >
                  {/* Project ID */}
                  <td className="py-2.5 px-3.5 font-mono font-medium text-ink dark:text-white">
                    <div className="flex items-center gap-1.5">
                      <span className="hover:underline">{p.project_id}</span>
                      <span className="text-[10px] text-ink/40 dark:text-gray-500 font-sans">
                        ({p.quarter})
                      </span>
                    </div>
                  </td>

                  {/* Sector & Region */}
                  <td className="py-2.5 px-3">
                    <div className="font-medium text-ink dark:text-gray-200 truncate max-w-[220px]">
                      {p.sector_extracted}
                    </div>
                    <div className="text-[11px] text-ink/50 dark:text-[#8A9086]">
                      {p.region_final} Region
                    </div>
                  </td>

                  {/* Predicted Delay Probability % */}
                  <td className="py-2.5 px-3 text-center">
                    <span className="font-mono text-sm font-semibold">
                      {((p.predicted_delay_probability ?? 0) * 100).toFixed(1)}%
                    </span>
                  </td>

                  {/* Risk Tier Badge */}
                  <td className="py-2.5 px-3 text-center">
                    <span
                      className="px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-wide inline-block"
                      style={{
                        backgroundColor: RISK_BG[p.risk_category],
                        color: RISK_COLORS[p.risk_category],
                      }}
                    >
                      {p.risk_category}
                    </span>
                  </td>

                  {/* Top Delay Drivers */}
                  <td className="py-2.5 px-3 max-w-[260px]">
                    <div className="flex flex-wrap gap-1">
                      {(p.top_contributing_drivers ?? []).slice(0, 2).map((driver, idx) => (
                        <span
                          key={idx}
                          className="bg-paper dark:bg-slate-800 border border-line dark:border-[#2A3742] text-[10px] px-1.5 py-0.5 rounded text-ink/70 dark:text-[#B9BEB2] truncate max-w-[170px]"
                          title={driver}
                        >
                          {driver}
                        </span>
                      ))}
                      {(p.top_contributing_drivers ?? []).length > 2 && (
                        <span className="text-[10px] text-ink/40 dark:text-[#8A9086] self-center">
                          +{(p.top_contributing_drivers ?? []).length - 2}
                        </span>
                      )}
                    </div>
                  </td>

                  {/* Data Completeness Badge */}
                  <td className="py-2.5 px-3">
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full border font-medium whitespace-nowrap ${
                        p.data_completeness === "Complete Data"
                          ? "border-emerald-300 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-300"
                          : p.data_completeness === "Partial Data"
                          ? "border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-300"
                          : "border-red-300 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-300"
                      }`}
                      title={`${p.missing_field_count} missing input field${
                        p.missing_field_count === 1 ? "" : "s"
                      }`}
                    >
                      {p.data_completeness}
                    </span>
                  </td>

                  {/* Physical Progress */}
                  <td className="py-2.5 px-3 text-right font-mono">
                    {p.physical_progress_pct ? `${p.physical_progress_pct.toFixed(1)}%` : "0.0%"}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-ink/60 dark:text-[#8A9086] px-1">
        <div>
          Showing{" "}
          <strong className="text-ink dark:text-white">
            {projects.length ? (page - 1) * pageSize + 1 : 0}
          </strong>{" "}
          to{" "}
          <strong className="text-ink dark:text-white">
            {Math.min(page * pageSize, totalCount)}
          </strong>{" "}
          of <strong className="text-ink dark:text-white">{totalCount}</strong> monitored projects
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="p-1.5 rounded border border-line dark:border-[#2A3742] disabled:opacity-30 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          >
            <ChevronLeft size={14} />
          </button>
          <span>
            Page <strong className="text-ink dark:text-white">{page}</strong> of{" "}
            <strong className="text-ink dark:text-white">{totalPages}</strong>
          </span>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            className="p-1.5 rounded border border-line dark:border-[#2A3742] disabled:opacity-30 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          >
            <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
