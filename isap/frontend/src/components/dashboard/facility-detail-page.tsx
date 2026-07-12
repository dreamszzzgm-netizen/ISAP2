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
} from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { isapApi, type PmlaDocumentListItem, type PmlaQuestionnaire } from "@/lib/api-client"
import { useNavStore } from "@/lib/nav-store"

type AnyRecord = Record<string, unknown>

type FacilityData = {
  id: string
  name: string
  organization_name?: string
  reg_number?: string
  hazard_class?: string
  facility_type?: string
  address?: string
}

export function FacilityDetailPage() {
  const { facilityDetailId: facilityId, goBack, openPmlaQuestionnaire, openDocumentDetail } = useNavStore()
  const [facility, setFacility] = useState<FacilityData | null>(null)
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
      const facilities = await isapApi.facilities()
      const found = Array.isArray(facilities) ? facilities.find((f: AnyRecord) => String(f.id) === facilityId) : null
      setFacility(found as FacilityData | null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить ОПО")
    } finally {
      setLoading(false)
    }
  }

  const loadQuestionnaire = async () => {
    if (!facilityId) return
    try {
      const q = await isapApi.getPmlaQuestionnaireByFacility(facilityId)
      setQuestionnaire(q)
      // Load documents for this questionnaire.
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

  const latestDoc = documents.length > 0 ? documents[0] : null

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={goBack} className="gap-1"><ArrowLeft className="h-4 w-4" />Назад</Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{facility?.name || "Загрузка..."}</h1>
            <p className="text-muted-foreground text-sm mt-1">Карточка опасного производственного объекта</p>
          </div>
        </div>
        <Button variant="outline" onClick={() => { loadFacility(); loadQuestionnaire() }} disabled={loading} className="gap-2">
          <RefreshCcw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />Обновить
        </Button>
      </div>

      {error && (
        <Alert variant="destructive"><AlertTitle>Ошибка</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>
      )}
      {message && (
        <Alert><CheckCircle2 className="h-4 w-4" /><AlertTitle>Готово</AlertTitle><AlertDescription>{message}</AlertDescription></Alert>
      )}

      {/* Facility Info */}
      {facility && (
        <Card>
          <CardHeader className="pb-3"><CardTitle className="text-base">Данные ОПО</CardTitle></CardHeader>
          <CardContent>
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4 text-sm">
              <div className="rounded-md border p-3">
                <div className="text-muted-foreground text-xs">Организация</div>
                <div className="font-medium mt-1">{facility.organization_name || "—"}</div>
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
                <div className="text-muted-foreground text-xs">Тип объекта</div>
                <div className="mt-1">{facility.facility_type || "—"}</div>
              </div>
            </div>
            {facility.address && (
              <div className="mt-3 text-sm text-muted-foreground">Адрес: {facility.address}</div>
            )}
          </CardContent>
        </Card>
      )}

      {/* PMLA Section */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <FileText className="h-5 w-5" />
            ПМЛА
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
              {/* Questionnaire info */}
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

              {/* Latest document */}
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

              {/* Actions */}
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
    </div>
  )
}
