# Hand check: drafted speakers

Jesus's words come from a red-letter KJV, and 33 speeches have hand-checked boundaries (`curation/speeches.csv`).
Everything else in Acts and John that is direct speech after an intro like *Peter said unto them,* is drafted by a
pattern pass in `build/layers.py`. It names the speaker only when the name before the speech verb is unambiguous;
otherwise it leaves the speaker blank with a note (pronoun, unnamed, ambiguous, or left unresolved on purpose).
Drawn with `python tests/samples.py speakers`.

**Result**

- Named speakers: 23 of 24 correct across both samples.
- Speech boundaries: 17 of 20 right in the random sample, 19 of 20 in the named sample.
- About 70% of drafted spans (212 of 293) have no speaker, on purpose: a blank is safer than a guess, and these are the ones to curate next.

## Sample A: 20 random drafted spans (seed 20261125)

| # | Verse | Speaker | Words | Verdict |
|---|---|---|---|---|
| 1 | Acts.10.19 | peter | Behold, three men seek thee. | Wrong speaker: the Spirit speaks; Peter is only named in the 'While Peter thought' clause.; span right |
| 2 | John.11.34 | (blank: pronoun) | Lord, come and see. | blank, which is right (no name before the verb); span right |
| 3 | John.21.7 | (blank: unnamed: disciple whom Jesus loved) | It is the Lord. Now when Simon Peter heard that it was the Lord, he girt his fisher’s coat unto him, (for he w… | blank, which is right (no name before the verb); Span runs on into the narrator ('Now when Simon Peter heard...'). |
| 4 | John.9.38 | (blank: pronoun) | Lord, I believe. | blank, which is right (no name before the verb); span right |
| 5 | Acts.9.17 | (blank: unnamed: and putting his hands on him) | Brother Saul, the Lord, even Jesus, that appeared unto thee in the way as thou camest, hath sent me, that thou… | blank, which is right (no name before the verb); span right |
| 6 | Acts.12.22 | (blank: unnamed: And the people gave a shout) | It is the voice of a god, and not of a man. | blank, which is right (no name before the verb); span right |
| 7 | John.7.52 | (blank: pronoun) | Art thou also of Galilee? Search, and look: for out of Galilee ariseth no prophet. | blank, which is right (no name before the verb); span right |
| 8 | John.19.24 | (blank: unnamed: the scripture might be fulfilled, which) | They parted my raiment among them, and for my vesture they did cast lots. These things therefore the soldiers … | blank, which is right (no name before the verb); Span runs on into the narrator ('These things therefore the soldiers did.'). |
| 9 | Acts.27.10 | (blank: unnamed: And) | Sirs, I perceive that this voyage will be with hurt and much damage, not only of the lading and ship, but also… | blank, which is right (no name before the verb); span right |
| 10 | John.4.49 | (blank: unnamed: The nobleman) | Sir, come down ere my child die. | blank, which is right (no name before the verb); span right |
| 11 | Acts.21.37 | (blank: unnamed: Who) | Canst thou speak Greek? | blank, which is right (no name before the verb); span right |
| 12 | John.10.33 | jews | For a good work we stone thee not; but for blasphemy; and because that thou, being a man, makest thyself God. | speaker right; span right |
| 13 | Acts.14.1 | (blank: unnamed: into the synagogue of the Jews, and so) | that a great multitude both of the Jews and also of the Greeks believed. | blank, which is right (no name before the verb); Not speech: 'so spake, that a great multitude... believed' is a result clause. |
| 14 | John.11.31 | (blank: unnamed: rose up hastily and went out, followed her) | She goeth unto the grave to weep there. | blank, which is right (no name before the verb); span right |
| 15 | Acts.13.10 | (blank: unnamed: And) | O full of all subtilty and all mischief, thou child of the devil, thou enemy of all righteousness, wilt thou n… | blank, which is right (no name before the verb); span right |
| 16 | Acts.10.4 | (blank: pronoun) | What is it, Lord? | blank, which is right (no name before the verb); span right |
| 17 | John.1.46 | nathanael | Can there any good thing come out of Nazareth? | speaker right; span right |
| 18 | John.9.8 | (blank: pronoun) | Is not this he that sat and begged? | blank, which is right (no name before the verb); span right |
| 19 | Acts.26.29 | paul | I would to God, that not only thou, but also all that hear me this day, were both almost, and altogether such … | speaker right; span right |
| 20 | Acts.17.19 | (blank: unnamed: they took him, and brought him unto Areopagus) | May we know what this new doctrine, whereof thou speakest, is? | blank, which is right (no name before the verb); span right |

## Sample B: 20 random drafted spans that name a speaker (seed 1125)

| # | Verse | Speaker | Words | Verdict |
|---|---|---|---|---|
| 1 | Acts.24.25 | felix | Go thy way for this time; when I have a convenient season, I will call for thee. | speaker right; span right |
| 2 | John.1.45 | philip-the-apostle | We have found him, of whom Moses in the law, and the prophets, did write, Jesus of Nazareth, the son of Joseph… | speaker right; span right |
| 3 | John.18.31 | jews | It is not lawful for us to put any man to death: | speaker right; span right |
| 4 | John.3.27 | john-the-baptist | A man can receive nothing, except it be given him from heaven. | speaker right; span right |
| 5 | Acts.2.38 | peter | Repent, and be baptized every one of you in the name of Jesus Christ for the remission of sins, and ye shall r… | speaker right; span right |
| 6 | John.13.9 | peter | Lord, not my feet only, but also my hands and my head. | speaker right; span right |
| 7 | Acts.27.33 | paul | This day is the fourteenth day that ye have tarried and continued fasting, having taken nothing. | speaker right; span right |
| 8 | Acts.22.28 | paul | But I was free born. | speaker right; span right |
| 9 | John.19.12 | jews | If thou let this man go, thou art not Caesar’s friend: whosoever maketh himself a king speaketh against Caesar… | speaker right; span right |
| 10 | John.7.11 | jews | Where is he? | speaker right; span right |
| 11 | John.1.29 | john-the-baptist | Behold the Lamb of God, which taketh away the sin of the world. | speaker right; span right |
| 12 | Acts.10.14 | peter | Not so, Lord; for I have never eaten any thing that is common or unclean. | speaker right; span right |
| 13 | Acts.25.12 | festus | Hast thou appealed unto Caesar? unto Caesar shalt thou go. | speaker right; span right |
| 14 | John.14.8 | philip-the-apostle | Lord, shew us the Father, and it sufficeth us. | speaker right; span right |
| 15 | John.1.32 | john-the-baptist | I saw the Spirit descending from heaven like a dove, and it abode upon him. | speaker right; span right |
| 16 | John.1.15 | john-the-baptist | This was he of whom I | speaker right; Speaker right; span stops at a nested 'spake,' and cuts the quotation short. |
| 17 | John.3.4 | nicodemus | How can a man be born when he is old? can he enter the second time into his mother’s womb, and be born? | speaker right; span right |
| 18 | Acts.21.13 | paul | What mean ye to weep and to break mine heart? for I am ready not to be bound only, but also to die at Jerusale… | speaker right; span right |
| 19 | John.1.46 | philip-the-apostle | Come and see. | speaker right; span right |
| 20 | Acts.9.34 | peter | Aeneas, Jesus Christ maketh thee whole: arise, and make thy bed. | speaker right; span right |
