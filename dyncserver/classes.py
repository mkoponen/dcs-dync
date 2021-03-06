import networkx as nx
import euclid3
import logging
import common
import constants

logger = logging.getLogger('general')


class Unit:

    @staticmethod
    def from_serializable(name, serializable_dict):
        if "position" not in serializable_dict or serializable_dict["position"] is None:
            position = (0.0, 0.0)
        else:
            position = serializable_dict["position"]
        unit_type = None
        if "type" in serializable_dict:
            unit_type = serializable_dict["type"]
        skill = "Good"
        if "skill" in serializable_dict:
            skill = serializable_dict["skill"]

        return Unit(name=name, position=position, unit_type=unit_type, skill=skill)

    def __init__(self, name, position=(0.0, 0.0), unit_type=None, skill="Good"):
        self.name = name
        self.position = position
        self.unit_type = unit_type
        self.skill = skill

    def set_position_by_str(self, point_str):
        split = point_str.split(",")

        for part in split:
            part.strip()

        self.position = (float(split[0]), float(split[1]))

    def to_serializable(self):
        return {"name": self.name, "position": self.position, "type": self.unit_type, "skill": self.skill}


class Group:

    @staticmethod
    def from_serializable(name, serializable_dict):

        if "category" not in serializable_dict:
            logger.error("Serialized group must contain the field \"category\".")
            return None
        if "coalition" not in serializable_dict:
            logger.error("Serialized group must contain the field \"coalition\".")
            return None

        units = {}
        is_dynamic = False

        if "dynamic" in serializable_dict and serializable_dict["dynamic"] is True:
            is_dynamic = True

        if "units" in serializable_dict and serializable_dict["units"] is not None:
            for unit_name in serializable_dict["units"]:
                unit_data = serializable_dict["units"][unit_name]
                unit = Unit.from_serializable(unit_name, unit_data)
                units[unit_name] = unit

        return Group(name=name, group_category=serializable_dict["category"], coalition=serializable_dict["coalition"],
                     units=units, dynamic=is_dynamic)

    def __init__(self, name, group_category, coalition, units=None, dynamic=False):
        if units is None:
            units = {}
        self.name = name
        self.category = group_category
        self.coalition = coalition
        self.units = units
        self.destination_node = None
        self.dynamic = dynamic

    def get_type(self):
        if self.units is None or len(self.units) == 0:
            return None
        # Since we know all units have the same type in a group, we use this admittedly somewhat obscure-looking line to
        # get an arbitrary unit from the dict, and then get its type.
        return next(iter(self.units.values())).unit_type

    def set_destination_node(self, node_id):
        self.destination_node = int(node_id)

    def add_unit(self, unit):
        self.units[unit.name] = unit

    def num_units(self):
        return len(list(self.units.keys()))

    def force_units_pos_to_node(self, node_id, campaign):
        node = campaign.map.graph.nodes(data=True)[int(node_id)]
        coords = (node["coord"][0], node["coord"][1])
        for unit_name in self.units:
            unit = self.units[unit_name]
            unit.set_position_by_str("%f,%f" % (coords[0], coords[1]))

    def force_units_pos_to_point(self, point):
        for unit_name in self.units:
            unit = self.units[unit_name]
            unit.set_position_by_str("%f,%f" % (point[0], point[1]))

    def to_serializable(self):

        serializable_units = {}

        for unit_name in self.units:
            serializable_units[unit_name] = self.units[unit_name].to_serializable()

        return {"name": self.name, "category": self.category, "coalition": self.coalition,
                "units": serializable_units, "dynamic": self.dynamic}

    def get_center(self):

        if len(self.units) == 0:
            return None
        euclidcenter = euclid3.Point2(0, 0)

        for unit_name in self.units:
            unit = self.units[unit_name]
            euclidpos = euclid3.Point2(unit.position[0], unit.position[1])
            euclidcenter += euclidpos
        euclidcenter /= len(self.units)
        return euclidcenter.x, euclidcenter.y

    @property
    def __str__(self):
        return self.name


class Map:

    @staticmethod
    def from_serializable(serializable_dict):

        if "graph" not in serializable_dict:
            logger.error("Serialized map must at least contain the graph.")
            return None

        graph = nx.node_link_graph(serializable_dict["graph"])

        if graph is None:
            logger.error("Graph in serializable_dict was not valid")
            return None

        new_map = Map(graph)
        new_map.groups_in_nodes = {}
        new_map.infantry_in_nodes = {}

        if "groups_in_nodes" in serializable_dict and isinstance(serializable_dict["groups_in_nodes"], dict):
            group_node_dict = serializable_dict["groups_in_nodes"]

            for node_id in group_node_dict:

                new_map.groups_in_nodes[int(node_id)] = {}

                for group_name in group_node_dict[node_id]:
                    group_data = group_node_dict[node_id][group_name]
                    group = Group.from_serializable(group_name, group_data)
                    new_map.groups_in_nodes[int(node_id)][group_name] = group

        if "infantry_in_nodes" in serializable_dict and isinstance(serializable_dict["infantry_in_nodes"], dict):
            infantry_node_dict = serializable_dict["infantry_in_nodes"]

            for node_id in infantry_node_dict:
                new_map.infantry_in_nodes[int(node_id)] = infantry_node_dict[node_id]

        if "red_goal_node" in serializable_dict:
            new_map.red_goal_node = serializable_dict["red_goal_node"]
        else:
            new_map.red_goal_node = None

        if "blue_goal_node" in serializable_dict:
            new_map.blue_goal_node = serializable_dict["blue_goal_node"]
        else:
            new_map.blue_goal_node = None

        if "red_bullseye" in serializable_dict:
            new_map.red_bullseye = serializable_dict["red_bullseye"]
        else:
            new_map.red_bullseye = None

        if "blue_bullseye" in serializable_dict:
            new_map.blue_bullseye = serializable_dict["blue_bullseye"]
        else:
            new_map.blue_bullseye = None

        # This is a reasonably lightweight operation. We can do it every time we read the JSON, instead of bloating the
        # campaign file by including a serialized form of it.

        new_map.update_nodes_by_distance()

        if "num_support_units" in serializable_dict:
            new_map.num_support_units = serializable_dict["num_support_units"]
        else:
            new_map.num_support_units = {"red": new_map.max_support_units_in_group,
                                         "blue": new_map.max_support_units_in_group}

        if "support_unit_nodes" in serializable_dict:
            new_map.support_unit_nodes = serializable_dict["support_unit_nodes"]
        else:
            new_map.support_unit_nodes = {"red": new_map.blue_goal_node, "blue": new_map.red_goal_node}

        if "mapmarkers" in serializable_dict:
            new_map.mapmarkers = serializable_dict["mapmarkers"]
        else:
            new_map.mapmarkers = []
        if "cornermarkers" in serializable_dict:
            new_map.cornermarkers = serializable_dict["cornermarkers"]
        else:
            new_map.cornermarkers = None
        if "multipliers_for_red" in serializable_dict:
            new_map.multipliers_for_red = {}
            for key in serializable_dict["multipliers_for_red"]:
                new_map.multipliers_for_red[int(key)] = serializable_dict["multipliers_for_red"][key]
        else:
            new_map.multipliers_for_red = None

        return new_map

    @staticmethod
    def create_merged_graph_from_routes(routes):
        graph = nx.Graph()
        pos = {}
        i = 0

        for route in routes:
            previous_point_index = None
            previous_point_coord = None
            for point_str in route:
                split = point_str.split(",")

                for part in split:
                    part.strip()

                point = euclid3.Point2(float(split[0]), float(split[1]))
                is_reinforcements = False
                if len(split) > 2 and split[2] == 'r':
                    is_reinforcements = True
                pos[i] = (point.x, point.y, is_reinforcements)
                graph.add_node(i)
                if previous_point_index is not None:
                    graph.add_edge(i, previous_point_index, weight=point.distance(previous_point_coord))
                previous_point_index = i
                previous_point_coord = point
                i += 1

        nx.set_node_attributes(graph, name='coord', values=pos)
        nodes = graph.nodes(data=True)

        # This will merge nodes that are 200.0 units or less away from each other
        qgraph = nx.quotient_graph(graph, lambda u, v: (
            (euclid3.Point2(nodes[u]['coord'][0], nodes[u]['coord'][1]) == euclid3.Point2(nodes[v]['coord'][0],
                                                                                          nodes[v]['coord'][1]) or
             euclid3.Point2(nodes[u]['coord'][0], nodes[u]['coord'][1]).distance(euclid3.Point2(nodes[v]['coord'][0],
                                                                                                nodes[v]['coord'][1])) <
             200.0)))

        # The quotient graph contains unnecessarily much subgraph information. We tidy it up.

        newgraph = nx.Graph()
        nodes = qgraph.nodes()

        newpos = {}

        for node in nodes:

            # If even one of the merged nodes is not a reinforcements node, the resulting node is not reinforcements.
            is_reinforcements = True
            for node_id in node:
                if pos[node_id][2] is False:
                    is_reinforcements = False
                    break

            # We just take the node ID with the smallest number from the subgraph that was contracted, and ignore the
            # rest
            newgraph.add_node(min(node))

            # We create a smaller pos-table which only contains the surviving nodes. We ignore the reinforcements tuple
            # index of the node, and substitute it with the value we determined above. Rest comes from the tuple.
            newpos[min(node)] = (pos[min(node)][0], pos[min(node)][1], is_reinforcements)

        edges = qgraph.edges(data=True)

        for edge in edges:
            # We aren't interested in the subgraphs. Again, just look at the node with the smallest ID.
            newgraph.add_edge(min(edge[0]), min(edge[1]), weight=edge[2]['weight'])

        nx.set_node_attributes(newgraph, name='coord', values=newpos)
        return newgraph

    def __init__(self, graph=None, red_goal_node=None, blue_goal_node=None):
        self.graph = graph
        self.groups_in_nodes = {}
        self.infantry_in_nodes = {}
        self.red_goal_node = red_goal_node
        self.blue_goal_node = blue_goal_node
        self.red_nodes_by_distance = {}
        self.blue_nodes_by_distance = {}
        self.support_unit_nodes = None
        self.max_support_units_in_group = 7
        self.num_support_units = {"red": self.max_support_units_in_group, "blue": self.max_support_units_in_group}
        self.mapmarkers = []
        self.cornermarkers = None
        self.red_bullseye = None
        self.blue_bullseye = None
        self.multipliers_for_red = None

    def get_num_units_in_node(self, coalition, node_id):
        if coalition != "red" and coalition != "blue":
            logger.error("Cannot get number of units: Coalition must be either 'red' or 'blue'; was: '%s'" % coalition)
            return None
        node_id = int(node_id)
        num_so_far = 0

        if node_id not in self.groups_in_nodes:
            return 0

        for group_name in self.groups_in_nodes[node_id]:
            group = self.groups_in_nodes[node_id][group_name]
            if group.coalition == coalition:
                num_so_far += group.num_units()
        return num_so_far

    def get_num_support_units(self, coalition):
        if coalition != "red" and coalition != "blue":
            logger.error("Cannot get number of support units: Coalition must be either 'red' or 'blue'; was: '%s'" %
                         coalition)
            return None
        return self.num_support_units[coalition]

    def set_num_support_units(self, coalition, number):
        if coalition != "red" and coalition != "blue":
            logger.error("Cannot set number of support units: Coalition must be either 'red' or 'blue'; was: '%s'" %
                         coalition)
            return
        self.num_support_units[coalition] = number

    def decrement_num_support_units(self, coalition):
        if coalition != "red" and coalition != "blue":
            logger.error("Cannot set number of support units: Coalition must be either 'red' or 'blue'; was: '%s'" %
                         coalition)
            return
        if self.num_support_units[coalition] < 1:
            return
        self.num_support_units[coalition] -= 1

    def update_nodes_by_distance(self):
        for node_id in self.graph.nodes:
            try:
                shortest_path_blue = nx.dijkstra_path(self.graph, self.red_goal_node, node_id)
            except nx.NetworkXNoPath:
                shortest_path_blue = None
            try:
                shortest_path_red = nx.dijkstra_path(self.graph, self.blue_goal_node, node_id)
            except nx.NetworkXNoPath:
                shortest_path_red = None

            if shortest_path_blue is not None:
                distance = len(shortest_path_blue) - 1

                if distance not in self.blue_nodes_by_distance:
                    self.blue_nodes_by_distance[distance] = []
                self.blue_nodes_by_distance[distance].append(int(node_id))
            if shortest_path_red is not None:
                distance = len(shortest_path_red) - 1
                if distance not in self.red_nodes_by_distance:
                    self.red_nodes_by_distance[distance] = []
                self.red_nodes_by_distance[distance].append(int(node_id))

    def get_nodes_in_graphical_coords(self):
        nodes = self.graph.nodes(data='coord')
        positions = {}
        min_x, max_x, min_y, max_y = None, None, None, None

        if self.cornermarkers is not None:
            for cornermarker in self.cornermarkers:
                pos = cornermarker["pos"]
                if max_y is None or max_y < pos[0]:
                    max_y = pos[0]
                if min_y is None or min_y > pos[0]:
                    min_y = pos[0]
                if max_x is None or max_x < pos[1]:
                    max_x = pos[1]
                if min_x is None or min_x > pos[1]:
                    min_x = pos[1]

        for node, value in nodes:
            positions[node] = [value[1], value[0]]
            if self.cornermarkers is None:
                if max_y is None or max_y < value[0]:
                    max_y = value[0]
                if min_y is None or min_y > value[0]:
                    min_y = value[0]
                if max_x is None or max_x < value[1]:
                    max_x = value[1]
                if min_x is None or min_x > value[1]:
                    min_x = value[1]

        for mapmarker in self.mapmarkers:
            pos = mapmarker["pos"]
            if self.cornermarkers is None:
                if max_y is None or max_y < pos[0]:
                    max_y = pos[0]
                if min_y is None or min_y > pos[0]:
                    min_y = pos[0]
                if max_x is None or max_x < pos[1]:
                    max_x = pos[1]
                if min_x is None or min_x > pos[1]:
                    min_x = pos[1]
        return positions, [min_x, max_x, min_y, max_y]

    def to_serializable(self):
        serialized_groups_in_nodes = {}
        serialized_infantry_in_nodes = {}

        for node_id in self.groups_in_nodes:
            groups = self.groups_in_nodes[int(node_id)]

            serialized_groups_in_nodes[int(node_id)] = {}
            for group_name in groups:
                group = groups[group_name]
                serialized_groups_in_nodes[int(node_id)][group_name] = group.to_serializable()
        for node_id in self.infantry_in_nodes:
            serialized_infantry_in_nodes[int(node_id)] = self.infantry_in_nodes[int(node_id)]

        serializable_graph = None
        if self.graph is not None:
            serializable_graph = nx.node_link_data(self.graph)

        return {"groups_in_nodes": serialized_groups_in_nodes, "infantry_in_nodes": serialized_infantry_in_nodes,
                "red_goal_node": self.red_goal_node, "blue_goal_node": self.blue_goal_node, "graph": serializable_graph,
                "support_unit_nodes": self.support_unit_nodes, "num_support_units": self.num_support_units,
                "mapmarkers": self.mapmarkers, "cornermarkers": self.cornermarkers, "red_bullseye": self.red_bullseye,
                "blue_bullseye": self.blue_bullseye, "multipliers_for_red": self.multipliers_for_red}

    def set_infantry_in_node(self, coalition, node_id, number):

        if coalition != "red" and coalition != "blue":
            logger.error("Cannot set infantry to node %d: Coalition must be either 'red' or 'blue'; was: '%s'" %
                         (node_id, coalition))
            return

        self.infantry_in_nodes[int(node_id)] = {"coalition": coalition, "number": number}

    def get_infantry_in_node(self, node_id):
        if node_id not in self.infantry_in_nodes:
            return None
        return self.infantry_in_nodes[int(node_id)]

    def get_infantry_in_nodes(self, coalition):
        if coalition != "red" and coalition != "blue":
            logger.error("Cannot get infantry in nodes: Coalition must be either 'red' or 'blue'; was: '%s'" %
                         coalition)
            return None
        return_dict = {}
        for node_id in self.infantry_in_nodes:
            if self.infantry_in_nodes[int(node_id)]["coalition"] == coalition:
                return_dict[int(node_id)] = self.infantry_in_nodes[int(node_id)]["number"]
        return return_dict

    def get_num_coalition_infantry_in_node(self, coalition, node_id):
        if coalition != "red" and coalition != "blue":
            logger.error("Cannot get number of coalition infantry in node %d: Coalition must be either 'red' or "
                         "'blue'; was: '%s'" % (node_id, coalition))
            return 0
        if node_id not in self.infantry_in_nodes:
            return 0
        if self.infantry_in_nodes[int(node_id)]["coalition"] != coalition:
            return 0
        return self.infantry_in_nodes[int(node_id)]["number"]

    def is_enemy_activity_in_node(self, own_coalition, node_id):

        if own_coalition != "red" and own_coalition != "blue":
            logger.error("Cannot get enemy activity from node %d: Coalition must be either 'red' or 'blue'; was: '%s'" %
                         (node_id, own_coalition))

        if own_coalition == "red":
            enemy_coalition = "blue"
        else:
            enemy_coalition = "red"

        if node_id in self.infantry_in_nodes and self.infantry_in_nodes[int(node_id)]["coalition"] == enemy_coalition:
            # There was enemy infantry in node
            return True

        if node_id in self.groups_in_nodes:
            for group_name in self.groups_in_nodes[int(node_id)]:
                group = self.groups_in_nodes[int(node_id)][group_name]
                if group.coalition == enemy_coalition:
                    # There were enemy ground force(s) in node
                    return True

        # Got here, so no enemy activity
        return False

    def add_group(self, group, node_id=None):

        if isinstance(group, Group) is False:
            logger.error("Parameter \"group\" must be of class Group in Map.add_group.")
            return False

        if node_id is None:
            center = group.get_center()

            if center is None:
                logger.error("Group must have at least one unit so we can figure out what node it goes in. "
                             "Add units first, then add group.")
                return False

            correct_node_id = self.find_node_by_center(center)
        else:
            correct_node_id = node_id

        correct_node_id = int(correct_node_id)

        for this_node_id in self.groups_in_nodes:
            groups = self.groups_in_nodes[int(this_node_id)]

            if group.name in groups:
                logger.info("Group %s already in map when calling Map.add_group" % str(group))
                return False

        # Group not already in map. Add.
        if correct_node_id not in self.groups_in_nodes:
            self.groups_in_nodes[correct_node_id] = {}

        self.groups_in_nodes[correct_node_id][group.name] = group

    def find_group_node_by_group_name(self, group_name):
        for node_id in self.groups_in_nodes:
            groups_in_node = self.groups_in_nodes[int(node_id)]

            if group_name in groups_in_node:
                return int(node_id)

        return None

    def find_group_node(self, group):

        if isinstance(group, Group) is False:
            logger.error("Parameter \"group\" must be of class Group in Map.find_group_node")
            return None

        name = group.name

        return self.find_group_node_by_group_name(name)

    def remove_group(self, group):

        for node_id in self.groups_in_nodes:
            groups_in_node = self.groups_in_nodes[int(node_id)]

            if group.name in groups_in_node:
                del groups_in_node[group.name]
                return True

        logger.warning("Group by name %s was not found when removing group." % group.name)
        return False

    def find_group_by_name(self, group_name):
        for node_id in self.groups_in_nodes:
            groups_in_node = self.groups_in_nodes[int(node_id)]

            if group_name in groups_in_node:
                return groups_in_node[group_name]

        return None

    def find_unit_by_name(self, unit_name):

        groups_dict = self.groups()

        for group_name in groups_dict:
            group = groups_dict[group_name]

            if unit_name in group.units:
                return group.units[unit_name]

        return None

    def get_shortest_path(self, source_node_id, target_node_id):

        try:
            path = nx.dijkstra_path(self.graph, source_node_id, target_node_id)
        except nx.NetworkXNoPath:
            return None

        return path

    def groups(self):
        groups_dict = {}

        for node_id in self.groups_in_nodes:
            for group_name in self.groups_in_nodes[int(node_id)]:
                group = self.groups_in_nodes[int(node_id)][group_name]
                groups_dict[group.name] = group

        return groups_dict

    def unit_and_group_names(self):

        # Key is unit name, value is group name
        units_dict = {}

        for node_id in self.groups_in_nodes:
            for group_name in self.groups_in_nodes[int(node_id)]:
                group = self.groups_in_nodes[int(node_id)][group_name]
                for unit_name in group.units:
                    units_dict[unit_name] = {"groupname": group_name}

    def get_coalition_goal(self, coalition):
        if coalition == "red":
            return self.red_goal_node
        elif coalition == "blue":
            return self.blue_goal_node
        else:
            logger.error("Unknown coalition: %s" % repr(coalition))
            return None

    def find_node_by_center(self, center):
        euclidcenter = euclid3.Point2(center[0], center[1])
        smallest_distance = 99999999.0
        nearest_node_index = None

        for node in self.graph.nodes(data=True):
            node2d = euclid3.Point2(node[1]["coord"][0], node[1]["coord"][1])

            if euclidcenter == node2d:
                nearest_node_index = node[0]
                break
            dist = euclidcenter.distance(node2d)

            if dist < smallest_distance:
                smallest_distance = dist
                nearest_node_index = node[0]

        if nearest_node_index is None:
            return None
        else:
            return int(nearest_node_index)

    def update_group_nodes(self):
        groups = self.groups()

        for group_name in groups:
            group = groups[group_name]
            center = group.get_center()

            new_node = self.find_node_by_center(center)
            old_node = self.find_group_node_by_group_name(group_name)

            if old_node is not None and old_node in self.groups_in_nodes and old_node != new_node:
                del self.groups_in_nodes[int(old_node)][group_name]
                if len(self.groups_in_nodes[int(old_node)]) == 0:
                    del self.groups_in_nodes[int(old_node)]
            if old_node != new_node:
                if new_node not in self.groups_in_nodes:
                    self.groups_in_nodes[int(new_node)] = {}
                self.groups_in_nodes[int(new_node)][group_name] = group

    def update_goals(self, red_goal, blue_goal, max_infantry_in_node):

        correct_coalition = "red"
        while True:
            if correct_coalition == "red":
                correct_goal = red_goal
            else:
                correct_goal = blue_goal

            split = correct_goal.split(",")
            for part in split:
                part.strip()
            euclidpoint = euclid3.Point2(float(split[0]), float(split[1]))
            smallest_distance = 99999999.0
            nearest_node_index = None

            for node_id in self.graph.nodes(data=True):
                dist = euclidpoint.distance(euclid3.Point2(node_id[1]["coord"][0], node_id[1]["coord"][1]))

                if dist < smallest_distance:
                    smallest_distance = dist
                    nearest_node_index = node_id[0]
            if correct_coalition == "red":
                self.red_goal_node = int(nearest_node_index)
                correct_coalition = "blue"
            else:
                self.blue_goal_node = int(nearest_node_index)
                break

        # Bases are always considered to hold maximum infantry, so that service will never consider refilling them.
        # Infantry in bases is useless because the game will already have ended before it would be considered.
        self.infantry_in_nodes[self.red_goal_node] = {"coalition": "blue", "number": max_infantry_in_node}
        self.infantry_in_nodes[self.blue_goal_node] = {"coalition": "red", "number": max_infantry_in_node}
        self.support_unit_nodes = {"red": int(self.blue_goal_node), "blue": int(self.red_goal_node)}

    def get_support_unit_node(self, coalition):
        if coalition != "red" and coalition != "blue":
            logger.error("Cannot get support unit node: Coalition must be either 'red' or 'blue'; was: '%s'" %
                         coalition)
            return None
        if self.support_unit_nodes[coalition] is None:
            return None
        else:
            return int(self.support_unit_nodes[coalition])

    def set_support_unit_node(self, coalition, node_id):
        if coalition != "red" and coalition != "blue":
            logger.error("Cannot set support unit node: Coalition must be either 'red' or 'blue'; was: '%s'" %
                         coalition)
            return
        self.support_unit_nodes[coalition] = int(node_id)

    def get_node_coords(self, node_id):
        coords = nx.get_node_attributes(self.graph, "coord")
        coord = coords[int(node_id)]
        node_coord = (coord[0], coord[1])
        return node_coord

    def is_node_reinforcements_path(self, node_id):
        return nx.get_node_attributes(self.graph, "coord")[int(node_id)][2]

    def get_longest_distance(self, coalition, include_reinforcement=True):
        if coalition == "red":
            correct_dict = self.red_nodes_by_distance
        else:
            correct_dict = self.blue_nodes_by_distance
        if include_reinforcement is False:
            # We create this dictionary anew, so that it doesn't even have distance keys for node lists that only have
            # reinforcement nodes.
            temp_dict = {}
            for distance in correct_dict:
                has_key = False
                for node_id in correct_dict[distance]:
                    if self.is_node_reinforcements_path(node_id) is False:
                        # Found at least one non-reinforcements node. Must add key.
                        if not has_key:
                            temp_dict[distance] = [node_id]
                            has_key = True
                        else:
                            temp_dict[distance].append(node_id)
            correct_dict = temp_dict

        distances = list(correct_dict.keys())
        return int(max(distances))

    def get_nodes_by_distance(self, coalition, distance, include_reinforcement=True):

        if coalition != "red" and coalition != "blue":
            logger.error("Cannot get nodes by distance: Coalition must be either 'red' or 'blue'; was: '%s'" %
                         coalition)
            return

        if coalition == "red":
            correct_dict = self.red_nodes_by_distance
        else:
            correct_dict = self.blue_nodes_by_distance

        if include_reinforcement is False:
            # We create this dictionary anew, so that it doesn't even have distance keys for node lists that only have
            # reinforcement nodes.
            temp_dict = {}
            for distance_key in correct_dict:
                has_key = False
                for node_id in correct_dict[distance_key]:
                    if self.is_node_reinforcements_path(node_id) is False:
                        # Found at least one non-reinforcements node. Must add key.
                        if not has_key:
                            temp_dict[distance_key] = [node_id]
                            has_key = True
                        else:
                            temp_dict[distance_key].append(node_id)
            correct_dict = temp_dict

        if distance not in correct_dict:
            return []
        return correct_dict[distance]

    def find_furtherst_own_groups_nodes(self, coalition):
        for distance in range(self.get_longest_distance(coalition, include_reinforcement=False), -1, -1):
            nodes = []
            for node_id in self.get_nodes_by_distance(coalition, distance, include_reinforcement=False):
                if self.get_num_units_in_node(coalition, int(node_id)) > 0:
                    nodes.append(int(node_id))
            if len(nodes) == 0:
                continue
            return nodes

    def find_greatest_threat_node(self, enemy_objective_node_id, enemy_coalition):
        potential_threats = {}
        if enemy_coalition == "red":
            this_coalition = "blue"
        else:
            this_coalition = "red"
        for node_id in self.groups_in_nodes:
            for group_name in self.groups_in_nodes[int(node_id)]:
                group = self.groups_in_nodes[int(node_id)][group_name]

                if group.coalition == enemy_coalition and group.category == "vehicle":
                    if node_id not in potential_threats:
                        # First number: number of threats. Second number: shortest path length to node
                        potential_threats[int(node_id)] = [1, 0]
                    else:
                        potential_threats[int(node_id)][0] += 1
                    try:
                        path = nx.dijkstra_path(self.graph, enemy_objective_node_id, node_id)
                    except nx.NetworkXNoPath:
                        continue
                    potential_threats[int(node_id)][1] = len(path)
        if len(potential_threats) == 0:
            logger.info("No threats at all from the part of %s coalition" % enemy_coalition)
            return -1

        logger.debug("Threats from the part of %s coalition: %s" % (enemy_coalition, repr(potential_threats)))
        ordered_threats = []

        for node_id in potential_threats:
            ordered_threats.append((int(node_id), potential_threats[int(node_id)][0],
                                    potential_threats[int(node_id)][1]))
        ordered_threats = sorted(ordered_threats, key=lambda x: (x[2], -x[1]))
        coords = self.get_node_coords(ordered_threats[0][0])
        logger.info("Greatest threat from %s towards %s: node %d, coordinates %f,%f" %
                    (enemy_coalition, this_coalition, ordered_threats[0][0], coords[0], coords[1]))
        return int(ordered_threats[0][0])

    def get_node_extra_multiplier(self, node_id, coalition):
        red = self.red_goal_node
        blue = self.blue_goal_node
        try:
            path_to_red = nx.dijkstra_path(self.graph, node_id, red)
        except nx.NetworkXNoPath:
            return None
        try:
            path_to_blue = nx.dijkstra_path(self.graph, node_id, blue)
        except nx.NetworkXNoPath:
            return None
        if len(path_to_red) <= 2:
            return 1.0
        if len(path_to_blue) <= 2:
            return 0.0
        multiplier_for_red = (len(path_to_blue)-2.0) / ((len(path_to_red)-2.0) + (len(path_to_blue)-2.0))
        if coalition == "red":
            return multiplier_for_red
        elif coalition == "blue":
            return 1.0 - multiplier_for_red
        else:
            return None


class Campaign:

    @staticmethod
    def is_compatible(campaign_json):
        if "software_version" not in campaign_json or campaign_json["software_version"] is None:
            return False
        campaign_num = common.version_string_to_number(campaign_json["software_version"])
        if campaign_num is None:
            logger.error("Invalid app version number in campaign file '%s'. Assuming campaign is incompatible." %
                         campaign_json["software_version"])

        compatibility_num = common.version_string_to_number(constants.backwards_compatibility_min_version)
        if compatibility_num is None:
            logger.error("This app version has an invalid compatibility version number, which is a bug. For now, "
                         "assuming campaign is incompatible." % constants.backwards_compatibility_min_version)
            return False

        return campaign_num >= compatibility_num

    @staticmethod
    def from_serializable(serializable_dict):
        if "map" not in serializable_dict or serializable_dict["map"] is None:
            logger.error("Serialized campaign must contain the field \"map\" and it must not be None.")
            return None
        new_map = Map.from_serializable(serializable_dict["map"])

        if new_map is None:
            logger.error("campaign[\"map\"] could not be decoded. Data corruption?")
            return None
        stage = 0
        destroyed_unit_names_and_groups = {}
        resources_generic = None

        if "stage" in serializable_dict and serializable_dict["stage"] is not None:
            stage = serializable_dict["stage"]

        if "destroyed_unit_names_and_groups" in \
                serializable_dict and serializable_dict["destroyed_unit_names_and_groups"] is not None:
            destroyed_unit_names_and_groups = serializable_dict["destroyed_unit_names_and_groups"]

        if "resources_generic" in serializable_dict and serializable_dict["resources_generic"] is not None:
            resources_generic = serializable_dict["resources_generic"]

        if "unit_movement_decisions" in serializable_dict and serializable_dict["unit_movement_decisions"] is not None:
            unit_movement_decisions = serializable_dict["unit_movement_decisions"]
        else:
            unit_movement_decisions = {}

        if "aa_unit_id_counter" in serializable_dict and serializable_dict["aa_unit_id_counter"] is not None:
            aa_unit_id_counter = serializable_dict["aa_unit_id_counter"]
        else:
            aa_unit_id_counter = 1

        if "allowed_aa_units" in serializable_dict and serializable_dict["allowed_aa_units"] is not None:
            allowed_aa_units = serializable_dict["allowed_aa_units"]
        else:
            allowed_aa_units = None
        if "extra_scores" in serializable_dict and serializable_dict["extra_scores"] is not None:
            extra_scores = serializable_dict["extra_scores"]
        else:
            extra_scores = None
        if "software_version" in serializable_dict and serializable_dict["software_version"] is not None:
            software_version = serializable_dict["software_version"]
        else:
            software_version = "0.0.0.0"

        return Campaign(stage=stage, game_map=new_map, destroyed_unit_names_and_groups=destroyed_unit_names_and_groups,
                        resources_generic=resources_generic, unit_movement_decisions=unit_movement_decisions,
                        aa_unit_id_counter=aa_unit_id_counter, allowed_aa_units=allowed_aa_units,
                        extra_scores=extra_scores, software_version=software_version)

    def __init__(self, game_map, stage=0, destroyed_unit_names_and_groups=None, resources_generic=None,
                 unit_movement_decisions=None, aa_unit_id_counter=1, allowed_aa_units=None, extra_scores=None,
                 software_version=None):
        if destroyed_unit_names_and_groups is None:
            destroyed_unit_names_and_groups = {}
        if unit_movement_decisions is None:
            unit_movement_decisions = {}
        if software_version is None:
            software_version = "0.0.0.0"
        self.stage = stage
        self.map = game_map
        self.destroyed_unit_names_and_groups = destroyed_unit_names_and_groups
        self.max_infantry_in_node = 4
        self.software_version = software_version
        if allowed_aa_units is None:
            self.allowed_aa_units = {"red": [], "blue": []}
        else:
            self.allowed_aa_units = allowed_aa_units
        if extra_scores is None:
            self.extra_scores = {"red": 0, "blue": 0}
        else:
            self.extra_scores = extra_scores
        self.aa_unit_id_counter = aa_unit_id_counter
        if resources_generic is not None:
            self.resources_generic = resources_generic
        else:
            self.resources_generic = {"red": 0, "blue": 0}
        self.unit_movement_decisions = unit_movement_decisions
        self.early_battles = set()
        self.engagements = []
        self.deaths = []
        self.group_data_mission_start = {}

    # Argument previously_scheduled is a set or list of group_names that have already been moved away from this apparent
    # node, to halfway point between some two nodes. Hence they will not participate.
    def get_battles_due_to_same_node(self, previously_scheduled=None):
        battles = set()
        if previously_scheduled is None:
            previously_scheduled = set()
        elif isinstance(previously_scheduled, list):
            previously_scheduled = set(previously_scheduled)
        elif isinstance(previously_scheduled, set) is False:
            logger.error('"previously_scheduled" to get_battles_due_to_same_node must be set, list or None.')
            previously_scheduled = set()

        for node_id in self.map.groups_in_nodes:
            encountered_coalitions = set()
            potential_group_names = set()
            for group_name in self.map.groups_in_nodes[node_id]:
                if group_name in previously_scheduled:
                    continue
                group = self.map.groups_in_nodes[node_id][group_name]
                coalition = group.coalition
                potential_group_names.add(group_name)
                if (coalition == "red" or coalition == "blue") and coalition not in encountered_coalitions:
                    encountered_coalitions.add(group.coalition)
            if len(encountered_coalitions) > 1:
                # Contains both coalitions, so now all groups in the node make up a battle. We take potential groups to
                # actual groups
                battle = Battle(nodes={node_id})
                battle.add_group_names(potential_group_names)
                battles.add(battle)
        return battles

    def add_battle_to_battles(self, battle):
        if isinstance(battle, Battle):
            self.early_battles.add(battle)
        else:
            logger.error("The argument \"battle\" to add_battle_to_battles must be Battle-object.")

    def add_to_battles(self, nodes, group_name):

        found = False
        for battle in self.early_battles:
            if battle.nodes == nodes:
                battle.add_group_name(group_name)
                found = True
                break
        if found is False:
            self.early_battles.add(Battle(nodes=nodes, group_names={group_name}))

    def add_resources_generic(self, coalition, number):
        if coalition != "red" and coalition != "blue":
            logger.error("Cannot add generic resources: Coalition must be either 'red' or 'blue'; was: '%s'" %
                         coalition)
            return
        self.resources_generic[coalition] += int(number)

    def set_movement_decision(self, group, node_id):
        self.unit_movement_decisions[group.name] = int(node_id)

    def get_movement_decisions(self):
        return self.unit_movement_decisions

    def get_resources_generic(self, coalition):
        if coalition != "red" and coalition != "blue":
            logger.error("Cannot get generic resources: Coalition must be either 'red' or 'blue'; was: '%s'" %
                         coalition)
            return None
        return self.resources_generic[coalition]

    def decrease_resources_generic(self, coalition, amount):
        if coalition != "red" and coalition != "blue":
            logger.error("Cannot get generic resources: Coalition must be either 'red' or 'blue'; was: '%s'" %
                         coalition)
            return False
        if self.resources_generic[coalition] < amount:
            logger.info("Not enough resources for coalition %s; had %d and tried to pay %d" %
                        (coalition, amount, self.resources_generic[coalition]))
            return False
        self.resources_generic[coalition] -= amount
        return True

    def count_units(self, include_destroyed=True, include_dynamic=False):
        units_so_far = 0
        groups_dict = self.map.groups()

        for group_name in groups_dict:
            group = groups_dict[group_name]
            if group.dynamic is False or include_dynamic is True:
                units_so_far += len(group.units)

        if include_destroyed:
            units_so_far += len(self.destroyed_unit_names_and_groups)

        return units_so_far

    def get_all_dynamic_groups(self):
        group_data = {"red": [], "blue": []}
        groups_dict = self.map.groups()
        for group_name in groups_dict:
            group = groups_dict[group_name]

            if group.dynamic is True:
                unit_list = []
                for unit_name in group.units:
                    unit = group.units[unit_name]
                    pos_str = "%f,%f" % (unit.position[0], unit.position[1])
                    unit_list.append({"name": unit_name, "type": unit.unit_type, "skill": unit.skill, "pos": pos_str})
                group_data[group.coalition].append({"category": group.category, "name": group_name, "units": unit_list})

        return group_data

    def get_all_unit_data(self, include_destroyed=True, include_dynamic=False):
        unit_data = {}
        groups_dict = self.map.groups()
        for group_name in groups_dict:
            group = groups_dict[group_name]

            if group.dynamic is False or include_dynamic is True:
                for unit_name in group.units:
                    unit_data[unit_name] = {"group": group_name}

        if include_destroyed:
            for unit_name in self.destroyed_unit_names_and_groups:
                unit_data[unit_name] = {"group": self.destroyed_unit_names_and_groups[unit_name]["group"]}

        return unit_data

    def units_match(self, reported_units):
        if len(reported_units) != self.count_units(include_destroyed=True):
            logger.info("Number of units don't match between expected and reported")
            return False

        unit_data = self.get_all_unit_data(include_destroyed=True, include_dynamic=False)

        for unit_name in reported_units:
            if unit_name not in unit_data:
                logger.info("Found a unit name mismatch between expected and reported")
                return False

            if reported_units[unit_name]["group"] != unit_data[unit_name]["group"]:
                logger.error("Found a unit name where group names mismatch between expected and reported")
                return False

        return True

    def find_potential_battles(self):

        # Finds all adjacent enemy groups of vehicles. Only these groups could potentially engage in a battle in this
        # turn, as units only travel one segment. Getting included does not yet mean that the battle in fact happens.
        # Note that the pairs generated are not where the groups currently are, but in the movement decisions such that
        # if they were to happen, would result in battle. The second stage of the process is to check that they in fact
        # happened. That is outside the scope of this function.
        potential_battles = []

        for node_id in self.map.groups_in_nodes:
            for group_name in self.map.groups_in_nodes[int(node_id)]:
                group = self.map.groups_in_nodes[int(node_id)][group_name]
                if group.category != "vehicle":
                    continue
                adjacent = self.map.graph[node_id]
                for node_id2 in adjacent:
                    if node_id2 in self.map.groups_in_nodes:
                        for group_name2 in self.map.groups_in_nodes[int(node_id2)]:
                            if {int(node_id2): group_name, int(node_id): group_name2} in potential_battles:
                                # Already in the list, no need to add again.
                                continue
                            group2 = self.map.groups_in_nodes[int(node_id2)][group_name2]
                            if group2.category != "vehicle":
                                continue
                            if group2.coalition != group.coalition:
                                # Not yet in list, are opposing coalitions, and are adjacent. Only now add to list.
                                # again, note the order in which we add them, comparing keys to values: 1 to 2 and 2 to
                                # 1. That is because this doesn't represent current locations, but the dangerous
                                # destination locations.
                                potential_battles.append({int(node_id2): group_name, int(node_id): group_name2})

        return potential_battles

    def to_serializable(self):
        serializable_map = None
        if self.map is not None:
            serializable_map = self.map.to_serializable()

        return {"stage": self.stage, "map": serializable_map,
                "destroyed_unit_names_and_groups": self.destroyed_unit_names_and_groups,
                "resources_generic": self.resources_generic, "unit_movement_decisions": self.unit_movement_decisions,
                "aa_unit_id_counter": self.aa_unit_id_counter, "allowed_aa_units": self.allowed_aa_units,
                "extra_scores": self.extra_scores, "software_version": self.software_version}


class Battle:
    def __init__(self, nodes=None, group_names=None):
        if nodes is None:
            self.nodes = set()
        elif isinstance(nodes, set) is False:
            logger.error("The argument \"nodes\" to the class Battle contructor must be None or a set.")
            self.nodes = set()
        else:
            self.nodes = nodes
        if group_names is None:
            self.group_names = set()
        elif isinstance(group_names, set) is False:
            logger.error("The argument \"group_names\" to the class Battle contructor must be None or a set.")
            self.group_names = set()
        else:
            self.group_names = group_names

    def __repr__(self):
        return "Battle(Nodes=%s, groups=%s)" % (repr(self.nodes), repr(self.group_names))

    def add_group_name(self, group_name):
        if group_name not in self.group_names:
            self.group_names.add(group_name)

    def add_group_names(self, group_names):
        if isinstance(group_names, list):
            self.group_names = self.group_names | set(group_names)
        elif isinstance(group_names, set):
            self.group_names = self.group_names | group_names
        else:
            logger.error("The argument \"group_names\" to add_group_names in Battle must be a set or list.")
