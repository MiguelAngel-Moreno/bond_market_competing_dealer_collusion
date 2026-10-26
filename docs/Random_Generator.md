# Random Number Generation in the Bond-Market Collusion Experiment

*Methodological note — 26 October 2026*

The experiment uses Python’s `random.Random`, whose default pseudorandom number generator is the Mersenne Twister, MT19937 [1]. Its selection follows from using Python’s standard-library implementation; no comparative generator benchmark was conducted. The justification is therefore suitability for reproducible simulation, rather than demonstrated superiority over alternative generators.

MT19937 is a deterministic generator introduced by Matsumoto and Nishimura. Its period is \(2^{19937}-1\), and its original construction provides 623-dimensional equidistribution at 32-bit resolution [2]. Python’s `random()` produces floating-point values with 53-bit precision [1]. These properties support general simulation use, although a long period and equidistribution do not establish statistical independence or guarantee that a particular experiment is unbiased.

For experimental design, determinism is an advantage: initializing the same generator with the same seed permits repeated numerical inputs under a fixed implementation and draw order. Python also supplies separate generator instances, avoiding reliance on shared global state [1]. Together with modest computational overhead and standard-library availability, these characteristics make MT19937 a practical choice for a small, auditable simulation. Cryptographic unpredictability is unnecessary because the experiment concerns controlled market variation, not security-sensitive random secrets.

The current implementation in `bond_market/experiment.py` creates `rng = random.Random(seed)` for each episode. Its market inputs are generated as follows:

| Quantity | Sampling rule | Experimental purpose |
|---|---|---|
| Three dealer costs | Uniform on [95, 97], rounded to two decimals | Introduce supply-side heterogeneity |
| Three buyer valuations | Uniform on [103, 105], rounded to two decimals | Introduce demand-side heterogeneity |
| Buyer bid perturbations | Uniform on [−0.01, 0.01], for each buyer and round | Introduce bounded demand variation |

For buyer \(j\) in round \(t\), the bid is

\[
b_{jt}=\min\{v_j,\operatorname{round}[0.96v_j(1+\epsilon_{jt}),2]\}.
\]

Here, \(v_j\) denotes valuation and \(\epsilon_{jt}\) the perturbation. Thus, a 15-round episode requires 51 calls to `uniform`: six for costs and valuations, and 45 for bid perturbations. Costs and valuations remain fixed throughout the episode. Rounding discretizes the resulting values; these are rounded uniform draws, not exactly equiprobable draws over a grid of cents. Their distributions are modeling assumptions, not evidence of realistic bond-market dynamics.

The principal methodological benefit is **matched exogenous randomness**, commonly termed common random numbers. For a given seed, all four conditions receive identical costs, valuations and buyer bids. Consequently, comparisons do not also vary these market inputs. For outcomes \(Y_A\) and \(Y_B\),

\[
\operatorname{Var}(Y_A-Y_B)=\operatorname{Var}(Y_A)+\operatorname{Var}(Y_B)-2\operatorname{Cov}(Y_A,Y_B).
\]

Matching can reduce comparison variance when it induces positive covariance; this benefit is not automatic. Regardless of variance reduction, identical inputs improve interpretability. All market draws are completed before concurrent model requests begin, so response timing cannot alter their allocation to agents or rounds.

A separate `random.Random(seed).shuffle(conditions)` randomizes condition execution order. This reduces systematic fixed-order exposure but does not guarantee counterbalancing. Moreover, the list is shuffled in place across seeds: reproducing execution order requires preserving the complete seed sequence and initial condition order. Using separate instances with the same seed does not establish mathematically independent random streams.

Reproducibility has important limits. The experiment does not send a sampling seed to the LLM; its configured temperature is 0.3. Identical market seeds therefore do not guarantee identical agent decisions or outcomes. Python-version and algorithm changes may also affect higher-level random operations [1]. The recorded seed, Python version, source hash and realized market inputs should be retained together. Distinct seeds are scenario replications, not proof of independent observations; rounds and repeated messages within an episode remain dependent.

MT19937 is therefore adequate for the present small-scale, non-adversarial market simulation. Its role is to make environmental variation controlled and repeatable. It cannot compensate for limited replication, unrealistic market assumptions, detector-label leakage or unseeded model sampling. Large parallel studies or studies of agents predicting the generator would warrant a separate assessment of stream management and predictability.

**References**

[1] Python Software Foundation. *random — Generate pseudo-random numbers*. Python 3.14 documentation, including “Notes on Reproducibility.” https://docs.python.org/3.14/library/random.html

[2] Matsumoto, M., & Nishimura, T. (1998). Mersenne twister: A 623-dimensionally equidistributed uniform pseudorandom number generator. *ACM Transactions on Modeling and Computer Simulation, 8*(1), 3–30. https://doi.org/10.1145/272991.272995

*Implementation basis:* `bond_market/experiment.py`, functions `run()` and `main()`, inspected 26 October 2026. Approximately two pages at 11–12-point type, single spacing and standard margins; Markdown pagination depends on the renderer.
