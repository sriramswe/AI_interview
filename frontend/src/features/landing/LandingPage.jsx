import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  Award,
  Bot,
  BrainCircuit,
  Briefcase,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Code,
  ExternalLink,
  FileCheck,
  FileText,
  Globe,
  Hand,
  Laptop,
  Lock,
  MessageSquare,
  Mic,
  Play,
  RefreshCw,
  ScreenShare,
  Send,
  ShieldCheck,
  Sparkles,
  Star,
  Terminal,
  TrendingUp,
  Users,
  Video,
  Volume2,
  XCircle,
  Zap,
} from 'lucide-react'
import { useInterviewApp } from '../../context/useInterviewApp'
import { DASHBOARD_PATH, LOGIN_PATH, REGISTER_PATH, RESUME_BUILDER_PATH, START_PATH } from '../../routing/routes'
import './landing.css'

const DEMO_QUESTIONS = {
  frontend: {
    title: 'Frontend React / Next.js',
    question: 'How do you optimize rendering performance in a large React application with real-time streaming data?',
    blueprint: [
      'State Isolation: Keep high-frequency streaming state localized to leaf components or via Zustand / signals rather than root Context.',
      'Virtualization: Use virtualized lists (@tanstack/react-virtual) for rendering thousands of DOM elements efficiently.',
      'Memoization: Apply useMemo, useCallback, and React.memo judiciously for heavy computations.',
      'Web Workers: Offload intensive data parsing and filtering off the main thread.',
    ],
    mistakes: 'Avoid putting streaming websocket payloads directly into a top-level Context that triggers full-tree re-renders.',
  },
  backend: {
    title: 'Backend Python / FastAPI',
    question: 'How would you handle database connection pooling and asynchronous worker starvation under 50,000 requests/sec?',
    blueprint: [
      'Async Engine: Configure SQLAlchemy AsyncEngine with SQLAlchemy pool_size=50 and max_overflow=20.',
      'Connection Offloading: Use PgBouncer in transaction pooling mode in front of PostgreSQL.',
      'FastAPI Concurrency: Ensure blocking I/O calls use asyncio.to_thread or run_in_threadpool.',
      'Caching & Throttling: Enforce Redis caching with sliding window rate limiting.',
    ],
    mistakes: 'Calling synchronous blocking libraries inside async def endpoints without threadpool offloading.',
  },
  system_design: {
    title: 'System Design & Distributed Systems',
    question: 'Design a distributed rate limiter that works across multiple data centers with low latency.',
    blueprint: [
      'Algorithm: Token Bucket or Sliding Window Log with Redis Lua script for atomic token consumption.',
      'Local Aggregation: Micro-batch local counts in memory per node and sync asynchronously to centralized Redis cluster.',
      'Fallback: Circuit breaker pattern - if cache is unreachable, allow traffic or fall back to local token bucket.',
      'Consistency: Eventual consistency across multi-region clusters using CRDTs or active-active replication.',
    ],
    mistakes: 'Making synchronous inter-datacenter RPC calls on every single API request, which destroys latency.',
  },
  behavioral: {
    title: 'Behavioral & Leadership (STAR)',
    question: 'Tell me about a time you had a strong disagreement with a senior engineer on technical architecture. How did you resolve it?',
    blueprint: [
      'Situation: Disagreed on adopting GraphQL vs REST APIs for a mission-critical mobile backend overhaul.',
      'Task: Needed to ensure fast delivery without introducing unmanageable caching and query complexity.',
      'Action: Built quick benchmark prototypes with latency measurements, invited team review with data over opinions.',
      'Result: Reached consensus on REST with tailored payloads; delivered project 2 weeks ahead of schedule.',
    ],
    mistakes: 'Focusing on personal friction rather than presenting empirical data and achieving team alignment.',
  },
}

const FAQS = [
  {
    q: 'How does CrackInterviewAI work during a live mock interview?',
    a: 'CrackInterviewAI provides a full Google Meet-style video call simulation. The AI recruiter speaks questions aloud using natural speech synthesis, transcribes your voice in real time, monitors your framing, checks speech pacing, and provides instant scoring and feedback after every response.',
  },
  {
    q: 'Is my webcam and microphone data kept private?',
    a: 'Yes, 100%. All camera previews, framing checks, and speech analysis are processed locally in your browser. No video recordings are stored or uploaded to third-party servers.',
  },
  {
    q: 'How does the ATS Resume Checker score my resume?',
    a: 'The ATS Resume Checker is available without a monthly usage limit on every plan. It provides a rule-based compatibility score and an AI-estimated role match; results are estimates, not a hiring guarantee.',
  },
  {
    q: 'Can I practice live coding assessments?',
    a: 'Yes! CrackInterviewAI includes an integrated Monaco Code Editor (the same engine powering VS Code) with multi-language execution, algorithmic hints, and unit test validation for technical coding rounds.',
  },
  {
    q: 'What is the pricing model in India and globally?',
    a: 'Every plan includes unlimited ATS resume checks. Free includes 3 mock interviews and 1 interview resume analysis per month. Pro is ₹299/month for 20 interviews, 5 interview resume analyses, detailed feedback, and 30 company-specific questions. Elite is ₹599/month with unlimited interviews, resume analyses, and company-specific questions plus an improvement roadmap. Elite also includes unlimited resume builds and uploaded-resume customization.',
  },
]

export default function LandingPage() {
  const { profile, token } = useInterviewApp()
  const destination = token && profile ? DASHBOARD_PATH : LOGIN_PATH
  const startDestination = token && profile ? DASHBOARD_PATH : START_PATH

  const [activeDemoTab, setActiveDemoTab] = useState('system_design')
  const [showBlueprint, setShowBlueprint] = useState(false)
  const [openFaq, setOpenFaq] = useState(0)
  const [currency, setCurrency] = useState('INR') // 'INR' | 'USD'
  const [speaking, setSpeaking] = useState(false)
  const [toolsOpen, setToolsOpen] = useState(false)

  const activeQuestion = DEMO_QUESTIONS[activeDemoTab]

  const handleSpeakDemo = () => {
    if (!window.speechSynthesis) return
    window.speechSynthesis.cancel()
    if (speaking) {
      setSpeaking(false)
      return
    }
    const utter = new SpeechSynthesisUtterance(activeQuestion.question)
    utter.onend = () => setSpeaking(false)
    setSpeaking(true)
    window.speechSynthesis.speak(utter)
  }

  return (
    <div className="min-h-screen bg-[#0d0e15] text-slate-100 selection:bg-purple-500 selection:text-white font-sans overflow-x-hidden">
      {/* Sticky Header */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-[#0d0e15]/85 border-b border-slate-800/80 transition-all">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3 group">
            <span className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center text-white font-black text-lg shadow-lg shadow-purple-500/25 group-hover:scale-105 transition-transform">
              <Zap size={20} className="fill-white" />
            </span>
            <div className="flex flex-col">
              <span className="font-extrabold text-xl tracking-tight text-white flex items-center gap-1.5">
                CrackInterview<span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400">AI</span>
                <span className="text-[10px] uppercase font-bold tracking-widest px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
                  PRO
                </span>
              </span>
            </div>
          </Link>

          {/* Desktop Navigation Links */}
          <nav className="hidden lg:flex flex-1 items-center justify-center gap-0.5">
            <a href="/#features" className="inline-flex min-h-10 items-center whitespace-nowrap rounded-full px-3.5 text-[13px] font-medium text-slate-400 transition-colors hover:bg-white/[0.05] hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/80">
              Features
            </a>
            <a href="/#how-it-works" className="inline-flex min-h-10 items-center whitespace-nowrap rounded-full px-3.5 text-[13px] font-medium text-slate-400 transition-colors hover:bg-white/[0.05] hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/80">
              How it Works
            </a>
            <a href="/#pricing" className="inline-flex min-h-10 items-center whitespace-nowrap rounded-full px-3.5 text-[13px] font-medium text-slate-400 transition-colors hover:bg-white/[0.05] hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/80">
              Pricing
            </a>
            <div
              className="relative"
              onBlur={(event) => {
                if (!event.currentTarget.contains(event.relatedTarget)) setToolsOpen(false)
              }}
            >
              <button
                type="button"
                aria-haspopup="menu"
                aria-expanded={toolsOpen}
                aria-controls="desktop-tools-menu"
                onClick={() => setToolsOpen((open) => !open)}
                onKeyDown={(event) => {
                  if (event.key === 'Escape') setToolsOpen(false)
                }}
                className="inline-flex min-h-10 items-center gap-1.5 whitespace-nowrap rounded-full px-3.5 text-[13px] font-medium text-slate-400 transition-colors hover:bg-white/[0.05] hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/80"
              >
                Tools
                <ChevronDown size={14} className={`transition-transform duration-200 ${toolsOpen ? 'rotate-180' : ''}`} aria-hidden="true" />
              </button>
              <div className={`absolute left-1/2 top-full z-50 w-80 -translate-x-1/2 pt-3 transition-all duration-150 ${toolsOpen ? 'visible translate-y-0 opacity-100' : 'invisible -translate-y-1 opacity-0'}`}>
                <div id="desktop-tools-menu" role="menu" className="overflow-hidden rounded-2xl border border-white/[0.09] bg-[#0a0d13]/98 p-2 shadow-[0_28px_80px_rgba(0,0,0,0.6)] backdrop-blur-2xl">
                  <p className="px-3 pb-2 pt-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                    Free career tools
                  </p>
                  <Link
                    role="menuitem"
                    to={RESUME_BUILDER_PATH}
                    onClick={() => setToolsOpen(false)}
                    className="group/tool flex min-h-16 items-center gap-3 rounded-xl border border-transparent px-3 py-3 transition-colors hover:border-white/[0.08] hover:bg-white/[0.045] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/80"
                  >
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-emerald-400/25 bg-emerald-400/[0.1] text-emerald-300">
                      <FileText size={18} aria-hidden="true" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-[13.5px] font-semibold text-white">Resume Builder</span>
                      <span className="mt-0.5 block text-xs text-slate-400">Create from 30 ATS-ready templates</span>
                    </span>
                    <ArrowRight size={16} className="shrink-0 text-slate-500 transition-colors group-hover/tool:text-emerald-300" aria-hidden="true" />
                  </Link>
                </div>
              </div>
            </div>
          </nav>

          {/* Action CTAs */}
          <div className="flex items-center gap-4">
            <Link
              to={destination}
              className="text-sm font-semibold text-slate-300 hover:text-white px-3 py-2 rounded-lg hover:bg-slate-800/60 transition-colors"
            >
              {token && profile ? 'Dashboard' : 'Sign in'}
            </Link>
            <Link
              to={startDestination}
              className="relative inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-bold text-sm text-white bg-gradient-to-r from-purple-600 via-indigo-600 to-pink-600 hover:from-purple-500 hover:via-indigo-500 hover:to-pink-500 shadow-lg shadow-purple-600/30 hover:shadow-purple-600/50 hover:scale-[1.02] active:scale-[0.98] transition-all"
            >
              <span>Start Free Practice</span>
              <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative pt-16 pb-24 md:pt-24 md:pb-32 overflow-hidden">
        {/* Glow Effects */}
        <div className="crack-glow-orb w-[600px] h-[600px] bg-purple-600/15 top-[-100px] left-1/2 -translate-x-1/2" />
        <div className="crack-glow-orb w-[400px] h-[400px] bg-pink-600/10 top-[200px] right-[-100px]" />
        <div className="crack-glow-orb w-[400px] h-[400px] bg-blue-600/10 bottom-[100px] left-[-100px]" />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center z-10">
          {/* Badge */}
          {/* <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-purple-500/10 border border-purple-500/30 text-purple-300 text-xs md:text-sm font-semibold mb-8 shadow-inner">
             <Sparkles size={15} className="text-yellow-400" />
            <span>India's #1 Real-Time AI Interview Copilot & Mock Simulator</span>
          </div>  */}

          {/* Main Headline */}
          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-white max-w-5xl mx-auto leading-[1.1] mb-6">
            Crack Your Next Tech Interview With{' '}
            <span className="crack-gradient-text">Real-Time AI Assistance</span>
          </h1>

          {/* Subtitle */}
          <p className="text-lg sm:text-xl text-slate-300 max-w-3xl mx-auto leading-relaxed mb-10 font-normal">
            Master live Google Meet mock interviews, real-time voice speech analysis, instant answer blueprints,
            in-browser Monaco coding challenges, and deep ATS resume matching before top tech recruiters evaluate you.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12">
            <Link
              to={startDestination}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2.5 px-8 py-4 rounded-xl font-extrabold text-base text-white bg-gradient-to-r from-purple-600 via-indigo-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 shadow-xl shadow-purple-600/30 hover:shadow-purple-600/50 hover:scale-[1.02] transition-all"
            >
              <span>Get started</span>
              <ArrowRight size={18} />
            </Link>
            <a
              href="#meet-simulator"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-7 py-4 rounded-xl font-bold text-base text-slate-200 bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 hover:border-slate-600 transition-all"
            >
              <Video size={18} className="text-purple-400" />
              <span>Explore Google Meet Simulator</span>
            </a>
          </div>

          {/* Trust Badges */}
          <div className="flex flex-wrap items-center justify-center gap-6 sm:gap-10 text-xs sm:text-sm text-slate-400 font-medium">
            <div className="flex items-center gap-1.5">
              <div className="flex text-amber-400">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} size={15} className="fill-amber-400" />
                ))}
              </div>
              <span className="text-white font-bold">4.9/5</span> (15,000+ candidates)
            </div>
            <div className="flex items-center gap-1.5">
              <ShieldCheck size={16} className="text-emerald-400" />
              <span>100% Private & Camera-Secured</span>
            </div>
          </div>

          {/* Interactive Hero Showcase (Google Meet & Real-Time Assistant Mock) */}
          <div id="meet-simulator" className="mt-16 max-w-5xl mx-auto rounded-2xl overflow-hidden border border-slate-700/70 shadow-2xl shadow-purple-950/50 bg-[#161722]">
            {/* Window Topbar */}
            <div className="bg-[#12131b] px-4 py-3 flex items-center justify-between border-b border-slate-800">
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-red-500/80 inline-block" />
                  <span className="w-3 h-3 rounded-full bg-yellow-500/80 inline-block" />
                  <span className="w-3 h-3 rounded-full bg-green-500/80 inline-block" />
                </div>
                <div className="text-xs font-semibold text-slate-400 flex items-center gap-2 pl-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping inline-block" />
                  <span>meet.google.com/crack-interview-ai</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-1 rounded-full bg-purple-500/15 border border-purple-500/30 text-purple-300 text-[11px] font-bold">
                  LIVE INTERVIEW SESSION
                </span>
              </div>
            </div>

            {/* Video Stage Split */}
            <div className="p-4 sm:p-6 grid grid-cols-1 md:grid-cols-2 gap-4 bg-[#1a1b26]">
              {/* Tile 1: AI Interviewer */}
              <div className="relative aspect-video rounded-xl bg-gradient-to-br from-slate-900 to-indigo-950/70 border border-slate-700/60 p-4 flex flex-col justify-between overflow-hidden shadow-inner">
                <div className="flex items-center justify-between">
                  <span className="px-2 py-0.5 rounded bg-black/60 text-[11px] font-semibold text-emerald-400 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> AI Recruiter
                  </span>
                  <div className="flex items-center gap-1 bg-black/50 px-2 py-0.5 rounded text-[11px] text-purple-300">
                    <Volume2 size={12} /> Speaking
                  </div>
                </div>

                {/* Avatar with speaking wave */}
                <div className="my-auto flex flex-col items-center">
                  <div className="relative w-20 h-20 rounded-full bg-gradient-to-tr from-purple-600 to-pink-500 flex items-center justify-center text-3xl shadow-xl shadow-purple-500/40 crack-pulse">
                    🤖
                    <span className="absolute inset-0 rounded-full border-2 border-purple-400 animate-ping opacity-30" />
                  </div>
                  <div className="flex items-center gap-1 mt-3">
                    <span className="crack-sound-bar" style={{ animationDelay: '0.1s' }} />
                    <span className="crack-sound-bar" style={{ animationDelay: '0.3s' }} />
                    <span className="crack-sound-bar" style={{ animationDelay: '0.2s' }} />
                    <span className="crack-sound-bar" style={{ animationDelay: '0.4s' }} />
                  </div>
                </div>

                {/* Subtitle Caption Overlay */}
                <div className="bg-black/85 backdrop-blur-md rounded-lg p-3 border border-white/10 text-left">
                  <p className="text-xs text-slate-200 leading-snug">
                    <strong className="text-purple-400 font-bold">AI Recruiter: </strong>
                    "Can you explain how you would design a distributed rate limiter that handles 100,000 requests/sec with low latency?"
                  </p>
                </div>
              </div>

              {/* Tile 2: Real-time Copilot & Instant Answer Blueprint */}
              <div className="aspect-video rounded-xl bg-slate-900/90 border border-slate-700/60 p-4 flex flex-col justify-between text-left overflow-y-auto">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-white">
                    <Zap size={14} className="text-yellow-400" />
                    <span>Real-Time Answer Copilot</span>
                  </div>
                  <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-[11px] font-bold">
                    Score: 9.4 / 10
                  </span>
                </div>

                <div className="space-y-2.5 my-auto text-xs py-2">
                  <div className="p-2 rounded bg-purple-950/40 border border-purple-800/40">
                    <strong className="text-purple-300 block mb-0.5">1. Algorithm Choice:</strong>
                    <span className="text-slate-300">Token Bucket / Sliding Window Log in Redis with Lua scripts for atomic decrement.</span>
                  </div>
                  <div className="p-2 rounded bg-indigo-950/40 border border-indigo-800/40">
                    <strong className="text-indigo-300 block mb-0.5">2. Low Latency Architecture:</strong>
                    <span className="text-slate-300">Local node in-memory batching synced asynchronously to Redis to avoid per-request latency.</span>
                  </div>
                  <div className="p-2 rounded bg-pink-950/40 border border-pink-800/40">
                    <strong className="text-pink-300 block mb-0.5">3. Resilience & Fallback:</strong>
                    <span className="text-slate-300">Circuit breaker pattern: allow traffic gracefully if central cache becomes partitioned.</span>
                  </div>
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-slate-800">
                  <span className="flex items-center gap-1 text-emerald-400">
                    <Check size={13} /> STAR Structure Verified
                  </span>
                  <span>Instant Recruiter Feedback</span>
                </div>
              </div>
            </div>

            {/* Bottom Google Meet Floating Controls */}
            <div className="bg-[#12131b] px-6 py-3.5 flex items-center justify-center gap-3 border-t border-slate-800">
              <span className="w-10 h-10 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 hover:text-white cursor-pointer">
                <Mic size={18} />
              </span>
              <span className="w-10 h-10 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 hover:text-white cursor-pointer">
                <Video size={18} />
              </span>
              <span className="w-10 h-10 rounded-full bg-purple-600 text-white flex items-center justify-center shadow-lg shadow-purple-600/40 cursor-pointer">
                <ScreenShare size={18} />
              </span>
              <span className="w-10 h-10 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 hover:text-white cursor-pointer">
                <Hand size={18} />
              </span>
              <span className="px-4 h-10 rounded-full bg-red-600 hover:bg-red-700 text-white font-bold text-xs flex items-center gap-1.5 cursor-pointer">
                Leave Call
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Marquee / Company Logos Bar */}
      <section className="py-12 border-y border-slate-800/60 bg-slate-950/40">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <p className="text-xs uppercase tracking-widest text-slate-400 font-semibold mb-6">
            Candidates Prepared with InterviewAI Have Landed Offers At
          </p>
          <div className="flex flex-wrap items-center justify-center gap-8 sm:gap-14 text-slate-400 font-bold text-lg sm:text-xl">
            <span className="hover:text-white transition-colors">Google</span>
            <span className="hover:text-white transition-colors">Microsoft</span>
            <span className="hover:text-white transition-colors">Amazon</span>
            <span className="hover:text-white transition-colors">Meta</span>
            <span className="hover:text-white transition-colors">Netflix</span>
            <span className="hover:text-white transition-colors">Uber</span>
            <span className="hover:text-white transition-colors">Infosys</span>
            <span className="hover:text-white transition-colors">TCS</span>
            <span className="hover:text-white transition-colors">Swiggy</span>
            <span className="hover:text-white transition-colors">Razorpay</span>
          </div>
        </div>
      </section>

      {/* Core Features Grid */}
      <section id="features" className="py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full bg-purple-500/10 border border-purple-500/30 text-purple-300 text-xs font-bold uppercase tracking-wider mb-4">
            <Zap size={14} /> Full Spectrum Interview Intelligence
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mb-4">
            Everything You Need to Beat the Interview Curve
          </h2>
          <p className="text-slate-400 text-base sm:text-lg">
            Built by engineers who cracked interviews at FAANG and top unicorn startups.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {/* Card 1 */}
          <div className="crack-glass-card rounded-2xl p-7 flex flex-col justify-between">
            <div>
              <div className="w-12 h-12 rounded-xl bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-400 mb-6">
                <Video size={24} />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">Google Meet Simulation</h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-6">
                Realistic face-to-face video mock calls. The AI recruiter speaks questions aloud,
                actively listens to your answers, monitors framing, and mimics real interview pacing.
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs font-semibold text-purple-400">
              <Check size={15} /> Real webcam & voice synthesis
            </div>
          </div>

          {/* Card 2 */}
          <div className="crack-glass-card rounded-2xl p-7 flex flex-col justify-between">
            <div>
              <div className="w-12 h-12 rounded-xl bg-pink-500/15 border border-pink-500/30 flex items-center justify-center text-pink-400 mb-6">
                <FileCheck size={24} />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">Deep ATS Resume Scanner</h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-6">
                Scan your PDF resume against target job postings. Uncover missing tech keywords,
                calculate 0-100% match scores, and get STAR-optimized bullet suggestions.
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs font-semibold text-pink-400">
              <Check size={15} /> Workday & Greenhouse compatibility
            </div>
          </div>

          {/* Card 3 */}
          <div className="crack-glass-card rounded-2xl p-7 flex flex-col justify-between">
            <div>
              <div className="w-12 h-12 rounded-xl bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center text-indigo-400 mb-6">
                <Terminal size={24} />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">Monaco Coding Assessments</h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-6">
                Simulate LeetCode and HackerRank style live coding rounds. Full multi-language Monaco
                editor with real-time test case execution and algorithmic hints.
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs font-semibold text-indigo-400">
              <Check size={15} /> Python, JavaScript, Java, C++
            </div>
          </div>

          {/* Card 4 */}
          <div className="crack-glass-card rounded-2xl p-7 flex flex-col justify-between">
            <div>
              <div className="w-12 h-12 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mb-6">
                <Mic size={24} />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">Speech-To-Text & Pitch Check</h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-6">
                Answer questions naturally with your microphone. Our browser speech recognition
                transcribes your answers live while checking pitch stability and tone.
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400">
              <Check size={15} /> Live browser transcription
            </div>
          </div>

          {/* Card 5 */}
          <div className="crack-glass-card rounded-2xl p-7 flex flex-col justify-between">
            <div>
              <div className="w-12 h-12 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400 mb-6">
                <BrainCircuit size={24} />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">Role & Company Intelligence</h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-6">
                Questions customized for specific companies (Amazon Leadership Principles, Google System
                Design) and tailored to your exact seniority level.
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs font-semibold text-amber-400">
              <Check size={15} /> Tailored to company interview loops
            </div>
          </div>

          {/* Card 6 */}
          <div className="crack-glass-card rounded-2xl p-7 flex flex-col justify-between">
            <div>
              <div className="w-12 h-12 rounded-xl bg-blue-500/15 border border-blue-500/30 flex items-center justify-center text-blue-400 mb-6">
                <TrendingUp size={24} />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">Master Recruiter Scorecard</h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-6">
                Download comprehensive performance feedback reports with hiring verdicts, strengths,
                weak points, and a 7-day personalized study roadmap.
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs font-semibold text-blue-400">
              <Check size={15} /> PDF export & 7-day roadmap
            </div>
          </div>
        </div>
      </section>

      {/* Interactive Live Demo Widget */}
      <section id="interactive-demo" className="py-20 bg-slate-950/70 border-y border-slate-800">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white mb-3">
              Try a Question Right Now
            </h2>
            <p className="text-slate-400 text-sm sm:text-base">
              Select a domain and see how CrackInterviewAI structures winning responses.
            </p>
          </div>

          {/* Tabs */}
          <div className="flex flex-wrap gap-2 justify-center mb-8">
            {Object.entries(DEMO_QUESTIONS).map(([key, data]) => (
              <button
                key={key}
                type="button"
                onClick={() => {
                  setActiveDemoTab(key)
                  setShowBlueprint(false)
                }}
                className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-bold transition-all ${
                  activeDemoTab === key
                    ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30'
                    : 'bg-slate-800/70 text-slate-400 hover:text-white hover:bg-slate-800'
                }`}
              >
                {data.title}
              </button>
            ))}
          </div>

          {/* Question Box */}
          <div className="rounded-2xl bg-[#141520] border border-slate-700/80 p-6 sm:p-8 shadow-2xl">
            <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
              <span className="text-xs uppercase font-bold tracking-wider text-purple-400 flex items-center gap-1.5">
                <Bot size={16} /> AI Interviewer Question
              </span>
              <button
                type="button"
                onClick={handleSpeakDemo}
                className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
              >
                <Volume2 size={14} className={speaking ? 'text-purple-400 animate-pulse' : ''} />
                {speaking ? 'Stop Audio' : 'Listen with Audio'}
              </button>
            </div>

            <p className="text-lg sm:text-xl font-semibold text-white mb-6 leading-relaxed">
              "{activeQuestion.question}"
            </p>

            <div className="flex items-center gap-4">
              <button
                type="button"
                onClick={() => setShowBlueprint((prev) => !prev)}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-sm bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-lg shadow-purple-600/25 transition-all"
              >
                <Sparkles size={16} />
                {showBlueprint ? 'Hide Answer Blueprint' : 'Show Ideal AI Answer Blueprint'}
              </button>
            </div>

            {showBlueprint && (
              <div className="mt-6 pt-6 border-t border-slate-800 space-y-4 animate-fadeIn">
                <div className="bg-purple-950/20 border border-purple-800/40 rounded-xl p-4">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-purple-400 mb-3 flex items-center gap-1.5">
                    <CheckCircle2 size={16} /> High-Scoring Talking Points:
                  </h4>
                  <ul className="space-y-2 text-xs sm:text-sm text-slate-300">
                    {activeQuestion.blueprint.map((point, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="text-purple-400 font-bold">•</span>
                        <span>{point}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="bg-amber-950/20 border border-amber-800/40 rounded-xl p-4">
                  <strong className="text-amber-400 text-xs uppercase tracking-wider block mb-1">
                    ⚠️ Red Flag to Avoid:
                  </strong>
                  <p className="text-xs sm:text-sm text-slate-300">{activeQuestion.mistakes}</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* How It Works (3 Steps) */}
      <section id="how-it-works" className="py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-bold uppercase tracking-wider mb-4">
            <Clock size={14} /> 3 Simple Steps
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mb-4">
            How CrackInterviewAI Works
          </h2>
          <p className="text-slate-400 text-base sm:text-lg">
            From setup to confident interview execution in under 5 minutes.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="crack-glass-card rounded-2xl p-8 relative">
            <span className="text-6xl font-black text-slate-800 absolute top-4 right-6 select-none pointer-events-none">
              01
            </span>
            <div className="w-12 h-12 rounded-xl bg-purple-600/20 border border-purple-500/40 flex items-center justify-center text-purple-400 font-bold text-lg mb-6">
              1
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Upload Resume & Pick Role</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Upload your PDF resume and target job description. The AI parses your technical skills,
              calculates ATS scores, and personalizes interview questions.
            </p>
          </div>

          <div className="crack-glass-card rounded-2xl p-8 relative">
            <span className="text-6xl font-black text-slate-800 absolute top-4 right-6 select-none pointer-events-none">
              02
            </span>
            <div className="w-12 h-12 rounded-xl bg-pink-600/20 border border-pink-500/40 flex items-center justify-center text-pink-400 font-bold text-lg mb-6">
              2
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Join Google Meet Mock Call</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Enter the immersive Google Meet interface. Turn on camera and mic, speak naturally to the
              AI recruiter, and tackle technical or coding challenges.
            </p>
          </div>

          <div className="crack-glass-card rounded-2xl p-8 relative">
            <span className="text-6xl font-black text-slate-800 absolute top-4 right-6 select-none pointer-events-none">
              03
            </span>
            <div className="w-12 h-12 rounded-xl bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400 font-bold text-lg mb-6">
              3
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Get Scored & Land The Job</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Receive detailed answer ratings (/10), STAR critique, and a 7-day personalized study roadmap.
              Refine your weak spots and walk into real interviews with zero fear.
            </p>
          </div>
        </div>
      </section>

      {/* India-First & Global Pricing Plans */}
      <section id="pricing" className="py-24 bg-slate-950/60 border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <div className="inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-bold uppercase tracking-wider mb-4">
              <Award size={14} /> Transparent & Flexible Plans
            </div>
            <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mb-4">
              Pay As You Practice. No Traps.
            </h2>
            <p className="text-slate-400 text-base sm:text-lg mb-8">
              Budget-friendly packs built for candidates in India and worldwide.
            </p>

            {/* Currency Switcher */}
            <div className="inline-flex items-center gap-2 p-1.5 rounded-xl bg-slate-900 border border-slate-800">
              <button
                type="button"
                onClick={() => setCurrency('INR')}
                className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  currency === 'INR' ? 'bg-purple-600 text-white shadow' : 'text-slate-400 hover:text-white'
                }`}
              >
                🇮🇳 INR (₹)
              </button>
              <button
                type="button"
                onClick={() => setCurrency('USD')}
                className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  currency === 'USD' ? 'bg-purple-600 text-white shadow' : 'text-slate-400 hover:text-white'
                }`}
              >
                🌐 USD ($)
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 max-w-7xl mx-auto">
            {/* Free Starter */}
            <div className="crack-glass-card rounded-2xl p-8 flex flex-col justify-between">
              <div>
                <span className="text-xs uppercase font-bold text-slate-400 tracking-wider">Free Starter</span>
                <div className="mt-4 mb-6">
                  <span className="text-4xl font-extrabold text-white">{currency === 'INR' ? '₹0' : '$0'}</span>
                  <span className="text-slate-400 text-sm ml-2">/ forever</span>
                </div>
                <p className="text-xs text-slate-400 mb-6">Start interview practice with unlimited ATS resume checks.</p>
                <ul className="space-y-3 text-xs sm:text-sm text-slate-300 mb-8">
                  <li className="flex items-center gap-2"><Check size={16} className="text-emerald-400" /> Unlimited ATS resume checks</li>
                  <li className="flex items-center gap-2"><Check size={16} className="text-emerald-400" /> 3 mock interviews per month</li>
                  <li className="flex items-center gap-2"><Check size={16} className="text-emerald-400" /> Basic AI feedback</li>
                  <li className="flex items-center gap-2"><Check size={16} className="text-emerald-400" /> 1 resume analysis per month</li>
                  <li className="flex items-center gap-2"><XCircle size={16} className="text-slate-500" /> No company-specific questions</li>
                  <li className="flex items-center gap-2"><Check size={16} className="text-emerald-400" /> Live Speech Recognition</li>
                </ul>
              </div>
              <Link
                to={startDestination}
                className="w-full text-center py-3 rounded-xl font-bold text-sm bg-slate-800 hover:bg-slate-700 text-white border border-slate-700 transition-colors"
              >
                Start Free Trial
              </Link>
            </div>

            {/* Pro Pack (Featured) */}
            <div className="relative crack-glass-card rounded-2xl p-8 flex flex-col justify-between border-2 border-purple-500 shadow-2xl shadow-purple-600/20 bg-gradient-to-b from-purple-950/30 to-slate-900">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-gradient-to-r from-purple-600 to-pink-600 text-white text-[11px] font-black uppercase tracking-wider shadow">
                MOST POPULAR
              </div>
              <div>
                <span className="text-xs uppercase font-bold text-purple-400 tracking-wider">Interview Pro</span>
                <div className="mt-4 mb-6">
                  <span className="text-4xl font-extrabold text-white">{currency === 'INR' ? '₹299' : '$8.99'}</span>
                  <span className="text-slate-400 text-sm ml-2">/ month</span>
                </div>
                <p className="text-xs text-slate-400 mb-6">Everything you need to crack any tech interview loop.</p>
                <ul className="space-y-3 text-xs sm:text-sm text-slate-200 mb-8">
                  <li className="flex items-center gap-2"><Check size={16} className="text-purple-400" /> 20 mock interviews per month</li>
                  <li className="flex items-center gap-2"><Check size={16} className="text-purple-400" /> Detailed AI feedback</li>
                  <li className="flex items-center gap-2"><Check size={16} className="text-purple-400" /> Unlimited ATS checks + 5 interview resume analyses/month</li>
                  <li className="flex items-center gap-2"><Check size={16} className="text-purple-400" /> Up to 30 company-specific questions per month</li>
                  <li className="flex items-center gap-2"><Check size={16} className="text-purple-400" /> Real-Time Voice Speech Recognition</li>
                  <li className="flex items-center gap-2"><Check size={16} className="text-purple-400" /> Monaco Live Coding Assessment</li>
                  <li className="flex items-center gap-2"><Check size={16} className="text-purple-400" /> Job-description tailored practice</li>
                </ul>
              </div>
              <Link
                to={token && profile ? startDestination : `${START_PATH}?plan=pro`}
                className="w-full text-center py-3.5 rounded-xl font-bold text-sm bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white shadow-lg shadow-purple-600/40 transition-all"
              >
                Get Pro Pack Now
              </Link>
            </div>

            {/* Elite Placement Pass */}
            <div className="crack-glass-card rounded-2xl p-8 flex flex-col justify-between">
              <div>
                <span className="text-xs uppercase font-bold text-slate-400 tracking-wider">Elite Placement Pass</span>
                <div className="mt-4 mb-6">
                  <span className="text-4xl font-extrabold text-white">{currency === 'INR' ? '₹599' : '$19.99'}</span>
                  <span className="text-slate-400 text-sm ml-2">/ month</span>
                </div>
                <p className="text-xs text-slate-400 mb-6">For senior engineers, lead roles, and executive loops.</p>
                <ul className="space-y-3 text-xs sm:text-sm text-slate-300 mb-8">
                  <li className="flex items-center gap-2"><Check size={16} className="text-emerald-400" /> Unlimited mock interviews</li>
                  <li className="flex items-center gap-2"><Check size={16} className="text-emerald-400" /> Detailed feedback + improvement roadmap</li>
                  <li className="flex items-center gap-2"><Check size={16} className="text-emerald-400" /> Unlimited ATS checks and interview resume analyses</li>
                  <li className="flex items-center gap-2"><Check size={16} className="text-emerald-400" /> Unlimited company-specific questions</li>
                  <li className="flex items-center gap-2"><Check size={16} className="text-emerald-400" /> Multi-Interviewer Panel Simulations</li>
                  <li className="flex items-center gap-2"><Check size={16} className="text-emerald-400" /> Master Recruiter Performance PDF</li>
                  <li className="flex items-center gap-2"><Check size={16} className="text-emerald-400" /> Priority Gemini 1.5 Pro AI Engine</li>
                  <li className="flex items-center gap-2"><Check size={16} className="text-emerald-400" /> Unlimited resume builds and customization</li>
                </ul>
              </div>
              <Link
                to={token && profile ? startDestination : `${START_PATH}?plan=elite`}
                className="w-full text-center py-3 rounded-xl font-bold text-sm bg-slate-800 hover:bg-slate-700 text-white border border-slate-700 transition-colors"
              >
                Get Elite Pass
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mb-4">
            Hear From Candidates Who Cracked Their Interviews
          </h2>
          <p className="text-slate-400 text-base sm:text-lg">
            Real stories from software engineers across India and worldwide.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="crack-glass-card rounded-2xl p-6">
            <div className="flex text-amber-400 mb-4">
              {[...Array(5)].map((_, i) => (<Star key={i} size={15} className="fill-amber-400" />))}
            </div>
            <p className="text-sm text-slate-300 leading-relaxed mb-6">
              "The Google Meet simulation felt unbelievably real. Getting real-time answer blueprints helped me organize my system design answers into clear trade-offs. Cracked SDE-2 at Amazon!"
            </p>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-purple-600 flex items-center justify-center font-bold text-white text-sm">
                AK
              </div>
              <div>
                <h4 className="text-sm font-bold text-white">Aditya Kumar</h4>
                <p className="text-xs text-purple-400">SDE-2 at Amazon (Bengaluru)</p>
              </div>
            </div>
          </div>

          <div className="crack-glass-card rounded-2xl p-6">
            <div className="flex text-amber-400 mb-4">
              {[...Array(5)].map((_, i) => (<Star key={i} size={15} className="fill-amber-400" />))}
            </div>
            <p className="text-sm text-slate-300 leading-relaxed mb-6">
              "The ATS resume scanner found 8 critical keywords missing from my resume that I had forgotten to highlight. After fixing them, I got callbacks from Swiggy and Razorpay within a week."
            </p>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-pink-600 flex items-center justify-center font-bold text-white text-sm">
                PS
              </div>
              <div>
                <h4 className="text-sm font-bold text-white">Pooja Sharma</h4>
                <p className="text-xs text-pink-400">Frontend Lead at Swiggy</p>
              </div>
            </div>
          </div>

          <div className="crack-glass-card rounded-2xl p-6">
            <div className="flex text-amber-400 mb-4">
              {[...Array(5)].map((_, i) => (<Star key={i} size={15} className="fill-amber-400" />))}
            </div>
            <p className="text-sm text-slate-300 leading-relaxed mb-6">
              "As someone with severe interview anxiety, practicing on voice with the AI interviewer gave me the confidence I needed. The speech pace and pitch diagnostics were a game changer."
            </p>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-indigo-600 flex items-center justify-center font-bold text-white text-sm">
                RV
              </div>
              <div>
                <h4 className="text-sm font-bold text-white">Rahul Verma</h4>
                <p className="text-xs text-indigo-400">Backend Engineer at Razorpay</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section id="faq" className="py-24 bg-slate-950/60 border-t border-slate-800">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mb-4">
              Frequently Asked Questions
            </h2>
            <p className="text-slate-400 text-base sm:text-lg">
              Everything you need to know about CrackInterviewAI.
            </p>
          </div>

          <div className="space-y-4">
            {FAQS.map((faq, index) => (
              <div
                key={index}
                className="crack-glass-card rounded-xl border border-slate-800 overflow-hidden"
              >
                <button
                  type="button"
                  onClick={() => setOpenFaq(openFaq === index ? -1 : index)}
                  className="w-full text-left p-5 font-bold text-sm sm:text-base text-white flex items-center justify-between gap-4"
                >
                  <span>{faq.q}</span>
                  {openFaq === index ? (
                    <ChevronUp size={18} className="text-purple-400 flex-shrink-0" />
                  ) : (
                    <ChevronDown size={18} className="text-slate-400 flex-shrink-0" />
                  )}
                </button>
                {openFaq === index && (
                  <div className="px-5 pb-5 text-xs sm:text-sm text-slate-300 leading-relaxed border-t border-slate-800/60 pt-4">
                    {faq.a}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final Call to Action */}
      <section className="py-20 relative overflow-hidden bg-gradient-to-br from-purple-950 via-[#10111a] to-slate-950 border-t border-slate-800">
        <div className="max-w-5xl mx-auto px-4 text-center relative z-10">
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mb-6">
            Ready to Walk Into Your Next Interview With Absolute Confidence?
          </h2>
          <p className="text-slate-300 text-base sm:text-lg max-w-2xl mx-auto mb-10">
            Join 15,000+ engineers who transformed their preparation with CrackInterviewAI.
            Get 30 free practice minutes right now.
          </p>
          <Link
            to={startDestination}
            className="inline-flex items-center justify-center gap-2 px-9 py-4 rounded-xl font-extrabold text-base text-white bg-gradient-to-r from-purple-600 via-indigo-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 shadow-xl shadow-purple-600/40 hover:scale-[1.03] transition-all"
          >
            <span>Start Your Free Practice Now</span>
            <ArrowRight size={18} />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-[#090a0f] border-t border-slate-800/80 py-12 text-xs text-slate-400">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <span className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-pink-500 flex items-center justify-center text-white font-bold text-sm">
              <Zap size={16} className="fill-white" />
            </span>
            <span className="font-extrabold text-base text-white">CrackInterviewAI</span>
          </div>
          <p className="text-center sm:text-left text-slate-500">
            © {new Date().getFullYear()} CrackInterviewAI. All rights reserved. Practice thoughtfully, crack confidently.
          </p>
          <div className="flex items-center gap-6">
            <Link to={LOGIN_PATH} className="hover:text-white transition-colors">Sign In</Link>
            <Link to={REGISTER_PATH} className="hover:text-white transition-colors">Register</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
