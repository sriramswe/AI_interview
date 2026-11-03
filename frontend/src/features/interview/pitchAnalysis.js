export function pitchFromSamples(samples, sampleRate) {
  let energy = 0
  for (const sample of samples) energy += sample * sample
  if (Math.sqrt(energy / samples.length) < 0.01) return null

  const minLag = Math.floor(sampleRate / 400)
  const maxLag = Math.min(Math.floor(sampleRate / 75), samples.length - 1)
  let bestLag = 0
  let bestCorrelation = 0
  for (let lag = minLag; lag <= maxLag; lag += 1) {
    let correlation = 0
    for (let index = 0; index < samples.length - lag; index += 1) {
      correlation += samples[index] * samples[index + lag]
    }
    if (correlation > bestCorrelation) {
      bestCorrelation = correlation
      bestLag = lag
    }
  }
  return bestLag ? Math.round(sampleRate / bestLag) : null
}
