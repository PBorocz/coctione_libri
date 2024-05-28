"""Tag Management Operations."""

import datetime
import logging as log
from collections import defaultdict

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from mongoengine.context_managers import switch_collection

from app.models.documents import Documents
from app.models.users import Users

matplotlib.use("agg")


def get_all_tags(user: Users, sort: str = "tag", order: str = "asc") -> list[str, int]:
    """Return a sorted list of all current tags & counts (ie. those attached to documents)."""
    tags = defaultdict(int)
    with switch_collection(Documents, Documents.as_user(user)) as user_documents:
        for document in user_documents.objects().only("tags"):
            for tag in document.tags:
                tags[tag] += 1

    log.info(f"{len(tags):,d} unique tags found.")
    offset = 0 if sort == "tag" else 1
    return sorted(tags.items(), key=lambda entry: entry[offset], reverse=(order == "desc"))


def get_tag_count(user: Users, tag: str) -> int:
    """Return the count of documents that have the specified tag."""
    with switch_collection(Documents, Documents.as_user(user)) as user_documents:
        return user_documents.objects(tags__in=[tag]).count()


def remove_tag(user: Users, tag: str) -> int:
    """Remove specified tag from all documents."""
    log.debug(f"Removing {tag=}")
    with switch_collection(Documents, Documents.as_user(user)) as user_documents:
        return user_documents.objects(tags__in=[tag]).update(pull__tags=tag)


def update_tag(user: Users, old: str, new: str) -> int:
    """Update all document with "old" tag to have "new" on instead."""
    log.debug(f"Updating {old=} {new=}")
    with switch_collection(Documents, Documents.as_user(user)) as user_documents:
        ids = [doc.id for doc in user_documents.objects(tags__in=[old]).only("id")]
        count_pulled = user_documents.objects(id__in=ids).update(pull__tags=old)
        count_pushed = user_documents.objects(id__in=ids).update(push__tags=new)
        if count_pulled != count_pushed:
            msg = f"Sorry, we 'should' have pulled {count_pulled=} as many document as we pushed {count_pushed=}"
            log.error(msg)

    return count_pushed


################################################################################
def create_figure(tags):
    """Generate an "economist" style bar plot.

    https://towardsdatascience.com/making-economist-style-plots-in-matplotlib-e7de6d679739
    """
    render_top_n = 30

    # Setup plot size.
    fig, ax = plt.subplots(figsize=(3, 10))

    # Create grid (Zorder tells it which layer to put it on. We are setting this to 1
    # and our data to 2 so the grid is behind the data)
    ax.grid(which="major", axis="x", color="#758D99", alpha=0.6, zorder=1)

    # Remove splines. Can be done one at a time or can slice with a list.
    ax.spines[["top", "right", "bottom"]].set_visible(False)

    # Make left spine slightly thicker
    ax.spines["left"].set_linewidth(1.1)

    # Setup data
    datum = pd.DataFrame(tags, columns=["tag", "count"])
    datum_bar = datum.sort_values(by="count")[-render_top_n:]

    # Plot data
    ax.barh(datum_bar["tag"], datum_bar["count"], color="#006BA2", zorder=2)

    # Set custom labels for x-axis
    ax.set_xticks([0, 10, 20, 30, 40, 50, 60])
    ax.set_xticklabels(["0", "10", " 20", "30", "40", "50", "60"])
    ax.xaxis.set_tick_params(
        labeltop=True,  # Put x-axis labels on top
        labelbottom=False,  # Set no x-axis labels on bottom
        bottom=False,  # Set no ticks on bottom
        labelsize=11,  # Set tick label size
        pad=-1,
    )  # Lower tick labels a bit

    # Set and format y-axis tick labels
    ax.set_yticks(datum_bar["tag"])
    ax.set_yticklabels(datum_bar["tag"], ha="left")  # Set labels (again) but now set horizontal alignment to left.
    ax.yaxis.set_tick_params(
        pad=100,  # Pad tick labels so they don"t go over y-axis
        labelsize=11,  # Set label size
        bottom=False,
    )  # Set no ticks on bottom/left

    # Shrink y-lim to make plot a bit tighter (for a bar-chart, this is the top and bottom)
    # (the bottom is 0.5 less than the number of items and the "top" is fixed at -0.5 of a bar)
    ax.set_ylim(-0.5, render_top_n - 0.5)

    # Add in top line and tag
    ax.plot(
        [-0.35, 0.87],  # Set width of line
        [1.02, 1.02],  # Set height of line
        transform=fig.transFigure,  # Set location relative to plot
        clip_on=False,
        color="#E3120B",
        linewidth=0.6,
    )

    ax.add_patch(
        plt.Rectangle(
            (-0.35, 1.02),  # Set location of rectangle by lower left corder
            0.12,  # Width of rectangle
            -0.02,  # Height of rectangle. Negative so it goes down.
            facecolor="#E3120B",
            transform=fig.transFigure,
            clip_on=False,
            linewidth=0,
        )
    )

    # Add in title and subtitle
    ax.text(
        x=-0.35,
        y=0.980,
        s="Tag Popularity",
        transform=fig.transFigure,
        ha="left",
        fontsize=13,
        weight="bold",
        alpha=0.8,
    )
    ax.text(x=-0.35, y=0.955, s="By Recipe Count", transform=fig.transFigure, ha="left", fontsize=11, alpha=0.8)

    # Set footer text (usually a data source)
    ax.text(
        x=-0.35,
        y=0.08,
        s=f"""As of {datetime.datetime.now().isoformat().split(".")[0]}""",
        transform=fig.transFigure,
        ha="left",
        fontsize=9,
        alpha=0.7,
    )

    # Export plot as high resolution PNG
    fn_ = "tag_count.png"
    fn_fig_render = f"images/{fn_}"  # Set path and filename to RENDER!
    fn_fig_save = f"app/static/{fn_fig_render}"  # Set path and filename to SAVE
    plt.savefig(
        fn_fig_save,
        dpi=100,  # Set dots per inch
        bbox_inches="tight",  # Remove extra whitespace around plot
        facecolor="white",
    )  # Set background color to white
    return fn_fig_render
