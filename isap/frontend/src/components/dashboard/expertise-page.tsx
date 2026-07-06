"use client"

import { useState } from "react"
import { Plus, Search, FileCheck2, ShieldCheck, AlertTriangle, CheckCircle2, Trash2 } from "lucide-react"
import { toast } from "sonner"
import { SmartImport } from "@/components/dashboard/smart-import"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Textarea } from "@/components/ui/textarea"
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

type ExpertiseStatus = "назначена" | "в работе" | "на проверке" | "завершена" | "отклонена"
type ExpertiseKind = "экспертиза ПБ" | "обследование" | "диагностика" | "оценка риска" | "аудит ПБ"

interface Expertise {
  id: string
  number: string
  organization: string
  objectName: string
  kind: ExpertiseKind
  expert: string
  dateStart: string
  dateEnd: string
  status: ExpertiseStatus
  conclusion: string
  notes: string
}

interface ExpertiseFormData {
  number: string
  organization: string
  objectName: string
  kind: ExpertiseKind
  expert: string
  dateStart: string
  dateEnd: string
  status: ExpertiseStatus
  conclusion: string
  notes: string
}

/* ─── Моковые данные ─── */

const mockExpertise: Expertise[] = [
  {
    id: "ЭКС-001",
    number: "Э-2026/012",
    organization: "ООО «Нефтегазпром»",
    objectName: "Резервуарный парк РВС-5000",
    kind: "экспертиза ПБ",
    expert: "Иванов А.П.",
    dateStart: "2026-06-15",
    dateEnd: "2026-07-15",
    status: "в работе",
    conclusion: "",
    notes: "Экспертиза проводится в рамках договора Д-2026/045. Включает обследование технического состояния 4 резервуаров.",
  },
  {
    id: "ЭКС-002",
    number: "Э-2026/008",
    organization: "АО «Химический завод»",
    objectName: "ГАЗ-005",
    kind: "экспертиза ПБ",
    expert: "Петрова М.С.",
    dateStart: "2026-05-01",
    dateEnd: "2026-06-20",
    status: "завершена",
    conclusion: "Положительное",
    notes: "Оборудование соответствует требованиям промышленной безопасности. Рекомендации по замене уплотнений.",
  },
  {
    id: "ЭКС-003",
    number: "Э-2026/015",
    organization: "ИП Сидоров К.А.",
    objectName: "Склад аммиака",
    kind: "обследование",
    expert: "Сидоров К.А.",
    dateStart: "2026-07-01",
    dateEnd: "2026-07-30",
    status: "назначена",
    conclusion: "",
    notes: "Плановое обследование склада аммиака. Необходимо проверить систему вентиляции и сигнализации.",
  },
  {
    id: "ЭКС-004",
    number: "Э-2026/010",
    organization: "ПАО «Газпереработка»",
    objectName: "Компрессорная станция КС-3",
    kind: "диагностика",
    expert: "Морозов С.Н.",
    dateStart: "2026-04-10",
    dateEnd: "2026-05-25",
    status: "завершена",
    conclusion: "Условно-положительное",
    notes: "Выявлены дефекты на компрессоре №2. Необходимо проведение ремонта до 01.09.2026.",
  },
  {
    id: "ЭКС-005",
    number: "Э-2026/018",
    organization: "ООО «Промтехмонтаж»",
    objectName: "Узел налива нефтепродуктов",
    kind: "оценка риска",
    expert: "Иванов А.П.",
    dateStart: "2026-06-20",
    dateEnd: "2026-08-20",
    status: "в работе",
    conclusion: "",
    notes: "Полная оценка риска аварий на узле налива. Разработка мер по снижению риска.",
  },
  {
    id: "ЭКС-006",
    number: "Э-2026/005",
    organization: "ЗАО «Химтрейд»",
    objectName: "Хранилище хлора",
    kind: "аудит ПБ",
    expert: "Петрова М.С.",
    dateStart: "2026-03-15",
    dateEnd: "2026-04-10",
    status: "завершена",
    conclusion: "Положительное",
    notes: "Аудит системы производственного контроля. Все требования выполняются.",
  },
  {
    id: "ЭКС-007",
    number: "Э-2026/020",
    organization: "ООО «Транснефть-Сервис»",
    objectName: "ЛПДС «Южная»",
    kind: "обследование",
    expert: "Морозов С.Н.",
    dateStart: "2026-07-05",
    dateEnd: "2026-07-25",
    status: "на проверке",
    conclusion: "",
    notes: "Обследование линейной части магистрального трубопровода. Результаты направлены на проверку.",
  },
]

/* ─── Справочники ─── */

const kindConfig: Record<ExpertiseKind, { label: string; variant: "destructive" | "default" | "secondary" | "outline" }> = {
  "экспертиза ПБ": { label: "Экспертиза ПБ", variant: "default" },
  обследование: { label: "Обследование", variant: "secondary" },
  диагностика: { label: "Диагностика", variant: "outline" },
  "оценка риска": { label: "Оценка риска", variant: "outline" },
  "аудит ПБ": { label: "Аудит ПБ", variant: "secondary" },
}

const statusConfig: Record<ExpertiseStatus, { label: string; variant: "destructive" | "default" | "secondary" | "outline" }> = {
  назначена: { label: "Назначена", variant: "outline" },
  "в работе": { label: "В работе", variant: "default" },
  "на проверке": { label: "На проверке", variant: "secondary" },
  завершена: { label: "Завершена", variant: "secondary" },
  отклонена: { label: "Отклонена", variant: "destructive" },
}

const conclusionConfig: Record<string, { variant: "destructive" | "default" | "secondary" | "outline" }> = {
  "Положительное": { variant: "default" },
  "Условно-положительное": { variant: "secondary" },
  "Отрицательное": { variant: "destructive" },
}

function formatDate(dateStr: string) {
  if (!dateStr) return "—"
  const d = new Date(dateStr)
  return d.toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" })
}

/* ─── Форма экспертизы ─── */

function ExpertiseForm({ data, onChange }: { data: ExpertiseFormData; onChange: (d: ExpertiseFormData) => void }) {
  const update = <K extends keyof ExpertiseFormData>(key: K, value: ExpertiseFormData[K]) =>
    onChange({ ...data, [key]: value })

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <Label>Номер экспертизы</Label>
          <Input
            placeholder="Э-2026/001"
            value={data.number}
            onChange={(e) => update("number", e.target.value)}
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
      <div>
        <Label>Объект экспертизы</Label>
        <Input
          placeholder="Наименование объекта ОПО"
          value={data.objectName}
          onChange={(e) => update("objectName", e.target.value)}
        />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <Label>Вид экспертизы</Label>
          <Select value={data.kind} onValueChange={(v) => update("kind", v as ExpertiseKind)}>
            <SelectTrigger>
              <SelectValue placeholder="Выберите" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="экспертиза ПБ">Экспертиза ПБ</SelectItem>
              <SelectItem value="обследование">Обследование</SelectItem>
              <SelectItem value="диагностика">Диагностика</SelectItem>
              <SelectItem value="оценка риска">Оценка риска</SelectItem>
              <SelectItem value="аудит ПБ">Аудит ПБ</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label>Эксперт</Label>
          <Input
            placeholder="ФИО эксперта"
            value={data.expert}
            onChange={(e) => update("expert", e.target.value)}
          />
        </div>
        <div>
          <Label>Статус</Label>
          <Select value={data.status} onValueChange={(v) => update("status", v as ExpertiseStatus)}>
            <SelectTrigger>
              <SelectValue placeholder="Выберите" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="назначена">Назначена</SelectItem>
              <SelectItem value="в работе">В работе</SelectItem>
              <SelectItem value="на проверке">На проверке</SelectItem>
              <SelectItem value="завершена">Завершена</SelectItem>
              <SelectItem value="отклонена">Отклонена</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <Label>Дата начала</Label>
          <Input type="date" value={data.dateStart} onChange={(e) => update("dateStart", e.target.value)} />
        </div>
        <div>
          <Label>Дата окончания</Label>
          <Input type="date" value={data.dateEnd} onChange={(e) => update("dateEnd", e.target.value)} />
        </div>
        {data.status === "завершена" && (
          <div>
            <Label>Заключение</Label>
            <Select value={data.conclusion} onValueChange={(v) => update("conclusion", v)}>
              <SelectTrigger>
                <SelectValue placeholder="Выберите" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Положительное">Положительное</SelectItem>
                <SelectItem value="Условно-положительное">Условно-положительное</SelectItem>
                <SelectItem value="Отрицательное">Отрицательное</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}
      </div>
      <div>
        <Label>Примечания</Label>
        <Textarea
          placeholder="Дополнительная информация..."
          rows={3}
          value={data.notes}
          onChange={(e) => update("notes", e.target.value)}
        />
      </div>
    </div>
  )
}

/* ─── Основная страница ─── */

export function ExpertisePage() {
  const [expertises, setExpertises] = useState<Expertise[]>(mockExpertise)
  const [search, setSearch] = useState("")
  const [filterStatus, setFilterStatus] = useState<string>("all")
  const [filterKind, setFilterKind] = useState<string>("all")
  const [open, setOpen] = useState(false)
  const [editingItem, setEditingItem] = useState<Expertise | undefined>(undefined)

  const openCard = (item: Expertise) => {
    setEditingItem(item)
    setOpen(true)
  }

  const filtered = expertises.filter((e) => {
    const matchSearch =
      e.number.toLowerCase().includes(search.toLowerCase()) ||
      e.organization.toLowerCase().includes(search.toLowerCase()) ||
      e.objectName.toLowerCase().includes(search.toLowerCase()) ||
      e.expert.toLowerCase().includes(search.toLowerCase())
    const matchStatus = filterStatus === "all" || e.status === filterStatus
    const matchKind = filterKind === "all" || e.kind === filterKind
    return matchSearch && matchStatus && matchKind
  })

  const handleSave = (data: ExpertiseFormData) => {
    if (editingItem) {
      setExpertises((prev) =>
        prev.map((e) =>
          e.id === editingItem.id ? { ...e, ...data } : e
        )
      )
    } else {
      const newItem: Expertise = {
        id: `ЭКС-${String(expertises.length + 1).padStart(3, "0")}`,
        ...data,
      }
      setExpertises((prev) => [...prev, newItem])
    }
    setOpen(false)
    setEditingItem(undefined)
  }

  const initialFormData: ExpertiseFormData = {
    number: editingItem?.number || "",
    organization: editingItem?.organization || "",
    objectName: editingItem?.objectName || "",
    kind: editingItem?.kind || "экспертиза ПБ",
    expert: editingItem?.expert || "",
    dateStart: editingItem?.dateStart || "",
    dateEnd: editingItem?.dateEnd || "",
    status: editingItem?.status || "назначена",
    conclusion: editingItem?.conclusion || "",
    notes: editingItem?.notes || "",
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Экспертиза промбезопасности</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Учёт экспертиз, обследований и диагностических работ
          </p>
        </div>
        <Dialog
          open={open}
          onOpenChange={(v) => {
            setOpen(v)
            if (!v) setEditingItem(undefined)
          }}
        >
          <DialogTrigger asChild>
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              Добавить экспертизу
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                {editingItem ? "Редактирование экспертизы" : "Новая экспертиза"}
              </DialogTitle>
            </DialogHeader>
            <ExpertiseFormWrapper
              key={editingItem?.id || "new"}
              initialData={initialFormData}
              onSave={handleSave}
              onCancel={() => {
                setOpen(false)
                setEditingItem(undefined)
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
            placeholder="Поиск по номеру, организации, объекту, эксперту..."
            className="pl-8"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select value={filterStatus} onValueChange={setFilterStatus}>
          <SelectTrigger className="w-[170px]">
            <SelectValue placeholder="Статус" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Все статусы</SelectItem>
            <SelectItem value="назначена">Назначена</SelectItem>
            <SelectItem value="в работе">В работе</SelectItem>
            <SelectItem value="на проверке">На проверке</SelectItem>
            <SelectItem value="завершена">Завершена</SelectItem>
            <SelectItem value="отклонена">Отклонена</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filterKind} onValueChange={setFilterKind}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Вид" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Все виды</SelectItem>
            <SelectItem value="экспертиза ПБ">Экспертиза ПБ</SelectItem>
            <SelectItem value="обследование">Обследование</SelectItem>
            <SelectItem value="диагностика">Диагностика</SelectItem>
            <SelectItem value="оценка риска">Оценка риска</SelectItem>
            <SelectItem value="аудит ПБ">Аудит ПБ</SelectItem>
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
                <TableHead className="w-[110px]">Номер</TableHead>
                <TableHead>Организация</TableHead>
                <TableHead className="hidden md:table-cell">Объект</TableHead>
                <TableHead className="w-[130px]">Вид</TableHead>
                <TableHead className="hidden sm:table-cell">Эксперт</TableHead>
                <TableHead className="w-[130px]">Статус</TableHead>
                <TableHead className="hidden lg:table-cell">Заключение</TableHead>
                <TableHead className="w-[100px]">Действия</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((exp) => (
                <TableRow
                  key={exp.id}
                  onDoubleClick={() => openCard(exp)}
                  className="cursor-pointer"
                >
                  <TableCell className="font-mono text-xs">{exp.id}</TableCell>
                  <TableCell className="font-mono text-sm">{exp.number}</TableCell>
                  <TableCell className="font-medium">{exp.organization}</TableCell>
                  <TableCell className="hidden md:table-cell text-muted-foreground text-sm max-w-[180px] truncate">
                    {exp.objectName}
                  </TableCell>
                  <TableCell>
                    <Badge variant={kindConfig[exp.kind].variant}>
                      {kindConfig[exp.kind].label}
                    </Badge>
                  </TableCell>
                  <TableCell className="hidden sm:table-cell text-muted-foreground text-sm">
                    {exp.expert}
                  </TableCell>
                  <TableCell>
                    <Badge variant={statusConfig[exp.status].variant}>
                      {statusConfig[exp.status].label}
                    </Badge>
                  </TableCell>
                  <TableCell className="hidden lg:table-cell">
                    {exp.conclusion ? (
                      <Badge variant={conclusionConfig[exp.conclusion]?.variant || "outline"}>
                        {exp.conclusion}
                      </Badge>
                    ) : (
                      <span className="text-muted-foreground text-sm">—</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation()
                          openCard(exp)
                        }}
                      >
                        Открыть
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground hover:text-destructive"
                        onClick={(e) => {
                          e.stopPropagation()
                          setExpertises((prev) => prev.filter((e) => e.id !== exp.id))
                          toast.success("Экспертиза удалена", { description: exp.number + " — " + exp.objectName })
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
                  <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                    Экспертизы не найдены
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

/* ─── Обёртка формы ─── */

function ExpertiseFormWrapper({
  initialData,
  onSave,
  onCancel,
}: {
  initialData: ExpertiseFormData
  onSave: (data: ExpertiseFormData) => void
  onCancel: () => void
}) {
  const [data, setData] = useState<ExpertiseFormData>(initialData)

  return (
    <div className="space-y-4">
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
          <ShieldCheck className="h-4 w-4" />
          Данные экспертизы
        </h3>
        <ExpertiseForm data={data} onChange={setData} />
      </div>

      <Separator />

      {/* Умный импорт */}
      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Импорт данных</h3>
        <SmartImport hint="Импорт данных экспертизы из файла (заключение, программа работ, дефектная ведомость)" />
      </div>

      <Separator />

      {data.conclusion && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4" />
            Заключение
          </h3>
          <div className="bg-muted/50 rounded-md p-3">
            <Badge variant={conclusionConfig[data.conclusion]?.variant || "outline"} className="mb-2">
              {data.conclusion}
            </Badge>
          </div>
        </div>
      )}

      {data.notes && (
        <>
          <Separator />
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Примечания</h3>
            <p className="text-sm text-muted-foreground leading-relaxed bg-muted/50 rounded-md p-3">
              {data.notes}
            </p>
          </div>
        </>
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