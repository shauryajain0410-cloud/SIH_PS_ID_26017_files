"use client";

import React, { useState } from "react";
import { HeatmapMatrixRow, ProgressTimelinePoint } from "@/lib/types";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import { TrendingUp, Grid } from "lucide-react";

interface ComparativeMatrixProps {
  regions: string[];
  matrix: HeatmapMatrixRow[];
  timeline: ProgressTimelinePoint[];
}

export function ComparativeMatrix({ regions, matrix, timeline }: ComparativeMatrixProps) {
  const [metricMode, setMetricMode] = useState<"delay_rate" | "avg_prob">("delay_rate");
  const [selectedSector, setSelectedSector] = useState<string>("All Sectors");

  // Helper to get color shade based on delay rate (0 - 100%)
  const getCellBg = (rate: number, count: number) => {
    if (count === 0) return "bg-gray-50/50 dark:bg-gray-900/30 text-ink/30 dark:text-gray-600";
    if (rate >= 80) return "bg-red-200/90 dark:bg-red-950/80 text-red-900 dark:text-red-200 font-semibold";
    if (rate >= 65) return "bg-red-100 dark:bg-red-950/50 text-red-800 dark:text-red-300 font-semibold";
    if (rate >= 45) return "bg-amber-100 dark:bg-amber-950/50 text-amber-800 dark:text-amber-300";
    if (rate >= 25) return "bg-emerald-50 dark:bg-emerald-950/30 text-emerald-800 dark:text-emerald-300";
    return "bg-emerald-100 dark:bg-emerald-950/60 text-emerald-900 dark:text-emerald-200";
  };

  return (
    <div className="space-y-8">
      {/* 1. Sector x Region Heatmap Table */}
      <div className="bg-surface dark:bg-[#141D26] border border-line dark:border-[#2A3742] rounded-lg p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <Grid size={18} className="text-teal" />
              <h3 className="font-serif text-lg font-semibold">Sector × Region Delay Risk Matrix</h3>
            </div>
            <p className="text-xs text-ink/60 dark:text-[#8A9086] mt-0.5">
              Heatmap comparison of delay incidence across top infrastructure sectors and geographical zones
            </p>
          </div>

          <div className="flex items-center gap-2 bg-paper dark:bg-slate-800 p-1 rounded border border-line dark:border-[#2A3742] text-xs">
            <button
              onClick={() => setMetricMode("delay_rate")}
              className={`px-2.5 py-1 rounded transition-colors ${
                metricMode === "delay_rate"
                  ? "bg-surface dark:bg-[#141D26] font-medium shadow-sm"
                  : "text-ink/60 dark:text-gray-400 hover:text-ink"
              }`}
            >
              High-Risk Rate (%)
            </button>
            <button
              onClick={() => setMetricMode("avg_prob")}
              className={`px-2.5 py-1 rounded transition-colors ${
                metricMode === "avg_prob"
                  ? "bg-surface dark:bg-[#141D26] font-medium shadow-sm"
                  : "text-ink/60 dark:text-gray-400 hover:text-ink"
              }`}
            >
              Avg Delay Probability
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className="border-b border-line dark:border-[#2A3742] bg-slate-50 dark:bg-slate-900/50">
                <th className="py-2.5 px-3 font-semibold text-ink/70 dark:text-[#8A9086]">Sector</th>
                {regions.map((reg) => (
                  <th key={reg} className="py-2.5 px-3 font-semibold text-center text-ink/70 dark:text-[#8A9086]">
                    {reg}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {matrix.map((row) => (
                <tr key={row.sector} className="border-b border-line/60 dark:border-[#2A3742]/60 hover:bg-slate-50/50 dark:hover:bg-slate-900/30">
                  <td className="py-2 px-3 font-medium text-ink dark:text-white max-w-[200px] truncate">
                    {row.sector}
                  </td>
                  {regions.map((reg) => {
                    const cell = row.regions[reg] || { count: 0, avg_prob: 0, delay_rate: 0 };
                    return (
                      <td
                        key={reg}
                        className={`py-2 px-2 text-center transition-colors rounded ${getCellBg(
                          cell.delay_rate,
                          cell.count
                        )}`}
                        title={`${row.sector} in ${reg}: ${cell.count} projects, ${cell.delay_rate}% high risk`}
                      >
                        {cell.count > 0 ? (
                          <div>
                            <div>
                              {metricMode === "delay_rate"
                                ? `${cell.delay_rate.toFixed(0)}%`
                                : `${(cell.avg_prob * 100).toFixed(0)}%`}
                            </div>
                            <div className="text-[10px] opacity-75 font-normal">
                              ({cell.count} proj)
                            </div>
                          </div>
                        ) : (
                          <span className="text-ink/25 dark:text-gray-600">—</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 2. Timeline Analysis: Progress Trajectory Across Quarters */}
      <div className="bg-surface dark:bg-[#141D26] border border-line dark:border-[#2A3742] rounded-lg p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <TrendingUp size={18} className="text-teal" />
              <h3 className="font-serif text-lg font-semibold">Quarterly Progress Trajectory</h3>
            </div>
            <p className="text-xs text-ink/60 dark:text-[#8A9086] mt-0.5">
              Comparing physical progress and land acquisition completion across reporting quarters
            </p>
          </div>
        </div>

                <div className="space-y-8">

          {/* Physical Progress */}
          <div>
            <p className="text-xs text-ink/60 dark:text-[#8A9086] mb-2">
              Average physical progress by risk group
            </p>

            <div className="h-[260px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={timeline}
                  margin={{
                    top: 10,
                    right: 20,
                    left: 0,
                    bottom: 20,
                  }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="#88888820"
                  />

                  <XAxis
                    dataKey="quarter"
                    interval={3}
                    tick={{ fontSize: 11 }}
                    angle={-30}
                    textAnchor="end"
                  />

                  <YAxis
                    tick={{ fontSize: 11 }}
                    domain={[0, 100]}
                    unit="%"
                  />

                  <Tooltip
                    offset={15}
                    wrapperStyle={{
                      transform: "translateY(-25px)",
                      pointerEvents: "none",
                    }}
                    contentStyle={{
                      backgroundColor: "#1F2937",
                      borderColor: "#374151",
                      borderRadius: 6,
                      color: "#F9FAFB",
                      fontSize: 11,
                      padding: "8px 10px",
                    }}
                    formatter={(value: number | string, name: string) => [
                      `${Number(value).toFixed(1)}%`,
                      name,
                    ]}
                  />

                  <Legend
                    wrapperStyle={{
                      fontSize: 12,
                      paddingTop: 10,
                    }}
                  />

                  <Line
                    type="monotone"
                    dataKey="ontrack_physical_progress"
                    name="On-Track Physical Progress"
                    stroke="#16A34A"
                    strokeWidth={2.5}
                    dot={{ r: 3 }}
                  />

                  <Line
                    type="monotone"
                    dataKey="high_risk_physical_progress"
                    name="High-Risk Physical Progress"
                    stroke="#DC2626"
                    strokeWidth={2.5}
                    dot={{ r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Land Acquisition */}
          <div>
            <p className="text-xs text-ink/60 dark:text-[#8A9086] mb-2">
              Percentage of projects with land fully acquired
            </p>

            <div className="h-[260px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={timeline}
                  margin={{
                    top: 10,
                    right: 20,
                    left: 0,
                    bottom: 20,
                  }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="#88888820"
                  />

                  <XAxis
                    dataKey="quarter"
                    interval={3}
                    tick={{ fontSize: 11 }}
                    angle={-30}
                    textAnchor="end"
                  />

                  <YAxis
                    tick={{ fontSize: 11 }}
                    domain={[0, 100]}
                    unit="%"
                  />

                  <Tooltip
                    offset={15}
                    wrapperStyle={{
                      transform: "translateY(-25px)",
                      pointerEvents: "none",
                    }}
                    contentStyle={{
                      backgroundColor: "#1F2937",
                      borderColor: "#374151",
                      borderRadius: 6,
                      color: "#F9FAFB",
                      fontSize: 11,
                      padding: "8px 10px",
                    }}
                    formatter={(value: number | string, name: string) => [
                      `${Number(value).toFixed(1)}%`,
                      name,
                    ]}
                  />

                  <Legend
                    wrapperStyle={{
                      fontSize: 12,
                      paddingTop: 10,
                    }}
                  />

                  <Bar
                    dataKey="ontrack_land_complete_pct"
                    name="On-Track Fully Acquired"
                    fill="#0284C7"
                    radius={[3, 3, 0, 0]}
                  />

                  <Bar
                    dataKey="high_risk_land_complete_pct"
                    name="High-Risk Fully Acquired"
                    fill="#D97706"
                    radius={[3, 3, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
