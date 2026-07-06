"use client"

import {
  LayoutDashboard,
  BarChart3,
  Users,
  ClipboardList,
  FileText,
  ShieldCheck,
  Factory,
  BookOpen,
  Settings,
  HelpCircle,
  ChevronUp,
  Brain,
  FileStack,
  ClipboardCheck,
} from "lucide-react"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import { useNavStore, type PageKey } from "@/lib/nav-store"

const mainNav: { title: string; icon: typeof LayoutDashboard; page: PageKey }[] = [
  { title: "Обзор", icon: LayoutDashboard, page: "overview" },
  { title: "Задачи", icon: ClipboardList, page: "tasks" },
  { title: "Организации", icon: Users, page: "clients" },
  { title: "Договоры", icon: FileText, page: "contracts" },
  { title: "Аналитика", icon: BarChart3, page: "analytics" },
]

const safetyNav: { title: string; icon: typeof ShieldCheck; page: PageKey }[] = [
  { title: "Экспертизы", icon: ShieldCheck, page: "expertise" },
  { title: "ОПО", icon: Factory, page: "opo" },
  { title: "ПМЛА", icon: FileStack, page: "pmla" },
  { title: "Анкета ПМЛА", icon: ClipboardCheck, page: "pmlaQuestionnaire" },
  { title: "Документы", icon: FileText, page: "documents" },
]

const refNav: { title: string; icon: typeof BookOpen; page: PageKey }[] = [
  { title: "Справочники", icon: BookOpen, page: "directories" },
  { title: "AI / LM Studio", icon: Brain, page: "ai" },
]

const bottomNav: { title: string; icon: typeof Settings; page: PageKey }[] = [
  { title: "Настройки", icon: Settings, page: "settings" },
  { title: "Помощь", icon: HelpCircle, page: "help" },
]

export function AppSidebar() {
  const { activePage, setActivePage } = useNavStore()

  return (
    <Sidebar variant="inset">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <a href="#" onClick={(e) => { e.preventDefault(); setActivePage("overview") }}>
                <div className="bg-primary text-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg">
                  <ShieldCheck className="size-4" />
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-semibold">ISAP</span>
                  <span className="truncate text-xs text-muted-foreground">
                    Industrial Safety AI
                  </span>
                </div>
              </a>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Основное</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {mainNav.map((item) => (
                <SidebarMenuItem key={item.page}>
                  <SidebarMenuButton
                    isActive={activePage === item.page}
                    tooltip={item.title}
                    onClick={() => setActivePage(item.page)}
                  >
                    <item.icon />
                    <span>{item.title}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Промышленная безопасность</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {safetyNav.map((item) => (
                <SidebarMenuItem key={item.page}>
                  <SidebarMenuButton
                    isActive={activePage === item.page}
                    tooltip={item.title}
                    onClick={() => setActivePage(item.page)}
                  >
                    <item.icon />
                    <span>{item.title}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Данные</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {refNav.map((item) => (
                <SidebarMenuItem key={item.page}>
                  <SidebarMenuButton
                    isActive={activePage === item.page}
                    tooltip={item.title}
                    onClick={() => setActivePage(item.page)}
                  >
                    <item.icon />
                    <span>{item.title}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Система</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {bottomNav.map((item) => (
                <SidebarMenuItem key={item.page}>
                  <SidebarMenuButton
                    isActive={activePage === item.page}
                    tooltip={item.title}
                    onClick={() => setActivePage(item.page)}
                  >
                    <item.icon />
                    <span>{item.title}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg">
              <div className="bg-muted flex aspect-square size-8 items-center justify-center rounded-full text-xs font-semibold">
                АП
              </div>
              <div className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-semibold">Инженер ПБ</span>
                <span className="truncate text-xs text-muted-foreground">
                  engineer@isap.local
                </span>
              </div>
              <ChevronUp className="ml-auto size-4" />
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  )
}
