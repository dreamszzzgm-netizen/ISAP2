"use client"

import { useState, useEffect, useCallback } from "react"
import {
  Building2, User, Pencil, Trash2, Download, Upload,
  X, Check, AlertCircle, ArrowLeft, ScrollText,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
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
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { toast } from "sonner"
import {
  isapApi,
  type Organization,
  type BankAccount,
  type OkvedCode,
  type License,
} from "@/lib/api-client"
import { useNavStore } from "@/lib/nav-store"

// ── Helpers ──

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—"
  const d = new Date(dateStr)
  return d.toLocaleDateString("ru-RU")
}

function formatFileSize(bytes: number | null): string {
  if (bytes === null || bytes === undefined) return "—"
  if (bytes < 1024) return `${bytes} Б`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`
}

// Backend: settings.max_upload_file_size_mb = 20
const MAX_LICENSE_FILE_SIZE_MB = 20
const MAX_LICENSE_FILE_SIZE_BYTES = MAX_LICENSE_FILE_SIZE_MB * 1024 * 1024
const ALLOWED_LICENSE_EXTENSIONS = [".pdf", ".jpg", ".jpeg", ".png"] as const
const ALLOWED_LICENSE_MIME_TYPES = ["application/pdf", "image/jpeg", "image/png"]

// ── Main Component ──

export function OrganizationPage() {
  const { organizationDetailId, setActivePage } = useNavStore()

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [org, setOrg] = useState<Organization | null>(null)
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([])
  const [okvedCodes, setOkvedCodes] = useState<OkvedCode[]>([])
  const [licenses, setLicenses] = useState<License[]>([])
  const [error, setError] = useState<string | null>(null)

  // ── Form state for requisites ──
  const [form, setForm] = useState({
    org_type: "legal" as string,
    // Общие поля
    full_name: "",
    short_name: "",
    legal_address: "",
    actual_address: "",
    postal_address: "",
    phone: "",
    phone_additional: "",
    phone_mobile: "",
    fax: "",
    email: "",
    website: "",
    inn: "",
    kpp: "",
    ogrn: "",
    ogrnip: "",
    okpo: "",
    // Руководитель (юрлицо) / ФИО (ИП)
    director_full_name: "",
    director_position: "",
    director_phone: "",
    director_email: "",
    ip_last_name: "",
    ip_first_name: "",
    ip_middle_name: "",
  })

  // ── Dialog states ──
  const [editBankOpen, setEditBankOpen] = useState(false)
  const [editOkvedOpen, setEditOkvedOpen] = useState(false)
  const [editLicenseOpen, setEditLicenseOpen] = useState(false)
  const [uploadLicenseId, setUploadLicenseId] = useState<string | null>(null)
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false)
  const [uploadingFile, setUploadingFile] = useState(false)
  const [licenseUploadFile, setLicenseUploadFile] = useState<File | null>(null)

  // ── Bank account form ──
  const [bankForm, setBankForm] = useState({
    account_number: "",
    bank_name: "",
    bank_bik: "",
    bank_corr_account: "",
    is_primary: false,
    notes: "",
  })
  const [editingBankId, setEditingBankId] = useState<string | null>(null)

  // ── OKVED form ──
  const [okvedForm, setOkvedForm] = useState({
    code: "",
    is_primary: false,
  })
  const [editingOkvedId, setEditingOkvedId] = useState<string | null>(null)

  // ── License form ──
  const [licenseForm, setLicenseForm] = useState({
    activity_type: "",
    license_number: "",
    issue_date: "",
    status: "active",
  })
  const [editingLicenseId, setEditingLicenseId] = useState<string | null>(null)

  const updateForm = (key: string, value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }))

  // ── Load data ──
  const loadOrg = useCallback(async () => {
    if (!organizationDetailId) return
    setLoading(true)
    setError(null)
    try {
      const data = await isapApi.getOrganizationDetail(organizationDetailId)
      setOrg(data)
      setBankAccounts(data.bank_accounts || [])
      setOkvedCodes(data.okved_codes || [])
      setLicenses(data.licenses || [])

      setForm({
        org_type: data.org_type || "legal",
        full_name: data.full_name || data.name || "",
        short_name: data.short_name || "",
        legal_address: data.legal_address || data.address || "",
        actual_address: data.actual_address || "",
        postal_address: data.postal_address || "",
        phone: data.phone || "",
        phone_additional: data.phone_additional || "",
        phone_mobile: data.phone_mobile || "",
        fax: data.fax || "",
        email: data.email || "",
        website: data.website || "",
        inn: data.inn || "",
        kpp: data.kpp || "",
        ogrn: data.ogrn || "",
        ogrnip: data.ogrnip || "",
        okpo: data.okpo || "",
        director_full_name: data.director_full_name || "",
        director_position: data.director_position || "",
        director_phone: data.director_phone || "",
        director_email: data.director_email || "",
        ip_last_name: data.ip_last_name || "",
        ip_first_name: data.ip_first_name || "",
        ip_middle_name: data.ip_middle_name || "",
      })
    } catch (err: any) {
      setError(err.message || "Ошибка загрузки организации")
      toast.error("Ошибка загрузки", { description: err.message })
    } finally {
      setLoading(false)
    }
  }, [organizationDetailId])

  useEffect(() => {
    if (organizationDetailId) loadOrg()
  }, [organizationDetailId, loadOrg])

  // ── Save organization ──
  const handleSaveOrg = async () => {
    if (!organizationDetailId) return
    setSaving(true)
    try {
      const payload: Record<string, unknown> = {
        org_type: form.org_type,
        name: form.full_name,
        full_name: form.full_name || null,
        short_name: form.short_name || null,
        legal_address: form.legal_address || null,
        actual_address: form.actual_address || null,
        postal_address: form.postal_address || null,
        phone: form.phone || null,
        phone_additional: form.phone_additional || null,
        phone_mobile: form.phone_mobile || null,
        fax: form.fax || null,
        email: form.email || null,
        website: form.website || null,
        inn: form.inn || "",
        kpp: form.kpp || null,
        ogrn: form.ogrn || null,
        ogrnip: form.ogrnip || null,
        okpo: form.okpo || null,
        director_full_name: form.director_full_name || null,
        director_position: form.director_position || null,
        director_phone: form.director_phone || null,
        director_email: form.director_email || null,
        ip_last_name: form.ip_last_name || null,
        ip_first_name: form.ip_first_name || null,
        ip_middle_name: form.ip_middle_name || null,
      }
      // Clean up by org_type
      if (form.org_type === "individual") {
        payload.kpp = null
        payload.ogrn = null
        payload.director_full_name = null
        payload.director_position = null
        payload.director_phone = null
        payload.director_email = null
      } else {
        payload.ogrnip = null
        payload.ip_last_name = null
        payload.ip_first_name = null
        payload.ip_middle_name = null
      }
      await isapApi.updateOrganization(organizationDetailId, payload)
      toast.success("Организация сохранена")
      await loadOrg()
    } catch (err: any) {
      toast.error("Ошибка сохранения", { description: err.message })
    } finally {
      setSaving(false)
    }
  }

  // ── Bank account CRUD ──
  const resetBankForm = () => {
    setBankForm({ account_number: "", bank_name: "", bank_bik: "", bank_corr_account: "", is_primary: false, notes: "" })
    setEditingBankId(null)
  }

  const openEditBank = (account?: BankAccount) => {
    if (account) {
      setBankForm({
        account_number: account.account_number,
        bank_name: account.bank_name || "",
        bank_bik: account.bank_bik || "",
        bank_corr_account: account.bank_corr_account || "",
        is_primary: account.is_primary,
        notes: account.notes || "",
      })
      setEditingBankId(account.id)
    } else {
      resetBankForm()
    }
    setEditBankOpen(true)
  }

  const handleSaveBank = async () => {
    if (!organizationDetailId) return
    try {
      if (editingBankId) {
        await isapApi.updateBankAccount(organizationDetailId, editingBankId, {
          account_number: bankForm.account_number,
          bank_name: bankForm.bank_name || null,
          bank_bik: bankForm.bank_bik || null,
          bank_corr_account: bankForm.bank_corr_account || null,
          is_primary: bankForm.is_primary,
          notes: bankForm.notes || null,
        })
        toast.success("Банковский счёт обновлён")
      } else {
        await isapApi.createBankAccount(organizationDetailId, {
          account_number: bankForm.account_number,
          bank_name: bankForm.bank_name || null,
          bank_bik: bankForm.bank_bik || null,
          bank_corr_account: bankForm.bank_corr_account || null,
          is_primary: bankForm.is_primary,
          notes: bankForm.notes || null,
        })
        toast.success("Банковский счёт добавлен")
      }
      setEditBankOpen(false)
      resetBankForm()
      const accounts = await isapApi.listBankAccounts(organizationDetailId)
      setBankAccounts(accounts)
    } catch (err: any) {
      if (err.message?.includes("основной")) {
        toast.error("У организации уже есть основной банковский счёт")
      } else {
        toast.error("Ошибка сохранения счёта", { description: err.message })
      }
    }
  }

  const handleDeleteBank = async (accountId: string) => {
    if (!organizationDetailId) return
    try {
      await isapApi.deleteBankAccount(organizationDetailId, accountId)
      toast.success("Банковский счёт удалён")
      const accounts = await isapApi.listBankAccounts(organizationDetailId)
      setBankAccounts(accounts)
    } catch (err: any) {
      toast.error("Ошибка удаления счёта", { description: err.message })
    }
  }

  // ── OKVED CRUD ──
  const resetOkvedForm = () => {
    setOkvedForm({ code: "", is_primary: false })
    setEditingOkvedId(null)
  }

  const openEditOkved = (code?: OkvedCode) => {
    if (code) {
      setOkvedForm({ code: code.code, is_primary: code.is_primary })
      setEditingOkvedId(code.id)
    } else {
      resetOkvedForm()
    }
    setEditOkvedOpen(true)
  }

  const handleSaveOkved = async () => {
    if (!organizationDetailId) return
    try {
      if (editingOkvedId) {
        await isapApi.updateOkvedCode(organizationDetailId, editingOkvedId, {
          code: okvedForm.code,
          is_primary: okvedForm.is_primary,
        })
        toast.success("Код ОКВЭД обновлён")
      } else {
        await isapApi.createOkvedCode(organizationDetailId, {
          code: okvedForm.code,
          is_primary: okvedForm.is_primary,
        })
        toast.success("Код ОКВЭД добавлен")
      }
      setEditOkvedOpen(false)
      resetOkvedForm()
      const codes = await isapApi.listOkvedCodes(organizationDetailId)
      setOkvedCodes(codes)
    } catch (err: any) {
      if (err.message?.includes("основной")) {
        toast.error("У организации уже есть основной код ОКВЭД")
      } else {
        toast.error("Ошибка сохранения ОКВЭД", { description: err.message })
      }
    }
  }

  const handleDeleteOkved = async (codeId: string) => {
    if (!organizationDetailId) return
    try {
      await isapApi.deleteOkvedCode(organizationDetailId, codeId)
      toast.success("Код ОКВЭД удалён")
      const codes = await isapApi.listOkvedCodes(organizationDetailId)
      setOkvedCodes(codes)
    } catch (err: any) {
      toast.error("Ошибка удаления ОКВЭД", { description: err.message })
    }
  }

  // ── License CRUD ──
  const resetLicenseForm = () => {
    setLicenseForm({ activity_type: "", license_number: "", issue_date: "", status: "active" })
    setEditingLicenseId(null)
  }

  const openEditLicense = (lic?: License) => {
    if (lic) {
      setLicenseForm({
        activity_type: lic.activity_type,
        license_number: lic.license_number,
        issue_date: lic.issue_date || "",
        status: lic.status,
      })
      setEditingLicenseId(lic.id)
    } else {
      resetLicenseForm()
    }
    setEditLicenseOpen(true)
  }

  const handleSaveLicense = async () => {
    if (!organizationDetailId) return
    try {
      const payload: Record<string, unknown> = {
        activity_type: licenseForm.activity_type,
        license_number: licenseForm.license_number,
        status: licenseForm.status,
      }
      if (licenseForm.issue_date) {
        payload.issue_date = licenseForm.issue_date
      }
      if (editingLicenseId) {
        await isapApi.updateLicense(organizationDetailId, editingLicenseId, payload)
        toast.success("Лицензия обновлена")
      } else {
        await isapApi.createLicense(organizationDetailId, payload)
        toast.success("Лицензия добавлена")
      }
      setEditLicenseOpen(false)
      resetLicenseForm()
      const list = await isapApi.listLicenses(organizationDetailId)
      setLicenses(list)
    } catch (err: any) {
      toast.error("Ошибка сохранения лицензии", { description: err.message })
    }
  }

  const handleDeleteLicense = async (licenseId: string) => {
    if (!organizationDetailId) return
    try {
      await isapApi.deleteLicense(organizationDetailId, licenseId)
      toast.success("Лицензия удалена")
      const list = await isapApi.listLicenses(organizationDetailId)
      setLicenses(list)
    } catch (err: any) {
      toast.error("Ошибка удаления лицензии", { description: err.message })
    }
  }

  // ── License file upload ──
  const openUploadFile = (licenseId: string) => {
    setUploadLicenseId(licenseId)
    setLicenseUploadFile(null)
    setUploadDialogOpen(true)
  }

  const validateLicenseFile = (file: File): string | null => {
    const ext = "." + file.name.split(".").pop()?.toLowerCase()
    const allowedExts = ALLOWED_LICENSE_EXTENSIONS as readonly string[]
    if (!allowedExts.includes(ext)) {
      return `Недопустимый формат файла. Разрешены: ${ALLOWED_LICENSE_EXTENSIONS.map(e => e.toUpperCase()).join(", ")}`
    }
    if (file.size > MAX_LICENSE_FILE_SIZE_BYTES) {
      return `Размер файла не должен превышать ${MAX_LICENSE_FILE_SIZE_MB} МБ`
    }
    return null
  }

  const handleUploadFile = async () => {
    if (!organizationDetailId || !uploadLicenseId || !licenseUploadFile) return

    const validationError = validateLicenseFile(licenseUploadFile)
    if (validationError) {
      toast.error(validationError)
      return
    }

    setUploadingFile(true)
    try {
      await isapApi.uploadLicenseFile(organizationDetailId, uploadLicenseId, licenseUploadFile)
      toast.success("Электронная копия лицензии загружена")
      setUploadDialogOpen(false)
      setLicenseUploadFile(null)
      const list = await isapApi.listLicenses(organizationDetailId)
      setLicenses(list)
    } catch (err: any) {
      toast.error("Ошибка загрузки файла", { description: err.message })
    } finally {
      setUploadingFile(false)
    }
  }

  const handleDeleteLicenseFile = async (licenseId: string) => {
    if (!organizationDetailId) return
    try {
      await isapApi.deleteLicenseFile(organizationDetailId, licenseId)
      toast.success("Электронная копия лицензии удалена")
      const list = await isapApi.listLicenses(organizationDetailId)
      setLicenses(list)
    } catch (err: any) {
      toast.error("Ошибка удаления файла", { description: err.message })
    }
  }

  const handleDownloadLicense = (licenseId: string) => {
    if (!organizationDetailId) return
    const url = isapApi.getLicenseDownloadUrl(organizationDetailId, licenseId)
    window.open(url, "_blank")
  }

  // ── Loading state ──
  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => setActivePage("clients")}><ArrowLeft className="h-4 w-4" /></Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Карточка организации</h1>
            <p className="text-muted-foreground text-sm mt-1">Загрузка...</p>
          </div>
        </div>
        <div className="flex items-center justify-center py-20">
          <p className="text-muted-foreground">Загрузка данных организации...</p>
        </div>
      </div>
    )
  }

  if (error || !org) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => setActivePage("clients")}><ArrowLeft className="h-4 w-4" /></Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Карточка организации</h1>
          </div>
        </div>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error || "Организация не найдена"}</AlertDescription>
        </Alert>
      </div>
    )
  }

  const isIndividual = form.org_type === "individual"

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => setActivePage("clients")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{org.name}</h1>
            <p className="text-muted-foreground text-sm mt-1">
              {isIndividual ? "Индивидуальный предприниматель" : "Юридическое лицо"} · ИНН {org.inn}
            </p>
          </div>
        </div>
        <Button size="sm" className="gap-2" onClick={handleSaveOrg} disabled={saving}>
          <Check className="h-4 w-4" />
          {saving ? "Сохранение..." : "Сохранить"}
        </Button>
      </div>

      <Tabs defaultValue="requisites" className="space-y-6">
        <TabsList>
          <TabsTrigger value="requisites" className="gap-2">
            <Building2 className="h-4 w-4" />
            Реквизиты
          </TabsTrigger>
          <TabsTrigger value="licenses" className="gap-2">
            <ScrollText className="h-4 w-4" />
            Лицензии
          </TabsTrigger>
        </TabsList>

        {/* ═══════════════════════════════════════════════════════════════════
           TAB 1: РЕКВИЗИТЫ
           ═══════════════════════════════════════════════════════════════ */}
        <TabsContent value="requisites" className="space-y-6">
          {/* Type selector */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Тип организации</CardTitle>
            </CardHeader>
            <CardContent>
              <Tabs value={form.org_type} onValueChange={(v) => updateForm("org_type", v)}>
                <TabsList className="grid w-full max-w-md grid-cols-2">
                  <TabsTrigger value="legal" className="gap-1.5">
                    <Building2 className="h-3.5 w-3.5" />
                    Юридическое лицо
                  </TabsTrigger>
                  <TabsTrigger value="individual" className="gap-1.5">
                    <User className="h-3.5 w-3.5" />
                    Индивидуальный предприниматель
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            </CardContent>
          </Card>

          {/* ── Full & short name (both types) ── */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                {isIndividual ? "Наименование ИП" : "Наименование организации"}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 gap-4">
                <div>
                  <Label>Полное наименование</Label>
                  <Input
                    value={form.full_name}
                    onChange={(e) => updateForm("full_name", e.target.value)}
                    placeholder={isIndividual ? "Иванов Иван Иванович" : "Общество с ограниченной ответственностью «...»"}
                  />
                </div>
                <div>
                  <Label>Сокращённое наименование</Label>
                  <Input
                    value={form.short_name}
                    onChange={(e) => updateForm("short_name", e.target.value)}
                    placeholder={isIndividual ? "ИП Иванов И.И." : "ООО «...»"}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* ── Tax / registration info ── */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Регистрационные данные</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {isIndividual ? (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <Label>Фамилия</Label>
                    <Input value={form.ip_last_name} onChange={(e) => updateForm("ip_last_name", e.target.value)} placeholder="Иванов" />
                  </div>
                  <div>
                    <Label>Имя</Label>
                    <Input value={form.ip_first_name} onChange={(e) => updateForm("ip_first_name", e.target.value)} placeholder="Иван" />
                  </div>
                  <div>
                    <Label>Отчество</Label>
                    <Input value={form.ip_middle_name} onChange={(e) => updateForm("ip_middle_name", e.target.value)} placeholder="Иванович" />
                  </div>
                  <div>
                    <Label>ИНН</Label>
                    <Input value={form.inn} onChange={(e) => updateForm("inn", e.target.value)} placeholder="123456789012" />
                  </div>
                  <div>
                    <Label>ОГРНИП</Label>
                    <Input value={form.ogrnip} onChange={(e) => updateForm("ogrnip", e.target.value)} placeholder="304123456789012" />
                  </div>
                  <div>
                    <Label>ОКПО</Label>
                    <Input value={form.okpo} onChange={(e) => updateForm("okpo", e.target.value)} placeholder="12345678" />
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <Label>ИНН</Label>
                    <Input value={form.inn} onChange={(e) => updateForm("inn", e.target.value)} placeholder="7712345678" />
                  </div>
                  <div>
                    <Label>КПП</Label>
                    <Input value={form.kpp} onChange={(e) => updateForm("kpp", e.target.value)} placeholder="771234567" />
                  </div>
                  <div>
                    <Label>ОГРН</Label>
                    <Input value={form.ogrn} onChange={(e) => updateForm("ogrn", e.target.value)} placeholder="1027700123456" />
                  </div>
                  <div>
                    <Label>ОКПО</Label>
                    <Input value={form.okpo} onChange={(e) => updateForm("okpo", e.target.value)} placeholder="12345678" />
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* ── Director (legal only) ── */}
          {!isIndividual && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Руководитель</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label>ФИО руководителя</Label>
                    <Input value={form.director_full_name} onChange={(e) => updateForm("director_full_name", e.target.value)} placeholder="Иванов Иван Иванович" />
                  </div>
                  <div>
                    <Label>Должность</Label>
                    <Input value={form.director_position} onChange={(e) => updateForm("director_position", e.target.value)} placeholder="Генеральный директор" />
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label>Телефон руководителя</Label>
                    <Input value={form.director_phone} onChange={(e) => updateForm("director_phone", e.target.value)} placeholder="+7 (495) 123-45-67" />
                  </div>
                  <div>
                    <Label>Email руководителя</Label>
                    <Input value={form.director_email} onChange={(e) => updateForm("director_email", e.target.value)} placeholder="director@company.ru" />
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* ── Addresses ── */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Адреса</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 gap-4">
                <div>
                  <Label>Юридический / Регистрационный адрес</Label>
                  <Input value={form.legal_address} onChange={(e) => updateForm("legal_address", e.target.value)} placeholder="г. Москва, ул. Примерная, д. 1" />
                </div>
                <div>
                  <Label>Фактический адрес</Label>
                  <Input value={form.actual_address} onChange={(e) => updateForm("actual_address", e.target.value)} placeholder="г. Москва, ул. Фактическая, д. 2" />
                </div>
                <div>
                  <Label>Почтовый адрес</Label>
                  <Input value={form.postal_address} onChange={(e) => updateForm("postal_address", e.target.value)} placeholder="123456, г. Москва, ул. Примерная, д. 1" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* ── Contacts ── */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Контакты</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <Label>Основной телефон</Label>
                  <Input value={form.phone} onChange={(e) => updateForm("phone", e.target.value)} placeholder="+7 (495) 123-45-67" />
                </div>
                <div>
                  <Label>Дополнительный телефон</Label>
                  <Input value={form.phone_additional} onChange={(e) => updateForm("phone_additional", e.target.value)} placeholder="+7 (495) 123-45-68" />
                </div>
                <div>
                  <Label>Мобильный телефон</Label>
                  <Input value={form.phone_mobile} onChange={(e) => updateForm("phone_mobile", e.target.value)} placeholder="+7 (999) 123-45-67" />
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <Label>Факс</Label>
                  <Input value={form.fax} onChange={(e) => updateForm("fax", e.target.value)} placeholder="+7 (495) 123-45-69" />
                </div>
                <div>
                  <Label>Email</Label>
                  <Input value={form.email} onChange={(e) => updateForm("email", e.target.value)} placeholder="info@company.ru" />
                </div>
                <div>
                  <Label>Сайт</Label>
                  <Input value={form.website} onChange={(e) => updateForm("website", e.target.value)} placeholder="www.company.ru" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* ── Bank accounts ── */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">Банковские счета</CardTitle>
              <Dialog open={editBankOpen} onOpenChange={(v) => { setEditBankOpen(v); if (!v) resetBankForm() }}>
                <DialogTrigger asChild>
                  <Button variant="outline" size="sm" className="gap-2" onClick={() => openEditBank()}>
                    <Building2 className="h-4 w-4" />
                    Добавить счёт
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-lg">
                  <DialogHeader>
                    <DialogTitle>{editingBankId ? "Редактировать счёт" : "Новый банковский счёт"}</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4 py-2">
                    <div>
                      <Label>Наименование банка</Label>
                      <Input value={bankForm.bank_name} onChange={(e) => setBankForm(p => ({ ...p, bank_name: e.target.value }))} placeholder="ПАО Сбербанк" />
                    </div>
                    <div>
                      <Label>Расчётный счёт</Label>
                      <Input value={bankForm.account_number} onChange={(e) => setBankForm(p => ({ ...p, account_number: e.target.value }))} placeholder="40702810123450000001" />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label>БИК</Label>
                        <Input value={bankForm.bank_bik} onChange={(e) => setBankForm(p => ({ ...p, bank_bik: e.target.value }))} placeholder="044525225" />
                      </div>
                      <div>
                        <Label>Корреспондентский счёт</Label>
                        <Input value={bankForm.bank_corr_account} onChange={(e) => setBankForm(p => ({ ...p, bank_corr_account: e.target.value }))} placeholder="30101810400000000225" />
                      </div>
                    </div>
                    <div>
                      <Label>Наименование получателя</Label>
                      <Input value={bankForm.notes} onChange={(e) => setBankForm(p => ({ ...p, notes: e.target.value }))} placeholder="ООО «...» (или ФИО)" />
                    </div>
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        className="h-4 w-4"
                        checked={bankForm.is_primary}
                        onChange={(e) => setBankForm(p => ({ ...p, is_primary: e.target.checked }))}
                      />
                      <Label className="cursor-pointer text-sm">Основной счёт</Label>
                    </div>
                    <div className="flex justify-end gap-3 pt-2">
                      <Button variant="outline" onClick={() => { setEditBankOpen(false); resetBankForm() }}>Отмена</Button>
                      <Button onClick={handleSaveBank}>Сохранить</Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Наименование банка</TableHead>
                    <TableHead>Расчётный счёт</TableHead>
                    <TableHead className="hidden md:table-cell">БИК</TableHead>
                    <TableHead className="hidden md:table-cell">Корр. счёт</TableHead>
                    <TableHead>Статус</TableHead>
                    <TableHead className="w-[120px]">Действия</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {bankAccounts.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center py-6 text-muted-foreground">
                        Нет банковских счетов
                      </TableCell>
                    </TableRow>
                  )}
                  {bankAccounts.map((acc) => (
                    <TableRow key={acc.id}>
                      <TableCell className="max-w-[150px] truncate">{acc.bank_name || "—"}</TableCell>
                      <TableCell className="font-mono text-sm">{acc.account_number}</TableCell>
                      <TableCell className="hidden md:table-cell font-mono text-sm">{acc.bank_bik || "—"}</TableCell>
                      <TableCell className="hidden md:table-cell font-mono text-sm">{acc.bank_corr_account || "—"}</TableCell>
                      <TableCell>
                        {acc.is_primary ? <Badge variant="default">Основной</Badge> : <Badge variant="outline">Дополнительный</Badge>}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => openEditBank(acc)}>
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-destructive" onClick={() => handleDeleteBank(acc.id)}>
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* ── OKVED codes ── */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">Коды ОКВЭД</CardTitle>
              <Dialog open={editOkvedOpen} onOpenChange={(v) => { setEditOkvedOpen(v); if (!v) resetOkvedForm() }}>
                <DialogTrigger asChild>
                  <Button variant="outline" size="sm" className="gap-2" onClick={() => openEditOkved()}>
                    <Building2 className="h-4 w-4" />
                    Добавить ОКВЭД
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-sm">
                  <DialogHeader>
                    <DialogTitle>{editingOkvedId ? "Редактировать ОКВЭД" : "Новый код ОКВЭД"}</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4 py-2">
                    <div>
                      <Label>Код</Label>
                      <Input value={okvedForm.code} onChange={(e) => setOkvedForm(p => ({ ...p, code: e.target.value }))} placeholder="35.22" />
                    </div>
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        className="h-4 w-4"
                        checked={okvedForm.is_primary}
                        onChange={(e) => setOkvedForm(p => ({ ...p, is_primary: e.target.checked }))}
                      />
                      <Label className="cursor-pointer text-sm">Основной вид деятельности</Label>
                    </div>
                    <div className="flex justify-end gap-3 pt-2">
                      <Button variant="outline" onClick={() => { setEditOkvedOpen(false); resetOkvedForm() }}>Отмена</Button>
                      <Button onClick={handleSaveOkved}>Сохранить</Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Код</TableHead>
                    <TableHead>Статус</TableHead>
                    <TableHead className="w-[120px]">Действия</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {okvedCodes.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={3} className="text-center py-6 text-muted-foreground">
                        Нет кодов ОКВЭД
                      </TableCell>
                    </TableRow>
                  )}
                  {okvedCodes.map((code) => (
                    <TableRow key={code.id}>
                      <TableCell className="font-mono text-sm">{code.code}</TableCell>
                      <TableCell>
                        {code.is_primary ? <Badge variant="default">Основной</Badge> : <Badge variant="outline">Дополнительный</Badge>}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => openEditOkved(code)}>
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-destructive" onClick={() => handleDeleteOkved(code.id)}>
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ═══════════════════════════════════════════════════════════════════
           TAB 2: ЛИЦЕНЗИИ
           ═══════════════════════════════════════════════════════════════ */}
        <TabsContent value="licenses" className="space-y-6">
          <div className="flex justify-end">
            <Dialog open={editLicenseOpen} onOpenChange={(v) => { setEditLicenseOpen(v); if (!v) resetLicenseForm() }}>
              <DialogTrigger asChild>
                <Button className="gap-2" onClick={() => openEditLicense()}>
                  <Building2 className="h-4 w-4" />
                  Добавить лицензию
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-lg">
                <DialogHeader>
                  <DialogTitle>{editingLicenseId ? "Редактировать лицензию" : "Новая лицензия"}</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-2">
                  <div>
                    <Label>Вид лицензируемой деятельности</Label>
                    <Input value={licenseForm.activity_type} onChange={(e) => setLicenseForm(p => ({ ...p, activity_type: e.target.value }))} placeholder="Эксплуатация взрывопожароопасных производственных объектов" />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Номер лицензии</Label>
                      <Input value={licenseForm.license_number} onChange={(e) => setLicenseForm(p => ({ ...p, license_number: e.target.value }))} placeholder="Л014-00101-77/123456" />
                    </div>
                    <div>
                      <Label>Дата выдачи</Label>
                      <Input type="date" value={licenseForm.issue_date} onChange={(e) => setLicenseForm(p => ({ ...p, issue_date: e.target.value }))} />
                    </div>
                  </div>
                  <div>
                    <Label>Статус</Label>
                    <Select value={licenseForm.status} onValueChange={(v) => setLicenseForm(p => ({ ...p, status: v }))}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="active">Действующая</SelectItem>
                        <SelectItem value="suspended">Приостановлена</SelectItem>
                        <SelectItem value="expired">Истекла</SelectItem>
                        <SelectItem value="revoked">Аннулирована</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex justify-end gap-3 pt-2">
                    <Button variant="outline" onClick={() => { setEditLicenseOpen(false); resetLicenseForm() }}>Отмена</Button>
                    <Button onClick={handleSaveLicense}>Сохранить</Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          </div>

          {/* License file upload dialog */}
          <Dialog open={uploadDialogOpen} onOpenChange={(v) => { setUploadDialogOpen(v); if (!v) setLicenseUploadFile(null) }}>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>Загрузка электронной копии лицензии</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-2">
                <div>
                  <Label>Файл (PDF, JPEG, PNG, до {MAX_LICENSE_FILE_SIZE_MB} МБ)</Label>
                  <Input
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png"
                    onChange={(e) => {
                      const f = e.target.files?.[0] || null
                      setLicenseUploadFile(f)
                      if (f) {
                        const err = validateLicenseFile(f)
                        if (err) toast.error(err)
                      }
                    }}
                  />
                </div>
                {licenseUploadFile && (
                  <p className="text-sm text-muted-foreground">
                    Выбран: {licenseUploadFile.name} ({formatFileSize(licenseUploadFile.size)})
                  </p>
                )}
                <Alert>
                  <AlertDescription>
                    После загрузки файл будет доступен для скачивания. Предыдущий файл (если был) будет заменён.
                    Допустимые форматы: PDF, JPEG, PNG. Максимальный размер: {MAX_LICENSE_FILE_SIZE_MB} МБ.
                  </AlertDescription>
                </Alert>
                <div className="flex justify-end gap-3 pt-2">
                  <Button variant="outline" onClick={() => { setUploadDialogOpen(false); setLicenseUploadFile(null) }}>Отмена</Button>
                  <Button onClick={handleUploadFile} disabled={!licenseUploadFile || uploadingFile}>
                    {uploadingFile ? "Загрузка..." : "Загрузить"}
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>

          {/* Licenses table */}
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Вид деятельности</TableHead>
                    <TableHead>Номер</TableHead>
                    <TableHead className="hidden md:table-cell">Дата выдачи</TableHead>
                    <TableHead>Статус</TableHead>
                    <TableHead className="hidden lg:table-cell">Электронная копия</TableHead>
                    <TableHead className="w-[200px]">Действия</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {licenses.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center py-6 text-muted-foreground">
                        Нет лицензий
                      </TableCell>
                    </TableRow>
                  )}
                  {licenses.map((lic) => (
                    <TableRow key={lic.id}>
                      <TableCell className="max-w-[200px] truncate">{lic.activity_type}</TableCell>
                      <TableCell className="font-mono text-sm">{lic.license_number}</TableCell>
                      <TableCell className="hidden md:table-cell text-muted-foreground">{formatDate(lic.issue_date)}</TableCell>
                      <TableCell>
                        <Badge variant={
                          lic.status === "active" ? "default" :
                          lic.status === "suspended" ? "secondary" :
                          "destructive"
                        }>
                          {lic.status === "active" ? "Действует" :
                           lic.status === "suspended" ? "Приостановлена" :
                           lic.status === "expired" ? "Истекла" :
                           lic.status === "revoked" ? "Аннулирована" : lic.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="hidden lg:table-cell">
                        {lic.has_file ? (
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className="text-xs">
                              {lic.file_name ? lic.file_name.split(".").pop()?.toUpperCase() : "ФАЙЛ"}
                            </Badge>
                            <span className="text-xs text-muted-foreground">{formatFileSize(lic.file_size)}</span>
                          </div>
                        ) : (
                          <span className="text-muted-foreground text-sm">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1 flex-wrap">
                          <Button variant="ghost" size="sm" className="h-8 px-2" onClick={() => openEditLicense(lic)} title="Редактировать">
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          {lic.has_file && (
                            <Button variant="ghost" size="sm" className="h-8 px-2" onClick={() => handleDownloadLicense(lic.id)} title="Скачать">
                              <Download className="h-3.5 w-3.5" />
                            </Button>
                          )}
                          <Button variant="ghost" size="sm" className="h-8 px-2" onClick={() => openUploadFile(lic.id)} title="Загрузить электронную копию">
                            <Upload className="h-3.5 w-3.5" />
                          </Button>
                          {lic.has_file && (
                            <Button variant="ghost" size="sm" className="h-8 px-2 text-muted-foreground hover:text-destructive" onClick={() => handleDeleteLicenseFile(lic.id)} title="Удалить электронную копию">
                              <X className="h-3.5 w-3.5" />
                            </Button>
                          )}
                          <Button variant="ghost" size="sm" className="h-8 px-2 text-muted-foreground hover:text-destructive" onClick={() => handleDeleteLicense(lic.id)} title="Удалить лицензию">
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
