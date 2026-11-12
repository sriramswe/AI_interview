import { useInterviewApp } from '../../context/useInterviewApp'

export default function InterviewBriefing() {
  const { handleEnterInterview, interview } = useInterviewApp()
  const intelligence = interview?.company_intelligence
  const companyName = intelligence?.name || interview?.target_company || 'Your target company'
  const interviewRounds = intelligence?.interview_rounds
  const roundNames = Array.isArray(interviewRounds)
    ? interviewRounds
    : interviewRounds && typeof interviewRounds === 'object'
      ? Object.keys(interviewRounds)
      : []

  return (
    <div className="briefing-backdrop">
      <section aria-labelledby="briefing-title" aria-modal="true" className="briefing-dialog" role="dialog">
        <p className="eyebrow">Interview intelligence briefing</p>
        <h2 id="briefing-title">{companyName}</h2>
        <p className="briefing-meta">
          {[intelligence?.industry, intelligence?.size && `${intelligence.size} company`]
            .filter(Boolean)
            .join(' · ') || `${interview.role_category} interview`}
        </p>
        {intelligence?.verification_status === 'unverified' && (
          <div className="briefing-insight">
            <span className="eyebrow">Company details not verified</span>
            <p>
              This session uses generic role-based practice. Company-specific
              hiring details could not be verified.
            </p>
          </div>
        )}
        {intelligence?.intelligence_reconciliation && (
          <div className="briefing-insight">
            <span className="eyebrow">What to expect</span>
            <p>{intelligence.intelligence_reconciliation}</p>
          </div>
        )}
        {intelligence?.interview_style && (
          <div className="briefing-insight">
            <span className="eyebrow">Interview style</span>
            <p>{intelligence.interview_style}</p>
          </div>
        )}
        {roundNames.length > 0 && (
          <div className="briefing-rounds">
            <span className="eyebrow">Likely round sequence</span>
            <ol>
              {roundNames.map((name, index) => <li key={name}><span>{index + 1}</span>{name}</li>)}
            </ol>
          </div>
        )}
        <button className="button primary full-width" onClick={handleEnterInterview} type="button">
          Enter interview
        </button>
        <p className="fine-print">This is an AI-generated practice briefing, not official company hiring guidance.</p>
      </section>
    </div>
  )
}
