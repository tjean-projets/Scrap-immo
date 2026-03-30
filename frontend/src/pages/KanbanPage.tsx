import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getLeads, updateLeadStatus, getPipelineValue } from '../api/client'
import LeadCard from '../components/LeadCard'
import LeadDetail from './LeadDetail'
import type { Lead, PipelineValue } from '../types'
import { KANBAN_COLUMNS } from '../types'

export default function KanbanPage() {
  const queryClient = useQueryClient()
  const [selectedLead, setSelectedLead] = useState<number | null>(null)

  const { data: leadsData } = useQuery({
    queryKey: ['leads'],
    queryFn: () => getLeads({ per_page: 100 }),
    refetchInterval: 30000,
  })

  const { data: pipeline } = useQuery<PipelineValue>({
    queryKey: ['pipeline'],
    queryFn: () => getPipelineValue(5),
    refetchInterval: 30000,
  })

  const moveMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      updateLeadStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] })
      queryClient.invalidateQueries({ queryKey: ['pipeline'] })
    },
  })

  const leads: Lead[] = leadsData?.items || []

  const leadsByStatus = KANBAN_COLUMNS.reduce(
    (acc, col) => {
      acc[col.key] = leads.filter(l => l.status === col.key)
      return acc
    },
    {} as Record<string, Lead[]>
  )

  const handleDrop = (leadId: number, newStatus: string) => {
    moveMutation.mutate({ id: leadId, status: newStatus })
  }

  if (selectedLead) {
    return <LeadDetail leadId={selectedLead} onBack={() => setSelectedLead(null)} />
  }

  return (
    <div className="p-6">
      {/* Pipeline Value Header */}
      {pipeline && (
        <div className="mb-6 bg-gradient-to-r from-emerald-900/20 to-slate-900 border border-emerald-800/30 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-400">Pipeline Total</p>
              <p className="text-3xl font-bold text-emerald-400">
                {pipeline.totaux.ca_potentiel.toLocaleString('fr-FR')}&euro;
              </p>
              <p className="text-xs text-slate-500">
                CA potentiel sur {pipeline.totaux.leads_actifs} leads &bull; taux {pipeline.totaux.taux_applique}%
              </p>
            </div>
            <div className="text-right">
              <p className="text-sm text-slate-400">Valeur biens</p>
              <p className="text-xl font-semibold text-white">
                {pipeline.totaux.valeur_biens.toLocaleString('fr-FR')}&euro;
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Kanban Board */}
      <div className="flex gap-4 overflow-x-auto pb-4" style={{ minHeight: 'calc(100vh - 220px)' }}>
        {KANBAN_COLUMNS.map(col => {
          const colLeads = leadsByStatus[col.key] || []
          const colPipeline = pipeline?.pipeline[col.key]

          return (
            <div
              key={col.key}
              className="flex-shrink-0 w-80 bg-slate-900/50 rounded-xl border border-slate-800"
              onDragOver={e => e.preventDefault()}
              onDrop={e => {
                const leadId = parseInt(e.dataTransfer.getData('leadId'))
                if (leadId) handleDrop(leadId, col.key)
              }}
            >
              {/* Column Header */}
              <div className="p-4 border-b border-slate-800">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: col.color }} />
                    <span className="font-medium text-sm text-white">{col.label}</span>
                    <span className="bg-slate-800 text-slate-400 text-xs px-2 py-0.5 rounded-full">
                      {colLeads.length}
                    </span>
                  </div>
                </div>
                {colPipeline && colPipeline.total_commission > 0 && (
                  <p className="text-xs text-emerald-400 mt-1 font-medium">
                    {colPipeline.total_commission.toLocaleString('fr-FR')}&euro; CA
                  </p>
                )}
              </div>

              {/* Cards */}
              <div className="p-3 space-y-3 max-h-[calc(100vh-300px)] overflow-y-auto">
                {colLeads.map(lead => (
                  <div
                    key={lead.id}
                    draggable
                    onDragStart={e => e.dataTransfer.setData('leadId', String(lead.id))}
                  >
                    <LeadCard lead={lead} onClick={() => setSelectedLead(lead.id)} />
                  </div>
                ))}
                {colLeads.length === 0 && (
                  <p className="text-center text-slate-600 text-xs py-8">
                    Aucun lead
                  </p>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
