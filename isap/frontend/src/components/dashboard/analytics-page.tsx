"use client"

import { useState } from "react"
import { BarChart3, Download, Filter } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Cell,
  Pie,
  PieChart,
  Line,
  LineChart,
} from "recharts"

/* ─── Данные для аналитики ─── */

const monthlyExpertise = [
  { month: "Янв", экспертиза: 12, обследование: 8, диагностика: 5 },
  { month: "Фев", экспертиза: 15, обследование: 10, диагностика: 7 },
  { month: "Мар", экспертиза: 13, обследование: 11, диагностика: 4 },
  { month: "Апр", экспертиза: 18, обследование: 12, диагностика: 9 },
  { month: "Май", экспертиза: 16, обследование: 9, диагностика: 6 },
  { month: "Июн", экспертиза: 20, обследование: 14, диагностика: 8 },
  { month: "Июл", экспертиза: 19, обследование: 13, диагностика: 10 },
  { month: "Авг", экспертиза: 22, обследование: 15, диагностика: 7 },
  { month: "Сен", экспертиза: 21, обследование: 11, диагностика: 9 },
  { month: "Окт", экспертиза: 24, обследование: 16, диагностика: 11 },
  { month: "Ноя", экспертиза: 22, обследование: 14, диагностика: 8 },
  { month: "Дек", экспертиза: 20, обследование: 12, диагностика: 10 },
]

const expertiseByOrg = [
  { org: "Нефтегазпром", количество: 28, fill: "var(--color-org1)" },
  { org: "Хим. завод", количество: 22, fill: "var(--color-org2)" },
  { org: "Газпереработка", количество: 18, fill: "var(--color-org3)" },
  { org: "Транснефть", количество: 15, fill: "var(--color-org4)" },
  { org: "Промтехмонтаж", количество: 12, fill: "var(--color-org5)" },
  { org: "Прочие", количество: 25, fill: "var(--color-org6)" },
]

const contractAmounts = [
  { month: "Янв", сумма: 4200000 },
  { month: "Фев", сумма: 3800000 },
  { month: "Мар", сумма: 5100000 },
  { month: "Апр", сумма: 4600000 },
  { month: "Май", сумма: 6200000 },
  { month: "Июн", сумма: 5800000 },
  { month: "Июл", сумма: 5500000 },
  { month: "Авг", сумма: 7100000 },
  { month: "Сен", сумма: 6400000 },
  { month: "Окт", сумма: 7800000 },
  { month: "Ноя", сумма: 7200000 },
  { month: "Дек", сумма: 6900000 },
]

const tasksByStatus = [
  { статус: "Завершена", количество: 142, fill: "var(--color-done)" },
  { статус: "В работе", количество: 23, fill: "var(--color-work)" },
  { статус: "Новая", количество: 15, fill: "var(--color-new)" },
  { статус: "На проверке", количество: 8, fill: "var(--color-review)" },
  { статус: "Просрочена", количество: 4, fill: "var(--color-overdue)" },
]

const quarterlyDynamics = [
  { period: "I кв. 2025", экспертизы: 45, договоры: 18, объекты: 28 },
  { period: "II кв. 2025", экспертизы: 52, договоры: 22, объекты: 31 },
  { period: "III кв. 2025", экспертизы: 48, договоры: 19, объекты: 35 },
  { period: "IV кв. 2025", экспертизы: 58, договоры: 25, объекты: 42 },
  { period: "I кв. 2026", экспертизы: 65, договоры: 28, объекты: 48 },
  { period: "II кв. 2026", экспертизы: 72, договоры: 32, объекты: 52 },
]

const COLORS_6 = [
  "oklch(0.55 0.2 260)",
  "oklch(0.65 0.18 145)",
  "oklch(0.6 0.2 55)",
  "oklch(0.55 0.22 25)",
  "oklch(0.55 0.2 330)",
  "oklch(0.6 0.15 200)",
]

const COLORS_5 = [
  "oklch(0.55 0.2 145)",
  "oklch(0.55 0.2 260)",
  "oklch(0.65 0.2 80)",
  "oklch(0.6 0.2 55)",
  "oklch(0.55 0.22 25)",
]

/* ─── Конфиги графиков ─── */

const monthlyExpConfig: ChartConfig = {
  экспертиза: { label: "Экспертиза", color: "oklch(0.55 0.2 260)" },
  обследование: { label: "Обследование", color: "oklch(0.65 0.18 145)" },
  диагностика: { label: "Диагностика", color: "oklch(0.6 0.2 55)" },
}

const orgConfig: ChartConfig = {
  org1: { label: "Нефтегазпром", color: "oklch(0.55 0.2 260)" },
  org2: { label: "Хим. завод", color: "oklch(0.65 0.18 145)" },
  org3: { label: "Газпереработка", color: "oklch(0.6 0.2 55)" },
  org4: { label: "Транснефть", color: "oklch(0.55 0.22 25)" },
  org5: { label: "Промтехмонтаж", color: "oklch(0.55 0.2 330)" },
  org6: { label: "Прочие", color: "oklch(0.6 0.15 200)" },
}

const contractConfig: ChartConfig = {
  сумма: { label: "Сумма", color: "oklch(0.55 0.2 145)" },
}

const taskStatusConfig: ChartConfig = {
  done: { label: "Завершена", color: "oklch(0.55 0.2 145)" },
  work: { label: "В работе", color: "oklch(0.55 0.2 260)" },
  new: { label: "Новая", color: "oklch(0.65 0.2 80)" },
  review: { label: "На проверке", color: "oklch(0.6 0.2 55)" },
  overdue: { label: "Просрочена", color: "oklch(0.55 0.22 25)" },
}

const quarterlyConfig: ChartConfig = {
  экспертизы: { label: "Экспертизы", color: "oklch(0.55 0.2 260)" },
  договоры: { label: "Договоры", color: "oklch(0.65 0.18 145)" },
  объекты: { label: "Объекты ОПО", color: "oklch(0.6 0.2 55)" },
}

/* ─── Страница ─── */

export function AnalyticsPage() {
  const [period, setPeriod] = useState("2026")

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Аналитика</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Детальные отчёты и статистика по промышленной безопасности
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={period} onValueChange={setPeriod}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Период" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="2026">2026 год</SelectItem>
              <SelectItem value="2025">2025 год</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" className="gap-2">
            <Download className="h-4 w-4" />
            Выгрузить
          </Button>
        </div>
      </div>

      {/* Количество экспертиз по видам */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Экспертизы и обследования по месяцам</CardTitle>
            <CardDescription>Детализация по видам работ</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={monthlyExpConfig} className="h-[320px] w-full">
              <BarChart data={monthlyExpertise} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
                <CartesianGrid vertical={false} strokeDasharray="3 3" />
                <XAxis dataKey="month" tickLine={false} axisLine={false} tickMargin={8} />
                <YAxis tickLine={false} axisLine={false} tickMargin={8} />
                <ChartTooltip content={<ChartTooltipContent formatter={(v) => `${v} шт.`} />} />
                <Bar dataKey="экспертиза" stackId="a" fill="oklch(0.55 0.2 260)" radius={[0, 0, 0, 0]} />
                <Bar dataKey="обследование" stackId="a" fill="oklch(0.65 0.18 145)" radius={[0, 0, 0, 0]} />
                <Bar dataKey="диагностика" stackId="a" fill="oklch(0.6 0.2 55)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Экспертизы по организациям</CardTitle>
            <CardDescription>Распределение за год</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={orgConfig} className="mx-auto h-[260px] w-full">
              <PieChart>
                <ChartTooltip
                  content={<ChartTooltipContent nameKey="org" formatter={(v) => `${v} шт.`} />}
                />
                <Pie
                  data={expertiseByOrg}
                  dataKey="количество"
                  nameKey="org"
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  innerRadius={45}
                  strokeWidth={2}
                  stroke="var(--color-background)"
                >
                  {expertiseByOrg.map((_entry, index) => (
                    <Cell key={index} fill={COLORS_6[index % COLORS_6.length]} />
                  ))}
                </Pie>
              </PieChart>
            </ChartContainer>
            <div className="mt-2 grid grid-cols-2 gap-1.5 px-2 text-xs">
              {expertiseByOrg.map((item, index) => (
                <div key={item.org} className="flex items-center gap-1.5">
                  <div
                    className="h-2 w-2 shrink-0 rounded-[2px]"
                    style={{ backgroundColor: COLORS_6[index % COLORS_6.length] }}
                  />
                  <span className="text-muted-foreground truncate">{item.org}</span>
                  <span className="ml-auto font-medium tabular-nums">{item.количество}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Динамика договоров и задач */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Сумма договоров по месяцам</CardTitle>
            <CardDescription>Объём финансирования (руб.)</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={contractConfig} className="h-[300px] w-full">
              <AreaChart data={contractAmounts} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
                <defs>
                  <linearGradient id="fillСумма" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="oklch(0.55 0.2 145)" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="oklch(0.55 0.2 145)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} strokeDasharray="3 3" />
                <XAxis dataKey="month" tickLine={false} axisLine={false} tickMargin={8} />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  tickMargin={8}
                  tickFormatter={(v) => `${(v / 1000000).toFixed(1)}М`}
                />
                <ChartTooltip content={<ChartTooltipContent formatter={(v) => `${Number(v).toLocaleString("ru-RU")} ₽`} />} />
                <Area dataKey="сумма" type="monotone" fill="url(#fillСумма)" stroke="oklch(0.55 0.2 145)" strokeWidth={2} />
              </AreaChart>
            </ChartContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Задачи по статусам</CardTitle>
            <CardDescription>Текущее распределение</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={taskStatusConfig} className="mx-auto h-[260px] w-full">
              <PieChart>
                <ChartTooltip
                  content={<ChartTooltipContent nameKey="статус" formatter={(v) => `${v} шт.`} />}
                />
                <Pie
                  data={tasksByStatus}
                  dataKey="количество"
                  nameKey="статус"
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  innerRadius={45}
                  strokeWidth={2}
                  stroke="var(--color-background)"
                >
                  {tasksByStatus.map((_entry, index) => (
                    <Cell key={index} fill={COLORS_5[index % COLORS_5.length]} />
                  ))}
                </Pie>
              </PieChart>
            </ChartContainer>
            <div className="mt-2 grid grid-cols-2 gap-1.5 px-2 text-xs">
              {tasksByStatus.map((item, index) => (
                <div key={item.статус} className="flex items-center gap-1.5">
                  <div
                    className="h-2 w-2 shrink-0 rounded-[2px]"
                    style={{ backgroundColor: COLORS_5[index % COLORS_5.length] }}
                  />
                  <span className="text-muted-foreground truncate">{item.статус}</span>
                  <span className="ml-auto font-medium tabular-nums">{item.количество}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Квартальная динамика */}
      <Card>
        <CardHeader>
          <CardTitle>Квартальная динамика</CardTitle>
          <CardDescription>Рост ключевых показателей по кварталам</CardDescription>
        </CardHeader>
        <CardContent>
          <ChartContainer config={quarterlyConfig} className="h-[300px] w-full">
            <LineChart data={quarterlyDynamics} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
              <CartesianGrid vertical={false} strokeDasharray="3 3" />
              <XAxis dataKey="period" tickLine={false} axisLine={false} tickMargin={8} />
              <YAxis tickLine={false} axisLine={false} tickMargin={8} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Line dataKey="экспертизы" type="monotone" stroke="oklch(0.55 0.2 260)" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
              <Line dataKey="договоры" type="monotone" stroke="oklch(0.65 0.18 145)" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
              <Line dataKey="объекты" type="monotone" stroke="oklch(0.6 0.2 55)" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
            </LineChart>
          </ChartContainer>
        </CardContent>
      </Card>
    </div>
  )
}