"""Export text content of rm files as Markdown."""

from rmscene import read_tree
from rmscene import scene_items as si
from rmscene.text import TextDocument, CrdtStr, BoldSpan, ItalicSpan

import logging



def print_text(f, fout):
    tree = read_tree(f)

    # Find out what anchor characters are used
    anchor_ids = set(collect_anchor_ids(tree.root))

    if tree.root_text:
        print_root_text(tree.root_text, fout)

    JOIN_TOLERANCE = 2
    # print("\n\n# Highlights", file=fout)
    last_pos = 0
    for item in tree.walk():
        if isinstance(item, si.GlyphRange):
            if item.start > last_pos + JOIN_TOLERANCE:
                print(file=fout)
            print(">", item.text, file=fout)
            last_pos = item.start + len(item.text)
    print(file=fout)

def format_paragraph(line):
    if isinstance(line, BoldSpan):
        return "**"+format_paragraph(line.contents)+"**"
    elif isinstance(line, ItalicSpan):
        return "~~"+format_paragraph(line.contents)+"~~"
    elif isinstance(line, list):
        text = ""
        for line_part in line:
            text = text + format_paragraph(line_part)
        return text
    else:
        return str(line)

def formatted_lines(doc):
    lines = []
    for p in doc.contents:
        lines.append((p.style.value, format_paragraph(p.contents)+"\n"))
    return lines


def print_root_text(root_text, fout):
    doc = TextDocument.from_scene_item(root_text)

    for style, text in formatted_lines(doc):
        
        if style == si.ParagraphStyle.BULLET:
            fout.write("- " + text)
        elif style == si.ParagraphStyle.BULLET2:
            fout.write("  + " + text)
        elif style == si.ParagraphStyle.BOLD:
            fout.write("> " + text)
        elif style == si.ParagraphStyle.HEADING:
            fout.write("# " + text)
        elif style == si.ParagraphStyle.PLAIN:
            fout.write(text)
        else:
            fout.write(("[unknown format %s] " % style) + text)


def annotate_anchor_ids(anchor_ids, line, ids):
    """Annotate appearances of `anchor_ids` in `line`."""
    result = ""
    for char, char_id in zip(line, ids):
        if char_id in anchor_ids:
            result += f"<<{char_id.part1},{char_id.part2}>>"
        result += char
    return result


def collect_anchor_ids(item):
    if isinstance(item, si.Group):
        if item.anchor_id is not None:
            yield item.anchor_id.value
        for child in item.children.values():
            yield from collect_anchor_ids(child)
