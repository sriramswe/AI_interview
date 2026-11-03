import { Link } from 'react-router-dom'
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  Check,
  CheckCircle2,
  FileText,
  LoaderCircle,
  MapPin,
  Menu,
  UploadCloud,
  X,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useInterviewApp } from '../../context/useInterviewApp'
import TargetRoleField from '../interview/TargetRoleField'
import { ADMIN_PATH, ATS_PATH, LOGIN_PATH, PROFILE_PATH, REGISTER_PATH, RESUME_BUILDER_PATH } from '../../routing/routes'
import ProgressTracker from './ProgressTracker'

const TECHNICAL_FOCUS_AREAS = [
  'Frontend',
  'Backend',
  'Database',
  'AI/ML',
  'Cloud & DevOps',
  'Testing',
  'System Design',
  'Security',
  'Project Deep Dive',
]

const INTERVIEW_REGIONS = [
  'India',
  'United States',
  'United Kingdom',
  'Canada',
  'Australia',
  'Germany',
  'Singapore',
  'United Arab Emirates',
  'Remote / Global',
]

const REGION_COMPANY_SUGGESTIONS = {
  India: [
    'Tata Consultancy Services (TCS)',
    'Infosys',
    'Wipro',
    'HCLTech',
    'Tech Mahindra',
    'Flipkart',
    'Zoho',
    'PhonePe',
    'Freshworks',
    'Razorpay',
  ],
  'United States': [
    'Google',
    'Microsoft',
    'Amazon',
    'Apple',
    'Meta',
    'Netflix',
    'Nvidia',
    'Salesforce',
    'OpenAI',
    'Anthropic',
  ],
  'United Kingdom': [
    'ARM',
    'Barclays',
    'HSBC',
    'Revolut',
    'DeepMind',
    'Wise',
    'Monzo',
    'AstraZeneca',
  ],
  Canada: [
    'Shopify',
    'Royal Bank of Canada',
    'TD Bank',
    'Scotiabank',
    'Thomson Reuters',
    'Wealthsimple',
    'OpenText',
  ],
  Australia: [
    'Atlassian',
    'Canva',
    'Commonwealth Bank',
    'WiseTech Global',
    'Telstra',
    'Xero',
    'REA Group',
  ],
  Germany: [
    'SAP',
    'Siemens',
    'BMW',
    'Mercedes-Benz',
    'Deutsche Telekom',
    'Zalando',
    'Delivery Hero',
    'N26',
  ],
  Singapore: [
    'Grab',
    'Sea',
    'Shopee',
    'DBS',
    'OCBC',
    'UOB',
    'GovTech Singapore',
  ],
  'United Arab Emirates': [
    'Careem',
    'Noon',
    'G42',
    'Emirates Group',
    'e&',
    'talabat',
  ],
}

export function AppHeader() {
  const { handleHome, handleLogout, profile, subscription } = useInterviewApp()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const displayName = profile?.username?.trim() || ''
  const avatarLabel = displayName
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase() || 'U'
  return (
    <header className="topbar app-header">
      <Link className="brand" to="/" onClick={handleHome}>
        <span className="brand-mark">IA</span> InterviewAI
      </Link>
      <div className="account">
        {profile ? (
          <>
            <button
              aria-controls="app-header-menu"
              aria-expanded={mobileMenuOpen}
              aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
              className="app-mobile-menu-toggle md:hidden"
              onClick={() => setMobileMenuOpen((open) => !open)}
              type="button"
            >
              {mobileMenuOpen ? <X aria-hidden="true" size={20} /> : <Menu aria-hidden="true" size={20} />}
            </button>
            <div
              className={`app-header-menu ${mobileMenuOpen ? 'flex' : 'hidden'} md:flex md:flex-row md:items-center md:gap-4`}
              id="app-header-menu"
            >
              <nav aria-label="Main navigation" className="app-header-nav">
                <Link className="app-header-link" onClick={() => setMobileMenuOpen(false)} to={ATS_PATH}>ATS Checker</Link>
                {/* <Link className="app-header-link" onClick={() => setMobileMenuOpen(false)} to={RESUME_BUILDER_PATH}>Resume builder</Link> */}
                {(profile.role === 'admin' || profile.is_super_admin) && ( 
                  <Link className="app-header-link" onClick={() => setMobileMenuOpen(false)} to={ADMIN_PATH}>Admin</Link>
                )}
              </nav>
              <div className="app-header-actions">
                <span className={`plan-pill plan-pill-${subscription?.plan || 'free'}`}>
                  {subscription?.plan === 'legacy_resume'
                    ? 'Legacy resume plan'
                    : `${subscription?.plan || 'free'} plan`}
                </span>
                <Link
                  aria-label={`Open ${displayName || 'your'} profile`}
                  className="profile-account-link"
                  onClick={() => setMobileMenuOpen(false)}
                  to={PROFILE_PATH}
                >
                  <span aria-hidden="true" className="profile-account-avatar">{avatarLabel}</span>
                  <span className="profile-account-name">{displayName || 'Profile'}</span>
                </Link>
                <button className="app-sign-out" type="button" onClick={handleLogout}>Sign out</button>
              </div>
            </div>
          </>
        ) : (
          <>
            <Link className="text-button" to="/">Home</Link>
            <Link className="text-button" to={LOGIN_PATH}>Sign in</Link>
            <Link className="button primary" style={{ padding: '6px 14px', fontSize: '13px' }} to={REGISTER_PATH}>Get started</Link>
          </>
        )}
      </div>
    </header>
  )
}

export function DashboardHero() {
  return (
    <section id="home" className="hero-card">
      <div>
        <p className="eyebrow">Your AI mock interview starts here</p>
        <h1>Get interview-ready, one answer at a time.</h1>
        <p className="muted">Set your target role, add your resume, and practice questions grounded in your own experience.</p>
      </div>
      <div className="hero-orb" aria-hidden="true"><span>01</span></div>
    </section>
  )
}

function SetupFlowProgress({ currentStep, onStepChange }) {
  const steps = [
    { number: '01', title: 'Your role', detail: 'Who you are' },
    { number: '02', title: 'Interview setup', detail: 'Where & what' },
    { number: '03', title: 'Your resume', detail: 'Optional' },
    { number: '04', title: 'Review', detail: 'Ready to practice' },
  ]

  return (
    <nav aria-label="Interview setup progress" className="setup-wizard-progress">
      <div className="setup-wizard-track">
        <span style={{ width: `${((currentStep - 1) / (steps.length - 1)) * 100}%` }} />
      </div>
      <ol className="setup-flow-progress">
        {steps.map((step, index) => {
          const stepNumber = index + 1
          const state = stepNumber === currentStep
            ? 'active'
            : stepNumber < currentStep
              ? 'complete'
              : ''
          return (
            <li className={`setup-flow-step ${state}`} key={step.number}>
              <button
                aria-current={stepNumber === currentStep ? 'step' : undefined}
                aria-label={`Step ${stepNumber}: ${step.title}${stepNumber < currentStep ? ', completed' : ''}`}
                className="setup-flow-step-button"
                disabled={stepNumber >= currentStep}
                onClick={() => onStepChange(stepNumber)}
                type="button"
              >
                <span className="setup-flow-number">
                  {stepNumber < currentStep ? <Check aria-hidden="true" size={14} /> : step.number}
                </span>
                <span className="setup-flow-copy">
                  <strong>{step.title}</strong>
                  <small>{step.detail}</small>
                </span>
              </button>
            </li>
          )
        })}
      </ol>
      <p className="setup-step-count">Step {currentStep} of {steps.length}</p>
    </nav>
  )
}

function InterviewSetupCard() {
  const [currentStep, setCurrentStep] = useState(1)
  const [customCompanySelected, setCustomCompanySelected] = useState(false)
  const [customGeographySelected, setCustomGeographySelected] = useState(false)
  const [stepError, setStepError] = useState('')
  const [resumeChoice, setResumeChoice] = useState('')
  const {
    busy,
    company,
    companySuggestions,
    difficultyLevel,
    geography,
    interviewerName,
    interviewProgress,
    isPanel,
    handleCreateCheckout,
    handleCompanyChange,
    handleDifficultyChange,
    handleGeographyChange,
    handleInterviewerChange,
    handleJobDescriptionChange,
    handleLoadRounds,
    handlePanelChange,
    handleQuestionsPerRoundChange,
    handleRoleChange,
    handleResumeFileChange,
    handleStartInterview,
    handleSubRoleChange,
    handleTechnicalCategoriesChange,
    jobDescription,
    role,
    resumeFile,
    rounds,
    subscription,
    subRole,
    technicalCategories,
    questionsPerRound,
  } = useInterviewApp()
  const currentPlan = subscription?.plan || 'free'
  const canUseJobDescription = ['pro', 'legacy_resume', 'elite'].includes(currentPlan)
  const canUseCompanyQuestions = ['pro', 'legacy_resume', 'elite'].includes(currentPlan)
    && (subscription?.company_questions_remaining == null
      || subscription.company_questions_remaining > 0)
  const canUsePanel = currentPlan === 'elite'
  const toggleTechnicalCategory = (category) => {
    handleTechnicalCategoriesChange((current) => current.includes(category)
      ? current.filter((value) => value !== category)
      : [...current, category])
  }
  const hasPlanRestrictedOptions = Boolean(
    (jobDescription.trim() && !canUseJobDescription)
    || (company && !canUseCompanyQuestions)
    || (isPanel && !canUsePanel),
  )

  useEffect(() => {
    if (!canUsePanel && isPanel) handlePanelChange(false)
  }, [canUsePanel, handlePanelChange, isPanel])

  const knownCompanySuggestions = new Set([
    ...companySuggestions,
    ...Object.values(REGION_COMPANY_SUGGESTIONS).flat(),
  ])
  const isCustomCompany = customCompanySelected
    || Boolean(company && !knownCompanySuggestions.has(company))
  const regionalCompanySuggestions = REGION_COMPANY_SUGGESTIONS[geography]
  const companyOptions = regionalCompanySuggestions
    ? [
        ...regionalCompanySuggestions,
        ...(company && !isCustomCompany && !regionalCompanySuggestions.includes(company) ? [company] : []),
      ]
    : companySuggestions
  const isCustomGeography = customGeographySelected
    || Boolean(geography && !INTERVIEW_REGIONS.includes(geography))

  const goToStep = (step) => {
    setCurrentStep(step)
    setStepError('')
  }

  const continueFromStep = () => {
    if (currentStep === 1 && !role.trim()) {
      setStepError('Enter your target role to continue.')
      return
    }
    if (currentStep === 3 && !resumeChoice && !resumeFile) setResumeChoice('skip')
    setStepError('')
    setCurrentStep((step) => Math.min(4, step + 1))
  }

  return (
    <section aria-labelledby="setup-title" className="panel setup-wizard">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Your interview, your pace</p>
          <h2 id="setup-title">
            {currentStep === 1 && 'What role are you preparing for?'}
            {currentStep === 2 && 'Let’s shape your interview'}
            {currentStep === 3 && 'Want to add your resume?'}
            {currentStep === 4 && 'Your practice is ready'}
          </h2>
          <p className="muted">
            {currentStep === 1 && 'We’ll use your role to choose relevant interview questions.'}
            {currentStep === 2 && 'Add a company or choose your preferred practice style. You can skip the optional details.'}
            {currentStep === 3 && 'A resume helps us ask about your real skills and projects. It’s optional and uses one resume analysis from your monthly allowance.'}
            {currentStep === 4 && 'Review your choices before we start your personalized mock interview.'}
          </p>
        </div>
      </div>
      <SetupFlowProgress currentStep={currentStep} onStepChange={goToStep} />
      <form
        className="stack-form setup-wizard-form"
        onSubmit={currentStep === 4 ? handleStartInterview : (event) => event.preventDefault()}
      >
        {currentStep === 1 && (
          <div className="setup-step-content" key="role">
            <TargetRoleField
              autoFocus
              onChange={handleRoleChange}
              required
              value={role}
            />
            <label>
              Specialization <span className="resume-optional-label">· optional</span>
              <input
                value={subRole}
                onChange={(event) => handleSubRoleChange(event.target.value)}
                placeholder="For example: Backend, UX research, Data science"
              />
            </label>
            <div className="setup-help-card">
              <span className="setup-help-icon">1</span>
              <p>We’ll tailor questions to your role and experience—not apply for jobs on your behalf.</p>
            </div>
          </div>
        )}

        {currentStep === 2 && (
          <div className="setup-step-content" key="details">
            <label>
              Company you’re practicing for <span className="resume-optional-label">· optional</span>
              <span className="setup-location-wrap">
                <Building2 aria-hidden="true" size={17} />
                <select
                  className="has-leading-icon"
                  onChange={(event) => {
                    const selectedCompany = event.target.value
                    const isCustom = selectedCompany === 'other'
                    setCustomCompanySelected(isCustom)
                    handleCompanyChange(isCustom ? '' : selectedCompany)
                  }}
                  value={!canUseCompanyQuestions ? '' : isCustomCompany ? 'other' : company}
                >
                  <option value="">General interview practice</option>
                  {canUseCompanyQuestions && companyOptions.map((name) => (
                    <option key={name} value={name}>{name}</option>
                  ))}
                  {canUseCompanyQuestions && <option value="other">Other company</option>}
                </select>
              </span>
              {!canUseCompanyQuestions && (
                <span className="fine-print">
                  {currentPlan === 'free'
                    ? 'Company-specific questions are included with Pro and Elite.'
                    : 'You have used this month’s company-specific question allowance.'}
                </span>
              )}
            </label>
            <label>
              Interview region <span className="resume-optional-label">· optional</span>
              <span className="setup-location-wrap">
                <MapPin aria-hidden="true" size={17} />
                <select
                  className="has-leading-icon"
                  onChange={(event) => {
                    const selectedRegion = event.target.value
                    const isCustom = selectedRegion === 'other'
                    setCustomGeographySelected(isCustom)
                    handleGeographyChange(isCustom ? '' : selectedRegion)
                  }}
                  value={isCustomGeography ? 'other' : geography}
                >
                  <option value="">Choose a region</option>
                  {INTERVIEW_REGIONS.map((region) => (
                    <option key={region} value={region}>{region}</option>
                  ))}
                  <option value="other">Other region</option>
                </select>
              </span>
              {regionalCompanySuggestions && (
                <span className="fine-print">Company suggestions are tailored to {geography}.</span>
              )}
            </label>
            {canUseCompanyQuestions && isCustomCompany && (
              <label>
                Company name <span className="resume-optional-label">· optional</span>
                <input
                  maxLength={255}
                  onChange={(event) => handleCompanyChange(event.target.value)}
                  placeholder="Enter a company name"
                  value={company}
                />
              </label>
            )}
            {isCustomGeography && (
              <label>
                Region name <span className="resume-optional-label">· optional</span>
                <input
                  maxLength={120}
                  onChange={(event) => handleGeographyChange(event.target.value)}
                  placeholder="Enter a country or region"
                  value={geography}
                />
              </label>
            )}
            <label>
              Practice difficulty
              <select value={difficultyLevel} onChange={(event) => handleDifficultyChange(event.target.value)}>
                <option value={1}>Junior — build confidence</option>
                <option value={2}>Mid-level — balanced practice</option>
                <option value={3}>Senior — deeper challenges</option>
              </select>
            </label>
            <label>
              Questions per round
              <select
                onChange={(event) => handleQuestionsPerRoundChange(event.target.value)}
                value={questionsPerRound}
              >
                <option value={5}>5 questions · Quick practice</option>
                <option value={10}>10 questions · Balanced practice</option>
                <option value={20}>20 questions · Full practice</option>
              </select>
            </label>
            <fieldset className="technical-focus-picker">
              <legend>Technical question categories <span className="resume-optional-label">· optional</span></legend>
              <p className="fine-print">
                Questions will be shuffled across these areas. With a resume and no manual selection,
                categories are detected from its skills and projects.
              </p>
              <div className="technical-focus-options">
                {TECHNICAL_FOCUS_AREAS.map((category) => (
                  <label
                    className={technicalCategories.includes(category) ? 'selected' : ''}
                    key={category}
                  >
                    <input
                      checked={technicalCategories.includes(category)}
                      disabled={!technicalCategories.includes(category) && technicalCategories.length >= 8}
                      onChange={() => toggleTechnicalCategory(category)}
                      type="checkbox"
                    />
                    <span>{category}</span>
                  </label>
                ))}
              </div>
              <small>
                {technicalCategories.length
                  ? `${technicalCategories.length} selected · questions will be shuffled`
                  : 'Auto-detect from resume skills and projects, or from role if no resume is added'}
              </small>
            </fieldset>
            <fieldset className="interviewer-picker">
              <legend>Choose your interviewer</legend>
              <div className="interviewer-options">
                {[
                  { name: 'Adinath', role: 'Technical mentor', icon: 'A' },
                  { name: 'Veda', role: 'Clarity specialist', icon: 'V' },
                ].map((person) => (
                  <button
                    aria-pressed={interviewerName === person.name}
                    className={`interviewer-option ${interviewerName === person.name ? 'selected' : ''}`}
                    key={person.name}
                    onClick={() => handleInterviewerChange(person.name)}
                    type="button"
                  >
                    <span className="interviewer-avatar">{person.icon}</span>
                    <span><strong>{person.name}</strong><small>{person.role}</small></span>
                  </button>
                ))}
              </div>
            </fieldset>
            <div className="setup-optional-card">
              <div className="panel-mode-option">
                <input
                  id="panel-interview"
                  checked={canUsePanel && isPanel}
                  disabled={!canUsePanel}
                  onChange={(event) => handlePanelChange(event.target.checked)}
                  type="checkbox"
                />
                <div>
                  <label htmlFor="panel-interview">
                    <strong>Panel interview</strong>
                    <small>{canUsePanel ? 'Practice with multiple interview personas' : 'Elite plan required'}</small>
                  </label>
                </div>
                {!canUsePanel && (
                  <button
                    className="text-button"
                    disabled={busy}
                    onClick={() => handleCreateCheckout('elite')}
                    type="button"
                  >
                    Upgrade
                  </button>
                )}
              </div>
            </div>
            <div className="setup-optional-card">
              <label htmlFor="job-description">
                Job description <span className="resume-optional-label">· {canUseJobDescription ? 'optional' : 'Pro plan'}</span>
                <textarea
                  id="job-description"
                  disabled={!canUseJobDescription}
                  rows="3"
                  value={jobDescription}
                  onChange={(event) => handleJobDescriptionChange(event.target.value)}
                  placeholder={canUseJobDescription
                    ? 'Paste a job description for more targeted interview questions.'
                    : 'Upgrade to Pro to tailor practice to a job description.'}
                />
              </label>
              {!canUseJobDescription && (
                <button
                  className="text-button"
                  disabled={busy}
                  onClick={() => handleCreateCheckout('pro')}
                  type="button"
                >
                  Get Pro
                </button>
              )}
            </div>
            <div className="setup-round-preview">
              <button className="button secondary" type="button" onClick={handleLoadRounds}>
                Preview likely interview rounds
              </button>
              {rounds.length > 0 && (
                <ol className="round-list">
                  {rounds.map((round, index) => (
                    <li key={round.name}>
                      <span>{index + 1}. {round.name}</span>
                      <small>{round.evaluation_criteria?.[0]}</small>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </div>
        )}

        {currentStep === 3 && (
          <div className="setup-step-content" key="resume">
            <fieldset className="resume-choice-grid">
              <legend>Choose what works for you</legend>
              <label className={`resume-choice-card ${resumeFile ? 'selected' : resumeChoice === 'upload' ? 'selected' : ''}`} htmlFor="resume-upload">
                <input
                  accept="application/pdf,.pdf"
                  className="resume-upload-input"
                  id="resume-upload"
                  onChange={(event) => {
                    const file = event.target.files?.[0] || null
                    if (file && !file.name.toLowerCase().endsWith('.pdf')) {
                      handleResumeFileChange(null)
                      setResumeChoice('')
                      setStepError('Please choose a PDF resume, or continue without one.')
                      event.target.value = ''
                      return
                    }
                    handleResumeFileChange(file)
                    setResumeChoice(file ? 'upload' : '')
                    setStepError('')
                  }}
                  type="file"
                />
                <span className="resume-choice-icon"><UploadCloud aria-hidden="true" size={21} /></span>
                <strong>{resumeFile?.name || 'I have a resume'}</strong>
                <small>
                  {resumeFile
                    ? `${(resumeFile.size / (1024 * 1024)).toFixed(2)} MB · Ready to personalize questions`
                    : 'Upload a PDF and we’ll use your experience to shape the interview.'}
                </small>
                <span className="resume-choice-action">{resumeFile ? 'Change PDF' : 'Choose PDF'}</span>
              </label>
              <button
                aria-pressed={resumeChoice === 'skip' && !resumeFile}
                className={`resume-choice-card ${resumeChoice === 'skip' && !resumeFile ? 'selected' : ''}`}
                onClick={() => {
                  handleResumeFileChange(null)
                  setResumeChoice('skip')
                  setStepError('')
                }}
                type="button"
              >
                <span className="resume-choice-icon no-resume">↗</span>
                <strong>I’ll continue without one</strong>
                <small>You can still practice role-based and company-specific questions.</small>
                <span className="resume-choice-action">No resume needed</span>
              </button>
            </fieldset>
            <p className="setup-privacy-note">
              Your resume is used to personalize this interview; it is not used to apply for jobs.
            </p>
          </div>
        )}

        {currentStep === 4 && (
          <div className="setup-step-content" key="review">
            <dl className="setup-review-list">
              <div><dt>Role</dt><dd>{role || 'Not provided'}{subRole && subRole !== role ? ` · ${subRole}` : ''}</dd></div>
              <div><dt>Company</dt><dd>{company || 'General interview practice'}</dd></div>
              <div><dt>Region</dt><dd>{geography || 'Not specified'}</dd></div>
              <div><dt>Difficulty</dt><dd>{({ 1: 'Junior', 2: 'Mid-level', 3: 'Senior' })[difficultyLevel] || 'Mid-level'}</dd></div>
              <div><dt>Questions per round</dt><dd>{questionsPerRound} questions</dd></div>
              <div><dt>Interviewer</dt><dd>{interviewerName}{isPanel ? ' · Panel mode' : ''}</dd></div>
              <div><dt>Resume</dt><dd>{resumeFile?.name || 'Not added — role-based questions will be used'}</dd></div>
              <div>
                <dt>Technical categories</dt>
                <dd>{technicalCategories.length
                  ? `${technicalCategories.join(', ')} · shuffled`
                  : 'Auto-detected from resume and role'}</dd>
              </div>
              {rounds.length > 0 && (
                <div>
                  <dt>Interview rounds</dt>
                  <dd>{rounds.map((round) => round.name).join(' → ')}</dd>
                </div>
              )}
            </dl>
            <div className="setup-help-card">
              <span className="setup-help-icon"><CheckCircle2 aria-hidden="true" size={19} /></span>
              <p>
                {resumeFile
                  ? 'We’ll scan your PDF, identify your experience level and technical topics, and shuffle resume-based questions across the selected categories.'
                  : 'We’ll create questions for your role. You can add a resume next time for more personalized practice.'}
              </p>
            </div>
          </div>
        )}

        {interviewProgress && (
          <section
            aria-label="Resume interview preparation"
            aria-live="polite"
            className={`resume-progress ${interviewProgress.stage === 'failed' ? 'failed' : ''}`}
            role="status"
          >
            <div className="resume-progress-heading">
              <span className="resume-progress-icon">
                {interviewProgress.stage === 'failed'
                  ? <FileText aria-hidden="true" size={18} />
                  : <LoaderCircle aria-hidden="true" className="resume-spinner" size={18} />}
              </span>
              <span>
                <strong>
                  {interviewProgress.stage === 'uploading' && 'Uploading your resume'}
                  {interviewProgress.stage === 'scanning' && 'Reading your resume'}
                  {interviewProgress.stage === 'preparing' && 'Preparing resume-based questions'}
                  {interviewProgress.stage === 'failed' && 'Resume preparation could not finish'}
                </strong>
                <small>
                  {interviewProgress.stage === 'uploading'
                    ? `${interviewProgress.percent}% uploaded`
                    : interviewProgress.stage === 'scanning'
                      ? 'Extracting text, skills, and experience from your PDF'
                      : interviewProgress.stage === 'preparing'
                        ? 'Building your opening question from your actual experience'
                        : 'Review the error above, then retry when the AI provider is available.'}
                </small>
              </span>
            </div>
            <div
              aria-label={interviewProgress.stage === 'uploading'
                ? `Resume upload ${interviewProgress.percent}% complete`
                : 'Resume processing in progress'}
              className="resume-progress-track"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={interviewProgress.stage === 'uploading' ? interviewProgress.percent : undefined}
              aria-valuetext={interviewProgress.stage === 'uploading'
                ? `${interviewProgress.percent}% uploaded`
                : interviewProgress.stage === 'failed'
                  ? 'Resume preparation failed'
                  : 'Resume processing in progress'}
            >
              <span
                className={['scanning', 'preparing'].includes(interviewProgress.stage) ? 'indeterminate' : ''}
                style={{ width: `${interviewProgress.percent}%` }}
              />
            </div>
            <ol className="resume-progress-steps">
              {['Upload PDF', 'Extract experience', 'Build interview'].map((step, index) => {
                const activeIndex = {
                  uploading: 0,
                  scanning: 1,
                  preparing: 2,
                  failed: -1,
                }[interviewProgress.stage]
                const completed = index < activeIndex
                const active = index === activeIndex
                return (
                  <li className={completed ? 'complete' : active ? 'active' : ''} key={step}>
                    {completed && <CheckCircle2 aria-hidden="true" size={13} />}
                    {step}
                  </li>
                )
              })}
            </ol>
          </section>
        )}

        {stepError && <p className="notice" role="alert">{stepError}</p>}
        <div className="setup-wizard-actions">
          {currentStep > 1 && (
            <button className="button secondary" onClick={() => goToStep(currentStep - 1)} type="button">
              <ArrowLeft aria-hidden="true" size={16} /> Back
            </button>
          )}
          {currentStep < 4
            ? (
              <button className="button primary setup-next-button" onClick={continueFromStep} type="button">
                {currentStep === 3 && !resumeFile ? 'Continue without resume' : 'Continue'}
                <ArrowRight aria-hidden="true" size={16} />
              </button>
            )
            : (
              <button
                className="button primary setup-next-button"
                disabled={busy || hasPlanRestrictedOptions}
                type="submit"
              >
                {busy
                  ? resumeFile ? 'Scanning resume & preparing interview…' : 'Preparing your interview…'
                  : 'Start my mock interview'}
                {!busy && <ArrowRight aria-hidden="true" size={16} />}
              </button>
            )}
        </div>
        {currentStep === 4 && hasPlanRestrictedOptions && (
          <p className="notice" role="alert">
            Upgrade or remove plan-only options before starting this interview.
          </p>
        )}
      </form>
    </section>
  )
}

function BillingPanel() {
  const [copyStatus, setCopyStatus] = useState('')
  const {
    busy,
    checkout,
    handleCreateCheckout,
    handlePaymentFileChange,
    handlePaymentReferenceChange,
    handlePaymentProofSubmit,
    paymentFile,
    paymentReference,
    paymentSubmissions,
    subscription,
  } = useInterviewApp()

  const copyToClipboard = async (value, label) => {
    try {
      await navigator.clipboard.writeText(value)
      setCopyStatus(`${label} copied.`)
    } catch {
      setCopyStatus(`Could not copy ${label.toLowerCase()}. Select and copy it manually.`)
    }
  }

  const upiAppLink = checkout?.payment_uri
    ? navigator.userAgent.toLowerCase().includes('android')
      ? `${checkout.payment_uri.replace(/^upi:\/\//, 'intent://')}#Intent;scheme=upi;S.browser_fallback_url=${encodeURIComponent(window.location.href)};end`
      : checkout.payment_uri
    : ''

  return (
    <section className="panel">
      <p className="eyebrow">Plans & payments</p>
      <h2>Current plan: {subscription?.plan === 'legacy_resume' ? 'Legacy resume' : subscription?.plan || 'free'}</h2>
      <p className="muted">Pro ₹299 · Elite ₹599 per month. UPI screenshot review is manual.</p>
      {subscription && (
        <p className="fine-print">
          This month: {subscription.interviews_used} / {subscription.interview_limit} mock interviews ·{' '}
          {subscription.resume_analyses_used} / {subscription.resume_analysis_limit} resume analyses ·{' '}
          {subscription.company_questions_used} / {subscription.company_question_limit} company-specific questions
        </p>
      )}
      <div className="button-row">
        <button className="button secondary" type="button" disabled={busy} onClick={() => handleCreateCheckout('pro')}>Get Pro</button>
        <button className="button secondary" type="button" disabled={busy} onClick={() => handleCreateCheckout('elite')}>Get Elite</button>
      </div>
      {checkout && (
        <div className="checkout-card">
          <h3>{checkout.plan.toUpperCase()} · ₹{checkout.amount_rupees}</h3>
          <img
            className="payment-qr"
            alt={`UPI payment QR for ${checkout.plan} plan, ₹${checkout.amount_rupees}`}
            src={`data:image/svg+xml;base64,${checkout.qr_svg_base64}`}
          />
          <a className="button primary full-width" href={upiAppLink}>Open in UPI app</a>
          <a
            className="text-button"
            download={`interviewai-${checkout.plan}-payment-qr.svg`}
            href={`data:image/svg+xml;base64,${checkout.qr_svg_base64}`}
          >
            Download QR for payment
          </a>
          <p className="fine-print">
            On a phone, open this link in a UPI app. On a computer, scan the QR with your phone.
            There is no universal UPI web checkout for manual payments.
          </p>
          <dl className="payment-instructions">
            <div><dt>Pay to</dt><dd>{checkout.payee_name}</dd></div>
            <div><dt>UPI ID</dt><dd>{checkout.upi_id}</dd></div>
            <div><dt>Amount</dt><dd>₹{checkout.amount_rupees} INR</dd></div>
          </dl>
          <div className="button-row payment-link-actions">
            <button
              className="button secondary"
              onClick={() => copyToClipboard(checkout.upi_id, 'UPI ID')}
              type="button"
            >
              Copy UPI ID
            </button>
            <button
              className="button secondary"
              onClick={() => copyToClipboard(checkout.payment_uri, 'UPI payment link')}
              type="button"
            >
              Copy UPI link
            </button>
          </div>
          {copyStatus && <p className="fine-print" role="status">{copyStatus}</p>}
          <form className="stack-form" onSubmit={handlePaymentProofSubmit}>
            <label>
              UPI transaction ID / UTR <span className="resume-optional-label">· recommended</span>
              <input
                autoComplete="off"
                maxLength={120}
                onChange={(event) => handlePaymentReferenceChange(event.target.value)}
                placeholder="Enter the UPI transaction reference"
                value={paymentReference}
              />
            </label>
            <label>
              Payment receipt screenshot
              <input
                required
                accept="image/png,image/jpeg,image/webp"
                type="file"
                onChange={(event) => handlePaymentFileChange(event.target.files?.[0] || null)}
              />
            </label>
            <button className="button secondary full-width" disabled={busy || !paymentFile} type="submit">
              Submit payment for review
            </button>
          </form>
          <p className="fine-print">Your plan activates after an administrator verifies the payment. Do not upload a screenshot that contains unrelated personal or banking information.</p>
        </div>
      )}
      {paymentSubmissions.length > 0 && (
        <div className="payment-history">
          <h3>Payment requests</h3>
          {paymentSubmissions.map((payment) => (
            <article className="payment-history-item" key={payment.payment_id}>
              <span>
                <strong>{payment.plan.toUpperCase()} · ₹{payment.amount_rupees}</strong>
                <small>Request #{payment.payment_id} · {new Date(payment.submitted_at).toLocaleString()}</small>
                {payment.review_note && <small>Review note: {payment.review_note}</small>}
              </span>
              <span className={`payment-status payment-status-${payment.status}`}>
                {payment.status}
              </span>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}

function SchedulePanel() {
  const { handleCreateCalendarInvite, handleScheduleTimeChange, scheduleTime } = useInterviewApp()

  return (
    <section className="panel">
      <p className="eyebrow">Keep your momentum</p>
      <h2>Schedule a practice reminder</h2>
      <label>
        Date and time
        <input type="datetime-local" value={scheduleTime} onChange={(event) => handleScheduleTimeChange(event.target.value)} />
      </label>
      <button className="button secondary full-width" type="button" onClick={handleCreateCalendarInvite}>
        Download calendar invite
      </button>
      <a
        className="text-button linkedin-link"
        href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(window.location.origin)}`}
        target="_blank"
        rel="noreferrer"
      >
        Share InterviewAI on LinkedIn ↗
      </a>
      <p className="fine-print">Calendar events are created locally. LinkedIn sharing does not request or store your LinkedIn credentials.</p>
    </section>
  )
}

export default function DashboardPage() {
  const { candidateProfile, paymentStatus, profile, token } = useInterviewApp()
  const employmentStages = {
    school_student: 'School student',
    college_student: 'College / university student',
    employed: 'Currently working',
    unemployed: 'Currently not working',
    career_changer: 'Changing careers',
    recent_graduate: 'Recent graduate',
    other: 'Other',
  }

  return (
    <main className="page-shell">
      <AppHeader />
      <DashboardHero />
      <section aria-label="Interview activity" className="dashboard-welcome">
        <div>
          <p className="eyebrow">Welcome back</p>
          <h2>{profile?.username?.split(' ')[0] || 'Candidate'}, ready for your next practice?</h2>
          {candidateProfile && (
            <p className="muted candidate-profile-summary">
              {[
                employmentStages[candidateProfile.employment_status],
                candidateProfile.education_level,
                candidateProfile.field_of_study,
                candidateProfile.years_of_experience !== null &&
                candidateProfile.years_of_experience !== undefined
                  ? `${candidateProfile.years_of_experience} years’ experience`
                  : null,
              ].filter(Boolean).join(' · ')}
            </p>
          )}
        </div>
      </section>
      {paymentStatus && <p className="notice" role="status">{paymentStatus}</p>}
      <div className="dashboard-grid">
        <InterviewSetupCard />
        <aside className="side-stack">
          <BillingPanel />
          <SchedulePanel />
        </aside>
      </div>
      <ProgressTracker token={token} />
      <footer className="footer-note">Your camera and microphone are accessed only after you choose to enable them.</footer>
    </main>
  )
}
