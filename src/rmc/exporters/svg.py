"""Convert blocks to svg file.

Code originally from https://github.com/lschwetlick/maxio through
https://github.com/chemag/maxio .
"""

import logging
import math
import string

from typing import Iterable

from dataclasses import dataclass

from rmscene import (
    read_blocks,
    Block,
    RootTextBlock,
    AuthorIdsBlock,
    MigrationInfoBlock,
    PageInfoBlock,
    SceneTreeBlock,
    TreeNodeBlock,
    SceneGroupItemBlock,
    SceneLineItemBlock,
)

from .writing_tools import (
    Pen,
)

_logger = logging.getLogger(__name__)


SCREEN_WIDTH = 1404
SCREEN_HEIGHT = 1872
SCREEN_DPI = 226

SCALE = 72.0 / SCREEN_DPI

PAGE_WIDTH_PT = SCREEN_WIDTH * SCALE
PAGE_HEIGHT_PT = SCREEN_HEIGHT * SCALE
X_SHIFT = PAGE_WIDTH_PT // 2


SVG_HEADER = string.Template("""
<svg xmlns="http://www.w3.org/2000/svg" height="$height" width="$width">
    <script type="application/ecmascript"> <![CDATA[
        var visiblePage = 'p1';
        function goToPage(page) {
            document.getElementById(visiblePage).setAttribute('style', 'display: none');
            document.getElementById(page).setAttribute('style', 'display: inline');
            visiblePage = page;
        }
    ]]>
    </script>
""")

SVG_HEADER_SIMPLE = string.Template("""
<svg xmlns="http://www.w3.org/2000/svg" height="$height" width="$width">
""")

XPOS_SHIFT = SCREEN_WIDTH / 2


@dataclass
class SvgDocInfo:
    height: int
    width: int
    ymin: int
    ymax: int
    xmin: int
    xmax: int
    xpos_delta: float
    ypos_delta: float


def rm_to_svg(rm_path, svg_path, debug=0):
    """Convert `rm_path` to SVG at `svg_path`."""
    with open(rm_path, "rb") as infile, open(svg_path, "wt") as outfile:
        blocks = read_blocks(infile)
        blocks_to_svg(blocks, outfile, debug)

def block_to_svg(block: Block, output, svg_doc_info, debug=0):
    """Convert Block to SVG."""



    print(repr(svg_doc_info))

    if (svg_doc_info.height==0 or svg_doc_info.width==0):
        return

    svg_doc_info.xpos_delta = 0-svg_doc_info.xmin
    svg_doc_info.ypos_delta = 0-svg_doc_info.ymin



    # add svg header
    output.write(SVG_HEADER_SIMPLE.substitute(height=svg_doc_info.height, width=svg_doc_info.width))
    output.write('\n')

    # add svg page info
    output.write('    <g id="p1" style="display:inline">\n')
    output.write('        <filter id="blurMe"><feGaussianBlur in="SourceGraphic" stdDeviation="10" /></filter>\n')

    draw_stroke(block, output, svg_doc_info, debug)

    # Closing page group
    output.write('    </g>\n')
    # END notebook
    output.write('</svg>\n')


def blocks_to_svg(blocks: Iterable[Block], output, debug=0):
    """Convert Blocks to SVG."""

    # we need to process the blocks twice to understand the dimensions, so
    # let's put the iterable into a list
    blocks = list(blocks)

    # get document dimensions
    svg_doc_info = get_dimensions(blocks, SCREEN_WIDTH, SCREEN_HEIGHT, debug)

    # add svg header
    output.write(SVG_HEADER.substitute(height=svg_doc_info.height, width=svg_doc_info.width))
    output.write('\n')

    # add svg page info
    output.write('    <g id="p1" style="display:inline">\n')
    output.write('        <filter id="blurMe"><feGaussianBlur in="SourceGraphic" stdDeviation="10" /></filter>\n')

    for block in blocks:
        if isinstance(block, SceneLineItemBlock):
            draw_stroke(block, output, svg_doc_info, debug)
        elif isinstance(block, RootTextBlock):
            draw_text(block, output, svg_doc_info, debug)
        else:
            if debug > 0:
                print(f'warning: not converting block: {block.__class__}')

    # Overlay the page with a clickable rect to flip pages
    output.write('\n')
    output.write('        <!-- clickable rect to flip pages -->\n')
    output.write(f'        <rect x="0" y="0" width="{svg_doc_info.width}" height="{svg_doc_info.height}" fill-opacity="0"/>\n')
    # Closing page group
    output.write('    </g>\n')
    # END notebook
    output.write('</svg>\n')


def draw_stroke(block, output, svg_doc_info, debug):
    if debug > 0:
        print('----SceneLineItemBlock')
    # a SceneLineItemBlock contains a stroke
    output.write(f'        <!-- SceneLineItemBlock item_id: {block.item.item_id} -->\n')

    # make sure the object is not empty
    if block.item.value is None:
        return

    # initiate the pen
    pen = Pen.create(block.item.value.tool.value, block.item.value.color.value, block.item.value.thickness_scale)

    # BEGIN stroke
    output.write(f'        <!-- Stroke tool: {block.item.value.tool.name} color: {block.item.value.color.name} thickness_scale: {block.item.value.thickness_scale} -->\n')
    output.write('        <polyline ')
    output.write(f'style="fill:none;stroke:{pen.stroke_color};stroke-width:{pen.stroke_width};opacity:{pen.stroke_opacity}" ')
    output.write(f'stroke-linecap="{pen.stroke_linecap}" ')
    output.write('points="')

    last_xpos = -1.
    last_ypos = -1.
    last_segment_width = 0
    # Iterate through the point to form a polyline
    for point_id, point in enumerate(block.item.value.points):
        # align the original position
        xpos = point.x + svg_doc_info.xpos_delta
        ypos = point.y + svg_doc_info.ypos_delta
        # stretch the original position
        # ratio = (svg_doc_info.height / svg_doc_info.width) / (1872 / 1404)
        # if ratio > 1:
        #    xpos = ratio * ((xpos * svg_doc_info.width) / 1404)
        #    ypos = (ypos * svg_doc_info.height) / 1872
        # else:
        #    xpos = (xpos * svg_doc_info.width) / 1404
        #    ypos = (1 / ratio) * (ypos * svg_doc_info.height) / 1872
        # process segment-origination points
        if point_id % pen.segment_length == 0:
            segment_color = pen.get_segment_color(point.speed, point.direction, point.width, point.pressure, last_segment_width)
            segment_width = pen.get_segment_width(point.speed, point.direction, point.width, point.pressure, last_segment_width)
            segment_opacity = pen.get_segment_opacity(point.speed, point.direction, point.width, point.pressure, last_segment_width)
            # print(segment_color, segment_width, segment_opacity, pen.stroke_linecap)
            # UPDATE stroke
            output.write('"/>\n')
            output.write('        <polyline ')
            output.write(f'style="fill:none; stroke:rgb(255,255,255);stroke-width:{segment_width:.3f};opacity:{segment_opacity}" ')
            output.write(f'stroke-linecap="{pen.stroke_linecap}" ')
            output.write('points="')
            if last_xpos != -1.:
                # Join to previous segment
                output.write(f'{last_xpos:.3f},{last_ypos:.3f} ')
        # store the last position
        last_xpos = xpos
        last_ypos = ypos
        last_segment_width = segment_width

        # BEGIN and END polyline segment
        output.write(f'{xpos:.3f},{ypos:.3f} ')

    # END stroke
    output.write('" />\n')


def draw_text(block, output, svg_doc_info, debug):
    if debug > 0:
        print('----RootTextBlock')
    # a RootTextBlock contains text
    output.write(f'        <!-- RootTextBlock item_id: {block.block_id} -->\n')

    # add some style to get readable text
    output.write('        <style>\n')
    output.write('            .default {\n')
    output.write('                font: 50px serif\n')
    output.write('            }\n')
    output.write('        </style>\n')


    sceneitem_text = block.value
    text = "".join([i[1] for i in block.value.items.items()])
    
    # A way to come up with some unique_id
    textid = ",".join([repr(i[0]) for i in block.value.items.items()])
    
    # BEGIN text
    # https://developer.mozilla.org/en-US/docs/Web/SVG/Element/text
    xpos = block.value.pos_x + svg_doc_info.width / 2
    ypos = block.value.pos_y + svg_doc_info.height / 2
    output.write(f'        <!-- TextItem item_id: {textid} -->\n')
    output.write(f'        <text x="{xpos}" y="{ypos}" class="default">{text}</text>\n')


def get_limits(blocks):
    xmin = xmax = None
    ymin = ymax = None
    for block in blocks:
        if isinstance(block, SceneLineItemBlock):
            xmin_tmp, xmax_tmp, ymin_tmp, ymax_tmp = get_limits_stroke(block)
        # text blocks use a different xpos/ypos coordinate system
        #elif isinstance(block, RootTextBlock):
        #    xmin_tmp, xmax_tmp, ymin_tmp, ymax_tmp = get_limits_text(block)
        else:
            continue
        if xmin_tmp is None:
            continue
        if xmin is None or xmin > xmin_tmp:
            xmin = xmin_tmp
        if xmax is None or xmax < xmax_tmp:
            xmax = xmax_tmp
        if ymin is None or ymin > ymin_tmp:
            ymin = ymin_tmp
        if ymax is None or ymax < ymax_tmp:
            ymax = ymax_tmp
    return xmin, xmax, ymin, ymax


def get_limits_stroke(block):
    # make sure the object is not empty

    if block.item.value is None:
        return None, None, None, None
    xmin = xmax = None
    ymin = ymax = None
    for point in block.item.value.points:
        xpos, ypos = point.x, point.y
        if xmin is None or xmin > xpos:
            xmin = xpos
        if xmax is None or xmax < xpos:
            xmax = xpos
        if ymin is None or ymin > ypos:
            ymin = ypos
        if ymax is None or ymax < ypos:
            ymax = ypos
    return xmin, xmax, ymin, ymax


def get_limits_text(block):
    xmin = block.pos_x
    xmax = block.pos_x + block.width
    ymin = block.pos_y
    ymax = block.pos_y
    return xmin, xmax, ymin, ymax


def get_dimensions(blocks, screen_width, screen_height, debug=0):
    # get block limits
    xmin, xmax, ymin, ymax = get_limits(blocks)
    if debug > 0:
        print(f"xmin: {xmin} xmax: {xmax} ymin: {ymin} ymax: {ymax}")
    # {xpos,ypos} coordinates are based on the top-center point
    # of the doc **iff there are no text boxes**. When you add
    # text boxes, the xpos/ypos values change.
    xpos_delta = XPOS_SHIFT
    if xmin is not None and (xmin + XPOS_SHIFT) < 0:
        # make sure there are no negative xpos
        xpos_delta += -(xmin + XPOS_SHIFT)
    #ypos_delta = SCREEN_HEIGHT / 2
    ypos_delta = 0
    # adjust dimensions if needed
    width = int(math.ceil(max(screen_width, xmax - xmin if xmin is not None and xmax is not None else 0)))
    height = int(math.ceil(max(screen_height, ymax - ymin if ymin is not None and ymax is not None else 0)))
    if debug > 0:
        print(f"height: {height} width: {width} xpos_delta: {xpos_delta} ypos_delta: {ypos_delta}")
    return SvgDocInfo(height=height, width=width, xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax, 
                      xpos_delta=xpos_delta, ypos_delta=ypos_delta)
