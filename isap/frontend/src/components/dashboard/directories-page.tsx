"use client"

import { useState } from "react"
import { Search, BookOpen, Scale, FileText, FolderOpen, FileCheck, Mail } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

/* ─── Типы ─── */

interface DirectoryItem {
  id: string
  code: string
  name: string
  description: string
  status: "действует" | "утратил силу" | "изменён"
  date: string
}

/* ─── Данные ─── */

const federalLaws: DirectoryItem[] = [
  { id: "ФЗ-001", code: "ФЗ-116", name: "О промышленной безопасности опасных производственных объектов", description: "Федеральный закон от 21.07.1997 № 116-ФЗ. Устанавливает требования к обеспечению промышленной безопасности ОПО.", status: "изменён", date: "01.01.2026" },
  { id: "ФЗ-002", code: "ФЗ-99", name: "Об обеспечении единства измерений", description: "Федеральный закон от 26.06.2008 № 102-ФЗ. Регулирует отношения в области обеспечения единства измерений.", status: "действует", date: "01.01.2026" },
  { id: "ФЗ-003", code: "ФЗ-68", name: "О защите населения и территорий от ЧС природного и техногенного характера", description: "Федеральный закон от 21.12.1994 № 68-ФЗ.", status: "действует", date: "01.01.2026" },
  { id: "ФЗ-004", code: "ФЗ-225", name: "Об обязательном страховании гражданской ответственности владельца ОПО", description: "Федеральный закон от 27.07.2010 № 225-ФЗ.", status: "действует", date: "01.01.2026" },
  { id: "ФЗ-005", code: "ФЗ-20", name: "О техническом регулировании", description: "Федеральный закон от 27.12.2002 № 184-ФЗ.", status: "действует", date: "01.01.2026" },
]

const governmentDecrees: DirectoryItem[] = [
  { id: "ПП-001", code: "ПП-739", name: "Об утверждении Правил регистрации объектов в государственном реестре ОПО", description: "Постановление Правительства РФ от 24.11.1998 № 1364.", status: "изменён", date: "15.03.2026" },
  { id: "ПП-002", code: "ПП-263", name: "Положение о лицензировании деятельности по эксплуатации ОПО", description: "Постановление Правительства РФ от 12.08.2024 № 1039.", status: "действует", date: "01.01.2026" },
  { id: "ПП-003", code: "ПП-880", name: "Об организации производственного контроля за соблюдением требований ПБ", description: "Постановление Правительства РФ от 10.03.2023 № 388.", status: "действует", date: "01.01.2026" },
  { id: "ПП-004", code: "ПП-610", name: "Положение о расследовании причин аварий на ОПО", description: "Постановление Правительства РФ от 11.06.2003 № 339.", status: "изменён", date: "01.01.2026" },
]

const rstOrders: DirectoryItem[] = [
  { id: "РТН-001", code: "РТН-525", name: "Порядок проведения экспертизы промышленной безопасности", description: "Приказ Ростехнадзора от 14.03.2024 № 118. Регламентирует порядок организации и проведения экспертизы ПБ.", status: "действует", date: "01.09.2024" },
  { id: "РТН-002", code: "РТН-146", name: "Федеральные нормы и правила в области ПБ: Общие правила взрывобезопасности", description: "Приказ Ростехнадзора от 11.12.2020 № 514.", status: "изменён", date: "01.01.2026" },
  { id: "РТН-003", code: "РТН-331", name: "Положение о порядке проведения аттестации в области ПБ", description: "Приказ Ростехнадзора от 29.01.2024 № 28.", status: "действует", date: "01.03.2024" },
  { id: "РТН-004", code: "РТН-448", name: "Правила устройства и безопасной эксплуатации сосудов под давлением", description: "Приказ Ростехнадзора от 25.03.2024 № 120.", status: "действует", date: "01.09.2024" },
  { id: "РТН-005", code: "РТН-219", name: "Правила безопасности при эксплуатации трубопроводов пара и горячей воды", description: "Приказ Ростехнадзора от 15.12.2020 № 535.", status: "действует", date: "01.01.2021" },
  { id: "РТН-006", code: "РТН-089", name: "Правила безопасности при работе с инструментом и приспособлениями", description: "Приказ Ростехнадзора от 19.10.2018 № 497.", status: "действует", date: "01.01.2019" },
]

const gosts: DirectoryItem[] = [
  { id: "ГОСТ-001", code: "ГОСТ 12.1.003-2014", name: "ССБТ. Шум. Общие требования безопасности", description: "Межгосударственный стандарт. Устанавливает классификацию шума, характеристики и допустимые уровни на рабочих местах.", status: "действует", date: "01.03.2015" },
  { id: "ГОСТ-002", code: "ГОСТ 12.1.005-88", name: "ССБТ. Общие санитарно-гигиенические требования к воздуху рабочей зоны", description: "Устанавливает предельно допустимые концентрации вредных веществ в воздухе рабочей зоны.", status: "действует", date: "01.01.1989" },
  { id: "ГОСТ-003", code: "ГОСТ Р 12.3.047-2012", name: "ССБТ. Пожарная безопасность технологических процессов", description: "Общие требования к методам обеспечения пожарной безопасности технологических процессов.", status: "действует", date: "01.01.2013" },
  { id: "ГОСТ-004", code: "ГОСТ Р 22.0.02-2016", name: "Безопасность в чрезвычайных ситуациях. Термины и определения", description: "Устанавливает основные термины и определения в области безопасности в ЧС.", status: "действует", date: "01.03.2017" },
  { id: "ГОСТ-005", code: "ГОСТ 12.0.006-2002", name: "ССБТ. Общие требования безопасности к оборудованию", description: "Требования безопасности к конструкции, изготовлению и эксплуатации производственного оборудования.", status: "изменён", date: "01.07.2003" },
  { id: "ГОСТ-006", code: "ГОСТ Р 50571.1-2023", name: "Электроустановки низковольтные. Часть 1. Основные положения", description: "Требования к проектированию, монтажу и эксплуатации электроустановок до 1000 В.", status: "действует", date: "01.01.2024" },
]

const snips: DirectoryItem[] = [
  { id: "СП-001", code: "СП 73.13330.2016", name: "Внутренние санитарно-технические системы зданий", description: "Свод правил. Актуализированная редакция СНиП 3.05.01-85. Правила монтажа внутренних систем.", status: "изменён", date: "01.07.2017" },
  { id: "СП-002", code: "СП 62.13330.2011", name: "Газораспределительные системы", description: "Свод правил. Актуализированная редакция СНиП 42-01-2002. Требования к проектированию и строительству.", status: "изменён", date: "01.01.2013" },
  { id: "СП-003", code: "СП 4.13130.2013", name: "Системы противопожарной защиты. Ограничение распространения пожара", description: "Требования к объёмно-планировочным и конструктивным решениям по ограничению распространения пожара.", status: "действует", date: "01.01.2014" },
  { id: "СП-004", code: "СП 484.1311500.2020", name: "Системы противопожарной защиты. Установки пожарной автоматики", description: "Нормы и правила проектирования установок пожарной сигнализации и автоматического пожаротушения.", status: "действует", date: "01.01.2021" },
  { id: "СП-005", code: "СП 256.1325800.2016", name: "Электроустановки жилых и общественных зданий", description: "Правила проектирования электроустановок зданий, монтажных и пусконаладочных работ.", status: "действует", date: "01.06.2017" },
]

const instructionsData: DirectoryItem[] = [
  { id: "ИН-001", code: "РД 03-614-03", name: "Порядок применения сварочных технологий при ремонте оборудования", description: "Руководящий документ. Требования к организациям сварочных работ при ремонте технических устройств ОПО.", status: "действует", date: "01.01.2004" },
  { id: "ИН-002", code: "РД 03-421-01", name: "Методические указания по проведению анализа риска ОПО", description: "Руководство по идентификации опасностей, оценке риска и разработке мер по его снижению.", status: "действует", date: "01.01.2002" },
  { id: "ИН-003", code: "РД 09-250-98", name: "Методические указания по оценке технического состояния сосудов и аппаратов", description: "Порядок оценки остаточного ресурса сосудов и аппаратов, работающих под давлением.", status: "действует", date: "01.01.1999" },
  { id: "ИН-004", code: "РД 13-220.00-КТН-207-09", name: "Инструкция по неразрушающему контролю оборудования и трубопроводов", description: "Требования к методам и объёмам неразрушающего контроля при техническом диагностировании.", status: "изменён", date: "01.01.2010" },
  { id: "ИН-005", code: "РД 05-473-03", name: "Инструкция по безопасному ведению работ газоопасных объектов", description: "Требования безопасности при проведении газоопасных работ, наряды-допуски, порядок допуска.", status: "действует", date: "01.01.2004" },
  { id: "ИН-006", code: "РД 03-607-03", name: "Инструкция по визуальному и измерительному контролю", description: "Методы визуального и измерительного контроля сварных соединений и основного металла.", status: "действует", date: "01.01.2004" },
]

const lettersData: DirectoryItem[] = [
  { id: "ПР-001", code: "РТН-00-67-2024", name: "О порядке подачи декларации промышленной безопасности в электронном виде", description: "Письмо Ростехнадзора от 15.04.2024. Разъясняет порядок представления декларации ПБ через Единый портал.", status: "действует", date: "15.04.2024" },
  { id: "ПР-002", code: "РТН-00-89-2024", name: "О применении ПБ 03-576-03 при регистрации ОПО", description: "Письмо Ростехнадзора от 22.06.2024. Разъяснение по вопросам идентификации ОПО и заполнения паспорта ОПО.", status: "действует", date: "22.06.2024" },
  { id: "ПР-003", code: "РТН-00-112-2023", name: "О порядке продления сроков эксплуатации технических устройств", description: "Письмо Ростехнадзора от 10.09.2023. Порядок продления срока безопасной эксплуатации по результатам экспертизы.", status: "действует", date: "10.09.2023" },
  { id: "ПР-004", code: "РТН-00-34-2025", name: "О требованиях к плану мероприятий по локализации и ликвидации аварий", description: "Письмо Ростехнадзора от 18.02.2025. Уточнение требований к содержанию и порядку согласования ПМЛА.", status: "действует", date: "18.02.2025" },
  { id: "ПР-005", code: "РТН-00-78-2025", name: "Об организации обучения и аттестации специалистов в области ПБ", description: "Письмо Ростехнадзора от 30.05.2025. Разъяснение по формам подготовки и периодичности аттестации.", status: "действует", date: "30.05.2025" },
  { id: "ПР-006", code: "РТН-00-95-2023", name: "О применении риск-ориентированного подхода при государственном контроле", description: "Письмо Ростехнадзора от 20.11.2023. Методология оценки рисков и определения периодичности проверок.", status: "действует", date: "20.11.2023" },
]

const docTypes = [
  { key: "plan_localization", name: "План мероприятий по локализации аварий", period: "Ежегодно", required: true },
  { key: "production_control", name: "Положение о производственном контроле", period: "При изменениях", required: true },
  { key: "rescue_services", name: "Договор с аварийно-спасательными формированиями", period: "Ежегодно", required: true },
  { key: "financial_resources", name: "Наличие финансовых и материальных ресурсов", period: "Ежегодно", required: true },
  { key: "safety_attestation", name: "Аттестация по промышленной безопасности", period: "Раз в 5 лет", required: true },
  { key: "pressure_equipment", name: "Регистрация оборудования под давлением", period: "При вводе в эксплуатацию", required: true },
  { key: "opo_insurance", name: "Договор обязательного страхования ОПО", period: "Ежегодно", required: true },
  { key: "expertise_conclusion", name: "Заключение экспертизы ПБ", period: "По графику", required: true },
  { key: "passport_opo", name: "Паспорт ОПО", period: "При изменениях", required: true },
  { key: "technical_device_passport", name: "Паспорт технического устройства", period: "При вводе в эксплуатацию", required: false },
  { key: "instructions", name: "Инструкции по безопасному ведению работ", period: "При изменениях", required: true },
  { key: "pc_report", name: "Отчёт о производственном контроле", period: "Ежеквартально", required: true },
]

/* ─── Вспомогательные ─── */

const statusVariant: Record<string, "destructive" | "default" | "secondary" | "outline"> = {
  "действует": "default",
  "изменён": "secondary",
  "утратил силу": "outline",
}

type ActiveTab = "laws" | "decrees" | "rst" | "gost" | "snip" | "instructions" | "letters" | "docTypes"

/* ─── Таблица ─── */

function NormativeTable({ items, filterStatus, search }: {
  items: DirectoryItem[]
  filterStatus: string
  search: string
}) {
  const filtered = items.filter((item) => {
    const matchSearch =
      item.name.toLowerCase().includes(search.toLowerCase()) ||
      item.code.toLowerCase().includes(search.toLowerCase()) ||
      item.description.toLowerCase().includes(search.toLowerCase())
    const matchStatus = filterStatus === "all" || item.status === filterStatus
    return matchSearch && matchStatus
  })

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-[170px]">Код</TableHead>
          <TableHead>Наименование</TableHead>
          <TableHead className="hidden lg:table-cell">Описание</TableHead>
          <TableHead className="w-[130px]">Статус</TableHead>
          <TableHead className="hidden sm:table-cell w-[110px]">Дата</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {filtered.map((item) => (
          <TableRow key={item.id}>
            <TableCell className="font-mono text-sm font-medium">{item.code}</TableCell>
            <TableCell className="font-medium">{item.name}</TableCell>
            <TableCell className="hidden lg:table-cell text-muted-foreground text-sm max-w-[300px] truncate">
              {item.description}
            </TableCell>
            <TableCell>
              <Badge variant={statusVariant[item.status] || "outline"}>
                {item.status}
              </Badge>
            </TableCell>
            <TableCell className="hidden sm:table-cell text-muted-foreground text-sm">
              {item.date}
            </TableCell>
          </TableRow>
        ))}
        {filtered.length === 0 && (
          <TableRow>
            <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
              Записи не найдены
            </TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  )
}

/* ─── Основная страница ─── */

export function DirectoriesPage() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("laws")
  const [search, setSearch] = useState("")
  const [filterStatus, setFilterStatus] = useState("all")

  const tabs: { key: ActiveTab; label: string; icon: typeof Scale; count: number }[] = [
    { key: "laws", label: "Федеральные законы", icon: Scale, count: federalLaws.length },
    { key: "decrees", label: "Постановления Правительства", icon: BookOpen, count: governmentDecrees.length },
    { key: "rst", label: "Приказы Ростехнадзора", icon: FileText, count: rstOrders.length },
    { key: "gost", label: "ГОСТ", icon: FileCheck, count: gosts.length },
    { key: "snip", label: "СНиП / СП", icon: FileCheck, count: snips.length },
    { key: "instructions", label: "Инструкции (РД)", icon: FileText, count: instructionsData.length },
    { key: "letters", label: "Письма разъяснения", icon: Mail, count: lettersData.length },
    { key: "docTypes", label: "Типы документов ОПО", icon: FolderOpen, count: docTypes.length },
  ]

  const currentItems = (() => {
    switch (activeTab) {
      case "laws": return federalLaws
      case "decrees": return governmentDecrees
      case "rst": return rstOrders
      case "gost": return gosts
      case "snip": return snips
      case "instructions": return instructionsData
      case "letters": return lettersData
      default: return []
    }
  })()

  const isNormative = activeTab !== "docTypes"

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Справочники</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Нормативно-правовая база и справочная информация по промышленной безопасности
        </p>
      </div>

      {/* Табы */}
      <div className="flex flex-wrap gap-2">
        {tabs.map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.key
          return (
            <Button
              key={tab.key}
              variant={isActive ? "default" : "outline"}
              size="sm"
              className="gap-2"
              onClick={() => { setActiveTab(tab.key); setSearch(""); setFilterStatus("all") }}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
              <Badge variant={isActive ? "secondary" : "outline"} className="ml-1 h-5 px-1.5 text-xs">
                {tab.count}
              </Badge>
            </Button>
          )
        })}
      </div>

      {/* Поиск и фильтр */}
      {isNormative && (
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <div className="relative flex-1 max-w-sm w-full">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Поиск по наименованию или коду..."
              className="pl-8"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <Select value={filterStatus} onValueChange={setFilterStatus}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Статус" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Все статусы</SelectItem>
              <SelectItem value="действует">Действует</SelectItem>
              <SelectItem value="изменён">Изменён</SelectItem>
              <SelectItem value="утратил силу">Утратил силу</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      {/* Содержимое */}
      {isNormative && (
        <Card>
          <CardContent className="p-4 md:p-6">
            <NormativeTable items={currentItems} filterStatus={filterStatus} search={search} />
          </CardContent>
        </Card>
      )}

      {activeTab === "docTypes" && (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[50px]">№</TableHead>
                  <TableHead>Наименование документа</TableHead>
                  <TableHead className="hidden sm:table-cell w-[160px]">Периодичность</TableHead>
                  <TableHead className="w-[120px]">Обязательный</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {docTypes.map((doc, idx) => (
                  <TableRow key={doc.key}>
                    <TableCell className="text-muted-foreground text-sm">{idx + 1}</TableCell>
                    <TableCell className="font-medium">{doc.name}</TableCell>
                    <TableCell className="hidden sm:table-cell text-muted-foreground text-sm">{doc.period}</TableCell>
                    <TableCell>
                      <Badge variant={doc.required ? "default" : "outline"}>
                        {doc.required ? "Да" : "Нет"}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}