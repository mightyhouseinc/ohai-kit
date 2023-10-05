from django import template
register = template.Library()

@register.filter
def columnize(item_list, period):
    """
    Take a list of items [1, 2, 3, 4, 5, 6, 7] and break it up into
    sub lists of some arbitrary period [[1, 2, 3, 4], [5, 6, 7]].
    """
    if not item_list:
        item_list = []
    columns = []
    for ct, item in enumerate(item_list):
        if ct % period == 0:
            columns.append([])
        columns[-1].append(item)
    return columns


@register.filter
def remainderize(item_list, period):
    """
    Generates a list of Nones to fill out the final row.  Used for
    evenly populating tables with data from columnize.
    """
    if not item_list:
        item_list = []
    columns = columnize(item_list, period)
    remainder = period - len(columns[-1])

    return [None for _ in range(remainder)]
