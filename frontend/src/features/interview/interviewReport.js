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

export async function downloadLearningRoadmapPdf(roadmap, { role, company } = {}) {
  const { jsPDF } = await import('jspdf')
  const doc = new jsPDF({ unit: 'mm', format: 'a4' })
  const pageWidth = doc.internal.pageSize.getWidth()
  const pageHeight = doc.internal.pageSize.getHeight()
  const margin = 16
  const contentWidth = pageWidth - margin * 2
  const bottom = pageHeight - 16
  const days = Array.isArray(roadmap.days) ? roadmap.days : []
  let y = margin

  const addPage = () => {
    doc.addPage()
    y = margin
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(9)
    doc.setTextColor(88, 69, 216)
    doc.text('7-DAY INTERVIEW LEARNING ROADMAP', margin, y)
    doc.setDrawColor(223, 227, 237)
    doc.line(margin, y + 3, pageWidth - margin, y + 3)
    y += 12
  }

  const ensureSpace = (height) => {
    if (y + height > bottom) addPage()
  }

  doc.setProperties({
    title: '7-Day Interview Learning Roadmap',
    subject: 'Personalized interview preparation plan',
    creator: 'InterviewAI',
  })
  doc.setFillColor(44, 38, 104)
  doc.rect(0, 0, pageWidth, 47, 'F')
  doc.setTextColor(255, 255, 255)
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(20)
  doc.text('Your 7-Day Learning Roadmap', margin, 19)
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(10)
  doc.text(
    `${role || 'Interview preparation'}${company ? `  |  ${company}` : ''}`,
    margin,
    28,
    { maxWidth: contentWidth },
  )
  doc.setFontSize(8)
  doc.text(`Created ${new Date().toLocaleDateString()}`, margin, 37)
  y = 57

  const drawListSection = (title, items) => {
    if (!Array.isArray(items) || items.length === 0) return
    ensureSpace(14)
    doc.setTextColor(44, 38, 104)
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(11)
    doc.text(title, margin, y)
    y += 6
    for (const item of items) {
      const lines = doc.splitTextToSize(String(item), contentWidth - 6)
      const itemHeight = lines.length * 4.3 + 2
      ensureSpace(itemHeight)
      doc.setFillColor(88, 69, 216)
      doc.circle(margin + 1, y - 1, 0.7, 'F')
      doc.setTextColor(55, 62, 82)
      doc.setFont('helvetica', 'normal')
      doc.setFontSize(9)
      doc.text(lines, margin + 5, y)
      y += itemHeight
    }
    y += 3
  }

  drawListSection('Focus areas', roadmap.failed_topics)
  drawListSection('Recommended resources', roadmap.resource_recommendations)

  for (const day of days) {
    const activities = Array.isArray(day.activities) ? day.activities : []
    const focusLines = doc.splitTextToSize(String(day.focus || ''), contentWidth - 14)
    const activityLines = activities.map((activity) => (
      doc.splitTextToSize(String(activity), contentWidth - 20)
    ))
    const promptLines = doc.splitTextToSize(
      String(day.practice_prompt || ''),
      contentWidth - 16,
    )
    const cardHeight = 24
      + focusLines.length * 5
      + activityLines.reduce((total, lines) => total + lines.length * 4.2 + 2, 0)
      + promptLines.length * 4.2
    ensureSpace(cardHeight + 4)

    doc.setFillColor(250, 250, 255)
    doc.setDrawColor(223, 227, 237)
    doc.roundedRect(margin, y, contentWidth, cardHeight, 3, 3, 'FD')
    let textY = y + 8
    doc.setTextColor(88, 69, 216)
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(8)
    doc.text(`DAY ${day.day}`, margin + 7, textY)
    textY += 6
    doc.setTextColor(33, 40, 61)
    doc.setFontSize(13)
    doc.text(focusLines, margin + 7, textY)
    textY += focusLines.length * 5 + 3
    doc.setFontSize(9)
    doc.text('Learning activities', margin + 7, textY)
    textY += 5
    doc.setFont('helvetica', 'normal')
    doc.setTextColor(55, 62, 82)
    doc.setFontSize(8.5)
    for (const lines of activityLines) {
      doc.setFillColor(88, 69, 216)
      doc.circle(margin + 9, textY - 1, 0.55, 'F')
      doc.text(lines, margin + 12, textY)
      textY += lines.length * 4.2 + 2
    }
    textY += 2
    doc.setFillColor(242, 240, 255)
    doc.roundedRect(margin + 6, textY - 4, contentWidth - 12, promptLines.length * 4.2 + 12, 2, 2, 'F')
    doc.setTextColor(88, 69, 216)
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(8)
    doc.text('PRACTICE PROMPT', margin + 10, textY + 1)
    doc.setTextColor(55, 62, 82)
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(8.5)
    doc.text(promptLines, margin + 10, textY + 6)
    y += cardHeight + 4
  }

  const pageCount = doc.getNumberOfPages()
  for (let page = 1; page <= pageCount; page += 1) {
    doc.setPage(page)
    doc.setDrawColor(223, 227, 237)
    doc.line(margin, pageHeight - 11, pageWidth - margin, pageHeight - 11)
    doc.setTextColor(98, 107, 128)
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(8)
    doc.text(
      `InterviewAI  |  Page ${page} of ${pageCount}`,
      pageWidth - margin,
      pageHeight - 6,
      { align: 'right' },
    )
  }

  doc.save(`7-day-learning-roadmap-${roadmap.session_id || 'interview'}.pdf`)
}
