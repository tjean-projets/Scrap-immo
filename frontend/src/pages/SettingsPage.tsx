import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getSettings, updateSettings, getCommissionConfig, updateCommissionConfig } from '../api/client'
import { Save, Plus, X, Clock, MapPin, Globe, Euro, Trash2 } from 'lucide-react'

interface CommissionTier {
  min: number
  max: number | null
  rate: number
}

export default function SettingsPage() {
  const queryClient = useQueryClient()
  const { data: settings } = useQuery({ queryKey: ['settings'], queryFn: getSettings })

  const [postalCodes, setPostalCodes] = useState<string[]>([])
  const [hours, setHours] = useState<number[]>([])
  const [sites, setSites] = useState<string[]>([])
  const [newCP, setNewCP] = useState('')
  const [saved, setSaved] = useState(false)
  const [saveError, setSaveError] = useState('')

  // Commission state
  const [commissionType, setCommissionType] = useState<'fixed' | 'progressive'>('fixed')
  const [fixedRate, setFixedRate] = useState(5.0)
  const [tiers, setTiers] = useState<CommissionTier[]>([
    { min: 0, max: 100000, rate: 7.0 },
    { min: 100000, max: 300000, rate: 5.0 },
    { min: 300000, max: 500000, rate: 4.0 },
    { min: 500000, max: null, rate: 3.0 },
  ])

  useEffect(() => {
    if (settings) {
      setPostalCodes(settings.postal_codes || [])
      setHours(settings.schedule_hours || [])
      setSites(settings.enabled_sites || [])
    }
  }, [settings])

  // Load commission config
  useEffect(() => {
    getCommissionConfig().then(r => {
      if (r.commission_type) setCommissionType(r.commission_type)
      if (r.commission_rate) setFixedRate(r.commission_rate)
      if (r.commission_tiers) setTiers(r.commission_tiers)
    }).catch(() => {})
  }, [])

  const saveAll = async () => {
    setSaveError('')
    try {
      await updateSettings({
        postal_codes: postalCodes,
        schedule_hours: hours,
        enabled_sites: sites,
      })
      try {
        await updateCommissionConfig({
          commission_type: commissionType,
          commission_rate: fixedRate,
          commission_tiers: commissionType === 'progressive' ? tiers : null,
        })
      } catch {}
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch {
      setSaveError('Erreur de sauvegarde — vérifiez que le backend est démarré.')
    }
  }

  const addCP = () => {
    const cp = newCP.trim()
    if (cp && /^\d{5}$/.test(cp) && !postalCodes.includes(cp)) {
      setPostalCodes([...postalCodes, cp])
      setNewCP('')
    }
  }

  const addTier = () => {
    const lastTier = tiers[tiers.length - 1]
    const newMin = lastTier?.max || (lastTier?.min || 0) + 100000
    // Set previous tier's max if it was null
    if (lastTier && lastTier.max === null) {
      const updated = [...tiers]
      updated[updated.length - 1] = { ...lastTier, max: newMin }
      setTiers([...updated, { min: newMin, max: null, rate: 3.0 }])
    } else {
      setTiers([...tiers, { min: newMin, max: null, rate: 3.0 }])
    }
  }

  const updateTier = (idx: number, field: keyof CommissionTier, value: number | null) => {
    const updated = [...tiers]
    updated[idx] = { ...updated[idx], [field]: value }
    setTiers(updated)
  }

  const removeTier = (idx: number) => {
    if (tiers.length <= 1) return
    const updated = tiers.filter((_, i) => i !== idx)
    // Set last tier max to null (illimite)
    if (updated.length > 0) {
      updated[updated.length - 1] = { ...updated[updated.length - 1], max: null }
    }
    setTiers(updated)
  }

  const availableSites = [
    { key: 'pap', name: 'PAP.fr', desc: '100% particuliers' },
    { key: 'entreparticuliers', name: 'Entreparticuliers.com', desc: '100% particuliers' },
    { key: 'paruvendu', name: 'ParuVendu.fr', desc: 'Filtrage pro/particulier' },
    { key: 'leboncoin', name: 'Leboncoin.fr', desc: 'Filtrage pro, interception API' },
    { key: 'bienici', name: "Bien'ici", desc: 'Filtrage pro, interception API' },
    { key: 'seloger', name: 'SeLoger.fr', desc: 'Filtrage pro, Datadome' },
    { key: 'avendrealouer', name: 'AVendreALouer.fr', desc: 'Filtrage pro/particulier' },
    { key: 'logicimmo', name: 'Logic-Immo.com', desc: 'Filtrage pro/particulier' },
  ]

  // Compute example commission
  const examplePrice = 300000
  let exampleCommission = 0
  if (commissionType === 'fixed') {
    exampleCommission = Math.round(examplePrice * fixedRate / 100)
  } else {
    let remaining = examplePrice
    for (const tier of tiers) {
      const tierMax = tier.max ?? Infinity
      const tranche = Math.min(remaining, tierMax - tier.min)
      if (tranche <= 0) break
      exampleCommission += Math.round(tranche * tier.rate / 100)
      remaining -= tranche
      if (remaining <= 0) break
    }
  }

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Parametres</h1>
        <div className="flex items-center gap-3">
          {saveError && (
            <p className="text-xs text-red-400">{saveError}</p>
          )}
          <button
            onClick={saveAll}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              saved ? 'bg-green-500 text-white' : 'bg-emerald-500 hover:bg-emerald-600 text-white'
            }`}
          >
            <Save className="w-4 h-4" />
            {saved ? 'Enregistre !' : 'Enregistrer'}
          </button>
        </div>
      </div>

      {/* === COMMISSION === */}
      <Section icon={<Euro className="w-5 h-5 text-emerald-400" />} title="Bareme de commission">
        {/* Toggle type */}
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setCommissionType('fixed')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              commissionType === 'fixed'
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
            }`}
          >
            Taux fixe
          </button>
          <button
            onClick={() => setCommissionType('progressive')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              commissionType === 'progressive'
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
            }`}
          >
            Bareme progressif
          </button>
        </div>

        {commissionType === 'fixed' ? (
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Taux de commission (%)</label>
            <div className="flex items-center gap-3">
              <input
                type="number"
                value={fixedRate}
                onChange={e => setFixedRate(parseFloat(e.target.value) || 0)}
                min={0}
                max={100}
                step={0.1}
                className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white w-24 focus:border-emerald-500 focus:outline-none"
              />
              <span className="text-slate-400 text-sm">%</span>
              <span className="text-xs text-slate-500 ml-4">
                Ex: bien a 300 000{'\u20ac'} = <span className="text-emerald-400 font-medium">{exampleCommission.toLocaleString('fr-FR')}{'\u20ac'} CA</span>
              </span>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {/* Tiers table */}
            <div className="bg-slate-800/50 rounded-lg overflow-hidden">
              <div className="grid grid-cols-[1fr_1fr_80px_40px] gap-2 px-3 py-2 text-xs text-slate-500 border-b border-slate-700">
                <span>De</span>
                <span>Jusqu'a</span>
                <span>Taux</span>
                <span></span>
              </div>
              {tiers.map((tier, idx) => (
                <div key={idx} className="grid grid-cols-[1fr_1fr_80px_40px] gap-2 px-3 py-2 items-center border-b border-slate-800/50">
                  <div className="flex items-center gap-1">
                    <input
                      type="number"
                      value={tier.min}
                      onChange={e => updateTier(idx, 'min', parseInt(e.target.value) || 0)}
                      className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm text-white w-full focus:border-emerald-500 focus:outline-none"
                    />
                    <span className="text-slate-500 text-xs">{'\u20ac'}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    {tier.max !== null ? (
                      <>
                        <input
                          type="number"
                          value={tier.max}
                          onChange={e => updateTier(idx, 'max', parseInt(e.target.value) || 0)}
                          className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm text-white w-full focus:border-emerald-500 focus:outline-none"
                        />
                        <span className="text-slate-500 text-xs">{'\u20ac'}</span>
                      </>
                    ) : (
                      <span className="text-sm text-emerald-400 font-medium">Illimite</span>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <input
                      type="number"
                      value={tier.rate}
                      onChange={e => updateTier(idx, 'rate', parseFloat(e.target.value) || 0)}
                      min={0}
                      max={100}
                      step={0.1}
                      className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm text-white w-full focus:border-emerald-500 focus:outline-none"
                    />
                    <span className="text-slate-500 text-xs">%</span>
                  </div>
                  <button
                    onClick={() => removeTier(idx)}
                    disabled={tiers.length <= 1}
                    className="p-1 text-slate-500 hover:text-red-400 disabled:opacity-20"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>

            <button
              onClick={addTier}
              className="flex items-center gap-1 text-xs bg-slate-800 text-slate-300 px-3 py-1.5 rounded-lg hover:bg-slate-700"
            >
              <Plus className="w-3 h-3" /> Ajouter une tranche
            </button>

            {/* Example */}
            <div className="bg-emerald-900/10 border border-emerald-800/20 rounded-lg p-3">
              <p className="text-xs text-slate-400">
                Exemple: bien a 300 000{'\u20ac'} ={' '}
                <span className="text-emerald-400 font-bold text-sm">{exampleCommission.toLocaleString('fr-FR')}{'\u20ac'}</span>
                {' '}de commission ({(exampleCommission / examplePrice * 100).toFixed(1)}% effectif)
              </p>
            </div>
          </div>
        )}
      </Section>

      {/* === CODES POSTAUX === */}
      <Section icon={<MapPin className="w-5 h-5 text-blue-400" />} title="Codes postaux surveilles">
        <div className="flex flex-wrap gap-2 mb-3">
          {postalCodes.map(cp => (
            <span key={cp} className="flex items-center gap-1 bg-blue-500/10 text-blue-400 border border-blue-500/20 px-3 py-1.5 rounded-lg text-sm">
              {cp}
              <button onClick={() => setPostalCodes(postalCodes.filter(c => c !== cp))} className="hover:text-red-400">
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            value={newCP}
            onChange={e => setNewCP(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && addCP()}
            placeholder="Ex: 75001"
            maxLength={5}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none w-32"
          />
          <button onClick={addCP} className="flex items-center gap-1 bg-slate-800 text-slate-300 px-3 py-2 rounded-lg text-sm hover:bg-slate-700">
            <Plus className="w-4 h-4" /> Ajouter
          </button>
        </div>
      </Section>

      {/* === HEURES === */}
      <Section icon={<Clock className="w-5 h-5 text-amber-400" />} title="Heures de scraping (3x/jour)">
        <div className="flex gap-3">
          {[0, 1, 2].map(idx => (
            <div key={idx} className="flex-1">
              <label className="text-xs text-slate-500 mb-1 block">
                {idx === 0 ? 'Matin' : idx === 1 ? 'Midi' : 'Soir'}
              </label>
              <select
                value={hours[idx] ?? ''}
                onChange={e => {
                  const newHours = [...hours]
                  newHours[idx] = parseInt(e.target.value)
                  setHours(newHours)
                }}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:border-amber-500 focus:outline-none"
              >
                {Array.from({ length: 24 }, (_, h) => (
                  <option key={h} value={h}>{h.toString().padStart(2, '0')}:00</option>
                ))}
              </select>
            </div>
          ))}
        </div>
      </Section>

      {/* === SITES === */}
      <Section icon={<Globe className="w-5 h-5 text-emerald-400" />} title="Sites de scraping actifs">
        <div className="space-y-2">
          {availableSites.map(site => (
            <label key={site.key} className="flex items-center gap-3 p-3 bg-slate-800/50 rounded-lg cursor-pointer hover:bg-slate-800">
              <input
                type="checkbox"
                checked={sites.includes(site.key)}
                onChange={e => {
                  if (e.target.checked) {
                    setSites([...sites, site.key])
                  } else {
                    setSites(sites.filter(s => s !== site.key))
                  }
                }}
                className="w-4 h-4 rounded border-slate-600 text-emerald-500 focus:ring-emerald-500 bg-slate-700"
              />
              <div>
                <p className="text-sm text-white font-medium">{site.name}</p>
                <p className="text-xs text-slate-500">{site.desc}</p>
              </div>
            </label>
          ))}
        </div>
      </Section>
    </div>
  )
}

function Section({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <div className="flex items-center gap-2 mb-4">
        {icon}
        <h3 className="text-sm font-semibold text-white">{title}</h3>
      </div>
      {children}
    </div>
  )
}
