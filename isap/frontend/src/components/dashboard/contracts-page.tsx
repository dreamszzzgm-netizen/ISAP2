"use client"

import { useState } from "react"
import { Plus, Search, FileText, Building2, CalendarRange, Trash2 } from "lucide-react"
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

type ContractStatus = "проект" | "на согласовании" | "действует" | "завершён" | "расторгнут"
type ContractType = "экспертиза" | "производственный контроль" | "обследование" | "страхование" | "аттестация" | "прочее"

interface Contract {
  id: string
  number: string
  organization: string
  type: ContractType
  subject: string
  amount: string
  dateStart: string
  dateEnd: string
  status: ContractStatus
  description: string
}

interface ContractFormData {
  number: string
  organization: string
  type: ContractType
  subject: string
  amount: string
  dateStart: string
  dateEnd: string
  status: ContractStatus
  description: string
}

/* ─── Моковые данные ─── */

const mockContracts: Contract[] = [
  {
    id: "ДГВ-001",
    number: "Д-2026/045",
    organization: "ООО «Нефтегазпром»",
    type: "экспертиза",
    subject: "Экспертиза промышленной безопасности резервуарного парка",
    amount: "850 000 ₽",
    dateStart: "2026-01-15",
    dateEnd: "2026-12-31",
    status: "действует",
    description: "Комплексная экспертиза промышленной безопасности опасных производственных объектов резервуарного парка РВС-5000, включая обследование технического состояния, оценку риска и разработку рекомендаций.",
  },
  {
    id: "ДГВ-002",
    number: "Д-2026/058",
    organization: "АО «Химический завод»",
    type: "производственный контроль",
    subject: "Организация производственного контроля",
    amount: "1 200 000 ₽",
    dateStart: "2026-03-01",
    dateEnd: "2027-02-28",
    status: "действует",
    description: "Ведение производственного контроля за соблюдением требований промышленной безопасности на объектах организации.",
  },
  {
    id: "ДГВ-003",
    number: "Д-2026/072",
    organization: "ИП Сидоров К.А.",
    type: "страхование",
    subject: "Обязательное страхование ответственности ОПО",
    amount: "145 000 ₽",
    dateStart: "2026-04-01",
    dateEnd: "2027-03-31",
    status: "действует",
    description: "Договор обязательного страхования гражданской ответственности владельца опасного производственного объекта.",
  },
  {
    id: "ДГВ-004",
    number: "Д-2026/033",
    organization: "ООО «Промтехмонтаж»",
    type: "аттестация",
    subject: "Аттестация специалистов по промышленной безопасности",
    amount: "320 000 ₽",
    dateStart: "2026-02-10",
    dateEnd: "2026-08-10",
    status: "действует",
    description: "Организация и проведение аттестации специалистов организации в области промышленной безопасности.",
  },
  {
    id: "ДГВ-005",
    number: "Д-2026/019",
    organization: "ПАО «Газпереработка»",
    type: "обследование",
    subject: "Техническое обследование оборудования под давлением",
    amount: "670 000 ₽",
    dateStart: "2026-05-01",
    dateEnd: "2026-10-31",
    status: "на согласовании",
    description: "Комплексное техническое обследование сосудов и аппаратов, работающих под избыточным давлением.",
  },
  {
    id: "ДГВ-006",
    number: "Д-2025/088",
    organization: "ООО «Транснефть-Сервис»",
    type: "производственный контроль",
    subject: "Производственный контроль — объекты магистрального транспорта",
    amount: "2 100 000 ₽",
    dateStart: "2025-06-01",
    dateEnd: "2026-05-31",
    status: "завершён",
    description: "Ведение производственного контроля на объектах магистрального трубопроводного транспорта нефти.",
  },
  {
    id: "ДГВ-007",
    number: "Д-2026/081",
    organization: "ЗАО «Химтрейд»",
    type: "экспертиза",
    subject: "Экспертиза зданий и сооружений на ОПО",
    amount: "540 000 ₽",
    dateStart: "2026-06-15",
    dateEnd: "2026-09-15",
    status: "проект",
    description: "Экспертиза промышленной безопасности зданий и сооружений, расположенных на территории опасного производственного объекта.",
  },
  {
    id: "ДГВ-008",
    number: "Д-2025/065",
    organization: "ООО «Нефтегазпром»",
    type: "обследование",
    subject: "Диагностика трубопроводов",
    amount: "430 000 ₽",
    dateStart: "2025-09-01",
    dateEnd: "2026-03-01",
    status: "завершён",
    description: "Инструментальная диагностика и дефектоскопия технологических трубопроводов.",
  },
]

/* ─── Справочники ─── */

const contractTypeConfig: Record<ContractType, { label: string; variant: "destructive" | "default" | "secondary" | "outline" }> = {
  экспертиза: { label: "Экспертиза", variant: "default" },
  "производственный контроль": { label: "Произв. контроль", variant: "secondary" },
  обследование: { label: "Обследование", variant: "outline" },
  страхование: { label: "Страхование", variant: "outline" },
  аттестация: { label: "Аттестация", variant: "secondary" },
  прочее: { label: "Прочее", variant: "outline" },
}

const contractStatusConfig: Record<ContractStatus, { label: string; variant: "destructive" | "default" | "secondary" | "outline" }> = {
  проект: { label: "Проект", variant: "outline" },
  "на согласовании": { label: "На согласовании", variant: "secondary" },
  действует: { label: "Действует", variant: "default" },
  завершён: { label: "Завершён", variant: "secondary" },
  расторгнут: { label: "Расторгнут", variant: "destructive" },
}

function formatDate(dateStr: string) {
  if (!dateStr) return "—"
  const d = new Date(dateStr)
  return d.toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" })
}

/* ─── Форма договора ─── */

function ContractForm({ data, onChange }: { data: ContractFormData; onChange: (d: ContractFormData) => void }) {
  const update = <K extends keyof ContractFormData>(key: K, value: ContractFormData[K]) =>
    onChange({ ...data, [key]: value })

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <Label>Номер договора</Label>
          <Input
            placeholder="Д-2026/001"
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
        <Label>Предмет договора</Label>
        <Input
          placeholder="Краткое описание предмета договора"
          value={data.subject}
          onChange={(e) => update("subject", e.target.value)}
        />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <Label>Тип договора</Label>
          <Select value={data.type} onValueChange={(v) => update("type", v as ContractType)}>
            <SelectTrigger>
              <SelectValue placeholder="Выберите" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="экспертиза">Экспертиза</SelectItem>
              <SelectItem value="производственный контроль">Производственный контроль</SelectItem>
              <SelectItem value="обследование">Обследование</SelectItem>
              <SelectItem value="страхование">Страхование</SelectItem>
              <SelectItem value="аттестация">Аттестация</SelectItem>
              <SelectItem value="прочее">Прочее</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label>Сумма договора</Label>
          <Input
            placeholder="1 000 000 ₽"
            value={data.amount}
            onChange={(e) => update("amount", e.target.value)}
          />
        </div>
        <div>
          <Label>Статус</Label>
          <Select value={data.status} onValueChange={(v) => update("status", v as ContractStatus)}>
            <SelectTrigger>
              <SelectValue placeholder="Выберите" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="проект">Проект</SelectItem>
              <SelectItem value="на согласовании">На согласовании</SelectItem>
              <SelectItem value="действует">Действует</SelectItem>
              <SelectItem value="завершён">Завершён</SelectItem>
              <SelectItem value="расторгнут">Расторгнут</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <Label>Дата заключения</Label>
          <Input
            type="date"
            value={data.dateStart}
            onChange={(e) => update("dateStart", e.target.value)}
          />
        </div>
        <div>
          <Label>Дата окончания</Label>
          <Input
            type="date"
            value={data.dateEnd}
            onChange={(e) => update("dateEnd", e.target.value)}
          />
        </div>
      </div>
      <div>
        <Label>Описание</Label>
        <Textarea
          placeholder="Подробное описание условий договора..."
          rows={3}
          value={data.description}
          onChange={(e) => update("description", e.target.value)}
        />
      </div>
    </div>
  )
}

/* ─── Основная страница ─── */

export function ContractsPage() {
  const [contracts, setContracts] = useState<Contract[]>(mockContracts)
  const [search, setSearch] = useState("")
  const [filterStatus, setFilterStatus] = useState<string>("all")
  const [filterType, setFilterType] = useState<string>("all")
  const [open, setOpen] = useState(false)
  const [editingContract, setEditingContract] = useState<Contract | undefined>(undefined)

  const openCard = (contract: Contract) => {
    setEditingContract(contract)
    setOpen(true)
  }

  const filtered = contracts.filter((c) => {
    const matchSearch =
      c.number.toLowerCase().includes(search.toLowerCase()) ||
      c.organization.toLowerCase().includes(search.toLowerCase()) ||
      c.subject.toLowerCase().includes(search.toLowerCase()) ||
      c.id.toLowerCase().includes(search.toLowerCase())
    const matchStatus = filterStatus === "all" || c.status === filterStatus
    const matchType = filterType === "all" || c.type === filterType
    return matchSearch && matchStatus && matchType
  })

  const handleSave = (data: ContractFormData) => {
    if (editingContract) {
      setContracts((prev) =>
        prev.map((c) =>
          c.id === editingContract.id ? { ...c, ...data } : c
        )
      )
    } else {
      const newContract: Contract = {
        id: `ДГВ-${String(contracts.length + 1).padStart(3, "0")}`,
        ...data,
      }
      setContracts((prev) => [...prev, newContract])
    }
    setOpen(false)
    setEditingContract(undefined)
  }

  const initialFormData: ContractFormData = {
    number: editingContract?.number || "",
    organization: editingContract?.organization || "",
    type: editingContract?.type || "экспертиза",
    subject: editingContract?.subject || "",
    amount: editingContract?.amount || "",
    dateStart: editingContract?.dateStart || "",
    dateEnd: editingContract?.dateEnd || "",
    status: editingContract?.status || "проект",
    description: editingContract?.description || "",
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Договора</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Реестр договоров и соглашений
          </p>
        </div>
        <Dialog
          open={open}
          onOpenChange={(v) => {
            setOpen(v)
            if (!v) setEditingContract(undefined)
          }}
        >
          <DialogTrigger asChild>
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              Добавить договор
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                {editingContract ? "Редактирование договора" : "Новый договор"}
              </DialogTitle>
            </DialogHeader>
            <ContractFormWrapper
              key={editingContract?.id || "new"}
              initialData={initialFormData}
              onSave={handleSave}
              onCancel={() => {
                setOpen(false)
                setEditingContract(undefined)
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
            placeholder="Поиск по номеру, организации, предмету..."
            className="pl-8"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select value={filterStatus} onValueChange={setFilterStatus}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Статус" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Все статусы</SelectItem>
            <SelectItem value="проект">Проект</SelectItem>
            <SelectItem value="на согласовании">На согласовании</SelectItem>
            <SelectItem value="действует">Действует</SelectItem>
            <SelectItem value="завершён">Завершён</SelectItem>
            <SelectItem value="расторгнут">Расторгнут</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filterType} onValueChange={setFilterType}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Тип" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Все типы</SelectItem>
            <SelectItem value="экспертиза">Экспертиза</SelectItem>
            <SelectItem value="производственный контроль">Производственный контроль</SelectItem>
            <SelectItem value="обследование">Обследование</SelectItem>
            <SelectItem value="страхование">Страхование</SelectItem>
            <SelectItem value="аттестация">Аттестация</SelectItem>
            <SelectItem value="прочее">Прочее</SelectItem>
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
                <TableHead className="hidden lg:table-cell">Предмет</TableHead>
                <TableHead className="w-[120px]">Тип</TableHead>
                <TableHead className="hidden sm:table-cell w-[110px]">Сумма</TableHead>
                <TableHead className="w-[130px]">Статус</TableHead>
                <TableHead className="hidden md:table-cell w-[100px]">Окончание</TableHead>
                <TableHead className="w-[100px]">Действия</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((contract) => (
                <TableRow
                  key={contract.id}
                  onDoubleClick={() => openCard(contract)}
                  className="cursor-pointer"
                >
                  <TableCell className="font-mono text-xs">{contract.id}</TableCell>
                  <TableCell className="font-mono text-sm">{contract.number}</TableCell>
                  <TableCell className="font-medium">{contract.organization}</TableCell>
                  <TableCell className="hidden lg:table-cell text-muted-foreground text-sm max-w-[200px] truncate">
                    {contract.subject}
                  </TableCell>
                  <TableCell>
                    <Badge variant={contractTypeConfig[contract.type].variant}>
                      {contractTypeConfig[contract.type].label}
                    </Badge>
                  </TableCell>
                  <TableCell className="hidden sm:table-cell font-mono text-sm">{contract.amount}</TableCell>
                  <TableCell>
                    <Badge variant={contractStatusConfig[contract.status].variant}>
                      {contractStatusConfig[contract.status].label}
                    </Badge>
                  </TableCell>
                  <TableCell className="hidden md:table-cell text-muted-foreground text-sm">
                    {formatDate(contract.dateEnd)}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); openCard(contract) }}>Открыть</Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground hover:text-destructive"
                        onClick={(e) => {
                          e.stopPropagation()
                          setContracts((prev) => prev.filter((c) => c.id !== contract.id))
                          toast.success("Договор удалён", { description: contract.number + " — " + contract.organization })
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
                    Договоры не найдены
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

function ContractFormWrapper({
  initialData,
  onSave,
  onCancel,
}: {
  initialData: ContractFormData
  onSave: (data: ContractFormData) => void
  onCancel: () => void
}) {
  const [data, setData] = useState<ContractFormData>(initialData)

  return (
    <div className="space-y-4">
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
          <FileText className="h-4 w-4" />
          Реквизиты договора
        </h3>
        <ContractForm data={data} onChange={setData} />
      </div>

      <Separator />

      {/* Умный импорт */}
      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Импорт данных</h3>
        <SmartImport hint="Импорт данных договора из файла (скан договора, спецификация, доп. соглашение)" />
      </div>

      <Separator />

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