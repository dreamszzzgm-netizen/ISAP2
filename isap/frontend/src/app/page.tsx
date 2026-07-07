"use client"

import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar"
import { AppSidebar } from "@/components/dashboard/sidebar"
import { DashboardHeader } from "@/components/dashboard/header"
import { KpiCard } from "@/components/dashboard/kpi-card"
import {
  ExpertiseChart,
  OpoByClassChart,
  ContractStatusChart,
  TasksByWeekChart,
} from "@/components/dashboard/charts"
import { UpcomingEventsTable } from "@/components/dashboard/data-table"
import { ClientsPage } from "@/components/dashboard/clients-page"
import { OpoPage } from "@/components/dashboard/opo-page"
import { TasksPage } from "@/components/dashboard/tasks-page"
import { ContractsPage } from "@/components/dashboard/contracts-page"
import { ExpertisePage } from "@/components/dashboard/expertise-page"
import { AnalyticsPage } from "@/components/dashboard/analytics-page"
import { DirectoriesPage } from "@/components/dashboard/directories-page"
import { PmlaPage } from "@/components/dashboard/pmla-page"
import { PmlaQuestionnairePage } from "@/components/dashboard/pmla-questionnaire-page"
import { DocumentDetailPage } from "@/components/dashboard/document-detail-page"
import { AiPage } from "@/components/dashboard/ai-page"
import { kpiData } from "@/lib/analytics-data"
import { useNavStore, type PageKey } from "@/lib/nav-store"
import { Settings, HelpCircle } from "lucide-react"

function PlaceholderPage({ title, description }: { title: string; description: string }) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
        <p className="text-muted-foreground text-sm mt-1">{description}</p>
      </div>
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="bg-muted rounded-full p-4 mb-4">
          <Settings className="h-8 w-8 text-muted-foreground" />
        </div>
        <p className="text-lg font-medium">Раздел в разработке</p>
        <p className="text-sm text-muted-foreground mt-1">Данный раздел будет доступен в ближайшем обновлении</p>
      </div>
    </div>
  )
}

function OverviewPage() {
  return (
    <div className="space-y-6">
      <div className="mb-2">
        <h1 className="text-2xl font-bold tracking-tight">Обзор</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Сводка по промышленной безопасности за текущий период
        </p>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4 mb-6">
        {kpiData.map((kpi) => (
          <KpiCard key={kpi.title} {...kpi} />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3 mb-6">
        <ExpertiseChart />
        <OpoByClassChart />
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 mb-6">
        <ContractStatusChart />
        <TasksByWeekChart />
      </div>
      <UpcomingEventsTable />
    </div>
  )
}

const PAGE_TITLES: Record<PageKey, { title: string; description: string }> = {
  overview: { title: "Обзор", description: "Ключевые метрики и аналитика" },
  tasks: { title: "Задачи", description: "Управление задачами и поручениями" },
  clients: { title: "Организации", description: "Единый справочник организаций и контрагентов" },
  contracts: { title: "Договоры", description: "Реестр договоров и соглашений" },
  analytics: { title: "Аналитика", description: "Детальная аналитика и отчёты" },
  expertise: { title: "Экспертизы", description: "Учёт экспертиз промышленной безопасности" },
  opo: { title: "ОПО", description: "Реестр опасных производственных объектов" },
  pmla: { title: "ПМЛА", description: "Генерация и проверка ПМЛА" },
  pmlaQuestionnaire: { title: "Анкета ПМЛА", description: "Инженерная анкета и generation context" },
  documents: { title: "Документы", description: "Общий реестр документов" },
  ai: { title: "AI / LM Studio", description: "Настройки и диагностика локальной модели" },
  directories: { title: "Справочники", description: "Нормативно-справочная информация" },
  settings: { title: "Настройки", description: "Параметры системы" },
  help: { title: "Помощь", description: "Справка и документация" },
}

export default function Home() {
  const { activePage } = useNavStore()

  const renderPage = () => {
    switch (activePage) {
      case "overview":
        return <OverviewPage />
      case "clients":
        return <ClientsPage />
      case "opo":
        return <OpoPage />
      case "tasks":
        return <TasksPage />
      case "contracts":
        return <ContractsPage />
      case "analytics":
        return <AnalyticsPage />
      case "expertise":
        return <ExpertisePage />
      case "directories":
        return <DirectoriesPage />
      case "pmla":
        return <PmlaPage />
      case "pmlaQuestionnaire":
        return <PmlaQuestionnairePage />
      case "ai":
        return <AiPage />
      case "documents":
        return <PlaceholderPage {...PAGE_TITLES.documents} />
      case "documentDetail":
        return <DocumentDetailPage />
      case "settings":
        return <PlaceholderPage {...PAGE_TITLES.settings} />
      case "help":
        return <PlaceholderPage {...PAGE_TITLES.help} />
      default:
        return <OverviewPage />
    }
  }

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <DashboardHeader />
        <main className="flex-1 overflow-auto p-4 md:p-6">
          {renderPage()}
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}
