"use client";

import React, { useState, useEffect } from "react";
import { UserRole, UserProfile } from "@/lib/types";
import { loginApi } from "@/lib/api";
import { Shield, UserCheck, KeyRound, LogOut } from "lucide-react";

interface RoleSelectorProps {
  currentRole: UserRole;
  onUserChange: (user: UserProfile) => void;
}

const DEMO_CREDENTIALS: Record<UserRole, { username: string; pass: string; title: string }> = {
  admin: { username: "admin", pass: "adminpassword", title: "System Administrator" },
  policymaker: { username: "policymaker", pass: "policypassword", title: "MoRD Policymaker" },
  project_manager: { username: "project_manager", pass: "pmpassword", title: "Project Manager (North Zone)" },
};

export function RoleSelector({ currentRole, onUserChange }: RoleSelectorProps) {
  const [loading, setLoading] = useState(false);

  const handleRoleSelect = async (role: UserRole) => {
    const creds = DEMO_CREDENTIALS[role];
    setLoading(true);
    try {
      const res = await loginApi(creds.username, creds.pass);
      localStorage.setItem("sih_auth_token", res.access_token);
      localStorage.setItem("sih_user_role", res.user.role);
      onUserChange(res.user);
    } catch (err) {
      console.error("Login failed, falling back to client profile:", err);
      onUserChange({
        username: creds.username,
        name: creds.title,
        role: role,
        region: role === "project_manager" ? "North" : "All",
        department: "Ministry of Rural Development",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center gap-1.5 rounded-md border border-line/70 dark:border-[#2A3742] bg-surface/70 dark:bg-[#141D26]/70 px-1.5 py-1 text-xs">
      <span className="text-[10px] uppercase tracking-wide text-ink/40 dark:text-[#717870]">
        Role
      </span>

      <select
        value={currentRole}
        onChange={(e) =>
          handleRoleSelect(e.target.value as UserRole)
        }
        disabled={loading}
        className="bg-transparent text-xs font-medium text-ink dark:text-gray-200 outline-none cursor-pointer disabled:opacity-50"
        aria-label="Current role"
      >
        <option value="admin">Administrator</option>
        <option value="policymaker">Policymaker</option>
        <option value="project_manager">Project Manager</option>
      </select>
    </div>
  );
}