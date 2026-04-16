# Growth, Poverty, and Planetary Boundaries

**A quantitative response to the claim that capitalism is "mathematically unworkable" for ending global poverty within ecological limits.**

This project uses World Bank, Maddison Project, Our World in Data, OECD, IEA, and USGS data to examine two papers arguing that growth-based poverty elimination is physically impossible and redistribution is the only viable path. The analysis was conducted collaboratively between a human analyst and AI assistants (Claude Opus 4.6 and GPT-5.4). All code, data, and figures are reproducible.

> The full exploratory analysis with all 65 charts, three rounds of GPT-5.4 critical review, and detailed supporting material is preserved in [README_v2_archive.md](README_v2_archive.md).

---

## Executive Summary

Thirteen analyses and 65 charts later, here is what the data shows:

1. **Growth alone cannot end poverty fast enough** at meaningful thresholds. Only 5% of GDP growth reaches the poorest 60%. The papers are right about this.

2. **But growth transformed the scale of the redistribution problem — dramatically at the bottom, modestly at higher thresholds.** The $6.85/day poverty gap fell from 18% to 1.6% of world GDP — from a genuinely crushing burden to a large but conceivable one. At $2.15/day, the gap is now smaller than existing aid flows. But 3.14 billion people remain below $6.85/day, a $3.1 trillion shortfall that international transfers cannot reliably close — not because the money doesn't exist, but because there is no sovereign authority to guarantee it. Domestic transfers (pensions, disability, UBI) work because states have taxing power and accountability to recipients. International aid has neither: one political pivot in a major donor can halve it overnight.

3. **The ecological constraint is real and differentiated.** Carbon has a clear technological pathway (renewables) that requires deployment at unprecedented speed. Nitrogen (3.4× over) is addressable through a stack of agricultural bioengineering, food technology, and precision farming — but requires breakthroughs (especially nitrogen-fixing cereals) not yet deployed. The aggregate "material footprint" metric overstates the constraint by treating all tonnes as equal; the boundary-specific problems (nitrogen, biodiversity, land use) are genuinely severe while the mass-based metric is weaker than the carbon budget. Six of nine planetary boundaries are breached.

4. **Poverty is a flow problem, not a stock problem.** The papers frame poverty as a gap to be filled with transfers. But even if you lifted everyone above $6.85/day tomorrow, you'd need to do it again next year — forever — unless the underlying economies develop the productive capacity to sustain welfare. Aid is humanitarian insurance (~10% of total resource flows to the developing world); investment is the growth driver (FDI alone is 4× all ODA).

5. **The development recipe is clear and not region-specific.** Peace, macroeconomic stability, high investment rates (25–40% of GDP), early fertility decline, trade openness, and capable states predict success. Bangladesh, Rwanda, and Vietnam demonstrate this is not an "Asian" formula. The most powerful rich-country levers are not aid but trade access, FDI facilitation, and cheaper remittance corridors.

6. **Sustainable consumption is about composition, not deprivation.** The ecological constraint is real but the aggregate "material footprint" conflates sand with burned coal. The ecologically destructive components of consumption — fossil fuels, nitrogen-intensive agriculture, land clearing — are artifacts of current technology, not inherent to high welfare. A post-transition economy at ~9 t/cap (mostly construction maintenance and recycled metals) has *less* ecological impact than today's 5 t/cap economy that includes fossil fuels and deforestation. The target is not less stuff but different stuff — and the technology pathways to get there are on observable S-curves.

---

## The Debate

Two papers were presented as proof that capitalism is "mathematically unworkable" and that there is "a moral imperative to move beyond it."

**Paper 1 — "Growth Alone Cannot End Poverty"** makes three interlocking arguments:

- *Arithmetic*: Between 1990–2008, every $100 of per capita growth contributed only $0.60 to poverty reduction below $1/day — a 166:1 inefficiency ratio. The poorest 60% received just 5% of new income. Growth elasticity of poverty collapses at higher thresholds (from –2.0 at $1.90/day to near zero at $6.85), meaning growth increasingly bypasses the poor as ambition rises.
- *Provisioning*: The world already extracts ~100 Gt of materials per year — enough to meet basic needs for 8.5 billion people several times over. The problem is allocation, not production capacity. Decent living standards require roughly 28–40 Gt/yr, well within current extraction. GDP growth is the wrong tool because capital flows toward profitable returns, not essential needs.
- *Ecological*: Material extraction is already 2× the sustainable limit (~50 Gt/yr). A synthesis of 835 peer-reviewed studies (Haberl et al. 2020) found absolute decoupling of GDP from material use "rare" and never observed at global scale. Even countries with absolute CO₂ decoupling would need 220+ years at achieved rates to cut emissions 95%, overshooting fair-share carbon budgets by 27×. The remaining 1.5°C carbon budget is exhausted in 6–10 years at current emissions.

The paper's strongest claim is not the 175× GDP headline. It is that a system which allocates by profitability rather than need will predictably underdeliver redistribution and ecological restraint — and that historically, it has.

**Paper 2 — "Measuring Global Poverty"** is the more methodologically rigorous of the two, and its real contribution is showing how measurement choices shape the narrative:

- *Threshold sensitivity*: At $2.15/day, both rates and absolute numbers fell dramatically. At $6.85/day, the rate fell (67% → 47%) but absolute numbers barely moved — ~3.5 billion for three decades. The poverty line you choose determines whether you see triumph or stagnation.
- *PPP and BNPL uncertainty*: The alternative Basic Needs Poverty Line methodology avoids PPP conversions by comparing incomes to local prices of essentials, finding more modest progress (only 6 percentage points of decline, 1980–2011, with absolute numbers *rising*). But BNPL has its own fatal flaw: under socialist price controls with severe shortages, low nominal prices produce artificially low poverty counts despite actual scarcity — making pre-reform China look implausibly good.
- *Non-income confirmation*: Independent welfare indicators (life expectancy +7 years, child mortality –59%, literacy 76% → 87%, caloric supply +400–600 kcal) confirm real material improvement that cannot be dismissed as a PPP artifact.
- *China's outsized not determinative role*: China drove ~75% of extreme poverty reduction, but excluding China entirely still shows poverty rates falling from 33% to 12% (1990–2025). Both camps overstate what China proves: growth-pessimists use it to minimize global progress; growth-optimists credit "capitalism" when China used heterodox state-directed development.

It concludes that *"whether this requires systemic transformation or continued growth is not a question empirical methodology alone can answer"* — and that measurement itself is political: the $1.90 line makes the world look like a success story; the $7.40 line makes it look catastrophic; both describe the same underlying reality.

We largely agree with Paper 2's measured framing. Our pushback is mainly against Paper 1's leap from "growth alone is insufficient" (true) to "capitalism is mathematically unworkable" (not supported). But Paper 1's provisioning and system-dynamics arguments deserve more serious engagement than most growth-optimist responses give them.

---

## Where the Papers Are Right

### Growth alone is too slow and too blunt

If only 5% of GDP growth reaches the poorest 60%, then relying on undirected growth to eliminate poverty is grotesquely inefficient. Our data confirms this: growth elasticities of poverty decline at higher thresholds, and progress above $6.85/day has been far more modest than the headline $2.15 numbers suggest.

![Regional poverty decomposition](charts/02_poverty_by_region.png)
*At $2.15/day, East Asia's dramatic decline dominates the global story. At $6.85/day, South Asia and Sub-Saharan Africa remain largely unchanged. The "declining poverty" narrative is essentially an East Asian story at higher thresholds.*

### Redistribution is vastly more efficient

Direct cash transfers deliver $0.85–$0.90 per dollar to recipients. Growth delivers roughly $0.005 per dollar to the poor. That is a 100:1 to 2,000:1 efficiency gap. For pure poverty-gap closure, there is no contest.

### Sub-Saharan Africa is being left behind

SSA's share of global extreme poverty rose from 13% to 65% while the absolute number of poor people nearly doubled. This is the most serious ongoing development failure, and no amount of global-average optimism erases it.

### Planetary boundaries are real

This is arguably the papers' strongest claim. Six of nine planetary boundaries are now transgressed, and the non-carbon boundaries are in many ways more alarming than the carbon story.

![Planetary boundaries scorecard](charts/31_planetary_scorecard.png)
*Four boundaries are clearly exceeded (red), three are at or near the limit (orange), and only ozone is recovering — thanks to the Montreal Protocol, one of the few successful global environmental agreements.*

| Boundary | Safe Limit | Current | Status |
|---|---|---|---|
| Climate change (CO₂) | 350 ppm | 424 ppm | **Exceeded** |
| Biosphere integrity (LPI) | 90 (index) | 27 (index) | **Exceeded** |
| Nitrogen fixation | ~44 Tg/yr | ~150 Tg/yr | **Exceeded (3.4×)** |
| Land-system change | 75% forests | 68% forests | **Exceeded** |
| Freshwater use | 4,000 km³/yr | ~3,949 km³/yr | At limit |
| Phosphorus flow | 11 Tg/yr | ~9 Tg/yr | Near limit |
| Ocean acidification | 2.75 Ω | 2.8 Ω | Near limit |
| Ozone depletion | 276 DU | 284 DU | Safe (recovering) |

### Progress depends on which poverty line you use

At $2.15/day, the world has achieved extraordinary progress — from 1.9 billion (36%) in 1990 to 0.45 billion (5.7%) in 2024. At $6.85/day, 3.14 billion people remain below the line, with only modest improvement in absolute numbers. The papers are right to insist on higher thresholds.

---

## The Poverty Arithmetic: What Growth Actually Changed

The papers frame growth and redistribution as alternatives. Our central finding is that they are complements. Growth didn't solve poverty directly, but it transformed the fiscal problem of solving it.

### Growth made redistribution dramatically cheaper — but it was never truly impossible

![Poverty gap as share of GDP](charts/01_poverty_gap_pct_gdp.png)
*The poverty gap at every threshold has fallen as a share of global GDP. At $2.15/day: from 1.4% to 0.06%. At $6.85/day: from ~18% to ~1.6%. Growth created the surplus from which redistribution can draw — though at $2.15, even the 1990 gap was within fiscal reach.*

| Poverty Line | People Below | Gap (Perfect) | Realistic Cost (3×) | % of World GDP |
|---|---|---|---|---|
| $2.15/day | 0.45B | $118B | $354B | 0.18% |
| $3.65/day | 1.21B | $560B | $1,680B | 0.84% |
| $6.85/day | 3.14B | $3,132B | $9,396B | 4.71% |

The trajectory tells the story: at $6.85/day, the gap fell from 18.1% of world GDP in 1990 to 1.6% today — still enormous in absolute terms ($3.1 trillion), but a 91% decline relative to global capacity. At $2.15/day, total ODA ($203B) now exceeds the theoretical poverty gap ($118B) — though even the 1990 gap of 1.4% of GDP was never a true resource constraint. For intuition: France collects 45% of GDP in taxes within its borders — 1.4% was never an arithmetically impossible ask, even if cross-border redistribution faces fundamentally different political obstacles. Growth made an already-solvable problem even cheaper, but the deeper shift is at higher thresholds where the gap was once genuinely crushing.

**Note on units:** Poverty gaps are in PPP dollars (the poverty line unit). ODA is in nominal USD. These ratios are approximate heuristics, not exact financial equivalences.

### The target is basic welfare, not American consumption — but that raises hard questions

The papers' most alarming scenario assumes everyone must converge to American consumption levels — a common rhetorical benchmark but not a serious policy target. A useful welfare proxy — the GDP per capita above which 91–95% of country-years achieve life expectancy ≥70 — converges at approximately **$15,000 per capita (PPP)**. This is a rough heuristic, not a definitive threshold. But it suggests the target is closer to 2× current poor-world GDP than to 175×.

This reframing, however, creates a moral problem we should not dodge. If $15,000 is "enough" for the poor world, why does the US consume at $75,000 — five times that level? Our own ecological data answers that question uncomfortably: **the US material footprint is 22.7 tonnes per capita against a sustainable limit of 5–8 tonnes.** Rich-world consumption is not just excessive relative to the poor world's needs; it is ecologically indefensible on its own terms. The planetary boundaries analysis in this project shows that even if the poor world stopped growing entirely, the rich world's current throughput still breaches multiple boundaries.

So the honest position is: yes, the poor world needs growth to reach basic welfare thresholds, and that growth does not require American consumption levels. But the rich world also needs to *reduce* its material throughput substantially — and whether market economies can deliver that reduction is genuinely uncertain. The morally defensible endpoint is not universal Americanization or poor-world restraint: it is upward convergence in human welfare and downward convergence in material throughput. Our data shows a few rich countries (UK, Germany) making progress on material decoupling, but none are anywhere near the sustainable limit. This is one of the strongest points in the papers' favor, and the provisioning critique deserves engagement: decent lives require specific material throughputs with real ecological costs, and the world may already produce enough to meet those needs through reallocation rather than further aggregate growth. Our $15k life-expectancy proxy is useful but does not directly rebut that framework.

![The good-life threshold](charts/14_good_life_threshold.png)
*Life expectancy reaches ~75 years around $15k GDP/capita, with sharp diminishing returns beyond that. Countries below this threshold need roughly 2× their current GDP, not 175×. At 5% growth, that is 15 years — not two centuries.*

### ODA and the extreme poverty gap converged

![ODA vs poverty gap convergence](charts/24b_oda_poverty_gap_convergence.png)
*The $2.15/day poverty gap fell from $420B to $118B while ODA rose to $203B — they crossed around 2018. At higher thresholds, ODA covers only 6% of the gap. Growth brought the extreme-poverty mountain down to where aid could reach it.*

### But the scale problem at higher thresholds is genuine

The papers propose redistribution of $1.3–6 trillion per year. Total global ODA is ~$224 billion (2024 OECD preliminary), stagnant and trending downward in several major donors. The proposals require 6–30× the entire current international aid system. In 50+ years, the world has never come close to the 0.7% GNI target (the DAC average is 0.36%). Redistribution at the scale needed for $6.85/day is not in any plausible political pipeline. Historically, every development success story — China, South Korea, Vietnam, Bangladesh, Botswana, Chile — was driven by FDI, export manufacturing, domestic savings, and state-directed industrial policy, not by international transfers. Higher-threshold gaps have only ever been closed by sustained domestic growth.

---

## The Ecological Constraint

### Carbon: severe, with a plausible but unproven technological pathway

The carbon budget arithmetic is sobering.

| Growth Rate | Required decoupling for 1.5°C | For 2°C | For ~3°C |
|---|---|---|---|
| 0% growth | 12.5%/yr | 3.4%/yr | 0.0%/yr |
| **3% growth** | **15.0%/yr** | **6.3%/yr** | **1.8%/yr** |
| 5% growth | 16.7%/yr | 8.0%/yr | 3.7%/yr |

**Current best achieved: ~2.5–2.8%/yr (high-income countries, 2010–2020).**

1.5°C is effectively gone regardless of growth path — even at zero growth, you need 12.5%/yr decoupling, roughly 5× the best ever achieved. 2°C at normal growth rates requires more than double the best performance. Current trends are compatible with roughly 3°C — which is not "on track" in any policy-relevant sense.

The energy transition is the wildcard. Solar generation grew from 4 TWh (2005) to 2,128 TWh (2024), doubling every ~3.2 years. If that continues, solar could supply 25% of global electricity by 2030. This *could* make 4–5%/yr decoupling achievable — but "could" is carrying substantial weight. The transition requires significant mineral inputs (lithium, cobalt, copper), though extraction volumes are 1–2 orders of magnitude smaller than the fossil fuels they replace, and minerals are recyclable while fossil fuels are burned once.

![Decoupling and carbon constraints](charts/21_absolute_decoupling.png)
*Absolute decoupling is happening in the US, UK, and Germany. But rolling rates of ~2–3%/yr need to at least double for 2°C compatibility at normal growth rates.*

### The poor world's growth is not the problem

The poor world (below $15k GDP/capita) produces only 20% of global CO₂ despite being 55% of the population. If the rich world froze emissions while the poor world grew to $15k, the 1.5°C budget is still exhausted in 8 years by the rich world's existing baseline alone.

![Poor-world-only growth scenario](charts/22_poor_world_growth_scenario.png)
*The planetary boundary problem is overwhelmingly a rich-world emissions problem, not a poor-world growth problem.*

### Beyond carbon: harder problems with emerging solutions

Carbon gets the headlines, but the non-carbon boundaries are arguably more concerning — because they lack equivalent technological exits.

![Material footprint](charts/28_material_footprint.png)
*Material intensity of GDP is declining at only 0.4%/yr — compared to 1.8%/yr for carbon. But see the discussion below on whether aggregate material tonnage is the right metric: a tonne of sand is not a tonne of burned coal.*

![Material vs carbon decoupling](charts/32_material_vs_carbon.png)
*Since 2000, carbon intensity fell ~30% while material intensity fell only ~8%. However, the composition of material extraction matters enormously — the energy transition eliminates the most ecologically damaging 15% entirely.*

The technology pathway analysis reveals a clear pattern:

| Boundary | Technology Exit? | Key Constraint |
|---|---|---|
| **Carbon** | Clear (solar/wind) | Deployment speed |
| **Freshwater** | Partial (desalination) | Too expensive for agriculture (70% of use) |
| **Nitrogen** | Emerging (bioengineering stack) | N-fixing cereals (holy grail, 10-20yr), cultivated meat, precision ag. Full stack could reach boundary but requires multiple breakthroughs |
| **Phosphorus** | Partial (recycling, recovery) | An element — cannot be synthesized, but can be recovered from waste streams |
| **Biodiversity** | Indirect (food tech → land release) | Population peak + ag tech could free 1-2B ha, but only if food technology scales |

Abundant cheap energy solves the energy-system boundaries and *enables* the agricultural technology stack (precision farming, controlled-environment agriculture, cultivated meat) — but the biogeochemical boundaries also require bioengineering breakthroughs and governance. **The papers' critique is weakest where technology has a clear deployment path (carbon), moderate where technology solutions exist but require breakthroughs (nitrogen, food/land), and strongest where harm is irreversible (biodiversity loss already incurred).** The honest response requires technology-driven decoupling for energy, bioengineering for agriculture, *and* governance-driven restraint for land use.

### The implied policy differentiation

The ecological evidence points toward a differentiated strategy rather than a single global prescription. Rich countries — which produce 80% of CO₂ on 45% of population — need rapid decarbonization and reduced material throughput. Poor countries still need substantial productivity growth to reach basic welfare thresholds, and that growth will have ecological costs. Both need far stronger ecological governance than currently exists. The question is not "growth or no growth" at the global level. It is whether the institutions exist to deliver restraint where it's needed and development where it's needed — simultaneously and fast enough. Our analysis suggests they currently do not.

### Can everyone live well? What a good future requires

The analysis so far establishes that rich-world material throughput is ecologically indefensible and poor-world growth is necessary. But this frames the future as a zero-sum tradeoff — the rich must consume less so the poor can consume more. Is that actually true? Or is there a plausible technological pathway to universal high welfare within planetary boundaries?

**The most important enabling condition is abundant cheap clean energy.** Solar generation grew from 4 TWh (2005) to 2,128 TWh (2024), doubling every ~3.2 years. Extrapolating that S-curve: ~8,000 TWh by 2030 (27% of current electricity), ~29,000 TWh by 2036 (100% of current electricity), and potentially 40% of all primary energy by 2040. If energy becomes abundant and nearly free, it unlocks a cascade of solutions that are currently too expensive:

| Boundary | What cheap clean energy unlocks | What remains hard |
|---|---|---|
| **Carbon** | Electrify everything; direct air capture at scale | DAC at gigatonne scale is unproven |
| **Freshwater** | Desalination becomes viable even for agriculture | Distribution infrastructure |
| **Nitrogen** | Precision ag, controlled-environment farming (95% N efficiency), cultivated meat (eliminates feed-grain demand), eliminates combustion NOx | N-fixing cereals are the biggest lever but still in R&D (Pivot Bio, ENSA, Gates CSIA). Full stack needed: precision ag alone only reaches 2.4× (insufficient) |
| **Materials** | Recycling becomes economically dominant; circular loops close | Mining the initial stock; some elements scarce |
| **Food/Land** | Vertical farming, precision fermentation, cultured meat | Cultural adoption; transition timeline |
| **Biodiversity** | If food production intensifies off-land, farmland returns to nature | Requires active rewilding, not just stopping damage |

**The food revolution is the second key.** Precision fermentation and cultured meat are on S-curves of their own. If they scale — and cost curves suggest they could — some estimates project freeing up to 75% of agricultural land — the single biggest lever for biodiversity, nitrogen, phosphorus, and the land-system boundary simultaneously. Agriculture is the primary driver of four of the six transgressed boundaries. Shrinking its footprint solves more ecological problems than any other single intervention.

**But does "material footprint" measure the right thing?** The optimistic technology scenario above still leaves the US at ~10.6 tonnes per capita against a "sustainable" budget of ~5.9 (50 Gt ÷ 8.5 billion people). That sounds alarming — until you ask what the 50 Gt limit actually measures and where it comes from.

The ~50 Gt "safe" material extraction limit (UNEP International Resource Panel; Bringezu 2015, Hickel et al. 2022) is far less rigorous than the carbon budget. The carbon budget rests on hard physics: CO₂ concentrations → radiative forcing → temperature, with a clear causal chain. The material budget is an aggregate mass estimate of ecosystem capacity to absorb extraction impacts — and it treats all tonnes as equal. A tonne of sand from a quarry and a tonne of rainforest cleared for soybeans count the same. They are obviously not the same.

Current global extraction (~100 Gt/yr) breaks down roughly as:

| Category | Gt/yr | Share | Ecological character |
|---|---|---|---|
| Construction minerals (sand, gravel, stone) | 44 | 44% | Quarries, mostly local. Among the *least* ecologically damaging per tonne |
| Biomass (crops, wood, fiber) | 24 | 24% | Agriculture and forestry. Primary driver of land, nitrogen, and phosphorus boundaries |
| Fossil fuels (coal, oil, gas) | 15 | 15% | *Burned and gone*. Drives the carbon boundary. Eliminated by solar/wind/nuclear |
| Metal ores | 10 | 10% | Mining. Concentrated ecological damage, but recyclable |
| Industrial minerals | 7 | 7% | Chemicals, fertilizer feedstocks |

After the energy and food transitions, the composition changes radically: fossil fuels (15 Gt) disappear entirely, agricultural biomass drops sharply, and metal ore extraction falls with circular-economy recycling. What remains is mostly construction minerals and recycled metals — ecologically far less damaging per tonne than what was removed. Whether ~55 Gt of mostly sand, gravel, and recycled steel is ecologically equivalent to today's 100 Gt (which includes burning fossil fuels and clearing forests) is not a question the aggregate metric can answer.

This matters because the aggregate material footprint metric is doing heavy argumentative lifting in both our document and the papers we're responding to. The *boundary-specific* problems — nitrogen fixation at 3.4× the safe limit, biodiversity collapse (73% LPI decline), land-system change — are well-measured and genuinely severe. The "total material extraction" aggregate is a weaker, more contested measure that may significantly overstate the ecological constraint on a post-transition economy.

One comparison illustrates the point: solar is roughly 4,000× less materially intensive than coal per lifetime GWh, because fossil fuels *burn through* their material input while renewables *reuse* their structure. The energy transition does not just solve the carbon problem — it eliminates 15% of global material extraction and transforms energy from a consumable input to durable capital. Nuclear power is similarly capital-intensive but fuel-light. A world running on solar, wind, and nuclear does not face the same material constraint as a world running on coal and oil, even if the aggregate tonnage metric doesn't fully capture that difference.

**What does a sustainable consumption target actually look like?** The aggregate material footprint obscures a crucial insight: different categories of consumption have vastly different ecological impacts. Decomposing the US footprint (22.7 t/cap) into sustainable targets by category:

| Category | Current US | Sustainable Target | How |
|---|---|---|---|
| Fossil fuels | 5.5 t/cap | 0.0 | Solar/wind/nuclear |
| Construction | 7.5 | 4.0 | Dense urbanism (Japanese/European density) |
| Biomass/food | 4.0 | 2.0 | Precision ag + bioreactor protein + waste reduction |
| Metals | 3.0 | 1.5 | Circular economy, 90%+ recycling with cheap clean energy |
| Other/imports | 2.7 | 1.5 | Lighter manufactured goods, digital substitution |
| **TOTAL** | **22.7** | **9.0** | |

The naive "sustainable budget" is 5.9 t/cap (50 Gt ÷ 8.5B). But if you weight by actual ecological damage rather than mass — fossil fuels cause ~40× more damage per tonne than construction minerals — the effective sustainable budget for a post-transition economy is closer to 8–10 t/cap. A person at 9 t/cap of mostly construction maintenance and recycled metal has *less* ecological impact than a person at 5 t/cap whose footprint includes fossil fuels and deforestation-driven agriculture. **Sustainable consumption is not about less stuff. It is about different stuff and different methods.**

**The crucial reframe: welfare can decouple from material throughput even when GDP doesn't fully.** The US economy is already 82% services by value. The marginal unit of American welfare is increasingly weightless — streaming, telehealth, education, AI tools, social connection, creative work. Welfare growth may be far less materially intensive than past GDP growth — better health outcomes, richer experiences, more knowledge, and more creativity do not require proportionally more tonnes of stuff. Whether this constitutes fully "weightless" growth or merely *lighter* growth is an open empirical question. But a future of continued improvement in living standards — more abundance, more research, more exploration, more wonders — does not require proportionally more material extraction, especially once energy is cheap, clean, and abundant.

What does this good future look like concretely?

- **Energy**: abundant, clean, and cheap enough to power desalination, recycling, vertical farming, and direct air capture at scale
- **Food**: this is the hardest boundary, because development and ecological sustainability are in *genuine* tension here. As populations become wealthier, meat consumption rises sharply — from ~10–15 kg/person/year in low-income countries to 60–80 kg in upper-middle-income countries to 125 kg in the US. China's meat consumption quadrupled from 15 to 63 kg/cap between 1980 and 2023. Beef is the critical variable: it requires ~164 m² of land per kg, versus ~7 m² for chicken and ~3 m² for tofu — a 20–50× difference. Without intervention, FAO projects meat demand rising 50–70% by 2050, requiring ~600 million more hectares of agricultural land — roughly all remaining tropical forest.

  Two forces push back. First, population is projected to peak this century (UN: ~10.3B in 2080s; IHME: ~9.7B by 2064) and then *decline*, so the total number of mouths to feed plateaus. Second, the development pattern matters: East Asian development was overwhelmingly pork and chicken (beef is only 8% of China's meat), not American-level beef. If developing countries follow the East Asian pattern rather than the American one, the land pressure is manageable.

  But the optimistic scenario — releasing 1–2 billion hectares back to forest and habitat — *requires* food technology reaching price parity. Cultivated meat fell from $300,000/kg in 2013 to ~$10/kg in 2025, but price parity ($2–5/kg) is not yet achieved. Precision fermentation for dairy proteins is already commercial. If these technologies scale, the combination of fewer people, higher yields, and protein produced in bioreactors rather than on pasture could free an area larger than the United States for ecosystem restoration. If they don't, agricultural land is the boundary where growth and sustainability most genuinely conflict. (New England's reforestation — 30% forest in 1850, 80% today — demonstrates that post-agricultural rewilding works, but it required agricultural intensification to make it possible.)
- **Materials**: circular economy where nearly everything is recycled, with virgin extraction limited to replacing losses — not feeding linear throughput
- **Welfare growth**: measured in health, longevity, education, digital abundance, and creative output rather than in tonnes of stuff consumed
- **Ecology**: restored forests, recovering biodiversity, and stabilized nutrient cycles. But nitrogen deserves honest treatment. At 3.4× the safe limit (150 vs 44 Mt N/yr), nitrogen fixation is currently *further* beyond its boundary than climate (1.2×). Precision agriculture alone — reducing application 20–40% — only gets to ~2.4×. That's insufficient. Closing the gap requires a *stack* of interventions: eliminating combustion NOx via the energy transition (−15 Mt), engineering cereal crops to fix their own nitrogen the way legumes do (the single biggest lever at −30 Mt; active research by Pivot Bio, Cambridge ENSA, and Gates Foundation CSIA), reducing feed-grain demand through cultivated meat (−15 Mt), widespread nitrification inhibitors (−15 Mt), and deploying engineered denitrifying organisms in constructed wetlands and buffer zones to intercept runoff before it reaches waterways (−10 Mt). The full stack can plausibly reach the boundary (~40–50 Mt), but it requires bioengineering breakthroughs — particularly nitrogen-fixing cereals — that are in active development but not yet deployed. Nitrogen is more regional than climate (dead zones, not global atmosphere), more reversible (ecosystems recover in decades once runoff stops), and more amenable to technology — but "more amenable" still means a multi-decade, multi-technology transition, not a quick fix. Cheap, abundant energy is again the enabler: it powers precision agriculture, controlled-environment farming with ~95% nitrogen efficiency, and cultivated meat production.

This is not utopian fantasy — every component is on an observable S-curve or has demonstrated feasibility. But assembly at global scale within 30–50 years requires everything to go right simultaneously: continued exponential solar deployment, food technology scaling, bioengineering breakthroughs in nitrogen-fixing cereals, circular economy adoption, *and* the political will to retire incumbent systems. The historical base rate for "everything goes right simultaneously" is not encouraging.

**The Jevons paradox is the most serious threat to this vision.** Historically, efficiency gains lead to *more* consumption, not less. Cheap energy could increase material extraction — more mining, more desalination, more of everything. The optimistic case requires that welfare growth shifts decisively to weightless goods. This *is* happening (the services share of GDP has risen from 58% to 82% in the US since 1950), but whether it can accelerate fast enough is an open question.

**The honest verdict:** Growth and ecological sustainability are not *mathematically* incompatible — the technology pathways to universal high welfare within planetary boundaries exist in principle. The boundary-specific problems vary enormously in tractability: carbon requires an economy-wide energy transition (underway but incomplete); nitrogen/phosphorus require an agricultural technology transition (proven solutions exist, deployment is the bottleneck); biodiversity loss requires land release (which population peak and food technology enable). The aggregate "material footprint" metric — which treats burned coal and quarried gravel as equivalent — overstates the constraint on a post-transition economy. But the transition itself requires a transformation in the *composition* of growth (from stuff to services), the *energy system* (from fossil to renewable), and the *food system* (from land-intensive to precision) that is unprecedented in speed and scope. The papers are wrong that this is impossible. They may be right that it is unlikely under current institutional arrangements — and that is a serious claim that deserves more than dismissal.

---

## Building Prosperity, Not Just Sending Checks

The papers frame poverty as a stock problem: X billion people are below the line, the gap is $Y trillion, redistribute it. But poverty is a *flow* problem. Even if you transferred $3.1 trillion to lift every person above $6.85/day, you would need to do it again next year, and the year after — forever — unless those economies develop the productive capacity to sustain rising welfare independently. The question for durable prosperity is: what actually transforms a $4,000/capita economy into a $15,000 one?

### Aid is the emergency room, not the cure

The scale of resource flows to developing countries reveals the real story:

| Flow | ~$B/yr | Character |
|---|---|---|
| Foreign Direct Investment (FDI) | 870 | Factories, telecom, retail — brings capital + technology + management |
| Remittances | 656 | Workers abroad → families directly, zero bureaucratic overhead |
| Portfolio investment | 300 | Stocks, bonds in emerging markets |
| Official Development Assistance (ODA) | 224 | Government-to-government aid |
| South-South investment (China, etc.) | 150 | Belt and Road, development loans |
| Private philanthropy (international) | 75 | Gates Foundation, charities, NGOs |

**ODA is ~10% of total resource flows to developing countries.** FDI is 4× ODA. Remittances are 3×. The growth-relevant flows dwarf the aid flows.

The academic evidence (Banerjee, Duflo, Easterly, Deaton, Moyo) converges on a nuanced consensus: aid *is* effective for specific interventions (vaccines, bed nets, famine relief, primary education) but has *not* generated sustained economic growth at the country level. No country has grown its way out of poverty via aid alone. Every success story — Korea, China, Vietnam, Bangladesh, Botswana, Chile — relied on FDI, exports, domestic savings, and institutional reform. (To be clear: no serious redistribution advocate proposes aid alone. The real proposal is transfers *plus* public investment *plus* structural transformation — a combination that looks more like what successful developers actually did. The question is whether external funding can catalyze that combination or whether it must be primarily domestically driven.)

Most aid is not designed to generate growth, and this is not a failure — PEPFAR is designed to save HIV patients, not grow GDP, and it succeeds at what it is designed to do. But conflating humanitarian aid with development strategy leads to confused policy on both sides. The clean narrative ("aid doesn't work") is wrong for emergencies; the clean narrative ("just redistribute more") is wrong for growth.

### The 2025 aid cuts: a tragic natural experiment

In early 2025, the US effectively dismantled USAID (~10,000 staff, 60–80% of bilateral programs frozen), and the UK cut ODA from 0.5% to 0.3% of GNI. By December 2025, the Trump administration began replacing multilateral aid with bilateral health deals — 17 African countries signed as of March 2026.

The humanitarian impact has been **severe and immediate**: PEPFAR disruptions affecting 20M+ people on antiretrovirals, WFP food shipments delayed in Ethiopia/Somalia/Sudan, UNFPA family planning funding cut entirely. These are the programs where aid clearly saves lives, and the cuts cause measurable suffering.

The growth impact is expected to be **small** based on the aid-effectiveness literature, though it is too early (~15 months) for definitive empirical confirmation. Aid was 3–5% of GDP for the median SSA country; FDI was 2–3%, remittances 3–4%, domestic revenue 15–20%. The countries that *were* growing fast (Rwanda, Bangladesh, Vietnam) were not primarily aid-dependent. The countries most hurt — Somalia, South Sudan, DRC — were fragile states where aid was substituting for non-functioning governments, not driving growth trajectories.

The tragedy is that the cuts hit *both* categories indiscriminately: PEPFAR (humanitarian, saves lives), Power Africa (investment, builds growth), and MCC compacts (the gold standard of growth-oriented aid) all frozen together. This is the sovereignty problem from our executive summary made concrete: international aid has no institutional guarantee, and one political pivot in a major donor can halve it overnight.

**Private philanthropy** (~$75B/yr internationally) is more politically stable — Gates Foundation operations continued through the USAID shutdown — but cannot replace $224B in ODA, particularly for large-scale humanitarian emergencies. And the elephant in the room remains **remittances** ($656B/yr): 3× all government ODA, going directly to families with zero bureaucratic overhead, completely insulated from donor politics. In many countries, remittances already dwarf aid: Philippines ($37B remittances vs $1.5B ODA), India ($125B), Kenya ($4.1B vs $3.2B).

### The development recipe is clear — and it isn't about aid

![Divergent development paths](charts/60_divergent_paths.png)
*East Asia pulled away from all other regions on income, savings, investment, trade openness, and education. The fertility panel is the leading indicator: East Asia began the demographic transition 20–30 years before Sub-Saharan Africa.*

The cross-country growth literature (Barro, Rodrik, Acemoglu, Hausmann, Pritchett) identifies a hierarchy. **Necessary conditions** (without these, nothing else works): physical security and basic macroeconomic stability. **Growth accelerators** (fundable from multiple sources): high investment rates, demographic transition, trade integration, infrastructure, and human capital. The factors that distinguish countries that took off from those that didn't:

- **High domestic savings** (30–45% in East Asia vs 10–20% in SSA) — funds investment without foreign debt
- **High investment rates** (25–40% of GDP) — the only statistically significant predictor of growth in our cross-country analysis (r = +0.69, p < 0.001)
- **Early fertility decline** — creating a demographic dividend of falling dependency ratios
- **Trade openness and export manufacturing** — technology transfer and learning-by-doing
- **State capacity** — whether government channels investment into productive capacity or elite consumption

This recipe is not "Asian." Bangladesh (+310% GDP/capita), Rwanda (+191%), Ethiopia (+231%), and Chile (+175%) all followed variations of the same pattern. Argentina (European, resource-rich) grew slower than Rwanda (African, landlocked, post-genocide). The relevant variable is institutional, not cultural or geographic.

### What rich countries can actually do

The most powerful development levers available to rich countries are, paradoxically, not about money:

**High impact (directly drive growth):**
- **Trade access.** Allow developing-country exports into rich-world markets. Bangladesh's $47B/yr garment industry was enabled by EU preferential access. Vietnam's $370B in exports followed trade agreements. This is the single most effective development tool — and costs donor countries almost nothing in aggregate GDP, though the political costs are concentrated in specific industries. Rich-world agricultural subsidies (EU CAP, US Farm Bill) that undercut developing-country farmers do active harm.
- **FDI facilitation.** Development Finance Institutions (US DFC, UK BII, Germany DEG) co-invest with private capital to de-risk pioneer investments. A $50M DFI investment in a solar project can unlock $500M in private follow-on. This is not aid — it is catalytic capital.
- **Remittance cost reduction.** SSA remittance costs average 7.9% — the highest in the world, against a UN target of 3%. Halving them would transfer ~$3–4B/yr more to African families, more than many aid programs, at essentially zero fiscal cost to donor governments.

**Moderate impact (build conditions for growth):**
- **Infrastructure investment** structured as loans, not grants — World Bank/IDA, AfDB, MCC compacts. Africa's infrastructure gap is ~$100–170B/yr; ODA covers ~$15–20B. China's Belt and Road, whatever its terms, has provided more infrastructure to Africa in 20 years than all Western donors combined.
- **Girls' education and family planning** — the highest-return investments in development, driving the demographic transition that unlocks everything else. Returns are real but generational (20–30 years).

**What rich countries should *stop* doing** often matters as much: agricultural subsidies that undercut poor farmers, enabling capital flight and tax havens, arms sales to conflict zones, tied aid (where contractors must be from the donor country), and expensive remittance corridors.

**The hardest truth:** the most important determinant of growth — institutional quality (Acemoglu & Robinson 2012) — is the variable outsiders have the *least* ability to change. Rwanda built institutions internally. So did Botswana. So did Korea. External "governance programs" have a poor track record. The things only developing countries can do — build institutions, maintain peace, invest domestically, complete the demographic transition, choose dense urbanization over sprawl — are the most important things.

### The debt trap: a binding constraint hiding in plain sight

The development literature focuses on investment, trade, and institutions. But for many developing countries, the binding constraint is simpler: debt service consumes the revenue that would fund investment.

![Debt burdens: success vs challenge](charts/67_success_vs_challenge_debt.png)
*Development successes maintained consistently lower debt service (1–2% of GNI) compared to SSA challenges (2–5%) and Latin America (2–5%). The external debt stock panel is even starker: SSA peaked at 130% of GNI in the late 1990s while success countries stayed below 70%.*

The correlation is statistically significant: across 25 countries over 2000–2023, average debt service and GDP growth show r = –0.48 (p = 0.024). China, Vietnam, Bangladesh, and India cluster in the low-debt/high-growth quadrant; SSA and Latin American countries in the high-debt/lower-growth zone.

![Debt service vs revenue](charts/69_debt_service_vs_revenue.png)
*The real constraint is what share of government revenue goes to creditors rather than investment. SSA peaked at 50%+ in the early 1990s, fell to ~5% after HIPC/MDRI debt relief, and is now climbing back toward 15%. Development successes stayed at 5–15% throughout.*

The history tells a story of vicious and virtuous cycles:

- **East Asian successes** had low external debt because high domestic savings (30–45% of GDP) meant less foreign borrowing. Low debt service left revenue available for infrastructure investment. Investment drove growth, which expanded revenue. China's external debt never exceeded 20% of GNI.
- **Latin America's "lost decade"** (1982–1992) was a debt crisis: external debt at 50–80% of GNI, debt service consuming 5–8% of GNI, growth stagnant. The Brady Plan (1989) restructured the debt; growth resumed only after.
- **SSA's debt relief and re-accumulation**: HIPC (1996) and MDRI (2005) wrote off most multilateral debt, dropping SSA external debt from ~100% to ~25% of GNI. This created fiscal space — and growth accelerated. But new borrowing since 2010, increasingly from China and commercial creditors (Eurobonds) on less concessional terms, has rebuilt the debt to ~45% of GNI. Ghana, Zambia, and Ethiopia all defaulted or restructured in 2020–2024.

The composition matters: SSA's new debt is 40–60% private/commercial (vs. mostly concessional multilateral pre-HIPC), with shorter maturities and higher interest rates. Latin America's is dominated by commercial creditors (67–93% private). This makes restructuring harder and rollover risk higher.

**Debt relief may be a bigger lever than aid.** Many SSA countries now pay *more* in debt service than they receive in ODA. Zambia, Ghana, and Kenya each spend 15–20% of government revenue on debt service — revenue that could fund the infrastructure, education, and health investment the development recipe requires. The HIPC/MDRI model demonstrated that debt relief creates fiscal space for investment; the subsequent re-accumulation demonstrates that without the underlying growth drivers (savings, exports, institutions), the debt rebuilds. **Debt is both a cause and a symptom of the low-growth trap: it is a vicious cycle that requires breaking from multiple points simultaneously.**

### The demographic transition is the leading indicator

![Demographic dividend](charts/62_demographic_dividend.png)
*Fertility decline since 1975 predicts GDP growth since 1990 — regardless of region. East Asia began the transition in the 1960s; SSA only in the 1990s. This 20–30 year head start is the single most important divergence driver.*

When fertility falls, dependency ratios improve, women enter the labor force, families invest more per child, and savings rates rise. Bangladesh — a Muslim-majority South Asian country — achieved replacement-rate fertility through female education and family planning programs, all while growing 310%. SSA is now entering this transition (TFR falling from ~6 to ~4), which is the single strongest reason for cautious optimism about the region's next 30 years.

### Transfers can relieve poverty but cannot build economies

![Transfers vs development](charts/46_transfers_vs_development.png)
*Transfers directly address 1–2 of the 7 components needed to reach $15k GDP/capita (human capital, partially demographics). Agricultural productivity, infrastructure, institutional capacity, structural transformation, and domestic savings require building productive economies.*

The evidence on transfers is real but limited:

- **Unconditional cash** (GiveDirectly): excellent immediate relief, $2.60 local multiplier, but modest long-run productivity effects
- **Graduation programs** (BRAC): 38% income gains sustained 7+ years — the best evidence that designed programs can create self-sustaining livelihoods
- **Conditional transfers** (Bolsa Família, Progresa): +0.7 years schooling, +8% next-generation earnings — works through children over 20–30 years

The key distinction is between "aid" structured as *investment* (infrastructure loans, DFI equity, trade capacity, girls' education) and "aid" structured as *consumption* (food aid, cash transfers, emergency health). Both are valuable. Only the first generates growth. The tragedy of indiscriminate aid cuts — like 2025 — is that they destroy both categories simultaneously. And the real proposal from redistribution advocates is transfers *plus* public investment *plus* structural transformation — a combination that looks less like "just sending checks" and more like what successful developers actually did, funded partly from external sources.

---

## What the Evidence Actually Shows

### Three claims well-supported by data:

**1. Growth alone is not enough.** Undirected growth with current distributional patterns cannot eliminate poverty at meaningful thresholds fast enough. Redistribution is 100–2,000× more efficient per dollar at reaching the poor. SSA is being left behind. The papers are right about this.

**2. Historical command economies failed, and no alternative has yet matched market-based development at scale.** The USSR peaked at 41% of US GDP per capita, then declined. China's market reform era (6.8%/yr) was 2.5× faster than the Mao era. But every successful market economy was heavily managed — Japan, Korea, Taiwan, China, and Vietnam all featured industrial policy, directed credit, and managed trade. The question is which *kind* of market economy, not whether to have one. This does not foreclose the possibility that as-yet-untested arrangements — democratic planning, provisioning models, hybrid systems — could outperform historical alternatives. It means the evidence base is currently thin.

**3. The ecological constraint is severe and binding.** Current decoupling rates land us at ~3°C. Staying under 2°C requires more than doubling the best performance ever achieved. Beyond carbon, material use, nitrogen, and biodiversity lack clear technological exits. The papers are more right on ecology than on economics.

### Two claims not supported by data:

**4. "Capitalism is mathematically unworkable."** The papers prove that growth *alone*, with *current distribution*, at *current coupling rates* is insufficient. Those are all policy variables, not laws of nature. Market economies with redistribution exist. Decoupling is accelerating. The 175× GDP scenario assumes convergence to American consumption, which no one proposes. The data supports "current policies are inadequate," not "the system is mathematically impossible."

**5. "The current growth model is basically on track."** Our own carbon arithmetic refutes growth triumphalism. 2°C requires decoupling rates not yet demonstrated at scale. 3.14 billion remain below $6.85/day. Six planetary boundaries are breached. Success is concentrated in East Asia. Growth has created enormous surplus and capacity, but the institutions for directing it — toward redistribution, decarbonization, and ecological restraint — are inadequate.

### The bottom line

The world has enough productive capacity to end extreme poverty. It has enough historical evidence to know what economic institutions promote development. It has enough ecological data to know the current trajectory is unsustainable across multiple dimensions.

**Growth shrank the poverty gap from 18% to 1.6% of world GDP at meaningful thresholds. The remaining barriers are political-economic and ecological — but those may not be separable from the system itself.**

As the Building Prosperity section demonstrates, poverty is a *flow problem*: the papers' redistribution arithmetic treats it as a reservoir to be filled, but the development evidence says it is a leak to be fixed. Both the filling and the fixing are needed, but confusing one for the other leads to policy failure. The growth drivers are not mysterious, the most powerful rich-country levers cost almost nothing in fiscal terms, and the most important determinants — institutional quality, domestic savings, security — are things only developing countries can do for themselves.

Capitalism is a powerful energy source that has generated unprecedented material progress and made redistribution cheaper than at any point in history. The question is whether we can build the containment structures — redistribution, climate policy, ecological governance, development strategy — fast enough. The papers make a compelling case that the containment is currently insufficient. They do not make a compelling case that the reactor should be shut down.

But we should be honest about the limits of that metaphor. The reactor predictably resists containment. Market economies structurally tend to concentrate gains, lock in luxury consumption at ecologically indefensible levels, and externalize ecological costs. Rich-world material throughput is 3–4× the sustainable limit, and no market economy has yet demonstrated a path to reducing it. That political failure is not separate from the system — it is a feature of it. Nordic social democracy shows that better containment is possible within capitalism. It does not prove that capitalism globally tends toward that outcome.

Two claims should be distinguished. First: **the evidence rejects mathematical impossibility.** The technology pathways exist, the fiscal arithmetic works at lower thresholds, and historical development successes demonstrate that market economies with strong states can deliver broad-based growth. The papers do not prove the system cannot work. Second: **the evidence does not resolve whether capitalism will reliably deliver the containment it needs** — redistribution, ecological restraint, rich-world throughput reduction. The papers' strongest argument is that it structurally won't, and the ecological crisis requires the rich world to consume *less*, not just *differently*. Our data illuminates both sides of that question without settling it.

---

## Limitations and What This Doesn't Settle

- **The systemic political economy critique.** We show redistribution plus managed growth *could* work. But if capitalist political economies structurally tend to concentrate gains, resist redistribution, and externalize ecological costs, then "political failure" is not an external caveat — it is part of the indictment. Nordic social democracy proves better outcomes are possible; it does not prove the global system tends toward them. This is arguably the central unresolved question, and our data does not settle it.

- **The provisioning argument.** Paper 1's strongest version is not "175× GDP." It is that decent lives require specific material throughputs with real ecological costs, and the world already produces enough to meet those needs through reallocation rather than further growth. Our $15k life-expectancy proxy is a useful heuristic, but it is not a direct rebuttal to provisioning frameworks that measure material sufficiency rather than GDP correlation.

- **The exploitation critique.** Our emissions-offshoring analysis is too narrow. It addresses carbon geography but not terms of trade, debt discipline, intellectual property regimes, supply chain ownership, currency hierarchy, or the structural orientation of Global South production toward exports rather than domestic provisioning.

- **East Asian replicability.** Asian development success depended partly on Cold War geopolitics, cheap fossil energy, export absorption by rich-country markets, and ecological slack that may not exist for today's poorest countries. The development recipe is clear in retrospect; whether it can be followed under 2020s constraints is genuinely uncertain.

- **Measurement as politics.** As Paper 2 demonstrates, the poverty line you choose determines whether you see triumph or stagnation — both are accurate descriptions of the same underlying reality. Our analysis uses multiple thresholds, but every number still reflects choices about what counts as poverty, how to convert across currencies, and which welfare indicators to privilege. Numbers like "0.06% of GDP" and "3.4× the safe boundary" suggest precision the underlying methods don't fully support.

- **The welfare question.** Whether growth has "worked" depends on how much you weight improvements for the poorest versus total output. Our [welfare-weighted analysis](README_v2_archive.md) (Charts 52–57) shows country rankings shift dramatically with this value judgment — the US leads on mean income; Norway leads on every pro-poor measure.

- **What we don't fully answer.** Historically observed growth can reduce low-end deprivation, but it does so through a system that channels gains upward, locks in luxury consumption, and externalizes ecological costs. The boundaries that matter most now — land use, biodiversity, nitrogen — are the ones with the weakest technological escape routes. This is the strongest version of the papers' argument, and our data does not decisively refute it.

---

## Appendix

### Data Sources

| Source | Key Variables |
|---|---|
| [World Bank WDI](https://data.worldbank.org/) | GDP, population, life expectancy, mortality, Gini, education, investment |
| [World Bank PIP](https://pip.worldbank.org/) | Headcount ratios and poverty gaps at $2.15, $3.65, $6.85, $10.0/day |
| [Maddison Project](https://www.rug.nl/ggdc/historicaldevelopment/maddison/) | Historical GDP per capita (1–2022) |
| [Our World in Data](https://github.com/owid/co2-data) | CO₂ emissions (production + consumption), decoupling metrics |
| [Our World in Data](https://github.com/owid/energy-data) | Solar/wind/fossil generation, energy mix, renewable shares |
| [Our World in Data](https://ourworldindata.org/) | Material footprint, LPI, Red List, nitrogen, phosphorus, water stress |
| [OECD Revenue Statistics](https://www.oecd.org/tax/tax-policy/revenue-statistics.htm) | Total government tax revenue (% GDP) |
| [IEA](https://www.iea.org/) | Critical minerals demand projections |
| [USGS](https://pubs.usgs.gov/) | Mineral production volumes |

### Analysis Pipeline

Fourteen scripts in `analysis/` produce 71 charts. Run sequentially after `download_data.py`:

| Script | Topic | Charts |
|---|---|---|
| `run_analysis.py` | Core poverty & growth | 01–08 |
| `run_analysis_2.py` | Poverty–growth feedbacks | 09–12 |
| `run_analysis_3.py` | Floor-raising, good-life threshold | 13–16 |
| `run_analysis_4.py` | Market reforms, command economies | 17–18 |
| `run_analysis_5.py` | Decoupling, carbon budget, trade flows | 19–23 |
| `run_analysis_6.py` | ODA, political economy, energy S-curve | 24–27 |
| `run_analysis_7.py` | Non-carbon planetary boundaries | 28–32 |
| `run_analysis_8.py` | Country-level ecological decomposition | 33–36 |
| `run_analysis_9.py` | Transition minerals vs fossil fuels | 37–40 |
| `run_analysis_10.py` | Transfers to self-sufficiency | 41–46 |
| `run_analysis_11.py` | Rich-world quintile incomes | 47–51 |
| `run_analysis_12.py` | Welfare-weighted growth (27 countries) | 52–57 |
| `run_analysis_13.py` | Why some countries develop | 58–65 |
| `run_analysis_14.py` | Debt burdens: success vs challenge | 66–71 |

### Methodology Notes

- **Poverty gaps** use the World Bank PIP world aggregate (WLD) row. The "realistic 3×" multiplier follows the literature's rough estimate that targeting inefficiency, administrative costs, and behavioral responses approximately triple perfect-targeting cost.
- **Decoupling rates** are annualized: $(I_t/I_0)^{1/t} - 1$ where $I$ is CO₂ intensity of GDP.
- **Carbon budget scenarios** solve for annual intensity decline $d$ such that cumulative emissions $\sum_{t=0}^{49} E_0 (1+g)^t (1-d)^t \leq B$.
- **"Good life" threshold** is the GDP/capita above which ≥91% of country-years achieve life expectancy ≥70, converging at ~$15,000 (2011 int'l $).
- **Welfare-weighted growth** uses the Atkinson EDEI at ε = 0, 0.5, 1, 2, and ∞ across 27 countries.

### Full Chart Atlas

The complete chart index is in [README_v2_archive.md](README_v2_archive.md). Charts featured in this document: 01, 02, 14, 21, 22, 24b, 28, 31, 32, 46, 60, 62, 67, 69.

### Tools & Environment

Python 3.14 · pandas, numpy, matplotlib, seaborn, scipy, statsmodels · April 2026
AI assistants: Claude Opus 4.6 (primary analysis and writing), GPT-5.4 (independent critical review)

---

*This project is open-source. All data is from publicly available sources. The full exploratory analysis with all 65 charts and three rounds of independent review is preserved in [README_v2_archive.md](README_v2_archive.md). Reproduce, critique, and extend.*
