import { Metadata } from 'next'
import { DashboardLayout } from '@/components/layout/dashboard-layout'
import { StatsCards } from '@/components/dashboard/stats-cards'
import { LeadChart } from '@/components/dashboard/lead-chart'
import { RecentLeads } from '@/components/dashboard/recent-leads'
import { AutonomyLevels } from '@/components/dashboard/autonomy-levels'

export const metadata: Metadata = {
  title: 'Dashboard - AIDA-CRM',
  description: 'Overview of your CRM performance and lead management',
}

export default function DashboardPage() {
  return (
    <DashboardLayout>
      <div className="flex-1 space-y-4 p-8 pt-6">
        <div className="flex items-center justify-between space-y-2">
          <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
          <div className="flex items-center space-x-2">
            <span className="text-sm text-muted-foreground">
              Welcome to AIDA-CRM v0.2
            </span>
          </div>
        </div>

        {/* Stats Overview */}
        <StatsCards />

        {/* Charts and Analytics */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
          <div className="col-span-4">
            <LeadChart />
          </div>
          <div className="col-span-3">
            <AutonomyLevels />
          </div>
        </div>

        {/* Recent Activity */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-8">
          <div className="col-span-5">
            <RecentLeads />
          </div>
          <div className="col-span-3">
            {/* Placeholder for additional widgets */}
            <div className="rounded-xl border bg-card text-card-foreground shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
              <div className="space-y-2">
                <button className="w-full text-left p-2 rounded hover:bg-muted text-sm">
                  📧 Send Campaign Email
                </button>
                <button className="w-full text-left p-2 rounded hover:bg-muted text-sm">
                  📊 Generate Report
                </button>
                <button className="w-full text-left p-2 rounded hover:bg-muted text-sm">
                  🤖 Configure Autonomy
                </button>
                <button className="w-full text-left p-2 rounded hover:bg-muted text-sm">
                  🎯 Create Campaign
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}