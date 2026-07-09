"use client"

import { useEffect, useRef, useState } from "react"
import { AlertTriangle, CheckCircle2, Download, FileUp, Loader2, Pencil, Plus, RefreshCcw, Trash2 } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { isapApi } from "@/lib/api-client"

type AnyRecord = Record<string, unknown>

const SERVICE_TYPE_LABELS: Record<string, string> = {
  fire: "Пожарная охрана",
  medical: "Медицинская помощь",
  police: "Полиция",
  gas: "Газовая служба",
  edds: "ЕДДС",
  other: "Прочее",
}

export function DirectoriesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Справочники</h1>
        <p className="text-muted-foreground text-sm mt-1">ПАСФ / АСФ и аварийные службы для ПМЛА</p>
      </div>
      <Tabs defaultValue="pasf" className="space-y-4">
        <TabsList>
          <TabsTrigger value="pasf">ПАСФ / АСФ</TabsTrigger>
          <TabsTrigger value="services">Аварийные службы</TabsTrigger>
        </TabsList>
        <TabsContent value="pasf"><PasfDirectory /></TabsContent>
        <TabsContent value="services"><EmergencyServicesDirectory /></TabsContent>
      </Tabs>
    </div>
  )
}

interface PasfFormProps {
  form: AnyRecord
  setForm: (value: AnyRecord) => void
  editingItem: AnyRecord | null
  onSubmit: () => void
  onCancel: () => void
}

function PasfForm({ form, setForm, editingItem, onSubmit, onCancel }: PasfFormProps) {
  return (
    <div className="grid gap-3 md:grid-cols-2 p-4 border rounded-md">
      <div><Label>Наименование *</Label><Input value={(form.name as string) || ""} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
      <div><Label>Краткое название</Label><Input value={(form.short_name as string) || ""} onChange={(e) => setForm({ ...form, short_name: e.target.value })} /></div>
      <div><Label>Юридический адрес</Label><Input value={(form.legal_address as string) || ""} onChange={(e) => setForm({ ...form, legal_address: e.target.value })} /></div>
      <div><Label>Фактический адрес</Label><Input value={(form.actual_address as string) || ""} onChange={(e) => setForm({ ...form, actual_address: e.target.value })} /></div>
      <div><Label>Телефон диспетчера</Label><Input value={(form.dispatch_phone as string) || ""} onChange={(e) => setForm({ ...form, dispatch_phone: e.target.value })} /></div>
      <div><Label>Email</Label><Input value={(form.email as string) || ""} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
      <div><Label>Руководитель</Label><Input value={(form.manager_name as string) || ""} onChange={(e) => setForm({ ...form, manager_name: e.target.value })} /></div>
      <div><Label>Номер свидетельства</Label><Input value={(form.certificate_number as string) || ""} onChange={(e) => setForm({ ...form, certificate_number: e.target.value })} /></div>
      <div><Label>Дата свидетельства</Label><Input value={(form.certificate_date as string) || ""} onChange={(e) => setForm({ ...form, certificate_date: e.target.value })} /></div>
      <div><Label>Свидетельство действительно до</Label><Input value={(form.certificate_valid_until as string) || ""} onChange={(e) => setForm({ ...form, certificate_valid_until: e.target.value })} /></div>
      <div><Label>Кол-во сотрудников</Label><Input value={(form.staff_count as string) || ""} onChange={(e) => setForm({ ...form, staff_count: e.target.value })} /></div>
      <div><Label>Режим готовности</Label><Input value={(form.readiness_mode as string) || ""} onChange={(e) => setForm({ ...form, readiness_mode: e.target.value })} /></div>
      <div><Label>Район обслуживания</Label><Input value={(form.service_area as string) || ""} onChange={(e) => setForm({ ...form, service_area: e.target.value })} /></div>
      <div className="md:col-span-2"><Label>Примечания</Label><Textarea value={(form.notes as string) || ""} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
      <div className="md:col-span-2 flex gap-2">
        <Button onClick={onSubmit}>{editingItem ? "Сохранить" : "Создать"}</Button>
        <Button variant="outline" onClick={onCancel}>Отмена</Button>
      </div>
    </div>
  )
}

function PasfDirectory() {
  const [items, setItems] = useState<AnyRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState("")
  const [showForm, setShowForm] = useState(false)
  const [editingItem, setEditingItem] = useState<AnyRecord | null>(null)
  const [error, setError] = useState("")
  const [message, setMessage] = useState("")
  const [form, setForm] = useState<AnyRecord>({})

  const load = async () => {
    setLoading(true)
    setError("")
    try {
      setItems((await isapApi.getPasfUnits(search || undefined)) as AnyRecord[])
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка загрузки")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleCreate = async () => {
    if (!form.name) { setError("Введите наименование"); return }
    try {
      await isapApi.createPasfUnit(form)
      setMessage("ПАСФ создан")
      setShowForm(false)
      setForm({})
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка создания")
    }
  }

  const handleEdit = (item: AnyRecord) => {
    setEditingItem(item)
    setForm({ ...item })
    setShowForm(false)
    setError("")
    setMessage("")
  }

  const handleUpdate = async () => {
    if (!editingItem?.id) return
    if (!form.name) { setError("Введите наименование"); return }
    try {
      await isapApi.updatePasfUnit(String(editingItem.id), form)
      setMessage("ПАСФ обновлён")
      setEditingItem(null)
      setForm({})
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка обновления")
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm("Удалить ПАСФ?")) return
    try {
      await isapApi.deletePasfUnit(id)
      setMessage("ПАСФ удалён")
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка удаления")
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">ПАСФ / АСФ</CardTitle>
        <CardDescription>Пожарно-спасательные формирования и аварийно-спасательные службы</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
        {message && <Alert><CheckCircle2 className="h-4 w-4" /><AlertDescription>{message}</AlertDescription></Alert>}

        <div className="flex gap-2">
          <Input placeholder="Поиск..." value={search} onChange={(e) => setSearch(e.target.value)} onKeyDown={(e) => e.key === "Enter" && load()} className="max-w-sm" />
          <Button variant="outline" onClick={load} disabled={loading}><RefreshCcw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /></Button>
          <ImportWidget importType="pasf_units" onImported={load} />
          <ExportWidget directoryType="pasf" />
          <Button onClick={() => { setShowForm(!showForm); setEditingItem(null); setForm({}) }} className="gap-2"><Plus className="h-4 w-4" />Добавить</Button>
        </div>

        {showForm && <PasfForm form={form} setForm={setForm} editingItem={editingItem} onSubmit={handleCreate} onCancel={() => { setShowForm(false); setEditingItem(null); setForm({}) }} />}
        {editingItem && <PasfForm form={form} setForm={setForm} editingItem={editingItem} onSubmit={handleUpdate} onCancel={() => { setShowForm(false); setEditingItem(null); setForm({}) }} />}

        <div className="overflow-auto rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Наименование</TableHead>
                <TableHead className="hidden md:table-cell">Адрес</TableHead>
                <TableHead className="hidden md:table-cell">Телефон</TableHead>
                <TableHead className="hidden lg:table-cell">Свидетельство</TableHead>
                <TableHead className="w-[80px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.length === 0 ? (
                <TableRow><TableCell colSpan={5} className="text-center py-8 text-muted-foreground">Нет данных</TableCell></TableRow>
              ) : items.map((item) => (
                <TableRow key={String(item.id)}>
                  <TableCell className="font-medium">{String(item.name)}</TableCell>
                  <TableCell className="hidden md:table-cell text-muted-foreground text-sm">{String(item.actual_address || "—")}</TableCell>
                  <TableCell className="hidden md:table-cell text-sm">{String(item.dispatch_phone || "—")}</TableCell>
                  <TableCell className="hidden lg:table-cell text-sm">{String(item.certificate_number || "—")}</TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="icon" onClick={() => handleEdit(item)}><Pencil className="h-4 w-4 text-muted-foreground hover:text-primary" /></Button>
                      <Button variant="ghost" size="icon" onClick={() => handleDelete(String(item.id))}><Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" /></Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <div className="text-xs text-muted-foreground">Всего: {items.length}</div>
      </CardContent>
    </Card>
  )
}

interface ServiceFormProps {
  form: AnyRecord
  setForm: (value: AnyRecord) => void
  editingItem: AnyRecord | null
  onSubmit: () => void
  onCancel: () => void
}

function ServiceForm({ form, setForm, editingItem, onSubmit, onCancel }: ServiceFormProps) {
  return (
    <div className="grid gap-3 md:grid-cols-2 p-4 border rounded-md">
      <div><Label>Тип службы *</Label>
        <Select value={(form.service_type as string) || "fire"} onValueChange={(v) => setForm({ ...form, service_type: v })}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>{Object.entries(SERVICE_TYPE_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}</SelectContent>
        </Select>
      </div>
      <div><Label>Наименование *</Label><Input value={(form.name as string) || ""} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
      <div><Label>Адрес</Label><Input value={(form.address as string) || ""} onChange={(e) => setForm({ ...form, address: e.target.value })} /></div>
      <div><Label>Телефон</Label><Input value={(form.phone as string) || ""} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
      <div><Label>Телефон диспетчера</Label><Input value={(form.dispatcher_phone as string) || ""} onChange={(e) => setForm({ ...form, dispatcher_phone: e.target.value })} /></div>
      <div><Label>Муниципалитет</Label><Input value={(form.municipality as string) || ""} onChange={(e) => setForm({ ...form, municipality: e.target.value })} /></div>
      <div><Label>Населённый пункт</Label><Input value={(form.settlement as string) || ""} onChange={(e) => setForm({ ...form, settlement: e.target.value })} /></div>
      <div><Label>Район обслуживания</Label><Input value={(form.service_area as string) || ""} onChange={(e) => setForm({ ...form, service_area: e.target.value })} /></div>
      <div><Label>Широта</Label><Input value={(form.latitude as string) || ""} onChange={(e) => setForm({ ...form, latitude: e.target.value })} /></div>
      <div><Label>Долгота</Label><Input value={(form.longitude as string) || ""} onChange={(e) => setForm({ ...form, longitude: e.target.value })} /></div>
      <div className="md:col-span-2"><Label>Примечания</Label><Textarea value={(form.notes as string) || ""} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
      <div className="md:col-span-2 flex gap-2">
        <Button onClick={onSubmit}>{editingItem ? "Сохранить" : "Создать"}</Button>
        <Button variant="outline" onClick={onCancel}>Отмена</Button>
      </div>
    </div>
  )
}

function EmergencyServicesDirectory() {
  const [items, setItems] = useState<AnyRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState("")
  const [filterType, setFilterType] = useState("all")
  const [showForm, setShowForm] = useState(false)
  const [editingItem, setEditingItem] = useState<AnyRecord | null>(null)
  const [error, setError] = useState("")
  const [message, setMessage] = useState("")
  const [form, setForm] = useState<AnyRecord>({})

  const load = async () => {
    setLoading(true)
    setError("")
    try {
      setItems((await isapApi.getEmergencyServices({
        search: search || undefined,
        service_type: filterType !== "all" ? filterType : undefined,
      })) as AnyRecord[])
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка загрузки")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleCreate = async () => {
    if (!form.name) { setError("Введите наименование"); return }
    try {
      await isapApi.createEmergencyService(form)
      setMessage("Служба создана")
      setShowForm(false)
      setForm({})
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка создания")
    }
  }

  const handleEdit = (item: AnyRecord) => {
    setEditingItem(item)
    setForm({ ...item })
    setShowForm(false)
    setError("")
    setMessage("")
  }

  const handleUpdate = async () => {
    if (!editingItem?.id) return
    if (!form.name) { setError("Введите наименование"); return }
    try {
      await isapApi.updateEmergencyService(String(editingItem.id), form)
      setMessage("Служба обновлена")
      setEditingItem(null)
      setForm({})
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка обновления")
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm("Удалить службу?")) return
    try {
      await isapApi.deleteEmergencyService(id)
      setMessage("Служба удалена")
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка удаления")
    }
  }

  const typeBadge = (type: string) => {
    const labels: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
      fire: { label: "Пожарная", variant: "destructive" },
      medical: { label: "Медицинская", variant: "default" },
      police: { label: "Полиция", variant: "secondary" },
      gas: { label: "Газовая", variant: "outline" },
      edds: { label: "ЕДДС", variant: "default" },
    }
    const cfg = labels[type] || { label: type, variant: "outline" as const }
    return <Badge variant={cfg.variant}>{cfg.label}</Badge>
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Аварийные службы</CardTitle>
        <CardDescription>Пожарные, скорая, полиция, газовая служба, ЕДДС</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
        {message && <Alert><CheckCircle2 className="h-4 w-4" /><AlertDescription>{message}</AlertDescription></Alert>}

        <div className="flex flex-wrap gap-2">
          <Input placeholder="Поиск..." value={search} onChange={(e) => setSearch(e.target.value)} onKeyDown={(e) => e.key === "Enter" && load()} className="max-w-sm" />
          <Select value={filterType} onValueChange={setFilterType}>
            <SelectTrigger className="w-[180px]"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Все типы</SelectItem>
              {Object.entries(SERVICE_TYPE_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={load} disabled={loading}><RefreshCcw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /></Button>
          <ImportWidget importType="emergency_services" onImported={load} />
          <ExportWidget directoryType="emergency-services" />
          <Button onClick={() => { setShowForm(!showForm); setEditingItem(null); setForm({}) }} className="gap-2"><Plus className="h-4 w-4" />Добавить</Button>
        </div>

        {showForm && <ServiceForm form={form} setForm={setForm} editingItem={editingItem} onSubmit={handleCreate} onCancel={() => { setShowForm(false); setEditingItem(null); setForm({}) }} />}
        {editingItem && <ServiceForm form={form} setForm={setForm} editingItem={editingItem} onSubmit={handleUpdate} onCancel={() => { setShowForm(false); setEditingItem(null); setForm({}) }} />}

        <div className="overflow-auto rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Тип</TableHead>
                <TableHead>Наименование</TableHead>
                <TableHead className="hidden md:table-cell">Адрес</TableHead>
                <TableHead className="hidden md:table-cell">Телефон</TableHead>
                <TableHead className="w-[80px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.length === 0 ? (
                <TableRow><TableCell colSpan={5} className="text-center py-8 text-muted-foreground">Нет данных</TableCell></TableRow>
              ) : items.map((item) => (
                <TableRow key={String(item.id)}>
                  <TableCell>{typeBadge(String(item.service_type))}</TableCell>
                  <TableCell className="font-medium">{String(item.name)}</TableCell>
                  <TableCell className="hidden md:table-cell text-muted-foreground text-sm">{String(item.address || "—")}</TableCell>
                  <TableCell className="hidden md:table-cell text-sm">{String(item.phone || "—")}</TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="icon" onClick={() => handleEdit(item)}><Pencil className="h-4 w-4 text-muted-foreground hover:text-primary" /></Button>
                      <Button variant="ghost" size="icon" onClick={() => handleDelete(String(item.id))}><Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" /></Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <div className="text-xs text-muted-foreground">Всего: {items.length}</div>
      </CardContent>
    </Card>
  )
}

function ExportWidget({ directoryType }: { directoryType: string }) {
  const [loading, setLoading] = useState(false)

  const handleExport = async (format: "csv" | "xlsx") => {
    setLoading(true)
    try {
      const response = await fetch(`/api/v1/directories/${directoryType}/export?format=${format}`, {
        headers: { Authorization: "Bearer isap-secret-2026" },
      })
      if (!response.ok) throw new Error("Ошибка экспорта")
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `directories_${directoryType}_${new Date().toISOString().slice(0, 10)}.${format === "csv" ? "csv" : "xlsx"}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      alert(err instanceof Error ? err.message : "Ошибка экспорта")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex gap-1">
      <Button variant="outline" size="sm" onClick={() => handleExport("csv")} disabled={loading} className="gap-1">
        <Download className="h-3.5 w-3.5" /> CSV
      </Button>
      <Button variant="outline" size="sm" onClick={() => handleExport("xlsx")} disabled={loading} className="gap-1">
        <Download className="h-3.5 w-3.5" /> Excel
      </Button>
    </div>
  )
}

function ImportWidget({ importType, onImported }: { importType: string; onImported: () => void }) {
  const [showPreview, setShowPreview] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [message, setMessage] = useState("")
  const [job, setJob] = useState<AnyRecord | null>(null)
  const [previewRows, setPreviewRows] = useState<AnyRecord[]>([])
  const [importing, setImporting] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setLoading(true)
    setError("")
    setMessage("")
    setJob(null)
    setPreviewRows([])
    try {
      const result = await isapApi.previewImport(importType, file)
      setJob(result.job)
      setPreviewRows(result.rows || [])
      setShowPreview(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка preview")
    } finally {
      setLoading(false)
      if (fileRef.current) fileRef.current.value = ""
    }
  }

  const handleConfirm = async () => {
    if (!job?.id) return
    setImporting(true)
    setError("")
    try {
      const result = await isapApi.confirmImportJob(String(job.id))
      setMessage(`Импорт завершён: создано ${result.created_rows || 0}, обновлено ${result.updated_rows || 0}, пропущено ${result.skipped_rows || 0}`)
      setShowPreview(false)
      setJob(null)
      setPreviewRows([])
      onImported()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка импорта")
    } finally {
      setImporting(false)
    }
  }

  return (
    <>
      <input ref={fileRef} type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={handleFileSelect} />
      <Button variant="outline" onClick={() => fileRef.current?.click()} disabled={loading} className="gap-2">
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileUp className="h-4 w-4" />}
        Импорт Excel/CSV
      </Button>

      {showPreview && job && (
        <div className="col-span-full space-y-3 p-4 border rounded-md bg-muted/30">
          <div className="flex items-center justify-between">
            <div className="text-sm font-medium">
              Preview: {String(job.filename || "импорт")} ({previewRows.length} строк)
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={handleConfirm} disabled={importing} className="gap-2">
                {importing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
                Подтвердить импорт
              </Button>
              <Button size="sm" variant="ghost" onClick={() => { setShowPreview(false); setJob(null) }}>Отмена</Button>
            </div>
          </div>
          {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
          {message && <Alert><CheckCircle2 className="h-4 w-4" /><AlertDescription>{message}</AlertDescription></Alert>}
          <div className="flex gap-3 text-xs">
            <Badge variant="default">Создать: {String(job.created_rows || 0)}</Badge>
            <Badge variant="secondary">Обновить: {String(job.updated_rows || 0)}</Badge>
            <Badge variant="outline">Ошибки: {String(job.error_rows || 0)}</Badge>
          </div>
          {previewRows.length > 0 && (
            <div className="max-h-60 overflow-auto rounded border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[50px]">#</TableHead>
                    <TableHead>Данные</TableHead>
                    <TableHead>Статус</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {previewRows.slice(0, 20).map((row, idx) => (
                    <TableRow key={String(row.id || idx)}>
                      <TableCell className="text-xs">{String(row.row_number || idx + 1)}</TableCell>
                      <TableCell className="text-xs max-w-[300px] truncate">
                        {Object.entries((row.normalized_data as Record<string, unknown>) || {}).slice(0, 3).map(([k, v]) => `${k}: ${String(v)}`).join(", ")}
                      </TableCell>
                      <TableCell>
                        <Badge variant={row.status === "invalid" ? "destructive" : row.status === "duplicate" ? "secondary" : "default"}>
                          {row.status === "invalid" ? "Ошибка" : row.status === "duplicate" ? "Дубликат" : "OK"}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      )}
    </>
  )
}
