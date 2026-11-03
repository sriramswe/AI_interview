function escapeCalendarText(value) {
  return value
    .replace(/\\/g, '\\\\')
    .replace(/,/g, '\\,')
    .replace(/;/g, '\\;')
    .replace(/\n/g, '\\n')
}

function formatCalendarDate(date) {
  return date.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '')
}

export function downloadCalendarInvite({ scheduleTime, role }) {
  const start = new Date(scheduleTime)
  if (!scheduleTime || Number.isNaN(start.getTime())) {
    throw new Error('Choose a valid date and time for your calendar reminder.')
  }

  const end = new Date(start.getTime() + 30 * 60 * 1000)
  const event = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//InterviewAI//Practice Reminder//EN',
    'BEGIN:VEVENT',
    `UID:${crypto.randomUUID()}@interviewai`,
    `DTSTAMP:${formatCalendarDate(new Date())}`,
    `DTSTART:${formatCalendarDate(start)}`,
    `DTEND:${formatCalendarDate(end)}`,
    `SUMMARY:${escapeCalendarText(`Interview practice: ${role}`)}`,
    `DESCRIPTION:${escapeCalendarText('Your scheduled InterviewAI practice session.')}`,
    'END:VEVENT',
    'END:VCALENDAR',
  ].join('\r\n')
  const url = URL.createObjectURL(new Blob([event], { type: 'text/calendar' }))
  const link = document.createElement('a')
  link.href = url
  link.download = 'interview-practice.ics'
  link.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 0)
}
