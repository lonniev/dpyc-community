# PersonalBrain MCP — Mar 16

**Operator:** PersonalBrain MCP
**Created:** March 16, 2026
**Updated:** March 29, 2026
**Status:** Deployed
**Interview Stage:** 6/6 (Recommendation)

---

## Bottom Line Up Front

**Pricing Philosophy:** Balanced

**Projected Revenue (moderate):** 4,500,000 sats/mo ($3330.00/mo)

**Tools:** 31 total, 5 sats average price

**Constraints:** free_trial, loyalty_discount, bulk_bonus, happy_hour, surge_pricing, finite_supply

## Revenue Projections

- **TAM:** 500,000 ever-active PersonalBrain users globally
- **SAM:** 10,000-30,000 paying subscribers with technical MCP readiness
- **SOM:** 500-1,500 reachable year-one MCP adopters plus potential enterprise team deployments

| Scenario | Users/Mo | Calls/User | Sats/Mo | USD/Mo |
|----------|---------|------------|---------|--------|
| Conservative | 25 | 4000 | 500,000 | $370.00 |
| Moderate | 150 | 6000 | 4,500,000 | $3330.00 |
| Optimistic | 400 | 8000 | 16,000,000 | $11840.00 |

## Second Opinion

### Devil's Advocate Pricing Review: PersonalBrain MCP Campaign (Mar 16)

As a Devil's Advocate Pricing Analyst, I’ve reviewed the PersonalBrain MCP pricing campaign within the DPYC economic framework. My critique focuses on sat-denominated unit economics, subjective value discovery, and the tollbooth model unique to DPYC.

#### 1. Strengths
- **Value-Driven Pricing Alignment:** The campaign correctly emphasizes value over cost recovery, aligning with the Austrian pricing philosophy of DPYC. Recognizing that a `brain_brain_query` call could enable multi-million dollar outcomes for professional researchers justifies higher pricing for high-value tools.
- **Tiered Pricing Structure:** The initial pricing (1 sat for reads, 5 sats for writes, 10 sats for heavy operations) reflects an understanding of differential value across tool categories. This granularity supports subjective price discovery between operator and patron.
- **Constraint Pipeline Usage:** Incorporating a 5-call free trial and considering loyalty discounts as pipeline steps (not hard paywalls) fits the DPYC model of fairness and experimentation. It allows onboarding without friction while encouraging paid usage.
- **Demand Insight:** Identifying the user base as human-paced professional researchers with habit-driven usage (not bots) informs realistic call volume projections (4,000–8,000 calls/user/month), grounding revenue estimates in plausible behavior.

#### 2. Risks and Weaknesses
- **Underpricing High-Value Tools:** The `brain_brain_query` tool, currently priced at 1 sat, is flagged as compute-intensive and high-value. At this price, it likely operates at a loss or fails to capture the subjective value (potentially worth hundreds of sats per call for critical synthesis moments).
- **Price Elasticity Risk:** The flat pricing (avg. 5 sats/call) may not account for demand elasticity. Researchers might tolerate higher prices for heavy tools (e.g., 50–100 sats for `brain_brain_query`) given the high stakes of their outcomes, but the campaign lacks testing for this threshold.
- **Free-Trial Abuse Potential:** A 5-call free trial, while generous, risks abuse if users cycle through Nostr identities to reset limits. Without a time-bound or rate-limit constraint, this could erode paid conversions.
- **Sat/USD Volatility Exposure:** Revenue projections convert sats to USD (e.g., 16M sats = $11,840/mo in the optimistic scenario). With Bitcoin’s volatility, a 30% price swing could distort perceived revenue by thousands of USD monthly, impacting operator planning if not hedged or communicated.
- **Demand Overestimation:** The SOM (500–1,500 adopters in year one) seems optimistic given the niche of MCP-ready PersonalBrain users. If adoption lags (e.g., <100 users), even moderate revenue (4.5M sats/mo) becomes unattainable.

#### 3. Alternative Pricing Suggestions
- **Reprice Heavy Tools:** Increase `brain_brain_query` to 50 sats and `brain_get_thought_graph_paginated` to 20 sats. These reflect compute intensity and subjective value for synthesis outcomes, balancing operator cost with patron willingness-to-pay.
- **Dynamic Read/Write Pricing:** Adjust reads to 2 sats (from 1 sat) and writes to 8 sats (from 5 sats) to better capture incremental value while keeping low-frequency calls affordable. This raises the average price per call from 5 sats to ~10 sats.
- **Enhanced Constraint Pipeline:** Replace the 5-call free trial with a time-bound free tier (e.g., 10 free calls within first 7 days per Nostr identity) to prevent abuse. Add a loyalty discount pipeline: 20% off per call after 1,000 paid calls lifetime (e.g., 50 sats → 40 sats for heavy tools).
- **Surge Pricing for Peak Usage:** Introduce a surge multiplier (1.5x) for heavy tools during high-demand windows (e.g., detected bursts >50 calls/hour per user), ensuring fairness in resource allocation. For `brain_brain_query`, this means 75 sats during surges.

#### 4. Revenue Impact Assessment
Using the revised pricing and constraints, I’ve recalculated revenue across the original scenarios (25, 150, 400 users). Assumptions: 20% of calls are heavy (50–75 sats), 30% writes (8 sats), 50% reads (2 sats); free-tier usage caps at 10 calls/user; surge applies to 10% of heavy calls. Bitcoin at ~$74,000 (1 sat = $0.00074).

- **Conservative (25 users, 4,000 calls/user/mo):** Total calls = 100,000/mo. Revenue per call mix: (20% * 55 sats avg heavy) + (30% * 8 sats) + (50% * 2 sats) = 14.4 sats avg. Total revenue = 1,440,000 sats/mo (~$1,066/mo), up from 500,000 sats/mo (~$370/mo). **+188% increase.**
- **Moderate (150 users, 6,000 calls/user/mo):** Total calls = 900,000/mo. Revenue at 14.4 sats avg = 12,960,000 sats/mo (~$9,590/mo), up from 4,500,000 sats/mo (~$3,330/mo). **+188% increase.**
- **Optimistic (400 users, 8,000 calls/user/mo):** Total calls = 3,200,000/mo. Revenue at 14.4 sats avg = 46,080,000 sats/mo (~$34,099/mo), up from 16,000,000 sats/mo (~$11,840/mo). **+188% increase.**

These estimates show a near-tripling of revenue across all scenarios due to higher per-call pricing, even with conservative adoption and free-tier limits. Volatility risk remains (e.g., a 30% BTC drop cuts optimistic revenue to ~$23,869 USD), but sat-denominated growth is robust.

#### 5. Final Verdict
**APPROVE WITH RESERVATIONS.** The campaign’s foundation is strong, with value-driven pricing and DPYC-aligned constraints. However, underpricing of high-value tools (`brain_brain_query`) and free-tier abuse risks undermine revenue potential. My alternative pricing (2/8/50–75 sats per tier) and enhanced constraints (time-bound trial, loyalty discounts, surge pricing) address these gaps, yielding a projected 188% revenue uplift. I reserve full approval due to untested elasticity—operators must monitor patron pushback at higher sats levels and adjust dynamically. If adoption stalls or volatility disrupts planning, revisit constraints before slashing prices. Implement my suggestions and launch, but commit to rapid iteration based on real usage data.

## Interview Transcript

The complete pricing consultant interview, 33 messages across 6 stages.

### Stage 1: Inventory

**Operator**:

Let's design a pricing campaign.

**Consultant**:

# Welcome, PersonalBrain MCP! 👋

Great to have you here. I can see you've already done some foundational work — you have **31 tools across 4 functional categories**:

- **Identity & navigation** (whoami, list/get/set brains, stats)
- **Thought CRUD & search** (create, read, update, delete, search thoughts)
- **Graph traversal** (thought graph, paginated graph)
- **Links, attachments & notes** (create/update/delete links, file/URL attachments, notes, modifications)

You're currently running a flat pricing model (1 sat reads, 5 sat writes, 10 sat heavy) with a 5-call free trial. That's a solid starting point.

---

## Where I'd like to take you

We'll move through these stages together, one question at a time:

1. **Inventory** — confirm tool groupings and any I've missed
2. **Demand** — who's calling, how often, what patterns?
3. **Value** — what is each call *worth* to the caller?
4. **Cost** — what does each call *cost* you to serve?
5. **Constraints** — what levers (trials, bulk, surge, etc.) make sense?
6. **Synthesis** — draft campaign + revenue projection

---

## Let's start with Inventory

My read is that `brain_get_thought_graph_paginated` is your only "heavy" tool — it's priced at 10x your reads, suggesting it's either compute-intensive or returns large payloads. Are there other tools you'd consider **high-cost or high-value** that aren't reflected in the current flat tiers? And is there anything in the list you're considering **deprecating or restricting**?

**Operator**:

the brain_query tool is also computationally heavy

**Consultant**:

Great catch — `brain_brain_query` makes sense as a heavy tool. It's doing semantic/AI-powered querying across your thought graph, which is almost certainly more expensive to serve than a simple key lookup.

So your **heavy tier** is actually two tools:

| Tool | Current Price | Category |
|------|--------------|----------|
| `brain_get_thought_graph_paginated` | 10 sats | Heavy — large payload |
| `brain_brain_query` | 1 sat | Heavy — compute (currently **underpriced**) |

That's an important finding — `brain_brain_query` at 1 sat may be costing you money on every call.

---

Before I dig into *how much* to reprice it, I want to understand the demand side first.

## Demand Question

Who are the primary callers of your PersonalBrain MCP tools? I'm thinking about personas like:

- **AI agents** running automated workflows (high frequency, programmatic)
- **Individual power users** querying their own brain interactively (medium frequency, exploratory)
- **Developers** building on top of your API (bursty, testing-heavy)

Which of these best describes your expected user base — and do you expect a mix?

**Operator**:

In a given day, a researcher might work tens of topics and want to record 10s to hundreds of Thoughts per topic. A knowledge engineer is markedly more valuable if they can quickly see and recall patterns. Saving hours of time per day avoiding repetitive research and helping win multi-million dollar contracts or litigations are entirely reasonable scenarios.

**Consultant**:

## The "Invisible Price" Heuristic

For your user base, I'd suggest thinking about pricing in terms of **what they'd spend without thinking:**

- A coffee while reading a paper: ~$5
- A journal article paywall bypass: ~$3–15
- A reference manager subscription (Zotero Pro, Notion): ~$8–16/month

The goal is to price each session such that the **total daily spend feels like a coffee**, not a software license.

### Stage 2: Demand

**Operator**:

My users are professional information researchers, aka data scientists, analysts, paper chasers, knowledge engineers. Throughout their day and career, they read research, abstract key concepts, make notes, and review those notes to look for patterns or to review prior studies. Generally, the MCP tools would not be called by high-speed analytics processing but are called by humans working at human speed each day.

**Consultant**:

That's a really crisp picture — thank you. This tells me a lot:

**Human-paced, habit-driven usage.** These aren't bots hammering your API — they're professionals building a knowledge practice over months and years. Think of it like a researcher's daily ritual: read → abstract → note → connect → query.

This suggests:
- **Write operations** (create/update thought, create link, append note) happen in focused bursts — maybe a research session of 1–3 hours
- **Read/search operations** happen throughout the day — quick lookups, graph browsing
- **Heavy queries** (`brain_brain_query`, paginated graph) happen less frequently but are **high-value moments** — the "aha" synthesis moments that are the whole point of building a knowledge graph

---

## Value Question

Let's focus on that high-value moment. When a knowledge engineer runs `brain_brain_query` and gets back a synthesized answer connecting 6 months of their research notes — what does that enable?

I'm probing for the **cost of NOT having it**:
- Are they replacing hours of manual cross-referencing?
- Is this informing a decision worth real money (a research paper, a client deliverable, an investment thesis)?
- Or is it more of a convenience — nice to have but they'd muddle through otherwise?

What's your sense of what a successful `brain_brain_query` result is *worth* to one of these professionals?

**Operator**:

The appropriate framing is ... business. Knowledge is power and this service enables knowledge engineers to be more powerful. We only want a sub-percentage of the economic value that they get from having the service. It is true, though, that many of these knowledge engineers are from academic backgrounds and think that Information Should be Free - they do not have a good understanding of market economics.

### Stage 3: Value

**Consultant**:

Excellent — so the cost structure for `brain_brain_query` is clearer than I initially assumed:

**No LLM API cost on your side.** The "heavy" cost is:
- PEG parsing (negligible CPU, microseconds)
- Query optimization pass (light compute)
- One or more REST calls to your backend knowledge base (network I/O + backend compute)

This means the cost floor for `brain_brain_query` is likely **similar to `brain_get_thought_graph_paginated`** — it's heavy because of backend fan-out (potentially multiple REST calls), not because of an expensive AI inference step.

So your cost structure across all tools is essentially:

| Tier | Driver | Estimated Cost Floor |
|------|--------|---------------------|
| Read (simple) | Single REST lookup | Very low — fraction of a sat |
| Write | Single REST write + indexing | Low — fraction of a sat |
| Heavy | Multiple REST calls + query optimization | Still low — maybe 1–2 sats at scale |

This is **very good news** — your cost floors are low across the board, meaning pricing is almost entirely a **value conversation**, not a cost recovery conversation.

---

## Value Ceiling Question

Given that your users are professionals whose careers are built on knowledge synthesis — and that `brain_brain_query` may replace 30–60 minutes of manual cross-referencing — how many times per day do you think a typical active user runs a heavy query or graph traversal?

**Operator**:

it may be an agent that constructs the BQL expression. However, within the MCP, the query is parsed with a traditional PEG and handled by a query optimizer. Then it makes one or more lower level REST calls into the backend knowledge base.

**Consultant**:

That's a fair and important question — I want to be straight with you here.

**I don't have reliable real-time industry data** on PersonalBrain's current adoption metrics. My training data has a cutoff and I can't browse the web, so anything I'd cite about active user counts or market penetration would be an estimate rather than a verified stat.

What I *can* tell you from training data:

| Data Point | What I Know |
|------------|-------------|
| PersonalBrain (TheBrain Technologies) | Has been around since 1998 — one of the oldest PKM tools |
| Reported user base (historical) | Claims of "hundreds of thousands" of users cited in older marketing materials |
| Pricing model | Historically subscription-based (~$219/year for Pro) |
| User profile | Skews toward knowledge-intensive professionals — consultants, researchers, lawyers |
| MCP ecosystem | Very new — adoption stats essentially don't exist yet |

**The honest implication for your revenue projection:** My TAM/SAM/SOM numbers were reasonable analogues but not PersonalBrain-specific. If TheBrain Technologies has an existing user base of even 50,000–100,000 users, your SAM is potentially much larger than I estimated — because those users already *have* a brain and would be natural adopters of the MCP interface.

---

**My recommendation:** Before we finalize the campaign, do you have any internal metrics you can share — active API users, beta testers, or even a sense of how many PersonalBrain subscribers might migrate to the MCP interface? That would sharpen the forecast considerably.

**Consultant**:

## Cost Question

Now let's anchor the floor. For `brain_brain_query` specifically — is this hitting an LLM API (OpenAI, Anthropic, etc.) on each call? If so, roughly what does a single query cost you in API fees?

### Stage 4: Cost

**Consultant**:

This is a really nuanced and honest assessment — thank you. Let me reflect back what I'm hearing:

**Philosophy signal:** You're clearly **balanced** — you want to run a real business and capture a fair slice of the value you create, but you're sensitive to the cultural context of your users who have academic "information should be free" instincts. You're not trying to extract maximum value; you're trying to price *fairly* while building something sustainable.

This has a direct strategic implication: **your pricing needs to feel invisible or trivially small** to academics, while still accumulating meaningful revenue at scale. The good news is that sats-denominated micropayments are *perfect* for this — a researcher who would balk at a $20/month subscription might not even notice spending 50 sats per session.

**Operator**:

can you pull any industry stats on PersonalBrain's actual adoption?

**Operator**:

The numbers are thin and somewhat contradictory across sources. Here's what's publicly available:

  Official claim (thebrain.com/about): "Downloaded by over 10 million people" — though this is cumulative lifetime downloads since 1998, not active users.

  Other data points:
  - More than half of Fortune 100 companies reportedly use TheBrain
  - Company is small — ~11 employees, headquartered in LA (per PitchBook)
  - Android app shows ~68K downloads on Google Play
  - Founded 1998, so 28 years in market

  What's missing: They don't publish active user counts, paying subscriber numbers, ARR, or retention figures. A https://forums.thebrain.com/post/how-many-users-does-thebrain-have-7231772 asked
  this exact question without getting a concrete answer. The 10M downloads figure is likely inflated by the free tier and nearly three decades of accumulation — actual active/paying users is
  almost certainly orders of magnitude smaller.

  The v15 announcement focused on the https://www.thebrain.com/blog/unifying-thebrain rather than any user milestones

### Stage 5: Constraints

**Consultant**:

This is a pivotal insight. Let me crystallize what you've just told me:

**The value ceiling is enormous.** A knowledge engineer who wins a $2M contract or litigation partly on the strength of their PersonalBrain-powered recall — you've delivered maybe $200K–$500K of value to that person. Capturing "a sub-percentage" of that means even 0.1% = $200–$500 of legitimate value per major win.

**The usage volume is also high.** Tens of topics per day, hundreds of thoughts per topic — this is not casual usage. An active power user might make:

| Operation | Estimate per Day |
|-----------|-----------------|
| `brain_create_thought` / `brain_update_thought` | 50–200 calls |
| `brain_create_link` / `brain_update_link` | 30–100 calls |
| `brain_search_thoughts` / `brain_get_thought` | 50–150 calls |
| `brain_brain_query` (synthesis moments) | 5–20 calls |
| `brain_get_thought_graph_paginated` | 2–10 calls |

At current pricing, a heavy day might cost a user **~500–2,000 sats** — roughly **$0.50–$2.00 at today's BTC prices**. That's *extremely* cheap for the value delivered.

---

## The Academic Perception Problem

Here's the tension you've identified perfectly:

> Academics think information should be free — but they'll pay $4 for a coffee without thinking.

The solution isn't to charge less — it's to make the **billing unit feel small** even when aggregate spend is meaningful. Micropayments per call are ideal for this. A researcher doesn't see "I spent $50 this month" — they see "2 sats, 5 sats, 1 sat" flashing by invisibly.

---

## Constraints Question

Given this usage pattern and value profile, I want to explore which pricing levers feel right to you. A few options that seem naturally suited to your users:

| Constraint | How it fits your users |
|------------|----------------------|
| `free_trial` | Already have 5 calls — enough to feel the product? Or should it be more generous to hook academics? |
| `loyalty_discount` | Rewards long-term knowledge engineers — aligns with career-long usage pattern |
| `bulk_bonus` | Encourages heavy research sessions — "the more you query today, the cheaper it gets" |
| `happy_hour` | Could reward off-peak usage — less relevant for human-paced researchers |
| `finite_supply` | Relevant for any premium/scarce feature you might add |
| `surge_pricing` | Probably not right — penalizes your best users at their most productive moments |

Two questions in one here — which of these resonate with your philosophy? And do you feel the **free trial of 5 calls is generous enough** to let an academic researcher actually experience the value before paying?

**Operator**:

the current free trial amount is not appropriate. We might want to give away a half or full day of access. I don't think the other constraints are relevant here.

**Consultant**:

That's a really clean, principled position — and it makes sense for your user profile. An academic researcher needs to experience a **full research session** before they can feel the value. Five calls gets them through "hello world" but not through a real workflow.

Let's size what a "half day" looks like in call volume. Based on your usage estimates:

| Session Length | Estimated Total Calls |
|---------------|----------------------|
| Quick session (1–2 hrs) | ~100–200 calls |
| Half day (3–4 hrs) | ~300–500 calls |
| Full day (6–8 hrs) | ~600–1,000 calls |

So a meaningful free trial is probably in the range of **300–1,000 free calls**, not 5.

That's a generous give — but strategically correct. If a researcher spends a half-day building their knowledge graph and runs their first `brain_brain_query` synthesis... they're hooked. The switching cost becomes enormous because **their data is in your system**.

---

## One clarifying question before synthesis:

You mentioned the other constraints aren't relevant — I want to make sure I haven't missed anything. 

What about **loyalty discounts** for your longest-tenured users? Given that knowledge engineers build their brain over *years*, rewarding someone who has spent 100,000 sats lifetime feels aligned with your "fair business" philosophy — and it directly counters the academic "this is getting expensive" instinct over time.

Is that worth including, or do you prefer **flat pricing for everyone** regardless of tenure?

**Operator**:

I'm not opposed to a loyalty discount after say $500 of usage. BTC is $74k today.

**Consultant**:

Great — let me do the sat conversion so we're working in concrete numbers:

| Milestone | USD | Sats (@ $74K BTC) |
|-----------|-----|-------------------|
| Loyalty threshold | $500 | ~675,000 sats |
| Daily heavy user spend | ~$1–2 | ~1,350–2,700 sats |
| Time to loyalty threshold (heavy user) | — | ~250–500 days |

So a dedicated daily user hits the loyalty threshold in **roughly 1–2 years** — which feels exactly right for a career-building tool. It rewards genuine long-term commitment, not gaming.

**What discount percentage feels right at that threshold?** A few framings:

| Discount | Feel | Monthly savings at heavy usage |
|----------|------|-------------------------------|
| 10% | Token gesture | ~$3–6/month |
| 20% | Meaningful acknowledgment | ~$6–12/month |
| 30% | Genuine reward for loyalty | ~$9–18/month |

Given your "fair business, not extraction" philosophy, I'd lean toward **20%** — meaningful enough to notice, not so deep it signals your base prices were inflated.

Does 20% resonate? Or would you go higher/lower?

**Operator**:

20% would be fine

### Stage 6: Recommendation

**Consultant**:

Perfect. Let me also confirm the free trial sizing before I move to synthesis.

You said "half or full day of access." Based on the call volume estimates:

| Option | Calls | What it covers |
|--------|-------|----------------|
| Half day | ~300–500 calls | One solid research session, enough to build a small topic graph and run 2–3 queries |
| Full day | ~600–1,000 calls | A complete working day, enough to experience the full write→link→query→synthesize loop |

Given that your users are academics who need convincing, and that the switching cost (their data living in your system) works strongly in your favor once they're in — **I'd recommend the full day at 1,000 calls.**

The logic: a researcher who spends a full day in PersonalBrain has almost certainly run a meaningful `brain_brain_query` synthesis, felt the "aha" moment, and has enough of their own data in the system that leaving feels like a loss.

Does **1,000 free calls** feel right as your trial, or would you prefer the more conservative 500?

**Consultant**:

## Proposed Pricing

| Tool | Current Price | Proposed Price | Rationale |
|------|--------------|----------------|-----------|
| `brain_whoami` | 1 sat | 1 sat | Identity lookup, negligible value/cost |
| `brain_list_brains` | 1 sat | 1 sat | Navigation, low value |
| `brain_get_brain` | 1 sat | 1 sat | Simple read |
| `brain_set_active_brain` | 1 sat | 2 sats | State-changing, slightly elevated |
| `brain_get_brain_stats` | 1 sat | 2 sats | Computed aggregation, modest cost |
| `brain_create_thought` | 5 sats | 5 sats | Core write, well priced |
| `brain_get_thought` | 1 sat | 1 sat | Simple read |
| `brain_get_thought_by_name` | 1 sat | 1 sat | Simple read |
| `brain_update_thought` | 5 sats | 5 sats | Core write, well priced |
| `brain_delete_thought` | 5 sats | 5 sats | Destructive write |
| `brain_search_thoughts` | 1 sat | 3 sats | Index scan, moderate compute |
| `brain_get_thought_graph` | 1 sat | 3 sats | Graph traversal, moderate compute |
| `brain_get_thought_graph_paginated` | 10 sats | 10 sats | Heavy, well priced |
| `brain_get_types` | 1 sat | 1 sat | Static/cached lookup |
| `brain_get_tags` | 1 sat | 1 sat | Static/cached lookup |
| `brain_create_link` | 5 sats | 5 sats | Core write |
| `brain_update_link` | 5 sats | 5 sats | Core write |
| `brain_get_link` | 1 sat | 1 sat | Simple read |
| `brain_delete_link` | 5 sats | 5 sats | Destructive write |
| `brain_add_file_attachment` | 5 sats | 5 sats | Write + storage |
| `brain_add_url_attachment` | 5 sats | 5 sats | Write + storage |
| `brain_get_attachment` | 1 sat | 1 sat | Simple read |
| `brain_get_attachment_content` | 1 sat | 2 sats | Content retrieval, slightly heavier |
| `brain_delete_attachment` | 5 sats | 5 sats | Destructive write |
| `brain_list_attachments` | 1 sat | 1 sat | Simple read |
| `brain_get_note` | 1 sat | 1 sat | Simple read |
| `brain_create_or_update_note` | 5 sats | 5 sats | Core write |
| `brain_append_to_note` | 5 sats | 5 sats | Core write |
| `brain_get_modifications` | 1 sat | 2 sats | Audit log scan |
| `brain_brain_query` | 1 sat | 10 sats | **Heavy compute — currently severely underpriced** |

**Operator**:

yes

**Consultant**:

Excellent — I have everything I need. Let me now present the full campaign draft.

**Consultant**:

## Bottom Line Up Front

PersonalBrain MCP should run a **balanced business** pricing model — micropayments that feel invisible per-call but accumulate meaningfully at professional usage volumes. With a 1,000-call free trial to hook academics, a loyalty discount for career-long users, and a repriced `brain_brain_query` to reflect its true heavy-compute status, you should expect **$200–$2,000/month** at modest adoption, scaling to **$15,000+/month** with a healthy active user base. The single most important constraint is the **1,000-call free trial** — it's your conversion engine.

**Consultant**:

## Pricing Pipeline

| Step | Constraint | Parameters |
|------|-----------|------------|
| 1 | Free Trial | First 1,000 calls free |
| 2 | Loyalty Discount | 20% off after 675,000 sats lifetime spend (~$500) |

**Consultant**:

## Revenue Projection

### Market Context
- **TAM**: ~500,000 professional knowledge workers globally who use PKM (Personal Knowledge Management) tools
- **SAM**: ~50,000 who use AI-augmented PKM tools and are comfortable with micropayment models
- **SOM**: ~2,000–5,000 reachable in year one via MCP ecosystem

### Comparable Services
| Service | Pricing Model | Monthly Cost |
|---------|--------------|--------------|
| Roam Research | Flat subscription | $15/month |
| Notion AI | Usage + subscription | $10–20/month |
| Semantic Scholar API | Freemium per-call | $0–50/month |

### Usage Assumptions
- Light user: ~200 calls/day × 20 working days = 4,000 calls/month
- Heavy user: ~800 calls/day × 20 working days = 16,000 calls/month
- Average blended spend: ~5 sats/call weighted across tool mix

### 3-Scenario Forecast

| Scenario | Monthly Active Users | Avg Calls/Month | Avg Sats/Call | Monthly Revenue (sats) | Monthly Revenue (USD) |
|----------|--------------------|-----------------|--------------|-----------------------|----------------------|
| Conservative | 50 | 4,000 | 5 | 1,000,000 | $740 |
| Moderate | 200 | 6,000 | 5 | 6,000,000 | $4,440 |
| Optimistic | 500 | 8,000 | 5 | 20,000,000 | $14,800 |

*Note: Free trial users excluded from revenue. Assumes ~30% of new users are in trial at any time.*

**Consultant**:

This is a draft — I'd love your critique before we finalize. A few things I'd specifically flag for your review:

1. **`brain_brain_query` at 10 sats** — this is the biggest change. Does that feel right given it's doing multi-REST-call query optimization?
2. **`brain_search_thoughts` and `brain_get_thought_graph` at 3 sats** — modest bump for compute-heavier reads. Too aggressive for academics?
3. **1,000 call free trial** — you confirmed this, just double-checking you're comfortable with that generosity given the revenue impact in early months.

What would you change?

**Consultant**:

This is really helpful forensic work — thank you. Let me re-calibrate the market picture with this data:

## Revised Market Sizing

| Funnel Stage | Estimate | Reasoning |
|-------------|----------|-----------|
| Lifetime downloads | 10,000,000 | Official claim, 28 years cumulative |
| Ever-active users | ~500,000 | Typical 5% retention on lifetime downloads for niche tools |
| Currently active (any tier) | ~50,000–100,000 | Android 68K alone suggests this floor |
| Paying subscribers | ~10,000–30,000 | Industry norm: 20–30% conversion on active PKM tools |
| MCP-ready (technical users) | ~2,000–5,000 | MCP requires technical sophistication; small slice of paying base |
| Year-one reachable SOM | ~500–1,500 | Realistic early adopter capture for a new MCP interface |

The Fortune 100 data point is actually your most interesting signal — **enterprise knowledge teams** are a real segment. A single Fortune 100 deployment could mean dozens of knowledge engineers using PersonalBrain MCP simultaneously, each generating thousands of calls per day.

## Revised Revenue Projection

| Scenario | Monthly Active Users | Avg Calls/Month | Avg Sats/Call | Monthly Revenue (sats) | Monthly Revenue (USD) |
|----------|--------------------|-----------------|--------------|-----------------------|----------------------|
| Conservative | 25 | 4,000 | 5 | 500,000 | $370 |
| Moderate | 150 | 6,000 | 5 | 4,500,000 | $3,330 |
| Optimistic | 400 | 8,000 | 5 | 16,000,000 | $11,840 |

*Optimistic scenario includes 2–3 small enterprise team deployments of 20–50 users each.*

---

## Strategic Implication for Pricing

The Fortune 100 / enterprise angle changes one thing worth flagging: **enterprise knowledge teams won't blink at 10 sats for `brain_brain_query`**. If anything, the risk is pricing *too low* for enterprise and signaling it's a hobbyist tool.

Individual academics are your price-sensitive segment. Enterprise teams are not. You might eventually want **two tiers** — but for now, the proposed pricing serves both adequately because the per-call amounts are small in USD terms regardless.

---

Does this revised picture feel accurate to your own sense of the addressable market? And are you broadly happy with the pricing table as drafted, or are there specific tools you'd like to revisit before we finalize?

**Operator**:

go ahead

**Consultant**:

Excellent — the campaign is approved. Here's the final design for your records:

## PersonalBrain MCP — Pricing Campaign

### Philosophy
**Balanced** — sustainable business pricing with generous onboarding for academic/researcher users. Micropayments feel invisible per-call while accumulating meaningful revenue at professional usage volumes.

---

### Final Pricing Table

| Tool | Price (sats) | Category |
|------|-------------|----------|
| `brain_whoami` | 1 | identity |
| `brain_list_brains` | 1 | navigation |
| `brain_get_brain` | 1 | navigation |
| `brain_set_active_brain` | 2 | navigation |
| `brain_get_brain_stats` | 2 | analytics |
| `brain_create_thought` | 5 | write |
| `brain_get_thought` | 1 | read |
| `brain_get_thought_by_name` | 1 | read |
| `brain_update_thought` | 5 | write |
| `brain_delete_thought` | 5 | write |
| `brain_search_thoughts` | 3 | compute |
| `brain_get_thought_graph` | 3 | compute |
| `brain_get_thought_graph_paginated` | 10 | heavy |
| `brain_get_types` | 1 | read |
| `brain_get_tags` | 1 | read |
| `brain_create_link` | 5 | write |
| `brain_update_link` | 5 | write |
| `brain_get_link` | 1 | read |
| `brain_delete_link` | 5 | write |
| `brain_add_file_attachment` | 5 | write |
| `brain_add_url_attachment` | 5 | write |
| `brain_get_attachment` | 1 | read |
| `brain_get_attachment_content` | 2 | read |
| `brain_delete_attachment` | 5 | write |
| `brain_list_attachments` | 1 | read |
| `brain_get_note` | 1 | read |
| `brain_create_or_update_note` | 5 | write |
| `brain_append_to_note` | 5 | write |
| `brain_get_modifications` | 2 | analytics |
| `brain_brain_query` | 10 | heavy |

---

### Pipeline Constraints

| Step | Type | Parameters |
|------|------|------------|
| 1 | Free Trial | First 1,000 calls free per user |
| 2 | Loyalty Discount | 20% off all calls after 675,000 sats lifetime spend |

---

### Revenue Forecast Summary

| Scenario | Monthly Users | Monthly Revenue (sats) | Monthly Revenue (USD) |
|----------|-------------|----------------------|-----------------------|
| Conservative | 25 | 500,000 | $370 |
| Moderate | 150 | 4,500,000 | $3,330 |
| Optimistic | 400 | 16,000,000 | $11,840 |

*BTC @ $74,000. Free trial users excluded.*

Thank you for a thorough and thoughtful session — good luck with the launch! 🚀

<!-- REVENUE {"projections":[{"scenario":"conservative","monthly_users":25,"calls_per_user_per_month":4000,"revenue_sats":500000,"revenue_usd":370.00},{"scenario":"moderate","monthly_users":150,"calls_per_user_per_month":6000,"revenue_sats":4500000,"revenue_usd":3330.00},{"scenario":"optimistic","monthly_users":

---

*Exported from [Pricing Studio](https://github.com/lonniev/tollbooth-pricing-studio) — part of the [DPYC](https://github.com/lonniev/dpyc-community) ecosystem.*
