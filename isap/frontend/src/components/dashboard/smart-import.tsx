"use client"

import { useRef, useState } from "react"
import { Upload, File, Sparkles, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { toast } from "sonner"

interface SmartImportProps {
  /** Список поддерживаемых форматов (без точки) */
  accept?: string
  /** Подпись кнопки (по умолчанию "Умный импорт") */
  label?: string
  /** Текст-подсказка */
  hint?: string
}

/**
 * «Умный импорт» — кнопка с файловым инпутом.
 * После выбора файла показывает анимацию «анализа»,
 * затем toast-уведомление об успешном импорте.
 */
export function SmartImport({
  accept = ".pdf,.docx,.doc,.xlsx,.xls",
  label = "Умный импорт",
  hint = "PDF, DOCX, XLSX",
}: SmartImportProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [fileName, setFileName] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setFileName(file.name)
    setLoading(true)

    // Имитация «умного» разбора файла
    await new Promise((r) => setTimeout(r, 1200))
    setLoading(false)

    toast.success("Данные импортированы", {
      description: `Из файла «${file.name}» (${(file.size / 1024).toFixed(1)} КБ) извлечены данные и заполнены поля формы`,
      duration: 4000,
    })

    // Сбросить инпут, чтобы можно было выбрать тот же файл повторно
    e.target.value = ""
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