import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useInterviewApp } from '../../context/useInterviewApp'
import { DASHBOARD_PATH } from '../../routing/routes'
import { getApiError } from '../../services/apiClient'
import {
  fetchCompanyDiscoveries,
  fetchCompanyDiscoveryStatus,
  startCompanyDiscovery,
} from '../../services/companyDiscoveryService'

const RESEARCH_STEPS = ['Routing', 'Researching', 'Auditing', 'Architecting', 'Critic review']

function getHttpUrl(value) {
  try {
    const url = new URL(value)
    return ['http:', 'https:'].includes(url.protocol) ? url.href : null
  } catch {
    return null
  }
}

export default function DiscoveryDashboardPage() {
  const { handleHome, token } = useInterviewApp()
  const [catalog, setCatalog] = useState([])
  const [company, setCompany] = useState('')
  const [jobDescription, setJobDescription] = useState('')
  const [geography, setGeography] = useState('')
  const [activeSearch, setActiveSearch] = useState(null)
  const [status, setStatus] = useState(null)
  const [query, setQuery] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const loadCatalog = useCallback(async () => {
    try {
      const data = await fetchCompanyDiscoveries(token)
      setCatalog(data.companies || [])
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not load company intelligence.'))
    }
  }, [token])

  useEffect(() => {
    let active = true
    fetchCompanyDiscoveries(token)
      .then((data) => {
        if (active) setCatalog(data.companies || [])
      })
      .catch((requestError) => {
        if (active) setError(getApiError(requestError, 'Could not load company intelligence.'))
      })
    return () => { active = false }
  }, [token])

  useEffect(() => {
    if (!activeSearch || !['starting', 'running'].includes(status?.status)) return undefined
    let active = true
    const poll = async () => {
      try {
        const latest = await fetchCompanyDiscoveryStatus({
          token,
          company: activeSearch.company,
          geography: activeSearch.geography,
        })
        if (!active) return
        setStatus(latest)
        if (latest.status === 'completed') loadCatalog()
        if (latest.status === 'failed') setError(latest.error || 'Company research failed.')
      } catch (requestError) {
        if (active) setError(getApiError(requestError, 'Could not read company research progress.'))
      }
    }
    const timer = window.setInterval(poll, 1200)
    poll()
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [activeSearch, loadCatalog, status?.status, token])

  const runResearch = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    setStatus({ status: 'starting', stage: 'Starting', events: [] })
    setActiveSearch({ company: company.trim(), geography: geography.trim() })
    try {
      await startCompanyDiscovery({
        token,
        company: company.trim(),
        jobDescription,
        geography: geography.trim(),
      })
      setStatus({ status: 'running', stage: 'Routing', events: [] })
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not start company research.'))
      setStatus({ status: 'failed', stage: 'Failed', events: [] })
    } finally {
      setBusy(false)
    }
  }

  const filteredCompanies = catalog.filter((entry) => {
    const needle = query.trim().toLowerCase()
    return !needle || `${entry.company_name} ${entry.industry || ''} ${entry.geography || ''}`
      .toLowerCase()
      .includes(needle)
  })

  return (
    <main className="page-shell">
      <header className="topbar">
        <Link className="brand" onClick={handleHome} to={DASHBOARD_PATH}>
          <span className="brand-mark">IA</span> InterviewAI
        </Link>
        <nav aria-label="Company intelligence navigation" className="account">
          <Link className="text-button" onClick={handleHome} to={DASHBOARD_PATH}>Home</Link>
        </nav>
      </header>
      <section className="hero-card discovery-hero">
        <div>
          <p className="eyebrow">Interview intelligence</p>
          <h1>Research companies before you practice.</h1>
          <p className="muted">Browse saved profiles or run a fresh, region-aware public research workflow.</p>
        </div>
        <div aria-hidden="true" className="hero-orb">AI</div>
      </section>

      <section className="panel discovery-run-panel">
        <p className="eyebrow">Agentic discovery</p>
        <h2>Research a company</h2>
        <form className="discovery-form" onSubmit={runResearch}>
          <label>
            Company
            <input maxLength={255} onChange={(event) => setCompany(event.target.value)} required value={company} />
          </label>
          <label>
            Region (optional)
            <input
              onChange={(event) => setGeography(event.target.value)}
              placeholder="For example: United States or India"
              value={geography}
            />
          </label>
          <label>
            Role context (optional)
            <textarea
              onChange={(event) => setJobDescription(event.target.value)}
              placeholder="Paste a job description to ground the research."
              rows="3"
              value={jobDescription}
            />
          </label>
          <button className="button primary" disabled={busy || !company.trim()} type="submit">
            {busy ? 'Starting…' : 'Start research'}
          </button>
        </form>

        {status && (
          <section aria-live="polite" className="research-terminal">
            <div className="research-terminal-heading">
              <strong>Researcher at work</strong>
              <span className={`research-indicator ${status.status}`}>{status.status}</span>
            </div>
            <p className="fine-print">
              {status.mode === 'curated'
                ? 'Curated profile · loaded from the expert-maintained company database.'
                : status.mode === 'stealth'
                ? 'Stealth mode · limited public information; using job-description and industry evidence.'
                : 'Public research · validating available sources for the selected company and region.'}
            </p>
            <ol>
              {RESEARCH_STEPS.map((step) => {
                const activeIndex = RESEARCH_STEPS.indexOf(status.stage)
                const index = RESEARCH_STEPS.indexOf(step)
                return (
                  <li className={index < activeIndex || status.status === 'completed' ? 'complete' : index === activeIndex ? 'active' : ''} key={step}>
                    <span>{step}</span>
                  </li>
                )
              })}
            </ol>
            {status.events?.length > 0 && (
              <ul className="research-events">
                {status.events.map((event, index) => (
                  <li key={`${event.message}-${index}`}>
                    <span>{event.decision || 'INFO'}</span>
                    {event.message}
                    {getHttpUrl(event.url) && (
                      <a href={getHttpUrl(event.url)} rel="noreferrer" target="_blank">Source</a>
                    )}
                  </li>
                ))}
              </ul>
            )}
            {status.error && <p className="notice error">{status.error}</p>}
          </section>
        )}
      </section>

      <section className="panel discovery-catalog">
        <div className="section-heading">
          <div><p className="eyebrow">Company profiles</p><h2>Saved intelligence</h2></div>
          <span className="plan-pill">{catalog.length} profiles</span>
        </div>
        <label className="discovery-search">
          Search profiles
          <input onChange={(event) => setQuery(event.target.value)} placeholder="Company, industry, or region" value={query} />
        </label>
        <div className="discovery-cards">
          {filteredCompanies.map((entry) => (
            <article className="discovery-card" key={`${entry.company_name}-${entry.geography || ''}`}>
              <div className="discovery-card-title">
                <h3>{entry.company_name}</h3>
                <span className={`discovery-source ${entry.is_synthetic ? 'stealth' : ''}`}>
                  {entry.is_synthetic ? 'Stealth' : entry.source_tier}
                </span>
              </div>
              <p>{[entry.industry, entry.geography].filter(Boolean).join(' · ') || 'Company profile'}</p>
              {entry.interview_style && <p>{entry.interview_style}</p>}
              <small>{entry.confidence_score ?? 0}% confidence · AI research, verify independently</small>
            </article>
          ))}
          {filteredCompanies.length === 0 && <p className="muted">No matching company profiles were found.</p>}
        </div>
      </section>
      {error && <p className="notice error" role="alert">{error}</p>}
      <footer className="footer-note">AI-generated interview intelligence can be incomplete or outdated. Verify important claims using official sources.</footer>
    </main>
  )
}
