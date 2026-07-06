"use client"

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
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
import { expertiseData, opoByClass, contractStatuses, tasksByWeek } from "@/lib/analytics-data"

const expertiseConfig: ChartConfig = {
  экспертизы: { label: "Экспертизы", color: "oklch(0.55 0.2 260)" },
  обследования: { label: "Обследования", color: "oklch(0.65 0.18 145)" },
}

const opoClassConfig: ChartConfig = {
  class1: { label: "Класс I", color: "oklch(0.55 0.22 25)" },
  class2: { label: "Класс II", color: "oklch(0.6 0.2 55)" },
  class3: { label: "Класс III", color: "oklch(0.55 0.2 145)" },
  class4: { label: "Класс IV", color: "oklch(0.55 0.2 260)" },
}

const contractConfig: ChartConfig = {
  active: { label: "Активные", color: "oklch(0.55 0.2 145)" },
  pending: { label: "На согласовании", color: "oklch(0.65 0.2 80)" },
  completed: { label: "Завершённые", color: "oklch(0.55 0.2 260)" },
  terminated: { label: "Расторгнутые", color: "oklch(0.6 0.15 0)" },
}

const tasksConfig: ChartConfig = {
  создано: { label: "Создано", color: "oklch(0.55 0.2 260)" },
  выполнено: { label: "Выполнено", color: "oklch(0.55 0.2 145)" },
}

const CLASS_COLORS = [
  "oklch(0.55 0.22 25)",
  "oklch(0.6 0.2 55)",
  "oklch(0.55 0.2 145)",
  "oklch(0.55 0.2 260)",
]

const CONTRACT_COLORS = [
  "oklch(0.55 0.2 145)",
  "oklch(0.65 0.2 80)",
  "oklch(0.55 0.2 260)",
  "oklch(0.6 0.15 0)",
]

export function ExpertiseChart() {
  return (
    <Card className="col-span-1 lg:col-span-2">
      <CardHeader>
        <CardTitle>Динамика экспертиз и обследований</CardTitle>
        <CardDescription>Количество проведённых экспертиз и обследований за 2026 год</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={expertiseConfig} className="h-[300px] w-full">
          <AreaChart data={expertiseData} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
            <defs>
              <linearGradient id="fillЭкспертизы" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="oklch(0.55 0.2 260)" stopOpacity={0.3} />
                <stop offset="95%" stopColor="oklch(0.55 0.2 260)" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="fillОбследования" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="oklch(0.65 0.18 145)" stopOpacity={0.3} />
                <stop offset="95%" stopColor="oklch(0.65 0.18 145)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} strokeDasharray="3 3" />
            <XAxis dataKey="month" tickLine={false} axisLine={false} tickMargin={8} />
            <YAxis tickLine={false} axisLine={false} tickMargin={8} />
            <ChartTooltip
              content={
                <ChartTooltipContent
                  labelFormatter={(value) => value}
                  formatter={(value) => `${Number(value).toLocaleString("ru-RU")} шт.`}
                />
              }
            />
            <Area
              dataKey="экспертизы"
              type="monotone"
              fill="url(#fillЭкспертизы)"
              stroke="oklch(0.55 0.2 260)"
              strokeWidth={2}
            />
            <Area
              dataKey="обследования"
              type="monotone"
              fill="url(#fillОбследования)"
              stroke="oklch(0.65 0.18 145)"
              strokeWidth={2}
            />
          </AreaChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}

export function OpoByClassChart() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Объекты ОПО по классу опасности</CardTitle>
        <CardDescription>Распределение зарегистрированных объектов</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={opoClassConfig} className="h-[300px] w-full">
          <BarChart data={opoByClass} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
            <CartesianGrid vertical={false} strokeDasharray="3 3" />
            <XAxis dataKey="класс" tickLine={false} axisLine={false} tickMargin={8} />
            <YAxis tickLine={false} axisLine={false} tickMargin={8} />
            <ChartTooltip
              content={
                <ChartTooltipContent
                  formatter={(value) => `${Number(value).toLocaleString("ru-RU")} шт.`}
                />
              }
            />
            <Bar dataKey="объекты" radius={[6, 6, 0, 0]}>
              {opoByClass.map((_entry, index) => (
                <Cell key={index} fill={CLASS_COLORS[index % CLASS_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}

export function ContractStatusChart() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Статус договоров</CardTitle>
        <CardDescription>Текущее состояние договорной базы</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={contractConfig} className="mx-auto h-[300px] w-full">
          <PieChart>
            <ChartTooltip
              content={
                <ChartTooltipContent
                  nameKey="статус"
                  formatter={(value) => `${Number(value).toLocaleString("ru-RU")} шт.`}
                />
              }
            />
            <Pie
              data={contractStatuses}
              dataKey="количество"
              nameKey="статус"
              cx="50%"
              cy="50%"
              outerRadius={100}
              innerRadius={55}
              strokeWidth={2}
              stroke="var(--color-background)"
            >
              {contractStatuses.map((_entry, index) => (
                <Cell key={index} fill={CONTRACT_COLORS[index % CONTRACT_COLORS.length]} />
              ))}
            </Pie>
          </PieChart>
        </ChartContainer>
        <div className="mt-2 grid grid-cols-2 gap-2 px-2 text-xs">
          {contractStatuses.map((item, index) => (
            <div key={item.статус} className="flex items-center gap-2">
              <div
                className="h-2.5 w-2.5 shrink-0 rounded-[2px]"
                style={{ backgroundColor: CONTRACT_COLORS[index % CONTRACT_COLORS.length] }}
              />
              <span className="text-muted-foreground truncate">{item.статус}</span>
              <span className="ml-auto font-medium tabular-nums">
                {item.количество.toLocaleString("ru-RU")}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

export function TasksByWeekChart() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Задачи по неделям</CardTitle>
        <CardDescription>Создание и выполнение задач за последние 8 недель</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={tasksConfig} className="h-[300px] w-full">
          <LineChart data={tasksByWeek} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
            <CartesianGrid vertical={false} strokeDasharray="3 3" />
            <XAxis dataKey="неделя" tickLine={false} axisLine={false} tickMargin={8} />
            <YAxis tickLine={false} axisLine={false} tickMargin={8} />
            <ChartTooltip content={<ChartTooltipContent />} />
            <Line
              dataKey="создано"
              type="monotone"
              stroke="oklch(0.55 0.2 260)"
              strokeWidth={2}
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
            <Line
              dataKey="выполнено"
              type="monotone"
              stroke="oklch(0.55 0.2 145)"
              strokeWidth={2}
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}