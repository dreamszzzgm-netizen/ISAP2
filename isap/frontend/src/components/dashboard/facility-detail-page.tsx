"use client"

import { useEffect, useState } from "react"
import {
  ArrowLeft,
  CheckCircle2,
  ClipboardCheck,
  FileText,
  Loader2,
  Plus,
  RefreshCcw,
  Sparkles,
  WandSparkles,
  Building2,
  Cpu,
  FlaskConical,
  MapPin,
} from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { isapApi, type PmlaDocumentListItem, type PmlaQuestionnaire } from "@/lib/api-client"
import { useNavStore } from "@/lib/nav-store"

type AnyRecord = Record<string, unknown>

export type FacilityData = {
  id: string
  name: string
  organization_name?: string
  reg_number?: string
  hazard_class?: string
  facility_type?: string
  address?: string
  opo_full_name?: string
  classification?: string[]
  work_processes?: Record<string, string>
  licensed_activities?: Array<{ license_id: string; activity?: string }>
  composition_structures?: Array<{ type: string; name: string; area_sqm?: number }>
  nearby_hazardous?: Array<{ name: string; distance_m?: number }>
  properties?: Record<string, string>
  commissioning_date?: string
}

export type CompositionData = {
  facility_id: string
  structures: Array<{ type: string; name: string }>
  equipment: Array<{ id: string; name: string; equipment_type?: string; serial_number?: string; manufacturer?: string; manufacture_year?: number }>
  substances: Array<{ id: string; name: string; cas_number?: string; quantity_kg?: number }>
  total_equipment: number
  total_substances: number
  total_structures: number
}

export const CLASSIFICATION_LABELS: Record<string, string> = {
  "4.1": "взрывопожароопасные",
  "4.2": "пожароопасные",
  "4.3": "взрывоопасные",
  "4.4": "химически опасные",
  "4.5": "токсичные",
  "4.6": "высокотоксичные",
  "4.7": "радиоактивные",
  "4.8": "взрывоопасные по газу",
  "4.9": "опасные по взрыву пыли",
  "4.10": "высокого давления",
  "4.11": "высоких температур",
  "4.12": "опасные производственные объекты транспорта",
}

export const WORK_PROCESS_LABELS: Record<string, string> = {
  "2.1": "транспортирование",
  "2.2": "переработка",
  "2.3": "хранение",
  "2.4": "утилизация",
  "2.5": "захоронение",
  "2.6": "использование",
}

export function FacilityDetailPage() {
  const { facilityDetailId: facilityId, goBack, openPmlaQuestionnaire, openDocumentDetail } = useNavStore()
  const [facility, setFacility] = useState<FacilityData | null>(null)
  const [composition, setComposition] = useState<CompositionData | null>(null)
  const [questionnaire, setQuestionnaire] = useState<PmlaQuestionnaire | null>(null)
  const [documents, setDocuments] = useState<PmlaDocumentListItem[]>([])
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState("")
  const [message, setMessage] = useState("")

  const loadFacility = async () => {
    if (!facilityId) return
    setLoading(true)
    setError("")
    try {
      const data = await isapApi.getFacilityFull(facilityId)
      setFacility(data as FacilityData)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить ОПО")
    } finally {
      setLoading(false)
    }
  }

  const loadComposition = async () => {
    if (!facilityId) return
    try {
      const data = await isapApi.getFacilityComposition(facilityId)
      setComposition(data as CompositionData)
    } catch {
      setComposition(null)
    }
  }

  const loadQuestionnaire = async () => {
    if (!facilityId) return
    try {
      const q = await isapApi.getPmlaQuestionnaireByFacility(facilityId)
      setQuestionnaire(q)
      const docs = await isapApi.getQuestionnaireDocuments(q.id)
      setDocuments(docs)
    } catch {
      setQuestionnaire(null)
      setDocuments([])
    }
  }

  const createQuestionnaire = async () => {
    if (!facilityId) return
    setCreating(true)
    setError("")
    try {
      const q = await isapApi.createPmlaQuestionnaire(facilityId)
      setQuestionnaire(q)
      setMessage("Анкета ПМЛА создана")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось создать анкету")
    } finally {
      setCreating(false)
    }
  }

  const generatePmla = async (template_version: "v1" | "v2") => {
    if (!questionnaire) return
    setGenerating(true)
    setError("")
    try {
      await isapApi.generatePmlaFromQuestionnaire(questionnaire.id, { template_version, save_debug_artifacts: true })
      setMessage("ПМЛА сгенерирован. Откройте анкету для просмотра результата.")
      await loadQuestionnaire()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сгенерировать ПМЛА")
    } finally {
      setGenerating(false)
    }
  }

  useEffect(() => {
    if (facilityId) {
      loadFacility()
      loadComposition()
      loadQuestionnaire()
    }
  }, [facilityId])

  if (!facilityId) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold tracking-tight">ОПО не выбрано</h1>
        <Button variant="outline" onClick={goBack} className="gap-2"><ArrowLeft className="h-4 w-4" />Назад</Button>
      </div>
    )
  }

  const displayName = facility?.opo_full_name || facility?.name || "Загрузка..."
  const latestDoc = documents.length > 0 ? documents[0] : null

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={goBack} className="gap-1"><ArrowLeft className="h-4 w-4" />Назад</Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{displayName}</h1>
            <p className="text-muted-foreground text-sm mt-1">Карточка опасного производственного объекта</p>
          </div>
        </div>
        <Button variant="outline" onClick={() => { loadFacility(); loadComposition(); loadQuestionnaire() }} disabled={loading} className="gap-2">
          <RefreshCcw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />Обновить
        </Button>
      </div>

      {error && (
        <Alert variant="destructive"><AlertTitle>Ошибка</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>
      )}
      {message && (
        <Alert><CheckCircle2 className="h-4 w-4" /><AlertTitle>Готово</AlertTitle><AlertDescription>{message}</AlertDescription></Alert>
      )}

      {/* Tabs */}
      {facility && (
        <Tabs defaultValue="basic" className="space-y-4">
          <TabsList>
            <TabsTrigger value="basic" className="gap-2"><Building2 className="h-4 w-4" />Основные сведения</TabsTrigger>
            <TabsTrigger value="characterization" className="gap-2"><Cpu className="h-4 w-4" />Сведения, характеризующие ОПО</TabsTrigger>
            <TabsTrigger value="pmla" className="gap-2"><FileText className="h-4 w-4" />ПМЛА</TabsTrigger>
          </TabsList>

          {/* ═══════════════════════════════════════════════════════════
              Tab 1: Основные сведения — только 4 поля
              ═══════════════════════════════════════════════════════════ */}
          <TabsContent value="basic" className="space-y-4">
            <Card>
              <CardHeader className="pb-3"><CardTitle className="text-base">Данные ОПО</CardTitle></CardHeader>
              <CardContent>
                <div className="grid gap-3 md:grid-cols-2 text-sm">
                  <div className="rounded-md border p-3">
                    <div className="text-muted-foreground text-xs">Наименование</div>
                    <div className="font-medium mt-1">{facility.opo_full_name || facility.name}</div>
                  </div>
                  <div className="rounded-md border p-3">
                    <div className="text-muted-foreground text-xs">Рег. номер</div>
                    <div className="font-mono text-xs mt-1">{facility.reg_number || "—"}</div>
                  </div>
                  <div className="rounded-md border p-3">
                    <div className="text-muted-foreground text-xs">Класс опасности</div>
                    <div className="mt-1">{facility.hazard_class ? <Badge variant="outline">{facility.hazard_class}</Badge> : "—"}</div>
                  </div>
                  <div className="rounded-md border p-3">
                    <div className="text-muted-foreground text-xs">Адрес</div>
                    <div className="mt-1 flex items-center gap-1">
                      <MapPin className="h-3.5 w-3.5 text-muted-foreground" />
                      {facility.address || "—"}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* ═══════════════════════════════════════════════════════════
              Tab 2: Сведения, характеризующие ОПО
              ═══════════════════════════════════════════════════════════ */}
          <TabsContent value="characterization" className="space-y-4">

            {/* Типовое наименование и hazard_class */}
            <Card>
              <CardHeader className="pb-3"><CardTitle className="text-base">Идентификация ОПО</CardTitle></CardHeader>
              <CardContent>
                <div className="grid gap-3 md:grid-cols-2 text-sm">
                  <div className="rounded-md border p-3">
                    <div className="text-muted-foreground text-xs">Типовое наименование</div>
                    <div className="font-medium mt-1">{facility.opo_full_name || facility.name}</div>
                  </div>
                  <div className="rounded-md border p-3">
                    <div className="text-muted-foreground text-xs">Класс опасности</div>
                    <div className="mt-1">{facility.hazard_class ? <Badge variant="outline">{facility.hazard_class}</Badge> : "—"}</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Отраслевая принадлежность, ОКТМО, дата ввода, собственник */}
            <Card>
              <CardHeader className="pb-3"><CardTitle className="text-base">Характеристики</CardTitle></CardHeader>
              <CardContent>
                <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4 text-sm">
                  <div className="rounded-md border p-3">
                    <div className="text-muted-foreground text-xs">Отраслевая принадлежность (ОКВЭД)</div>
                    <div className="font-mono text-xs mt-1">{facility.properties?.okved || "—"}</div>
                  </div>
                  <div className="rounded-md border p-3">
                    <div className="text-muted-foreground text-xs">ОКТМО</div>
                    <div className="font-mono text-xs mt-1">{facility.properties?.oktmo || "—"}</div>
                  </div>
                  <div className="rounded-md border p-3">
                    <div className="text-muted-foreground text-xs">Дата ввода в эксплуатацию</div>
                    <div className="mt-1">{facility.commissioning_date || "—"}</div>
                  </div>
                  <div className="rounded-md border p-3">
                    <div className="text-muted-foreground text-xs">Собственник</div>
                    <div className="text-xs mt-1">{facility.properties?.owner || "—"}</div>
                  </div>
                </div>
                {facility.properties?.owner_basis && (
                  <div className="mt-3 text-sm text-muted-foreground">
                    Основание владения: {facility.properties.owner_basis}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Процессы 2.1–2.6 */}
            <Card>
              <CardHeader className="pb-3"><CardTitle className="text-base">Процессы и работы (2.1–2.6)</CardTitle></CardHeader>
              <CardContent>
                {facility.work_processes && Object.keys(facility.work_processes).length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(facility.work_processes).map(([key, value]) => (
                      <Badge key={key} variant="outline">{key} {WORK_PROCESS_LABELS[key] || value}</Badge>
                    ))}
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground">Не указаны</div>
                )}
              </CardContent>
            </Card>

            {/* Классификация 4.1–4.12 */}
            <Card>
              <CardHeader className="pb-3"><CardTitle className="text-base">Признаки классификации (4.1–4.12)</CardTitle></CardHeader>
              <CardContent>
                {facility.classification && facility.classification.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {facility.classification.map((code) => (
                      <Badge key={code} variant="secondary">{code} {CLASSIFICATION_LABELS[code] || ""}</Badge>
                    ))}
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground">Не указаны</div>
                )}
              </CardContent>
            </Card>

            {/* Лицензируемые виды деятельности */}
            <Card>
              <CardHeader className="pb-3"><CardTitle className="text-base">Лицензируемые виды деятельности</CardTitle></CardHeader>
              <CardContent>
                {facility.licensed_activities && facility.licensed_activities.length > 0 ? (
                  <div className="space-y-2">
                    {facility.licensed_activities.map((la, i) => (
                      <div key={i} className="rounded-md border p-3 text-sm">
                        <div className="font-medium">{la.activity || "Лицензия"}</div>
                        <div className="text-muted-foreground text-xs font-mono">{la.license_id}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground">Лицензии не привязаны</div>
                )}
              </CardContent>
            </Card>

            {/* Состав ОПО: площадки/здания */}
            <Card>
              <CardHeader className="pb-3"><CardTitle className="text-base">Площадки и здания</CardTitle></CardHeader>
              <CardContent>
                {composition && composition.structures.length > 0 ? (
                  <div className="space-y-2">
                    {composition.structures.map((s, i) => (
                      <div key={i} className="flex items-center gap-3 rounded-md border p-3 text-sm">
                        <Badge variant="outline">{s.type}</Badge>
                        <span className="font-medium">{s.name}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground">Структурные элементы не добавлены</div>
                )}
              </CardContent>
            </Card>

            {/* Состав ОПО: технические устройства */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Cpu className="h-4 w-4" />Технические устройства
                  {composition && <Badge variant="secondary">{composition.total_equipment}</Badge>}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {composition && composition.equipment.length > 0 ? (
                  <div className="space-y-2">
                    {composition.equipment.map((eq) => (
                      <div key={eq.id} className="flex items-center gap-3 rounded-md border p-3 text-sm">
                        <Badge variant="outline">{eq.equipment_type || "—"}</Badge>
                        <div className="flex-1">
                          <div className="font-medium">{eq.name}</div>
                          <div className="text-muted-foreground text-xs">
                            {eq.manufacturer && `${eq.manufacturer}`}
                            {eq.manufacture_year && ` (${eq.manufacture_year})`}
                            {eq.serial_number && ` — ${eq.serial_number}`}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground">Оборудование не добавлено</div>
                )}
              </CardContent>
            </Card>

            {/* Состав ОПО: опасные вещества */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <FlaskConical className="h-4 w-4" />Опасные вещества
                  {composition && <Badge variant="secondary">{composition.total_substances}</Badge>}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {composition && composition.substances.length > 0 ? (
                  <div className="space-y-2">
                    {composition.substances.map((sub) => (
                      <div key={sub.id} className="flex items-center gap-3 rounded-md border p-3 text-sm">
                        <div className="flex-1">
                          <div className="font-medium">{sub.name}</div>
                          <div className="text-muted-foreground text-xs">
                            {sub.cas_number && `CAS: ${sub.cas_number}`}
                            {sub.quantity_kg && ` — ${sub.quantity_kg} кг`}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground">Опасные вещества не добавлены</div>
                )}
              </CardContent>
            </Card>

            {/* Опасные вещества на других ОПО ближе 500м */}
            <Card>
              <CardHeader className="pb-3"><CardTitle className="text-base">Опасные вещества на других ОПО ближе 500 м</CardTitle></CardHeader>
              <CardContent>
                {facility.nearby_hazardous && facility.nearby_hazardous.length > 0 ? (
                  <div className="space-y-2">
                    {facility.nearby_hazardous.map((nh, i) => (
                      <div key={i} className="flex items-center gap-3 rounded-md border p-3 text-sm">
                        <span className="font-medium">{nh.name}</span>
                        {nh.distance_m && <Badge variant="outline">{nh.distance_m} м</Badge>}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground">Нет данных</div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* ═══════════════════════════════════════════════════════════
              Tab 3: ПМЛА — без изменений
              ═══════════════════════════════════════════════════════════ */}
          <TabsContent value="pmla" className="space-y-4">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <FileText className="h-5 w-5" />ПМЛА
                </CardTitle>
                <CardDescription>План мероприятий по локализации и ликвидации последствий аварий</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {!questionnaire ? (
                  <div className="space-y-3">
                    <Alert>
                      <AlertDescription>Анкета ПМЛА ещё не создана для этого объекта.</AlertDescription>
                    </Alert>
                    <Button onClick={createQuestionnaire} disabled={creating} className="gap-2">
                      {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                      Создать анкету ПМЛА
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="grid gap-3 md:grid-cols-3 text-sm">
                      <div className="rounded-md border p-3">
                        <div className="text-muted-foreground text-xs">Анкета</div>
                        <div className="font-mono text-xs mt-1">{questionnaire.id}</div>
                      </div>
                      <div className="rounded-md border p-3">
                        <div className="text-muted-foreground text-xs">Обновлена</div>
                        <div className="mt-1">{questionnaire.updated_at ? new Date(questionnaire.updated_at).toLocaleString("ru-RU") : "—"}</div>
                      </div>
                      <div className="rounded-md border p-3">
                        <div className="text-muted-foreground text-xs">Версий документов</div>
                        <div className="font-semibold mt-1">{documents.length}</div>
                      </div>
                    </div>

                    {latestDoc ? (
                      <div className="rounded-md border p-4 space-y-2">
                        <div className="flex items-center gap-2 text-sm font-medium">
                          <FileText className="h-4 w-4" />
                          Последний документ
                          <Badge variant="outline">v{latestDoc.version ?? "—"}</Badge>
                          <Badge variant={latestDoc.status === "approved" ? "default" : "secondary"}>{latestDoc.status}</Badge>
                        </div>
                        <div className="flex items-center gap-4 text-xs text-muted-foreground">
                          {latestDoc.quality_score != null && (
                            <span className={`font-medium ${latestDoc.quality_status === "critical" ? "text-red-600" : latestDoc.quality_status === "warning" ? "text-yellow-600" : "text-green-600"}`}>
                              Качество: {latestDoc.quality_score} / 100
                            </span>
                          )}
                          {latestDoc.created_at && <span>{new Date(latestDoc.created_at).toLocaleString("ru-RU")}</span>}
                        </div>
                        <Button variant="outline" size="sm" onClick={() => openDocumentDetail(latestDoc.document_id)} className="gap-1 mt-2">
                          <FileText className="h-3.5 w-3.5" />Открыть документ
                        </Button>
                      </div>
                    ) : (
                      <Alert>
                        <AlertDescription>Документы ПМЛА ещё не создавались.</AlertDescription>
                      </Alert>
                    )}

                    <div className="flex flex-wrap gap-2">
                      <Button variant="outline" onClick={() => openPmlaQuestionnaire(facilityId)} className="gap-2">
                        <ClipboardCheck className="h-4 w-4" />Открыть анкету ПМЛА
                      </Button>
                      <Button onClick={() => generatePmla("v1")} disabled={generating} className="gap-2">
                        {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <WandSparkles className="h-4 w-4" />}
                        Сгенерировать ПМЛА
                      </Button>
                      <Button onClick={() => generatePmla("v2")} disabled={generating} variant="secondary" className="gap-2">
                        {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                        PMLA v2 — пилот
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}
