from textwrap import wrap

import matplotlib.pyplot as plt


def plot_pas(pas):
    fig, ax = plt.subplots()

    plt.axis("off")

    pas["pa"].plot(
        ax=ax, linewidth=0.5, ec="green", hatch_linewidth=0.5, hatch="///", fc="none"
    )
    pas.reset_index().apply(
        lambda x: ax.annotate(
            text=x["name"], xy=x["pa"].centroid.coords[0], ha="center", wrap=True
        ),
        axis=1,
    )
    pas["buffer"].plot(
        ax=ax, linewidth=0.5, ec="yellow", hatch_linewidth=0.5, hatch="///", fc="none"
    )

    return fig, ax


def save_png(fig, f_name):
    fig.savefig(f_name, dpi=150, format="png", bbox_inches="tight")

    return "figure saved"
