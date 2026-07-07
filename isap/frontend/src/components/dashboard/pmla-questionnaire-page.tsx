"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  FileJson,
  FileUp,
  Loader2,
  Plus,
  RefreshCcw,
  Trash2,
  WandSparkles,
} from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { isapApi, type ImportPreviewResult, type PmlaGenerationResult, type PmlaQuestionnaire } from "@/lib/api-client"

type AnyRecord = Record<string, any>

type FacilityOption = {
  id: string
  name: string
  organization?: string
  regNumber?: string
  hazardClass?: string
  facilityType?: string
  address?: string
}

const EMPTY_DATA: AnyRecord = {
  incident_history: { has_incidents: null, period: "за период эксплуатации", items: [] },
  selected_scenarios: [],
  custom_scenarios: [],
  selected_pasf_id: "",
  pasf_manual: {},
  selected_emergency_service_ids: [],
  selected_emergency_services: [],
  organization_resources: { actual_items: [], recommended_items: [], user_notes: "" },
  notification_scheme: {},
  financial_reserve: {},
  insurance: {},
  training: {},
  attachments_checklist: [],
}

const SCENARIOS = [
  "утечка опасного вещества",
  "разгерметизация оборудования",
  "загазованность помещения",
  "воспламенение газовоздушной смеси",
  "взрыв",
  "пожар",
  "отказ автоматики",
  "отключение электроэнергии",
]

const ATTACHMENTS = [
  "схема расположения ОПО",
  "ситуационный план",
  "схема оповещения",
  "схема эвакуации",
  "схема отключающих устройств",
  "перечень сил и средств",
  "договор с ПАСФ",
  "свидетельство ПАСФ",
  "приказ о финансовом резерве",
  "страховой полис",
]

const SERVICE_TYPES = ["fire", "medical", "police", "gas", "edds"]

function toFacility(row: AnyRecord): FacilityOption {
  return {
    id: String(row.id || row.uuid || ""),
    name: String(row.name || row.facility_name || row.title || "ОПО без названия"),
    organization: String(row.organization_name || row.organization?.name || row.orgName || ""),
    regNumber: String(row.reg_number || row.registration_number || row.regNumber || ""),
    hazardClass: String(row.hazard_class || row.dangerClass || ""),
    facilityType: String(row.facility_type || row.object_type || ""),
    address: String(row.address || row.actual_address || ""),
  }
}

function dataOf(questionnaire: PmlaQuestionnaire | null): AnyRecord {
  return { ...EMPTY_DATA, ...(questionnaire?.data || {}) }
}

function getList(value: unknown): AnyRecord[] {
  return Array.isArray(value) ? value as AnyRecord[] : []
}

function getStrings(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String) : []
}

function pretty(value: unknown) {
  return JSON.stringify(value ?? {}, null, 2)
}

function SectionActions({ saving, onSave }: { saving: boolean; onSave: () => void }) {
  return (
    <div className="flex justify-end pt-4">
      <Button onClick={onSave} disabled={saving} className="gap-2">
        {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
        Сохранить блок
      </Button>
    </div>
  )
}

export function PmlaQuestionnairePage() {
  const [facilities, setFacilities] = useState<FacilityOption[]>([])
  const [facilityId, setFacilityId] = useState("")
  const [questionnaire, setQuestionnaire] = useState<PmlaQuestionnaire | null>(null)
  const [draft, setDraft] = useState<AnyRecord>(EMPTY_DATA)
  const [contextPreview, setContextPreview] = useState<AnyRecord | null>(null)
  const [generation, setGeneration] = useState<PmlaGenerationResult | null>(null)
  const [importPreview, setImportPreview] = useState<ImportPreviewResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState("")
  const [message, setMessage] = useState("")
  const fileRef = useRef<HTMLInputElement>(null)

  const selectedFacility = useMemo(
    () => facilities.find((facility) => facility.id === facilityId),
    [facilities, facilityId],
  )

  const qid = questionnaire?.id || ""
  const incident = draft.incident_history || EMPTY_DATA.incident_history
  const resources = draft.organization_resources || EMPTY_DATA.organization_resources

  const loadFacilities = async () => {
    setError("")
    setLoading(true)
    try {
      const rows = await isapApi.facilities()
      const mapped = Array.isArray(rows) ? rows.map((row) => toFacility(row as AnyRecord)).filter((row) => row.id) : []
      setFacilities(mapped)
      if (!facilityId && mapped[0]) setFacilityId(mapped[0].id)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить ОПО")
    } finally {
      setLoading(false)
    }
  }

  const openQuestionnaire = async (create = false) => {
    if (!facilityId) return
    setError("")
    setMessage("")
    setLoading(true)
    try {
      const item = create
        ? await isapApi.createPmlaQuestionnaire(facilityId)
        : await isapApi.getPmlaQuestionnaireByFacility(facilityId)
      setQuestionnaire(item)
      setDraft(dataOf(item))
      setContextPreview(null)
      setGeneration(null)
      setMessage(create ? "Анкета создана" : "Анкета открыта")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось открыть анкету")
    } finally {
      setLoading(false)
    }
  }

  const saveBlock = async (block: string, data: unknown) => {
    if (!qid) {
      setError("Сначала откройте или создайте анкету")
      return
    }
    setSaving(true)
    setError("")
    try {
      const item = await isapApi.updatePmlaQuestionnaireBlock(qid, block, data)
      setQuestionnaire(item)
      setDraft(dataOf(item))
      setMessage(`Блок ${block} сохранен`)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сохранить блок")
    } finally {
      setSaving(false)
    }
  }

  const updateDraft = (key: string, value: unknown) => setDraft((prev) => ({ ...prev, [key]: value }))

  const updateNested = (block: string, key: string, value: unknown) => {
    setDraft((prev) => ({ ...prev, [block]: { ...(prev[block] || {}), [key]: value } }))
  }

  const addIncident = () => {
    const items = getList(incident.items)
    updateDraft("incident_history", {
      ...incident,
      has_incidents: true,
      items: [...items, { date: "", event_type: "incident", place: "", description: "", reason: "", consequences: "", measures: "", source_document: "" }],
    })
  }

  const updateIncident = (index: number, key: string, value: string) => {
    const items = getList(incident.items)
    items[index] = { ...items[index], [key]: value }
    updateDraft("incident_history", { ...incident, items })
  }

  const addCustomScenario = async () => {
    if (!qid) {
      setError("Сначала откройте анкету")
      return
    }
    const scenario = { title: "Новый сценарий", description: "", source_equipment: "", substance: "", consequences: "" }
    setSaving(true)
    try {
      const item = await isapApi.addCustomScenario(qid, scenario)
      setQuestionnaire(item)
      setDraft(dataOf(item))
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось добавить сценарий")
    } finally {
      setSaving(false)
    }
  }

  const deleteCustomScenario = async (index: number) => {
    if (!qid) return
    setSaving(true)
    try {
      const item = await isapApi.deleteCustomScenario(qid, index)
      setQuestionnaire(item)
      setDraft(dataOf(item))
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось удалить сценарий")
    } finally {
      setSaving(false)
    }
  }

  const updateCustomScenario = (index: number, key: string, value: string) => {
    const scenarios = getList(draft.custom_scenarios)
    scenarios[index] = { ...scenarios[index], [key]: value }
    updateDraft("custom_scenarios", scenarios)
  }

  const addRow = (block: string, key: string, row: AnyRecord) => {
    const base = draft[block] || {}
    updateDraft(block, { ...base, [key]: [...getList(base[key]), row] })
  }

  const updateRow = (block: string, key: string, index: number, field: string, value: string) => {
    const base = draft[block] || {}
    const rows = getList(base[key])
    rows[index] = { ...rows[index], [field]: value }
    updateDraft(block, { ...base, [key]: rows })
  }

  const removeRow = (block: string, key: string, index: number) => {
    const base = draft[block] || {}
    updateDraft(block, { ...base, [key]: getList(base[key]).filter((_, i) => i !== index) })
  }

  const buildContext = async () => {
    if (!qid) return
    setLoading(true)
    setError("")
    try {
      setContextPreview(await isapApi.getPmlaQuestionnaireContext(qid))
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось собрать context")
    } finally {
      setLoading(false)
    }
  }

  const generate = async () => {
    if (!qid) return
    setGenerating(true)
    setError("")
    try {
      setGeneration(await isapApi.generatePmlaFromQuestionnaire(qid, { save_debug_artifacts: true }))
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось запустить генерацию")
    } finally {
      setGenerating(false)
    }
  }

  const previewImport = async (file: File) => {
    setLoading(true)
    setError("")
    try {
      setImportPreview(await isapApi.previewPmlaQuestionnaireImport(file))
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось получить preview импорта")
    } finally {
      setLoading(false)
    }
  }

  const confirmImport = async () => {
    const jobId = importPreview?.job?.id
    if (!jobId) return
    setLoading(true)
    try {
      await isapApi.confirmImportJob(jobId)
      setMessage("Импорт подтвержден")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось подтвердить импорт")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadFacilities()
  }, [])

  const disabled = !qid
  const selectedScenarios = getStrings(draft.selected_scenarios)
  const customScenarios = getList(draft.custom_scenarios)
  const emergencyServices = getList(draft.selected_emergency_services)
  const actualResources = getList(resources.actual_items)
  const hasManualPasf = Boolean((draft.pasf_manual || {}).name || (draft.pasf_manual || {}).certificate_number)
  const generationWarnings = [
    !qid ? "Анкета еще не создана или не открыта" : "",
    incident.has_incidents === null || incident.has_incidents === undefined ? "Не заполнен блок аварий/инцидентов" : "",
    !draft.selected_pasf_id && !hasManualPasf ? "Не выбран или не заполнен ПАСФ" : "",
    emergencyServices.length === 0 && getStrings(draft.selected_emergency_service_ids).length === 0 ? "Не добавлены аварийные службы" : "",
    selectedScenarios.length === 0 && customScenarios.length === 0 ? "Не подтверждены сценарии аварий" : "",
    actualResources.length === 0 ? "Не заполнены фактические силы и средства организации" : "",
  ].filter(Boolean)
  const completedBlocks = [
    Boolean(qid),
    incident.has_incidents !== null && incident.has_incidents !== undefined,
    selectedScenarios.length > 0 || customScenarios.length > 0,
    Boolean(draft.selected_pasf_id || hasManualPasf),
    emergencyServices.length > 0 || getStrings(draft.selected_emergency_service_ids).length > 0,
    actualResources.length > 0,
  ].filter(Boolean).length
  const readinessPercent = Math.round((completedBlocks / 6) * 100)

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Анкета ПМЛА</h1>
          <p className="text-sm text-muted-foreground">
            Данные анкеты становятся проверяемым источником для generation context и DOCX ПМЛА.
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
          <div className="min-w-[280px]">
            <Label>ОПО</Label>
            <Select value={facilityId} onValueChange={setFacilityId}>
              <SelectTrigger><SelectValue placeholder="Выберите ОПО" /></SelectTrigger>
              <SelectContent>
                {facilities.map((facility) => (
                  <SelectItem key={facility.id} value={facility.id}>
                    {facility.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button variant="outline" onClick={loadFacilities} disabled={loading} className="gap-2">
            <RefreshCcw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            ОПО
          </Button>
          <Button variant="outline" onClick={() => openQuestionnaire(false)} disabled={!facilityId || loading}>
            Открыть
          </Button>
          <Button onClick={() => openQuestionnaire(true)} disabled={!facilityId || loading} className="gap-2">
            <Plus className="h-4 w-4" />
            Создать
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Ошибка</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {message && (
        <Alert>
          <CheckCircle2 className="h-4 w-4" />
          <AlertTitle>Готово</AlertTitle>
          <AlertDescription>{message}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>{selectedFacility?.name || "ОПО не выбрано"}</CardTitle>
          <CardDescription>
            {questionnaire ? `Анкета: ${questionnaire.title}` : "Создайте или откройте анкету по выбранному ОПО"}
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm md:grid-cols-4">
          <div><span className="text-muted-foreground">Организация</span><div className="font-medium">{selectedFacility?.organization || "—"}</div></div>
          <div><span className="text-muted-foreground">Рег. номер</span><div className="font-medium">{selectedFacility?.regNumber || "—"}</div></div>
          <div><span className="text-muted-foreground">Класс</span><div className="font-medium">{selectedFacility?.hazardClass || "—"}</div></div>
          <div><span className="text-muted-foreground">Тип</span><div className="font-medium">{selectedFacility?.facilityType || "—"}</div></div>
        </CardContent>
      </Card>

      <Tabs defaultValue="main" className="space-y-4">
        <TabsList className="flex h-auto flex-wrap justify-start">
          <TabsTrigger value="main">Основные</TabsTrigger>
          <TabsTrigger value="incidents">Аварии</TabsTrigger>
          <TabsTrigger value="scenarios">Сценарии</TabsTrigger>
          <TabsTrigger value="pasf">ПАСФ</TabsTrigger>
          <TabsTrigger value="services">Службы</TabsTrigger>
          <TabsTrigger value="resources">Силы</TabsTrigger>
          <TabsTrigger value="notify">Оповещение</TabsTrigger>
          <TabsTrigger value="finance">Финансы</TabsTrigger>
          <TabsTrigger value="training">Тренировки</TabsTrigger>
          <TabsTrigger value="context">Context</TabsTrigger>
          <TabsTrigger value="generate">Генерация</TabsTrigger>
        </TabsList>

        <TabsContent value="main">
          <Card>
            <CardHeader><CardTitle>Основные данные</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              {!selectedFacility && (
                <Alert>
                  <AlertTriangle className="h-4 w-4" />
                  <AlertTitle>Нет данных ОПО</AlertTitle>
                  <AlertDescription>Не заполнены основные данные ОПО. Генерация может быть неполной.</AlertDescription>
                </Alert>
              )}
              <pre className="max-h-80 overflow-auto rounded-md bg-muted p-4 text-xs">{pretty({ facility: selectedFacility, questionnaire: { id: qid, title: questionnaire?.title } })}</pre>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="incidents">
          <Card>
            <CardHeader><CardTitle>Аварии и инциденты</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <RadioGroup
                value={incident.has_incidents === true ? "true" : incident.has_incidents === false || incident.has_incidents === "нет" ? "false" : "review"}
                onValueChange={(value) => updateDraft("incident_history", { ...incident, has_incidents: value === "true" ? true : value === "false" ? false : null })}
                className="grid gap-3 md:grid-cols-3"
              >
                {[
                  ["false", "Нет"],
                  ["true", "Да"],
                  ["review", "Требует проверки"],
                ].map(([value, label]) => (
                  <Label key={value} className="flex items-center gap-2 rounded-md border p-3">
                    <RadioGroupItem value={value} />
                    {label}
                  </Label>
                ))}
              </RadioGroup>
              <Input value={incident.period || ""} onChange={(event) => updateDraft("incident_history", { ...incident, period: event.target.value })} placeholder="Период" />
              {incident.has_incidents === true && (
                <div className="space-y-3">
                  <Button variant="outline" onClick={addIncident} className="gap-2"><Plus className="h-4 w-4" />Добавить событие</Button>
                  {getList(incident.items).map((item, index) => (
                    <div key={index} className="grid gap-2 rounded-md border p-3 md:grid-cols-4">
                      {["date", "event_type", "place", "description", "reason", "consequences", "measures", "source_document"].map((key) => (
                        <Input key={key} value={item[key] || ""} onChange={(event) => updateIncident(index, key, event.target.value)} placeholder={key} />
                      ))}
                      <Button variant="ghost" onClick={() => updateDraft("incident_history", { ...incident, items: getList(incident.items).filter((_, i) => i !== index) })}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
              <SectionActions saving={saving} onSave={() => saveBlock("incident_history", incident)} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="scenarios">
          <Card>
            <CardHeader><CardTitle>Сценарии аварий</CardTitle></CardHeader>
            <CardContent className="space-y-5">
              <div className="grid gap-2 md:grid-cols-2">
                {SCENARIOS.map((scenario) => {
                  const selected = getStrings(draft.selected_scenarios)
                  return (
                    <Label key={scenario} className="flex items-center gap-2 rounded-md border p-3">
                      <Checkbox
                        checked={selected.includes(scenario)}
                        onCheckedChange={(checked) => updateDraft("selected_scenarios", checked ? [...selected, scenario] : selected.filter((item) => item !== scenario))}
                      />
                      {scenario}
                    </Label>
                  )
                })}
              </div>
              <SectionActions saving={saving} onSave={() => saveBlock("selected_scenarios", getStrings(draft.selected_scenarios))} />
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-medium">Пользовательские сценарии / Другое</h3>
                  <Button variant="outline" onClick={addCustomScenario} disabled={disabled || saving} className="gap-2"><Plus className="h-4 w-4" />Добавить</Button>
                </div>
                {getList(draft.custom_scenarios).map((scenario, index) => (
                  <div key={index} className="grid gap-2 rounded-md border p-3 md:grid-cols-3">
                    {["title", "description", "source_equipment", "substance", "consequences"].map((key) => (
                      <Input key={key} value={scenario[key] || ""} onChange={(event) => updateCustomScenario(index, key, event.target.value)} placeholder={key} />
                    ))}
                    <Button variant="ghost" onClick={() => deleteCustomScenario(index)}><Trash2 className="h-4 w-4" /></Button>
                  </div>
                ))}
                <SectionActions saving={saving} onSave={() => saveBlock("custom_scenarios", getList(draft.custom_scenarios))} />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="pasf">
          <Card>
            <CardHeader><CardTitle>ПАСФ</CardTitle></CardHeader>
            <CardContent className="grid gap-3 md:grid-cols-2">
              <Input value={draft.selected_pasf_id || ""} onChange={(event) => updateDraft("selected_pasf_id", event.target.value)} placeholder="selected_pasf_id" />
              {["name", "phone", "address", "certificate_number", "permitted_work_types", "equipment"].map((key) => (
                <Input key={key} value={(draft.pasf_manual || {})[key] || ""} onChange={(event) => updateNested("pasf_manual", key, event.target.value)} placeholder={key} />
              ))}
              {!draft.selected_pasf_id && <Alert className="md:col-span-2"><AlertTriangle className="h-4 w-4" /><AlertTitle>ПАСФ не выбран</AlertTitle><AlertDescription>Можно заполнить ручные данные сейчас и связать справочник позже.</AlertDescription></Alert>}
              <div className="md:col-span-2"><SectionActions saving={saving} onSave={async () => { await saveBlock("selected_pasf_id", draft.selected_pasf_id || ""); await saveBlock("pasf_manual", draft.pasf_manual || {}) }} /></div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="services">
          <Card>
            <CardHeader><CardTitle>Аварийные службы</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <Button variant="outline" onClick={() => updateDraft("selected_emergency_services", [...getList(draft.selected_emergency_services), { service_type: "fire", name: "", address: "", phone: "", dispatcher_phone: "", distance: "", arrival_time: "" }])} className="gap-2">
                <Plus className="h-4 w-4" />Добавить службу
              </Button>
              {getList(draft.selected_emergency_services).map((service, index) => (
                <div key={index} className="grid gap-2 rounded-md border p-3 md:grid-cols-4">
                  <Select value={service.service_type || "fire"} onValueChange={(value) => {
                    const rows = getList(draft.selected_emergency_services)
                    rows[index] = { ...rows[index], service_type: value }
                    updateDraft("selected_emergency_services", rows)
                  }}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>{SERVICE_TYPES.map((type) => <SelectItem key={type} value={type}>{type}</SelectItem>)}</SelectContent>
                  </Select>
                  {["name", "address", "phone", "dispatcher_phone", "distance", "arrival_time"].map((key) => (
                    <Input key={key} value={service[key] || ""} onChange={(event) => {
                      const rows = getList(draft.selected_emergency_services)
                      rows[index] = { ...rows[index], [key]: event.target.value }
                      updateDraft("selected_emergency_services", rows)
                    }} placeholder={key} />
                  ))}
                  <Button variant="ghost" onClick={() => updateDraft("selected_emergency_services", getList(draft.selected_emergency_services).filter((_, i) => i !== index))}><Trash2 className="h-4 w-4" /></Button>
                </div>
              ))}
              <SectionActions saving={saving} onSave={() => saveBlock("selected_emergency_services", getList(draft.selected_emergency_services))} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="resources">
          <Card>
            <CardHeader><CardTitle>Силы и средства</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <Button variant="outline" onClick={() => addRow("organization_resources", "actual_items", { name: "", type: "", quantity: "", location: "", responsible_person: "", purpose: "" })} className="gap-2">
                <Plus className="h-4 w-4" />Добавить средство
              </Button>
              {getList(resources.actual_items).map((row, index) => (
                <div key={index} className="grid gap-2 rounded-md border p-3 md:grid-cols-3">
                  {["name", "type", "quantity", "location", "responsible_person", "purpose"].map((key) => (
                    <Input key={key} value={row[key] || ""} onChange={(event) => updateRow("organization_resources", "actual_items", index, key, event.target.value)} placeholder={key} />
                  ))}
                  <Button variant="ghost" onClick={() => removeRow("organization_resources", "actual_items", index)}><Trash2 className="h-4 w-4" /></Button>
                </div>
              ))}
              <Textarea value={resources.user_notes || ""} onChange={(event) => updateDraft("organization_resources", { ...resources, user_notes: event.target.value })} placeholder="Примечания" />
              {contextPreview?.recommendations && <pre className="max-h-60 overflow-auto rounded-md bg-muted p-3 text-xs">{pretty(contextPreview.recommendations)}</pre>}
              <SectionActions saving={saving} onSave={() => saveBlock("organization_resources", resources)} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notify">
          <SimpleFields title="Оповещение" block="notification_scheme" fields={["first_receiver", "responsible_manager", "calls_pasf", "calls_fire", "calls_medical", "stops_equipment", "evacuation_responsible", "meets_services"]} draft={draft} updateNested={updateNested} saving={saving} saveBlock={saveBlock} />
        </TabsContent>

        <TabsContent value="finance">
          <div className="grid gap-4 lg:grid-cols-2">
            <SimpleFields title="Финансовый резерв" block="financial_reserve" fields={["created", "order_number", "order_date", "amount", "responsible_person"]} draft={draft} updateNested={updateNested} saving={saving} saveBlock={saveBlock} />
            <SimpleFields title="Страхование" block="insurance" fields={["has_contract", "company", "contract_number", "valid_until", "insured_amount"]} draft={draft} updateNested={updateNested} saving={saving} saveBlock={saveBlock} />
          </div>
        </TabsContent>

        <TabsContent value="training">
          <Card>
            <CardHeader><CardTitle>Тренировки и приложения</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 md:grid-cols-3">
                {["conducted", "frequency", "last_date", "last_topic", "participants", "result"].map((key) => (
                  <Input key={key} value={(draft.training || {})[key] || ""} onChange={(event) => updateNested("training", key, event.target.value)} placeholder={key} />
                ))}
              </div>
              <div className="grid gap-2 md:grid-cols-2">
                {ATTACHMENTS.map((item) => {
                  const selected = getStrings(draft.attachments_checklist)
                  return (
                    <Label key={item} className="flex items-center gap-2 rounded-md border p-3">
                      <Checkbox checked={selected.includes(item)} onCheckedChange={(checked) => updateDraft("attachments_checklist", checked ? [...selected, item] : selected.filter((value) => value !== item))} />
                      {item}
                    </Label>
                  )
                })}
              </div>
              <SectionActions saving={saving} onSave={async () => { await saveBlock("training", draft.training || {}); await saveBlock("attachments_checklist", getStrings(draft.attachments_checklist)) }} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="context">
          <Card>
            <CardHeader>
              <CardTitle>Проверка generation context</CardTitle>
              <CardDescription>Context собирается backend-ом из анкеты, ОПО и справочников.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button onClick={buildContext} disabled={disabled || loading} className="gap-2"><FileJson className="h-4 w-4" />Собрать context</Button>
              <pre className="max-h-[520px] overflow-auto rounded-md bg-muted p-4 text-xs">{pretty(contextPreview || {})}</pre>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="generate">
          <div className="grid gap-4 xl:grid-cols-[1fr_420px]">
            <Card>
              <CardHeader>
                <CardTitle>Генерация ПМЛА из анкеты</CardTitle>
                <CardDescription>
                  Перед запуском проверьте context и предупреждения по заполненности анкеты.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3 md:grid-cols-3">
                  <div className="rounded-md border p-3">
                    <div className="text-sm text-muted-foreground">Готовность</div>
                    <div className="text-2xl font-semibold">{readinessPercent}%</div>
                  </div>
                  <div className="rounded-md border p-3">
                    <div className="text-sm text-muted-foreground">Сценарии</div>
                    <div className="text-2xl font-semibold">{selectedScenarios.length + customScenarios.length}</div>
                  </div>
                  <div className="rounded-md border p-3">
                    <div className="text-sm text-muted-foreground">Службы</div>
                    <div className="text-2xl font-semibold">{emergencyServices.length}</div>
                  </div>
                </div>
                {generationWarnings.length > 0 ? (
                  <Alert>
                    <AlertTriangle className="h-4 w-4" />
                    <AlertTitle>Документ может быть неполным</AlertTitle>
                    <AlertDescription>
                      <ul className="list-disc pl-4">
                        {generationWarnings.map((warning) => <li key={warning}>{warning}</li>)}
                      </ul>
                    </AlertDescription>
                  </Alert>
                ) : (
                  <Alert>
                    <CheckCircle2 className="h-4 w-4" />
                    <AlertTitle>Ключевые блоки заполнены</AlertTitle>
                    <AlertDescription>Можно собрать context и запускать генерацию.</AlertDescription>
                  </Alert>
                )}
                <div className="flex flex-wrap gap-2">
                  <Button variant="outline" onClick={buildContext} disabled={disabled || loading} className="gap-2">
                    <FileJson className="h-4 w-4" />
                    Собрать context
                  </Button>
                  <Button onClick={generate} disabled={disabled || generating} className="gap-2">
                    {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <WandSparkles className="h-4 w-4" />}
                    Сгенерировать ПМЛА
                  </Button>
                </div>
                {generation && (
                  <div className="space-y-3">
                    <div className="grid gap-3 md:grid-cols-3">
                      <div className="rounded-md border p-3 text-sm">
                        <div className="text-muted-foreground">document_id</div>
                        <div className="break-all font-mono text-xs">{generation.document_id}</div>
                      </div>
                      <div className="rounded-md border p-3 text-sm">
                        <div className="text-muted-foreground">status</div>
                        <Badge variant="outline">{generation.status}</Badge>
                      </div>
                      <div className="rounded-md border p-3 text-sm">
                        <div className="text-muted-foreground">version</div>
                        <div className="font-semibold">{generation.version}</div>
                      </div>
                    </div>
                    <pre className="max-h-96 overflow-auto rounded-md bg-muted p-4 text-xs">{pretty(generation)}</pre>
                    {generation.quality_review && <QualityReviewBlock review={generation.quality_review} />}
                  </div>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Импорт анкеты из DOCX</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <input ref={fileRef} type="file" accept=".docx" className="hidden" onChange={(event) => {
                  const file = event.target.files?.[0]
                  if (file) previewImport(file)
                  event.target.value = ""
                }} />
                <Button variant="outline" onClick={() => fileRef.current?.click()} disabled={loading} className="gap-2"><FileUp className="h-4 w-4" />Загрузить DOCX</Button>
                {importPreview && (
                  <>
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="outline">job {importPreview.job?.id || "—"}</Badge>
                      <Badge variant={(importPreview.job?.error_rows || 0) > 0 ? "destructive" : "secondary"}>errors {importPreview.job?.error_rows || 0}</Badge>
                      <Badge variant="secondary">warnings {importPreview.job?.warning_rows || 0}</Badge>
                    </div>
                    <div className="max-h-72 overflow-auto rounded-md border">
                      <Table>
                        <TableHeader><TableRow><TableHead>Поле</TableHead><TableHead>Значение</TableHead></TableRow></TableHeader>
                        <TableBody>
                          {Object.entries((importPreview.rows?.[0]?.normalized_data as AnyRecord) || {}).map(([key, value]) => (
                            <TableRow key={key}><TableCell>{key}</TableCell><TableCell>{String(Array.isArray(value) ? value.join(", ") : value || "—")}</TableCell></TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                    <Button onClick={confirmImport} disabled={!importPreview.job?.id || loading}>Подтвердить импорт</Button>
                  </>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

function SimpleFields({
  title,
  block,
  fields,
  draft,
  updateNested,
  saving,
  saveBlock,
}: {
  title: string
  block: string
  fields: string[]
  draft: AnyRecord
  updateNested: (block: string, key: string, value: unknown) => void
  saving: boolean
  saveBlock: (block: string, data: unknown) => void
}) {
  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 md:grid-cols-2">
          {fields.map((field) => (
            <Input key={field} value={(draft[block] || {})[field] || ""} onChange={(event) => updateNested(block, field, event.target.value)} placeholder={field} />
          ))}
        </div>
        <SectionActions saving={saving} onSave={() => saveBlock(block, draft[block] || {})} />
      </CardContent>
    </Card>
  )
}

function QualityReviewBlock({ review }: { review: import("@/lib/api-client").PmlaQualityReview }) {
  const statusConfig = {
    ok: { label: "OK", variant: "default" as const, color: "text-green-600" },
    warning: { label: "ВНИМАНИЕ", variant: "secondary" as const, color: "text-yellow-600" },
    critical: { label: "КРИТИЧНО", variant: "destructive" as const, color: "text-red-600" },
  }
  const cfg = statusConfig[review.overall_status] || statusConfig.ok

  return (
    <Card className="border-dashed">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <ClipboardCheck className="h-5 w-5" />
          Проверка качества ПМЛА
          <Badge variant={cfg.variant}>{cfg.label}</Badge>
          <span className="ml-auto text-2xl font-bold">{review.score}%</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 md:grid-cols-2">
          {review.checks.map((check) => (
            <div key={check.code} className="flex items-start gap-2 rounded-md border p-2 text-sm">
              <Badge variant={check.status === "ok" ? "default" : check.status === "warning" ? "secondary" : "destructive"} className="shrink-0 text-xs">
                {check.status === "ok" ? "OK" : check.status === "warning" ? "!" : "X"}
              </Badge>
              <div>
                <div className="font-medium">{check.title}</div>
                <div className="text-muted-foreground text-xs">{check.message}</div>
              </div>
            </div>
          ))}
        </div>
        {review.missing_required_data.length > 0 && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Отсутствуют обязательные данные</AlertTitle>
            <AlertDescription>
              <ul className="list-disc pl-4">{review.missing_required_data.map((item) => <li key={item}>{item}</li>)}</ul>
            </AlertDescription>
          </Alert>
        )}
        {review.manual_review_required.length > 0 && (
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Требуется ручная проверка</AlertTitle>
            <AlertDescription>
              <ul className="list-disc pl-4">{review.manual_review_required.map((item) => <li key={item}>{item}</li>)}</ul>
            </AlertDescription>
          </Alert>
        )}
        {review.recommendations.length > 0 && (
          <div className="rounded-md bg-muted p-3 text-sm">
            <div className="font-medium mb-1">Рекомендации</div>
            <ul className="list-disc pl-4 text-muted-foreground">{review.recommendations.map((item) => <li key={item}>{item}</li>)}</ul>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
