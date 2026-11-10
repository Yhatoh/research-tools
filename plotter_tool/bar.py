import matplotlib.pyplot as plt
import argparse
import json
import math

CONFIG_HELP = """
fields of the json config file:

  output_file   (required) path of the image to write, the extension picks the
                format (.pdf, .png, ...)
  legendnames   (required) name of each series in the legend, one per file
  files         (required for a single plot, or inside every entry of "plots")
                data files of each series, in the same order as legendnames.
                every file is a list of "category value" lines, the value is
                the number after the last space and the category is everything
                before it, so it can contain spaces. the bars of every series
                are grouped by category
  plots         (optional) list of plots to draw in a grid, every entry is an
                object with its own "files" and optionally "title",
                "categories", "limity", "ticksy", "logy" (falling back to the
                top level value). omit it to draw a single plot from "files"
  categories    (optional) categories to draw, in order, for example
                ["a", "b", "c"]. every category can also be a
                [category, label] pair to write something else under the group
                (default: every category of the files, in the order they first
                appear)
  grid          (optional) [rows, cols] of the grid (default: as square as
                possible). leftover cells are left empty
  gridlines     (optional) draw gray lines behind the bars, at the ticks of the
                y axis (default: true)
  figsize       (optional) [width, height] of the whole image in inches
                (default: 4.5 x 3.5 per cell of the grid)
  colors        (optional) color of each series, matplotlib names, hex or "C0"
                (default: the matplotlib color cycle)
  hatches       (optional) pattern inside the bars of each series: "", "/",
                "\\\\", "x", "o", ".", "-", "+", ... (default: "" for all of
                them)
  filled        (optional) fill the bars or draw only their outline, either one
                bool for every series or one bool per series (default: true)
  barwidth      (optional) fraction of the space of a category taken by its
                group of bars, between 0 and 1 (default: 0.8)
  labelx        (optional) label of the x axis, only drawn on the bottommost
                plots (default: no label)
  labely        (optional) label of the y axis, only drawn on the leftmost
                plots (default: "y")
  limity        (optional) [min, max] of the y axis (default: min 0 and
                matplotlib picks the max, unless the axis is logarithmic)
  ticksy        (optional) positions of the ticks of the y axis, for example
                [0, 10, 20, 30, 40] (default: matplotlib picks them). every
                position can also be a [position, label] pair to write
                something else next to the tick
  logy          (optional) use a log scale in the y axis (default: false)
  title         (optional) title of the plot, or of the whole figure when
                there is a grid (default: no title)

colors, hatches and filled are shared by every plot of the grid, so they all
have the same legend, which is drawn once below the figure.

example of a grid, using every field:

  {
    "output_file": "grid.pdf",
    "legendnames": ["k2octopus", "k2tree"],
    "colors": ["red", "blue"],
    "hatches": ["//", ""],
    "filled": [true, false],
    "barwidth": 0.7,
    "labelx": "dataset",
    "labely": "time",
    "limity": [1, 1000],
    "ticksy": [1, 10, 100, 1000],
    "logy": true,
    "categories": ["0004", "1619", ["2350", "big"]],
    "title": "octopus against tree",
    "grid": [1, 2],
    "figsize": [9, 3.5],
    "plots": [
      {"files": ["data/a1", "data/a2"], "title": "query a"},
      {"files": ["data/b1", "data/b2"], "title": "query b",
       "categories": ["0004", "1619"], "limity": [0, 100], "logy": false,
       "ticksy": [[0, "fast"], [100, "slow"]]}
    ]
  }

the same fields for a single plot, "files" at the top level and no "plots",
"grid" or per plot overrides:

  {
    "output_file": "plot.pdf",
    "legendnames": ["k2octopus", "k2tree"],
    "files": ["data/a1", "data/a2"],
    "colors": ["red", "blue"],
    "hatches": ["//", ""],
    "filled": [true, false],
    "barwidth": 0.7,
    "labelx": "dataset",
    "labely": "time",
    "limity": [1, 1000],
    "ticksy": [1, 10, 100, 1000],
    "logy": true,
    "categories": ["0004", "1619", ["2350", "big"]],
    "title": "octopus against tree",
    "figsize": [4.5, 3.5]
  }
"""

def parse_args():
    parser = argparse.ArgumentParser(description='do a bar plot data',
                                     epilog=CONFIG_HELP,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('config_file', type=str, help='json config file path')
    parser.add_argument('--show', action='store_true', help='do plt.show()')
    return parser.parse_args()

# every tick is either its position or a [position, label] pair, without a
# label the position is written as a plain number
def parse_ticks(ticks):
    positions, labels = [], []
    for tick in ticks:
        position, label = tick if isinstance(tick, list) else (tick, tick)
        positions.append(position)
        labels.append(label if isinstance(label, str) else "%g" % label)
    return positions, labels

# every category is either its name or a [name, label] pair, without a label
# the name is written under the group
def parse_categories(categories):
    names, labels = [], []
    for category in categories:
        name, label = category if isinstance(category, list) else (category, category)
        names.append(str(name))
        labels.append(str(label))
    return names, labels

# "category value" lines, the category is everything before the last space
def parse_files(files):
    series = []
    for file in files:
        fstream = open(file, "r")

        series.append({})
        for line in fstream:
            line = line.strip()
            if line == "":
                continue
            category, value = line.rsplit(" ", 1)
            series[-1][category.strip()] = float(value)
    return series

args = parse_args()
config = json.load(open(args.config_file, "r"))

ofile = config["output_file"]
legendnames = config["legendnames"]
colors = config.get("colors", [])
hatches = config.get("hatches", [])
filled = config.get("filled", True)
barwidth = config.get("barwidth", 0.8)
labelx = config.get("labelx", "")
labely = config.get("labely", "y")
title = config.get("title", "")
gridlines = config.get("gridlines", True)

# a single plot is just a grid of one
plots = config.get("plots", [config])

# a single bool applies to every file
if isinstance(filled, bool):
    filled = [filled] * len(legendnames)

assert colors == [] or len(colors) == len(legendnames), "you have more/less colors than legend names"
assert hatches == [] or len(hatches) == len(legendnames), "you have more/less hatches than legend names"
assert len(filled) == len(legendnames), "you have more/less filled flags than legend names"
assert 0 < barwidth <= 1, "barwidth must be between 0 and 1"

if "grid" in config:
    nrows, ncols = config["grid"]
else:
    ncols = math.ceil(math.sqrt(len(plots)))
    nrows = math.ceil(len(plots) / ncols)
assert nrows * ncols >= len(plots), "the grid is too small for the number of plots"

figsize = config.get("figsize", [4.5 * ncols, 3.5 * nrows])

plt.rcParams['text.usetex'] = True
plt.rcParams['hatch.linewidth'] = 0.6
fig, axes = plt.subplots(nrows, ncols, figsize=figsize, squeeze=False)

for p in range(len(plots)):
    plot = plots[p]
    ax = axes[p // ncols][p % ncols]

    files = plot["files"]
    series = parse_files(files)

    assert len(series) == len(files), "the parser didn't work correctly"
    assert len(legendnames) == len(series), "you have more/less files than legend names"

    categories = plot.get("categories", config.get("categories", None))
    if categories is not None:
        names, catlabels = parse_categories(categories)
    else:
        names = []
        for values in series:
            names += [name for name in values if name not in names]
        catlabels = names

    # the group of a category is centered at its index, every series takes
    # the same slice of it. a category missing from a file has no bar there
    width = barwidth / len(series)
    for i in range(len(series)):
        positions = [c - barwidth / 2 + (i + 0.5) * width for c in range(len(names)) if names[c] in series[i]]
        heights = [series[i][name] for name in names if name in series[i]]
        lname = legendnames[i]
        color = colors[i] if colors != [] else "C" + str(i % 10)
        hatch = hatches[i] if hatches != [] else ''
        # the edge line is centered on the border of the bar, so half of it
        # would be drawn over the next bar. clipping every bar to itself keeps
        # only the inner half, the line widths are doubled to compensate
        if filled[i]:
            bars = ax.bar(positions, heights, width, label="\\texttt{"+lname+"}", color=color,
                          hatch=hatch, edgecolor='black' if hatch else color, linewidth=1.2)
        else:
            bars = ax.bar(positions, heights, width, label="\\texttt{"+lname+"}", facecolor='none',
                          hatch=hatch, edgecolor=color, linewidth=2)
        for bar in bars:
            bar.set_clip_path(bar)

    ax.set_xticks(range(len(names)), catlabels)
    ax.set_xlim(-0.5, len(names) - 0.5)

    logy = plot.get("logy", config.get("logy", False))
    if logy:
        ax.set_yscale('log')

    # without limits the axis starts at 0, matplotlib still picks the max.
    # a log axis can't reach 0, so it keeps the automatic min
    limity = plot.get("limity", config.get("limity", None))
    if limity is not None:
        ax.set_ylim(limity[0], limity[1])
    elif not logy:
        ax.set_ylim(bottom=0)

    # given ticks replace the automatic ones, in a log axis they also replace
    # the minor ticks drawn between the powers
    ticksy = plot.get("ticksy", config.get("ticksy", None))
    if ticksy is not None:
        positions, ticklabels = parse_ticks(ticksy)
        ax.set_yticks(positions, ticklabels)
        ax.set_yticks([], minor=True)

    # gray lines at the ticks of the y axis, behind the bars
    if plot.get("gridlines", gridlines):
        ax.grid(True, axis='y', color='gainsboro', linestyle='--', linewidth=0.6)
        ax.set_axisbelow(True)

    # labels only on the leftmost and the bottommost plots
    if p % ncols == 0:
        ax.set_ylabel(labely)
    if p + ncols >= len(plots):
        ax.set_xlabel(labelx)

    if len(plots) > 1:
        ax.set_title(plot.get("title", ""))

# empty cells of an incomplete grid
for p in range(len(plots), nrows * ncols):
    axes[p // ncols][p % ncols].axis('off')

if len(plots) > 1:
    fig.suptitle(title)
else:
    axes[0][0].set_title(title)

# one legend for every plot, they all draw the same series
handles, labels = axes[0][0].get_legend_handles_labels()
legend = fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, 0), ncol=len(legendnames))

# the patches of the legend aren't clipped, so their edge lines are drawn
# whole and need their original width back
for patch in legend.get_patches():
    patch.set_linewidth(patch.get_linewidth() / 2)

fig.tight_layout()
fig.savefig(ofile, bbox_inches='tight')
if args.show:
    plt.show()
