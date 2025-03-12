import geopandas as gp
import matplotlib.pyplot as plt


def make_fig(fig_name="Figure1"):
    fig, ax = plt.subplots(figsize=(10, 10), layout="tight", num=fig_name)
    plt.axis("off")

    return fig, ax


def plot_pas(ax, pas, buffer=True):
    pas["pa"].plot(
        ax=ax, linewidth=0.5, ec="green", hatch_linewidth=0.5, hatch="///", fc="none"
    )

    pas.apply(
        lambda x: ax.annotate(
            text=x["name"],
            xy=x["pa"].representative_point().coords[0],
            ha="center",
            wrap=True,
            color="green",
            fontsize="medium",
        ),
        axis=1,
    )

    pa_bounds = pas["pa"].bounds

    if buffer:
        pas["buffer"].plot(
            ax=ax,
            linewidth=0.5,
            ec="yellow",
            hatch_linewidth=0.5,
            hatch="///",
            fc="none",
        )

        pa_bounds = pas["buffer"].bounds

    minx = pa_bounds["minx"].min()
    miny = pa_bounds["miny"].min()

    maxx = pa_bounds["maxx"].max()
    maxy = pa_bounds["maxy"].max()

    plt.xlim(minx, maxx)
    plt.ylim(miny, maxy)

    return "PA(s) added"


def plot_admin(ax, gdf):
    txt_sizes = [
        "medium",
        "small",
        "x-small",
        "xx-small",
    ]

    gdf.plot(ax=ax, linewidth=0.5, ec="grey", fc="none", linestyle="--")

    gdf.apply(
        lambda x: ax.annotate(
            text=x["name"],
            xy=x.geometry.representative_point().coords[0],
            ha="center",
            wrap=True,
            color="grey",
            fontsize=txt_sizes[gdf.index.nlevels - 1],
        ),
        axis=1,
    )

    return "Admin(s) added"


def save_png(fig, f_name):
    fig.savefig(f_name, dpi=150, format="png", bbox_inches="tight")

    return "figure saved"


def multi_plot_pas(row, admins=[]):
    name = str(row.name) + "_" + row["name"]
    fig, ax = make_fig(name)

    for a in admins:
        plot_admin(ax, a)

    pa = gp.GeoSeries(row.pa)
    pa_buffer = gp.GeoSeries(row.buffer)
    total = gp.GeoSeries(row.pa.union(row.buffer))

    pa.plot(
        ax=ax, linewidth=0.5, ec="green", hatch_linewidth=0.5, hatch="///", fc="none"
    )

    pa_rep_point = pa.representative_point().get_coordinates().values[0]

    ax.annotate(
        text=row["name"],
        xy=(pa_rep_point[0], pa_rep_point[1]),
        ha="center",
        wrap=True,
        color="green",
        fontsize="medium",
    )

    pa_buffer.plot(
        ax=ax,
        linewidth=0.5,
        ec="yellow",
        hatch_linewidth=0.5,
        hatch="///",
        fc="none",
    )

    pa_bounds = total.bounds

    xylimits = pa_bounds.values[0]

    plt.xlim(xylimits[0], xylimits[2])
    plt.ylim(xylimits[1], xylimits[3])

    return [name, fig]


def plot_zip(gdf, lst):
    figs = []

    for i in range(len(lst)):
        fig, ax = make_fig(str(i))

        plot_admin(ax, lst[i])

        name = gdf.loc[0, "name"]
        pa = gp.GeoSeries(gdf.loc[i, "pa"])
        buffer = gp.GeoSeries(gdf.loc[i, "buffer"])

        buffer.plot(
            ax=ax,
            linewidth=0.5,
            ec="yellow",
            hatch_linewidth=0.5,
            hatch="///",
            fc="none",
        )

        pa.plot(
            ax=ax,
            linewidth=0.5,
            ec="green",
            hatch_linewidth=0.5,
            hatch="///",
            fc="none",
        )

        pa_rep_point = pa.representative_point().get_coordinates().values[0]

        ax.annotate(
            text=name,
            xy=(pa_rep_point[0], pa_rep_point[1]),
            ha="center",
            wrap=True,
            color="green",
            fontsize="medium",
        )

        xylimits = lst[i].bounds

        plt.xlim(xylimits["minx"].min(), xylimits["maxx"].max())
        plt.ylim(xylimits["miny"].min(), xylimits["maxy"].max())

        figs.append(fig)

    return figs


def get_intersects(gdf, p):
    gdf2 = gdf.copy()
    gdf2["geometry"] = gdf["geometry"].intersection(p)
    gdf2 = gdf2[~gdf2["geometry"].is_empty]

    return gdf2
