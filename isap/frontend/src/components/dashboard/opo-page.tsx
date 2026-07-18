"use client"

import { useEffect, useState, useRef } from "react"
import { Plus, Search, ChevronDown, ChevronUp, FileText, Upload, Trash2, File, FilePlus2, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { useNavStore } from "@/lib/nav-store"
import { isapApi } from "@/lib/api-client"
import { SmartImport } from "@/components/dashboard/smart-import"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

/* ─── Типы ─── */

interface OpoObject {
  id: string
  name: string
  orgName: string
  regNumber: string
  dangerClass: string
  address: string
}

function hazardClassToLabel(cls: string | number | null | undefined): string {
  if (!cls && cls !== 0) return ""
  const num = typeof cls === "string" ? parseInt(cls, 10) : cls
  switch (num) {
    case 1: return "I"
    case 2: return "II"
    case 3: return "III"
    case 4: return "IV"
    default: return String(cls || "")
  }
}

function hazardClassToApiValue(cls: string | null | undefined): number | undefined {
  switch (cls) {
    case "I": return 1
    case "II": return 2
    case "III": return 3
    case "IV": return 4
    default: return undefined
  }
}

function mapFromApi(item: Record<string, unknown>): OpoObject {
  const hazardClass =
    typeof item.hazard_class === "string" || typeof item.hazard_class === "number" || item.hazard_class == null
      ? item.hazard_class
      : String(item.hazard_class)

  const organizationName = item.organization_name
  const organizationId = item.organization_id

  return {
    id: String(item.id || ""),
    name: String(item.name || ""),
    orgName: String(organizationName || organizationId || ""),
    regNumber: String(item.reg_number || ""),
    dangerClass: hazardClassToLabel(hazardClass),
    address: String(item.address || ""),
  }
}

interface OpoData {
  objectName: string
  objectAddress: string
  regNumber: string
  dangerClass: string
}

interface DocItem {
  id: string
  typeKey: string
  number: string
  date: string
  extraField?: string
  fileName?: string
  fileSize?: string
}

/* ─── Справочник типов документов ─── */

const DOC_TYPES = [
  { key: "plan_localization", label: "План мероприятий по локализации аварий и ликвидации их последствий", hasDate: true },
  { key: "production_control", label: "Положение о Производственном контроле", hasDate: true },
  { key: "rescue_services", label: "Договор с аварийно-спасательными службами", hasDate: true },
  { key: "financial_resources", label: "Наличие финансовых средств материальных ресурсов", hasDate: true },
  { key: "safety_attestation", label: "Аттестации по промышленной безопасности", hasDate: true, extraLabel: "Области аттестации" },
  { key: "pressure_equipment", label: "Постановка на учёт оборудования работающего под давлением", hasDate: false },
  { key: "opo_insurance", label: "Страховка ОПО", hasDate: true },
  { key: "other_docs", label: "Прочие документы", hasDate: false },
]

/* ─── Справочник подготовки документов ─── */

const PREPARE_DOCS = [
  { key: "opo_characteristics", label: "Сведения, характеризующие ОПО" },
  { key: "plan_localization", label: "План мероприятий по локализации аварий и ликвидации их последствий" },
  { key: "expertise_statement", label: "Заявление и Экспертизу Промышленной Безопасности" },
  { key: "production_control_position", label: "Положение о Производственном контроле" },
  { key: "material_resources_calc", label: "Расчет материальных ресурсов" },
  { key: "safety_attestation_statement", label: "Заявление об Аттестации по промышленной безопасности" },
  { key: "pressure_equipment_docs", label: "Документы на Постановку на учет оборудования работающего под давлением" },
  { key: "orders_instructions", label: "Приказов Инструкций" },
  { key: "production_control_report", label: "Отчет о Производственном контроле" },
  { key: "letter", label: "Письмо" },
]

/* ─── Компонент: Секция с кнопкой ─── */

function CollapsibleSection({ title, children, defaultOpen = false }: {
  title: string
  children: React.ReactNode
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border rounded-lg">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium hover:bg-muted/50 transition-colors rounded-lg"
      >
        {title}
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>
      {open && <div className="px-4 pb-4 pt-1">{children}</div>}
    </div>
  )
}

/* ─── Компонент: Форма данных ОПО ─── */

function OpoDataForm({ data, onChange }: {
  data: OpoData
  onChange: (d: OpoData) => void
}) {
  const update = (key: keyof OpoData, value: string) => onChange({ ...data, [key]: value })
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div className="md:col-span-2">
        <Label>Название объекта</Label>
        <Input placeholder="Резервуарный парк РВС-5000" value={data.objectName} onChange={(e) => update("objectName", e.target.value)} />
      </div>
      <div className="md:col-span-2">
        <Label>Адрес объекта</Label>
        <Input placeholder="г. Москва, ул. Промышленная, д. 5" value={data.objectAddress} onChange={(e) => update("objectAddress", e.target.value)} />
      </div>
      <div>
        <Label>Рег. № номер ОПО</Label>
        <Input placeholder="ОПО-77-00123" value={data.regNumber} onChange={(e) => update("regNumber", e.target.value)} />
      </div>
      <div>
        <Label>Класс опасности ОПО</Label>
        <Select
          value={data.dangerClass}
          onValueChange={(v) => update("dangerClass", v)}
        >
          <SelectTrigger>
            <SelectValue placeholder="Выберите класс" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="I">Класс I — чрезвычайно высокая опасность</SelectItem>
            <SelectItem value="II">Класс II — высокая опасность</SelectItem>
            <SelectItem value="III">Класс III — средняя опасность</SelectItem>
            <SelectItem value="IV">Класс IV — низкая опасность</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  )
}

/* ─── Компонент: Форма документов с импортом ─── */

function DocFileRow({ doc, docType, onUpdate, onRemove, fileInputRef }: {
  doc: DocItem
  docType: typeof DOC_TYPES[number]
  onUpdate: (id: string, field: keyof DocItem, value: string) => void
  onRemove: (id: string) => void
  fileInputRef: React.RefObject<HTMLInputElement | null>
}) {
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    onUpdate(doc.id, "fileName", file.name)
    onUpdate(doc.id, "fileSize", `${(file.size / 1024).toFixed(1)} КБ`)
  }

  return (
    <div key={doc.id} className="border rounded-md p-3 bg-muted/30 space-y-2">
      <div className="flex items-end gap-3 flex-wrap">
        <div className="flex-1 min-w-[140px]">
          <Label className="text-xs">Номер</Label>
          <Input
            placeholder="№ документа"
            className="h-8 text-sm"
            value={doc.number}
            onChange={(e) => onUpdate(doc.id, "number", e.target.value)}
          />
        </div>
        {docType.hasDate && (
          <div className="flex-1 min-w-[140px]">
            <Label className="text-xs">Дата</Label>
            <Input
              type="date"
              className="h-8 text-sm"
              value={doc.date}
              onChange={(e) => onUpdate(doc.id, "date", e.target.value)}
            />
          </div>
        )}
        {docType.extraLabel && (
          <div className="flex-1 min-w-[180px]">
            <Label className="text-xs">{docType.extraLabel}</Label>
            <Input
              placeholder={docType.extraLabel}
              className="h-8 text-sm"
              value={doc.extraField || ""}
              onChange={(e) => onUpdate(doc.id, "extraField", e.target.value)}
            />
          </div>
        )}
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-muted-foreground hover:text-destructive shrink-0"
          onClick={() => onRemove(doc.id)}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Импорт файла */}
      <div className="flex items-center gap-2 pt-1">
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.doc"
          className="hidden"
          onChange={handleFileChange}
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="h-7 gap-1.5 text-xs"
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload className="h-3 w-3" />
          Импорт документа
        </Button>
        {doc.fileName && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <File className="h-3 w-3 shrink-0" />
            <span className="truncate max-w-[200px]">{doc.fileName}</span>
            {doc.fileSize && (
              <span className="text-muted-foreground/60">({doc.fileSize})</span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function DocumentsForm({ docs, onChange }: {
  docs: DocItem[]
  onChange: (d: DocItem[]) => void
}) {
  const fileInputRefs = useRef<Record<string, HTMLInputElement | null>>({})
  const nextDocIdRef = useRef(0)

  const addDoc = (typeKey: string) => {
    const docType = DOC_TYPES.find((d) => d.key === typeKey)
    if (!docType) return
    const newItem: DocItem = {
      id: `doc-${++nextDocIdRef.current}`,
      typeKey,
      number: "",
      date: "",
      extraField: docType.extraLabel ? "" : undefined,
    }
    onChange([...docs, newItem])
  }

  const updateDoc = (id: string, field: keyof DocItem, value: string) => {
    onChange(docs.map((d) => (d.id === id ? { ...d, [field]: value } : d)))
  }

  const removeDoc = (id: string) => {
    onChange(docs.filter((d) => d.id !== id))
  }

  return (
    <div className="space-y-3">
      {DOC_TYPES.map((docType) => {
        const typeDocs = docs.filter((d) => d.typeKey === docType.key)
        return (
          <div key={docType.key} className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium">{docType.label}</Label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-7 gap-1 text-xs"
                onClick={() => addDoc(docType.key)}
              >
                <Plus className="h-3 w-3" />
                Добавить
              </Button>
            </div>

            {typeDocs.length === 0 && (
              <p className="text-xs text-muted-foreground pl-1">Документы не добавлены</p>
            )}

            {typeDocs.map((doc) => (
              <DocFileRow
                key={doc.id}
                doc={doc}
                docType={docType}
                onUpdate={updateDoc}
                onRemove={removeDoc}
                fileInputRef={{
                  get current() { return fileInputRefs.current[doc.id] || null },
                  set current(el) { fileInputRefs.current[doc.id] = el },
                }}
              />
            ))}
          </div>
        )
      })}
    </div>
  )
}

/* ─── Компонент: Оборудование ОПО ─── */

interface EquipmentItem {
  id: string
  name: string
  equipment_type: string
  serial_number: string
  manufacturer: string
  manufacture_year: string
}

function EquipmentForm({ facilityId }: { facilityId: string }) {
  const [items, setItems] = useState<EquipmentItem[]>([])
  const [loading, setLoading] = useState(true)
  const [savingId, setSavingId] = useState<string | null>(null)
  const nextIdRef = useRef(0)

  const load = async () => {
    try {
      setLoading(true)
      const data = await isapApi.equipment(facilityId)
      setItems((Array.isArray(data) ? data : []).map((d) => ({
        id: String(d.id || ""),
        name: String(d.name || ""),
        equipment_type: String(d.equipment_type || ""),
        serial_number: String(d.serial_number || ""),
        manufacturer: String(d.manufacturer || ""),
        manufacture_year: String(d.manufacture_year || ""),
      })))
    } catch {
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (facilityId) load()
  }, [facilityId])

  const addRow = () => {
    setItems((prev) => [...prev, {
      id: `new-${++nextIdRef.current}`,
      name: "", equipment_type: "", serial_number: "", manufacturer: "", manufacture_year: "",
    }])
  }

  const updateRow = (id: string, field: keyof EquipmentItem, value: string) => {
    setItems((prev) => prev.map((it) => it.id === id ? { ...it, [field]: value } : it))
  }

  const saveRow = async (item: EquipmentItem) => {
    setSavingId(item.id)
    try {
      const payload: Record<string, unknown> = {
        hazardous_facility_id: facilityId,
        name: item.name,
        equipment_type: item.equipment_type || null,
        serial_number: item.serial_number || null,
        manufacturer: item.manufacturer || null,
        manufacture_year: item.manufacture_year ? Number(item.manufacture_year) : null,
      }
      if (item.id.startsWith("new-")) {
        const created = await isapApi.createEquipment(payload)
        setItems((prev) => prev.map((it) => it.id === item.id ? { ...item, id: String((created as Record<string, unknown>).id) } : it))
      } else {
        await isapApi.updateEquipment(item.id, payload)
      }
      toast.success("Оборудование сохранено")
    } catch (err) {
      toast.error("Ошибка сохранения оборудования", { description: err instanceof Error ? err.message : "" })
    } finally {
      setSavingId(null)
    }
  }

  const removeRow = async (item: EquipmentItem) => {
    if (item.id.startsWith("new-")) {
      setItems((prev) => prev.filter((it) => it.id !== item.id))
      return
    }
    try {
      await isapApi.deleteEquipment(item.id)
      setItems((prev) => prev.filter((it) => it.id !== item.id))
      toast.success("Оборудование удалено")
    } catch (err) {
      toast.error("Ошибка удаления", { description: err instanceof Error ? err.message : "" })
    }
  }

  if (loading) {
    return <div className="flex items-center gap-2 text-sm text-muted-foreground py-2"><Loader2 className="h-4 w-4 animate-spin" />Загрузка оборудования...</div>
  }

  return (
    <div className="space-y-3">
      {items.length === 0 && (
        <p className="text-xs text-muted-foreground">Оборудование не добавлено. Нажмите «Добавить», чтобы создать первую запись.</p>
      )}
      {items.map((item) => (
        <div key={item.id} className="border rounded-md p-3 bg-muted/30 space-y-2">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Наименование</Label>
              <Input placeholder="Резервуар РВС-5000" className="h-8 text-sm" value={item.name} onChange={(e) => updateRow(item.id, "name", e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Тип оборудования</Label>
              <Input placeholder="Резервуар вертикальный" className="h-8 text-sm" value={item.equipment_type} onChange={(e) => updateRow(item.id, "equipment_type", e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Заводской номер</Label>
              <Input placeholder="№ 12345" className="h-8 text-sm" value={item.serial_number} onChange={(e) => updateRow(item.id, "serial_number", e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Изготовитель</Label>
              <Input placeholder="ОАО «Завод»" className="h-8 text-sm" value={item.manufacturer} onChange={(e) => updateRow(item.id, "manufacturer", e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Год выпуска</Label>
              <Input type="number" placeholder="2018" className="h-8 text-sm" value={item.manufacture_year} onChange={(e) => updateRow(item.id, "manufacture_year", e.target.value)} />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" size="sm" className="h-7 text-xs" disabled={savingId === item.id || !item.name} onClick={() => saveRow(item)}>
              {savingId === item.id && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
              Сохранить
            </Button>
            <Button type="button" variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-destructive" onClick={() => removeRow(item)}>
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      ))}
      <Button type="button" variant="outline" size="sm" className="gap-1.5" onClick={addRow}>
        <Plus className="h-3.5 w-3.5" />Добавить оборудование
      </Button>
    </div>
  )
}

/* ─── Компонент: Опасные вещества ОПО ─── */

interface SubstanceItem {
  id: string
  name: string
  cas_number: string
  quantity_kg: string
  threshold_quantity_kg: string
}

function SubstanceForm({ facilityId }: { facilityId: string }) {
  const [items, setItems] = useState<SubstanceItem[]>([])
  const [loading, setLoading] = useState(true)
  const [savingId, setSavingId] = useState<string | null>(null)
  const nextIdRef = useRef(0)

  const load = async () => {
    try {
      setLoading(true)
      const data = await isapApi.substances(facilityId)
      setItems((Array.isArray(data) ? data : []).map((d) => ({
        id: String(d.id || ""),
        name: String(d.name || ""),
        cas_number: String(d.cas_number || ""),
        quantity_kg: String(d.quantity_kg ?? ""),
        threshold_quantity_kg: String(d.threshold_quantity_kg ?? ""),
      })))
    } catch {
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (facilityId) load()
  }, [facilityId])

  const addRow = () => {
    setItems((prev) => [...prev, {
      id: `new-${++nextIdRef.current}`,
      name: "", cas_number: "", quantity_kg: "", threshold_quantity_kg: "",
    }])
  }

  const updateRow = (id: string, field: keyof SubstanceItem, value: string) => {
    setItems((prev) => prev.map((it) => it.id === id ? { ...it, [field]: value } : it))
  }

  const saveRow = async (item: SubstanceItem) => {
    setSavingId(item.id)
    try {
      const payload: Record<string, unknown> = {
        hazardous_facility_id: facilityId,
        name: item.name,
        cas_number: item.cas_number || null,
        quantity_kg: item.quantity_kg ? Number(item.quantity_kg) : null,
        threshold_quantity_kg: item.threshold_quantity_kg ? Number(item.threshold_quantity_kg) : null,
      }
      if (item.id.startsWith("new-")) {
        const created = await isapApi.createSubstance(payload)
        setItems((prev) => prev.map((it) => it.id === item.id ? { ...item, id: String((created as Record<string, unknown>).id) } : it))
      } else {
        await isapApi.updateSubstance(item.id, payload)
      }
      toast.success("Вещество сохранено")
    } catch (err) {
      toast.error("Ошибка сохранения вещества", { description: err instanceof Error ? err.message : "" })
    } finally {
      setSavingId(null)
    }
  }

  const removeRow = async (item: SubstanceItem) => {
    if (item.id.startsWith("new-")) {
      setItems((prev) => prev.filter((it) => it.id !== item.id))
      return
    }
    try {
      await isapApi.deleteSubstance(item.id)
      setItems((prev) => prev.filter((it) => it.id !== item.id))
      toast.success("Вещество удалено")
    } catch (err) {
      toast.error("Ошибка удаления", { description: err instanceof Error ? err.message : "" })
    }
  }

  if (loading) {
    return <div className="flex items-center gap-2 text-sm text-muted-foreground py-2"><Loader2 className="h-4 w-4 animate-spin" />Загрузка веществ...</div>
  }

  return (
    <div className="space-y-3">
      {items.length === 0 && (
        <p className="text-xs text-muted-foreground">Вещества не добавлены. Нажмите «Добавить», чтобы создать первую запись.</p>
      )}
      {items.map((item) => (
        <div key={item.id} className="border rounded-md p-3 bg-muted/30 space-y-2">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Наименование вещества</Label>
              <Input placeholder="Пропан" className="h-8 text-sm" value={item.name} onChange={(e) => updateRow(item.id, "name", e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">CAS-номер</Label>
              <Input placeholder="74-98-6" className="h-8 text-sm" value={item.cas_number} onChange={(e) => updateRow(item.id, "cas_number", e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Количество, кг</Label>
              <Input type="number" placeholder="5000" className="h-8 text-sm" value={item.quantity_kg} onChange={(e) => updateRow(item.id, "quantity_kg", e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Пороговое количество, кг</Label>
              <Input type="number" placeholder="5000" className="h-8 text-sm" value={item.threshold_quantity_kg} onChange={(e) => updateRow(item.id, "threshold_quantity_kg", e.target.value)} />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" size="sm" className="h-7 text-xs" disabled={savingId === item.id || !item.name} onClick={() => saveRow(item)}>
              {savingId === item.id && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
              Сохранить
            </Button>
            <Button type="button" variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-destructive" onClick={() => removeRow(item)}>
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      ))}
      <Button type="button" variant="outline" size="sm" className="gap-1.5" onClick={addRow}>
        <Plus className="h-3.5 w-3.5" />Добавить вещество
      </Button>
    </div>
  )
}

/* ─── Компонент: Полная карточка ОПО ─── */

function OpoCardForm({ initialData, onSave, onCancel }: {
  initialData?: OpoObject
  onSave: (data: Partial<OpoObject>) => void
  onCancel: () => void
}) {
  const [opoData, setOpoData] = useState<OpoData>({
    objectName: initialData?.name || "",
    objectAddress: initialData?.address || "",
    regNumber: initialData?.regNumber || "",
    dangerClass: initialData?.dangerClass || "",
  })
  const [docs, setDocs] = useState<DocItem[]>([])

  /** Заполнить поля формы данными из импорта */
  const handleImport = (data: Record<string, unknown>) => {
    // Маппинг полей из WordImportService → поля формы
    // WordImportService возвращает: f1_1 (название), f1_4 (адрес),
    // danger_class, reg_number, f1_7_1 (собственник)
    const name = String(data.f1_1 || data.name || data.full_name || "")
    const address = String(data.f1_4 || data.address || data.legal_address || "")
    const dangerClass = String(data.danger_class || "")
    const regNumber = String(data.reg_number || data.f1_3 || "")

    if (name) setOpoData((prev) => ({ ...prev, objectName: name }))
    if (address) setOpoData((prev) => ({ ...prev, objectAddress: address }))
    if (regNumber) setOpoData((prev) => ({ ...prev, regNumber }))
    if (dangerClass) setOpoData((prev) => ({ ...prev, dangerClass }))

    toast.success("Поля ОПО заполнены из импорта")
  }

  return (
    <div className="space-y-4">
      {/* Данные об ОПО — всегда открыты */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Данные об ОПО</h3>
        <OpoDataForm data={opoData} onChange={setOpoData} />
      </div>

      <Separator />

      {/* Умный импорт */}
      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Импорт данных</h3>
        <SmartImport
          hint="Импорт данных ОПО из файла (паспорт ОПО, декларация ПБ, сведения, характеризующие ОПО)"
          apiEndpoint="/api/v1/facilities/import-word"
          onImported={handleImport}
        />
      </div>

      <Separator />

      {/* Прикрепление документов — раскрываемая секция */}
      <CollapsibleSection title="Прикрепление документов" defaultOpen={false}>
        <DocumentsForm docs={docs} onChange={setDocs} />
      </CollapsibleSection>

      <Separator />

      {/* Оборудование ОПО — доступно только для сохранённого объекта */}
      {initialData?.id ? (
        <CollapsibleSection title="Оборудование" defaultOpen={false}>
          <EquipmentForm facilityId={initialData.id} />
        </CollapsibleSection>
      ) : (
        <div className="space-y-1">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Оборудование</h3>
          <p className="text-xs text-muted-foreground">Сохраните объект ОПО, затем добавьте оборудование и опасные вещества.</p>
        </div>
      )}

      <Separator />

      {/* Опасные вещества — доступны только для сохранённого объекта */}
      {initialData?.id ? (
        <CollapsibleSection title="Опасные вещества" defaultOpen={false}>
          <SubstanceForm facilityId={initialData.id} />
        </CollapsibleSection>
      ) : (
        <div className="space-y-1">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Опасные вещества</h3>
          <p className="text-xs text-muted-foreground">Доступно после сохранения объекта ОПО.</p>
        </div>
      )}

      <Separator />

      {/* Подготовить документ */}
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Подготовка документов</h3>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" className="gap-2 w-full sm:w-auto justify-center">
              <FilePlus2 className="h-4 w-4" />
              Подготовить документ
              <ChevronDown className="h-4 w-4 opacity-50" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-[460px]">
            {PREPARE_DOCS.map((doc) => (
              <DropdownMenuItem
                key={doc.key}
                className="py-2.5 cursor-pointer"
                onClick={() => toast.success(`Документ «${doc.label}» подготовлен`, { description: opoData.objectName || "Новый объект" })}
              >
                <FileText className="h-4 w-4 mr-2 shrink-0 text-muted-foreground" />
                <span className="text-sm leading-snug">{doc.label}</span>
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <Separator />

      <div className="flex justify-end gap-3">
        <Button variant="outline" onClick={onCancel}>Отмена</Button>
        <Button onClick={() => onSave({
          name: opoData.objectName,
          address: opoData.objectAddress,
          regNumber: opoData.regNumber,
          dangerClass: opoData.dangerClass,
        })}>
          Сохранить
        </Button>
      </div>
    </div>
  )
}

/* ─── Основная страница ─── */

export function OpoPage() {
  const { openFacilityDetail, opoPreSelectedOrgId, setActivePage } = useNavStore()
  const [opos, setOpos] = useState<OpoObject[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [open, setOpen] = useState(false)
  const [editingOpo, setEditingOpo] = useState<OpoObject | undefined>(undefined)

  const loadOpos = async () => {
    try {
      setLoading(true)
      const data = await isapApi.facilities()
      setOpos((data || []).map(mapFromApi))
    } catch (err) {
      toast.error("Ошибка загрузки ОПО", {
        description: err instanceof Error ? err.message : "Неизвестная ошибка",
      })
    } finally {
      setLoading(false)
    }
  }

  // Загружаем с сервера при монтировании
  const loadedRef = useRef(false)
  useEffect(() => {
    if (!loadedRef.current) {
      loadedRef.current = true
      loadOpos()
    }
  }, [])

  // Если пришли из карточки организации — открыть диалог создания
  useEffect(() => {
    if (opoPreSelectedOrgId && !loadedRef.current) {
      // Ждём загрузку, потом откроем
      return
    }
    if (opoPreSelectedOrgId && loadedRef.current && !open) {
      setEditingOpo(undefined)
      setOpen(true)
    }
  }, [opoPreSelectedOrgId, open])

  const openCard = (opo: OpoObject) => {
    setEditingOpo(opo)
    setOpen(true)
  }

  const filtered = opos.filter((o) =>
    o.name.toLowerCase().includes(search.toLowerCase()) ||
    o.regNumber.toLowerCase().includes(search.toLowerCase()) ||
    o.orgName.toLowerCase().includes(search.toLowerCase()) ||
    o.address.toLowerCase().includes(search.toLowerCase())
  )

  const handleSave = async (data: Partial<OpoObject>) => {
    try {
      if (editingOpo) {
        // Обновление существующего
        const hazardClass = hazardClassToApiValue(data.dangerClass)
        await isapApi.updateFacility(editingOpo.id, {
          name: data.name,
          address: data.address,
          reg_number: data.regNumber,
          hazard_class: hazardClass,
        })
        toast.success("Объект ОПО обновлён")
      } else {
        // Создание нового
        const hazardClass = hazardClassToApiValue(data.dangerClass)
        const orgId = opoPreSelectedOrgId || undefined
        await isapApi.createFacility({
          organization_id: orgId || "00000000-0000-0000-0000-000000000001",
          name: data.name || "Новый объект",
          reg_number: data.regNumber,
          hazard_class: hazardClass,
          address: data.address,
        })
        toast.success("Новый объект ОПО создан")
      }
      setOpen(false)
      setEditingOpo(undefined)
      // Сбросить pre-selected org
      setActivePage("opo")
      // Перезагрузить список
      await loadOpos()
    } catch (err) {
      toast.error("Ошибка сохранения", {
        description: err instanceof Error ? err.message : "Неизвестная ошибка",
      })
    }
  }

  const handleDelete = async (opo: OpoObject) => {
    try {
      await isapApi.deleteFacility(opo.id)
      setOpos((prev) => prev.filter((o) => o.id !== opo.id))
      toast.success("Объект ОПО удалён", { description: opo.name })
    } catch (err) {
      toast.error("Ошибка удаления", {
        description: err instanceof Error ? err.message : "Неизвестная ошибка",
      })
    }
  }

  const dangerClassBadge = (cls: string) => {
    switch (cls) {
      case "I": return <Badge variant="destructive">Класс I</Badge>
      case "II": return <Badge variant="default">Класс II</Badge>
      case "III": return <Badge variant="secondary">Класс III</Badge>
      case "IV": return <Badge variant="outline">Класс IV</Badge>
      default: return <Badge variant="secondary">{cls || "—"}</Badge>
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Объекты ОПО</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Реестр опасных производственных объектов с данными и документами
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={loadOpos} disabled={loading}>
            <Loader2 className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`} />
            Обновить
          </Button>
          <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) setEditingOpo(undefined) }}>
            <DialogTrigger asChild>
              <Button className="gap-2">
                <Plus className="h-4 w-4" />
                Добавить ОПО
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>{editingOpo ? "Карточка объекта ОПО" : "Новый объект ОПО"}</DialogTitle>
              </DialogHeader>
              <OpoCardForm initialData={editingOpo} onSave={handleSave} onCancel={() => { setOpen(false); setEditingOpo(undefined) }} />
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Поиск по названию, рег. №, организации или адресу..."
            className="pl-8"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          {loading && opos.length === 0 ? (
            <div className="flex items-center justify-center py-12 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin mr-2" />
              Загрузка...
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[100px]">ID</TableHead>
                  <TableHead>Наименование объекта</TableHead>
                  <TableHead className="hidden sm:table-cell">Организация</TableHead>
                  <TableHead className="hidden md:table-cell">Рег. №</TableHead>
                  <TableHead className="hidden lg:table-cell min-w-[220px]">Адрес объекта</TableHead>
                  <TableHead className="w-[160px]">Класс опасности</TableHead>
                  <TableHead className="w-[100px]">Действия</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((opo) => (
                  <TableRow key={opo.id} onClick={() => openFacilityDetail(opo.id)} className="cursor-pointer hover:bg-muted/50">
                    <TableCell className="font-mono text-xs">{opo.id.slice(0, 8)}…</TableCell>
                    <TableCell className="font-medium">{opo.name}</TableCell>
                    <TableCell className="hidden sm:table-cell text-muted-foreground">{opo.orgName}</TableCell>
                    <TableCell className="hidden md:table-cell font-mono text-sm">{opo.regNumber}</TableCell>
                    <TableCell className="hidden lg:table-cell text-muted-foreground text-sm">{opo.address}</TableCell>
                    <TableCell>
                      {dangerClassBadge(opo.dangerClass)}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); openCard(opo) }}>Открыть</Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-muted-foreground hover:text-destructive"
                          onClick={(e) => {
                            e.stopPropagation()
                            handleDelete(opo)
                          }}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
                {filtered.length === 0 && !loading && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                      Объекты ОПО не найдены
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
