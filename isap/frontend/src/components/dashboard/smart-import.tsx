"use client"

import { useRef, useState } from "react"
import { Upload, File, Sparkles, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { toast } from "sonner"
import { apiUpload } from "@/lib/api-client"

interface SmartImportProps {
  /** Список поддерживаемых форматов (без точки) */
  accept?: string
  /** Подпись кнопки (по умолчанию "Умный импорт") */
  label?: string
  /** Текст-подсказка */
  hint?: string
  /** API endpoint для импорта (если не указан — работает в демо-режиме) */
  apiEndpoint?: string
  /** Callback с распарсенными данными после успешного импорта */
  onImported?: (data: Record<string, unknown>) => void
}

/**
 * «Умный импорт» — загружает файл на бэкенд, получает распарсенные данные
 * и передаёт их через onImported callback.
 */
export function SmartImport({
  accept = ".pdf,.docx,.doc,.xlsx,.xls",
  label = "Умный импорт",
  hint = "PDF, DOCX, XLSX",
  apiEndpoint,
  onImported,
}: SmartImportProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [fileName, setFileName] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setFileName(file.name)
    setLoading(true)

    try {
      if (apiEndpoint) {
        // Реальный вызов API
        const result = await apiUpload<{
          success: boolean
          data: Record<string, unknown>
          warnings?: string[]
        }>(apiEndpoint, file)

        if (result.success && result.data) {
          toast.success("Данные импортированы", {
            description: `Из файла «${file.name}» извлечены данные (${Object.keys(result.data).length} полей)`,
            duration: 4000,
          })

          // Передаём данные в форму
          if (onImported) {
            onImported(result.data)
          }

          if (result.warnings?.length) {
            result.warnings.forEach((w) => toast.warning(w))
          }
        } else {
          toast.error("Не удалось извлечь данные из файла", {
            description: result.warnings?.[0] || "Проверьте структуру документа",
          })
        }
      } else {
        // Демо-режим (заглушка)
        await new Promise((r) => setTimeout(r, 1200))
        toast.success("Данные импортированы (демо)", {
          description: `Из файла «${file.name}» (${(file.size / 1024).toFixed(1)} КБ)`,
          duration: 4000,
        })
      }
    } catch (err) {
      toast.error("Ошибка импорта", {
        description: err instanceof Error ? err.message : "Неизвестная ошибка",
      })
    } finally {
      setLoading(false)
      // Сбросить инпут, чтобы можно было выбрать тот же файл повторно
      e.target.value = ""
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          className="hidden"
          onChange={handleFile}
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="gap-2"
          disabled={loading}
          onClick={() => inputRef.current?.click()}
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Sparkles className="h-4 w-4" />
          )}
          {label}
        </Button>
        {fileName && !loading && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <File className="h-3 w-3 shrink-0" />
            <span className="truncate max-w-[200px]">{fileName}</span>
          </div>
        )}
      </div>
      {hint && (
        <p className="text-xs text-muted-foreground/70 pl-0.5">{hint}</p>
      )}
    </div>
  )
}
