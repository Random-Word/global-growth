# Growth, Poverty, and Planetary Boundaries: A Data-Driven Response

**A quantitative examination of whether capitalism is "mathematically unworkable" for ending global poverty within ecological limits.**

This repository contains a data-driven analysis responding to two papers that argue growth-based poverty elimination is physically impossible and redistribution is the only viable path. The analysis uses World Bank, Maddison Project, and Our World in Data sources to test specific claims with publicly available data.

The analysis was conducted collaboratively between a human analyst and AI assistants (Claude Opus 4.6 and GPT-5.4). All code, data pipelines, and figures are reproducible.

---

## Table of Contents

1. [What the Papers Argue](#what-the-papers-argue)
2. [Where We Agree](#where-we-agree)
3. [Where We Push Back](#where-we-push-back)
4. [The Carbon Budget Reality Check](#the-carbon-budget-reality-check)
5. [Independent Critical Review (GPT-5.4)](#independent-critical-review)
6. [What a Reasonable Person Should Conclude](#what-a-reasonable-person-should-conclude)
7. [Appendix: Methodology](#appendix-methodology)

---

## What the Papers Argue

Two papers were presented with the claim that they "mathematically prove capitalism is unworkable" and establish "a moral imperative to move beyond it as soon as possible."

### Paper 1: "Growth Alone Cannot End Poverty"

The core argument is arithmetical:

- Eliminating poverty at meaningful thresholds ($6.85–$10/day) through growth alone would require multiplying global GDP by **5 to 175 times** — taking one to two centuries
- Only **5% of new income** from GDP growth reaches the poorest 60% of humanity
- The poverty gap at $5/day was $4.5 trillion in 2010, but closing it through growth required **$11,500 trillion** in additional GDP — a 2,500:1 inefficiency ratio
- Remaining carbon budget for 1.5°C is ~250–400 GtCO₂, exhausted in **6–10 years** at current emissions
- Material extraction is already **2x the sustainable limit** (~100 Gt/yr vs ~50 Gt/yr)
- Conclusion: growth-based poverty elimination is physically impossible; only redistribution works

### Paper 2: "Measuring Global Poverty"

A more balanced analysis that finds:

- Poverty rates have declined at **every measurable threshold** since 1990
- Non-income indicators confirm massive improvement: life expectancy +7 years, child mortality -59%, literacy 76%→87%
- But 3.5 billion people remain below $6.85/day with little change in absolute numbers
- China drove ~75% of extreme poverty reduction
- Concludes: *"whether this requires systemic transformation or continued growth is not a question empirical methodology alone can answer"*

---

## Where We Agree

The papers make several claims that our data confirms. We take these seriously.

### 1. Growth alone, with current distributional patterns, is insufficient

This is the papers' strongest claim and it is correct. If the poorest 60% receive only 5% of growth income, solving poverty through undirected growth is grotesquely inefficient.

### 2. The $2.15/day line dramatically understates deprivation

Our data confirms 3.5 billion people remain below $6.85/day. Progress at the bottom is real; progress at meaningful thresholds is far more modest.

### 3. Planetary boundaries are a real constraint

Our own carbon budget arithmetic (corrected after finding an error in our initial analysis) shows the constraint is severe — see [the reality check below](#the-carbon-budget-reality-check).

### 4. Redistribution is far more efficient than undirected growth at reaching the poor

Direct transfers deliver $0.85–$0.90 per dollar to recipients. Growth delivers roughly $0.005. This is a 100:1 to 2,000:1 efficiency gap.

### 5. Sub-Saharan Africa is being left behind

SSA's share of global extreme poverty rose from 13% to 65% while the absolute number of extremely poor people nearly doubled. This is the most serious ongoing development failure.

![Regional poverty decomposition](charts/02_poverty_by_region.png)
*At $2.15/day, East Asia's dramatic decline (green line, top-left) is the dominant global story. At $6.85/day (bottom-left), South Asia and Sub-Saharan Africa remain largely unchanged. The "declining poverty" narrative is essentially an East Asian story at higher thresholds.*

---

## Where We Push Back

### 1. Growth has made redistribution dramatically cheaper — this changes the math

The papers present growth and redistribution as alternatives. Our data shows they are complements. Growth didn't solve poverty directly, but it *transformed the fiscal arithmetic* of redistribution.

![Poverty gap as share of GDP](charts/01_poverty_gap_pct_gdp.png)
*The poverty gap at every threshold has fallen as a share of global GDP. At $2.15/day: from 3.1% to 0.17% (a 95% decline). At $6.85/day: from ~39% to ~5% (87% decline). Ending extreme poverty is now cheap enough to be a policy choice, not a resource constraint.*

| Poverty Line | People Below | Perfect Gap | Realistic Cost (3x) | % of World GDP |
|---|---|---|---|---|
| $2.15/day | 1.27B | $332B | $996B | 0.50% |
| $3.65/day | 3.13B | $1,518B | $4,555B | 2.28% |
| $6.85/day | 7.35B | $7,755B | $23,264B | 11.65% |
| $10.0/day | 9.77B | $17,733B | $53,200B | 26.64% |

The papers' own preferred solution — redistribution — has become dramatically more feasible precisely *because of growth*. A world with 3.1% of GDP as the extreme poverty gap is resource-constrained. A world with 0.17% is not. Growth created the surplus from which redistribution can draw.

### 2. The poor world doesn't need 175x GDP — it needs 2–3x

The papers' most alarming scenarios assume everyone must converge to current American consumption levels through undirected growth with unchanged distributional patterns. That's a straw man. Our analysis finds:

- The "good life" threshold — where 91–95% of country-years achieve life expectancy ≥70 — is approximately **$15,000 GDP per capita (PPP)**
- Countries below this threshold need only **2.1x their current GDP** to reach it
- At 5% growth, that's **15 years**, not 200

![The good-life threshold](charts/14_good_life_threshold.png)
*The Preston curve (top-left, bottom-left) shows that life expectancy reaches ~75 years around $15k GDP/capita, with diminishing returns beyond that. The bottom-right panel shows 91–95% of country-years above $15k achieve life expectancy ≥70. The goal is not American consumption levels — it's the point where material deprivation stops killing people.*

### 3. The floor IS rising — welfare convergence is real even without income convergence

The papers focus on whether poor countries are "catching up" to rich ones (convergence). We argue the more important question is whether the poorest are getting less poor in absolute terms (floor-raising).

![Floor-raising analysis](charts/13_floor_rising.png)
*Top-left: The P5 floor (poorest 5% of countries) has risen from ~$600 to ~$1,400 since 1950. Top-right (population-weighted): even more dramatic improvement. Bottom-left: the floor grew fastest in 2000–2022. Bottom-right: the P90/P5 ratio rose (divergence) from 1950–2000 but has started falling since — the gap is narrowing.*

The Preston curve shift is especially important: the same income buys *more* welfare over time. A country at $5,000 GDP/capita in 2020 has higher life expectancy than a country at $5,000 in 1990, because of public health advances, the Green Revolution, and technology diffusion. Welfare is converging even where incomes aren't.

### 4. Market economies are necessary — the data shows no alternative

The papers implicitly argue for a non-capitalist alternative but never specify one. Our examination of actual non-market economies finds:

- **Zero sustained >4% non-resource growth episodes in pure command economies**
- The USSR peaked at 41% of US GDP/capita in 1980, then declined to 20% by 1998
- China's reform era (6.8%/yr) was **2.5x faster** than the Mao era (2.8%/yr)
- The command economy pattern is universal: fast extensive growth (mobilizing unused resources), then stagnation once the frontier requires innovation

![Command vs market growth](charts/18_command_vs_market.png)
*Left: GDP per capita indexed to 1950. China (pink) stagnated under Mao then exploded after 1978 reforms. Russia (red) grew impressively until the 1970s then flatlined and collapsed. Right: 10-year rolling growth rates showing the USSR's steady deceleration while China accelerated post-reform.*

This doesn't mean laissez-faire capitalism. None of the East Asian successes (Japan, Korea, Taiwan, China, Vietnam) were laissez-faire — all featured heavy state industrial policy, directed credit, and managed trade. The common thread across all sustained development successes is **market mechanisms within state-directed development strategy**. The nuclear reactor metaphor: capitalism is a powerful energy source that requires careful containment and direction, not abandonment.

### 5. The "exploitation" claim is empirically weak

The implicit argument that the rich world's material abundance depends on exploiting the poor world is testable through consumption-based emissions accounting:

![CO₂ trade flows](charts/20_co2_trade_exploitation.png)
*Top-left: Production vs consumption-based CO₂ for major economies. The US consumes ~10% more than it produces; China EXPORTS ~11% of its production emissions for others' consumption. Top-right: Trade CO₂ over time — China is a massive net exporter of embodied emissions. Bottom panels: the rich world produces 85–92% of its consumed emissions domestically.*

| Country | Production CO₂ | Consumption CO₂ | Offshored |
|---|---|---|---|
| United States | 5,055 Mt | 5,566 Mt | +10.1% |
| United Kingdom | 311 Mt | 503 Mt | +61.6% |
| Germany | 668 Mt | 839 Mt | +25.6% |
| China | 11,712 Mt | 10,427 Mt | **-11.0%** (net exporter) |
| India | 2,831 Mt | 2,340 Mt | **-17.3%** (net exporter) |

There *is* some emissions offshoring, particularly by the UK. But the claim that the rich world "couldn't sustain itself without exploiting the poor world" is not supported. The real trade dependency runs the other direction: poor countries depend on access to rich-world markets for export-led growth.

---

## The Carbon Budget Reality Check

This is where we must be honest: the planetary boundaries argument is stronger than we initially presented. After catching and correcting an error in our analysis, the numbers are sobering.

### Required annual CO₂ intensity decline rates (over 50 years)

| Growth Rate | 1.5°C (300 Gt) | 2°C (900 Gt) | 3°C (~2500 Gt) |
|---|---|---|---|
| 0% | 12.5%/yr | 3.4%/yr | 0.0%/yr |
| 1% | 13.4%/yr | 4.4%/yr | 0.0%/yr |
| 2% | 14.2%/yr | 5.3%/yr | 0.9%/yr |
| **3%** | **15.0%/yr** | **6.3%/yr** | **1.8%/yr** |
| 4% | 15.9%/yr | 7.2%/yr | 2.8%/yr |
| 5% | 16.7%/yr | 8.0%/yr | 3.7%/yr |

**Current best achieved decoupling: ~2.5–2.8%/yr (high-income countries, 2010–2020)**

What this means:

- **1.5°C is essentially gone** regardless of growth path — even at zero growth, you need 12.5%/yr decoupling, roughly 5x the best rate ever achieved
- **2°C at normal growth rates (3%) requires 6.3%/yr** — more than double the current best. This is not "approximately on track." It's a major acceleration that has not yet been demonstrated
- **~3°C at moderate growth is where current trends land** — 1.8%/yr needed vs. ~2.2%/yr being achieved

The papers are right that current decoupling rates are insufficient for safe climate outcomes at normal growth rates. Where we push back: they treat these rates as fixed structural constants. Decoupling *is* accelerating (from -1.25%/yr in 1970–1990 to -2.23%/yr in 2010–2020 globally), and we're at the early stage of an energy transition that could dramatically increase the rate. But "could" is doing a lot of work in that sentence.

![Decoupling trends](charts/19_decoupling_trends.png)
*Top-left: CO₂ intensity of GDP is falling everywhere, with high-income countries leading. Top-right: The rate of decline is accelerating by decade. Bottom-left: Absolute emissions — the US, EU, and Japan are declining; China and India still rising. Bottom-right: Energy intensity follows a similar pattern.*

![Absolute decoupling and climate constraints](charts/21_absolute_decoupling.png)
*Top-left: GDP (solid) vs CO₂ (dashed) for the US, UK, and Germany since 1990, showing absolute decoupling. Top-right: When each country's CO₂ peaked. Bottom-left: Rolling decoupling rate — we're achieving ~2–3%/yr but need 3.5%+ for 1.5°C. Bottom-right: The required decoupling rate for each growth rate × carbon budget combination.*

### What if only the poor world grew?

This is a critical test. The poor world (countries below $15k GDP/capita) currently produces only **20% of global CO₂** despite being 55% of the population. If the rich world froze its emissions while the poor world grew to the good-life threshold:

- The 1.5°C budget is blown in **8 years** regardless — because the rich world's existing 30 Gt/yr baseline eats it immediately
- The 2°C budget is exceeded in **27–32 years** depending on decoupling assumptions
- The poor world's growth to $15k/capita (a 2.1x multiplication over 15 years) adds only a modest amount to global emissions

**The planetary boundary problem is overwhelmingly a rich-world emissions problem, not a poor-world growth problem.**

![Poor-world-only growth scenario](charts/22_poor_world_growth_scenario.png)
*Left: Annual global CO₂ under different decoupling scenarios with the rich world frozen. At 4–5%/yr decoupling, annual emissions decline steadily. Right: Cumulative emissions vs carbon budgets. The 1.5°C budget is unreachable in all scenarios; the 2°C budget is a stretch but not impossible with aggressive decoupling.*

---

## The Redistribution Gap: What's Actually Delivered vs. What's Proposed

GPT-5.4's sharpest criticism was that we treated redistribution as a simple policy lever without examining whether it actually gets pulled. The data on this is devastating — and it cuts against *both* sides.

### The scale problem

The papers propose redistribution of $1.3–6 trillion per year to close poverty gaps. Here's what the international system actually delivers:

![ODA reality](charts/24_oda_reality.png)
*Top-left: Global ODA has grown but remains a fraction of even the extreme poverty gap. The green dashed line shows the $2.15/day poverty gap ($332B) — ODA has never reliably exceeded it. Bottom-left: Only 5-6 countries consistently meet the UN 0.7% ODA/GNI target. The US gives 0.22% (heading to ~0.10% after recent cuts); the UK cut from 0.72% to ~0.40%. Bottom-right: The scale problem on a log chart — total ODA is two orders of magnitude smaller than the realistic $6.85/day gap.*

| Flow | Amount | Scale Reference |
|---|---|---|
| Total global ODA (2022) | ~$200B | |
| Poverty gap at $2.15/day | $332B | ODA covers ~60% |
| Poverty gap at $6.85/day (perfect) | $7,755B | ODA covers ~2.6% |
| Poverty gap at $6.85/day (realistic 3x) | $23,264B | ODA covers ~0.9% |
| Papers' proposed redistribution | $1,300–6,000B | **6–30x total current ODA** |

The papers' redistribution proposals aren't just politically difficult — they're asking for 6 to 30 times the entire current international aid system. In 50+ years, the world has never come close to the 0.7% GNI target (the DAC average is 0.36%), and the trend is **downward** — the US and UK, two of the largest donors, are actively cutting.

### And the headline numbers overstate reality

Your point about questionable items being billed as aid is well-documented:

- **14.4% of DAC ODA in 2022** ($29.3B of $204B) was in-donor refugee costs — money that never left the donor country
- Sweden counted domestic refugee housing as "ODA," inflating its ratio to 1.4% of GNI in 2015
- Debt relief shows up as "new aid" (Iraq relief added ~$14B to 2005 figures)
- Administrative costs of aid agencies count
- ~20% of bilateral ODA is still tied (recipient must buy donor goods, reducing effective value by 15-30%)

Effective real resource transfer to poor countries is roughly **25-40% less** than the headline ODA number suggests.

### The "squeezed middle" is real

The papers treat rich-world redistribution as a policy choice blocked by greed. The data suggests something more structural:

![Domestic redistribution](charts/25_domestic_redistribution.png)
*Top-left: Tax revenue as % of GDP varies enormously (Sweden ~28%, US ~11%, China ~8%). Bottom-left: Rich-world GDP/capita growth has roughly halved — from 2.5-6.5%/yr in 1960-75 to 0.9-1.7%/yr in 2010-23. This isn't imagined. Bottom-right: Countries with higher domestic tax rates tend to give more ODA — domestic and international redistribution come from the same political wellspring.*

| Country | Growth 1960–75 | Growth 2010–23 | Decline |
|---|---|---|---|
| United States | 2.5%/yr | 1.7%/yr | -32% |
| United Kingdom | 2.3%/yr | 1.0%/yr | -57% |
| Germany | 3.2%/yr | 1.3%/yr | -59% |
| France | 4.2%/yr | 0.9%/yr | -79% |
| Japan | 6.5%/yr | 1.1%/yr | -83% |

When GDP/capita growth halves and domestic inequality widens, the median voter feels stagnant even as aggregate GDP rises. Telling these voters to increase foreign aid is a political non-starter — not because they're selfish, but because their real experience is one of diminishing returns from the growth model.

**This is the deepest challenge to the papers' proposed solution:** redistribution requires political will, political will requires voters who feel they have enough to share, and the rich-world growth slowdown has eroded exactly that feeling. The papers' logical chain — "redistribution is efficient, therefore we should redistribute" — skips the hardest step.

### The energy S-curve: the wildcard

One reason for optimism despite the political economy problem:

![Energy transition S-curve](charts/26_energy_transition_scurve.png)
*Top-left: Solar generation has gone from 4 TWh (2005) to 2,128 TWh (2024) — a 500x increase, doubling every ~3 years. Top-right: Solar + wind now supply ~15% of global electricity and the curve is steepening. Bottom-left: Fossil fuels have fallen from 94% to 81% of primary energy. Bottom-right: Renewable electricity shares by country — Germany and UK above 50%, world average approaching 30%.*

Solar is doubling every 3 years. If that rate continues:
- By 2030: ~4,000-5,000 TWh (matching current US total electricity)
- By 2035: ~10,000 TWh (approaching global electricity needs)

This could resolve the tension between growth and climate in a way that neither the papers' redistribution proposals nor current policy trajectories anticipate. The energy transition is the variable that could make 4-5%/yr decoupling achievable — moving us from the 3°C path to something closer to 2°C.

---

## Independent Critical Review

*This section was written by GPT-5.4 as an independent assessment of the entire project.*

This project is materially stronger than the polemical claim it is responding to. It does not just wave at "growth" in the abstract; it breaks the question into poverty gaps, regional composition, convergence, elasticity, redistribution cost, historical growth episodes, decoupling, and carbon-budget arithmetic. That is the right way to approach a loaded ideological argument. The project uses mainstream public sources — World Bank poverty data, WDI, Maddison Project, and OWID — giving it a credible empirical foundation. But a credible foundation is not the same as a decisive argument, and some of the project's most confident conclusions go further than its own evidence allows.

### What's Solid

The single strongest empirical move is the poverty-gap-as-share-of-GDP framing. If the global poverty gap at $2.15 fell from 3.1% of world GDP in 1990 to 0.17% in 2024, and the $6.85 gap fell from roughly 39% to roughly 5%, that is a major fact. It means growth did not "solve" poverty, but it dramatically changed the fiscal scale of the problem. A world where the extreme-poverty gap is $332 billion is morally scandalous, but it is not resource-constrained in the same way a world with a 3.1% GDP gap was.

The project deserves credit for using multiple thresholds rather than hiding behind $2.15 alone. The convergence analysis is especially good: showing that population-weighted convergence is real while unweighted sigma divergence worsened from 0.95 to 1.21 is exactly the kind of distinction serious work should make.

The carbon-budget correction is probably the project's most valuable single contribution. It replaces fuzzy ecological rhetoric with explicit rates: ~12.5% annual decoupling for 1.5°C at zero growth, 6.3% for 2°C at 3% growth, 1.8% for 3°C at 3% growth. That is clear, falsifiable, and much better than ideological handwaving from either side.

### Blind Spots and Steel-Man Arguments Missed

**The biggest blind spot is political economy.** The project correctly identifies that "capitalism is unworkable" requires equating capitalism with zero redistribution, which is empirically false (Nordic social democracy exists). But this only defeats a weak version of the anti-capitalist claim. A stronger version is that capitalist systems have a *persistent tendency* to underprovide redistribution and overexploit ecological sinks because profits are private, losses are socialized, and wealthy coalitions resist both taxes and climate constraints. The project says redistribution is possible. The papers would reply that the problem is it is *systematically not done*.

**The ecological rebuttal is too carbon-centric.** The papers invoke "planetary boundaries" — plural. Material extraction, land use, biodiversity loss, nitrogen cycles, water stress, and mining impacts from energy transition minerals are mostly outside the analysis frame. If the papers wanted to strengthen their case, this is exactly where they should press.

**The exploitation analysis is too narrow.** Carbon-accounting geography doesn't capture the full dependency critique. Terms of trade, ownership of supply chains, debt discipline, intellectual property regimes, currency hierarchy, and historical extraction all matter. The analysis knocks down a crude emissions-offshoring story. It does not dispose of dependency-style critiques in general.

### Where the Project's Own Arguments Are Weakest

The corrected carbon arithmetic actually supports a significant part of the ecological critique. The numbers show:

- 1.5°C is effectively unattainable under any plausible macro path
- 2°C with continued 3% global growth requires **more than double** the best recent decoupling performance (6.3%/yr vs. 2.8%/yr achieved)
- Current trends are compatible with **~3°C warming** — which is not "on track" in any policy-relevant sense

Saying "we're on track for 3°C because only 1.8% decoupling is needed" is not a defense of the growth model. It is an admission that current trajectories are compatible with dangerous warming.

The project also underplays how much its own poverty analysis vindicates the papers at higher thresholds. If the realistic redistribution cost at $6.85/day is $23.3 trillion (11.65% of GDP), then the remaining task is genuinely enormous — not a rounding error that growth has nearly solved.

### Independent Insights

The most important thing this data implies is something neither side states cleanly: **growth and redistribution are complements, not substitutes.**

Growth has done two things at once: it has raised floors somewhat (P5 income: $620→$1,378, 1950–2022) and it has dramatically reduced the share of world output required to close the very bottom poverty gaps. That means growth has real moral value even when it is not sufficient. But it also means the remaining obstacle to ending extreme poverty is now more political than material.

However, once you move from destitution to mass flourishing, redistribution alone stops being a serious answer. You cannot permanently cash-transfer billions of people into durable prosperity without productivity, infrastructure, urban systems, public health, education, electricity, housing, and functioning states. That is why the project is right to emphasize development and why the papers are right to emphasize distribution.

### The Real Dispute

The real dispute is not "growth or redistribution." It is **what mix of growth, redistribution, industrial policy, public goods, and climate constraint can actually work** — and whether existing political-economic institutions are capable of delivering that mix fast enough.

---

## What a Reasonable Person Should Conclude

Based on all the evidence assembled here, three claims are well-supported and two are not.

### Supported by the data:

1. **Growth alone is not enough.** The papers are right that undirected growth with current distributional patterns cannot eliminate poverty at meaningful thresholds fast enough. Growth elasticities decline at higher poverty lines, Sub-Saharan Africa is being left behind, and redistribution is 100–2,000x more efficient per dollar at reaching the poor.

2. **Anti-market alternatives are not credible.** Zero sustained high-growth episodes without market mechanisms. The USSR and every command economy hit innovation walls. China's market reforms doubled its growth rate. The evidence overwhelmingly supports market economies — but heavily managed ones with strong state capacity and redistribution, not laissez-faire.

3. **The climate constraint is severe and binding.** Current decoupling rates of ~2.5–2.8%/yr land us at roughly 3°C. Staying under 2°C at normal growth rates requires more than doubling the best decoupling performance ever achieved. This is not impossible — the energy transition is accelerating — but it's a bet on unprecedented deployment speed, not a projection of current trends.

### Not supported by the data:

4. **"Capitalism is mathematically unworkable"** — The papers do not prove this. They prove that growth *alone*, with *current distribution*, at *current coupling rates* is insufficient. Those are all policy variables, not laws of nature. Capitalist economies with redistribution exist. Decoupling is accelerating. The "175x GDP" scenario assumes everyone converges to American consumption, which no one proposes.

5. **"The current growth model is basically on track"** — The project's own numbers refute this. 2°C requires decoupling rates we have not demonstrated. 3.5 billion remain below $6.85/day. Success is concentrated in East Asia. The honest position is that growth has created enormous surplus and capacity, but the institutions for directing it — toward redistribution, decarbonization, and development in the hardest places — are inadequate.

### The bottom line

The world has enough productive capacity to end extreme poverty. It has enough historical evidence to know markets and growth matter. It has enough climate evidence to know the current way of doing growth is environmentally inadequate. **The real failure is not mathematical impossibility. It is political inability.**

The nuclear reactor metaphor stands: capitalism is a powerful energy source that has already generated unprecedented material progress and made redistribution cheaper than at any point in history. The question is whether we can build the containment structures — institutions, redistribution, climate policy, development assistance — fast enough to prevent meltdown. The papers make a compelling case that the containment is currently insufficient. They do not make a compelling case that the reactor should be shut down.

---

## Appendix: Methodology

### Data Sources

| Source | Dataset | Coverage | Key Variables |
|---|---|---|---|
| [World Bank WDI](https://data.worldbank.org/) | World Development Indicators | 1960–2024, ~200 countries | GDP (constant 2015 USD, PPP), population, life expectancy, under-5 mortality, Gini |
| [World Bank PIP](https://pip.worldbank.org/) | Poverty and Inequality Platform | 1981–2024, country + regional | Headcount ratios and poverty gaps at $2.15, $3.65, $6.85, $10.0/day |
| [Maddison Project](https://www.rug.nl/ggdc/historicaldevelopment/maddison/) | MPD 2023 | 1–2022, 169 entities | GDP per capita (2011 int'l $), population |
| [Our World in Data](https://github.com/owid/co2-data) | CO₂ and Greenhouse Gas Emissions | 1750–2024 | CO₂ (production + consumption), CO₂/GDP, CO₂/energy, energy/GDP, trade CO₂ |
| [Our World in Data](https://github.com/owid/energy-data) | Energy Dataset | 1965–2024, 200+ entities | Solar/wind/fossil generation (TWh), renewable shares, energy mix |
| [World Bank WDI](https://data.worldbank.org/) | ODA & Fiscal Indicators | 1960–2024 | Net ODA received, bilateral ODA by donor, tax revenue/GDP, GDP/capita growth |

### Analysis Scripts

All scripts are in the `analysis/` directory and can be run sequentially:

```bash
# Set up environment
python3 -m venv .venv && source .venv/bin/activate
pip install pandas numpy matplotlib seaborn requests openpyxl xlrd scipy statsmodels

# Download all data
python analysis/download_data.py

# Run analyses
python analysis/run_analysis.py      # Core poverty & growth analysis (Charts 01–08)
python analysis/run_analysis_2.py    # Poverty-growth feedback & structural profiles (Charts 09–12)
python analysis/run_analysis_3.py    # Floor-raising, good-life threshold, Preston curve (Charts 13–16)
python analysis/run_analysis_4.py    # Market reforms, command vs market economies (Charts 17–18)
python analysis/run_analysis_5.py    # Decoupling, planetary boundaries, trade flows (Charts 19–23)
python analysis/run_analysis_6.py    # ODA, political economy, energy transition (Charts 24–27)
```

### Analysis Pipeline

1. **`download_data.py`** — Fetches and caches all datasets from World Bank APIs, Maddison Excel, and OWID GitHub. Raw data stored in `data/raw/`; processed CSVs in `data/processed/`.

2. **`run_analysis.py`** — Seven-part analysis:
   - Poverty gap as % of global GDP over time (all 4 thresholds)
   - Regional decomposition of poverty reduction
   - Growth trajectories normalized to takeoff date
   - Sigma and beta convergence (weighted and unweighted)
   - Growth elasticity of poverty by region
   - Redistribution cost at each threshold (perfect and 3x realistic targeting)
   - "Flying geese" growth rotation pattern

3. **`run_analysis_2.py`** — Tests poverty–growth feedback loops, demand injection from poverty gap closure, structural profile of $6.85/day economies, transition paths.

4. **`run_analysis_3.py`** — Floor-raising vs convergence framing. Tracks GDP per capita by percentile (P5, P10, P20, P50, P90) over time. Preston curve analysis. "Good life" threshold identification.

5. **`run_analysis_4.py`** — Historical analysis of market reforms and growth. USSR trajectory, sustained growth episodes classified by economic system, China Mao vs reform period comparison.

6. **`run_analysis_5.py`** — Carbon intensity trends and acceleration. Production vs consumption-based emissions. Trade CO₂ flows (exploitation hypothesis test). Carbon budget arithmetic for required decoupling rates. Poor-world-only growth scenario. Energy transition decomposition.

6. **`run_analysis_6.py`** — Political economy of redistribution. ODA trends vs poverty gaps. The 0.7% GNI target. ODA quality problems (in-donor refugee costs, tied aid). Rich-world growth slowdown. Domestic vs international redistribution correlation. Energy transition S-curve. Terms of trade.

### Key Methodological Notes

- **Poverty gap calculations** use World Bank PIP data. The "gap" is the total income shortfall below each poverty line, aggregated across all people below the line. The "realistic 3x" estimate follows the literature's rule of thumb that targeting inefficiency, administrative costs, and behavioral responses roughly triple the perfect-targeting cost.

- **Convergence analysis** uses Maddison GDP per capita. Sigma convergence is the standard deviation of log GDP/capita across countries. Beta convergence regresses growth rates on initial income levels. Both are computed weighted (by population) and unweighted.

- **Decoupling rates** are computed as annualized rates: $\left(\frac{I_t}{I_0}\right)^{1/t} - 1$ where $I$ is CO₂ intensity (CO₂/GDP). The decomposition splits CO₂/GDP into (CO₂/Energy) × (Energy/GDP) to separate energy mix cleaning from efficiency gains.

- **Carbon budget scenarios** compute the required annual intensity decline rate $d$ such that cumulative emissions $\sum_{t=0}^{49} E_0 \cdot (1+g)^t \cdot (1-d)^t \leq B$ where $E_0$ is current annual emissions, $g$ is GDP growth, and $B$ is the remaining carbon budget. Solved by binary search.

- **"Good life" threshold** is identified empirically: the GDP per capita above which ≥91% of country-year observations achieve life expectancy ≥70 years. This converges at approximately $15,000 (2011 international $).

### Charts Index

| Chart | File | Description |
|---|---|---|
| 01 | `01_poverty_gap_pct_gdp.png` | Poverty gap as % of global GDP, 4 thresholds |
| 02 | `02_poverty_by_region.png` | People in poverty by region, 4 thresholds |
| 03 | `03_growth_trajectories.png` | Historical GDP/capita trajectories |
| 04 | `04_convergence.png` | Sigma and beta convergence |
| 05 | `05_growth_elasticity.png` | Growth elasticity of poverty by region |
| 06 | `06_redistribution_cost.png` | Cost of ending poverty at each threshold |
| 07 | `07_growth_rotation.png` | "Flying geese" growth leadership rotation |
| 08 | `08_escape_velocity.png` | Escape velocity — who grew fastest |
| 09 | `09_poverty_and_growth.png` | Poverty–growth feedback analysis |
| 10 | `10_building_685_economy.png` | Structural profile of $6.85/day economies |
| 11 | `11_demand_injection.png` | Demand injection from poverty gap closure |
| 12 | `12_path_to_685.png` | Transition paths to $6.85/day |
| 13 | `13_floor_rising.png` | Floor-raising by income percentile |
| 14 | `14_good_life_threshold.png` | "Good life" threshold & Preston curve |
| 15 | `15_nebraska_inequality.png` | Inequality dynamics & growth |
| 16 | `16_floor_scorecard.png` | Floor-raising scorecard |
| 17 | `17_market_reforms_growth.png` | Market reforms & growth episodes |
| 18 | `18_command_vs_market.png` | Command vs market economy growth |
| 19 | `19_decoupling_trends.png` | Carbon & energy decoupling trends |
| 20 | `20_co2_trade_exploitation.png` | CO₂ trade flows & exploitation test |
| 21 | `21_absolute_decoupling.png` | Absolute decoupling & climate constraints |
| 22 | `22_poor_world_growth_scenario.png` | Poor-world-only growth scenario |
| 23 | `23_energy_transition.png` | Energy transition progress |
| 24 | `24_oda_reality.png` | ODA flows vs poverty gaps |
| 25 | `25_domestic_redistribution.png` | Tax, spending, and the squeezed middle |
| 26 | `26_energy_transition_scurve.png` | Solar/wind S-curve |
| 27 | `27_debt_and_trade.png` | Debt and terms of trade constraints |

### Tools & Environment

- Python 3.14 with pandas, numpy, matplotlib, seaborn, scipy, statsmodels
- Analysis conducted April 2026
- AI assistants used: Claude Opus 4.6 (primary analysis and writing), GPT-5.4 (independent critical review)

---

*This project is open-source. All data is from publicly available sources. Reproduce, critique, and extend.*
