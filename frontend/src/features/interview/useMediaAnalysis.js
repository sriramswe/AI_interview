import { useCallback, useEffect, useRef, useState } from 'react'
import { pitchFromSamples } from './pitchAnalysis'

export function useMediaAnalysis() {
  const [cameraEnabled, setCameraEnabled] = useState(false)
  const [cameraMessage, setCameraMessage] = useState('Camera is off.')
  const [framingStatus, setFramingStatus] = useState('Not analyzed')
  const [micEnabled, setMicEnabled] = useState(false)
  const [pitchRange, setPitchRange] = useState(null)
  const [mediaError, setMediaError] = useState('')
  const videoRef = useRef(null)
  const mediaStreamRef = useRef(null)
  const pitchCleanupRef = useRef(null)
  const frameStatsRef = useRef({ centered: 0, total: 0 })

  useEffect(() => {
    if (!cameraEnabled) return undefined
    let active = true
    let timerId
    const FaceDetector = window.FaceDetector
    if (!FaceDetector) {
      return () => {
        active = false
        window.clearTimeout(timerId)
      }
    }

    const detector = new FaceDetector({ fastMode: true, maxDetectedFaces: 3 })
    const inspectFrame = async () => {
      if (!active || !videoRef.current?.videoWidth) {
        timerId = window.setTimeout(inspectFrame, 700)
        return
      }
      try {
        const faces = await detector.detect(videoRef.current)
        if (!active) return
        const face = faces[0]?.boundingBox
        const isCentered = face
          ? Math.abs(face.x + face.width / 2 - videoRef.current.videoWidth / 2) <
            videoRef.current.videoWidth * 0.2
          : false
        frameStatsRef.current.total += 1
        if (isCentered) frameStatsRef.current.centered += 1
        const stats = frameStatsRef.current
        setFramingStatus(
          !face
            ? 'No face detected in the preview.'
            : stats.total < 3
              ? 'Checking face framing…'
              : stats.centered / stats.total >= 0.7
                ? 'Face is generally centered in the camera frame.'
                : 'Try centering yourself in the camera frame.',
        )
        setCameraMessage(
          'Local framing check only. No video is uploaded and no emotion or personality is inferred.',
        )
      } catch {
        setCameraMessage('Camera preview is on, but face framing could not be analyzed.')
      }
      timerId = window.setTimeout(inspectFrame, 900)
    }
    inspectFrame()
    return () => {
      active = false
      window.clearTimeout(timerId)
    }
  }, [cameraEnabled])

  useEffect(() => () => {
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop())
    pitchCleanupRef.current?.()
    window.speechSynthesis?.cancel()
  }, [])

  const startCamera = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraMessage('Camera access is not supported by this browser.')
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true })
      mediaStreamRef.current?.getTracks().forEach((track) => track.stop())
      mediaStreamRef.current = stream
      if (videoRef.current) videoRef.current.srcObject = stream
      frameStatsRef.current = { centered: 0, total: 0 }
      if (!window.FaceDetector) {
        setCameraMessage('Camera preview is on. Face-framing checks are not supported by this browser.')
      } else {
        setCameraMessage('Local framing check only. No video is uploaded and no emotion or personality is inferred.')
      }
      setCameraEnabled(true)
      setMediaError('')
    } catch (error) {
      setCameraMessage(error.name === 'NotAllowedError'
        ? 'Camera permission was denied. Allow camera access in your browser settings.'
        : 'Could not start the camera. Check that a camera is connected and available.')
    }
  }, [])

  const stopCamera = useCallback(() => {
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop())
    mediaStreamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
    setCameraEnabled(false)
    setFramingStatus('Not analyzed')
    setCameraMessage('Camera is off.')
  }, [])

  const startPitchAnalysis = useCallback(async () => {
    if (!window.AudioContext && !window.webkitAudioContext) {
      setMediaError('Live pitch analysis is not supported by this browser.')
      return
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      setMediaError('Microphone access is not supported by this browser.')
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const AudioContext = window.AudioContext || window.webkitAudioContext
      const context = new AudioContext()
      const analyser = context.createAnalyser()
      analyser.fftSize = 4096
      context.createMediaStreamSource(stream).connect(analyser)
      const samples = new Float32Array(analyser.fftSize)
      const observedPitches = []
      const timerId = window.setInterval(() => {
        analyser.getFloatTimeDomainData(samples)
        const pitch = pitchFromSamples(samples, context.sampleRate)
        if (pitch) observedPitches.push(pitch)
        if (observedPitches.length) {
          setPitchRange({
            min: Math.min(...observedPitches),
            max: Math.max(...observedPitches),
          })
        }
      }, 350)
      pitchCleanupRef.current = () => {
        window.clearInterval(timerId)
        stream.getTracks().forEach((track) => track.stop())
        void context.close()
      }
      setMicEnabled(true)
      setMediaError('')
    } catch (error) {
      setMediaError(error.name === 'NotAllowedError'
        ? 'Microphone permission was denied.'
        : 'Could not start microphone pitch analysis.')
    }
  }, [])

  const stopPitchAnalysis = useCallback(() => {
    pitchCleanupRef.current?.()
    pitchCleanupRef.current = null
    setMicEnabled(false)
  }, [])

  const speakQuestion = useCallback((question) => {
    if (!window.speechSynthesis) {
      setMediaError('Speech playback is not supported by this browser.')
      return
    }
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(question)
    const preferredVoice = window.speechSynthesis
      .getVoices()
      .find((voice) => /en/i.test(voice.lang))
    if (preferredVoice) utterance.voice = preferredVoice
    window.speechSynthesis.speak(utterance)
    setMediaError('')
  }, [])

  const stopQuestionSpeech = useCallback(() => {
    window.speechSynthesis?.cancel()
  }, [])

  return {
    cameraEnabled,
    cameraMessage,
    framingStatus,
    mediaError,
    micEnabled,
    pitchRange,
    videoRef,
    startCamera,
    stopCamera,
    startPitchAnalysis,
    stopPitchAnalysis,
    speakQuestion,
    stopQuestionSpeech,
  }
}
