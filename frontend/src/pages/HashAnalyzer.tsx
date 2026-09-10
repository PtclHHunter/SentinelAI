import { useState } from 'react'
import { Hash, Upload, AlertTriangle, CheckCircle, Copy, Clipboard } from 'lucide-react'
import { hashAPI } from '../services/api'
import { useToast } from '../App'
import type { HashResult, HashAnalyzeResult } from '../types'

export default function HashAnalyzerPage() {
  const { toast } = useToast()
  const [fileResult, setFileResult] = useState<HashResult | null>(null)
  const [pasteResult, setPasteResult] = useState<HashAnalyzeResult | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [activeTab, setActiveTab] = useState<'file' | 'paste'>('file')
  const [pasteInput, setPasteInput] = useState('')

  const handleFileAnalyze = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setAnalyzing(true)
    setPasteResult(null)
    try {
      const res = await hashAPI.analyze(file)
      setFileResult(res)
      toast(res.ioc_matches.length > 0 ? `WARNING: Hash matches ${res.ioc_matches.length} IOC(s)!` : 'File hashes computed - no IOC matches', res.ioc_matches.length > 0 ? 'error' : 'success')
    } catch (err: any) { toast(err.message, 'error') }
    setAnalyzing(false)
    e.target.value = ''
  }

  const handlePasteAnalyze = async () => {
    const val = pasteInput.trim()
    if (!val) return
    setAnalyzing(true)
    setFileResult(null)
    try {
      const res = await hashAPI.analyzeHash(val)
      setPasteResult(res)
      toast(res.ioc_matches.length > 0 ? `WARNING: Hash matches IOC in database!` : `No IOC match for this ${res.detected_algorithm} hash`, res.ioc_matches.length > 0 ? 'error' : 'success')
    } catch (err: any) { toast(err.message, 'error') }
    setAnalyzing(false)
  }

  const copyHash = (value: string) => {
    navigator.clipboard.writeText(value)
    toast('Hash copied to clipboard', 'info')
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold flex items-center gap-2"><Hash className="w-6 h-6 text-sentinel-cyan" /> File Hash Analyzer</h2>

      <div className="flex gap-2 border-b border-sentinel-border">
        {([['file', 'Upload File'], ['paste', 'Paste Hash']] as const).map(([key, label]) => (
          <button key={key} onClick={() => setActiveTab(key as 'file' | 'paste')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${activeTab === key ? 'border-sentinel-cyan text-sentinel-cyan' : 'border-transparent text-sentinel-text-secondary hover:text-sentinel-text'}`}>
            {label}
          </button>
        ))}
      </div>

      {activeTab === 'file' && (
        <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-8 text-center">
          <Upload className="w-12 h-12 mx-auto text-sentinel-text-secondary mb-4" />
          <p className="text-sm text-sentinel-text-secondary mb-2">Select a file to calculate MD5, SHA-1, SHA-256, and SHA-512 hashes</p>
          <p className="text-xs text-sentinel-text-secondary mb-4">The file will be analyzed locally and never executed or uploaded to any server.</p>
          <label className="inline-flex items-center gap-2 px-6 py-3 bg-sentinel-cyan text-sentinel-bg rounded-lg text-sm font-medium cursor-pointer hover:bg-sentinel-cyan/90 transition-colors">
            <Upload className="w-4 h-4" /> Select File
            <input type="file" className="hidden" onChange={handleFileAnalyze} />
          </label>
        </div>
      )}

      {activeTab === 'paste' && (
        <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-8">
          <div className="flex items-center gap-2 mb-4">
            <Clipboard className="w-5 h-5 text-sentinel-cyan" />
            <h3 className="text-sm font-semibold text-sentinel-text-secondary">Paste a Hash to Check Against IOC Database</h3>
          </div>
          <p className="text-xs text-sentinel-text-secondary mb-4">Enter an MD5 (32 chars), SHA-1 (40 chars), SHA-256 (64 chars), or SHA-512 (128 chars) hex hash.</p>
          <div className="flex gap-3">
            <input value={pasteInput} onChange={e => setPasteInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handlePasteAnalyze()}
              className="flex-1 bg-sentinel-bg border border-sentinel-border rounded-lg px-4 py-3 text-sm font-mono text-sentinel-text placeholder-sentinel-text-secondary focus:outline-none focus:border-sentinel-cyan"
              placeholder="e.g. d41d8cd98f00b204e9800998ecf8427e" />
            <button onClick={handlePasteAnalyze} disabled={analyzing || !pasteInput.trim()}
              className="px-6 py-3 bg-sentinel-cyan text-sentinel-bg rounded-lg text-sm font-medium hover:bg-sentinel-cyan/90 transition-colors disabled:opacity-50 flex items-center gap-2">
              <Hash className="w-4 h-4" /> {analyzing ? 'Checking...' : 'Check Hash'}
            </button>
          </div>
        </div>
      )}

      {analyzing && (
        <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-6 text-center">
          <div className="animate-spin w-8 h-8 border-2 border-sentinel-cyan border-t-transparent rounded-full mx-auto mb-3"></div>
          <p className="text-sm text-sentinel-text-secondary">{activeTab === 'file' ? 'Computing hashes...' : 'Checking hash against database...'}</p>
        </div>
      )}

      {/* File upload results */}
      {fileResult && (
        <div className="space-y-4">
          <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-sentinel-text-secondary">File Information</h3>
              <span className="text-xs text-sentinel-text-secondary">{(fileResult.file_size / 1024).toFixed(2)} KB</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {[
                { label: 'MD5', value: fileResult.md5 },
                { label: 'SHA-1', value: fileResult.sha1 },
                { label: 'SHA-256', value: fileResult.sha256 },
                { label: 'SHA-512', value: fileResult.sha512 },
              ].map(h => (
                <div key={h.label} className="bg-sentinel-bg border border-sentinel-border rounded-lg p-3">
                  <div className="text-xs font-medium text-sentinel-cyan mb-1">{h.label}</div>
                  <div className="flex items-center gap-2">
                    <code className="text-xs font-mono text-sentinel-text break-all flex-1">{h.value}</code>
                    <button onClick={() => copyHash(h.value)} className="p-1 text-sentinel-text-secondary hover:text-sentinel-cyan transition-colors flex-shrink-0">
                      <Copy className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {fileResult.ioc_matches.length > 0 && (
            <div className="bg-sentinel-card border border-sentinel-critical/30 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-sentinel-critical mb-3 flex items-center gap-2"><AlertTriangle className="w-4 h-4" /> IOC Matches</h3>
              <div className="space-y-2">
                {fileResult.ioc_matches.map((m, i) => (
                  <div key={i} className="bg-sentinel-bg border border-sentinel-critical/30 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs px-2 py-0.5 rounded bg-sentinel-critical/20 text-sentinel-critical font-medium uppercase">{m.ioc_type}</span>
                      <span className="text-sm font-mono text-sentinel-critical">{m.value}</span>
                    </div>
                    <div className="text-xs text-sentinel-text-secondary">{m.matched_ioc.description}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {fileResult.ioc_matches.length === 0 && (
            <div className="bg-sentinel-card border border-sentinel-low/30 rounded-xl p-5 flex items-center gap-3">
              <CheckCircle className="w-5 h-5 text-sentinel-low" />
              <div>
                <div className="text-sm font-medium text-sentinel-low">No IOC Matches</div>
                <div className="text-xs text-sentinel-text-secondary">This file's hashes do not match any IOCs in the local database.</div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Paste hash results */}
      {pasteResult && (
        <div className="space-y-4">
          <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5">
            <h3 className="text-sm font-semibold text-sentinel-text-secondary mb-4">Hash Analysis Result</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
              <div className="bg-sentinel-bg border border-sentinel-border rounded-lg p-3">
                <div className="text-xs font-medium text-sentinel-cyan mb-1">Algorithm</div>
                <div className="text-sm font-medium">{pasteResult.detected_algorithm}</div>
              </div>
              <div className="bg-sentinel-bg border border-sentinel-border rounded-lg p-3">
                <div className="text-xs font-medium text-sentinel-cyan mb-1">Type</div>
                <div className="text-sm font-medium uppercase">{pasteResult.detected_type}</div>
              </div>
              <div className="bg-sentinel-bg border border-sentinel-border rounded-lg p-3">
                <div className="text-xs font-medium text-sentinel-cyan mb-1">In IOC Database</div>
                <div className={`text-sm font-medium ${pasteResult.in_database ? 'text-sentinel-critical' : 'text-sentinel-low'}`}>
                  {pasteResult.in_database ? 'YES - THREAT DETECTED' : 'No'}
                </div>
              </div>
            </div>
            <div className="bg-sentinel-bg border border-sentinel-border rounded-lg p-3">
              <div className="text-xs font-medium text-sentinel-cyan mb-1">Input Hash</div>
              <div className="flex items-center gap-2">
                <code className="text-xs font-mono text-sentinel-text break-all flex-1">{pasteResult.input_hash}</code>
                <button onClick={() => copyHash(pasteResult.input_hash)} className="p-1 text-sentinel-text-secondary hover:text-sentinel-cyan transition-colors flex-shrink-0">
                  <Copy className="w-3 h-3" />
                </button>
              </div>
            </div>
          </div>

          {pasteResult.ioc_matches.length > 0 && (
            <div className="bg-sentinel-card border border-sentinel-critical/30 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-sentinel-critical mb-3 flex items-center gap-2"><AlertTriangle className="w-4 h-4" /> IOC Match Found</h3>
              <div className="space-y-2">
                {pasteResult.ioc_matches.map((m, i) => (
                  <div key={i} className="bg-sentinel-bg border border-sentinel-critical/30 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs px-2 py-0.5 rounded bg-sentinel-critical/20 text-sentinel-critical font-medium uppercase">{m.ioc_type}</span>
                      <span className="text-sm font-mono text-sentinel-critical">{m.value}</span>
                    </div>
                    <div className="text-xs text-sentinel-text-secondary">{m.matched_ioc.description}</div>
                    {m.matched_ioc.source && <div className="text-xs text-sentinel-text-secondary mt-1">Source: {m.matched_ioc.source}</div>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {pasteResult.ioc_matches.length === 0 && (
            <div className="bg-sentinel-card border border-sentinel-low/30 rounded-xl p-5 flex items-center gap-3">
              <CheckCircle className="w-5 h-5 text-sentinel-low" />
              <div>
                <div className="text-sm font-medium text-sentinel-low">No IOC Match</div>
                <div className="text-xs text-sentinel-text-secondary">This {pasteResult.detected_algorithm} hash does not match any IOCs in the local database.</div>
              </div>
            </div>
          )}

          <div className="text-xs text-sentinel-text-secondary">Scan time: {pasteResult.scan_time_ms.toFixed(1)}ms</div>
        </div>
      )}
    </div>
  )
}