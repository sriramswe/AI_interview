import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  AlertCircle,
  Award,
  CheckCircle2,
  Clipboard,
  Loader2,
  RefreshCw,
  Sparkles,
  Target,
  TrendingUp,
  UploadCloud,
  XCircle,
} from 'lucide-react'
import { useInterviewApp } from '../../context/useInterviewApp'
import {
  analyzeAtsScore,
  generateTargetJobDescription,
} from '../../services/atsService'
import { getApiError } from '../../services/apiClient'
import { AppHeader } from '../dashboard/DashboardPage'
import { DASHBOARD_PATH, LOGIN_PATH } from '../../routing/routes'
import './ats.css'

export default function ATSCheckerPage() {
  const { token } = useInterviewApp()
  const navigate = useNavigate()

  const [inputMode, setInputMode] = useState('upload') // 'upload' | 'text'
  const [resumeFile, setResumeFile] = useState(null)
  const [resumeText, setResumeText] = useState('')
  const [jobDescription, setJobDescription] = useState('')
  const [targetRole, setTargetRole] = useState('')
  const [loading, setLoading] = useState(false)
  const [generatingTarget, setGeneratingTarget] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [copiedKey, setCopiedKey] = useState(false)
  const [aiProcessingAcknowledged, setAiProcessingAcknowledged] = useState(false)

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        setError('Please upload a PDF file.')
        return
      }
      setResumeFile(file)
      setJobDescription('')
      setTargetRole('')
      setResult(null)
      setError('')
    }
  }

  const handleResumeTextChange = (event) => {
    setResumeText(event.target.value)
    setJobDescription('')
    setTargetRole('')
    setResult(null)
  }

  const handleInputModeChange = (mode) => {
    setInputMode(mode)
    setJobDescription('')
    setTargetRole('')
    setResult(null)
    setError('')
  }

  const handleGenerateTarget = async () => {
    if (!token) {
      setError('Please sign in to generate a target job description.')
      return
    }
    if (!aiProcessingAcknowledged) {
      setError('Please acknowledge AI processing before generating a target job description.')
      return
    }
    if (inputMode === 'upload' && !resumeFile) {
      setError('Please choose a PDF resume first.')
      return
    }
    if (inputMode === 'text' && !resumeText.trim()) {
      setError('Please paste your resume text first.')
      return
    }

    setGeneratingTarget(true)
    setError('')
    setResult(null)
    try {
      const generated = await generateTargetJobDescription({
        file: inputMode === 'upload' ? resumeFile : null,
        resumeText: inputMode === 'text' ? resumeText : null,
        aiProcessingAcknowledged,
        token,
      })
      setTargetRole(generated.target_role)
      setJobDescription(generated.job_description)
    } catch (err) {
      setError(getApiError(err, 'Could not generate a target job description from your resume.'))
    } finally {
      setGeneratingTarget(false)
    }
  }

  const handleAnalyze = async (e) => {
    e?.preventDefault()
    if (!aiProcessingAcknowledged) {
      setError('Please acknowledge that your resume will be processed by the configured AI provider.')
      return
    }
    if (inputMode === 'upload' && !resumeFile) {
      setError('Please choose a PDF resume to scan.')
      return
    }
    if (inputMode === 'text' && !resumeText.trim()) {
      setError('Please paste your resume text to scan.')
      return
    }
    if (!jobDescription.trim()) {
      setError('Generate a target job description from your resume before running the ATS check.')
      return
    }

    setLoading(true)
    setError('')
    setResult(null)

    try {
      const data = await analyzeAtsScore({
        file: inputMode === 'upload' ? resumeFile : null,
        resumeText: inputMode === 'text' ? resumeText : null,
        jobDescription: jobDescription.trim(),
        targetRole: targetRole.trim(),
        aiProcessingAcknowledged,
        token,
      })
      setResult(data)
    } catch (err) {
      setError(getApiError(err, 'Could not analyze resume. Please check your file or try again.'))
    } finally {
      setLoading(false)
    }
  }

  const copyMissingKeywords = () => {
    if (!result?.missing_keywords?.length) return
    navigator.clipboard.writeText(result.missing_keywords.join(', '))
    setCopiedKey(true)
    setTimeout(() => setCopiedKey(false), 2000)
  }

  const getScoreColor = (score) => {
    if (score >= 80) return '#10b981' // emerald
    if (score >= 65) return '#3b82f6' // blue
    if (score >= 50) return '#f59e0b' // amber
    return '#ef4444' // red
  }

  return (
    <main className="page-shell">
      <AppHeader />

      {/* Hero Banner */}
      <section className="ats-hero-card">
        <div className="ats-hero-content">
          <div className="ats-badge">
            <Sparkles size={16} /> ATS Score + AI Role Match
          </div>
          <h1>Optimize Your Resume for Applicant Tracking Systems</h1>
          <p className="ats-hero-subtitle">
            Get a rule-based ATS compatibility score and an AI-estimated role match,
            with evidence-grounded strengths, gaps, and improvement ideas.
          </p>
          {!token ? (
            <p className="fine-print">
              <Link to={LOGIN_PATH}>Sign in</Link> to analyze your resume.
            </p>
          ) : null}
        </div>
      </section>

      {/* Form / Input Panel */}
      <section className="ats-scanner-panel">
        <form onSubmit={handleAnalyze} className="ats-form">
          <div className="ats-form-grid">
            {/* Left Column: Resume Input */}
            <div className="ats-input-box">
              <div className="ats-box-header">
                <h3>1. Your Resume</h3>
                <div className="ats-tab-switch">
                  <button
                    type="button"
                    className={`ats-tab-btn ${inputMode === 'upload' ? 'active' : ''}`}
                    onClick={() => handleInputModeChange('upload')}
                  >
                    Upload PDF
                  </button>
                  <button
                    type="button"
                    className={`ats-tab-btn ${inputMode === 'text' ? 'active' : ''}`}
                    onClick={() => handleInputModeChange('text')}
                  >
                    Paste Text
                  </button>
                </div>
              </div>

              {inputMode === 'upload' ? (
                <div className="ats-upload-dropzone">
                  <input
                    type="file"
                    id="ats-resume-file"
                    accept=".pdf,application/pdf"
                    onChange={handleFileChange}
                    className="ats-file-hidden"
                  />
                  <label htmlFor="ats-resume-file" className="ats-dropzone-label">
                    <UploadCloud size={36} className="ats-upload-icon" />
                    {resumeFile ? (
                      <div className="ats-selected-file">
                        <strong>{resumeFile.name}</strong>
                        <span>{(resumeFile.size / (1024 * 1024)).toFixed(2)} MB • Ready to analyze</span>
                        <span className="ats-change-pill">Change file</span>
                      </div>
                    ) : (
                      <div className="ats-prompt-text">
                        <strong>Click or drag PDF resume here</strong>
                        <span>Maximum file size 10 MB (PDF format)</span>
                      </div>
                    )}
                  </label>
                </div>
              ) : (
                <div className="ats-textarea-wrapper">
                  <textarea
                    rows={10}
                    value={resumeText}
                    onChange={handleResumeTextChange}
                    placeholder="Paste your full resume text here including Summary, Skills, Experience, Projects, and Education..."
                    className="ats-textarea"
                  />
                </div>
              )}
            </div>

            {/* Right Column: Job Description */}
            <div className="ats-input-box">
              <div className="ats-box-header ats-jd-header">
                <div>
                  <h3>2. Target Job Description</h3>
                  {targetRole && (
                    <span className="ats-generated-role">Resume-based role: {targetRole}</span>
                  )}
                </div>
                <button
                  type="button"
                  className="button secondary ats-generate-jd-btn"
                  disabled={
                    generatingTarget
                    || loading
                    || !token
                    || !aiProcessingAcknowledged
                    || (inputMode === 'upload' ? !resumeFile : !resumeText.trim())
                  }
                  onClick={handleGenerateTarget}
                >
                  {generatingTarget ? (
                    <>
                      <Loader2 size={16} className="spin-icon" /> Generating…
                    </>
                  ) : (
                    <>
                      <Sparkles size={16} /> Generate from resume
                    </>
                  )}
                </button>
              </div>
              <p className="ats-hint-note">
                Add your resume and acknowledge AI processing below to generate an editable target description.
              </p>
              <div className="ats-textarea-wrapper">
                <textarea
                  rows={8}
                  value={jobDescription}
                  onChange={(event) => setJobDescription(event.target.value)}
                  disabled={!jobDescription || generatingTarget}
                  placeholder="Your resume-based target job description will appear here. You can edit it before checking your ATS score."
                  className="ats-textarea"
                />
              </div>
            </div>
          </div>

          {error && (
            <div className="notice error ats-error-notice" role="alert">
              <AlertCircle size={18} />
              <span>{error}</span>
            </div>
          )}

          <label className="ats-privacy-consent">
            <input
              type="checkbox"
              checked={aiProcessingAcknowledged}
              onChange={(event) => setAiProcessingAcknowledged(event.target.checked)}
            />
            <span>
              I understand my resume will be sent to this app's configured AI provider
              to generate a target job description and analyze my ATS match. Depending
              on the provider, data may be processed outside this app; avoid submitting
              information you do not want to share.
            </span>
          </label>

          <div className="ats-action-row">
            <button
              type="submit"
              disabled={
                loading
                || generatingTarget
                || !token
                || !aiProcessingAcknowledged
                || !jobDescription.trim()
              }
              className="button primary ats-scan-btn"
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="spin-icon" /> Analyzing Resume & Job Match…
                </>
              ) : (
                <>
                  <Sparkles size={18} /> Check ATS Score Now
                </>
              )}
            </button>
          </div>
        </form>
      </section>

      {/* Results Section */}
      {result && (
        <section className="ats-results-panel">
          {/* Main Score Header */}
          <div className="ats-score-hero-card">
            <div className="ats-score-gauge">
              <div
                className="ats-circle-score"
                style={{
                  background: `conic-gradient(${getScoreColor(result.ats_score)} ${
                    result.ats_score * 3.6
                  }deg, rgba(255, 255, 255, 0.08) 0deg)`,
                }}
              >
                <div className="ats-circle-inner">
                  <span className="ats-score-number">{result.ats_score}</span>
                  <span className="ats-score-total">/100</span>
                </div>
              </div>
            </div>

            <div className="ats-score-verdict">
              <div className="ats-grade-row">
                <span
                  className="ats-grade-badge"
                  style={{
                    backgroundColor: `${getScoreColor(result.ats_score)}22`,
                    color: getScoreColor(result.ats_score),
                    borderColor: getScoreColor(result.ats_score),
                  }}
                >
                  <Award size={16} /> {result.score_grade}
                </span>
                <span className="ats-meta-stat">{result.word_count} words analyzed</span>
              </div>
              <h2>{result.verdict}</h2>
              <p className="ats-verdict-desc">
                {result.ats_score >= 80
                  ? 'Your resume has strong rule-based keyword alignment and structure for this role.'
                  : result.ats_score >= 60
                    ? 'Your resume is competitive, but targeted keyword and metric improvements may help.'
                    : 'We detected skill gaps and formatting areas to address before applying.'}
              </p>

              <div className="ats-action-buttons">
                <button
                  type="button"
                  className="button primary"
                  onClick={() => navigate(DASHBOARD_PATH)}
                >
                  <Target size={16} /> Practice Mock Interview for this Role
                </button>
                <button
                  type="button"
                  className="button secondary"
                  onClick={() => {
                    setResult(null)
                    window.scrollTo({ top: 0, behavior: 'smooth' })
                  }}
                >
                  <RefreshCw size={16} /> Scan Another Resume
                </button>
              </div>
            </div>
          </div>

          {result.ai_match_prediction && (
            <section className="ats-ai-match-card" aria-labelledby="ats-ai-match-heading">
              <div className="ats-ai-match-header">
                <div>
                  <span className="ats-ai-match-label">
                    <Sparkles size={16} /> AI estimate
                  </span>
                  <h2 id="ats-ai-match-heading">Role match: {result.ai_match_prediction.match_level}</h2>
                </div>
                <strong className="ats-ai-match-score">
                  {result.ai_match_prediction.match_score}<small>/100</small>
                </strong>
              </div>
              <p className="ats-ai-match-summary">{result.ai_match_prediction.summary}</p>
              <div className="ats-ai-match-columns">
                <div>
                  <h3>Relevant strengths</h3>
                  {result.ai_match_prediction.strengths.length ? (
                    <ul>{result.ai_match_prediction.strengths.map((item, index) => <li key={index}>{item}</li>)}</ul>
                  ) : <p>No clear strengths identified from the supplied information.</p>}
                </div>
                <div>
                  <h3>Potential gaps</h3>
                  {result.ai_match_prediction.gaps.length ? (
                    <ul>{result.ai_match_prediction.gaps.map((item, index) => <li key={index}>{item}</li>)}</ul>
                  ) : <p>No major gaps identified from the supplied information.</p>}
                </div>
              </div>
              {result.ai_match_prediction.recommendations.length > 0 && (
                <div className="ats-ai-recommendations">
                  <h3>Suggested next steps</h3>
                  <ul>{result.ai_match_prediction.recommendations.map((item, index) => <li key={index}>{item}</li>)}</ul>
                </div>
              )}
              {result.ai_match_prediction.bullet_rewrites.length > 0 && (
                <div className="ats-ai-rewrites">
                  <h3>Evidence-based bullet rewrites</h3>
                  {result.ai_match_prediction.bullet_rewrites.map((item, index) => (
                    <article key={index}>
                      <p><strong>Current:</strong> {item.original}</p>
                      <p><strong>Suggested:</strong> {item.improved}</p>
                      <small>{item.rationale}</small>
                    </article>
                  ))}
                </div>
              )}
              <p className="ats-ai-disclaimer">{result.ai_match_prediction.disclaimer}</p>
            </section>
          )}

          {/* Breakdown Score Cards */}
          <div className="ats-metrics-grid">
            <div className="ats-metric-card">
              <div className="ats-metric-header">
                <span>Keyword Match</span>
                <strong>{result.breakdown?.keyword_match}%</strong>
              </div>
              <div className="ats-progress-bar">
                <div
                  className="ats-progress-fill"
                  style={{
                    width: `${result.breakdown?.keyword_match}%`,
                    background: getScoreColor(result.breakdown?.keyword_match),
                  }}
                />
              </div>
              <small>Matched against JD keywords & technical terms</small>
            </div>

            <div className="ats-metric-card">
              <div className="ats-metric-header">
                <span>Section Completeness</span>
                <strong>{result.breakdown?.section_completeness}%</strong>
              </div>
              <div className="ats-progress-bar">
                <div
                  className="ats-progress-fill"
                  style={{
                    width: `${result.breakdown?.section_completeness}%`,
                    background: getScoreColor(result.breakdown?.section_completeness),
                  }}
                />
              </div>
              <small>Summary, Experience, Education, Skills, Projects</small>
            </div>

            <div className="ats-metric-card">
              <div className="ats-metric-header">
                <span>Quantifiable Metrics</span>
                <strong>{result.breakdown?.measurable_metrics}%</strong>
              </div>
              <div className="ats-progress-bar">
                <div
                  className="ats-progress-fill"
                  style={{
                    width: `${result.breakdown?.measurable_metrics}%`,
                    background: getScoreColor(result.breakdown?.measurable_metrics),
                  }}
                />
              </div>
              <small>{result.metrics_found_count} metrics found (%, $, numbers, throughput)</small>
            </div>

            <div className="ats-metric-card">
              <div className="ats-metric-header">
                <span>Action Verbs</span>
                <strong>{result.breakdown?.action_verbs}%</strong>
              </div>
              <div className="ats-progress-bar">
                <div
                  className="ats-progress-fill"
                  style={{
                    width: `${result.breakdown?.action_verbs}%`,
                    background: getScoreColor(result.breakdown?.action_verbs),
                  }}
                />
              </div>
              <small>{result.action_verbs_found?.length || 0} strong action verbs identified</small>
            </div>
          </div>

          {/* Keywords Section: Matched vs Missing */}
          <div className="ats-keywords-container">
            <div className="ats-keyword-column matched">
              <div className="ats-col-heading">
                <h4>
                  <CheckCircle2 size={18} className="text-emerald" /> Matched Keywords (
                  {result.matched_keywords?.length || 0})
                </h4>
                <span className="ats-subtext">Keywords successfully identified in your resume</span>
              </div>
              <div className="ats-tag-cloud">
                {result.matched_keywords?.length ? (
                  result.matched_keywords.map((kw) => (
                    <span key={kw} className="ats-tag matched">
                      ✓ {kw}
                    </span>
                  ))
                ) : (
                  <p className="ats-empty-text">No direct keyword matches found.</p>
                )}
              </div>
            </div>

            <div className="ats-keyword-column missing">
              <div className="ats-col-heading">
                <div className="ats-heading-flex">
                  <h4>
                    <XCircle size={18} className="text-amber" /> Missing Target Keywords (
                    {result.missing_keywords?.length || 0})
                  </h4>
                  {result.missing_keywords?.length > 0 && (
                    <button
                      type="button"
                      className="ats-copy-btn"
                      onClick={copyMissingKeywords}
                      title="Copy missing keywords to clipboard"
                    >
                      <Clipboard size={14} /> {copiedKey ? 'Copied!' : 'Copy'}
                    </button>
                  )}
                </div>
                <span className="ats-subtext">Add these keywords to your resume to increase ranking</span>
              </div>
              <div className="ats-tag-cloud">
                {result.missing_keywords?.length ? (
                  result.missing_keywords.map((kw) => (
                    <span key={kw} className="ats-tag missing">
                      + {kw}
                    </span>
                  ))
                ) : (
                  <p className="ats-empty-text text-emerald">Great job! No major keywords missing.</p>
                )}
              </div>
            </div>
          </div>

          {/* Suggestions & Action Plan */}
          {result.suggestions?.length > 0 && (
            <div className="ats-suggestions-box">
              <div className="ats-box-title">
                <TrendingUp size={20} />
                <h3>Actionable Improvements for Maximum ATS Score</h3>
              </div>
              <ul className="ats-suggestions-list">
                {result.suggestions.map((suggestion, idx) => (
                  <li key={idx} className="ats-suggestion-item">
                    <span className="ats-bullet-num">{idx + 1}</span>
                    <p>{suggestion}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}

        </section>
      )}
    </main>
  )
}
