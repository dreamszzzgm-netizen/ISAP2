"use client"

import { useState } from "react"
import { Plus, Search, CalendarDays, User, Flag, CircleDot, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Textarea } from "@/components/ui/textarea"
import { toast } from "sonner"
import { SmartImport } from "@/components/dashboard/smart-import"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

/* ─── Типы ─── */

type TaskPriority = "высокий" | "средний" | "низкий"
type TaskStatus = "новая" | "в работе" | "на проверке" | "завершена" | "просрочена"

interface TaskItem {
  id: string
  title: string
  description: string
  assignee: string
  organization: string
  priority: TaskPriority
  status: TaskStatus
  deadline: string
  createdAt: string
}

interface TaskFormData {
  title: string
  description: string
  assignee: string
  organization: string
  priority: TaskPriority
  status: TaskStatus
  deadline: string
}

/* ─── Моковые данные ─── */

const mockTasks: TaskItem[] = [
  {
    id: "ЗДЧ-001",
    title: "Провести экспертизу РВС-5000",
    description: "Провести экспертизу промышленной безопасности резервуарного парка РВС-5000 в ООО «Нефтегазпром». Подготовить заключение.",
    assignee: "Иванов А.П.",
    organization: "ООО «Нефтегазпром»",
    priority: "высокий",
    status: "в работе",
    deadline: "2026-07-12",
    createdAt: "2026-06-28",
  },
  {
    id: "ЗДЧ-002",
    title: "Подготовить план мероприятий по ликвидации аварий",
    description: "Разработать план мероприятий по локализации и ликвидации аварий для ОПО класса I.",
    assignee: "Петрова М.С.",
    organization: "АО «Химический завод»",
    priority: "высокий",
    status: "на проверке",
    deadline: "2026-07-10",
    createdAt: "2026-06-25",
  },
  {
    id: "ЗДЧ-003",
    title: "Проверка производственного контроля",
    description: "Плановая проверка состояния производственного контроля на объектах склада аммиака.",
    assignee: "Сидоров К.А.",
    organization: "ИП Сидоров К.А.",
    priority: "средний",
    status: "новая",
    deadline: "2026-07-20",
    createdAt: "2026-07-01",
  },
  {
    id: "ЗДЧ-004",
    title: "Продление страховки ОПО",
    description: "Своевременное продление договора обязательного страхования ответственности владельца ОПО.",
    assignee: "Козлова Е.В.",
    organization: "ИП Сидоров К.А.",
    priority: "высокий",
    status: "просрочена",
    deadline: "2026-07-01",
    createdAt: "2026-06-20",
  },
  {
    id: "ЗДЧ-005",
    title: "Аттестация специалистов по ПБ",
    description: "Организация аттестации специалистов организации по промышленной безопасности.",
    assignee: "Иванов А.П.",
    organization: "ООО «Промтехмонтаж»",
    priority: "средний",
    status: "в работе",
    deadline: "2026-07-22",
    createdAt: "2026-07-02",
  },
  {
    id: "ЗДЧ-006",
    title: "Постановка на учёт оборудования под давлением",
    description: "Регистрация в Ростехнадзоре оборудования работающего под давлением: 3 сосуда, 2 компрессора.",
    assignee: "Морозов С.Н.",
    organization: "ПАО «Газпереработка»",
    priority: "средний",
    status: "новая",
    deadline: "2026-07-25",
    createdAt: "2026-07-03",
  },
  {
    id: "ЗДЧ-007",
    title: "Сдача отчёта о ПК за II квартал",
    description: "Подготовить и сдать отчёт о деятельности производственного контроля за второй квартал 2026 года.",
    assignee: "Петрова М.С.",
    organization: "ООО «Транснефть-Сервис»",
    priority: "высокий",
    status: "в работе",
    deadline: "2026-07-28",
    createdAt: "2026-07-04",
  },
  {
    id: "ЗДЧ-008",
    title: "Обновление положения о ПК",
    description: "Актуализировать положение о производственном контроле с учётом изменений в законодательстве.",
    assignee: "Козлова Е.В.",
    organization: "ЗАО «Химтрейд»",
    priority: "низкий",
    status: "завершена",
    deadline: "2026-07-05",
    createdAt: "2026-06-15",
  },
]

/* ─── Вспомогательные ─── */

const priorityConfig: Record<TaskPriority, { label: string; variant: "destructive" | "default" | "secondary" | "outline" }> = {
  высокий: { label: "Высокий", variant: "destructive" },
  средний: { label: "Средний", variant: "default" },
  низкий: { label: "Низкий", variant: "secondary" },
}

const statusConfig: Record<TaskStatus, { label: string; variant: "destructive" | "default" | "secondary" | "outline" }> = {
  новая: { label: "Новая", variant: "outline" },
  "в работе": { label: "В работе", variant: "default" },
  "на проверке": { label: "На проверке", variant: "secondary" },
  завершена: { label: "Завершена", variant: "secondary" },
  просрочена: { label: "Просрочена", variant: "destructive" },
}

function formatDate(dateStr: string) {
  if (!dateStr) return "—"
  const d = new Date(dateStr)
  return d.toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" })
}

/* ─── Форма задачи ─── */

function TaskForm({ data, onChange }: { data: TaskFormData; onChange: (d: TaskFormData) => void }) {
  const update = <K extends keyof TaskFormData>(key: K, value: TaskFormData[K]) =>
    onChange({ ...data, [key]: value })

  return (
    <div className="space-y-4">
      <div>
        <Label>Название задачи</Label>
        <Input
          placeholder="Например: Провести экспертизу промышленной безопасности"
          value={data.title}
          onChange={(e) => update("title", e.target.value)}
        />
      </div>
      <div>
        <Label>Описание</Label>
        <Textarea
          placeholder="Подробное описание задачи..."
          rows={3}
          value={data.description}
          onChange={(e) => update("description", e.target.value)}
        />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <Label>Исполнитель</Label>
          <Input
            placeholder="ФИО исполнителя"
            value={data.assignee}
            onChange={(e) => update("assignee", e.target.value)}
          />
        </div>
        <div>
          <Label>Организация</Label>
          <Input
            placeholder="Наименование организации"
            value={data.organization}
            onChange={(e) => update("organization", e.target.value)}
          />
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <Label>Приоритет</Label>
          <Select value={data.priority} onValueChange={(v) => update("priority", v as TaskPriority)}>
            <SelectTrigger>
              <SelectValue placeholder="Выберите" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="высокий">Высокий</SelectItem>
              <SelectItem value="средний">Средний</SelectItem>
              <SelectItem value="низкий">Низкий</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label>Статус</Label>
          <Select value={data.status} onValueChange={(v) => update("status", v as TaskStatus)}>
            <SelectTrigger>
              <SelectValue placeholder="Выберите" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="новая">Новая</SelectItem>
              <SelectItem value="в работе">В работе</SelectItem>
              <SelectItem value="на проверке">На проверке</SelectItem>
              <SelectItem value="завершена">Завершена</SelectItem>
              <SelectItem value="просрочена">Просрочена</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label>Срок выполнения</Label>
          <Input
            type="date"
            value={data.deadline}
            onChange={(e) => update("deadline", e.target.value)}
          />
        </div>
      </div>
    </div>
  )
}

/* ─── Основная страница ─── */

export function TasksPage() {
  const [tasks, setTasks] = useState<TaskItem[]>(mockTasks)
  const [search, setSearch] = useState("")
  const [filterStatus, setFilterStatus] = useState<string>("all")
  const [filterPriority, setFilterPriority] = useState<string>("all")
  const [open, setOpen] = useState(false)
  const [editingTask, setEditingTask] = useState<TaskItem | undefined>(undefined)

  const openCard = (task: TaskItem) => {
    setEditingTask(task)
    setOpen(true)
  }

  const filtered = tasks.filter((t) => {
    const matchSearch =
      t.title.toLowerCase().includes(search.toLowerCase()) ||
      t.assignee.toLowerCase().includes(search.toLowerCase()) ||
      t.organization.toLowerCase().includes(search.toLowerCase()) ||
      t.id.toLowerCase().includes(search.toLowerCase())
    const matchStatus = filterStatus === "all" || t.status === filterStatus
    const matchPriority = filterPriority === "all" || t.priority === filterPriority
    return matchSearch && matchStatus && matchPriority
  })

  const handleSave = (data: TaskFormData) => {
    if (editingTask) {
      setTasks((prev) =>
        prev.map((t) =>
          t.id === editingTask.id ? { ...t, ...data } : t
        )
      )
    } else {
      const newTask: TaskItem = {
        id: `ЗДЧ-${String(tasks.length + 1).padStart(3, "0")}`,
        ...data,
        createdAt: new Date().toISOString().split("T")[0],
      }
      setTasks((prev) => [...prev, newTask])
    }
    setOpen(false)
    setEditingTask(undefined)
  }

  const initialFormData: TaskFormData = {
    title: editingTask?.title || "",
    description: editingTask?.description || "",
    assignee: editingTask?.assignee || "",
    organization: editingTask?.organization || "",
    priority: editingTask?.priority || "средний",
    status: editingTask?.status || "новая",
    deadline: editingTask?.deadline || "",
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Задачи</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Управление задачами и контроль сроков
          </p>
        </div>
        <Dialog
          open={open}
          onOpenChange={(v) => {
            setOpen(v)
            if (!v) setEditingTask(undefined)
          }}
        >
          <DialogTrigger asChild>
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              Добавить задачу
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                {editingTask ? "Редактирование задачи" : "Новая задача"}
              </DialogTitle>
            </DialogHeader>
            <TaskFormWrapper
              key={editingTask?.id || "new"}
              initialData={initialFormData}
              onSave={handleSave}
              onCancel={() => {
                setOpen(false)
                setEditingTask(undefined)
              }}
            />
          </DialogContent>
        </Dialog>
      </div>

      {/* Поиск и фильтры */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
        <div className="relative flex-1 max-w-sm w-full">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Поиск по названию, исполнителю, организации..."
            className="pl-8"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select value={filterStatus} onValueChange={setFilterStatus}>
          <SelectTrigger className="w-[180px]">
            <CircleDot className="h-4 w-4 mr-2 text-muted-foreground" />
            <SelectValue placeholder="Статус" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Все статусы</SelectItem>
            <SelectItem value="новая">Новая</SelectItem>
            <SelectItem value="в работе">В работе</SelectItem>
            <SelectItem value="на проверке">На проверке</SelectItem>
            <SelectItem value="завершена">Завершена</SelectItem>
            <SelectItem value="просрочена">Просрочена</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filterPriority} onValueChange={setFilterPriority}>
          <SelectTrigger className="w-[180px]">
            <Flag className="h-4 w-4 mr-2 text-muted-foreground" />
            <SelectValue placeholder="Приоритет" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Все приоритеты</SelectItem>
            <SelectItem value="высокий">Высокий</SelectItem>
            <SelectItem value="средний">Средний</SelectItem>
            <SelectItem value="низкий">Низкий</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Таблица */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[90px]">ID</TableHead>
                <TableHead>Название</TableHead>
                <TableHead className="hidden md:table-cell">Исполнитель</TableHead>
                <TableHead className="hidden lg:table-cell">Организация</TableHead>
                <TableHead className="w-[110px]">Приоритет</TableHead>
                <TableHead className="w-[130px]">Статус</TableHead>
                <TableHead className="hidden sm:table-cell w-[110px]">Срок</TableHead>
                <TableHead className="w-[100px]">Действия</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((task) => (
                <TableRow
                  key={task.id}
                  onDoubleClick={() => openCard(task)}
                  className="cursor-pointer"
                >
                  <TableCell className="font-mono text-xs">{task.id}</TableCell>
                  <TableCell className="font-medium max-w-[220px] truncate">{task.title}</TableCell>
                  <TableCell className="hidden md:table-cell text-muted-foreground text-sm">
                    {task.assignee}
                  </TableCell>
                  <TableCell className="hidden lg:table-cell text-muted-foreground text-sm">
                    {task.organization}
                  </TableCell>
                  <TableCell>
                    <Badge variant={priorityConfig[task.priority].variant}>
                      {priorityConfig[task.priority].label}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={statusConfig[task.status].variant}>
                      {statusConfig[task.status].label}
                    </Badge>
                  </TableCell>
                  <TableCell className="hidden sm:table-cell text-muted-foreground text-sm">
                    {formatDate(task.deadline)}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); openCard(task) }}>Открыть</Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground hover:text-destructive"
                        onClick={(e) => {
                          e.stopPropagation()
                          setTasks((prev) => prev.filter((t) => t.id !== task.id))
                          toast.success("Задача удалена", { description: task.title })
                        }}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                    Задачи не найдены
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}

/* ─── Обёртка формы (для key-перезагрузки) ─── */

function TaskFormWrapper({
  initialData,
  onSave,
  onCancel,
}: {
  initialData: TaskFormData
  onSave: (data: TaskFormData) => void
  onCancel: () => void
}) {
  const [data, setData] = useState<TaskFormData>(initialData)

  return (
    <div className="space-y-4">
      {/* Информация о задаче */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
          <CircleDot className="h-4 w-4" />
          Информация о задаче
        </h3>
        <TaskForm data={data} onChange={setData} />
      </div>

      <Separator />

      {/* Умный импорт */}
      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Импорт данных</h3>
        <SmartImport hint="Импорт задачи из файла (план работ, протокол, распоряжение)" />
      </div>

      <Separator />

      {/* Детали */}
      {data.description && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Описание</h3>
          <p className="text-sm text-muted-foreground leading-relaxed bg-muted/50 rounded-md p-3">
            {data.description}
          </p>
        </div>
      )}

      <Separator />

      <div className="flex justify-end gap-3">
        <Button variant="outline" onClick={onCancel}>
          Отмена
        </Button>
        <Button onClick={() => onSave(data)}>Сохранить</Button>
      </div>
    </div>
  )
}