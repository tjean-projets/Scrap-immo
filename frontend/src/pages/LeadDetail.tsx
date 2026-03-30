import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getLead, updateLead, exportLeadsCSV } from '../api/client'
import type { Lead } from '../types'
import { ArrowLeft, Phone, MessageCircle, ExternalLink, Flame, TrendingDown, Clock, Copy, Check, Pencil, Download } from 'lucide-react'
import { useState } from 'react'

export default function LeadDetail({ leadId, onBack }: { leadId: number; onBack: () => void }) {
  const queryClient = useQueryClient()
  const { data: lead, isLoading } = useQuery<Lead>({
    queryKey: ['lead', leadId],
    queryFn: () => getLead(leadId),
  })

  const [editingSms, setEditingSms] = useState(false)
  const [smsText, setSmsText] = useState('')
  const [copied, setCopied] = useState(false)

  const updateMutation = useMutation({
    mutationFn: (data: { strategic_sms?: string; notes?: string }) =>
      updateLead(leadId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lead', leadId] })
      setEditingSms(false)
    },
  })

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const handleSaveSms = () => {
    updateMutation.mutate({ strategic_sms: smsText })
  }

  if (isLoading || !lead) {
    return <div className="p-8 text-slate-400">Chargement...</div>
  }

  const l = lead.listing

  return (
    <div className="p-3 lg:p-6 max-w-4xl mx-auto">
      {/* Back button */}
      <button onClick={onBack} className="flex items-center gap-2 text-slate-400 hover:text-white mb-4 lg:mb-6 text-sm">
        <ArrowLeft className="w-4 h-4" /> Retour au Kanban
      </button>

      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 lg:p-6 mb-4 lg:mb-6">
        <div className="flex flex-col sm:flex-row justify-between items-start gap-3">
          <div className="min-w-0">
            <h2 className="text-xl lg:text-2xl font-bold text-white truncate">{l?.title}</h2>
            <p className="text-slate-400 mt-1">
              {l?.city || l?.postal_code} &bull; {l?.source_site?.toUpperCase()} &bull; {l?.property_type}
            </p>
          </div>
          <div className="text-right">
            <p className="text-3xl font-bold text-white">
              {l?.price?.toLocaleString('fr-FR')}&euro;
            </p>
            {lead.commission_amount && (
              <p className="text-xl font-bold text-emerald-400">
                {lead.commission_amount.toLocaleString('fr-FR')}&euro; CA
              </p>
            )}
          </div>
        </div>

        {/* Quick stats */}
        <div className="flex gap-4 mt-4 flex-wrap">
          {l?.surface_m2 && <Stat label="Surface" value={`${l.surface_m2}m²`} />}
          {l?.nb_rooms && <Stat label="Pieces" value={String(l.nb_rooms)} />}
          {l?.price && l?.surface_m2 && (
            <Stat label="Prix/m²" value={`${Math.round(l.price / l.surface_m2).toLocaleString('fr-FR')}€`} />
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-wrap gap-2 lg:gap-3 mt-4">
          {l?.seller_phone && (
            <a href={`tel:${l.seller_phone}`} className="flex items-center gap-2 bg-blue-500/10 text-blue-400 px-4 py-2 rounded-lg hover:bg-blue-500/20 text-sm">
              <Phone className="w-4 h-4" /> {l.seller_phone}
            </a>
          )}
          <a href={`https://wa.me/${l?.seller_phone?.replace(/\D/g, '')}`} target="_blank" className="flex items-center gap-2 bg-green-500/10 text-green-400 px-4 py-2 rounded-lg hover:bg-green-500/20 text-sm">
            <MessageCircle className="w-4 h-4" /> WhatsApp
          </a>
          <a href={l?.source_url} target="_blank" className="flex items-center gap-2 bg-slate-700 text-slate-300 px-4 py-2 rounded-lg hover:bg-slate-600 text-sm">
            <ExternalLink className="w-4 h-4" /> Voir l'annonce
          </a>
        </div>

        {/* Alternate URLs - cross-site links */}
        {l?.alternate_urls && l.alternate_urls.length > 0 && (
          <div className="mt-4 bg-slate-800/50 rounded-lg p-3">
            <p className="text-xs text-slate-500 mb-2">Aussi disponible sur :</p>
            <div className="flex flex-wrap gap-2">
              <a href={l.source_url} target="_blank" className="inline-flex items-center gap-1 text-xs bg-blue-500/10 text-blue-400 px-2.5 py-1 rounded-lg hover:bg-blue-500/20">
                <ExternalLink className="w-3 h-3" /> {l.source_site?.toUpperCase()}
              </a>
              {l.alternate_urls.map((alt, i) => (
                <a key={i} href={alt.url} target="_blank" className="inline-flex items-center gap-1 text-xs bg-purple-500/10 text-purple-400 px-2.5 py-1 rounded-lg hover:bg-purple-500/20">
                  <ExternalLink className="w-3 h-3" /> {alt.site?.toUpperCase()}
                </a>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6">
        {/* Analyses */}
        <div className="space-y-4">
          {/* Urgency */}
          <AnalysisCard title="Score d'Urgence" icon={<Flame className="w-5 h-5 text-orange-400" />}>
            <div className="flex items-center gap-3 mb-2">
              <div className="text-4xl font-bold text-white">{lead.urgency?.score || 0}</div>
              <div className="text-sm text-slate-400">/100</div>
              <span className={`px-2 py-1 rounded text-xs font-medium ${
                (lead.urgency?.level === 'tres_chaud') ? 'bg-red-500/20 text-red-400' :
                (lead.urgency?.level === 'chaud') ? 'bg-orange-500/20 text-orange-400' :
                (lead.urgency?.level === 'tiede') ? 'bg-amber-500/20 text-amber-400' :
                'bg-slate-700 text-slate-400'
              }`}>
                {lead.urgency?.level}
              </span>
            </div>
            {lead.urgency?.factors?.map((f, i) => (
              <p key={i} className="text-xs text-slate-400">&bull; {f}</p>
            ))}
          </AnalysisCard>

          {/* Price Gap */}
          <AnalysisCard title="Ecart de Prix" icon={<TrendingDown className="w-5 h-5 text-blue-400" />}>
            {lead.price_gap?.gap_pct !== null && lead.price_gap?.gap_pct !== undefined ? (
              <>
                <div className={`text-3xl font-bold ${
                  lead.price_gap.gap_pct > 10 ? 'text-red-400' :
                  lead.price_gap.gap_pct < -5 ? 'text-green-400' : 'text-white'
                }`}>
                  {lead.price_gap.gap_pct > 0 ? '+' : ''}{lead.price_gap.gap_pct.toFixed(1)}%
                </div>
                {lead.price_gap.price_m2_market && (
                  <p className="text-xs text-slate-400 mt-1">Marche: {lead.price_gap.price_m2_market.toLocaleString('fr-FR')}€/m²</p>
                )}
                <p className="text-xs text-slate-400 mt-2">{lead.price_gap.comment}</p>
              </>
            ) : (
              <p className="text-sm text-slate-500">Donnees insuffisantes</p>
            )}
          </AnalysisCard>

          {/* Chronology */}
          <AnalysisCard title="Chronologie" icon={<Clock className="w-5 h-5 text-purple-400" />}>
            <span className={`inline-block px-2 py-1 rounded text-xs font-medium mb-2 ${
              lead.chronology?.type === 'BAISSE_PRIX' ? 'bg-green-500/20 text-green-400' :
              lead.chronology?.type === 'REPUBLICATION' ? 'bg-amber-500/20 text-amber-400' :
              'bg-blue-500/20 text-blue-400'
            }`}>
              {lead.chronology?.type || 'NOUVELLE'}
            </span>
            {lead.chronology?.days_on_market && (
              <p className="text-sm text-slate-300">{lead.chronology.days_on_market} jours en vente</p>
            )}
            <p className="text-xs text-slate-400 mt-1">{lead.chronology?.comment}</p>
          </AnalysisCard>
        </div>

        {/* Strategy + Description */}
        <div className="space-y-4">
          {/* Strategic Advice */}
          <AnalysisCard title="Conseil Strategique" icon={<span className="text-lg">&#x1F3AF;</span>}>
            <span className={`inline-block px-2 py-1 rounded text-xs font-medium mb-3 ${
              lead.strategic?.priority === 'critique' ? 'bg-red-500/20 text-red-400' :
              lead.strategic?.priority === 'haute' ? 'bg-orange-500/20 text-orange-400' :
              'bg-blue-500/20 text-blue-400'
            }`}>
              Priorite: {lead.strategic?.priority}
            </span>
            <p className="text-sm text-slate-300 leading-relaxed">{lead.strategic?.angle}</p>
          </AnalysisCard>

          {/* SMS Script — editable */}
          <AnalysisCard title="Script SMS / WhatsApp" icon={<MessageCircle className="w-5 h-5 text-green-400" />}>
            {editingSms ? (
              <div className="space-y-2">
                <textarea
                  value={smsText}
                  onChange={e => setSmsText(e.target.value)}
                  rows={5}
                  className="w-full bg-slate-800 border border-slate-600 rounded-lg p-3 text-sm text-slate-300 leading-relaxed focus:border-emerald-500 focus:outline-none resize-none"
                />
                <div className="flex gap-2">
                  <button
                    onClick={handleSaveSms}
                    disabled={updateMutation.isPending}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500 hover:bg-emerald-600 disabled:bg-slate-700 text-white rounded-lg text-xs font-medium transition-colors"
                  >
                    <Check className="w-3.5 h-3.5" />
                    {updateMutation.isPending ? 'Sauvegarde...' : 'Sauvegarder'}
                  </button>
                  <button
                    onClick={() => setEditingSms(false)}
                    className="px-3 py-1.5 bg-slate-800 text-slate-400 hover:bg-slate-700 rounded-lg text-xs transition-colors"
                  >
                    Annuler
                  </button>
                </div>
              </div>
            ) : (
              <div className="bg-slate-800 rounded-lg p-3 text-sm text-slate-300 leading-relaxed relative group">
                {lead.strategic?.sms_script ? (
                  <p className="pr-16 whitespace-pre-wrap">{lead.strategic.sms_script}</p>
                ) : (
                  <p className="text-slate-500 italic">Aucun script. Cliquez sur modifier pour en créer un.</p>
                )}
                <div className="absolute top-2 right-2 flex gap-1">
                  <button
                    onClick={() => {
                      setSmsText(lead.strategic?.sms_script || '')
                      setEditingSms(true)
                    }}
                    className="p-1 hover:bg-slate-700 rounded transition-colors"
                    title="Modifier"
                  >
                    <Pencil className="w-4 h-4 text-slate-500 hover:text-slate-300" />
                  </button>
                  {lead.strategic?.sms_script && (
                    <button
                      onClick={() => handleCopy(lead.strategic?.sms_script || '')}
                      className="p-1 hover:bg-slate-700 rounded transition-colors"
                      title="Copier"
                    >
                      {copied
                        ? <Check className="w-4 h-4 text-emerald-400" />
                        : <Copy className="w-4 h-4 text-slate-500 hover:text-slate-300" />
                      }
                    </button>
                  )}
                </div>
              </div>
            )}
            {/* Quick send via WhatsApp */}
            {lead.strategic?.sms_script && l?.seller_phone && (
              <a
                href={`https://wa.me/${l.seller_phone.replace(/\D/g, '')}?text=${encodeURIComponent(lead.strategic.sms_script)}`}
                target="_blank"
                className="mt-2 inline-flex items-center gap-2 bg-green-500/10 text-green-400 hover:bg-green-500/20 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
              >
                <MessageCircle className="w-3.5 h-3.5" />
                Envoyer via WhatsApp
              </a>
            )}
          </AnalysisCard>

          {/* Description */}
          {l?.description && (
            <AnalysisCard title="Description de l'annonce" icon={<span className="text-lg">&#x1F4DD;</span>}>
              <p className="text-sm text-slate-400 leading-relaxed whitespace-pre-wrap">
                {l.description.substring(0, 500)}
                {l.description.length > 500 ? '...' : ''}
              </p>
            </AnalysisCard>
          )}
        </div>
      </div>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-slate-800 px-3 py-2 rounded-lg">
      <p className="text-[10px] text-slate-500 uppercase">{label}</p>
      <p className="text-sm font-semibold text-white">{value}</p>
    </div>
  )
}

function AnalysisCard({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-3">
        {icon}
        <h3 className="text-sm font-semibold text-white">{title}</h3>
      </div>
      {children}
    </div>
  )
}
