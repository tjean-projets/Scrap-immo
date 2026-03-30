import { useQuery } from '@tanstack/react-query'
import { getDashboardStats, getPipelineValue, getScrapeRuns, triggerScrape, getKanbanColumns } from '../api/client'
import type { DashboardStats, PipelineValue, KanbanColumnType } from '../types'
import { Zap, Users, TrendingUp, RefreshCw } from 'lucide-react'
import { useState } from 'react'

export default function DashboardPage() {
  const [scraping, setScraping] = useState(false)
  const { data: stats } = useQuery<DashboardStats>({ queryKey: ['stats'], queryFn: getDashboardStats, refetchInterval: 15000 })
  const { data: pipeline } = useQuery<PipelineValue>({ queryKey: ['pipeline'], queryFn: () => getPipelineValue(5), refetchInterval: 15000 })
  const { data: columns = [] } = useQuery<KanbanColumnType[]>({ queryKey: ['kanban-columns'], queryFn: getKanbanColumns })
  const { data: runs } = useQuery({ queryKey: ['runs'], queryFn: getScrapeRuns, refetchInterval: 15000 })

  const handleScrape = async () => {
    setScraping(true)
    try { await triggerScrape() } catch {}
    setTimeout(() => setScraping(false), 5000)
  }

  return (
    <div className="p-4 lg:p-6 space-y-4 lg:space-y-6">
      {/* Top row */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <h1 className="text-xl lg:text-2xl font-bold text-white">Dashboard</h1>
        <button
          onClick={handleScrape}
          disabled={scraping}
          className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-600 disabled:bg-slate-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${scraping ? 'animate-spin' : ''}`} />
          {scraping ? 'Scraping en cours...' : 'Lancer un scraping'}
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 lg:gap-4">
        <KpiCard
          icon={<Users className="w-5 h-5 text-blue-400" />}
          label="Leads totaux"
          value={stats?.total_leads || 0}
        />
        <KpiCard
          icon={<Zap className="w-5 h-5 text-amber-400" />}
          label="Nouveaux leads"
          value={stats?.by_status?.['Nouveau Lead'] || 0}
        />
        <KpiCard
          icon={<TrendingUp className="w-5 h-5 text-emerald-400" />}
          label="CA Pipeline"
          value={`${(pipeline?.totaux.ca_potentiel || 0).toLocaleString('fr-FR')}\u20ac`}
        />
      </div>

      {/* Pipeline par colonne — CA progression */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-white mb-4">CA Pipeline par avancement</h3>
        <div className="space-y-3">
          {columns.filter(c => !c.is_archive).map(col => {
            const data = pipeline?.pipeline[col.name]
            const maxComm = Math.max(
              ...columns.map(c => pipeline?.pipeline[c.name]?.total_commission || 0),
              1
            )
            const pct = data ? (data.total_commission / maxComm) * 100 : 0
            return (
              <div key={col.id} className="flex items-center gap-3">
                <div className="w-36 text-xs text-slate-400 flex items-center gap-2 flex-shrink-0">
                  <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: col.color }} />
                  <span className="truncate">{col.name}</span>
                </div>
                <div className="flex-1 bg-slate-800 rounded-full h-7 overflow-hidden">
                  <div
                    className="h-full rounded-full flex items-center px-3 text-[11px] text-white font-medium transition-all duration-500"
                    style={{ width: `${Math.max(pct, 2)}%`, backgroundColor: col.color + '80' }}
                  >
                    {data?.total_commission ? `${data.total_commission.toLocaleString('fr-FR')}\u20ac` : ''}
                  </div>
                </div>
                <span className="text-xs text-slate-500 w-8 text-right flex-shrink-0">{data?.count || 0}</span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Historique des scrapings */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-white mb-4">Historique des scrapings</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-500 text-xs border-b border-slate-800">
                <th className="text-left py-2 px-3">Site</th>
                <th className="text-left py-2 px-3">CP</th>
                <th className="text-center py-2 px-3">Status</th>
                <th className="text-center py-2 px-3">Trouvees</th>
                <th className="text-center py-2 px-3">Nouvelles</th>
                <th className="text-center py-2 px-3">Dedup</th>
                <th className="text-left py-2 px-3 hidden sm:table-cell">Date</th>
              </tr>
            </thead>
            <tbody>
              {(runs || []).slice(0, 10).map((r: any) => (
                <tr key={r.id} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                  <td className="py-2 px-3 text-slate-300 uppercase text-xs">{r.site}</td>
                  <td className="py-2 px-3 text-slate-400">{r.postal_code}</td>
                  <td className="py-2 px-3 text-center">
                    <span className={`px-2 py-0.5 rounded text-xs ${r.status === 'success' ? 'bg-green-900/30 text-green-400' : r.status === 'error' ? 'bg-red-900/30 text-red-400' : 'bg-amber-900/30 text-amber-400'}`}>
                      {r.status}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-center text-slate-300">{r.listings_found}</td>
                  <td className="py-2 px-3 text-center text-emerald-400 font-medium">{r.listings_new}</td>
                  <td className="py-2 px-3 text-center text-slate-500">{r.listings_dedup}</td>
                  <td className="py-2 px-3 text-slate-500 text-xs hidden sm:table-cell">
                    {r.started_at ? new Date(r.started_at).toLocaleString('fr-FR') : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {(!runs || runs.length === 0) && (
            <p className="text-center text-slate-500 py-4">Aucun scraping effectue</p>
          )}
        </div>
      </div>
    </div>
  )
}

function KpiCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <span className="text-xs text-slate-400">{label}</span>
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
    </div>
  )
}
