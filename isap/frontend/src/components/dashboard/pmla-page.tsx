"use client"

import { useEffect, useState } from "react"
import { FileText, RefreshCcw, WandSparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { isapApi } from "@/lib/api-client"
import { useNavStore } from "@/lib/nav-store"

type AnyRow = Record<string, unknown>

export function PmlaPage() {
  const { openDocumentDetail } = useNavStore()
  const [documents, setDocuments] = useState<AnyRow[]>([])
  const [expiring, setExpiring] = useState<AnyRow[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  const load = async () => {
    setLoading(true)
    setError("")
    try {
      const [docs, near] = await Promise.all([
        isapApi.pmlaDocuments(),
        isapApi.pmlaExpiring(30),
      ])
      setDocuments(Array.isArray(docs) ? docs as AnyRow[] : [])
      setExpiring(Array.isArray(near) ? near as AnyRow[] : [])
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить ПМЛА")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">ПМЛА</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Генерация, проверка, версии и экспорт планов мероприятий по локализации и ликвидации аварий.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={load} disabled={loading} className="gap-2">
            <RefreshCcw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Обновить
          </Button>
          <Button className="gap-2" disabled title="Будет подключено после Identity/Organizations/OPO">
            <WandSparkles className="h-4 w-4" />
            Создать ПМЛА
          </Button>
        </div>
      </div>

      {error && (
        <Card className="border-destructive/40 bg-destructive/5">
          <CardContent className="pt-6 text-sm text-destructive">{error}</CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2"><CardDescription>Всего ПМЛА</CardDescription></CardHeader>
          <CardContent className="text-3xl font-bold">{documents.length}</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardDescription>К пересмотру 30 дней</CardDescription></CardHeader>
          <CardContent className="text-3xl font-bold">{expiring.length}</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardDescription>AI pipeline</CardDescription></CardHeader>
          <CardContent><Badge variant="secondary">LM Studio + RAG</Badge></CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><FileText className="h-5 w-5" />Реестр ПМЛА</CardTitle>
          <CardDescription>Данные берутся из FastAPI backend.</CardDescription>
        </CardHeader>
        <CardContent>
          {documents.length === 0 ? (
            <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
              Документы ПМЛА пока не найдены. После подключения карточки ОПО здесь появится реестр.
            </div>
          ) : (
            <div className="overflow-auto rounded-lg border">
              <table className="w-full text-sm">
                <thead className="bg-muted text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 text-left">Название</th>
                    <th className="px-3 py-2 text-left">ОПО</th>
                    <th className="px-3 py-2 text-left">Статус</th>
                    <th className="px-3 py-2 text-left">Создан</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((doc, index) => (
                    <tr key={String(doc.id || index)} className="border-t cursor-pointer hover:bg-muted/50" onClick={() => doc.id && openDocumentDetail(String(doc.id))}>
                      <td className="px-3 py-2 font-medium">{String(doc.title || "ПМЛА")}</td>
                      <td className="px-3 py-2">{String(doc.facility_name || "—")}</td>
                      <td className="px-3 py-2"><Badge variant="outline">{String(doc.status || "—")}</Badge></td>
                      <td className="px-3 py-2">{String(doc.created_at || "—")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
