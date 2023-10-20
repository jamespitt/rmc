"""Export text content of rm files as Markdown."""
import logging

from rmscene.scene_items import ParagraphStyle
from rmscene.scene_stream import read_tree
from rmscene.text import TextDocument
from rmscene import SceneLineItemBlock
from .svg import block_to_svg, get_dimensions

SCREEN_WIDTH = 1404
SCREEN_HEIGHT = 1872
SCREEN_DPI = 226

SCALE = 72.0 / SCREEN_DPI

PAGE_WIDTH_PT = SCREEN_WIDTH * SCALE
PAGE_HEIGHT_PT = SCREEN_HEIGHT * SCALE
X_SHIFT = PAGE_WIDTH_PT // 2


def xx(screen_x):
    return screen_x * SCALE #+ X_SHIFT


def yy(screen_y):
    return screen_y * SCALE


TEXT_TOP_Y = -88
LINE_HEIGHTS = {
    # Tuned this line height using template grid -- it definitely seems to be
    # 71, rather than 70 or 72. Note however that it does interact a bit with
    # the initial text y-coordinate below.
    ParagraphStyle.PLAIN: 71,
    ParagraphStyle.BASIC: 71,
    ParagraphStyle.BULLET: 35,
    ParagraphStyle.BULLET2: 35,
    ParagraphStyle.BOLD: 70,
    ParagraphStyle.HEADING: 150,

    # There appears to be another format code (value 0) which is used when the
    # text starts far down the page, which case it has a negative offset (line
    # height) of about -20?
    #
    # Probably, actually, the line height should be added *after* the first
    # line, but there is still something a bit odd going on here.
}

# From rmscene tests: test_text_files.py
def formatted_lines(doc):
    return [(p.style.value, str(p)) for p in doc.contents]

# From rmscene tests: test_text_files.py (modfied version extract_doc)
def extract_doc(fh):
    tree = read_tree(fh)
    if tree.root_text:
        print(tree.root_text)
        assert tree.root_text
        return TextDocument.from_scene_item(tree.root_text)
    else:
        return None

def print_text_with_svg(fin, fout, blocks):
    lines = []
    doc = extract_doc(fin)
    if doc is  None:
        print("No text content found")
    else:
        for fmt, line in formatted_lines(doc):
            if fmt == ParagraphStyle.BULLET:
                # add line and height to array
                lines.append(("- " + line, LINE_HEIGHTS[fmt]))
            elif fmt == ParagraphStyle.BULLET2:
                lines.append(("+ " + line, LINE_HEIGHTS[fmt]))
            elif fmt == ParagraphStyle.BOLD:
                lines.append(("> " + line, LINE_HEIGHTS[fmt]))
            elif fmt == ParagraphStyle.HEADING:
                lines.append(("# " + line, LINE_HEIGHTS[fmt]))
            elif fmt == ParagraphStyle.PLAIN:
                lines.append((line, LINE_HEIGHTS[fmt]))
            else:
                print(("[unknown format %s] " % fmt) + line, file=fout)

    y_text_offset = TEXT_TOP_Y
    y_graphics_offset = TEXT_TOP_Y
    currline, height = lines.pop()
    for block in blocks:
        if isinstance(block, SceneLineItemBlock):
            blocks = list([block])
            svg_doc_info = get_dimensions(blocks, 0,0)
            if not svg_doc_info.ymin is None:
                print("ymin: " + str(svg_doc_info.ymin))
                y_graphics_offset = svg_doc_info.ymin
                while len(lines) > 0 and y_text_offset<y_graphics_offset:
                    y_text_offset += height
                    print(currline + str(y_text_offset), file=fout)
                    currline,height= lines.pop()
                block_to_svg(block, fout, svg_doc_info)

    while len(lines) > 0:
        currline,height= lines.pop()
        y_text_offset += height
        print(currline+str(y_text_offset), file=fout)
