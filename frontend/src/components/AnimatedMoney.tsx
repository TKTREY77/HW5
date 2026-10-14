import { useEffect, useRef, useState } from 'react'
import { money } from '../format'

/** Counts from the old value to the new one and flashes up/down, like a till display. */
export default function AnimatedMoney({ value, className = '' }: { value: number | null; className?: string }) {
  const [shown, setShown] = useState(value)
  const [flash, setFlash] = useState<'up' | 'down' | null>(null)
  const prev = useRef(value)

  useEffect(() => {
    const from = prev.current
    prev.current = value
    if (value == null || from == null || from === value) { setShown(value); return }
    setFlash(value < from ? 'down' : 'up')
    const start = performance.now()
    const dur = 900
    let raf = 0
    const step = (t: number) => {
      const p = Math.min(1, (t - start) / dur)
      const eased = 1 - Math.pow(1 - p, 3)
      setShown(from + (value - from) * eased)
      if (p < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    const off = setTimeout(() => setFlash(null), 1600)
    return () => { cancelAnimationFrame(raf); clearTimeout(off) }
  }, [value])

  return <span className={`money ${flash ? `flash-${flash}` : ''} ${className}`}>{money(shown)}</span>
}
