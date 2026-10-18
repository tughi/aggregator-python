# Similar entries

Entries covering the same story are found by comparing their words: two entries are similar when they share words that
are rare among the other entries, like names and products. The code lives in
[`application/aggregator/similarity.py`](../application/aggregator/similarity.py).

## Turning an entry into weighted words

1. **Text**: the entry's title, counted twice because it describes the story best, followed by its summary as plain text
   (cut to 1500 characters).
2. **Words**: the text is lowercased and split into words of at least two characters.
3. **Weights** (TF-IDF), computed over all entries published around the same time:
   - **IDF**: the fewer entries contain a word, the more it weighs. Words found in only one entry can't match anything,
     and words found in more than 5% of the entries carry no meaning, like "the", so both are ignored.
   - **TF**: a word repeated in the entry weighs more, with diminishing returns (`1 + log(count)`).
   - Each entry's weights are scaled so that long summaries don't score higher just for having more words.

## Comparing two entries

The similarity score (cosine similarity) adds up the products of the weights of the words both entries share. It ranges
from 0, no shared words, to 1, identical words. The same story typically scores 0.4 or more, the same topic around 0.2
to 0.35.

## When entries are compared

When a feed update adds new entries, each is compared with the entries published up to 14 days before or after it. The
matches scoring at least 0.2 are stored in both directions, keeping the best 10 per entry.

Storing both directions means existing entries learn about new ones: when a new entry N matches an existing entry A, N
is added to A's matches too, if it ranks among A's best 10. A's other matches aren't recomputed.

Only new entries are compared. An entry whose title or summary changes later keeps the matches it got when it arrived.
