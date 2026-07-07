"use client"

import { useEffect, useState } from "react"
import {
  ArrowLeft,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ClipboardCheck,
  Copy,
  Download,
  FileDown,
  FileText,
  Loader2,
  RefreshCcw,
  WandSparkles,
  XCircle,
} from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { isapApi } from "@/lib/api-client"
import { useNavStore } from "@/lib/nav-store"

type AnyRecord = Record<string, unknown>

function pretty(value: unknown) {
  return JSON.stringify(value ?? {}, null, 2)
}

export function DocumentDetailPage() {
  const { documentDetailId: docId, goBack } = useNavStore()
  const [doc, setDoc] = useState<AnyRecord | null>(null)
  const [preview, setPreview] = useState<AnyRecord | null>(null)
  const [versions, setVersions] = useState<AnyRecord[]>([])
  const [aiReview, setAiReview] = useState<AnyRecord | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [message, setMessage] = useState("")
  const [copied, setCopied] = useState(false)
  const [reviewing, setReviewing] = useState(false)
  const [runningAiReview, setRunningAiReview] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [showRawJson, setShowRawJson] = useState(false)

  const loadDocument = async () => {
    if (!docId) return
    setLoading(true)
    setError("")
    try {
      const [status, vers] = await Promise.all([
        isapApi.getPmlaDocumentStatus(docId),
        isapApi.getPmlaDocumentVersions(docId),
      ])
      setDoc(status)
      setVersions(Array.isArray(vers) ? vers : [])
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить документ")
    } finally {
      setLoading(false)
    }
  }

  const loadPreview = async () => {
    if (!docId) return
    try {
      setPreview(await isapApi.getPmlaDocumentPreview(docId))
    } catch { /* preview may not be available */ }
  }

  const loadAiReview = async () => {
    if (!docId) return
    try {
      setAiReview(await isapApi.getAiReview(docId))
    } catch { /* ai review may not be available */ }
  }

  const handleReview = async (action: "approve" | "reject") => {
    if (!docId) return
    setReviewing(true)
    setError("")
    try {
      await isapApi.reviewPmlaDocument(docId, action)
      setMessage(action === "approve" ? "Документ утверждён" : "Документ возвращён на доработку")
      await loadDocument()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось выполнить действие")
    } finally {
      setReviewing(false)
    }
  }

  const handleRunAiReview = async () => {
    if (!docId) return
    setRunningAiReview(true)
    try {
      await isapApi.runAiReview(docId)
      await loadAiReview()
      setMessage("AI-ревью завершено")
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI-ревью недоступно")
    } finally {
      setRunningAiReview(false)
    }
  }

  const copyId = async () => {
    if (!docId) return
    try {
      await navigator.clipboard.writeText(docId)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch { /* ignore */ }
  }

  const handleDownload = async () => {
    if (!docId) return
    setDownloading(true)
    setError("")
    try {
      const blob = await isapApi.downloadPmlaDocumentBlob(docId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `PMLA-${docId}.docx`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось скачать документ")
    } finally {
      setDownloading(false)
    }
  }

  useEffect(() => {
    if (docId) {
      loadDocument()
      loadPreview()
      loadAiReview()
    }
  }, [docId])

  if (!docId) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold tracking-tight">Документ не выбран</h1>
        <Button variant="outline" onClick={goBack} className="gap-2"><ArrowLeft className="h-4 w-4" />Назад к списку</Button>
      </div>
    )
  }

  const status = String(doc?.status || "—")
  const statusVariant = status === "approved" ? "default" : status === "rejected" ? "destructive" : "secondary"
  const version = doc?.version_number ?? doc?.version ?? "—"
  const title = String(doc?.title || "ПМЛА")
  const source = String(doc?.generation_meta?.source || "—")
  const canReview = status === "pending_review"

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={goBack} className="gap-1"><ArrowLeft className="h-4 w-4" />Назад</Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              <FileText className="h-6 w-6" />
              {title}
              <Badge variant={statusVariant}>{status}</Badge>
            </h1>
            <p className="text-muted-foreground text-sm mt-1">Детали документа ПМЛА</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadDocument} disabled={loading} className="gap-2">
            <RefreshCcw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />Обновить
          </Button>
          <Button variant="default" onClick={handleDownload} disabled={downloading} className="gap-2">
            {downloading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileDown className="h-4 w-4" />}
            Скачать DOCX
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive"><AlertTriangle className="h-4 w-4" /><AlertTitle>Ошибка</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>
      )}
      {message && (
        <Alert><CheckCircle2 className="h-4 w-4" /><AlertTitle>Готово</AlertTitle><AlertDescription>{message}</AlertDescription></Alert>
      )}

      {/* Document Info */}
      <Card>
        <CardHeader className="pb-3"><CardTitle className="text-base">Информация о документе</CardTitle></CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4 text-sm">
            <div className="rounded-md border p-3">
              <div className="text-muted-foreground text-xs">document_id</div>
              <div className="break-all font-mono text-xs mt-1">{docId}</div>
            </div>
            <div className="rounded-md border p-3">
              <div className="text-muted-foreground text-xs">Статус</div>
              <div className="mt-1"><Badge variant={statusVariant}>{status}</Badge></div>
            </div>
            <div className="rounded-md border p-3">
              <div className="text-muted-foreground text-xs">Версия</div>
              <div className="font-semibold mt-1">{version}</div>
            </div>
            <div className="rounded-md border p-3">
              <div className="text-muted-foreground text-xs">Источник</div>
              <div className="mt-1">{source === "pmla_questionnaire" ? "Анкета ПМЛА" : source}</div>
            </div>
          </div>
          <div className="flex gap-2 mt-3">
            <Button variant="outline" size="sm" onClick={copyId} className="gap-1">
              <Copy className="h-3.5 w-3.5" />{copied ? "Скопировано!" : "Копировать ID"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Actions for pending_review */}
      {canReview && (
        <Card>
          <CardHeader className="pb-3"><CardTitle className="text-base">Решение по документу</CardTitle></CardHeader>
          <CardContent className="flex gap-2">
            <Button onClick={() => handleReview("approve")} disabled={reviewing} className="gap-2">
              {reviewing ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
              Утвердить
            </Button>
            <Button variant="destructive" onClick={() => handleReview("reject")} disabled={reviewing} className="gap-2">
              {reviewing ? <Loader2 className="h-4 w-4 animate-spin" /> : <XCircle className="h-4 w-4" />}
              Вернуть на доработку
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Tabs: Preview / Versions / AI Review */}
      <Tabs defaultValue="preview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="preview">Просмотр</TabsTrigger>
          <TabsTrigger value="versions">Версии ({versions.length})</TabsTrigger>
          <TabsTrigger value="ai-review">AI-ревью</TabsTrigger>
          <TabsTrigger value="raw">JSON</TabsTrigger>
        </TabsList>

        <TabsContent value="preview">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Предпросмотр документа</CardTitle>
              <CardDescription>Разделы DOCX, извлечённые из сохранённого файла.</CardDescription>
            </CardHeader>
            <CardContent>
              {preview?.sections && preview.sections.length > 0 ? (
                <div className="space-y-4 max-h-[600px] overflow-auto">
                  {preview.sections.map((section: AnyRecord, i: number) => (
                    <div key={i} className="rounded-md border p-3">
                      <div className="font-medium text-sm mb-1">{String(section.title || `Раздел ${i + 1}`)}</div>
                      <div className="text-xs text-muted-foreground whitespace-pre-wrap">{String(section.content || "—")}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-muted-foreground py-8 text-center">Предпросмотр недоступен</div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="versions">
          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-base">История версий</CardTitle></CardHeader>
            <CardContent>
              {versions.length === 0 ? (
                <div className="text-sm text-muted-foreground py-8 text-center">Версии отсутствуют</div>
              ) : (
                <div className="space-y-2">
                  {versions.map((v: AnyRecord, i: number) => (
                    <div key={i} className="flex items-center justify-between rounded-md border p-3 text-sm">
                      <div>
                        <span className="font-medium">Версия {String(v.version_number || i + 1)}</span>
                        {v.created_at && <span className="text-muted-foreground ml-2">{String(v.created_at)}</span>}
                      </div>
                      <Badge variant="outline">{String(v.status || "—")}</Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="ai-review">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <ClipboardCheck className="h-5 w-5" />
                AI-ревью
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button variant="outline" onClick={handleRunAiReview} disabled={runningAiReview} className="gap-2">
                {runningAiReview ? <Loader2 className="h-4 w-4 animate-spin" /> : <WandSparkles className="h-4 w-4" />}
                Запустить AI-ревью
              </Button>
              {aiReview && (
                <pre className="max-h-96 overflow-auto rounded-md bg-muted p-4 text-xs">{pretty(aiReview)}</pre>
              )}
              {!aiReview && !runningAiReview && (
                <div className="text-sm text-muted-foreground py-4 text-center">AI-ревью ещё не запускалось</div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="raw">
          <Card>
            <CardContent className="pt-6">
              <pre className="max-h-96 overflow-auto rounded-md bg-muted p-4 text-xs">{pretty(doc)}</pre>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
