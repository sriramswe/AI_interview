import { useCallback, useEffect, useRef, useState } from 'react'

export function useSpeechRecognition(onTranscript) {
  const [listening, setListening] = useState(false)
  const [speechError, setSpeechError] = useState('')
  const [interimTranscript, setInterimTranscript] = useState('')
  const recognitionRef = useRef(null)
  const speechSupported = typeof window !== 'undefined' &&
    Boolean(window.SpeechRecognition || window.webkitSpeechRecognition)

  const stop = useCallback(() => {
    recognitionRef.current?.stop()
    setListening(false)
    setInterimTranscript('')
  }, [])

  const start = useCallback(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      setSpeechError('Speech recognition is not supported by this browser.')
      return
    }

    const recognition = new SpeechRecognition()
    recognition.lang = 'en-US'
    recognition.continuous = true
    recognition.interimResults = true
    recognition.onresult = (event) => {
      let finalText = ''
      let interimText = ''
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const transcript = event.results[index][0].transcript
        if (event.results[index].isFinal) finalText += transcript
        else interimText += transcript
      }
      if (finalText) onTranscript(finalText.trim())
      setInterimTranscript(interimText)
    }
    recognition.onerror = (event) => {
      setListening(false)
      setInterimTranscript('')
      setSpeechError(event.error === 'not-allowed' || event.error === 'service-not-allowed'
        ? 'Microphone permission was denied. Allow microphone access in your browser settings.'
        : `Speech recognition stopped: ${event.error}.`)
    }
    recognition.onend = () => {
      setListening(false)
      setInterimTranscript('')
    }
    recognitionRef.current = recognition
    setSpeechError('')
    try {
      recognition.start()
      setListening(true)
    } catch (error) {
      setSpeechError(`Could not start speech recognition: ${error.message}`)
    }
  }, [onTranscript])

  useEffect(() => () => {
    recognitionRef.current?.abort()
  }, [])

  return {
    listening,
    speechError,
    speechSupported,
    interimTranscript,
    start,
    stop,
  }
}
