# Cache keep-alive pings: extension idea

Status: idea, not built. Recheck on or after **2026-10-10**. See [Recheck](#recheck-on-or-after-2026-10-10).

Scope: Claude Fable 5.1 is the current orchestrator, meaning the main interactive session that spawns subagents. All results below are for Fable main sessions. Subagent sessions finish their task and aren't left idle, so pinging them would be wasted.

## Idea

When a session goes idle for longer than the provider's prompt-cache lifetime, the next message rewrites the whole context into the cache. For Claude Fable 5.1 that costs roughly 38× more per token than reading the cache. A small omp extension could keep the cache alive during idle periods by sending a cheap "ping" before the cache expires. The ping would send the same prefix the cache already holds and ask for a minimal reply. Rules would decide when pinging is worth it.

Why a ping is cheap: it pays a cache read of the context, and it refreshes the cache's lifetime.

Break-even: with one ping per hour, pinging costs less than one re-cache as long as work resumes within about `write price / read price` hours. At Fable prices that is about **38 hours**, whatever the context size.

What omp already does (`providers.cacheRetention: auto`):

- API-key logins get 5-minute cache entries plus idle keep-alive refreshes.
- Subscription (OAuth) logins get 1-hour entries and no keep-alive.
- `long` gives 1-hour entries and turns keep-alive off.

The logs analyzed show that neither mode keeps a cache alive past about 1 hour.

### Rules to build in

- Ping every ~55 minutes while idle (the cache lives 1 hour).
- Stop after a cap. The best cap so far is 12–24 hours; see the results below.
- No pings from Friday evening through Sunday.
- Stop when the session is closed, or when work resumes.
- Candidate rule, still untested: keep pinging until early afternoon on the next weekday. Overnight returns cluster there.

### Open questions for building it

- **Exact prefix:** the ping must reproduce the cached prefix exactly: system prompt, tools, messages, model and thinking settings. Otherwise it misses the cache and pays for a full rewrite itself. omp's side-request path (`buildSideRequestContext`, used by handoff) looks like the right mechanism, but this hasn't been verified.
- **History:** the ping must not be saved into the session history.
- **Subscription usage:** on a subscription, pings spend usage limits rather than dollars. Also check the provider's terms for automated keep-alive requests.

## Data analyzed (2026-09-25)

- About three weeks of omp session logs, 2026-09-04 to 2026-09-25.
- Costs are the list-price figures omp recorded per request.
- All savings below are percentages of Fable 5.1 spend in the same window.

Fable 5.1 (main sessions):

- Spend split: 44% cache reads, 44% cache writes, 12% output.
- Context size per request: median 257k tokens, mean 291k, and 25% of requests above 400k.

The logs fall into two periods by cache lifetime:

| Window | Cache lifetime | Gaps of 5–60 min that still hit the cache | Gaps over 60 min that still hit the cache |
|---|---|---|---|
| Sep 4–12 | 5 min (omp keep-alive active) | 42 of 47 | 0 of 18 |
| Sep 15–25 | 1 hour (current) | 146 of 151 | 1 of 27 |

Returning after more than 60 minutes idle rewrote the whole context 43 times across all dates. That cost **about 22.5% of Fable spend**.

## Results by window

### Current setup: Sep 15–25 (1-hour cache)

- 26 returns found the cache expired. The re-caches cost **about 32% of Fable spend** in this window.
- With a 24-hour cap, 23 of those caches would have been kept alive. The other 3 were absences longer than 24 hours, and 6 sessions were never resumed.

| Rule | Net saved (% of Fable spend) |
|---|---|
| 24 h cap | 15.1% |
| 24 h cap + no weekend pings | 15.6% |

Net saved by cap length:

| Cap | With weekend rule | Without |
|---|---|---|
| 8 h | 14.7% | 14.5% |
| 12 h | **17.2%** | 17.0% |
| 16 h | 15.7% | 15.4% |
| 18 h | 14.9% | 14.6% |
| 20 h | 14.2% | 13.8% |
| 24 h | 15.6% | 15.1% |
| 36 h | 13.6% | 11.7% |

Notes:

- **Why 18 h loses:** all 5 overnight returns came back to the session around midday the next day, 20.7–22.5 hours after it went idle. An 18-hour cap expires just before them. Only a cap of 24 hours or more catches them.
- **Why the weekend rule barely helps:** the costly misses started on weekdays. Two long weekends went idle on a Thursday, and 5 of the 6 abandoned sessions started midweek. The Thursday-to-Monday stretch was a one-off.
- **The most valuable saves:** same-day gaps on very large sessions. For example, a ~770k-token session idle for 1.4–1.6 hours: its re-cache cost about 44× the pings that would have prevented it.

### All dates: Sep 4–25 (assumes 1-hour entries throughout)

| Rule | Net saved (% of Fable spend) |
|---|---|
| No cap | Pinging would have cost about 54% of the re-caching it replaced. It was cheaper in 39 of 45 returns. |
| 24 h cap | 7.7% |
| 24 h cap + no weekend pings | 8.7%. 7 of 44 returns fell inside the blackout and lose their save. |

### Alternative to compare against

omp's idle compaction is off here (`compaction.idleEnabled`). With `idleTimeoutSeconds: 3000`, it would shrink an idle context before the cache expires. My rough estimate is about 80% off the cost of re-caching after long gaps. The cost is lost detail when resuming the session.

## Other models

Would this be equally valuable with other expensive models? Mostly no. A model's price matters less than three other things:

- **Miss-to-read cost ratio:** what an expired cache costs to rebuild, divided by what a cache read costs. This ratio sets the break-even.
  - Anthropic 1-hour cache entries: about 40×.
  - OpenAI models: about 10×. OpenAI charges no cache-write premium, so a miss only pays the normal input price.
- **Cache lifetime:** pings must arrive before the cache expires.
  - With a 5-minute cache, pings are needed about every 4.5 minutes, so pinging stops paying off after roughly an hour of idle time.
  - Where a provider offers long retention (for example, OpenAI's 24-hour option), pings are unnecessary.
- **How big and how long-lived idle main sessions are:** bigger contexts mean more money per saved return. Frequently abandoning sessions eats the savings.

Same simulation (24 h cap, main sessions only, all dates, each model's own recorded prices). The Opus sample is small.

| Model | Miss-to-read ratio | Expired returns | Median context | Net saved (% of that model's main-session spend) |
|---|---|---|---|---|
| Fable 5.1 | ~38× | 44 | 205k | +7.9% |
| Opus 5.5 | ~40× | 4 | 366k | +6.7% |
| Opus 5 | ~19× | 6 | 251k | −25.3% |
| GPT-5.6 Sol | ~10× | 34 | 110k | −11.9% |
| GPT-6 Astra | ~11× | 14 | 99k | −22.0% |

Takeaways:

- Only worth it for a model with a high miss-to-read ratio and a 1-hour cache, used as the long-running orchestrator.
- On the GPT models, pings cost more than the misses they prevent. Those sessions also compact regularly, so their contexts stay smaller.
- If the orchestrator model changes, rerun this table before building anything.

## Method

This is so the recheck produces comparable numbers.

- Only Fable 5.1 assistant messages count. For each, read `usage`: `input`, `cacheRead`, `cacheWrite`, `cost.*` and `cttl` (the cache lifetime).
- **Expired cache:**
  - the gap since the previous request is over 60 minutes;
  - the previous request's context is over 20k tokens;
  - `cacheRead` is under 50% of the previous request's context.
- **Ping cost:** `floor(gap / 55 min) × previous context × cache-read price`. Pinging stops at the cap or at the first ping inside the blackout. If it stops before work resumes, the re-cache is paid anyway.
- **Abandoned session:** its last Fable request is at least 24 hours before the newest log entry. It is charged for pings up to the cap.
- Weekday and hour use local time.

## Recheck on or after 2026-10-10

Rerun the analysis on logs from **2026-09-26 to 2026-10-10**, a new window with no overlap, and compare with the Sep 15–25 results above.

- [ ] Count returns after the cache expired, and their re-cache cost as a share of Fable spend (was 26 returns, ~32%).
- [ ] Recompute net savings for caps of 8, 12, 16, 18, 20, 24 and 36 hours, with and without the weekend rule.
- [ ] Check whether overnight returns still land around midday the next day, and try the "until early afternoon next weekday" rule.
- [ ] Count abandoned sessions and absences over 24 hours, and the pings wasted on them.
- [ ] Confirm the cache lifetime is still 1 hour (`cttl.ephemeral1h`) and that the write/read price ratio hasn't changed.
- [ ] Rerun the per-model table if the orchestrator is no longer Fable 5.1.

Decision:

- **Build the extension** if the best rule saves meaningfully in both windows (roughly 10% or more of Fable spend) and the best cap is similar in both.
- **Drop the idea** if savings shrink or the best rule flips between windows.
- Compare against simply turning on idle compaction before building anything.
