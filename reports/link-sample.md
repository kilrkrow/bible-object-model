# Gate 5: random sample of 20 links, checked by hand

Drawn by `tests/link_sample.py` with seed 20261124: 8 name mentions, 6 travel stops, 6 family links. Each was read against its verse. The test fails if the sample changes and this file is not redone.

| # | Kind | Link | Verse | Verdict | Why |
|---|---|---|---|---|---|
| 1 | mention | 'Gentiles' in Acts.15.23 is Gentiles (gentiles) | Acts.15.23 | correct | Gentiles as a people group: the council's letter is to Gentile believers in Antioch, Syria and Cilicia. |
| 2 | mention | 'Abraham' in Acts.7.32 is Abraham (abraham) | Acts.7.32 | correct | The patriarch Abraham, in 'the God of Abraham, Isaac and Jacob'. |
| 3 | mention | 'Asia' in Acts.27.2 is Asia (asia) | Acts.27.2 | correct | The Roman province of Asia (western Turkey), whose coast the ship meant to follow. |
| 4 | mention | 'Ephesian' in Acts.21.29 is Ephesians (ephesians) | Acts.21.29 | correct | Trophimus 'an Ephesian': a man of Ephesus, so the Ephesians group, linked to Ephesus. |
| 5 | mention | 'Samaria' in Acts.8.1 is Samaria (samaria) | Acts.8.1 | correct | Samaria the region, where the church scattered. |
| 6 | mention | 'Paul' in Acts.16.17 is Paul (Saul) (paul) | Acts.16.17 | correct | Paul, followed by the slave girl at Philippi. |
| 7 | mention | 'Paul' in Acts.21.39 is Paul (Saul) (paul) | Acts.21.39 | correct | Paul, speaking to the captain in Jerusalem. |
| 8 | mention | 'Galilee' in Acts.9.31 is Galilee (galilee) | Acts.9.31 | correct | Galilee the region. Before the fix this word was also wrongly given to Judaea; it is now one place. |
| 9 | itinerary | Paul (Saul) stop 57: Caesarea  ("came unto Caesarea") | Acts.21.8 | correct | Caesarea Maritima, where Philip the evangelist lived: the right Caesarea, not Caesarea Philippi. |
| 10 | itinerary | Paul (Saul) stop 55: Tyre  ("landed at Tyre") | Acts.21.3 | correct | Tyre, where the ship unloaded on the way to Jerusalem. |
| 11 | itinerary | Paul (Saul) stop 32: Apollonia  ("and Apollonia") | Acts.17.1 | correct | Apollonia in Macedonia, passed through between Amphipolis and Thessalonica. |
| 12 | itinerary | Paul (Saul) stop 10: Salamis  ("when they were at Salamis") | Acts.13.5 | correct | Salamis on Cyprus, first stop of the first journey. |
| 13 | itinerary | Paul (Saul) stop 1: Jerusalem  ("bring them bound unto Jerusalem") | Acts.9.2 | correct | Start of the route: Saul sets out from Jerusalem with the high priest's letters (9:1-2). The quote shows the city is Jerusalem. |
| 14 | itinerary | Paul (Saul) stop 8: Antioch (Syria)  ("the church that was at Antioch") | Acts.13.1 | correct | Antioch in Syria, where Barnabas and Saul are listed among the teachers before being sent out. |
| 15 | family | father of Timothy parent of Timothy  ("his father was a Greek") | Acts.16.1 | correct | Timothy's unnamed father, 'a Greek', is kept as an entity of its own so the family link has someone to point to. |
| 16 | family | Jesus descendant of David  ("Of this man’s seed hath God according to his promise raised unto Israel a Saviour") | Acts.13.23 | correct | Jesus descended from David: 'this man' in 13:23 is David, named in 13:22; the link carries that note. |
| 17 | family | Jacob (Israel) parent of Joseph son of Jacob  ("called his father Jacob") | Acts.7.14 | correct | Joseph calls 'his father Jacob': Jacob parent of Joseph. |
| 18 | family | Saul descendant of Benjamin  ("a man of the tribe of Benjamin") | Acts.13.21 | correct | King Saul (not Paul) is of the tribe of Benjamin; recorded as descendant of Benjamin, not as son. |
| 19 | family | Abraham parent of Isaac  ("Abraham begat Isaac") | Acts.7.8 | correct | Abraham begat Isaac: parent of, stated directly. |
| 20 | family | James son of Zebedee sibling of John the apostle  ("James the brother of John") | Acts.12.2 | correct | James son of Zebedee is 'the brother of John'; this is the James Herod killed. |

Result: 20 of 20 correct.

An earlier draw (before the one-name-one-person fix) was also 20 of 20, but the gate 4 tests then found that TIPNR lists several people with the same name at some verses (three Jameses and two Simons in Acts 1:13 and 10:32, Claudius at verses where 'Caesar' is the reigning emperor). Those are now settled one occurrence at a time in `curation/occurrence_choices.csv`, and the build refuses to run if any name is claimed twice.

## Verse texts

- **Acts.15.23** And they wrote letters by them after this manner; The apostles and elders and brethren send greeting unto the brethren which are of the Gentiles in Antioch and Syria and Cilicia:
- **Acts.7.32** Saying, I am the God of thy fathers, the God of Abraham, and the God of Isaac, and the God of Jacob. Then Moses trembled, and durst not behold.
- **Acts.27.2** And entering into a ship of Adramyttium, we launched, meaning to sail by the coasts of Asia; one Aristarchus, a Macedonian of Thessalonica, being with us.
- **Acts.21.29** (For they had seen before with him in the city Trophimus an Ephesian, whom they supposed that Paul had brought into the temple.)
- **Acts.8.1** And Saul was consenting unto his death. And at that time there was a great persecution against the church which was at Jerusalem; and they were all scattered abroad throughout the regions of Judaea and Samaria, except the apostles.
- **Acts.16.17** The same followed Paul and us, and cried, saying, These men are the servants of the most high God, which shew unto us the way of salvation.
- **Acts.21.39** But Paul said, I am a man which am a Jew of Tarsus, a city in Cilicia, a citizen of no mean city: and, I beseech thee, suffer me to speak unto the people.
- **Acts.9.31** Then had the churches rest throughout all Judaea and Galilee and Samaria, and were edified; and walking in the fear of the Lord, and in the comfort of the Holy Ghost, were multiplied.
- **Acts.21.8** And the next day we that were of Paul’s company departed, and came unto Caesarea: and we entered into the house of Philip the evangelist, which was one of the seven; and abode with him.
- **Acts.21.3** Now when we had discovered Cyprus, we left it on the left hand, and sailed into Syria, and landed at Tyre: for there the ship was to unlade her burden.
- **Acts.17.1** Now when they had passed through Amphipolis and Apollonia, they came to Thessalonica, where was a synagogue of the Jews:
- **Acts.13.5** And when they were at Salamis, they preached the word of God in the synagogues of the Jews: and they had also John to their minister.
- **Acts.9.2** And desired of him letters to Damascus to the synagogues, that if he found any of this way, whether they were men or women, he might bring them bound unto Jerusalem.
- **Acts.13.1** Now there were in the church that was at Antioch certain prophets and teachers; as Barnabas, and Simeon that was called Niger, and Lucius of Cyrene, and Manaen, which had been brought up with Herod the tetrarch, and Saul.
- **Acts.16.1** Then came he to Derbe and Lystra: and, behold, a certain disciple was there, named Timotheus, the son of a certain woman, which was a Jewess, and believed; but his father was a Greek:
- **Acts.13.23** Of this man’s seed hath God according to his promise raised unto Israel a Saviour, Jesus:
- **Acts.7.14** Then sent Joseph, and called his father Jacob to him, and all his kindred, threescore and fifteen souls.
- **Acts.13.21** And afterward they desired a king: and God gave unto them Saul the son of Cis, a man of the tribe of Benjamin, by the space of forty years.
- **Acts.7.8** And he gave him the covenant of circumcision: and so Abraham begat Isaac, and circumcised him the eighth day; and Isaac begat Jacob; and Jacob begat the twelve patriarchs.
- **Acts.12.2** And he killed James the brother of John with the sword.
