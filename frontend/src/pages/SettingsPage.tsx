import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getSettings, updateSettings } from '../api/client'
import { Save, Plus, X, Clock, MapPin, Globe } from 'lucide-react'

export default function SettingsPage() {
  const queryClient = useQueryClient()
  const { data: settings } = useQuery({ queryKey: ['settings'], queryFn: getSettings })

  const [postalCodes, setPostalCodes] = useState<string[]>([])
  const [hours, setHours] = useState<number[]>([])
  const [sites, setSites] = useState<string[]>([])
  const [newCP, setNewCP] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (settings) {
      setPostalCodes(settings.postal_codes || [])
      setHours(settings.schedule_hours || [])
      setSites(settings.enabled_sites || [])
    }
  }, [settings])

  const mutation = useMutation({
    mutationFn: () =>
      updateSettings({
        postal_codes: postalCodes,
        schedule_hours: hours,
        enabled_sites: sites,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    },
  })

  const addCP = () => {
    const cp = newCP.trim()
    if (cp && /^\d{5}$/.test(cp) && !postalCodes.includes(cp)) {
      setPostalCodes([...postalCodes, cp])
      setNewCP('')
    }
  }

  const availableSites = [
    { key: 'pap', name: 'PAP.fr' },
    { key: 'entreparticuliers', name: 'Entreparticuliers.com' },
    { key: 'paruvendu', name: 'ParuVendu.fr' },
  ]

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Parametres</h1>
        <button
          onClick={() => mutation.mutate()}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            saved ? 'bg-green-500 text-white' : 'bg-emerald-500 hover:bg-emerald-600 text-white'
          }`}
        >
          <Save className="w-4 h-4" />
          {saved ? 'Enregistre !' : 'Enregistrer'}
        </button>
      </div>

      {/* Codes postaux */}
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

      {/* Heures de scraping */}
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

      {/* Sites actifs */}
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
                <p className="text-xs text-slate-500">
                  {site.key === 'pap' ? '100% particuliers' :
                   site.key === 'entreparticuliers' ? '100% particuliers' :
                   'Filtrage pro/particulier actif'}
                </p>
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
