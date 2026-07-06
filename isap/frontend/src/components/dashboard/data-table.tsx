"use client"

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { upcomingEvents } from "@/lib/analytics-data"

function getStatusVariant(status: string) {
  switch (status) {
    case "В работе":
      return "default" as const
    case "Запланировано":
      return "secondary" as const
    case "Требует внимания":
      return "destructive" as const
    default:
      return "outline" as const
  }
}

function getTypeVariant(type: string) {
  switch (type) {
    case "Экспертиза":
      return "default" as const
    case "Проверка":
      return "secondary" as const
    case "Документ":
      return "outline" as const
    case "Аттестация":
      return "secondary" as const
    case "Учёт":
      return "outline" as const
    case "Отчёт":
      return "destructive" as const
    case "План":
      return "secondary" as const
    default:
      return "outline" as const
  }
}

export function UpcomingEventsTable() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Ближайшие мероприятия</CardTitle>
        <CardDescription>Запланированные мероприятия и контрольные сроки</CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[380px]">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[90px]">ID</TableHead>
                <TableHead>Организация</TableHead>
                <TableHead className="hidden md:table-cell">Мероприятие</TableHead>
                <TableHead>Тип</TableHead>
                <TableHead>Срок</TableHead>
                <TableHead className="hidden sm:table-cell">Статус</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {upcomingEvents.map((evt) => (
                <TableRow key={evt.id}>
                  <TableCell className="font-mono text-xs">{evt.id}</TableCell>
                  <TableCell className="font-medium">{evt.organization}</TableCell>
                  <TableCell className="hidden max-w-[260px] truncate md:table-cell text-muted-foreground text-sm">
                    {evt.event}
                  </TableCell>
                  <TableCell>
                    <Badge variant={getTypeVariant(evt.type)} className="text-xs">
                      {evt.type}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-mono text-sm">{evt.deadline}</TableCell>
                  <TableCell className="hidden sm:table-cell">
                    <Badge variant={getStatusVariant(evt.status)}>
                      {evt.status}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}