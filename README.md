# GRating Rebalancer

GRating Rebalancer is a Calibre GUI plugin that turns Goodreads rating data
into library-relative scores. It reads each book's Goodreads rating and vote
count from Calibre identifiers, compares the book against the rest of your
library, and writes the result to custom columns you choose.

The plugin is useful when you want ratings that are comparable inside your own
library instead of raw Goodreads averages. A 4.1 with thousands of votes may
mean something different from a 4.1 with very few votes; GRating Rebalancer
uses the full library distribution, vote counts, and optional series correction
to produce more useful local outputs.

## What It Writes

GRating Rebalancer never overwrites the source Goodreads identifiers.

It can write:

- An Output column containing the raw library percentile from `0.0` to `100.0`.
- An optional Rating column containing a display-shaped value, such as a
  percentile, decimal, custom number range, or Calibre star rating.

The Output column is the stable raw result. Distribution settings only affect
the optional Rating column.

## Requirements

- Calibre with support for third-party GUI plugins.
- Books with Goodreads data stored in Calibre identifiers:
  - `grrating` for the Goodreads average rating.
  - `grvotes` for the Goodreads vote count.
- At least one compatible Calibre custom column for the Output value.

For best results, the plugin should be run on a library with enough rated books
to form a meaningful distribution.

## Install

1. Download the plugin zip file, such as `GRating Rebalancer.zip`.
2. In Calibre, open `Preferences`.
3. Choose `Plugins`.
4. Select `Load plugin from file`.
5. Choose the downloaded zip file.
6. Restart Calibre if prompted.

After installation, the toolbar action is labeled `GRating RB`.

## Set Up Columns

Create the columns you want before configuring the plugin.

Recommended setup:

- Output: a numeric custom column for the raw `0.0-100.0` percentile.
- Rating: optional. Use this if you also want a shaped value, custom range, or
  star rating written to a second field.

The plugin filters the dropdowns to compatible destination columns. It does not
offer `grrating` or `grvotes` as write targets.

## Configure

Open `GRating RB` customization from Calibre's plugin preferences or plugin
menu.

Main options:

- `Output`: the required custom column for raw percentiles.
- `Rating type`: how the optional Rating value should be formatted.
- `Rating`: optional destination for the shaped Rating value.
- `Mapping scope`: choose whether locked maps are global or separate per
  Calibre library.
- `Locked map`: lock or rebuild the rating-to-percentile map for consistent
  future runs.

Series options:

- `Series correction`: enable or disable series-position penalties.
- `Correction strength`: choose how strongly learned series penalties apply.
- `Rerank after series penalties`: when enabled, the optional Rating field is
  reranked after series penalties. When disabled, direct penalty values are
  written.

Distribution options:

- `Uniform`: keeps values close to their calculated percentile.
- `Bell curve`: compresses values toward a configurable peak.
- `Positive skew`: pushes more values toward the higher end.
- `J-Curve`: creates a more selective, top-heavy scale.

## Run

1. Select one or more books in Calibre.
2. Click `GRating RB`.
3. Review any confirmation or warning dialogs.
4. Let the plugin scan the library, calculate scores, and write selected
   outputs.

The plugin uses the selected books as the write target, but it scans the wider
library to build the percentile distribution.

## Locked Maps

By default, GRating Rebalancer can recalculate the rating-to-percentile map each
run. Locking a map preserves the current rating curve so later runs stay
consistent even as your library changes.

Use a locked map when you want stable results over time. Rebuild the map when
your library has changed enough that you want a new baseline.

## Notes

- Percentile `100.0` means the book is at the top of your library's Goodreads
  rating distribution.
- Star output treats percentile `0.0` as unrated.
- Books without usable Goodreads rating or vote data are skipped.
- The plugin writes only to the fields you configure.
