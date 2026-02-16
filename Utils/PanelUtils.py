def go_to_row(layout, *, scale_y=1.2, align=False):
    row = layout.row(align=align)
    row.scale_y = scale_y
    return row

def go_to_box_row(layout, scale_y=1.2, align=False):
    box = layout.box()
    row = box.row(align=align)
    row.scale_y = scale_y
    return row, box

def dropdown_menu(layout, data, prop_name: str, text: str, section_icon=None, force_layout=None):
    expanded = getattr(data, prop_name)
    row, box = go_to_box_row(layout if not force_layout else force_layout, scale_y=1.0 if force_layout else 1.2)
    row.prop(data, prop_name,
             text=text,
             icon='TRIA_DOWN' if expanded else 'TRIA_RIGHT',
             emboss=False,
             toggle=True)
    if section_icon:
        r = row.row(align=True)
        r.enabled = True if expanded else False
        r.label(icon=section_icon)
    return box if expanded else None

def split_row(row, factor=0.5, align=False, right_align=True):
    split = row.split(factor=factor)
    left = split.row(align=align)
    right = split.row(align=align)
    if right_align:
        right.alignment = 'RIGHT'
    return left, right