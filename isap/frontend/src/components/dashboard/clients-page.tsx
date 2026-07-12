"use client"

import { useState, useEffect, useCallback } from "react"
import { Plus, Search, Building2, User, Trash2 } from "lucide-react"
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
  Tabs,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import { SmartImport } from "@/components/dashboard/smart-import"
import { toast } from "sonner"
import { apiRequest } from "@/lib/api-client"
import { useNavStore } from "@/lib/nav-store"

type CounterpartyType = "legal" | "ip"

interface Client {
  id: string
  name: string
  type: CounterpartyType
  inn: string
  ogrn: string
  address: string
  phone: string
  email: string
}

function ClientForm({ initialData, onSave, onCancel, onCreateOpo }: {
  initialData?: Client
  onSave: (data: Partial<Client>) => void
  onCancel: () => void
  onCreateOpo?: () => void
}) {
  const [type, setType] = useState<CounterpartyType>(initialData?.type || "legal")

  const [form, setForm] = useState({
    fullName: initialData?.name || "",
    inn: initialData?.inn || "",
    ogrn: initialData?.ogrn || "",
    kpp: "",
    legalAddress: initialData?.address || "",
    actualAddress: initialData?.address || "",
    director: "",
    phone: initialData?.phone || "",
    email: initialData?.email || "",
    bankName: "",
    rs: "",
    ks: "",
    bik: "",
    bankAddress: "",
  })

  const update = (key: string, value: string) => setForm((prev) => ({ ...prev, [key]: value }))

  /** Заполнить поля формы из данных импорта */
  const handleImport = (data: Record<string, unknown>) => {
    if (data.name) update("fullName", String(data.name))
    if (data.inn) update("inn", String(data.inn))
    if (data.ogrn) update("ogrn", String(data.ogrn))
    if (data.address) update("legalAddress", String(data.address))
    if (data.phone) update("phone", String(data.phone))
    toast.success("Поля формы заполнены из импорта")
  }

  return (
    <div className="space-y-6">
      <div>
        <Label className="text-sm font-semibold mb-2 block">Тип контрагента</Label>
        <Tabs value={type} onValueChange={(v) => setType(v as CounterpartyType)}>
          <TabsList className="grid w-full max-w-md grid-cols-2">
            <TabsTrigger value="legal" className="gap-1.5">
              <Building2 className="h-3.5 w-3.5" />
              Юр. лицо
            </TabsTrigger>
            <TabsTrigger value="ip" className="gap-1.5">
              <User className="h-3.5 w-3.5" />
              ИП
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      <Separator />

      {type === "ip" && (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Данные ИП</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <Label>ФИО</Label>
              <Input placeholder="Иванов Иван Иванович" value={form.fullName} onChange={(e) => update("fullName", e.target.value)} />
            </div>
            <div className="md:col-span-2">
              <Label>Адрес регистрации</Label>
              <Input placeholder="г. Москва, ул. Примерная, д. 1" value={form.legalAddress} onChange={(e) => update("legalAddress", e.target.value)} />
            </div>
            <div>
              <Label>ИНН</Label>
              <Input placeholder="123456789012" value={form.inn} onChange={(e) => update("inn", e.target.value)} />
            </div>
            <div>
              <Label>ОГРНИП</Label>
              <Input placeholder="304123456789012" value={form.ogrn} onChange={(e) => update("ogrn", e.target.value)} />
            </div>
          </div>
          <Separator />
        </div>
      )}

      {type === "legal" && (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Реквизиты организации</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <Label>Полное наименование</Label>
              <Input placeholder="ООО «Название»" value={form.fullName} onChange={(e) => update("fullName", e.target.value)} />
            </div>
            <div>
              <Label>ИНН</Label>
              <Input placeholder="7712345678" value={form.inn} onChange={(e) => update("inn", e.target.value)} />
            </div>
            <div>
              <Label>ОГРН</Label>
              <Input placeholder="1027700123456" value={form.ogrn} onChange={(e) => update("ogrn", e.target.value)} />
            </div>
            <div className="md:col-span-2">
              <Label>Юридический адрес</Label>
              <Input placeholder="г. Москва, ул. Примерная, д. 1" value={form.legalAddress} onChange={(e) => update("legalAddress", e.target.value)} />
            </div>
          </div>
          <Separator />
        </div>
      )}

      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Контакты</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label>Телефон</Label>
            <Input placeholder="+7 (999) 123-45-67" value={form.phone} onChange={(e) => update("phone", e.target.value)} />
          </div>
          <div>
            <Label>Email</Label>
            <Input placeholder="info@company.ru" value={form.email} onChange={(e) => update("email", e.target.value)} />
          </div>
        </div>
      </div>

      <Separator />

      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Импорт данных</h3>
        <SmartImport
          hint="Импорт реквизитов контрагента из файла"
          apiEndpoint="/api/v1/organizations/import-word"
          onImported={handleImport}
        />
      </div>

      <Separator />

      {/* Кнопка создания ОПО */}
      {initialData && onCreateOpo && (
        <>
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Объекты ОПО</h3>
            <p className="text-xs text-muted-foreground">
              Создать опасный производственный объект для этой организации
            </p>
            <Button variant="outline" size="sm" className="gap-2" onClick={onCreateOpo}>
              <Building2 className="h-4 w-4" />
              Создать ОПО
            </Button>
          </div>
          <Separator />
        </>
      )}

      <div className="flex justify-end gap-3">
        <Button variant="outline" onClick={onCancel}>Отмена</Button>
        <Button onClick={() => onSave({ name: form.fullName, type, inn: form.inn, ogrn: form.ogrn, address: form.legalAddress, phone: form.phone, email: form.email })}>
          Сохранить
        </Button>
      </div>
    </div>
  )
}

export function ClientsPage() {
  const [clients, setClients] = useState<Client[]>([])
  const [search, setSearch] = useState("")
  const [open, setOpen] = useState(false)
  const [editingClient, setEditingClient] = useState<Client | undefined>(undefined)
  const [loading, setLoading] = useState(true)
  const { openOpoForOrganization } = useNavStore()

  const fetchClients = useCallback(async () => {
    try {
      setLoading(true)
      const data = await apiRequest<unknown[]>("/api/v1/organizations/")
      const mapped: Client[] = data.map((o: any) => ({
        id: o.id,
        name: o.name,
        type: "legal" as CounterpartyType,
        inn: o.inn || "",
        ogrn: o.ogrn || "",
        address: o.address || "",
        phone: o.phone || "",
        email: o.email || "",
      }))
      setClients(mapped)
    } catch (err: any) {
      toast.error("Ошибка загрузки организаций", { description: err.message })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchClients() }, [fetchClients])

  const openCard = (client: Client) => {
    setEditingClient(client)
    setOpen(true)
  }

  const filtered = clients.filter((c) =>
    c.name.toLowerCase().includes(search.toLowerCase()) ||
    c.inn.includes(search)
  )

  const handleSave = async (data: Partial<Client>) => {
    try {
      if (editingClient) {
        await apiRequest(`/api/v1/organizations/${editingClient.id}`, {
          method: "PUT",
          body: JSON.stringify({ name: data.name, inn: data.inn, ogrn: data.ogrn, address: data.address, phone: data.phone, email: data.email }),
        })
        toast.success("Организация обновлена")
      } else {
        await apiRequest("/api/v1/organizations/", {
          method: "POST",
          body: JSON.stringify({ name: data.name, inn: data.inn || "", ogrn: data.ogrn, address: data.address, phone: data.phone, email: data.email }),
        })
        toast.success("Организация создана")
      }
      await fetchClients()
    } catch (err: any) {
      toast.error("Ошибка сохранения", { description: err.message })
    }
    setOpen(false)
    setEditingClient(undefined)
  }

  const handleDelete = async (client: Client) => {
    try {
      await apiRequest(`/api/v1/organizations/${client.id}`, { method: "DELETE" })
      toast.success("Организация удалена", { description: client.name })
      await fetchClients()
    } catch (err: any) {
      toast.error("Ошибка удаления", { description: err.message })
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Организации</h1>
          <p className="text-muted-foreground text-sm mt-1">Единый справочник организаций</p>
        </div>
        <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) setEditingClient(undefined) }}>
          <DialogTrigger asChild>
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              Добавить
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{editingClient ? "Редактировать" : "Новая организация"}</DialogTitle>
            </DialogHeader>
            <ClientForm
              initialData={editingClient}
              onSave={handleSave}
              onCancel={() => { setOpen(false); setEditingClient(undefined) }}
              onCreateOpo={editingClient ? () => {
                setOpen(false);
                setEditingClient(undefined);
                openOpoForOrganization(editingClient.id);
              } : undefined}
            />
          </DialogContent>
        </Dialog>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input placeholder="Поиск по названию или ИНН..." className="pl-8" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Наименование</TableHead>
                <TableHead className="hidden sm:table-cell">Тип</TableHead>
                <TableHead className="hidden md:table-cell">ИНН</TableHead>
                <TableHead className="hidden lg:table-cell">Адрес</TableHead>
                <TableHead className="hidden md:table-cell">Телефон</TableHead>
                <TableHead className="w-[100px]">Действия</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">Загрузка...</TableCell>
                </TableRow>
              )}
              {!loading && filtered.map((client) => (
                <TableRow key={client.id} onDoubleClick={() => openCard(client)} className="cursor-pointer">
                  <TableCell className="font-medium">{client.name}</TableCell>
                  <TableCell className="hidden sm:table-cell">
                    <Badge variant={client.type === "legal" ? "default" : "secondary"}>
                      {client.type === "legal" ? "Юр. лицо" : "ИП"}
                    </Badge>
                  </TableCell>
                  <TableCell className="hidden md:table-cell font-mono text-sm">{client.inn}</TableCell>
                  <TableCell className="hidden lg:table-cell max-w-[200px] truncate text-muted-foreground">{client.address}</TableCell>
                  <TableCell className="hidden md:table-cell text-muted-foreground">{client.phone}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); openCard(client) }}>Открыть</Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-destructive" onClick={(e) => { e.stopPropagation(); handleDelete(client) }}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {!loading && filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">Организации не найдены</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
