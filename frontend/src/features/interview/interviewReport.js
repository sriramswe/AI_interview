function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function formatScore(value) {
  const score = Number(value)
  return Number.isFinite(score) ? `${score.toFixed(1)}%` : 'Not available'
}

export function downloadInterviewReport(session) {
  const answers = Array.isArray(session.answers) ? session.answers : []
  const rounds = Array.isArray(session.rounds_completed) ? session.rounds_completed : []
  const roundScores = session.round_scores && typeof session.round_scores === 'object'
    ? session.round_scores
    : {}
  const answerSections = answers.length
    ? answers.map((answer, index) => `
        <article class="answer">
          <h3>Question ${index + 1}</h3>
          <p class="label">Question</p><p>${escapeHtml(answer.question)}</p>
          <p class="label">Your answer</p><p>${escapeHtml(answer.answer)}</p>
          <p><strong>Score:</strong> ${formatScore(answer.final_score)}</p>
          ${answer.feedback ? `<p class="label">Feedback</p><p>${escapeHtml(answer.feedback)}</p>` : ''}
          ${answer.missing_concepts?.length
            ? `<p><strong>Topics to revisit:</strong> ${escapeHtml(answer.missing_concepts.join(', '))}</p>`
            : ''}
        </article>`).join('')
    : '<p>No answers were recorded for this session.</p>'
  const roundRows = rounds.map((round) => `
    <tr><th>${escapeHtml(round)}</th><td>${formatScore(Number(roundScores[round]) * 10)}</td></tr>
  `).join('')
  const date = new Date(session.created_at)
  const dateLabel = Number.isNaN(date.getTime()) ? 'Date unavailable' : date.toLocaleString()
  const title = `${session.role || 'Interview'} performance report`
  const html = `<!doctype html>
  <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>${escapeHtml(title)}</title>
      <style>
        body{font:16px/1.6 system-ui,sans-serif;color:#202538;max-width:850px;margin:40px auto;padding:0 24px}
        h1,h2,h3{line-height:1.2;color:#18203a}.summary,.answer{border:1px solid #dfe3ed;border-radius:12px;padding:20px;margin:20px 0}
        .metrics{display:flex;gap:24px;flex-wrap:wrap}.label{font-size:12px;font-weight:700;text-transform:uppercase;color:#626b80;margin-bottom:0}
        table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:10px;border-bottom:1px solid #dfe3ed}
        .toolbar{display:flex;gap:12px;margin:24px 0}.toolbar button{padding:10px 16px}
        @media print{body{margin:0 auto;padding:0 12px}.toolbar{display:none}.summary,.answer{break-inside:avoid}}
      </style>
    </head>
    <body>
      <div class="toolbar">
        <button onclick="window.print()" type="button">Print / Save as PDF</button>
      </div>
      <h1>${escapeHtml(title)}</h1>
      <p>Practice report · Generated ${escapeHtml(new Date().toLocaleString())}</p>
      <section class="summary">
        <div class="metrics">
          <p><strong>Company</strong><br>${escapeHtml(session.target_company || 'Not specified')}</p>
          <p><strong>Date</strong><br>${escapeHtml(dateLabel)}</p>
          <p><strong>Status</strong><br>${escapeHtml(session.status || 'Unknown')}</p>
          <p><strong>Answers</strong><br>${answers.length}</p>
          <p><strong>Average score</strong><br>${formatScore(session.average_score)}</p>
        </div>
      </section>
      ${rounds.length ? `<h2>Round scores</h2><table><tbody>${roundRows}</tbody></table>` : ''}
      <h2>Answer review</h2>
      ${answerSections}
      <p><small>This is an AI-generated practice report, not an actual hiring decision.</small></p>
    </body>
  </html>`
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `interview-report-${session.session_id || 'session'}.html`
  document.body.append(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
