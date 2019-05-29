from werkzeug.wrappers import Request, Response
from werkzeug.serving import run_simple
import json
from jsonrpc import JSONRPCResponseManager, dispatcher
import os.path
from os.path import expanduser
from threading import Thread
from configparser import ConfigParser
from pathlib import Path
import socket

from ai import *
from classes import *
from gui import *
from graphics import GfxHelper
from windowloghandler import WindowLogHandler
from message_service_discord import MessageService

server_obj = None


class DynCServer:

    cfg_default_content = \
        '[campaign]\nMAX_INFANTRY = 4\n\n' \
        '# USA AA types: "Vulcan" "M1097 Avenger" "M48 Chaparral" "Hawk cwar" "Hawk ln" "Hawk pcp"\n' \
        '# "Hawk sr" "Hawk tr" "M6 Linebacker" "Patriot AMG" "Patriot ECS" "Patriot EPP" "Patriot cp"\n' \
        '# "Patriot ln" "Patriot str" "Soldier stinger" "Stinger comm"\n' \
        '# \n' \
        '# Russia AA types: "ZU-23 Emplacement" "ZU-23 Emplacement Closed" "Ural-375 ZU-23"\n' \
        '# "Dog Ear radar" "1L13 EWR" "55G6 EWR" "S-300PS 54K6 cp" "S-300PS 5P85C ln" "S-300PS 5P85D ln"\n' \
        '# "S-300PS 40B6MD sr" "S-300PS 64H6E sr" "S-300PS 40B6M tr" "SA-11 Buk CC 9S470M1"\n' \
        '# "SA-11 Buk LN 9A310M1" "SA-11 Buk SR 9S18M1" "Strela-10M3" "Tor 9A331" "SA-18 Igla-S comm"\n' \
        '# "SA-18 Igla-S manpad" "2S6 Tunguska" "5p73 s-125 ln" "p-19 s-125 sr"\n' \
        '# "snr s-125 tr" "Kub 2P25 ln" "Kub 1S91 str" "Osa 9A33 ln" "Strela-1 9P31" "ZSU-23-4 Shilka"\n' \
        '# \n' \
        '# Example line of several units:\n' \
        '# AA_RED = "ZSU-23-4 Shilka", "Ural-375 ZU-23"\n' \
        'AA_RED = "ZSU-23-4 Shilka"\n' \
        'AA_BLUE = "Vulcan"\n\n' \
        '[logging]\n\n' \
        '# LOG_X_LEVEL: Lowest log level to write. 1=Debug, 2=Info, 3=Warning, 4=Error, 5=Critical\n\n' \
        'LOG_FILE_LEVEL = 2\n' \
        'LOG_WINDOW_LEVEL = 3\n' \
        'LOG_CONSOLE_LEVEL = 2\n\n' \
        '# Uncomment below to use a particular log directory. Make sure you are permitted to write to it.\n' \
        '# LOG_FILE = C:\\dync.log\n\n' \
        '[comms]\n\n# Uncomment and replace with correct URL to have the server post to a Discord channel\n' \
        '# URL = https://discordapp.com/api/webhooks/SOMETHING\n' \
        'USER = DynC Server\n'

    def __init__(self, campaign_json, conf_file, mapbg):
        self.logger = logging.getLogger('general')
        self.logger.setLevel(logging.DEBUG)
        self.log_file_handler = None
        self.log_file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.log_console_handler = logging.StreamHandler()
        self.log_console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        self.log_window_handler = WindowLogHandler()
        self.log_window_formatter = logging.Formatter('%(levelname)s: %(message)s')
        self.campaign = None
        self.campaign_json = campaign_json
        self.conf_file = conf_file
        self.mapbg = mapbg
        self.config = ConfigParser()
        self.server_thread = None
        self.window = None
        self.messages_url = None
        self.messages_user = None
        self.display_map_paths = False
        self.display_map_background = True

        if os.path.isfile(self.conf_file) is False:
            with open(self.conf_file, 'w') as f:
                f.write(DynCServer.cfg_default_content)
        self.init_campaign()
        self.read_config(self.conf_file)

    def init_campaign(self):
        if os.path.isfile(self.campaign_json) is False:
            game_map = Map()
            self.campaign = Campaign(stage=0, game_map=game_map)
        else:
            with open(self.campaign_json, 'r') as f:
                self.campaign = Campaign.from_serializable(json.loads(f.read()))

    def post_init(self):
        if self.campaign.stage > 0:
            self.campaign_changed()

    def read_config(self, conf_file):
        # Note that logging is not completely set up in this function yet. You can partially log, but not to the window.
        # See comment far below, that starts with "From here on".

        self.conf_file = conf_file
        self.config.read(self.conf_file)

        if self.config.has_option("logging", "LOG_FILE"):
            self.log_file_handler = logging.FileHandler(Path(self.config.get("logging", "LOG_FILE")))
        else:
            self.log_file_handler = logging.FileHandler(Path(expanduser('~/DCS-DynC/dync.log')))
        if self.config.has_option("logging", "LOG_FILE_LEVEL"):
            log_file_level = int(self.config.get("logging", "LOG_FILE_LEVEL")) * 10
        else:
            log_file_level = 20
        if self.config.has_option("logging", "LOG_WINDOW_LEVEL"):
            log_window_level = int(self.config.get("logging", "LOG_WINDOW_LEVEL")) * 10
        else:
            log_window_level = 30
        if self.config.has_option("logging", "LOG_CONSOLE_LEVEL"):
            log_console_level = int(self.config.get("logging", "LOG_CONSOLE_LEVEL")) * 10
        else:
            log_console_level = 20
        if self.config.has_option("comms", "URL") and self.config.has_option("comms", "USER"):
            self.messages_url = self.config.get("comms", "URL")
            self.messages_user = self.config.get("comms", "USER")

        self.log_file_handler.setLevel(log_file_level)
        self.log_file_handler.setFormatter(self.log_file_formatter)
        self.log_console_handler.setLevel(log_console_level)
        self.log_console_handler.setFormatter(self.log_console_formatter)
        self.log_window_handler.setLevel(log_window_level)
        self.log_window_handler.setFormatter(self.log_window_formatter)
        self.logger.addHandler(self.log_file_handler)
        self.logger.addHandler(self.log_console_handler)
        self.logger.addHandler(self.log_window_handler)

        # From here on, you can log to console and file, but not to the window log yet.

        self.campaign.max_infantry_in_node = int(self.config.get("campaign", "MAX_INFANTRY"))
        aa_red_list = self.config.get("campaign", "AA_RED").split(",")
        aa_blue_list = self.config.get("campaign", "AA_BLUE").split(",")
        self.campaign.allowed_aa_units["red"] = []
        self.campaign.allowed_aa_units["blue"] = []
        for item in aa_red_list:
            item_clean = item.strip().replace('"', '')
            self.campaign.allowed_aa_units["red"].append(item_clean)
        for item in aa_blue_list:
            item_clean = item.strip().replace('"', '')
            self.campaign.allowed_aa_units["blue"].append(item_clean)

    def reset_campaign(self):
        self.delete_campaign()
        self.init_campaign()
        self.read_config(self.conf_file)

    def get_graph_image(self):
        if self.campaign.map is None or self.campaign.map.graph is None:
            self.logger.warning("Cannot draw graph because some information is missing")
            return
        coords, bbox = self.campaign.map.get_nodes_in_graphical_coords()

        groups_dict = self.campaign.map.groups()
        passed_groups_dict = {}
        for group_name in groups_dict:
            group = groups_dict[group_name]
            node_id = self.campaign.map.find_group_node_by_group_name(group_name)
            if node_id not in passed_groups_dict:
                passed_groups_dict[node_id] = []
            passed_groups_dict[node_id].append({"name": group_name, "coalition": group.coalition,
                                                "type": group.category, "number": group.num_units()})

        coalitions = ("red", "blue")

        for coalition in coalitions:
            num_support = self.campaign.map.get_num_support_units(coalition)
            if num_support > 0:
                node_id = self.campaign.map.get_support_unit_node(coalition)
                if node_id not in passed_groups_dict:
                    passed_groups_dict[node_id] = []
                passed_groups_dict[node_id].append({"name": "Support", "coalition": coalition, "type": "support",
                                                    "number": num_support})
            infantry = self.campaign.map.get_infantry_in_nodes(coalition=coalition)
            for node_id in infantry:
                if node_id not in passed_groups_dict:
                    passed_groups_dict[node_id] = []
                passed_groups_dict[node_id].append({"name": "Infantry", "coalition": coalition, "type": "infantry",
                                                    "number": infantry[node_id]})

        movement_list = []
        # The internal format is that this is a dictionary in which the key is the group name, and the value is the
        # node it is traveling to. We must convert this to the format required by draw_map, which contains more
        # information. Not just for the vehicle units, but also the virtual units such as support. We put them all in
        # the same dictionary since as far as representation goes, they have no difference.
        movement_decisions = self.campaign.get_movement_decisions()
        for key in movement_decisions:
            group = self.campaign.map.find_group_by_name(key)
            origin_node = self.campaign.map.find_group_node_by_group_name(key)
            destination_node = movement_decisions[key]
            movement_list.append({"origin_node": origin_node, "destination_node": destination_node, "name": key,
                                  "type": group.category, "coalition": group.coalition})

        # There's a little hiccup here: DCS World coordinates have x in up-down and y in left-right. To get a graphichal
        # representation of the coordinates, we have to switch them around.
        graphical_coord_mapmarkers = []

        for mapmarker in self.campaign.map.mapmarkers:
            graphical_coord_mapmarkers.append({"name": mapmarker["name"],
                                               "pos": (mapmarker["pos"][1], mapmarker["pos"][0])})

        if self.campaign.map.cornermarkers is None:
            graphical_coord_cornermarkers = None
        else:
            graphical_coord_cornermarkers = []
            for cornermarker in self.campaign.map.cornermarkers:
                graphical_coord_cornermarkers.append({"pos": (cornermarker["pos"][1], cornermarker["pos"][0])})

        bullseyes = {"red": None, "blue": None}
        if self.campaign.map.red_bullseye is not None:
            bullseyes["red"] = (self.campaign.map.red_bullseye[1], self.campaign.map.red_bullseye[0])
        if self.campaign.map.blue_bullseye is not None:
            bullseyes["blue"] = (self.campaign.map.blue_bullseye[1], self.campaign.map.blue_bullseye[0])

        param_mapbg = None
        if self.display_map_background is True:
            param_mapbg = self.mapbg

        return GfxHelper.draw_map(graph=self.campaign.map.graph, coords=coords, bbox=bbox,
                                  red_goal=self.campaign.map.red_goal_node, blue_goal=self.campaign.map.blue_goal_node,
                                  groups=passed_groups_dict, movement_decisions=movement_list,
                                  paths=self.display_map_paths, mapmarkers=graphical_coord_mapmarkers,
                                  cornermarkers=graphical_coord_cornermarkers, bullseyes=bullseyes, mapbg=param_mapbg)

    def get_aa_unit_type(self, coalition):
        if coalition != "red" and coalition != "blue":
            self.logger.warning("Cannot get type for new aa-unit: Coalition must be either 'red' or 'blue'; was: '%s'" %
                                coalition)
            return None
        return np.random.choice(self.campaign.allowed_aa_units[coalition])

    def delete_campaign(self):
        try:
            os.remove(self.campaign_json)
        except OSError:
            pass
        self.campaign = None

    def missionend(self, _):
        # noinspection PyBroadException
        try:
            if self.campaign is None:
                return ""

            groups = self.campaign.map.groups()
            victory_red = False
            victory_blue = False

            if len(groups) == 0:
                self.logger.info("Draw: All units destroyed!")
                self.delete_campaign()
                return '{"code": "0", "event": "end", "result": "Draw: All units destroyed"}'

            for group_name in groups:
                group = groups[group_name]

                if group.category == "vehicle" and (group.coalition == "red" or group.coalition == "blue") and \
                        "__sg__" not in group_name:

                    node_id = int(self.campaign.map.find_group_node(group))

                    shortest_path = \
                        self.campaign.map.get_shortest_path(node_id,
                                                            self.campaign.map.get_coalition_goal(group.coalition))

                    self.logger.info("Group %s is now at node %d and shortest path is %s" %
                                     (group_name, node_id, repr(shortest_path)))

                    if group.coalition == "red":
                        enemy_coalition = "blue"
                    else:
                        enemy_coalition = "red"

                    num_enemy_infantry = \
                        self.campaign.map.get_num_coalition_infantry_in_node(enemy_coalition, node_id)

                    if num_enemy_infantry > 0:
                        num_enemy_infantry -= group.num_units()
                        if num_enemy_infantry < 0:
                            num_enemy_infantry = 0
                        self.logger.info("We have decreased the number of %s coalition infantry to %d from node %d" %
                                         (enemy_coalition, num_enemy_infantry, node_id))
                        self.campaign.map.set_infantry_in_node(enemy_coalition, node_id, num_enemy_infantry)

                    if num_enemy_infantry == 0 and shortest_path is not None and len(shortest_path) < 3:
                        if group.coalition == "red":
                            victory_red = True
                        else:
                            victory_blue = True

            if victory_red is True and victory_blue is True:
                self.logger.info("Draw: Both sides enter the other's base")
                self.delete_campaign()
                self.post_message_if_necessary("Draw: Both sides enter the other\'s base")
                return '{"code": "0", "event": "end", "result": "Draw: Both sides enter the other\'s base"}'
            elif victory_red is True:
                self.logger.info("Red coalition won")
                self.delete_campaign()
                self.post_message_if_necessary("Red coalition won")
                return '{"code": "0", "event": "end", "result": "Red coalition won"}'
            elif victory_blue is True:
                self.logger.info("Blue coalition won")
                self.delete_campaign()
                self.post_message_if_necessary("Blue coalition won")
                return '{"code": "0", "event": "end", "result": "Blue coalition won"}'

            self.campaign.stage += 1

            with open(self.campaign_json, 'w') as f:
                json.dump(self.campaign.to_serializable(), f)

            return '{"code": "0", "event": "continue"}'
        except Exception:
            self.logger.exception("Exception in missionend", exc_info=True)
            return '{"code": "1", "error": "Internal Server Error. See server logs for more information."}'

    def post_message_if_necessary(self, message):
        if self.messages_user is not None:
            MessageService.hook_post_message(username=self.messages_user, url=self.messages_url,
                                             message=message)

    def supportdestroyed(self, coalition):
        self.campaign.map.decrement_num_support_units(coalition)
        self.logger.info("Number of support units for coalition %s now %d" %
                         (coalition, self.campaign.map.get_num_support_units(coalition)))

        if self.campaign.map.get_num_support_units(coalition) <= 2:
            self.logger.info("Support for coalition %s is now considered destroyed" % coalition)

    def unitdestroyed(self, unitname, groupname):
        # noinspection PyBroadException
        try:
            self.logger.info("Destroyed unit: %s, group: %s" % (unitname, groupname))
            group = self.campaign.map.find_group_by_name(groupname)

            if group is None:
                self.logger.warning("Unit %s in group %s supposed to be destroyed, but was not found" %
                                    (unitname, groupname))
                return ""

            if unitname not in self.campaign.destroyed_unit_names_and_groups:
                self.campaign.destroyed_unit_names_and_groups[unitname] = {"group": groupname}

            for dict_unit_name in group.units:
                if dict_unit_name == unitname:
                    del group.units[dict_unit_name]
                    break
            if len(group.units) == 0:
                self.logger.info("That was group's final unit, remove group")
                if groupname in self.campaign.unit_movement_decisions:
                    del self.campaign.unit_movement_decisions[groupname]
                self.campaign.map.remove_group(group)

            with open(self.campaign_json, 'w') as f:
                json.dump(self.campaign.to_serializable(), f)

            return "ok"
        except Exception:
            self.logger.exception("Exception in unitdestroyed", exc_info=True)
            return '{"code": "1", "error": "Internal Server Error. See server logs for more information."}'

    def processjson(self, jsondata):
        # noinspection PyBroadException
        try:
            obj = json.loads(jsondata)
            routes = obj["routes"]
            units = obj["units"]
            goals = obj["goals"]
            bullseyes = obj["bullseye"]

            mapmarkers = []
            if "mapmarkers" in obj:
                for mapmarker in obj["mapmarkers"]:
                    real_name = mapmarker["name"].replace("__mm__", "")
                    # If removing __mm__ left two consecutive spaces because it was somewhere in the middle, we combine
                    real_name = real_name.replace("  ", " ")
                    split_pos = mapmarker["pos"].split(",")
                    point = euclid3.Point2(float(split_pos[0]), float(split_pos[1]))
                    mapmarkers.append({"name": real_name, "pos": (point.x, point.y)})

            cornermarkers = []
            if "cornermarkers" in obj:
                for cornermarker in obj["cornermarkers"]:
                    split_pos = cornermarker["pos"].split(",")
                    point = euclid3.Point2(float(split_pos[0]), float(split_pos[1]))
                    cornermarkers.append({"pos": (point.x, point.y)})

            if os.path.isfile(self.campaign_json) is True:
                # Note: dynamically generated units are not included by default by units_match; DCS wouldn't know about
                # them
                if self.campaign.units_match(units) is False:
                    self.logger.warning("Mismatch in units reported by DCS, and our existing campaign file. "
                                        "Resetting campaign.")
                    self.reset_campaign()
            must_update_distances = False
            # Merging the graph can be reasonably costly, so we do it only once
            if self.campaign.map.graph is None:
                self.campaign.map.graph = Map.create_merged_graph_from_routes(routes)
                must_update_distances = True

            for unit_name in units:
                received_unit = units[unit_name]

                if unit_name in self.campaign.destroyed_unit_names_and_groups:
                    continue

                unit_type = None
                if "type" in received_unit:
                    unit_type = received_unit["type"]

                if "group" in received_unit:
                    group_name = received_unit["group"]
                else:
                    self.logger.error("Corrupt JSON from DCS: Unit doesn't have group-field")

                    returndata = \
                        {"code": "1", "error": "Corrupt JSON: Unit doesn't have group-field. Your mission script is " 
                                               "incompatible with server version."}

                    return json.dumps(returndata)

                if "pos" in received_unit:
                    pos_str = received_unit["pos"]
                else:
                    self.logger.error("Corrupt JSON from DCS: Unit doesn't have pos-field")

                    returndata = \
                        {"code": "1", "error": "Corrupt JSON: Unit doesn't have pos-field. Your mission script is " 
                                               "incompatible with server version."}

                    return json.dumps(returndata)

                if "category" in received_unit:
                    unit_category = received_unit["category"]
                else:
                    self.logger.error("Corrupt JSON from DCS: Unit doesn't have category-field")

                    returndata = \
                        {"code": "1", "error": "Corrupt JSON: Unit doesn't have category-field. Your mission script is " 
                                               "incompatible with server version."}

                    return json.dumps(returndata)

                if "coalition" in received_unit:
                    unit_coalition = received_unit["coalition"]
                else:
                    self.logger.error("Corrupt JSON from DCS: Unit doesn't have coalition-field")

                    returndata = \
                        {"code": "1", "error": "Corrupt JSON: Unit doesn't have coalition-field. Your mission script "
                                               "is incompatible with server version."}

                    return json.dumps(returndata)

                split_pos = pos_str.split(",")
                point = euclid3.Point2(float(split_pos[0]), float(split_pos[1]))
                unit = self.campaign.map.find_unit_by_name(unit_name)

                if unit is None:
                    must_add_group = False
                    group = self.campaign.map.find_group_by_name(group_name)

                    if group is None:
                        # Groups always consist of units of same category, which is why we can mix group_category and
                        # unit_category. Same for type.

                        group = Group(name=group_name, group_category=unit_category, coalition=unit_coalition)
                        must_add_group = True
                    unit = Unit(name=unit_name, position=(point.x, point.y), unit_type=unit_type)
                    group.add_unit(unit)
                    if must_add_group:
                        # Note that we take a guess here about what node this group goes in, based on just one unit. But
                        # just after this loop comes update_group_nodes() and if the other units have changed the
                        # group's center so much that it moves to another node, that will happen there.
                        self.campaign.map.add_group(group)
                elif self.campaign.stage == 0:

                    # At mission start, DCS knows useful information only on stage 0. After that, the server knows the
                    # most reliable data at mission start, and DCS at mission end.
                    unit.position = (point.x, point.y)

            if self.campaign.stage == 0:
                # There is a chance that this function will change a group's node because now it has access to all the
                # units and can calculate its position better.

                self.campaign.map.update_group_nodes()

                self.campaign.map.update_goals(red_goal=goals["red"], blue_goal=goals["blue"],
                                               max_infantry_in_node=self.campaign.max_infantry_in_node)

            self.campaign.add_resources_generic("red", 1)
            self.campaign.add_resources_generic("blue", 1)

            if must_update_distances:
                self.campaign.map.update_nodes_by_distance()

            # If we have received any mapmarkers and they aren't in the map already, update the map. If the map already
            # has any markers at all, don't change it.
            if (self.campaign.map.mapmarkers is None or len(self.campaign.map.mapmarkers) == 0) and len(mapmarkers) > 0:
                self.campaign.map.mapmarkers = mapmarkers

            if (self.campaign.map.cornermarkers is None or len(self.campaign.map.cornermarkers) == 0) and \
                    len(cornermarkers) > 0:
                self.campaign.map.cornermarkers = cornermarkers

            if self.campaign.map.red_bullseye is None:
                split_pos = bullseyes["red"].split(",")
                point = euclid3.Point2(float(split_pos[0]), float(split_pos[1]))
                self.campaign.map.red_bullseye = (point.x, point.y)
            if self.campaign.map.blue_bullseye is None:
                split_pos = bullseyes["blue"].split(",")
                point = euclid3.Point2(float(split_pos[0]), float(split_pos[1]))
                self.campaign.map.blue_bullseye = (point.x, point.y)

            groups = self.campaign.map.groups()
            groups_pos = {}
            groups_dest = {}
            decisions = self.campaign.get_movement_decisions()

            # This is a bit ugly. It looks like DCS scripting has some kind of a bug where a group ignores its route if
            # it is given too early, or something else that teleporting the group appears to fix, as the problem has
            # only manifested on the first stage, and the only difference is the lack of teleporting. In order to force
            # all stages to behave the same, and thereby remove one variable in debugging this problem, we crudely make
            # the first stage teleport too, roughly to the units' original location. Note that this also means that you
            # shouldn't bother to set the individual unit positions on any groups except those that have __ig__ tag. The
            # teleporting, and the random scattering that is done while teleporting, will make it of none effect.
            if self.campaign.stage == 0:
                for group_name in groups:
                    group = groups[group_name]
                    if group is None or group.category != "vehicle" or "__sg__" in group_name:
                        continue
                    node = self.campaign.map.find_group_node_by_group_name(group_name)
                    coords = self.campaign.map.get_node_coords(node)
                    groups_pos[group_name] = "%f,%f" % (coords[0], coords[1])

            # list of dicts of the format:
            # [{ node_id: group_name, node_id: group_name}, {node_id: group_name, node_id: group_name}, ...]

            # This function finds all enemy vehicle groups in adjacent nodes. It creates a list of pairs of those
            # groups. Next, we have to check if the battle in fact happened, but this first step allows us to eliminate
            # most of the groups already. The pairs contain the nodes where the groups currently are.
            potential_battles = self.campaign.find_potential_battles()

            # So, if both moves of a list item actually get decided, the result is a battle; placing both groups
            # at the center. That is to say, if group 1 of the pair decided to move to the node of group 2 in the pair,
            # and vice versa. Both of the aforementioned conditions have to be true in order for there to be a battle.

            # We create a list of battles that fulfill both conditions of a potential battle.
            actual_battles = []

            # The AI will create this dict. Key is the node to move to, and value is a list of group names that move
            # there.
            decided_moves = {}

            # We also create a list of groups engaged in battle, so we don't move them according to the normal rules.
            groups_engaged_in_battle = []

            for group_name in decisions:
                if decisions[group_name] not in decided_moves:
                    # Remember: The key is the node where we move to.
                    decided_moves[decisions[group_name]] = []
                # And to this key, we now append the group that is moving there.
                decided_moves[decisions[group_name]].append(group_name)

            # Now we know what everyone has decided, and we know what pair of decisions result in battle. In other
            # words, decided_moves now tells us for every node, what groups have decided to move there, containing a
            # list of those group names. If no group has decided to move to a node, the node does not exist in the dict.

            # Remember: These were pairs of adjacent nodes, where and only where a battle could imaginably happen. They
            # represent the DESTINATION nodes, such that if these decisions were to happen exactly, it would result in
            # and actual battle and not just a potential one.
            for potential_battle in potential_battles:

                # There are exactly two keys in potential_battle, and they are node numbers. We make a list from them,
                # so that they would be a bit easier to refer to.
                the_nodes = list(potential_battle.keys())

                # This is the most important condition. It takes a bit of unpacking. Remember, the key of
                # potential_battle was the node ID, and the value was the group name. So, potential_battle[the_nodes[0]]
                # gives you the name of the first group, potentially moving to a dangerous destination location, and
                # same for [1]. The decided_moves[], on the other hand, tells us if it ACTUALLY moved to that location
                # and not just potentially. So, if both potential movements of the pair are found in the actual
                # movements, that and only that means a battle.
                if the_nodes[0] in decided_moves and the_nodes[1] in decided_moves and \
                        potential_battle[the_nodes[0]] in decided_moves[the_nodes[0]] and \
                        potential_battle[the_nodes[1]] in decided_moves[the_nodes[1]]:

                    # Both conditions have in fact happened. Now we just check the battle isn't already scheduled.
                    # (group1, group2) is considered equivalent to (group2, group1)

                    if (potential_battle[the_nodes[0]], potential_battle[the_nodes[1]]) not in actual_battles and \
                       (potential_battle[the_nodes[1]], potential_battle[the_nodes[0]]) not in actual_battles:

                        # Battle was not yet scheduled. Do it now.

                        self.logger.info("Scheduled a battle between %s and %s" %
                                         (potential_battle[the_nodes[0]], potential_battle[the_nodes[1]]))

                        actual_battles.append((potential_battle[the_nodes[0]], potential_battle[the_nodes[1]]))

                        # Groups engaged in battle are excluded from normal moving. So, put them in a list.
                        if potential_battle[the_nodes[0]] not in groups_engaged_in_battle:
                            groups_engaged_in_battle.append(potential_battle[the_nodes[0]])

                        if potential_battle[the_nodes[1]] not in groups_engaged_in_battle:
                            groups_engaged_in_battle.append(potential_battle[the_nodes[1]])

            # Move all the non-battle groups
            for decided_node_id in decided_moves:
                for group_name in decided_moves[decided_node_id]:
                    if group_name not in groups_engaged_in_battle:
                        group = self.campaign.map.find_group_by_name(group_name)
                        if group is None:
                            # Group has made a decision, but then died
                            continue
                        coords = self.campaign.map.get_node_coords(decided_node_id)
                        if group.dynamic is False:
                            # We only announce non-dynamic groups with groups_pos, since DCS already knows the rest of
                            # the information for this group. Dynamic groups we have to announce in full.
                            groups_pos[group_name] = "%f,%f" % (coords[0], coords[1])
                        group.force_units_pos_to_node(decided_node_id, self.campaign)

            # Note: Groups engaged in battle remain in their original nodes as far as their data goes. We'll just have
            # to see how the battle plays out during actual simulation. In the end, DCS will report back their real
            # coordinates, and that's when we correct our group's node.
            self.campaign.map.update_group_nodes()

            for battle in actual_battles:
                group1 = self.campaign.map.find_group_by_name(battle[0])
                group2 = self.campaign.map.find_group_by_name(battle[1])
                if group1 is None or group2 is None:
                    continue
                node1 = self.campaign.map.find_group_node_by_group_name(battle[0])
                node2 = self.campaign.map.find_group_node_by_group_name(battle[1])
                coords1 = self.campaign.map.get_node_coords(node1)
                coords2 = self.campaign.map.get_node_coords(node2)
                euclidcoords1 = euclid3.Point2(coords1[0], coords1[1])
                euclidcoords2 = euclid3.Point2(coords2[0], coords2[1])
                euclidcenter = (euclidcoords1 + euclidcoords2) / 2
                group1.force_units_pos_to_point((euclidcenter.x, euclidcenter.y))
                group2.force_units_pos_to_point((euclidcenter.x, euclidcenter.y))

                # We only announce non-dynamic groups with groups_pos, since DCS already knows the rest of the
                # information for this group. Dynamic groups we have to announce in full.
                if group1.dynamic is False:
                    groups_pos[group1.name] = "%f,%f" % (euclidcenter.x, euclidcenter.y)
                if group2.dynamic is False:
                    groups_pos[group2.name] = "%f,%f" % (euclidcenter.x, euclidcenter.y)

            # Positions done, if this was not stage 0. In all stages, also decide destinations.
            # Do not make decisions for aa-groups yet, that will happen in a loop after this.
            for group_name in groups:
                group = groups[group_name]

                # sg = staticgroup, aa = anti-aircraft
                if group is None or group.category != "vehicle" or "__sg__" in group_name or "__spaa__" in group_name:
                    continue

                if group.coalition == "red":
                    enemy_coalition = "blue"
                else:
                    enemy_coalition = "red"

                origin_node = self.campaign.map.find_group_node(group)

                num_enemy_infantry = \
                    self.campaign.map.get_num_coalition_infantry_in_node(enemy_coalition, origin_node)

                if num_enemy_infantry == 0:
                    node_id = decide_move(group, self.campaign.map)

                    if node_id is not None:

                        # This will also cause the groups engaged in a battle to continue pushing forward, if they
                        # survive the battle. When the mission ends, we may find some groups near their actual
                        # destination, and that's when we update their node information to there.
                        group.set_destination_node(node_id)

                        coords = self.campaign.map.get_node_coords(node_id)
                        groups_dest[group_name] = "%f,%f" % (coords[0], coords[1])
                        self.campaign.set_movement_decision(group, node_id)
                else:
                    coords = self.campaign.map.get_node_coords(origin_node)
                    groups_dest[group_name] = "%f,%f" % (coords[0], coords[1])
                    self.campaign.set_movement_decision(group, origin_node)

            # We make the decisions in random order, because theoretically the support units of both sides can compete
            # for the same node. The first one to decide will already have placed its own infantry in the node by the
            # time the second gets to make its decision, and hence that node will be ruled out.
            coalitions = ["red", "blue"]
            random.shuffle(coalitions)

            for coalition in coalitions:

                if self.campaign.map.get_num_support_units(coalition) <= 2:
                    self.logger.info("Coalition %s purchases new support" % coalition)
                    # Note: Since we increment by one every turn, and this is the first potential purchase (by design)
                    # we know we have enough resources.
                    self.campaign.decrease_resources_generic(coalition, 1)
                    self.campaign.map.set_num_support_units(coalition, self.campaign.map.max_support_units_in_group)

                    if coalition == "red":
                        node_id = self.campaign.map.get_coalition_goal("blue")
                    else:
                        node_id = self.campaign.map.get_coalition_goal("red")
                    self.campaign.map.set_support_unit_node(coalition, node_id)
                    continue

                current_node = self.campaign.map.get_support_unit_node(coalition)
                move = decide_support_move(current_node, coalition, self.campaign.map,
                                           self.campaign.max_infantry_in_node)
                if move is None:
                    self.logger.info("A %s coalition support unit has nowhere to move" % coalition)
                    continue
                self.campaign.map.set_infantry_in_node(coalition, move, self.campaign.max_infantry_in_node)
                self.campaign.map.set_support_unit_node(coalition, move)

            # Decision to purchase support takes priority. Only if we still have enough resources, do we purchase AA.

            for coalition in coalitions:
                if self.campaign.get_resources_generic(coalition) >= 2:
                    self.logger.info("Coalition %s purchases new AA unit" % coalition)
                    new_dynamic_group = Group(name="Anti-aircraft %s %d (dyn) __spaa__" %
                                                   (coalition, self.campaign.aa_unit_id_counter),
                                              group_category="vehicle", coalition=coalition, units=None, dynamic=True)
                    new_dynamic_group.add_unit(Unit(name="Anti-aircraft unit %s %d (dyn)" %
                                                         (coalition, self.campaign.aa_unit_id_counter),
                                                    unit_type=self.get_aa_unit_type(coalition), skill="Good"))
                    self.campaign.aa_unit_id_counter += 1
                    if coalition == "red":
                        node_id = self.campaign.map.get_coalition_goal("blue")
                    else:
                        node_id = self.campaign.map.get_coalition_goal("red")
                    new_dynamic_group.force_units_pos_to_node(node_id, self.campaign)
                    self.campaign.map.add_group(new_dynamic_group, node_id)
                    self.campaign.decrease_resources_generic(coalition, 2)

            # Dynamic groups may have been added, so re-reading groups.
            groups = self.campaign.map.groups()

            # Now deciding aa-groups, since we know where normal groups have moved.
            for group_name in groups:
                group = groups[group_name]

                if group is None or group.category != "vehicle" or "__spaa__" not in group_name:
                    continue

                node_id = decide_aa_move(group, self.campaign.map)

                if node_id is not None:
                    # This will also cause the groups engaged in a battle to continue pushing forward, if they survive
                    # the battle. When the mission ends, we may find some groups near their actual destination, and
                    # that's when we update their node information to there.
                    group.set_destination_node(node_id)

                    coords = self.campaign.map.get_node_coords(node_id)
                    groups_dest[group_name] = "%f,%f" % (coords[0], coords[1])
                    self.campaign.set_movement_decision(group, node_id)

            # Returns -1 if there are no threats at all
            threat_for_blue = self.campaign.map.find_greatest_threat_node(self.campaign.map.red_goal_node, "red")
            threat_for_red = self.campaign.map.find_greatest_threat_node(self.campaign.map.blue_goal_node, "blue")

            if threat_for_blue < 0 or threat_for_red < 0:
                return '{"code": "1", "error": "Mission is not playable because no threats have been defined for one ' \
                       'side or both"}'

            coords_for_blue = self.campaign.map.get_node_coords(threat_for_blue)
            coords_for_red = self.campaign.map.get_node_coords(threat_for_red)

            self.logger.info("Red support now in node %d, and blue in node %d" %
                             (self.campaign.map.get_support_unit_node("red"),
                              self.campaign.map.get_support_unit_node("blue")))

            coords_for_support_blue = self.campaign.map.get_node_coords(self.campaign.map.get_support_unit_node("blue"))
            coords_for_support_red = self.campaign.map.get_node_coords(self.campaign.map.get_support_unit_node("red"))
            infantry_pos_dict = {"red": [], "blue": []}

            for coalition in coalitions:
                infantry_in_nodes = self.campaign.map.get_infantry_in_nodes(coalition)
                for node_id in infantry_in_nodes:
                    coords = self.campaign.map.get_node_coords(node_id)
                    new_item = {"pos": "%f,%f" % (coords[0], coords[1]), "number": "%d" %
                                                                                   infantry_in_nodes[int(node_id)]}
                    infantry_pos_dict[coalition].append(new_item)

            returndata = {"code": "0", "stage": "%d" % self.campaign.stage,
                          "destroyed": self.campaign.destroyed_unit_names_and_groups,
                          "groupspos": groups_pos, "groupsdest": groups_dest,
                          "airdest": {"red": "%f,%f" % (coords_for_red[0], coords_for_red[1]),
                                      "blue": "%f,%f" % (coords_for_blue[0], coords_for_blue[1])},
                          "supportpos": {"red": "%f,%f" % (coords_for_support_red[0], coords_for_support_red[1]),
                                         "blue": "%f,%f" % (coords_for_support_blue[0], coords_for_support_blue[1])},
                          "supportnum": {"red": "%d" % self.campaign.map.get_num_support_units("red"),
                                         "blue": "%d" % self.campaign.map.get_num_support_units("blue")},
                          "infantrypos": {"red": infantry_pos_dict["red"], "blue": infantry_pos_dict["blue"]},
                          "dyngroups": self.campaign.get_all_dynamic_groups()}

            with open(self.campaign_json, 'w') as f:
                json.dump(self.campaign.to_serializable(), f)

            self.campaign_changed()

            return json.dumps(returndata)
        except Exception as e:
            self.logger.exception("Exception in processjson", exc_info=True)
            raise e

    def campaign_changed(self):
        if self.campaign.map.graph is not None:
            buf = server_obj.get_graph_image()
            self.window.update_map(buf)

    def save_image(self):

        if self.window.old_image_buffer is not None:
            self.window.old_image_buffer.seek(0)
            img = self.window.old_image_buffer.read()
            # Just to be sure, return file pointer to beginning in case some other code forgets to do it first.
            self.window.old_image_buffer.seek(0)
            path = os.path.join(Path(expanduser('~/DCS-DynC/')), "map.png")
            with open(path, 'wb') as file:
                file.write(img)
        else:
            self.logger.warning("No map has been received yet")


@Request.application
def application(request):
    global server_obj
    # Dispatcher is dictionary {<method_name>: callable}
    dispatcher["processjson"] = server_obj.processjson
    dispatcher["unitdestroyed"] = server_obj.unitdestroyed
    dispatcher["missionend"] = server_obj.missionend
    dispatcher["supportdestroyed"] = server_obj.supportdestroyed

    response = JSONRPCResponseManager.handle(
        request.data, dispatcher)
    return Response(response.json, mimetype='application/json')


class ServerThread(Thread):
    def __init__(self):
        Thread.__init__(self)

    def run(self):
        run_simple('localhost', 44444, application)
        run_simple(socket.gethostbyname(socket.gethostname()), 44445, application)


def main():
    global server_thread
    global server_obj

    user_directory = Path(expanduser('~/DCS-DynC/'))
    try:
        os.mkdir(user_directory)
    except FileExistsError:
        pass

    server_obj = DynCServer(campaign_json=os.path.join(user_directory, "campaign.json"),
                            conf_file=os.path.join(user_directory, "setup.cfg"),
                            mapbg=os.path.join(user_directory, "map-bg.dat"))
    server_thread = ServerThread()
    server_thread.daemon = True
    app = wx.App()
    frm = DyncCFrame(None, title="DynC Server", server=server_obj)
    server_obj.log_window_handler.set_window(frm)
    server_obj.window = frm
    frm.SetSize((766, 1024))
    frm.Centre()
    frm.Show()
    server_obj.post_init()

    # Remember: In CPython, threads are not genuinely parallel due to GIL. As long as everything the software does is
    # IO-bound, threads are your best option due to small memory overhead. But if you ever start doing CPU-bound things
    # here, you'll need to switch to multiprocessing. Remember: Every process will then have the entire memory footprint
    # of the software. In other words, as long as you only ever need the processing power of just one CPU core, use
    # threading.
    server_thread.start()

    socket.gethostbyname(socket.gethostname())

    # Start the event loop.
    app.MainLoop()


if __name__ == '__main__':
    main()
