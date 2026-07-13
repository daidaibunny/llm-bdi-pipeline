# Third-Party Notices

GP2PL depends on public research software and benchmark repositories. These
materials are not relicensed by GP2PL.

## Benchmark Sources

| Source | Pinned revision | Local use | License status at audit |
| --- | --- | --- | --- |
| [DillonZChen/moose-dataset](https://github.com/DillonZChen/moose-dataset) | `e00970516154e9042b783a4613a1ed7286c9beee` | MOOSE classical and numeric train/test splits | No repository license file was exposed by GitHub on 2026-07-13. |
| [potassco/pddl-instances](https://github.com/potassco/pddl-instances) | `cf19edf7c53d1540ddbb396c642595e0926ee552` | IPC Blocksworld Tower instances | No repository license file was exposed by GitHub on 2026-07-13. |
| [bonetblai/learner-policies-from-examples](https://github.com/bonetblai/learner-policies-from-examples) | `9991926f7655c4b6c8dc2f0404123639e42056f2` | Blocksworld Clear and On train/test splits | No repository license file was exposed by GitHub on 2026-07-13. |
| [rleap-project/d2l](https://github.com/rleap-project/d2l) | `0620e169c894d79b3c84f435dba1462996f7c270` | Depots instances | GPL-3.0 repository license. |

The first three sources are publicly downloadable but do not declare a license
through GitHub's license endpoint. Their files are consequently fetched from
the pinned upstream repositories for local reproduction and remain outside the
scope of the GP2PL code and data licenses.

## Principal Software Dependencies

| Component | Fixed version or revision | Role |
| --- | --- | --- |
| [MOOSE](https://github.com/DillonZChen/moose) | `ce1e99bc12e9c839c5e8e870aac878fd5d31cf9e` | Singleton-goal generalized-planning evidence provider. |
| [Clingo](https://potassco.org/clingo/) | 5.8.0 | Certified branch-set optimization. |
| [Jason](https://github.com/jason-lang/jason) | 3.1.2 | AgentSpeak(L) execution. |
| [ltlf2dfa](https://github.com/whitemech/ltlf2dfa) | 1.0.2 | LTLf-to-MONA translation. |
| [MONA](https://www.brics.dk/mona/) | 1.4-18 | Deterministic finite automaton construction. |
| [VAL](https://github.com/KCL-Planning/VAL) | `3c7a1f330bdab0ba28a4762bb45c3f06c27fb6d4` | Independent PDDL trace validation. |

Consult each upstream project for its complete copyright and license terms.
