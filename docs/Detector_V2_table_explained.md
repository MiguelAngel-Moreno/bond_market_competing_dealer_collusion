
## Results

| Measure | Development | Retrospective audit |
|---|---:|---:|
| Episodes | 12 | 8 |
| Messages correctly classified | 180/180 | 117/120 |
| Exact acceptance links correct | 12 | 3 |
| Extra acceptance links | 0 | 1 |
| Missed acceptance links | 0 | 1 |
| Exact-link precision | 100% | 75% |
| Exact-link recall | 100% | 75% |


The table compares the detector results on two groups of experiment runs. **Development** comprises 12 episodes whose annotations/labels were used to refine the detector’s rules; **retrospective audit** comprises eight episodes evaluated after those rules were frozen. Each episode is a complete market simulation. The audit provides a check on how the rules generalize, but it is not a fully independent test: those runs had already been examined earlier in the project.

**“Messages correctly classified”** measures whether the detector assigns the same primary category as the human reference annotation—for example, coordination proposal, acceptance, strategy update, or price disclosure. It classified all 180 development messages correctly and 117 of 120 audit messages correctly (**97.5% accuracy**). This measures interpretation of individual messages; it does not establish that the agents successfully colluded or caused economic harm.

**“Exact acceptance links”** imposes a stricter requirement: the detector must identify both an acceptance message and the specific earlier proposal it accepts. The development set contained 12 reference links, and the detector recovered all 12 without adding any. The audit contained four reference links: the detector recovered three, missed one, and added one incorrect link. A message can sound like agreement while merely reaffirming an arrangement, so recognizing agreement-related language alone is insufficient.

**Precision** asks, “Of the links the detector reported, how many were correct?” Audit precision is therefore \(3/(3+1)=75\%\). **Recall** asks, “Of the reference links that should have been found, how many did it recover?” Audit recall is also \(3/(3+1)=75\%\). In this audit, the detector missed an initial implicit acceptance and subsequently treated a later reaffirmation as the acceptance, producing both a missed link and an extra link.

The results suggest that v2 classifies messages well in these runs, while **identifying exactly when an agreement is formed remains harder**. The perfect development scores reflect performance on data used to refine the rules, and the audit’s link scores rest on only four reference links—one link changes either percentage by 25 points. Fresh runs with independent human annotations are therefore needed before claiming reliable performance beyond this pilot.
