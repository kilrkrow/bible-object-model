# Use cases

What this model is for, written down so later rounds build toward it. The first four work now.

## Working now

1. **Ask the graph a set question, with evidence.** "Where did Paul send letters that he is never shown visiting?"
   `b.paul.wrote_to - b.paul.visited` gives Colossae as the one place, plus the people Apphia, Archippus,
   Philemon, Timothy and Titus, each with the verse that names it as a recipient. (Galatia and Achaia drop out
   because Acts 16:6, 18:23 and 18:12 put Paul there.)
2. **Read past the English to the Greek.** "Which love is this?" `b.words("John 21:15")` shows the first "love"
   is agapaō and Peter's "I love thee" is phileō.
3. **Who says what.** "Does Jesus use agapaō or phileō more in John?" `b.speaker_lemma_crosstab(["agapaō",
   "phileō"])` counts each speaker's uses, with the verses.
4. **Ask Claude.** The same questions in plain English through the MCP server, with a raw read-only SQL tool for
   anything the named tools don't cover.

## Recorded, not built: principles as code

Some statements in the text read like rules that can be applied to other text. The first example:

> "He that loveth not knoweth not God; for God is love." (1 John 4:8)

Read as a substitution, "God is love" says that wherever a verse speaks of God, the lemma for love (agapē,
G0026) can stand in its place, and the reverse. Applied to 1 Corinthians 13:4-7 ("Charity suffereth long, and
is kind..."), where "charity" is agapē, it would yield statements about God ("God suffereth long, and is kind").

What building it would need, when the time comes:

- The Greek layer extended to the books involved (1 John, 1 Corinthians), so the substitution works on lemmas,
  not on English words that translate several Greek ones.
- A table of principles: the verse that states it, the two sides (a lemma or an entity), and the direction
  (one way or both).
- Results that are always labelled as derived by a principle, with the principle's verse, and never mixed in with
  what the text states. The same rule the data already keeps for dates.

Other candidates of the same shape, to be checked before they are added: "the Word was God" (John 1:1) and
"God is light" (1 John 1:5).

## Later rounds

- Hebrew: the schema already stores language per lemma; the OT needs a tagged Hebrew text (OpenScriptures Hebrew
  Bible or STEPBible TAHOT) and its own alignment run.
- More books in depth: the entity and relationship curation is done for Acts and the opening lines of Paul's
  letters only.
- Curating the drafted speakers that were left blank (about 70% of the drafted spans), starting with John's
  dialogues, where the speaker alternates between "he" and "Jesus".
