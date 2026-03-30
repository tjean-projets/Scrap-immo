import { useQuery } from '@tanstack/react-query'
import { getDashboardStats, getPipelineValue, getTerritoireDashboard, getScrapeRuns, triggerScrape } from '../api/client'
import type { DashboardStats, PipelineValue, TerritoireDashboard } from '../types'
import { KANBAN_COLUMNS } from '../types'
import { Zap, Users, MapPin, TrendingUp, RefreshCw } from 'lucide-react'
import { useState } from 'react'

export default function DashboardPage() {
  const [scraping, setScraping] = useState(false)
  const { data: stats } = useQuery<DashboardStats>({ queryKey: ['stats'], queryFn: getDashboardStats, refetchInterval: 15000 })
  const { data: pipeline } = useQuery<PipelineValue>({ queryKey: ['pipeline'], queryFn: () => getPipelineValue(5), refetchInterval: 15000 })
  const { data: territoire } = useQuery<TerritoireDashboard>({ queryKey: ['territoire'], queryFn: getTerritoireDashboard, refetchInterval: 15000 })
  const { data: runs } = useQuery({ queryKey: ['runs'], queryFn: getScrapeRuns, refetchInterval: 15000 })

  const handleScrape = async () => {
    setScraping(true)
    try { await triggerScrape() } catch {}
    setTimeout(() => setScraping(false), 5000)
  }

  return (
    <div className="p-6 space-y-6">
      {/* Top row - Key metrics */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
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
      <div className="grid grid-cols-4 gap-4">
        <KpiCard
          icon={<Users className="w-5 h-5 text-blue-400" />}
          label="Leads totaux"
          value={stats?.total_leads || 0}
          color="blue"
        />
        <KpiCard
          icon={<Zap className="w-5 h-5 text-amber-400" />}
          label="Leads 24h"
          value={territoire?.leads_24h || 0}
          color="amber"
        />
        <KpiCard
          icon={<TrendingUp className="w-5 h-5 text-emerald-400" />}
          label="CA Pipeline"
          value={`${(pipeline?.totaux.ca_potentiel || 0).toLocaleString('fr-FR')}\u20ac`}
          color="emerald"
        />
        <KpiCard
          icon={<MapPin className="w-5 h-5 text-purple-400" />}
          label="Zones exclusives"
          value={territoire?.zones_exclusives?.length || 0}
          color="purple"
        />
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Pipeline by status */}
        <div className="col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-white mb-4">Pipeline par statut</h3>
          <div className="space-y-3">
            {KANBAN_COLUMNS.filter(c => c.key !== 'archive').map(col => {
              const data = pipeline?.pipeline[col.key]
              const maxComm = Math.max(...Object.values(pipeline?.pipeline || {}).map(v => v.total_commission || 0), 1)
              const pct = data ? (data.total_commission / maxComm) * 100 : 0
              return (
                <div key={col.key} className="flex items-center gap-3">
                  <div className="w-32 text-xs text-slate-400 flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: col.color }} />
                    {col.label}
                  </div>
                  <div className="flex-1 bg-slate-800 rounded-full h-6 overflow-hidden">
                    <div
                      className="h-full rounded-full flex items-center px-2 text-[10px] text-white font-medium transition-all duration-500"
                      style={{ width: `${Math.max(pct, 2)}%`, backgroundColor: col.color + '80' }}
                    >
                      {data?.total_commission ? `${data.total_commission.toLocaleString('fr-FR')}€` : ''}
                    </div>
                  </div>
                  <span className="text-xs text-slate-500 w-8 text-right">{data?.count || 0}</span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Leads par site */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-white mb-4">Leads par source</h3>
          {stats?.by_site && Object.entries(stats.by_site).length > 0 ? (
            <div className="space-y-3">
              {Object.entries(stats.by_site).sort((a, b) => b[1] - a[1]).map(([site, count]) => (
                <div key={site} className="flex justify-between items-center">
                  <span className="text-sm text-slate-300 uppercase">{site}</span>
                  <span className="bg-slate-800 text-white px-3 py-1 rounded-lg text-sm font-medium">{count}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">Aucun lead pour l'instant</p>
          )}
        </div>
      </div>

      {/* Scrape runs history */}
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
                <th className="text-left py-2 px-3">Date</th>
              </tr>
            </thead>
            <tbody>
              {(runs || []).slice(0, 10).map((r: any) => (
                <tr key={r.id} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                  <td className="py-2 px-3 text-slate-300 uppercase">{r.site}</td>
                  <td className="py-2 px-3 text-slate-400">{r.postal_code}</td>
                  <td className="py-2 px-3 text-center">
                    <span className={`px-2 py-0.5 rounded text-xs ${r.status === 'success' ? 'bg-green-900/30 text-green-400' : r.status === 'error' ? 'bg-red-900/30 text-red-400' : 'bg-amber-900/30 text-amber-400'}`}>
                      {r.status}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-center text-slate-300">{r.listings_found}</td>
                  <td className="py-2 px-3 text-center text-emerald-400 font-medium">{r.listings_new}</td>
                  <td className="py-2 px-3 text-center text-slate-500">{r.listings_dedup}</td>
                  <td className="py-2 px-3 text-slate-500 text-xs">
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

function KpiCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: string | number; color: string }) {
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
