export const meta = {
  name: 'research-grounding',
  description: 'Two-lane research for a study walkthrough: authoritative ground truth + practitioner opinion, synthesised with a ground-truth-wins reconciliation.',
  whenToUse:
    'Invoked by /study-walkthrough at Phase 1 to ground explanations and the wiki page. Authoritative lane = docs/RFC/source for facts; practitioner lane = blogs/talks/forums for tradeoffs, experiences, architectural nuance, and gotchas. Synthesis keeps the two strictly separate and flags any practitioner claim that contradicts ground truth. args: { topic, cadence?, thoroughness?, depth?, lastDeepened?, fromUrl? }.',
  phases: [
    { title: 'Authoritative', detail: 'docs / RFC / source — establish facts' },
    { title: 'Practitioner', detail: 'blogs / talks / forums — tradeoffs, experience, gotchas' },
    { title: 'Synthesize', detail: 'reconcile; ground truth wins; opinions stay labelled' },
  ],
}

// ---------- structured-output schemas ----------

const AUTH_SCHEMA = {
  type: 'object',
  required: ['sources', 'facts'],
  properties: {
    sources: {
      type: 'array',
      items: {
        type: 'object',
        required: ['url', 'what'],
        properties: { url: { type: 'string' }, what: { type: 'string' } },
      },
    },
    facts: {
      type: 'array',
      items: {
        type: 'object',
        required: ['claim', 'source', 'confidence'],
        properties: {
          claim: { type: 'string' },
          source: { type: 'string' },
          confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
      },
    },
    versionGotchas: { type: 'array', items: { type: 'string' } },
  },
}

const PRACT_SCHEMA = {
  type: 'object',
  required: ['sources', 'opinions'],
  properties: {
    sources: {
      type: 'array',
      items: {
        type: 'object',
        required: ['url', 'what'],
        properties: { url: { type: 'string' }, what: { type: 'string' }, author: { type: 'string' } },
      },
    },
    opinions: {
      type: 'array',
      items: {
        type: 'object',
        required: ['claim', 'kind', 'source', 'stance'],
        properties: {
          claim: { type: 'string' },
          kind: {
            type: 'string',
            enum: ['tradeoff', 'experience', 'architecture-nuance', 'gotcha', 'pattern-critique'],
          },
          source: { type: 'string' },
          stance: { type: 'string', enum: ['consensus', 'contested', 'single-voice'] },
        },
      },
    },
  },
}

const SYNTH_SCHEMA = {
  type: 'object',
  required: [
    'confidence',
    'authoritativeSources',
    'practitionerSources',
    'facts',
    'loadBearing',
    'misconceptions',
    'opinions',
    'divergence',
  ],
  properties: {
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    authoritativeSources: {
      type: 'array',
      items: {
        type: 'object',
        required: ['url', 'what'],
        properties: { url: { type: 'string' }, what: { type: 'string' } },
      },
    },
    practitionerSources: {
      type: 'array',
      items: {
        type: 'object',
        required: ['url', 'what'],
        properties: { url: { type: 'string' }, what: { type: 'string' } },
      },
    },
    facts: {
      type: 'array',
      items: {
        type: 'object',
        required: ['claim', 'source', 'confidence'],
        properties: {
          claim: { type: 'string' },
          source: { type: 'string' },
          confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
      },
    },
    loadBearing: { type: 'array', items: { type: 'string' } },
    misconceptions: { type: 'array', items: { type: 'string' } },
    opinions: {
      type: 'array',
      items: {
        type: 'object',
        required: ['claim', 'kind', 'source', 'stance', 'contradictsGroundTruth'],
        properties: {
          claim: { type: 'string' },
          kind: { type: 'string' },
          source: { type: 'string' },
          stance: { type: 'string', enum: ['consensus', 'contested', 'single-voice'] },
          contradictsGroundTruth: { type: 'boolean' },
          note: { type: 'string' },
        },
      },
    },
    divergence: { type: 'array', items: { type: 'string' } },
  },
}

// ---------- lane angles (sliced by fan-out size) ----------

const AUTH_ANGLES = [
  {
    key: 'spec',
    focus:
      'the canonical specification / official documentation — normative behaviour, exact semantics, default values, version applicability',
  },
  {
    key: 'impl',
    focus:
      'the reference implementation or source code / API surface — actual signatures, edge behaviours, what the code really does versus what the prose implies',
  },
  {
    key: 'evolution',
    focus:
      'historical evolution and competing or superseding specs — what changed across versions, what is deprecated, what replaced what',
  },
]

const PRACT_ANGLES = [
  {
    key: 'tradeoffs',
    focus:
      'tradeoffs and when-NOT-to-use — practitioner critiques of the established pattern, cost/benefit, when experienced engineers reach for an alternative and why',
  },
  {
    key: 'warstories',
    focus:
      'real-world gotchas and war stories — surprising behaviours, footguns, migration pain, production incidents, "I wish I had known this earlier" posts',
  },
  {
    key: 'architecture',
    focus:
      'architectural nuance at scale — how the pattern holds up in large systems, how it composes with other patterns, where it breaks down, long-running experience reports',
  },
]

// ---------- args ----------

// Normalise args. The Workflow tool may deliver `args` as a real object OR — if
// the caller stringifies it, a known footgun — as a JSON string. A bare string
// has no `.topic`, which would silently fall through to a placeholder and make
// every agent research nothing. Parse it back into an object first.
let opts = args
if (typeof opts === 'string') {
  try {
    opts = JSON.parse(opts)
  } catch (e) {
    opts = {}
  }
}
if (!opts || typeof opts !== 'object') opts = {}

const topic = opts.topic
if (!topic || !String(topic).trim()) {
  // Fail loud rather than research a meaningless default — the caller (or the
  // skill's single-agent fallback) gets a clear signal instead of garbage.
  throw new Error(
    'research-grounding: missing `topic`. Pass args as a real JSON object, e.g. { "topic": "...", "cadence": "learning" } — not a JSON-encoded string.'
  )
}
const fromUrl = opts.fromUrl
const cadence = opts.cadence || 'learning'
const depth = opts.depth
const lastDeepened = opts.lastDeepened
const thoroughness =
  opts.thoroughness || (cadence === 'concise' || cadence === 'refresh' ? 'lite' : 'normal')
const isRefresh = cadence === 'refresh' || (typeof depth === 'number' && depth >= 3)

const N = { lite: 1, normal: 2, deep: 3 }[thoroughness] || 2
const authAngles = AUTH_ANGLES.slice(0, N)
const practAngles = PRACT_ANGLES.slice(0, N)

const fromClause = fromUrl
  ? `\nThe developer supplied this source: ${fromUrl}. Cross-check its factual claims against your own findings and flag any divergence.`
  : ''
const refreshClause = isRefresh
  ? `\nThis is a REFRESH of an existing page${typeof depth === 'number' ? ` (depth ${depth})` : ''}${
      lastDeepened ? ` last deepened ${lastDeepened}` : ''
    }. Prioritise what changed since then: deprecations, version drift, behaviour changes, and any newer practitioner consensus.`
  : ''

// ---------- prompt builders ----------

function authPrompt(a) {
  return [
    `Research "${topic}" for a developer walkthrough — AUTHORITATIVE / GROUND-TRUTH lane.`,
    `Angle: ${a.focus}.`,
    `Establish what is factually true, sourced to authoritative references only: official docs, specs, RFCs, source code, canonical references. Prefer these strongly over blogs; ignore opinion pieces in this lane.`,
    `Use WebSearch to locate sources and WebFetch to read the one or two most authoritative.${fromClause}${refreshClause}`,
    `Return: sources (max 3; url + one-line "what this is"); facts (each: claim, source url, confidence high|medium|low — every fact MUST be traceable to one of your sources); versionGotchas (behaviour that differs across versions, or non-obvious defaults).`,
    `Be precise. Under 350 words of content, no preamble.`,
  ].join('\n')
}

function practPrompt(a) {
  return [
    `Research "${topic}" for a developer walkthrough — PRACTITIONER / OPINION lane.`,
    `Angle: ${a.focus}.`,
    `Gather informed opinion and experience from blog posts, conference talks, credible practitioner write-ups, and high-signal forum threads — the colour official docs leave out. This lane is explicitly NOT ground truth; it is opinion, and you will label it as such.`,
    `Use WebSearch to find practitioner sources and WebFetch to read the one or two highest-signal. Prefer named, credible authors and widely-cited posts over anonymous SEO content.${refreshClause}`,
    `Return: sources (max 3; url + what + author if known); opinions, each: claim (the tradeoff / experience / nuance / gotcha, stated concretely), kind (tradeoff | experience | architecture-nuance | gotcha | pattern-critique), source url, stance (consensus = widely held | contested = practitioners disagree | single-voice = one notable source).`,
    `Do NOT present speculation as fact. A blog's factual claim about how the technology behaves is an opinion to be checked, not truth. Under 350 words, no preamble.`,
  ].join('\n')
}

function synthPrompt(auth, pract) {
  return [
    `Synthesise research for a developer walkthrough on "${topic}". Two lanes of findings follow as JSON.`,
    ``,
    `AUTHORITATIVE (ground truth):`,
    JSON.stringify(auth, null, 2),
    ``,
    `PRACTITIONER (opinion):`,
    JSON.stringify(pract, null, 2),
    ``,
    `Reconcile under one HARD rule: authoritative sources are ground truth; practitioner opinions never override a fact.`,
    `Produce: confidence (high = multiple authoritative sources agree, medium = one, low = sparse); authoritativeSources (dedup, max 4); practitionerSources (dedup, max 4); facts (dedup authoritative facts only, each traceable to the authoritative lane); loadBearing (3-6 facts the walkthrough should anchor on, plain strings); misconceptions (where common explanations diverge from the canonical source, or version gotchas); opinions (each: claim, kind, source, stance, contradictsGroundTruth, optional note); divergence (where practitioners disagree among themselves, so the walkthrough can present it as open rather than settled).`,
    `Be adversarial about the opinions: for each, set contradictsGroundTruth=true when it conflicts with an authoritative fact — keep the fact, and in note state what it contradicts and that the opinion is likely stale, wrong, or context-specific. Never merge an opinion into facts. Never drop a contradiction silently.`,
    `Under 500 words total.`,
  ].join('\n')
}

// ---------- run ----------

log(
  `Researching "${topic}" — ${authAngles.length} authoritative + ${practAngles.length} practitioner agent(s) (${thoroughness}${
    isRefresh ? ', refresh' : ''
  })`
)

const authThunks = authAngles.map(
  (a) => () => agent(authPrompt(a), { label: `auth:${a.key}`, phase: 'Authoritative', schema: AUTH_SCHEMA })
)
const practThunks = practAngles.map(
  (a) => () => agent(practPrompt(a), { label: `practitioner:${a.key}`, phase: 'Practitioner', schema: PRACT_SCHEMA })
)

// Barrier is correct here: synthesis needs ALL lane results together to reconcile.
const laneResults = await parallel([...authThunks, ...practThunks])
const authFindings = laneResults.slice(0, authThunks.length).filter(Boolean)
const practFindings = laneResults.slice(authThunks.length).filter(Boolean)

log(`Synthesising ${authFindings.length} authoritative + ${practFindings.length} practitioner finding(s)`)

const synthesis = await agent(synthPrompt(authFindings, practFindings), {
  label: 'synthesize',
  phase: 'Synthesize',
  schema: SYNTH_SCHEMA,
})

// Fallback: if the synthesis agent died, return the raw merged lanes so the
// skill still has something to ground on rather than nothing.
return (
  synthesis || {
    confidence: 'low',
    authoritativeSources: authFindings.flatMap((f) => f.sources || []).slice(0, 4),
    practitionerSources: practFindings.flatMap((f) => f.sources || []).slice(0, 4),
    facts: authFindings.flatMap((f) => f.facts || []),
    loadBearing: [],
    misconceptions: authFindings.flatMap((f) => f.versionGotchas || []),
    opinions: practFindings.flatMap((f) =>
      (f.opinions || []).map((o) => ({ ...o, contradictsGroundTruth: false }))
    ),
    divergence: [],
    note: 'synthesis agent failed; returning raw merged lanes',
  }
)
