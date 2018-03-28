from math import ceil, cos, radians, sin
from PIL import Image, ImageDraw, ImageFont

vu_navy =   (  0,  31,  91)
vu_yellow = (255, 220,  79)
vu_orange = (248, 151,  40)
vu_green =  (193, 205,  35)
vu_blue =   ( 80, 145, 205)
vu_teal =   (  0, 146, 143)
vu_gray=    (148, 156, 166)

colors = [vu_navy, vu_blue, vu_orange, vu_yellow]

def comma(num):
    return '{:,}'.format(num)

def smart_text(draw, text, x, y, font, align="left", fillColor=(255, 255, 255), border=vu_navy):
    draw.text((x - 1, y), text, fill=border, font=font, align=align)
    draw.text((x, y - 1), text, fill=border, font=font, align=align)
    draw.text((x + 1, y), text, fill=border, font=font, align=align)
    draw.text((x, y + 1), text, fill=border, font=font, align=align)
    draw.text((x - 1, y + 1), text, fill=border, font=font, align=align)
    draw.text((x - 1, y - 1), text, fill=border, font=font, align=align)
    draw.text((x + 1, y + 1), text, fill=border, font=font, align=align)
    draw.text((x + 1, y - 1), text, fill=border, font=font, align=align)
    draw.text((x, y), text, fill=fillColor, font=font, align=align)

def bar_graph(filename, data, title=None, key=None, labels=None, numbers=True):
    bar_width = 60
    bar_gap = 15
    bar_border = 1
    padding = 20
    width = ((bar_width + bar_gap) * len(data)) - bar_gap + padding * 2
    height = 600

    im = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(im)
    gotham_font = ImageFont.truetype("fonts/opensans-semibold-webfont.ttf", 10)

    bottom_pad = 0
    if labels != None:
        for l in labels:
            _, th = draw.textsize(l, font=gotham_font, spacing=2)
            if th > bottom_pad:
                bottom_pad = th
    bottom = height - (padding / 2) - bottom_pad

    x = padding
    max = 0
    for arr in data:
        for d in arr:
            if d > max:
                max = d
    bar = 0
    totals = []
    for i in data[0]:
        totals.append(0)
    for arr in data:
        arr.sort(reverse=True)
        index = 0
        for d in arr:
            totals[index] += d
            if d == 0:
                continue
            bar_h = (height - bottom_pad - padding * 2) * (d / max)
            if index == 0:
                box = (
                    x - bar_border,
                    bottom - bar_h - bar_border,
                    x + bar_width + bar_border,
                    bottom + bar_border
                )
                draw.rectangle(box, fill=(0, 0, 0))
                if numbers:
                    c_arr = []
                    c_colors = []
                    for i in range(len(arr)):
                        if arr[i] > 0:
                            c_arr.append(arr[i])
                            c_colors.append(colors[i])
                    stats = ", ".join([comma(d) for d in c_arr])
                    _, h = draw.textsize("0,", font=gotham_font)
                    w, _ = draw.textsize(stats, font=gotham_font)
                    for i in range(len(c_arr)):
                        stats = ", ".join([comma(d) for d in c_arr[i:]])
                        draw.text((x + bar_width + bar_border - w, bottom - bar_h - h), comma(c_arr[i]), fill=c_colors[i], spacing=2, font=gotham_font)
                        if i == len(c_arr) - 1:
                            break
                        sub_w, _ = draw.textsize(comma(c_arr[i]), font=gotham_font)
                        w -= sub_w
                        draw.text((x + bar_width + bar_border - w, bottom - bar_h - h), ", ", fill=c_colors[0], spacing=2, font=gotham_font)
                        sub_w, _ = draw.textsize(", ", font=gotham_font)
                        w -= sub_w
            box = (
                x,
                bottom - bar_h,
                x + bar_width,
                bottom
            )
            draw.rectangle(box, fill=(colors[index]))
            index += 1
        if labels != None:
            draw.text((x, bottom + 3), labels[bar], fill=(0, 0, 0), spacing=2, font=gotham_font)
        x += bar_width + bar_gap
        bar += 1

    # Titles
    if title != None:
        gotham_title = ImageFont.truetype("fonts/opensans-semibold-webfont.ttf", 24)
        title_w, title_h = draw.textsize(title, font=gotham_title)
        draw.text((width - title_w - padding, padding), title, fill=(0, 0, 0), font=gotham_title)

    # Key
    if key != None:
        y = padding + 28
        max_w = 0
        max_h = 0
        for k in key:
            w, h = draw.textsize(k, font=gotham_font)
            if w > max_w:
                max_w = w
            if h > max_h:
                max_h = h
        for i in range(len(key)):
            # Bar
            draw.rectangle((width - max_w - padding - 20, y, width - padding, y + max_h + 9), fill=(colors[i]))
            smart_text(draw, key[i], width - max_w - padding - 10, y + 5, gotham_font)
            # Totals
            total_text = comma(totals[i])
            if i > 0:
                total_text += " (%.1f%%)" % (100 * totals[i] / totals[0])
            total_w, _ = draw.textsize(total_text, font=gotham_font)
            draw.text((width - total_w - max_w - padding - 25, y + 5), total_text, fill=(colors[i]), font=gotham_font)
            y += max_h + 9 + 5

    del draw
    im.save(filename)

def pie_chart(filename, data, gap=0):
    padding = 100
    width = height = 600 + padding
    full_width = width + padding

    im = Image.new("RGB", (full_width, full_width), (255, 255, 255))
    draw = ImageDraw.Draw(im)

    gotham_title = ImageFont.truetype("fonts/opensans-semibold-webfont.ttf", 48)
    title_w, title_h = draw.textsize(data["title"], font=gotham_title)
    draw.text(((padding + width - title_w) / 2, (padding - title_h) / 2), data["title"], fill=(0, 0, 0), font=gotham_title)

    levels = {}
    level_step = 50
    label_text = []
    label_colors = []
    for arc in data["arcs"]:
        label_text.append(arc["label"])
        label_colors.append(arc["color"])

        if not arc["level"] in levels:
            levels[arc["level"]] = -90
        perc = (360 * arc["value"] / data["total"])
        mid_angle_rad = radians(levels[arc["level"]] + perc / 2)
        shrink = arc["level"] * level_step
        arc_xy = (padding + shrink + gap * cos(mid_angle_rad),padding + shrink + gap * sin(mid_angle_rad) , width - shrink,height - shrink)
        draw.pieslice(arc_xy, levels[arc["level"]], levels[arc["level"]] + perc, fill=arc["color"])
        levels[arc["level"]] += perc

    gotham_medium = ImageFont.truetype("fonts/opensans-semibold-webfont.ttf", 12)
    _, line_height = draw.textsize("0g", font=gotham_medium)
    box_width = full_width / len(label_text)
    box_height = line_height * 4
    x = 0
    y = full_width - box_height
    for l in range(len(label_text)):
        draw.rectangle((x, y, x + box_width, y + box_height), fill=(label_colors[l]))
        text_w, text_h = draw.textsize(label_text[l], font=gotham_medium)
        smart_text(draw, label_text[l], x + (box_width - text_w) / 2, y + 2 + (box_height - text_h) / 2, border=(100,100,100), font=gotham_medium, align="center")
        x += box_width
    # draw.text(((padding + width - title_w) / 2, (padding - title_h) / 2), data["title"], fill=(0, 0, 0), font=gotham_title)

    del draw
    im.save(filename)

def box_chart(filename, data):
    width = height = 800
    gutter = 50
    im = Image.new("RGB", (width, height + gutter), (200, 200, 200))
    draw = ImageDraw.Draw(im)
    gotham_title = ImageFont.truetype("fonts/opensans-semibold-webfont.ttf", 24)

    data_total = 0
    min_width = 3
    min_value = (min_width + 1) * data["total"] / width
    for box in data["values"]:
        box_total = 0
        for v in box:
            box_total += v["value"]
        if box_total == 0:
            continue
        if box_total < min_value:
            data_total += min_value
        else:
            data_total += box_total

    pos_y = gutter
    pos_list = []
    sub_bar_pos = []
    for box in data["values"]:
        box_total = 0
        for v in box:
            box_total += v["value"]
        if box_total == 0:
            pos_list.append(pos_y)
            continue
        box_h = width * max(min_value, box_total) / data_total
        min_h = max(min_value, box_total) / box_h
        if len(box) == 1:
            draw.rectangle((0,pos_y , width,pos_y + box_h), fill=(box[0]["color"]))
        else:
            pos_x = 0
            for i in range(len(box)):
                v = box[i]
                if v["value"] == 0:
                    sub_bar_pos.append(pos_x)
                    continue
                link_gap = (len(data["key"]) - i) * 2
                box_w = width * max(min_h, v["value"]) / box_total
                draw.rectangle((pos_x,pos_y - link_gap , pos_x + box_w,pos_y + box_h + link_gap), fill=(v["color"]))
                sub_bar_pos.append(pos_x)
                pos_x += box_w
            sub_bar_pos.append(width)
        pos_y += box_h
        pos_list.append(pos_y)
    # Labels
    prev_label_y = 0
    for i in range(len(data["values"])):
        box = data["values"][i]
        if len(box) != 1:
            continue
        if box[0]["value"] == 0:
            continue
        label_w, label_h = draw.textsize(box[0]["label"], font=gotham_title)
        label_y = max(prev_label_y, pos_list[i] - label_h - 1)
        smart_text(draw, box[0]["label"], (width - label_w) / 2, label_y, font=gotham_title, fillColor=(0, 0, 0), border=box[0]["color"])
        prev_label_y = label_y + label_h + 1

    # chart_box = (0, 0, width, height)
    # region = im.crop(chart_box)
    # region = region.rotate(90)
    # im.paste(region, chart_box)

    gotham_label = ImageFont.truetype("fonts/opensans-semibold-webfont.ttf", 12)
    # draw.rectangle((0,0 , width,gutter), fill=(0, 0, 0))
    pos_x = 0
    gap = 2
    key_w = width / len(data["key"])
    for i in range(len(data["key"])):
        key = data["key"][i]
        # Rect
        draw.rectangle((pos_x,0, pos_x + key_w,gutter), fill=key["color"])
        # Gap Line
        if i == 1:
            draw.rectangle((sub_bar_pos[i],gutter - gap , pos_x + key_w  - 1,gutter), fill=key["color"])
            # Dividers
            draw.rectangle((sub_bar_pos[i],gutter - gap - 1 , pos_x  - 1,gutter - gap - 1), fill=(0, 0, 0))
            draw.rectangle((sub_bar_pos[i + 1],gutter , pos_x + key_w  - 1,gutter), fill=(0, 0, 0))
            if sub_bar_pos[i] > 2:
                draw.rectangle((sub_bar_pos[i] - 1,gutter - gap - 1 , sub_bar_pos[i] - 1,gutter), fill=(0, 0, 0))

        # Label
        key_label_w, key_label_h = draw.textsize(key["label"], font=gotham_label)
        smart_text(
            draw, key["label"],
            pos_x + (key_w - key_label_w) / 2, (gutter - key_label_h) / 2,
            font=gotham_label, align="center"
        )
        pos_x += key_w

    del draw
    im.save(filename)
