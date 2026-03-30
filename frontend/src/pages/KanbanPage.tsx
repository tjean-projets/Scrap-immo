import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getLeads, updateLeadStatus, getPipelineValue, getKanbanColumns, createKanbanColumn, updateKanbanColumn, deleteKanbanColumn } from '../api/client'
import LeadCard from '../components/LeadCard'
import LeadDetail from './LeadDetail'
import type { Lead, PipelineValue, KanbanColumnType } from '../types'
import { Filter, SortAsc, Plus, Pencil, Trash2, Check, X } from 'lucide-react'

type SortKey = 'date' | 'price' | 'urgency' | 'commission'
type FilterPriority = 'all' | 'critique' | 'haute' | 'normale' | 'basse'

export default function KanbanPage() {
  const queryClient = useQueryClient()
  const [selectedLead, setSelectedLead] = useState<number | null>(null)
  const [sortBy, setSortBy] = useState<SortKey>('date')
  const [filterPriority, setFilterPriority] = useState<FilterPriority>('all')
  const [editingCol, setEditingCol] = useState<number | null>(null)
  const [editName, setEditName] = useState('')
  const [showNewCol, setShowNewCol] = useState(false)
  const [newColName, setNewColName] = useState('')

  // Data
  const { data: columns = [] } = useQuery<KanbanColumnType[]>({
    queryKey: ['kanban-columns'],
    queryFn: getKanbanColumns,
  })

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

  const createColMutation = useMutation({
    mutationFn: (data: { name: string; color: string }) => createKanbanColumn(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['kanban-columns'] }),
  })

  const updateColMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { name?: string } }) => updateKanbanColumn(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kanban-columns'] })
      // Also update leads that had the old column name
      queryClient.invalidateQueries({ queryKey: ['leads'] })
    },
  })

  const deleteColMutation = useMutation({
    mutationFn: (id: number) => deleteKanbanColumn(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['kanban-columns'] }),
  })

  const leads: Lead[] = leadsData?.items || []

  // Filter
  const filteredLeads = leads.filter(l => {
    if (filterPriority !== 'all' && l.strategic?.priority !== filterPriority) return false
    return true
  })

  // Sort
  const sortLeads = (arr: Lead[]) => {
    return [...arr].sort((a, b) => {
      switch (sortBy) {
        case 'price': return (b.listing?.price || 0) - (a.listing?.price || 0)
        case 'urgency': return (b.urgency?.score || 0) - (a.urgency?.score || 0)
        case 'commission': return (b.commission_amount || 0) - (a.commission_amount || 0)
        default: return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      }
    })
  }

  const leadsByStatus = columns.reduce(
    (acc, col) => {
      acc[col.name] = sortLeads(filteredLeads.filter(l => l.status === col.name))
      return acc
    },
    {} as Record<string, Lead[]>
  )

  const handleDrop = (leadId: number, newStatus: string) => {
    moveMutation.mutate({ id: leadId, status: newStatus })
  }

  const handleRenameCol = (col: KanbanColumnType) => {
    if (editName.trim() && editName !== col.name) {
      // Update column name + update all leads with old name
      updateColMutation.mutate({ id: col.id, data: { name: editName.trim() } })
    }
    setEditingCol(null)
  }

  const handleAddCol = () => {
    if (newColName.trim()) {
      const colors = ['#3b82f6', '#f59e0b', '#8b5cf6', '#10b981', '#ef4444', '#06b6d4', '#ec4899']
      const color = colors[columns.length % colors.length]
      createColMutation.mutate({ name: newColName.trim(), color })
      setNewColName('')
      setShowNewCol(false)
    }
  }

  if (selectedLead) {
    return <LeadDetail leadId={selectedLead} onBack={() => setSelectedLead(null)} />
  }

  return (
    <div className="p-3 lg:p-6">
      {/* Pipeline Value Header */}
      {pipeline && (
        <div className="mb-4 lg:mb-6 bg-gradient-to-r from-emerald-900/20 to-slate-900 border border-emerald-800/30 rounded-xl p-3 lg:p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs lg:text-sm text-slate-400">Pipeline Total</p>
              <p className="text-2xl lg:text-3xl font-bold text-emerald-400">
                {pipeline.totaux.ca_potentiel.toLocaleString('fr-FR')}&euro;
              </p>
              <p className="text-[10px] lg:text-xs text-slate-500">
                CA potentiel sur {pipeline.totaux.leads_actifs} leads
              </p>
            </div>
            <div className="text-right hidden sm:block">
              <p className="text-sm text-slate-400">Valeur biens</p>
              <p className="text-xl font-semibold text-white">
                {pipeline.totaux.valeur_biens.toLocaleString('fr-FR')}&euro;
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Filters bar */}
      <div className="mb-3 lg:mb-4 flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-1.5 text-xs text-slate-400">
          <Filter className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Priorite:</span>
        </div>
        {(['all', 'critique', 'haute', 'normale', 'basse'] as const).map(p => (
          <button
            key={p}
            onClick={() => setFilterPriority(p)}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
              filterPriority === p
                ? p === 'critique' ? 'bg-red-500/20 text-red-400'
                : p === 'haute' ? 'bg-orange-500/20 text-orange-400'
                : p === 'all' ? 'bg-slate-700 text-white'
                : 'bg-blue-500/20 text-blue-400'
                : 'bg-slate-800/50 text-slate-500 hover:text-slate-300'
            }`}
          >
            {p === 'all' ? 'Tous' : p}
          </button>
        ))}

        <div className="w-px h-5 bg-slate-700 mx-1 hidden sm:block" />

        <div className="flex items-center gap-1.5 text-xs text-slate-400">
          <SortAsc className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Tri:</span>
        </div>
        {([['date', 'Date'], ['commission', 'CA'], ['urgency', 'Urgence'], ['price', 'Prix']] as const).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setSortBy(key as SortKey)}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
              sortBy === key
                ? 'bg-emerald-500/20 text-emerald-400'
                : 'bg-slate-800/50 text-slate-500 hover:text-slate-300'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Kanban Board */}
      <div className="flex gap-3 lg:gap-4 overflow-x-auto pb-4 snap-x snap-mandatory" style={{ minHeight: 'calc(100vh - 280px)' }}>
        {columns.map(col => {
          const colLeads = leadsByStatus[col.name] || []
          const colPipeline = pipeline?.pipeline[col.name]
          const isEditing = editingCol === col.id

          return (
            <div
              key={col.id}
              className="flex-shrink-0 w-72 lg:w-80 snap-start bg-slate-900/50 rounded-xl border border-slate-800"
              onDragOver={e => e.preventDefault()}
              onDrop={e => {
                const leadId = parseInt(e.dataTransfer.getData('leadId'))
                if (leadId) handleDrop(leadId, col.name)
              }}
            >
              {/* Column Header */}
              <div className="p-3 lg:p-4 border-b border-slate-800">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: col.color }} />
                    {isEditing ? (
                      <div className="flex items-center gap-1 flex-1">
                        <input
                          value={editName}
                          onChange={e => setEditName(e.target.value)}
                          onKeyDown={e => e.key === 'Enter' && handleRenameCol(col)}
                          className="bg-slate-800 border border-slate-600 rounded px-2 py-0.5 text-sm text-white flex-1 min-w-0 focus:outline-none focus:border-emerald-500"
                          autoFocus
                        />
                        <button onClick={() => handleRenameCol(col)} className="text-emerald-400 hover:text-emerald-300">
                          <Check className="w-3.5 h-3.5" />
                        </button>
                        <button onClick={() => setEditingCol(null)} className="text-slate-500 hover:text-slate-300">
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ) : (
                      <>
                        <span className="font-medium text-sm text-white truncate">{col.name}</span>
                        <span className="bg-slate-800 text-slate-400 text-xs px-2 py-0.5 rounded-full flex-shrink-0">
                          {colLeads.length}
                        </span>
                      </>
                    )}
                  </div>
                  {!isEditing && (
                    <div className="flex items-center gap-1 ml-2">
                      <button
                        onClick={() => { setEditingCol(col.id); setEditName(col.name) }}
                        className="p-1 text-slate-600 hover:text-slate-300 transition-colors"
                        title="Renommer"
                      >
                        <Pencil className="w-3 h-3" />
                      </button>
                      {!col.is_default && (
                        <button
                          onClick={() => deleteColMutation.mutate(col.id)}
                          className="p-1 text-slate-600 hover:text-red-400 transition-colors"
                          title="Supprimer"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  )}
                </div>
                {colPipeline && colPipeline.total_commission > 0 && (
                  <p className="text-xs text-emerald-400 mt-1 font-medium">
                    {colPipeline.total_commission.toLocaleString('fr-FR')}&euro; CA
                  </p>
                )}
              </div>

              {/* Cards */}
              <div className="p-3 space-y-3 max-h-[calc(100vh-350px)] overflow-y-auto">
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

        {/* Add column button */}
        <div className="flex-shrink-0 w-72 lg:w-80 snap-start">
          {showNewCol ? (
            <div className="bg-slate-900/50 rounded-xl border border-slate-800 p-4">
              <input
                value={newColName}
                onChange={e => setNewColName(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleAddCol()}
                placeholder="Nom de la colonne"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none mb-3"
                autoFocus
              />
              <div className="flex gap-2">
                <button onClick={handleAddCol} className="flex-1 bg-emerald-500 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-emerald-600">
                  Creer
                </button>
                <button onClick={() => setShowNewCol(false)} className="px-3 py-1.5 bg-slate-800 text-slate-400 rounded-lg text-xs hover:bg-slate-700">
                  Annuler
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setShowNewCol(true)}
              className="w-full h-24 border-2 border-dashed border-slate-800 rounded-xl flex items-center justify-center gap-2 text-slate-600 hover:text-slate-400 hover:border-slate-700 transition-colors"
            >
              <Plus className="w-5 h-5" />
              <span className="text-sm">Ajouter une colonne</span>
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
