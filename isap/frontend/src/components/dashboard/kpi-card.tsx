"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { TrendingUp, TrendingDown, ShieldAlert, FileText, ClipboardCheck, ListChecks } from "lucide-react"
import type { LucideIcon } from "lucide-react"

const iconMap: Record<string, LucideIcon> = {
  "Объекты ОПО": ShieldAlert,
  "Договора": FileText,
  "Экспертизы": ClipboardCheck,
  "Задачи": ListChecks,
}

interface KpiCardProps {
  title: string
  value: string
  change: string
  trend: "up" | "down"
  description: string
}

export function KpiCard({ title, value, change, trend, description }: KpiCardProps) {
  const Icon = iconMap[title] || ShieldAlert
  const isUp = trend === "up"

  return (
    <Card className="relative overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <div className="bg-muted flex h-9 w-9 items-center justify-center rounded-lg">
          <Icon className="h-4 w-4 text-muted-foreground" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <div className="mt-1 flex items-center gap-1 text-xs">
          <span
            className={cn(
              "flex items-center font-medium",
              isUp ? "text-emerald-600" : "text-red-500"
            )}
          >
            {isUp ? (
              <TrendingUp className="mr-0.5 h-3 w-3" />
            ) : (
              <TrendingDown className="mr-0.5 h-3 w-3" />
            )}
            {change}
          </span>
          <span className="text-muted-foreground">{description}</span>
        </div>
      </CardContent>
    </Card>
  )
}