"use client"

import { useEffect, useState } from "react"
import { AlertTriangle, CheckCircle2, Loader2, Plus, RefreshCcw, Trash2 } from "lucide-react"
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

function PasfDirectory() {
  const [items, setItems] = useState<AnyRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState("")
  const [showForm, setShowForm] = useState(false)
  const [error, setError] = useState("")
  const [message, setMessage] = useState("")
  const [form, setForm] = useState<AnyRecord>({})

  const load = async () => {
    setLoading(true)
    setError("")
    try {
      setItems(await isapApi.getPasfUnits(search || undefined))
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
          <Button onClick={() => setShowForm(!showForm)} className="gap-2"><Plus className="h-4 w-4" />Добавить</Button>
        </div>

        {showForm && (
          <div className="grid gap-3 md:grid-cols-2 p-4 border rounded-md">
            <div><Label>Наименование *</Label><Input value={form.name || ""} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
            <div><Label>Краткое название</Label><Input value={form.short_name || ""} onChange={(e) => setForm({ ...form, short_name: e.target.value })} /></div>
            <div><Label>Фактический адрес</Label><Input value={form.actual_address || ""} onChange={(e) => setForm({ ...form, actual_address: e.target.value })} /></div>
            <div><Label>Телефон диспетчера</Label><Input value={form.dispatch_phone || ""} onChange={(e) => setForm({ ...form, dispatch_phone: e.target.value })} /></div>
            <div><Label>Номер свидетельства</Label><Input value={form.certificate_number || ""} onChange={(e) => setForm({ ...form, certificate_number: e.target.value })} /></div>
            <div><Label>Район обслуживания</Label><Input value={form.service_area || ""} onChange={(e) => setForm({ ...form, service_area: e.target.value })} /></div>
            <div className="md:col-span-2"><Label>Примечания</Label><Textarea value={form.notes || ""} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
            <div className="md:col-span-2 flex gap-2">
              <Button onClick={handleCreate}>Создать</Button>
              <Button variant="outline" onClick={() => setShowForm(false)}>Отмена</Button>
            </div>
          </div>
        )}

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
                  <TableCell><Button variant="ghost" size="icon" onClick={() => handleDelete(String(item.id))}><Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" /></Button></TableCell>
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

function EmergencyServicesDirectory() {
  const [items, setItems] = useState<AnyRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState("")
  const [filterType, setFilterType] = useState("all")
  const [showForm, setShowForm] = useState(false)
  const [error, setError] = useState("")
  const [message, setMessage] = useState("")
  const [form, setForm] = useState<AnyRecord>({})

  const load = async () => {
    setLoading(true)
    setError("")
    try {
      setItems(await isapApi.getEmergencyServices({
        search: search || undefined,
        service_type: filterType !== "all" ? filterType : undefined,
      }))
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
          <Button onClick={() => setShowForm(!showForm)} className="gap-2"><Plus className="h-4 w-4" />Добавить</Button>
        </div>

        {showForm && (
          <div className="grid gap-3 md:grid-cols-2 p-4 border rounded-md">
            <div><Label>Тип службы *</Label>
              <Select value={form.service_type || "fire"} onValueChange={(v) => setForm({ ...form, service_type: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{Object.entries(SERVICE_TYPE_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div><Label>Наименование *</Label><Input value={form.name || ""} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
            <div><Label>Адрес</Label><Input value={form.address || ""} onChange={(e) => setForm({ ...form, address: e.target.value })} /></div>
            <div><Label>Телефон</Label><Input value={form.phone || ""} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
            <div><Label>Телефон диспетчера</Label><Input value={form.dispatcher_phone || ""} onChange={(e) => setForm({ ...form, dispatcher_phone: e.target.value })} /></div>
            <div><Label>Район обслуживания</Label><Input value={form.service_area || ""} onChange={(e) => setForm({ ...form, service_area: e.target.value })} /></div>
            <div className="md:col-span-2"><Label>Примечания</Label><Textarea value={form.notes || ""} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
            <div className="md:col-span-2 flex gap-2">
              <Button onClick={handleCreate}>Создать</Button>
              <Button variant="outline" onClick={() => setShowForm(false)}>Отмена</Button>
            </div>
          </div>
        )}

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
                  <TableCell><Button variant="ghost" size="icon" onClick={() => handleDelete(String(item.id))}><Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" /></Button></TableCell>
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
