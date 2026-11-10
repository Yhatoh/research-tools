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
                every file is a list of "x y" lines, separated by a space
  plots         (optional) list of plots to draw in a grid, every entry is an
                object with its own "files" and optionally "title", "limitx",
                "limity", "ticksx", "ticksy", "logx", "logy" (falling back to
                the top level value). omit it to draw a single plot from
                "files"
  grid          (optional) [rows, cols] of the grid (default: as square as
                possible). leftover cells are left empty
  gridlines     (optional) draw gray lines behind the points, at the ticks of
                both axes (default: true)
  figsize       (optional) [width, height] of the whole image in inches
                (default: 4.5 x 3.5 per cell of the grid)
  colors        (optional) color of each series, matplotlib names, hex or "C0"
                (default: the matplotlib color cycle)
  symbols       (optional) marker of each series: "o", "^", "s", "x", "*",
                "D", ... (default: "o" for all of them)
  filled        (optional) fill the markers or draw them hollow, either one
                bool for every series or one bool per series (default: true)
  labelx        (optional) label of the x axis, only drawn on the bottommost
                plots (default: "x")
  labely        (optional) label of the y axis, only drawn on the leftmost
                plots (default: "y")
  limitx        (optional) [min, max] of the x axis (default: min 0 and
                matplotlib picks the max, unless the axis is logarithmic)
  limity        (optional) [min, max] of the y axis (default: min 0 and
                matplotlib picks the max, unless the axis is logarithmic)
  ticksx        (optional) positions of the ticks of the x axis, for example
                [0, 10, 20, 30, 40] (default: matplotlib picks them). every
                position can also be a [position, label] pair to write
                something else under the tick
  ticksy        (optional) the same for the y axis
  logx          (optional) use a log scale in the x axis (default: false)
  logy          (optional) use a log scale in the y axis (default: false)
  title         (optional) title of the plot, or of the whole figure when
                there is a grid (default: no title)

colors, symbols and filled are shared by every plot of the grid, so they all
have the same legend, which is drawn once below the figure.

example of a grid, using every field:

  {
    "output_file": "grid.pdf",
    "legendnames": ["k2octopus", "k2tree"],
    "colors": ["red", "blue"],
    "symbols": ["^", "s"],
    "filled": [true, false],
    "labelx": "space",
    "labely": "time",
    "limitx": [0, 100],
    "limity": [1, 1000],
    "ticksx": [0, 25, 50, 75, 100],
    "ticksy": [1, 10, 100, 1000],
    "logx": false,
    "logy": true,
    "title": "octopus against tree",
    "grid": [1, 2],
    "figsize": [9, 3.5],
    "plots": [
      {"files": ["data/a1", "data/a2"], "title": "dataset a"},
      {"files": ["data/b1", "data/b2"], "title": "dataset b",
       "limitx": [0, 50], "limity": [1, 100], "logx": true, "logy": false,
       "ticksx": [1, 10, 50], "ticksy": [[1, "fast"], [100, "slow"]]}
    ]
  }

the same fields for a single plot, "files" at the top level and no "plots",
"grid" or per plot overrides:

  {
    "output_file": "plot.pdf",
    "legendnames": ["k2octopus", "k2tree"],
    "files": ["data/a1", "data/a2"],
    "colors": ["red", "blue"],
    "symbols": ["^", "s"],
    "filled": [true, false],
    "labelx": "space",
    "labely": "time",
    "limitx": [0, 100],
    "limity": [1, 1000],
    "ticksx": [0, 25, 50, 75, 100],
    "ticksy": [1, 10, 100, 1000],
    "logx": false,
    "logy": true,
    "title": "octopus against tree",
    "figsize": [4.5, 3.5]
  }
"""

def parse_args():
    parser = argparse.ArgumentParser(description='do a scatter plot data',
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

# separated space format
def parse_files(files):
    points = []
    for file in files:
        fstream = open(file, "r")

        points.append([[], []])
        for line in fstream:
            points[-1][0].append(float(line.split(" ")[0]))
            points[-1][1].append(float(line.split(" ")[1]))
    return points

args = parse_args()
config = json.load(open(args.config_file, "r"))

ofile = config["output_file"]
legendnames = config["legendnames"]
colors = config.get("colors", [])
symbols = config.get("symbols", [])
filled = config.get("filled", True)
labelx = config.get("labelx", "x")
labely = config.get("labely", "y")
title = config.get("title", "")
gridlines = config.get("gridlines", True)

# a single plot is just a grid of one
plots = config.get("plots", [config])

# a single bool applies to every file
if isinstance(filled, bool):
    filled = [filled] * len(legendnames)

assert colors == [] or len(colors) == len(legendnames), "you have more/less colors than legend names"
assert symbols == [] or len(symbols) == len(legendnames), "you have more/less symbols than legend names"
assert len(filled) == len(legendnames), "you have more/less filled flags than legend names"

if "grid" in config:
    nrows, ncols = config["grid"]
else:
    ncols = math.ceil(math.sqrt(len(plots)))
    nrows = math.ceil(len(plots) / ncols)
assert nrows * ncols >= len(plots), "the grid is too small for the number of plots"

figsize = config.get("figsize", [4.5 * ncols, 3.5 * nrows])

plt.rcParams['text.usetex'] = True
fig, axes = plt.subplots(nrows, ncols, figsize=figsize, squeeze=False)

for p in range(len(plots)):
    plot = plots[p]
    ax = axes[p // ncols][p % ncols]

    files = plot["files"]
    points = parse_files(files)

    assert len(points) == len(files), "the parser didn't work correctly"
    assert len(legendnames) == len(points), "you have more/less files than points"

    for i in range(len(points)):
        x, y = points[i]
        lname = legendnames[i]
        color = colors[i] if colors != [] else "C" + str(i % 10)
        symbol = symbols[i] if symbols != [] else 'o'
        if filled[i]:
            ax.scatter(x, y, label="\\texttt{"+lname+"}", marker=symbol, color=color)
        else:
            ax.scatter(x, y, label="\\texttt{"+lname+"}", marker=symbol, facecolors='none', edgecolors=color)

    logx = plot.get("logx", config.get("logx", False))
    logy = plot.get("logy", config.get("logy", False))
    if logx:
        ax.set_xscale('log')
    if logy:
        ax.set_yscale('log')

    # without limits the axis starts at 0, matplotlib still picks the max.
    # a log axis can't reach 0, so it keeps the automatic min
    limitx = plot.get("limitx", config.get("limitx", None))
    limity = plot.get("limity", config.get("limity", None))
    if limitx is not None:
        ax.set_xlim(limitx[0], limitx[1])
    elif not logx:
        ax.set_xlim(left=0)
    if limity is not None:
        ax.set_ylim(limity[0], limity[1])
    elif not logy:
        ax.set_ylim(bottom=0)

    # given ticks replace the automatic ones, in a log axis they also replace
    # the minor ticks drawn between the powers
    ticksx = plot.get("ticksx", config.get("ticksx", None))
    ticksy = plot.get("ticksy", config.get("ticksy", None))
    if ticksx is not None:
        positions, ticklabels = parse_ticks(ticksx)
        ax.set_xticks(positions, ticklabels)
        ax.set_xticks([], minor=True)
    if ticksy is not None:
        positions, ticklabels = parse_ticks(ticksy)
        ax.set_yticks(positions, ticklabels)
        ax.set_yticks([], minor=True)

    # gray lines at the ticks, behind the points
    if plot.get("gridlines", gridlines):
        ax.grid(True, color='gainsboro', linestyle='--', linewidth=0.6)
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
fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, 0), ncol=len(legendnames))

fig.tight_layout()
fig.savefig(ofile, bbox_inches='tight')
if args.show:
    plt.show()
