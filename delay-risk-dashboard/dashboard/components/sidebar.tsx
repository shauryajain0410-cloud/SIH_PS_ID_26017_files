"use client";

import React from "react";
import { UserRole } from "@/lib/types";
import { LayoutDashboard, TableProperties, Map, Bell, Cpu, FileText } from "lucide-react";

export type NavSection = "overview" | "register" | "regional" | "alerts" | "model" | "predict-new"; 

interface SidebarProps {
  activeSection: NavSection;
  onSectionChange: (section: NavSection) => void;
  userRole: UserRole;
  alertCount?: number;
}

export function Sidebar({
  activeSection,
  onSectionChange,
  userRole,
  alertCount = 0,
}: SidebarProps) {
  const navItems: { id: NavSection; label: string; icon: any; roles: UserRole[]; badge?: number }[] = [
    {
      id: "overview",
      label: "Executive Overview",
      icon: LayoutDashboard,
      roles: ["admin", "policymaker"],
    },
    {
      id: "register",
      label: "Risk Register",
      icon: TableProperties,
      roles: ["admin", "project_manager"],
    },
    {
    id: "predict-new",
    label: "Predict New Project",
    icon: FileText,
    roles: ["admin", "project_manager"],
    },
    {
      id: "regional",
      label: "Regional Analytics",
      icon: Map,
      roles: ["admin", "policymaker"],
    },
    {
      id: "alerts",
      label: "Alerts Feed",
      icon: Bell,
      roles: ["admin", "policymaker", "project_manager"],
      badge: alertCount,
    },
    {
      id: "model",
      label: "Model Governance",
      icon: Cpu,
      roles: ["admin"],
    },
  ];

  return (
    <aside className="hidden lg:flex flex-col w-60 shrink-0 border-r border-line dark:border-[#2A3742] py-6 pr-4 sticky top-0 h-screen bg-surface dark:bg-[#141D26]">
      {/* Brand Header */}
      <div className="px-3 mb-6">
        <span className="text-[10px] font-mono uppercase tracking-widest text-teal font-semibold">
          MoRD &bull; SIH 26017
        </span>
        <h2 className="font-serif text-base font-bold text-ink dark:text-white leading-tight mt-0.5">
          Land Acquisition Delay Predictor
        </h2>
      </div>

      {/* Navigation Links */}
      <nav className="flex flex-col gap-1 flex-1">
        {navItems.map((item) => {
          const isAllowed = item.roles.includes(userRole);
          const isActive = activeSection === item.id;
          const Icon = item.icon;

          return (
            <button
              key={item.id}
              onClick={() => {
                if (isAllowed) onSectionChange(item.id);
              }}
              disabled={!isAllowed}
              className={`flex items-center justify-between text-left text-xs px-3 py-2.5 rounded-lg font-medium transition-all ${
                isActive
                  ? "bg-teal text-white shadow-sm"
                  : isAllowed
                  ? "text-ink/70 dark:text-gray-300 hover:bg-slate-100 dark:hover:bg-slate-800"
                  : "text-ink/30 dark:text-gray-600 cursor-not-allowed opacity-50"
              }`}
            >
              <div className="flex items-center gap-2.5">
                <Icon size={16} />
                <span>{item.label}</span>
              </div>
              {item.badge !== undefined && item.badge > 0 && (
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono font-bold ${
                    isActive ? "bg-white text-teal" : "bg-red-500 text-white"
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Role Scoping Notice */}
      <div className="mt-auto px-3 pt-4 border-t border-line dark:border-[#2A3742] text-[11px] text-ink/50 dark:text-[#8A9086]">
        {userRole === "policymaker" && (
          <p className="leading-tight">
            Policy View: Aggregated metrics active. Individual project narratives restricted.
          </p>
        )}
        {userRole === "project_manager" && (
          <p className="leading-tight">
            Project Manager View: Scoped to assigned zone (North Region).
          </p>
        )}
        {userRole === "admin" && (
          <p className="leading-tight">
            Admin View: Full platform access — all regions, inference logs, and model audit trail.
          </p>
        )}
      </div>
    </aside>
  );
}
