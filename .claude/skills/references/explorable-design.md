# Explorable Design

How `/study-walkthrough` builds an **explorable**: a small interactive page where the developer explores a topic before discussing it. Published as a private claude.ai Artifact, linked from the wiki page's `explorables` frontmatter, and opened from Omvida's Explore button.

Read this whole file before storyboarding. The `artifact-design` and `artifact-capabilities` skills own the general page contract (title, tokens, dark mode, CDN rules, size); this file adds what an explorable needs on top. When and how a scene is tested and published is the walkthrough's Phase 2.

## What the research says, and what it means here

| Finding | Rule for the page |
| --- | --- |
| An explorable guides attention to one phenomenon; a sandbox that says "figure it out" is not an explanation (Victor, *Explorable Explanations*; Case) | Every interactive answers **one named question**, stated above it. No free-floating playgrounds. |
| Animation alone rarely beats a good static diagram: too fast, too much at once. Gains came from interactivity and learner control (Tversky, Morrison & Betrancourt 2002) | Motion is **learner-paced**: step, scrub, replay. No autoplay loops. A process is a sequence of discrete states the developer steps through. |
| Learner-paced segments help; extraneous material hurts. Removing "seductive details" was among the largest effects in Mayer's corpus, while animation and games were inconsistent (Mayer meta-analysis, 2022) | Playful comes from **pulling levers on the real mechanism** (toggle the defence off, watch the attack land), never from decoration, confetti, mascots or flavour text. |
| Predicting before seeing helps even when the guess is wrong (pretesting effect; Predict-Observe-Explain). Problem-first can lose to explanation-first on material with many interacting parts (productive-failure replications) | Each scene asks for a **prediction before the reveal** on a *small* mechanism. A scene with many interacting parts explains the parts first, then asks. |
| For discrete steps, a stepper beats scrollytelling: known length, replay, direct access (McKenna et al. 2017; Kosara) | The page is a **stepper of scenes** with a visible "scene 2 of 5" and back/next, not a scroll-driven story. |
| Immediate feedback and short segments keep a learner going (Brilliant's learn-by-doing; testing effect) | Predictions get **instant** feedback in the page. A scene fits on one screen. |
| Words next to the thing they describe, highlight what changed (signaling, contiguity) | Labels sit on the diagram, not in a legend. The element that changed on a step is highlighted for that step. |

Sources: [Victor](https://worrydream.com/ExplorableExplanations/), [Case](https://blog.ncase.me/explorable-explanations), [Hohman et al., Distill 2020](https://distill.pub/2020/communicating-with-interactive-articles/), [Tversky et al. 2002](https://hci.stanford.edu/courses/cs448b/papers/Tversky_AnimationFacilitate_IJHCS02.pdf), [Mayer meta-analysis](https://par.nsf.gov/biblio/10637927), [McKenna et al. 2017](https://vdl.sci.utah.edu/publications/2017_eurovis_narrative-flow/), [Kosara](https://eagereyes.org/blog/2016/the-scrollytelling-scourge), [pretesting](https://www.structural-learning.com/post/pretesting-effect-testing-before-teaching), [productive failure](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10185511/).

## Page anatomy

One self-contained HTML file: a short header (topic, one-sentence promise of what the developer will be able to do), then **3-6 scenes** in a stepper, one visible at a time.

Each scene, top to bottom:

1. **The question** (one line, bold): what this scene lets you find out. "What does the browser attach when evil.com submits a form to bank.com?"
2. **At most ~60 words of prose.** Only what the interactive needs to make sense. The rest is in the interactive or in the wiki page later.
3. **The interactive** (see the catalogue). It owns the screen.
4. **A prediction gate** before the reveal: a choice, a number, a drag into place. The reveal (the step, the animation, the result) unlocks only after the prediction is made. Immediate feedback, one line of *why*, never a score.
5. **Ask Claude** (collapsed until opened): a small box for a question about this scene. See "In-page Ask".

Scene 1 is the hook: the most surprising behaviour of the topic, set up so the developer's first prediction is likely wrong. The last scene combines what came before (two levers at once, a variant of an earlier setup).

## Scene catalogue

Pick the type by what the concept *is*. One type per scene.

| Type | Fits | Example |
| --- | --- | --- |
| **Step-through** | A protocol, handshake, request lifecycle, algorithm run: a sequence of states | CSRF: the forged form submit, step by step, the cookie riding along on step 3 |
| **Lever sandbox** | A system whose behaviour depends on a few settings | Cookie `SameSite` × request type: flip each and see which requests carry the cookie |
| **Break it** | A defence or invariant: what it prevents | Turn off the CSRF token check and replay the attack; turn it on and watch it fail |
| **Compare** | Two designs or two mechanisms side by side, same input | Same query with and without an index: rows scanned, step by step |
| **Sort it** | A classification the developer should be able to make | Drag requests into "same-origin", "same-site", "cross-site" |
| **Spot the bug** | A code or config pattern with a typical mistake | Click the line that makes this CORS config unsafe |
| **Timeline scrubber** | Change over time: caches, TTLs, retries, event replay | Scrub time and watch a cached response go stale, revalidate, refresh |
| **Build it** | Composition: assemble the parts in the right order | Order the middleware so the auth check runs before the handler |

Diagrams are **inline SVG** generated from data in the script, so a step is a state change, not a redrawn picture. Use the `artifact-diagramming` skill when a diagram's layout is non-trivial.

## Motion rules

- **Every animation is a transition between two states the developer asked for** (next step, a lever flip). Nothing moves on its own except an explicit Play, which steps through the states and can be paused.
- Transitions run 200-600 ms. Long enough to see what moved, short enough not to wait.
- **Highlight what changed** on each step (accent outline or a short pulse), then let it settle.
- Controls: back / next / replay on every step-through, plus keyboard: `←`/`→` steps, `Space` play/pause, `R` replay.
- `prefers-reduced-motion: reduce` → states switch instantly, highlights stay.
- No scroll-driven motion, no parallax, no looping background animation.

## Technical contract

- **One HTML file, vanilla JS, inline SVG and CSS.** No build step, no framework. A library only when it saves real work (e.g. a physics or graph-layout engine), loaded per the Artifact tool's CDN rules (exact version). Most scenes need none.
- **Scene data as a JS object at the top of the script**: per scene its id, question, the states of the interactive, the prediction (options, correct answer, one-line why). Adding a scene means adding an entry plus its render function. That keeps scene-by-scene republishing cheap.
- **Works without capabilities.** Opened from disk there is no `window.claude` at all, and in a viewer `claude.use()` can resolve `null`. Guard with `const db = window.claude ? await window.claude.use("db") : null` and render the full exploration either way. Only the recording and the Ask box light up when the capabilities resolve.
- Phone width works (Artifact contract: 16 px gutter, no horizontal scroll). An interactive that needs width stacks its controls under the diagram.
- Accessibility: every control is a real `<button>`/`<input>` reachable by keyboard, feedback is announced in an `aria-live` region, and colour is never the only signal (pair it with a label or an icon).
- **Source lives in the repo** at `explore/<folder>/<slug>.html`, where `<folder>/<slug>` is the wiki page key it belongs to (or will belong to). Publish from that path every time, so each republish updates the same artifact URL.

## Recording: the `db` capability

The page uses the `db` and `sample` capabilities (declared on the first publish). It is private to the developer, so the default access rules are right; no `user` capability, no per-viewer paths.

Two collections, written only on a developer action, one write per action:

| Collection | One document per | Fields |
| --- | --- | --- |
| `attempts` | prediction or in-page challenge answered (`add()`) | `scene` (id), `kind` (`prediction` \| `challenge`), `answer` (what they picked or typed), `expected`, `correct` (bool), `at` (ISO time) |
| `questions` | Ask Claude question (`add()`) | `scene`, `question`, `answer` (Claude's reply, once it finished), `at` |

That is a few dozen documents per page, far below the store's limits. A failed write never blocks the exploration: catch it, keep going, and show nothing louder than a small "not recorded" note.

`/study-walkthrough` reads both collections with the `ArtifactData` tool (`list`) when the developer comes back, and `/study-flashcard` reads `attempts` to seed cards from misses. That is the whole feedback channel: no local server, nothing to run.

**A miss**, for both skills: an attempt with `correct: false`. Several misses on one scene are one miss. A scene missed and then answered right on a later attempt still counts: it was the shaky one. The collections keep every session's attempts, so a reader that cares about one session (the walkthrough, on an extended explorable) keeps only attempts whose `at` is after that session started.

## In-page Ask (the `sample` capability)

A collapsed "Ask Claude about this scene" box on each scene, for quick questions while exploring. Bigger questions belong in the terminal's Discuss phase, and the box says so in its placeholder.

- Call `sample` only on the Ask button. Show "Thinking..." until the first `onText`, stream the answer into the box, offer Stop. On `not_granted` or `null`, hide the box.
- `sample` remembers nothing and has no system prompt, so the **prompt carries everything**: an instruction line, the page's fact sheet, the current scene's question, prose and current state (which step, which levers), the developer's prediction if made, then their question. Instruction: "You are helping a developer explore <topic> in an interactive page. Answer their question about the scene in at most 120 words, plain text, grounded only in the facts below. If the facts don't cover it, say so and suggest raising it in the Claude Code session."
- **The fact sheet is a constant in the page script**: the research workflow's authoritative `facts` relevant to the page, one line each with its source URL. It keeps in-page answers grounded in the same sources as the scenes. It is written once at the first publish and extended when a scene adds facts.
- Default `modelTier`. Store the question and the finished answer in `questions`.

## Anti-patterns

- A **wall of text** above the interactive. If a scene needs more than ~60 words of prose, it is two scenes, or the prose belongs in the wiki page.
- A **sandbox with no question**: sliders with nothing asked about them.
- **Autoplay**, looping or decorative motion; scroll-jacking; parallax.
- **Rewards and decoration**: confetti, points, streaks, sounds, mascots. The payoff is the mechanism making sense.
- **Two concepts in one scene.** Split it.
- **A quiz wearing a costume**: multiple choice with no interactive behind it. Predictions gate something the developer then *sees*.
- Revealing the answer in the scene's question or prose before the prediction.
- Jargon in a control's label that the page hasn't introduced yet.
