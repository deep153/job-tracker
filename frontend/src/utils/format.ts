import type { FilterRule, Job } from "../types/job";
import type { Platform } from "../types/searchSettings";

export const PLATFORM_LABELS: Record<Platform, string> = {
  greenhouse: "Greenhouse",
  lever: "Lever",
  ashby: "Ashby",
};

export const FILTER_LABELS: Record<FilterRule, string> = {
  role: "Role",
  excluded_keyword: "Excluded keyword",
  location: "Location",
  seniority: "Seniority",
  experience: "Experience",
  sponsorship: "Sponsorship",
  salary: "Salary",
};

/** Near misses: jobs whose title matched one of my roles but that another filter dropped. */
export function nearMisses(counts: Record<FilterRule, number>): number {
  return Object.entries(counts).reduce((sum, [rule, n]) => (rule === "role" ? sum : sum + n), 0);
}

const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 365 * 24 * 3600],
  ["month", 30 * 24 * 3600],
  ["week", 7 * 24 * 3600],
  ["day", 24 * 3600],
  ["hour", 3600],
  ["minute", 60],
];

const relative = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
const absolute = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });

export function timeAgo(iso: string, now: number = Date.now()): string {
  const seconds = (new Date(iso).getTime() - now) / 1000;
  for (const [unit, size] of UNITS) {
    if (Math.abs(seconds) >= size) {
      return relative.format(Math.round(seconds / size), unit);
    }
  }
  return "just now";
}

export function fullDate(iso: string): string {
  return absolute.format(new Date(iso));
}

export function companyName(boardId: string): string {
  return boardId
    .split(/[-_]/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function formatSalary(salary: NonNullable<Job["salary"]>): string {
  const money = (n: number) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: salary.currency ?? "USD",
      notation: "compact",
      maximumFractionDigits: 0,
    }).format(n);
  const { min, max } = salary;
  if (min !== null && max !== null && min !== max) return `${money(min)}–${money(max)}`;
  return money((max ?? min) as number);
}

/** An approximate AI cost: cents need more precision than whole dollars do. */
export function formatCost(usd: number): string {
  if (usd === 0) return "$0";
  if (usd < 0.01) return "<$0.01";
  return `$${usd.toFixed(usd < 10 ? 2 : 0)}`;
}
