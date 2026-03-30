import type { Lead } from '../types'
import { Phone, MessageCircle, ExternalLink, Flame, TrendingDown, Clock } from 'lucide-react'

const urgencyColors: Record<string, string> = {
  froid: 'bg-slate-700 text-slate-300',
  tiede: 'bg-amber-900/50 text-amber-300',
  chaud: 'bg-orange-900/50 text-orange-300',
  tres_chaud: 'bg-red-900/50 text-red-300',
}

const priorityBadge: Record<string, string> = {
  critique: 'bg-red-500/20 text-red-400 border-red-500/30',
  haute: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  normale: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  basse: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
}

export default function LeadCard({ lead, onClick }: { lead: Lead; onClick: () => void }) {
  const l = lead.listing
  const commission = lead.commission_amount
  const urgLevel = lead.urgency?.level || 'froid'
  const urgScore = lead.urgency?.score || 0
  const priority = lead.strategic?.priority || 'basse'
  const priceGap = lead.price_gap?.gap_pct

  return (
    <div
      onClick={onClick}
      className="bg-slate-800/80 border border-slate-700 rounded-xl p-4 cursor-pointer hover:border-slate-600 hover:bg-slate-800 transition-all group"
    >
      {/* Header: Price + Commission */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="text-white font-semibold text-sm truncate max-w-[180px]">
            {l?.title || 'Sans titre'}
          </p>
          <p className="text-slate-400 text-xs mt-0.5">
            {l?.city || l?.postal_code} &bull; {l?.source_site?.toUpperCase()}
          </p>
        </div>
        {commission && commission > 0 && (
          <div className="text-right">
            <p className="text-emerald-400 font-bold text-lg leading-none">
              {commission.toLocaleString('fr-FR')}&euro;
            </p>
            <p className="text-emerald-600 text-[10px]">CA estim&eacute;</p>
          </div>
        )}
      </div>

      {/* Price + Surface */}
      <div className="flex gap-3 text-xs text-slate-300 mb-3">
        {l?.price && (
          <span className="bg-slate-700/50 px-2 py-1 rounded">
            {l.price.toLocaleString('fr-FR')}&euro;
          </span>
        )}
        {l?.surface_m2 && (
          <span className="bg-slate-700/50 px-2 py-1 rounded">
            {l.surface_m2}m&sup2;
          </span>
        )}
        {l?.nb_rooms && (
          <span className="bg-slate-700/50 px-2 py-1 rounded">
            {l.nb_rooms}p
          </span>
        )}
      </div>

      {/* Badges */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {/* Urgency */}
        <span className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full ${urgencyColors[urgLevel]}`}>
          <Flame className="w-3 h-3" />
          {urgScore}/100
        </span>

        {/* Priority */}
        <span className={`inline-flex items-center text-[10px] px-2 py-0.5 rounded-full border ${priorityBadge[priority]}`}>
          {priority}
        </span>

        {/* Price gap */}
        {priceGap !== null && priceGap !== undefined && (
          <span className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full ${
            priceGap > 10 ? 'bg-red-900/30 text-red-400' : priceGap < -5 ? 'bg-green-900/30 text-green-400' : 'bg-slate-700 text-slate-300'
          }`}>
            <TrendingDown className="w-3 h-3" />
            {priceGap > 0 ? '+' : ''}{priceGap?.toFixed(0)}%
          </span>
        )}

        {/* Days on market */}
        {lead.chronology?.days_on_market && (
          <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-slate-700 text-slate-300">
            <Clock className="w-3 h-3" />
            {lead.chronology.days_on_market}j
          </span>
        )}

        {lead.is_suspicious && (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-yellow-900/30 text-yellow-400 border border-yellow-500/20">
            suspect
          </span>
        )}
      </div>

      {/* IA Insight */}
      {lead.strategic?.angle && (
        <p className="text-[11px] text-slate-400 italic line-clamp-2 mb-3">
          {lead.strategic.angle.substring(0, 120)}...
        </p>
      )}

      {/* Quick actions */}
      <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
        {l?.seller_phone && (
          <a
            href={`tel:${l.seller_phone}`}
            onClick={e => e.stopPropagation()}
            className="flex items-center gap-1 text-[10px] bg-blue-500/10 text-blue-400 px-2 py-1 rounded-lg hover:bg-blue-500/20"
          >
            <Phone className="w-3 h-3" /> Appel
          </a>
        )}
        <a
          href={`https://wa.me/${l?.seller_phone?.replace(/\D/g, '')}`}
          target="_blank"
          onClick={e => e.stopPropagation()}
          className="flex items-center gap-1 text-[10px] bg-green-500/10 text-green-400 px-2 py-1 rounded-lg hover:bg-green-500/20"
        >
          <MessageCircle className="w-3 h-3" /> WhatsApp
        </a>
        <a
          href={l?.source_url}
          target="_blank"
          onClick={e => e.stopPropagation()}
          className="flex items-center gap-1 text-[10px] bg-slate-700 text-slate-300 px-2 py-1 rounded-lg hover:bg-slate-600"
        >
          <ExternalLink className="w-3 h-3" /> Annonce
        </a>
      </div>
    </div>
  )
}
