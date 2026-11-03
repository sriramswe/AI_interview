import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronDown,
  Download,
  FileText,
  LoaderCircle,
  Plus,
  Sparkles,
  UploadCloud,
  X,
} from 'lucide-react'
import { useInterviewApp } from '../../context/useInterviewApp'
import { getApiError } from '../../services/apiClient'
import {
  createResume,
  fetchResumeBuilderData,
  importResumeForCustomization,
  updateResume,
} from '../../services/resumeBuilderService'
import { ATS_PATH, DASHBOARD_PATH } from '../../routing/routes'
import { AppHeader } from '../dashboard/DashboardPage'
import './resumeBuilder.css'

const EMPTY_CONTENT = {
  full_name: '',
  headline: '',
  email: '',
  phone: '',
  location: '',
  website: '',
  summary: '',
  skills: [],
  experience: [],
  education: [],
  projects: [],
  raw_resume_text: '',
}

const EMPTY_RESUME = {
  template_id: '',
  title: 'My resume',
  source: 'template',
  content: EMPTY_CONTENT,
}

const TEMPLATE_FAMILIES = [
  { id: 'all', label: 'All 30' },
  { id: 'classic', label: 'Classic' },
  { id: 'modern', label: 'Modern' },
  { id: 'executive', label: 'Executive' },
  { id: 'creative', label: 'Creative' },
  { id: 'minimal', label: 'Minimal' },
  { id: 'ats', label: 'ATS' },
]

const ATS_FRIENDLY_LAYOUTS = new Set(['traditional', 'modern', 'executive', 'minimal'])

const EXPERIENCE_LEVELS = [
  { value: 'none', label: 'No Experience' },
  { value: 'under-3', label: 'Less than 3 years' },
  { value: '3-5', label: '3-5 Years' },
  { value: '5-10', label: '5-10 Years' },
  { value: '10-plus', label: '10+ Years' },
]

const EDUCATION_LEVELS = [
  'Secondary School',
  'Vocational Certificate or Diploma',
  'Apprenticeship or Internship Training',
  'Associates',
  'Bachelors',
  'Masters',
  'Doctorate or Ph.D.',
]

const RECOMMENDED_FAMILY_BY_EXPERIENCE = {
  none: 'modern',
  'under-3': 'modern',
  '3-5': 'classic',
  '5-10': 'executive',
  '10-plus': 'executive',
}

function ResumePreview({ template, content }) {
  const skills = Array.isArray(content.skills) ? content.skills : []

  return (
    <article
      className={`resume-paper resume-layout-${template?.layout || 'modern'}`}
      style={{ '--resume-accent': template?.accent || '#334155' }}
      aria-label="Resume preview"
    >
      <header className="resume-paper-header">
        <div>
          <h1>{content.full_name || 'Your name'}</h1>
          <p className="resume-paper-headline">{content.headline || 'Professional title'}</p>
        </div>
        <div className="resume-contact">
          {[content.email, content.phone, content.location, content.website].filter(Boolean).map((value, index) => (
            <span key={`${index}-${value}`}>{value}</span>
          ))}
        </div>
      </header>

      {content.raw_resume_text ? (
        <section className="resume-paper-section resume-imported-text">
          <h2>Resume</h2>
          <p>{content.raw_resume_text}</p>
        </section>
      ) : (
        <>
          {content.summary && (
            <section className="resume-paper-section">
              <h2>Profile</h2>
              <p>{content.summary}</p>
            </section>
          )}
          {skills.length > 0 && (
            <section className="resume-paper-section">
              <h2>Skills</h2>
              <p className="resume-skills">{skills.join('  ·  ')}</p>
            </section>
          )}
          {content.experience?.some((item) => item.role || item.company || item.description) && (
            <section className="resume-paper-section">
              <h2>Experience</h2>
              {content.experience.filter((item) => item.role || item.company || item.description).map((item, index) => (
                <div className="resume-paper-entry" key={`${item.company}-${item.role}-${index}`}>
                  <div className="resume-entry-heading">
                    <strong>{item.role || 'Position'}{item.company ? ` · ${item.company}` : ''}</strong>
                    <span>{item.dates}</span>
                  </div>
                  {item.description && <p>{item.description}</p>}
                </div>
              ))}
            </section>
          )}
          {content.projects?.some((item) => item.name || item.description) && (
            <section className="resume-paper-section">
              <h2>Projects</h2>
              {content.projects.filter((item) => item.name || item.description).map((item, index) => (
                <div className="resume-paper-entry" key={`${item.name}-${index}`}>
                  <div className="resume-entry-heading">
                    <strong>{item.name || 'Project'}</strong>
                    {item.link && <span>{item.link}</span>}
                  </div>
                  {item.description && <p>{item.description}</p>}
                </div>
              ))}
            </section>
          )}
          {content.education?.some((item) => item.degree || item.institution || item.details) && (
            <section className="resume-paper-section">
              <h2>Education</h2>
              {content.education.filter((item) => item.degree || item.institution || item.details).map((item, index) => (
                <div className="resume-paper-entry" key={`${item.institution}-${item.degree}-${index}`}>
                  <div className="resume-entry-heading">
                    <strong>{item.degree || 'Degree'}{item.institution ? ` · ${item.institution}` : ''}</strong>
                    <span>{item.dates}</span>
                  </div>
                  {item.details && <p>{item.details}</p>}
                </div>
              ))}
            </section>
          )}
        </>
      )}
    </article>
  )
}

function TemplateCard({ template, onChoose }) {
  return (
    <button className="resume-template-card" onClick={() => onChoose(template)} type="button">
      <span className={`resume-template-thumb resume-thumb-${template.layout}`} style={{ '--resume-accent': template.accent }}>
        <span className="resume-thumb-name" />
        <span className="resume-thumb-contact" />
        <span className="resume-thumb-rule" />
        <span className="resume-thumb-lines" />
        <span className="resume-thumb-lines short" />
      </span>
      <span className="resume-template-card-copy">
        <strong>{template.name}</strong>
        <small>{template.layout} layout</small>
      </span>
      <ArrowRight aria-hidden="true" size={16} />
    </button>
  )
}

export default function ResumeBuilderPage() {
  const { profile, subscription, token } = useInterviewApp()
  const [builderData, setBuilderData] = useState(null)
  const [templates, setTemplates] = useState([])
  const [draft, setDraft] = useState(EMPTY_RESUME)
  const [editingId, setEditingId] = useState(null)
  const [familyFilter, setFamilyFilter] = useState('all')
  const [page, setPage] = useState('profile')
  const [profileStep, setProfileStep] = useState(1)
  const [experienceLevel, setExperienceLevel] = useState('')
  const [isStudent, setIsStudent] = useState(null)
  const [educationLevel, setEducationLevel] = useState('')
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const activePlan = builderData?.plan || subscription?.plan || 'free'
  const paidBuilder = ['legacy_resume', 'elite'].includes(activePlan)
  const atsTemplates = useMemo(
    () => templates.filter((template) => ATS_FRIENDLY_LAYOUTS.has(template.layout)),
    [templates],
  )
  const filteredTemplates = useMemo(
    () => familyFilter === 'all'
      ? templates
      : familyFilter === 'ats'
        ? atsTemplates
        : templates.filter((template) => template.family === familyFilter),
    [atsTemplates, familyFilter, templates],
  )
  const selectedTemplate = templates.find((template) => template.id === draft.template_id)

  useEffect(() => {
    let active = true
    fetchResumeBuilderData(token)
      .then((data) => {
        if (!active) return
        setBuilderData(data)
        setTemplates(data.templates)
      })
      .catch((requestError) => {
        if (active) setError(getApiError(requestError, 'Could not load resume templates.'))
      })
      .finally(() => {
        if (active) setBusy(false)
      })
    return () => {
      active = false
    }
  }, [token])

  const refreshBuilderData = async () => {
    const data = await fetchResumeBuilderData(token)
    setBuilderData(data)
    setTemplates(data.templates)
    return data
  }

  const startTemplate = (template) => {
    setDraft({
      ...EMPTY_RESUME,
      template_id: template.id,
      title: 'My resume',
      content: { ...EMPTY_CONTENT, full_name: profile?.username || '' },
    })
    setEditingId(null)
    setError('')
    setNotice('')
    setPage('editor')
  }

  const handleUpload = async (file) => {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Upload a PDF resume to customize it.')
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      setError('Resume exceeds the 10 MB limit.')
      return
    }
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const imported = await importResumeForCustomization({ token, file })
      const defaultTemplate = templates[0]
      if (!defaultTemplate) throw new Error('Resume templates are still loading. Try again shortly.')
      setDraft({
        ...EMPTY_RESUME,
        template_id: defaultTemplate.id,
        title: imported.filename.replace(/\.pdf$/i, ''),
        source: 'upload',
        content: {
          ...EMPTY_CONTENT,
          full_name: profile?.username || '',
          raw_resume_text: imported.resume_text,
        },
      })
      setEditingId(null)
      setPage('editor')
      setNotice('Resume imported. Edit the text and choose a template, then save your customized copy.')
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not import that PDF resume.'))
    } finally {
      setBusy(false)
    }
  }

  const handleEdit = (resume) => {
    if (resume.source === 'upload' && !paidBuilder) {
      setError('An active Elite or legacy resume subscription is required to customize an uploaded resume.')
      return
    }
    setDraft({
      template_id: resume.template_id,
      title: resume.title,
      source: resume.source,
      content: { ...EMPTY_CONTENT, ...resume.content },
    })
    setEditingId(resume.id)
    setError('')
    setNotice('')
    setPage('editor')
  }

  const setContentField = (field, value) => {
    setDraft((current) => ({
      ...current,
      content: { ...current.content, [field]: value },
    }))
  }

  const updateEntry = (section, index, field, value) => {
    setDraft((current) => ({
      ...current,
      content: {
        ...current.content,
        [section]: current.content[section].map((item, itemIndex) => (
          itemIndex === index ? { ...item, [field]: value } : item
        )),
      },
    }))
  }

  const addEntry = (section, item) => {
    setDraft((current) => ({
      ...current,
      content: { ...current.content, [section]: [...current.content[section], item] },
    }))
  }

  const removeEntry = (section, index) => {
    setDraft((current) => ({
      ...current,
      content: {
        ...current.content,
        [section]: current.content[section].filter((_, itemIndex) => itemIndex !== index),
      },
    }))
  }

  const persistDraft = async () => {
    if (!draft.template_id) throw new Error('Choose a resume template before saving.')
    const payload = {
      template_id: draft.template_id,
      title: draft.title,
      content: draft.content,
    }
    const saved = editingId
      ? await updateResume({ token, resumeId: editingId, resume: payload })
      : await createResume({ token, resume: { ...payload, source: draft.source } })
    setEditingId(saved.id)
    setDraft((current) => ({ ...current, title: saved.title, source: saved.source }))
    await refreshBuilderData()
    return saved
  }

  const handleSave = async () => {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await persistDraft()
      setNotice('Resume saved to your account.')
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not save your resume.'))
    } finally {
      setBusy(false)
    }
  }

  const handleExport = async () => {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await persistDraft()
      setNotice('Use “Save as PDF” in the print dialog to download your resume.')
      window.setTimeout(() => window.print(), 100)
    } catch (requestError) {
      setError(getApiError(requestError, 'Could not save your resume before export.'))
    } finally {
      setBusy(false)
    }
  }

  const startNewResume = () => {
    setDraft({ ...EMPTY_RESUME, content: { ...EMPTY_CONTENT, full_name: profile?.username || '' } })
    setEditingId(null)
    setProfileStep(1)
    setExperienceLevel('')
    setIsStudent(null)
    setEducationLevel('')
    setError('')
    setNotice('')
    setPage('profile')
  }

  const finishProfileQuestions = () => {
    const recommendedFamily = experienceLevel === 'none' && isStudent
      ? 'modern'
      : RECOMMENDED_FAMILY_BY_EXPERIENCE[experienceLevel]
    setFamilyFilter(recommendedFamily || 'all')
    setPage('templates')
  }

  const remaining = builderData?.remaining_free_builds ?? 3
  const buildCount = builderData?.build_count ?? 0
  const canCreate = builderData ? Boolean(builderData.can_build) : true

  return (
    <main className="page-shell resume-builder-page">
      <AppHeader />
      <section className="resume-builder-hero">
        <div>
          <p className="eyebrow"><Sparkles aria-hidden="true" size={15} /> RESUME STUDIO</p>
          <h1>Build a resume that feels like you.</h1>
          <p className="muted">Choose from 30 ATS-friendly designs, customize every section, and save a print-ready PDF.</p>
        </div>
        <div className="resume-usage-card" aria-live="polite">
          <span className="resume-usage-icon"><FileText aria-hidden="true" size={20} /></span>
          <span>
            <strong>{paidBuilder ? `${activePlan.toUpperCase()} · Unlimited builds` : `${remaining} free build${remaining === 1 ? '' : 's'} left`}</strong>
            <small>{paidBuilder ? 'Resume creation and customization are unlocked.' : `${buildCount} of 3 free resumes created`}</small>
          </span>
        </div>
      </section>

      {error && <p className="notice error resume-builder-notice" role="alert">{error}</p>}
      {notice && <p className="notice resume-builder-notice" role="status">{notice}</p>}

      {page === 'profile' ? (
        <section aria-labelledby="resume-profile-title" className="resume-profile-flow">
          <div className="resume-profile-progress">
            <p className="eyebrow">Resume setup · Step {profileStep} of 2</p>
            <div
              aria-label={`Step ${profileStep} of 2`}
              aria-valuemax={2}
              aria-valuemin={1}
              aria-valuenow={profileStep}
              className="resume-profile-progress-track"
              role="progressbar"
            >
              <span style={{ width: `${(profileStep / 2) * 100}%` }} />
            </div>
          </div>

          {profileStep === 1 && (
            <div>
              <h2 id="resume-profile-title">How long have you been working?</h2>
              <p className="muted">We’ll find the best templates for your experience level.</p>
              <div aria-label="Work experience" className="resume-choice-grid">
                {EXPERIENCE_LEVELS.map((level) => (
                  <button
                    aria-pressed={experienceLevel === level.value}
                    className={`resume-choice-card ${experienceLevel === level.value ? 'selected' : ''}`}
                    key={level.value}
                    onClick={() => {
                      setExperienceLevel(level.value)
                      if (level.value !== 'none') setIsStudent(null)
                      setProfileStep(2)
                    }}
                    type="button"
                  >
                    {level.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {profileStep === 2 && (
            <div>
              {experienceLevel === 'none' ? (
                <>
                  <h2 id="resume-profile-title">Are you a student?</h2>
                  <p className="muted">We’ll use this to recommend a suitable resume layout.</p>
                  <div aria-label="Student status" className="resume-choice-grid resume-student-choice">
                    {[true, false].map((student) => (
                      <button
                        aria-pressed={isStudent === student}
                        className={`resume-choice-card ${isStudent === student ? 'selected' : ''}`}
                        key={String(student)}
                        onClick={() => {
                          setIsStudent(student)
                          finishProfileQuestions()
                        }}
                        type="button"
                      >
                        {student ? 'Yes' : 'No'}
                      </button>
                    ))}
                  </div>
                </>
              ) : (
                <>
                  <h2 id="resume-profile-title">What is your highest education level?</h2>
                  <p className="muted">Choose the highest level you’ve completed so we can organize your resume correctly.</p>
                  <div aria-label="Education level" className="resume-choice-grid">
                    {EDUCATION_LEVELS.map((level) => (
                      <button
                        aria-pressed={educationLevel === level}
                        className={`resume-choice-card ${educationLevel === level ? 'selected' : ''}`}
                        key={level}
                        onClick={() => {
                          setEducationLevel(level)
                          finishProfileQuestions()
                        }}
                        type="button"
                      >
                        {level}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {profileStep === 2 && (
            <button
              className="text-button resume-profile-back"
              onClick={() => setProfileStep((step) => step - 1)}
              type="button"
            >
              <ArrowLeft aria-hidden="true" size={16} /> Back
            </button>
          )}
        </section>
      ) : page === 'templates' ? (
        <>
          {!canCreate && (
            <section className="resume-upgrade-card">
              <div>
                <p className="eyebrow">Free builds used</p>
                <h2>Upgrade to keep building</h2>
                <p className="muted">Elite unlocks unlimited resume builds and uploaded resume customization.</p>
              </div>
              <Link className="button primary" to={DASHBOARD_PATH}>View plans <ArrowRight aria-hidden="true" size={16} /></Link>
            </section>
          )}

          <section aria-labelledby="resume-ats-title" className="resume-ats-section">
            <div>
              <p className="eyebrow">Application tracking systems</p>
              <h2 id="resume-ats-title">Choose an ATS-friendly layout</h2>
              <p>
                Browse {atsTemplates.length} clean, structured templates designed to make resume details
                easier for applicant tracking systems to read. ATS results can vary by employer and system.
              </p>
            </div>
            <div className="resume-ats-actions">
              <button
                className="button secondary"
                onClick={() => setFamilyFilter('ats')}
                type="button"
              >
                Browse ATS templates
              </button>
              <Link className="button primary" to={ATS_PATH}>
                Check my resume score
              </Link>
            </div>
          </section>

          <section className="resume-template-section">
            <div className="resume-section-heading">
              <div>
                <p className="eyebrow">30 ready-to-edit designs</p>
                <h2>Pick a starting template</h2>
                <p className="muted">
                  {isStudent
                    ? `Suggestions for students pursuing ${educationLevel}.`
                    : `Suggestions for ${EXPERIENCE_LEVELS.find((level) => level.value === experienceLevel)?.label.toLowerCase() || 'your experience level'}.`}
                </p>
              </div>
              <div className="resume-template-heading-actions">
                <button
                  className="button secondary"
                  onClick={() => {
                    setProfileStep(1)
                    setPage('profile')
                  }}
                  type="button"
                >
                  Edit preferences
                </button>
                <span className="resume-template-count">
                  {familyFilter === 'ats'
                    ? `${filteredTemplates.length} ATS templates`
                    : `${templates.length} templates`}
                </span>
              </div>
            </div>
            <div className="resume-family-filters" aria-label="Filter templates">
              {TEMPLATE_FAMILIES.map((family) => (
                <button
                  aria-pressed={familyFilter === family.id}
                  className={familyFilter === family.id ? 'active' : ''}
                  key={family.id}
                  onClick={() => setFamilyFilter(family.id)}
                  type="button"
                >
                  {family.label}
                </button>
              ))}
            </div>
            {busy && !builderData ? (
              <p className="resume-loading"><LoaderCircle className="resume-spinner" aria-hidden="true" size={18} /> Loading templates…</p>
            ) : (
              <div className="resume-template-grid">
                {filteredTemplates.map((template) => (
                  <TemplateCard
                    key={template.id}
                    template={template}
                    onChoose={canCreate ? startTemplate : () => setError('You have used all 3 free builds. Upgrade to Elite to continue.')}
                  />
                ))}
              </div>
            )}
          </section>

          <section className="resume-existing-section">
            <div className="resume-section-heading">
              <div>
                <p className="eyebrow">Have a resume already?</p>
                <h2>Upload and customize it</h2>
                <p className="muted">Upload a PDF, edit its extracted text, then apply any of the 30 templates.</p>
              </div>
              {builderData?.can_customize_upload ? (
                <label className="button secondary resume-upload-button">
                  <UploadCloud aria-hidden="true" size={17} /> {busy ? 'Importing…' : 'Upload PDF'}
                  <input
                    accept=".pdf,application/pdf"
                    disabled={busy}
                    onChange={(event) => {
                      void handleUpload(event.target.files?.[0])
                      event.target.value = ''
                    }}
                    type="file"
                  />
                </label>
              ) : (
                <Link className="button secondary" to={DASHBOARD_PATH}>Elite required <ArrowRight aria-hidden="true" size={16} /></Link>
              )}
            </div>
            {!builderData?.can_customize_upload && (
              <p className="resume-upload-gate">An active Elite subscription is required to upload and customize an existing resume.</p>
            )}
          </section>

          {builderData?.resumes?.length > 0 && (
            <section className="resume-saved-section">
              <div className="resume-section-heading">
                <div>
                  <p className="eyebrow">Your work</p>
                  <h2>Saved resumes</h2>
                </div>
                <button className="button secondary" onClick={startNewResume} type="button"><Plus aria-hidden="true" size={16} /> New resume</button>
              </div>
              <div className="resume-saved-list">
                {builderData.resumes.map((resume) => (
                  <article className="resume-saved-item" key={resume.id}>
                    <span className="resume-saved-icon"><FileText aria-hidden="true" size={18} /></span>
                    <span className="resume-saved-copy">
                      <strong>{resume.title}</strong>
                      <small>{templates.find((template) => template.id === resume.template_id)?.name || resume.template_id} · Updated {new Date(resume.updated_at).toLocaleDateString()}</small>
                    </span>
                    <button className="button secondary" disabled={resume.source === 'upload' && !paidBuilder} onClick={() => handleEdit(resume)} type="button">Open</button>
                  </article>
                ))}
              </div>
            </section>
          )}
        </>
      ) : (
        <section className="resume-editor-page">
          <div className="resume-editor-toolbar">
            <button className="text-button" onClick={() => setPage('templates')} type="button"><ArrowLeft aria-hidden="true" size={16} /> All templates</button>
            <label className="resume-title-field">
              Resume name
              <input maxLength={160} onChange={(event) => setDraft((current) => ({ ...current, title: event.target.value }))} value={draft.title} />
            </label>
            <div className="resume-editor-actions">
              <button className="button secondary" disabled={busy} onClick={handleSave} type="button">{busy ? 'Saving…' : 'Save'}</button>
              <button className="button primary" disabled={busy} onClick={handleExport} type="button"><Download aria-hidden="true" size={16} /> PDF</button>
            </div>
          </div>
          <div className="resume-editor-layout">
            <form className="resume-editor-form" onSubmit={(event) => event.preventDefault()}>
              <fieldset className="resume-form-section">
                <legend>Template</legend>
                <label>
                  Choose a design
                  <span className="resume-select-wrap">
                    <select value={draft.template_id} onChange={(event) => setDraft((current) => ({ ...current, template_id: event.target.value }))}>
                      {templates.map((template) => <option key={template.id} value={template.id}>{template.name}</option>)}
                    </select>
                    <ChevronDown aria-hidden="true" size={15} />
                  </span>
                </label>
                <small className="resume-source-note">{draft.source === 'upload' ? 'Imported resume · Elite or legacy access' : 'Template build'}</small>
              </fieldset>

              <fieldset className="resume-form-section">
                <legend>Contact details</legend>
                <div className="resume-form-grid">
                  <label>Full name<input maxLength={120} onChange={(event) => setContentField('full_name', event.target.value)} value={draft.content.full_name} /></label>
                  <label>Professional title<input maxLength={160} onChange={(event) => setContentField('headline', event.target.value)} value={draft.content.headline} /></label>
                  <label>Email<input maxLength={160} onChange={(event) => setContentField('email', event.target.value)} value={draft.content.email} /></label>
                  <label>Phone<input maxLength={60} onChange={(event) => setContentField('phone', event.target.value)} value={draft.content.phone} /></label>
                  <label>Location<input maxLength={160} onChange={(event) => setContentField('location', event.target.value)} value={draft.content.location} /></label>
                  <label>Portfolio / LinkedIn<input maxLength={500} onChange={(event) => setContentField('website', event.target.value)} value={draft.content.website} /></label>
                </div>
              </fieldset>

              {draft.source === 'upload' ? (
                <fieldset className="resume-form-section">
                  <legend>Imported resume text</legend>
                  <label>
                    Edit your resume
                    <textarea maxLength={30000} onChange={(event) => setContentField('raw_resume_text', event.target.value)} rows={18} value={draft.content.raw_resume_text} />
                  </label>
                </fieldset>
              ) : (
                <>
                  <fieldset className="resume-form-section">
                    <legend>Professional summary</legend>
                    <label>Summary<textarea maxLength={5000} onChange={(event) => setContentField('summary', event.target.value)} rows={4} value={draft.content.summary} /></label>
                    <label>Skills <small>Separate skills with commas</small>
                      <input
                        maxLength={2000}
                        onChange={(event) => setContentField('skills', event.target.value.split(',').map((skill) => skill.trim()).filter(Boolean))}
                        value={draft.content.skills.join(', ')}
                      />
                    </label>
                  </fieldset>
                  <fieldset className="resume-form-section">
                    <legend>Experience</legend>
                    {draft.content.experience.map((item, index) => (
                      <div className="resume-edit-entry" key={`experience-${index}`}>
                        <button aria-label="Remove experience" className="resume-remove-entry" onClick={() => removeEntry('experience', index)} type="button"><X aria-hidden="true" size={15} /></button>
                        <div className="resume-form-grid">
                          <label>Role<input maxLength={160} onChange={(event) => updateEntry('experience', index, 'role', event.target.value)} value={item.role} /></label>
                          <label>Company<input maxLength={160} onChange={(event) => updateEntry('experience', index, 'company', event.target.value)} value={item.company} /></label>
                          <label className="resume-full-field">Dates<input maxLength={100} onChange={(event) => updateEntry('experience', index, 'dates', event.target.value)} value={item.dates} /></label>
                          <label className="resume-full-field">Achievements<textarea maxLength={5000} onChange={(event) => updateEntry('experience', index, 'description', event.target.value)} rows={3} value={item.description} /></label>
                        </div>
                      </div>
                    ))}
                    <button className="resume-add-entry" onClick={() => addEntry('experience', { role: '', company: '', dates: '', description: '' })} type="button"><Plus aria-hidden="true" size={15} /> Add experience</button>
                  </fieldset>
                  <fieldset className="resume-form-section">
                    <legend>Education</legend>
                    {draft.content.education.map((item, index) => (
                      <div className="resume-edit-entry" key={`education-${index}`}>
                        <button aria-label="Remove education" className="resume-remove-entry" onClick={() => removeEntry('education', index)} type="button"><X aria-hidden="true" size={15} /></button>
                        <div className="resume-form-grid">
                          <label>Degree<input maxLength={160} onChange={(event) => updateEntry('education', index, 'degree', event.target.value)} value={item.degree} /></label>
                          <label>School<input maxLength={160} onChange={(event) => updateEntry('education', index, 'institution', event.target.value)} value={item.institution} /></label>
                          <label className="resume-full-field">Dates<input maxLength={100} onChange={(event) => updateEntry('education', index, 'dates', event.target.value)} value={item.dates} /></label>
                          <label className="resume-full-field">Details<textarea maxLength={2000} onChange={(event) => updateEntry('education', index, 'details', event.target.value)} rows={2} value={item.details} /></label>
                        </div>
                      </div>
                    ))}
                    <button className="resume-add-entry" onClick={() => addEntry('education', { degree: '', institution: '', dates: '', details: '' })} type="button"><Plus aria-hidden="true" size={15} /> Add education</button>
                  </fieldset>
                  <fieldset className="resume-form-section">
                    <legend>Projects</legend>
                    {draft.content.projects.map((item, index) => (
                      <div className="resume-edit-entry" key={`project-${index}`}>
                        <button aria-label="Remove project" className="resume-remove-entry" onClick={() => removeEntry('projects', index)} type="button"><X aria-hidden="true" size={15} /></button>
                        <div className="resume-form-grid">
                          <label>Project<input maxLength={160} onChange={(event) => updateEntry('projects', index, 'name', event.target.value)} value={item.name} /></label>
                          <label>Link<input maxLength={500} onChange={(event) => updateEntry('projects', index, 'link', event.target.value)} value={item.link} /></label>
                          <label className="resume-full-field">Description<textarea maxLength={3000} onChange={(event) => updateEntry('projects', index, 'description', event.target.value)} rows={3} value={item.description} /></label>
                        </div>
                      </div>
                    ))}
                    <button className="resume-add-entry" onClick={() => addEntry('projects', { name: '', link: '', description: '' })} type="button"><Plus aria-hidden="true" size={15} /> Add project</button>
                  </fieldset>
                </>
              )}
            </form>

            <aside className="resume-preview-column">
              <div className="resume-preview-heading"><span><Check aria-hidden="true" size={14} /> Live preview</span><small>{selectedTemplate?.name}</small></div>
              <ResumePreview template={selectedTemplate} content={draft.content} />
            </aside>
          </div>
        </section>
      )}
    </main>
  )
}
