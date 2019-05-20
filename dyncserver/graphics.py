import matplotlib
import matplotlib.pyplot as plt
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import networkx as nx
import logging
import math

matplotlib.use('Agg')
logger = logging.getLogger('general')


class GfxHelper:

    image_size = 750

    @staticmethod
    def map_coords_to_image_coords(map_coords, bbox, img_side_len):
        # Remember that in image coordinates, origin is at top left, but in graph coordinates the lowest number is found
        # at bottom left. This is why the y-coordinates are of the form "1.0 - (ratio in graph coordinates)"
        x = (map_coords[0] - bbox[0]) / img_side_len
        y = 1.0 - ((map_coords[1] - bbox[2]) / img_side_len)

        # We know our image is given number of  pixels, so we simply multiply it with the ratio and get the pixel
        # coordinates of the correct node in the image.
        x, y = GfxHelper.image_size * x, GfxHelper.image_size * y
        return x, y

    @staticmethod
    def draw_map(graph, coords, bbox, red_goal, blue_goal, groups, movement_decisions):

        plt.figure(figsize=(GfxHelper.image_size/100.0, GfxHelper.image_size/100.0), dpi=100)

        # Bounding box numbers are listed in this order: min-x, max-x, min-y, max-y. NetworkX expects to get them in
        # this order in a list.
        width, height = bbox[1] - bbox[0], bbox[3] - bbox[2]

        if width <= height:
            padding_total = height / 10
            print(repr(padding_total))
            difference = height - width
            bbox[1] += (difference / 2) + (padding_total / 2)
            bbox[0] -= (difference / 2) + (padding_total / 2)
            bbox[3] += padding_total / 2
            bbox[2] -= padding_total / 2
            height += padding_total
            square_side_len = height
        else:
            padding_total = width / 10
            difference = width - height
            bbox[3] += (difference / 2) + (padding_total / 2)
            bbox[2] -= (difference / 2) + (padding_total / 2)
            bbox[1] += padding_total / 2
            bbox[0] -= padding_total / 2
            width += padding_total
            square_side_len = width

        # Due to all the fiddling above, these don't contain valid values anymore. Use square_side_len.
        # noinspection PyUnusedLocal
        height, width = None, None

        nx.drawing.nx_pylab.draw(graph, coords, node_size=6, node_color="#80e080", edge_color="#a0a0a0")
        plt.axis(bbox)
        buf = BytesIO()
        plt.savefig(buf, format="png", dpi=100)
        plt.close()
        buf.seek(0)
        # Now the graph itself is drawn, and we can start drawing over it with Pillow. We load the original buffer, save
        # to another buffer from Pillow, and close the original. Then return the other one to caller.

        # Note: Pillow has a strange quirk that is not well documented. In case to draw over an existing bitmap using
        # Any alpha values, the image to which we are drawing must be RGB, not RGBA. If it is the latter, the alphas
        # will not blend between the image and the drawing. Since NetworkX saved the graph as RGBA we need to open it,
        # and paste it into a new RGB image. This will allow us to use alpha in the expected way.

        oldimage = Image.open(buf)
        image = Image.new(mode="RGB", size=(GfxHelper.image_size, GfxHelper.image_size))
        image.paste(oldimage)
        oldimage.close()
        buf.close()

        # Ok, now we are through with the alpha channel unpleasantness, and can start drawing.

        draw = ImageDraw.Draw(image, mode="RGBA")
        font = ImageFont.truetype('verdana.ttf', size=20)
        line_spacing = 6

        # red_goal and blue_goal contain node ID's. The dictionary coords maps these to graph node coordinates. They are
        # tuples of the form (x, y)
        red_goal_coords = coords[red_goal]
        blue_goal_coords = coords[blue_goal]

        # Remember that in image coordinates, origin is at top left, but in graph coordinates the lowest number is found
        # at bottom left. This is why the y-coordinates are of the form "1.0 - (ratio in graph coordinates)"
        # ratio_red_goal_x = (red_goal_coords[0] - bbox[0]) / square_side_len
        # ratio_red_goal_y = 1.0 - ((red_goal_coords[1] - bbox[2]) / square_side_len)
        # ratio_blue_goal_x = (blue_goal_coords[0] - bbox[0]) / square_side_len
        # ratio_blue_goal_y = 1.0 - ((blue_goal_coords[1] - bbox[2]) / square_side_len)

        # We know our image is given number of  pixels, so we simply multiply it with the ratio and get the pixel
        # coordinates of the correct node in the image.
        # x, y = GfxHelper.image_size * ratio_red_goal_x, GfxHelper.image_size * ratio_red_goal_y
        x, y = GfxHelper.map_coords_to_image_coords(red_goal_coords, bbox, square_side_len)

        message = "Red\nGoal"
        color = '#ff0000'
        size = draw.textsize(message, font=font, spacing=line_spacing)

        # Alpha zero = invisible outline
        draw.ellipse([x - 4, y - 4, x + 4, y + 4], outline="#ffffff00", fill="#ff0000")

        # Now we still have the problem that draw.text expects to get the coordinates of the top left corner of the
        # text and we really want to place center. We use the text size we just received, for that end.

        x -= size[0] / 2
        # The +3 is just a magic constant that makes the text LOOK more centered vertically. It was acquired by trying
        # variables until centering was good over several line heights.
        y -= (size[1] / 2) + 3

        draw.text((x, y), message, fill=color, font=font, align="center", spacing=line_spacing)

        # Finally, we do the exact same thing for the other goal. Comments are not repeated here.
        x, y = GfxHelper.map_coords_to_image_coords(blue_goal_coords, bbox, square_side_len)

        # x, y = GfxHelper.image_size * ratio_blue_goal_x, GfxHelper.image_size * ratio_blue_goal_y
        message = "Blue\nGoal"
        color = '#0000ff'
        size = draw.textsize(message, font=font, spacing=line_spacing)

        draw.ellipse([x - 4, y - 4, x + 4, y + 4], outline="#ffffff00", fill="#0000ff")

        x -= size[0] / 2
        y -= (size[1] / 2) + 3
        draw.text((x, y), message, fill=color, font=font, align="center", spacing=line_spacing)

        # font = ImageFont.truetype('verdana.ttf', size=14)

        for node_id in groups:
            group_node_list = groups[node_id]
            for group_data in group_node_list:
                if group_data["coalition"] == "red":
                    solid_color = "#ff0000ff"
                    symbol_color = "#ff000090"
                    unimportant_symbol_color = "#ff000050"
                elif group_data["coalition"] == "blue":
                    solid_color = "#0000ffff"
                    symbol_color = "#0000ff90"
                    unimportant_symbol_color = "#0000ff50"
                else:
                    continue
                if node_id not in coords:
                    logger.warning('While drawing map, node %d is not in the dictionary "coords"' % node_id)
                    continue
                group_coords = coords[node_id]
                ratio_x = (group_coords[0] - bbox[0]) / square_side_len
                ratio_y = 1.0 - ((group_coords[1] - bbox[2]) / square_side_len)
                x, y = GfxHelper.image_size * ratio_x, GfxHelper.image_size * ratio_y

                group_type = group_data["type"]

                if group_type == "infantry":
                    triangle_side_len = 12.0
                    top = (x, y - (1.732 * triangle_side_len / 4))
                    left = (x + (-1 * triangle_side_len / 2), y - (-1.732 * triangle_side_len / 4))
                    right = (x + (triangle_side_len / 2), y - (-1.732 * triangle_side_len / 4))
                    draw.polygon([top, right, left], outline=solid_color, fill=symbol_color)
                elif group_type == "support":
                    draw.rectangle([x - 6, y - 6, x + 6, y + 6], outline=solid_color, fill=symbol_color)
                elif group_type == "vehicle":
                    draw.ellipse([x - 5, y - 5, x + 5, y + 5], outline=symbol_color, fill=unimportant_symbol_color)

                # Uncomment these to draw name of unit. Warning: will make things look crowded. Also uncomment the font
                # definition above the loop.
                # if group_type == "vehicle":
                #     size = draw.textsize(group_data["name"], font=font)
                #     x_text = x - size[0] / 2
                #     y_text = y - ((size[1] / 2) + 10)
                #     draw.text((x_text, y_text), group_data["name"], fill=solid_color, font=font)

        for decision in movement_decisions:
            print(repr(decision))
            origin_node = decision["origin_node"]
            destination_node = decision["destination_node"]

            if decision["coalition"] == "red":
                color = "#ff00007f"
            elif decision["coalition"] == "blue":
                color = "#0000ff7f"
            else:
                continue
            if origin_node not in coords or destination_node not in coords:
                logger.warning('While drawing map, origin (%d) and/or destination (%d) node is not in the dictionary '
                               '"coords"' % (origin_node, destination_node))
                continue
            origin = coords[origin_node]
            destination = coords[destination_node]
            origin_x, origin_y = GfxHelper.map_coords_to_image_coords(origin, bbox, square_side_len)
            dest_x, dest_y = GfxHelper.map_coords_to_image_coords(destination, bbox, square_side_len)
            draw.line([(origin_x, origin_y), (dest_x, dest_y)], width=4, fill=color)

            # Now we draw an arrowhead to the line. Since we're doing trigonometry, we have to switch to a standard
            # coordinate system instead of image coordinates. In other words, positive y must be up. Origin and
            # destination are already in such coordinates, but when we are dealing with image coordinates, we have to
            # multiply y by -1 in order to move between the two systems.
            angle = GfxHelper.clockwise_angle(origin, destination)

            # Coordinates for an arrowhead pointing right, in standard coordinates (positive y is up)
            arrow_end_coords = [(5, 0), (-1, -5), (-1, 5)]

            # We rotate them clockwise by the line's angle
            arrow_end_coords = GfxHelper.rotate_points_around_origin_clockwise(arrow_end_coords, angle)

            # We move the rotated head to the end of the line, remembering to translate image coordinates to normal.
            arrow_end_coords = [GfxHelper.move_point(point, (dest_x, -1 * dest_y)) for point in arrow_end_coords]

            # Finally we translate the result to image coordinates, and we're done. We draw the polygon.
            arrow_end_coords = [(point[0], -1*point[1]) for point in arrow_end_coords]
            draw.polygon(arrow_end_coords, outline=color, fill=color)
        buf = BytesIO()
        image.save(buf, format="png")
        image.close()
        buf.seek(0)

        return buf

    @staticmethod
    def rotate_point_around_origin_clockwise(point, radians):
        # rotates clockwise
        x, y = point
        x2 = x * math.cos(radians) + y * math.sin(radians)
        y2 = -x * math.sin(radians) + y * math.cos(radians)
        return x2, y2

    @staticmethod
    def rotate_points_around_origin_clockwise(points, radians):
        return [GfxHelper.rotate_point_around_origin_clockwise(point, radians) for point in points]

    @staticmethod
    def clockwise_angle(p1, p2):
        # Measures CLOCKWISE rotation angle
        x_diff = p2[0] - p1[0]
        y_diff = p2[1] - p1[1]
        # Atan2 gives counterclockwise angle, hence multiplying by -1
        return -1*math.atan2(y_diff, x_diff)

    @staticmethod
    def move_point(point, target):
        return point[0] + target[0], point[1] + target[1]
