"use client"

import { useEffect, useState } from "react"
import { Brain, CheckCircle2, RefreshCcw, Save, ServerCog, Settings, TriangleAlert } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { toast } from "sonner"
import { apiRequest, isapApi } from "@/lib/api-client"

type HealthState = Record<string, unknown> | null

interface AiSettings {
  llm_provider: string
  lmstudio_model: string
  lmstudio_base_url: string
  lmstudio_api_key: string
  lmstudio_embedding_model: string
  openai_model: string
  openai_base_url: string
  openai_api_key: string
  openai_embedding_model: string
  ollama_model: string
  ollama_base_url: string
  ollama_embedding_model: string
  embedding_provider: string
  llm_fallback_enabled: boolean
}

const PROVIDERS = [
  { value: "lmstudio", label: "LM Studio (локально)" },
  { value: "ollama", label: "Ollama (локально)" },
  { value: "openai", label: "OpenAI / Gemini / Облако" },
  { value: "yandex", label: "YandexGPT" },
  { value: "glm", label: "GLM (Zhipu AI)" },
]

function StatusBadge({ data }: { data: HealthState }) {
  const status = data?.status
  if (status === "ok") return <Badge className="gap-1 bg-emerald-600 hover:bg-emerald-600"><CheckCircle2 className="h-3.5 w-3.5" />OK</Badge>
  if (status === "error") return <Badge variant="destructive" className="gap-1"><TriangleAlert className="h-3.5 w-3.5" />Ошибка</Badge>
  return <Badge variant="secondary">—</Badge>
}

function JsonView({ data }: { data: unknown }) {
  return (
    <pre className="max-h-60 overflow-auto rounded-lg bg-muted p-3 text-xs leading-relaxed">
      {JSON.stringify(data, null, 2)}
    </pre>
  )
}

function SettingsForm({ settings, onSave }: { settings: AiSettings; onSave: (s: Partial<AiSettings>) => Promise<void> }) {
  const [form, setForm] = useState(settings)
  const [saving, setSaving] = useState(false)

  const update = (key: keyof AiSettings, value: string | boolean) => setForm((p) => ({ ...p, [key]: value }))

  const handleSave = async () => {
    setSaving(true)
    try {
      await onSave(form)
      toast.success("Настройки сохранены")
    } catch (err: any) {
      toast.error("Ошибка", { description: err.message })
    } finally {
      setSaving(false)
    }
  }

  const provider = form.llm_provider

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Label className="text-sm font-semibold">Провайдер LLM</Label>
        <Select value={provider} onValueChange={(v) => update("llm_provider", v)}>
          <SelectTrigger className="w-full max-w-sm"><SelectValue /></SelectTrigger>
          <SelectContent>
            {PROVIDERS.map((p) => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {provider === "lmstudio" && (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">LM Studio</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label>Chat модель</Label>
              <Input value={form.lmstudio_model} onChange={(e) => update("lmstudio_model", e.target.value)} placeholder="local-model" />
            </div>
            <div>
              <Label>Base URL</Label>
              <Input value={form.lmstudio_base_url} onChange={(e) => update("lmstudio_base_url", e.target.value)} placeholder="http://host.docker.internal:1234/v1" />
            </div>
            <div>
              <Label>API Key</Label>
              <Input value={form.lmstudio_api_key} onChange={(e) => update("lmstudio_api_key", e.target.value)} placeholder="lm-studio" />
            </div>
            <div>
              <Label>Embedding модель</Label>
              <Input value={form.lmstudio_embedding_model} onChange={(e) => update("lmstudio_embedding_model", e.target.value)} placeholder="text-embedding-nomic-embed-text-v1.5" />
            </div>
          </div>
        </div>
      )}

      {provider === "ollama" && (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Ollama</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label>Chat модель</Label>
              <Input value={form.ollama_model} onChange={(e) => update("ollama_model", e.target.value)} placeholder="llama3:8b" />
            </div>
            <div>
              <Label>Base URL</Label>
              <Input value={form.ollama_base_url} onChange={(e) => update("ollama_base_url", e.target.value)} placeholder="http://localhost:11434" />
            </div>
            <div>
              <Label>Embedding модель</Label>
              <Input value={form.ollama_embedding_model} onChange={(e) => update("ollama_embedding_model", e.target.value)} placeholder="nomic-embed-text" />
            </div>
          </div>
        </div>
      )}

      {provider === "openai" && (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">OpenAI / Gemini</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label>Chat модель</Label>
              <Input value={form.openai_model} onChange={(e) => update("openai_model", e.target.value)} placeholder="gemini-2.5-flash" />
            </div>
            <div>
              <Label>Base URL</Label>
              <Input value={form.openai_base_url} onChange={(e) => update("openai_base_url", e.target.value)} placeholder="https://api.openai.com/v1" />
            </div>
            <div>
              <Label>API Key</Label>
              <Input type="password" value={form.openai_api_key} onChange={(e) => update("openai_api_key", e.target.value)} placeholder="sk-..." />
            </div>
            <div>
              <Label>Embedding модель</Label>
              <Input value={form.openai_embedding_model} onChange={(e) => update("openai_embedding_model", e.target.value)} placeholder="text-embedding-3-small" />
            </div>
          </div>
        </div>
      )}

      <div className="space-y-2">
        <Label className="text-sm font-semibold">Embedding провайдер</Label>
        <Select value={form.embedding_provider} onValueChange={(v) => update("embedding_provider", v)}>
          <SelectTrigger className="w-full max-w-sm"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="lmstudio">LM Studio</SelectItem>
            <SelectItem value="openai">OpenAI</SelectItem>
            <SelectItem value="ollama">Ollama</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="flex items-center gap-3">
        <Switch checked={form.llm_fallback_enabled} onCheckedChange={(v) => update("llm_fallback_enabled", v)} />
        <Label className="text-sm">Fallback провайдер (автопереключение при ошибке)</Label>
      </div>

      <Separator />

      <Button onClick={handleSave} disabled={saving} className="gap-2">
        <Save className="h-4 w-4" />
        {saving ? "Сохранение..." : "Сохранить настройки"}
      </Button>
    </div>
  )
}

export function AiPage() {
  const [config, setConfig] = useState<HealthState>(null)
  const [chat, setChat] = useState<HealthState>(null)
  const [embeddings, setEmbeddings] = useState<HealthState>(null)
  const [settings, setSettings] = useState<AiSettings | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  const load = async () => {
    setLoading(true)
    setError("")
    try {
      const [cfg, chatHealth, embeddingsHealth, aiSettings] = await Promise.all([
        isapApi.aiConfig(),
        isapApi.aiHealth(),
        isapApi.embeddingsHealth(),
        apiRequest<AiSettings>("/api/v1/ai/settings"),
      ])
      setConfig(cfg)
      setChat(chatHealth)
      setEmbeddings(embeddingsHealth)
      setSettings(aiSettings)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить данные")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleSaveSettings = async (updated: Partial<AiSettings>) => {
    await apiRequest("/api/v1/ai/settings", {
      method: "POST",
      body: JSON.stringify(updated),
    })
    await load()
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">AI / LM Studio</h1>
          <p className="text-muted-foreground text-sm mt-1">Настройка и диагностика AI-провайдеров</p>
        </div>
        <Button onClick={load} disabled={loading} className="gap-2">
          <RefreshCcw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Обновить
        </Button>
      </div>

      {error && (
        <Card className="border-destructive/40 bg-destructive/5">
          <CardContent className="pt-6 text-sm text-destructive">{error}</CardContent>
        </Card>
      )}

      <Tabs defaultValue="settings">
        <TabsList>
          <TabsTrigger value="settings" className="gap-1.5"><Settings className="h-4 w-4" />Настройки</TabsTrigger>
          <TabsTrigger value="health" className="gap-1.5"><Brain className="h-4 w-4" />Диагностика</TabsTrigger>
        </TabsList>

        <TabsContent value="settings" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><Settings className="h-5 w-5" />AI-провайдеры</CardTitle>
              <CardDescription>Настройте подключение к LLM и embedding-моделям. Настройки сохраняются на сервере.</CardDescription>
            </CardHeader>
            <CardContent>
              {settings ? (
                <SettingsForm settings={settings} onSave={handleSaveSettings} />
              ) : (
                <p className="text-muted-foreground text-sm">Загрузка настроек...</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="health" className="mt-4 space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader className="flex flex-row items-start justify-between gap-4 space-y-0">
                <div>
                  <CardTitle className="flex items-center gap-2"><Brain className="h-5 w-5" />Chat LLM</CardTitle>
                  <CardDescription>Генерация текстов ПМЛА</CardDescription>
                </div>
                <StatusBadge data={chat} />
              </CardHeader>
              <CardContent><JsonView data={chat || { status: "loading" }} /></CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-start justify-between gap-4 space-y-0">
                <div>
                  <CardTitle className="flex items-center gap-2"><ServerCog className="h-5 w-5" />Embeddings</CardTitle>
                  <CardDescription>Векторизация для RAG</CardDescription>
                </div>
                <StatusBadge data={embeddings} />
              </CardHeader>
              <CardContent><JsonView data={embeddings || { status: "loading" }} /></CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Текущая конфигурация</CardTitle>
            </CardHeader>
            <CardContent><JsonView data={config || { status: "loading" }} /></CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
