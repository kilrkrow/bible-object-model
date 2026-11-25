# Hand check: KJV-to-Greek word alignment

The alignment links each KJV content word of Acts and John to the Greek word it translates. It is a machine draft
(IBM Model 1 trained on the whole New Testament, with a word-order prior and STEPBible's English glosses as hints),
so it was checked by hand on a random sample. Drawn with `python tests/samples.py alignment` (seed 20261125).

**Result: 39 of 40 correct.** The one miss is a preposition that has no Greek word of its own in this verse's
alignment, a known weak spot (prepositions and particles are often folded into a Greek verb or case ending).

The gold set in `tests/test_layers.py` (19 words, including every *love* in John 21:15-17) passes in full.

| # | Verse | KJV word | Greek | Strong's | Lexicon gloss | Score | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | Acts.10.11 | opened | ἀνεῳγμένον (aneōgmenon) | G0455 | to open | 1.0 | correct |
| 2 | Acts.9.40 | sat | ἀνεκάθισεν (anekathisen) | G0339 | to sit up | 0.8188 | correct |
| 3 | John.21.24 | true | ἀληθὴς (alēthēs) | G0227 | true | 1.0 | correct |
| 4 | Acts.4.10 | people | λαῷ (laō) | G2992 | a people | 1.0 | correct |
| 5 | Acts.12.21 | made | ἐδημηγόρει (edēmēgorei) | G1215 | to give a speech | 0.4632 | correct |
| 6 | John.7.51 | law | νόμος (nomos) | G3551 | law | 1.0 | correct |
| 7 | John.16.29 | said | Λέγουσιν (Legousin) | G3004 | to say: call | 0.1402 | correct |
| 8 | Acts.23.6 | out | ἔκραξεν (ekraxen) | G2896 | to cry | 0.4753 | correct |
| 9 | John.5.10 | therefore | οὖν (oun) | G3767 | therefore/then | 1.0 | correct |
| 10 | Acts.2.12 | amazed | ἐξίσταντο (existanto) | G1839 | to amaze | 0.8385 | correct |
| 11 | Acts.8.27 | man | ἀνὴρ (anēr) | G0435 | man: husband | 0.7135 | correct |
| 12 | John.21.24 | disciple | μαθητὴς (mathētēs) | G3101 | disciple | 1.0 | correct |
| 13 | Acts.13.47 | Gentiles | ἐθνῶν (ethnōn) | G1484 | Gentiles | 1.0 | correct |
| 14 | Acts.9.31 | throughout | καθ᾽ (kath᾽) | G2596 | according to | 0.0275 | correct |
| 15 | Acts.13.15 | reading | ἀνάγνωσιν (anagnōsin) | G0320 | reading | 1.0 | correct |
| 16 | Acts.11.13 | surname | ἐπικαλούμενον (epikaloumenon) | G1941 | to call (on)/name | 0.2843 | correct |
| 17 | Acts.7.42 | years | ἔτη (etē) | G2094 | year | 1.0 | correct |
| 18 | Acts.23.22 | man | νεανίαν (neanian) | G3494 | young man | 0.8989 | correct |
| 19 | Acts.16.24 | charge | παραγγελίαν (parangelian) | G3852 | order | 0.2941 | correct |
| 20 | Acts.3.22 | say | λαλήσῃ (lalēsē) | G2980 | to speak | 0.0251 | correct |
| 21 | Acts.7.19 | live | ζῳογονεῖσθαι (zōogoneisthai) | G2225 | to give life | 0.2994 | correct |
| 22 | John.2.24 | all | πάντας (pantas) | G3956 | all | 1.0 | correct |
| 23 | John.1.45 | write | ἔγραψεν (egrapsen) | G1125 | to write | 0.2109 | correct |
| 24 | Acts.3.23 | among | ἐξολεθρευθήσεται (exolethreuthēsetai) | G1842 | to root out | 0.2486 | Wrong. Acts 3:23 'destroyed from among the people': 'among' belongs to ἐκ (ek), not to the verb. |
| 25 | John.13.20 | sent | πέμψαντά (pempsanta) | G3992 | to send | 1.0 | correct |
| 26 | John.13.23 | disciples | μαθητῶν (mathētōn) | G3101 | disciple | 1.0 | correct |
| 27 | Acts.5.6 | carried | ἐξενέγκαντες (exenegkantes) | G1627 | to bring/carry out | 0.19 | correct |
| 28 | John.1.47 | saith | λέγει (legei) | G3004 | to say: call | 0.2203 | correct |
| 29 | Acts.10.38 | devil | διαβόλου (diabolou) | G1228 | devilish/the Devil | 1.0 | correct |
| 30 | John.1.39 | day | ἡμέραν (hēmeran) | G2250 | day | 1.0 | correct |
| 31 | John.20.19 | disciples | μαθηταὶ (mathētai) | G3101 | disciple | 1.0 | correct |
| 32 | John.16.12 | many | πολλὰ (polla) | G4183 | much | 1.0 | correct |
| 33 | John.3.33 | set | ἐσφράγισεν (esphragisen) | G4972 | to seal | 0.0762 | correct |
| 34 | Acts.19.4 | saying | λέγων (legōn) | G3004 | to say: call | 0.5924 | correct |
| 35 | John.20.3 | forth | Ἐξῆλθεν (Exēlthen) | G1831 | to go out | 0.2023 | correct |
| 36 | Acts.21.14 | done | γενέσθω (genesthō) | G1096 | to be | 0.3309 | correct |
| 37 | Acts.28.15 | brethren | ἀδελφοὶ (adelphoi) | G0080 | brother | 0.6359 | correct |
| 38 | John.18.36 | world | κόσμου (kosmou) | G2889 | world | 1.0 | correct |
| 39 | John.20.13 | saith | λέγει (legei) | G3004 | to say: call | 0.2203 | correct |
| 40 | Acts.25.26 | examination | ἀνακρίσεως (anakriseōs) | G0351 | investigation | 0.6605 | correct |
