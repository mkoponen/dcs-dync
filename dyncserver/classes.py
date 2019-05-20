import networkx as nx
import euclid3
import logging

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
                pos[i] = (point.x, point.y)
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

            # We just take the node ID with the smallest number from the subgraph that was contracted, and ignore the
            # rest
            newgraph.add_node(min(node))

            # We create a smaller pos-table which only contains the surviving nodes
            newpos[min(node)] = pos[min(node)]

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

    def get_num_units_in_node(self, coalition, node_id):
        if coalition != "red" and coalition != "blue":
            logger.error("Cannot get number of support units: Coalition must be either 'red' or 'blue'; was: '%s'" %
                         coalition)
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

        for node, value in nodes:
            positions[node] = [value[1], value[0]]
            if max_y is None or max_y < value[0]:
                max_y = value[0]
            if min_y is None or min_y > value[0]:
                min_y = value[0]
            if max_x is None or max_x < value[1]:
                max_x = value[1]
            if min_x is None or min_x > value[1]:
                min_x = value[1]
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
                "support_unit_nodes": self.support_unit_nodes, "num_support_units": self.num_support_units}

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

    def get_longest_distance(self, coalition):
        if coalition == "red":
            correct_dict = self.red_nodes_by_distance
        else:
            correct_dict = self.blue_nodes_by_distance
        distances = list(correct_dict.keys())
        return int(max(distances))

    def get_nodes_by_distance(self, coalition, distance):

        if coalition != "red" and coalition != "blue":
            logger.error("Cannot get nodes by distance: Coalition must be either 'red' or 'blue'; was: '%s'" %
                         coalition)
            return

        if coalition == "red":
            correct_dict = self.red_nodes_by_distance
        else:
            correct_dict = self.blue_nodes_by_distance

        if distance not in correct_dict:
            return []
        return correct_dict[distance]

    def find_furtherst_own_groups_nodes(self, coalition):
        for distance in range(self.get_longest_distance(coalition), -1, -1):
            nodes = []
            for node_id in self.get_nodes_by_distance(coalition, distance):
                if self.get_num_units_in_node(coalition, int(node_id)) > 0:
                    nodes.append(int(node_id))
            if len(nodes) == 0:
                continue
            return nodes

    def find_greatest_threat_node(self, enemy_objective_node_id, enemy_coalition):
        potential_threats = {}
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

        logger.info("Threats from the part of %s coalition: %s" % (enemy_coalition, repr(potential_threats)))
        ordered_threats = []

        for node_id in potential_threats:
            ordered_threats.append((int(node_id), potential_threats[int(node_id)][0],
                                    potential_threats[int(node_id)][1]))
        ordered_threats = sorted(ordered_threats, key=lambda x: (x[2], -x[1]))
        coords = self.get_node_coords(ordered_threats[0][0])
        logger.info("Greatest threat: node %d, coordinates %f,%f" % (ordered_threats[0][0], coords[0], coords[1]))
        return int(ordered_threats[0][0])


class Campaign:

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

        return Campaign(stage=stage, game_map=new_map, destroyed_unit_names_and_groups=destroyed_unit_names_and_groups,
                        resources_generic=resources_generic, unit_movement_decisions=unit_movement_decisions,
                        aa_unit_id_counter=aa_unit_id_counter, allowed_aa_units=allowed_aa_units)

    def __init__(self, game_map, stage=0, destroyed_unit_names_and_groups=None, resources_generic=None,
                 unit_movement_decisions=None, aa_unit_id_counter=1, allowed_aa_units=None):
        if destroyed_unit_names_and_groups is None:
            destroyed_unit_names_and_groups = {}
        if unit_movement_decisions is None:
            unit_movement_decisions = {}
        self.stage = stage
        self.map = game_map
        self.destroyed_unit_names_and_groups = destroyed_unit_names_and_groups
        self.max_infantry_in_node = 4
        if allowed_aa_units is None:
            self.allowed_aa_units = {"red": [], "blue": []}
        else:
            self.allowed_aa_units = allowed_aa_units
        self.aa_unit_id_counter = aa_unit_id_counter
        if resources_generic is not None:
            self.resources_generic = resources_generic
        else:
            self.resources_generic = {"red": 0, "blue": 0}
        self.unit_movement_decisions = unit_movement_decisions

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
                                continue
                            group2 = self.map.groups_in_nodes[int(node_id2)][group_name2]
                            if group2.category != "vehicle":
                                continue
                            if group2.coalition != group.coalition:
                                # logger.info("Potential battle between groups %s, entering to %d and %s, entering to "
                                #             "%d " % (group_name, node_id2, group_name2, node_id))
                                potential_battles.append({int(node_id2): group_name, int(node_id): group_name2})

        return potential_battles

    def to_serializable(self):
        serializable_map = None
        if self.map is not None:
            serializable_map = self.map.to_serializable()

        return {"stage": self.stage, "map": serializable_map,
                "destroyed_unit_names_and_groups": self.destroyed_unit_names_and_groups,
                "resources_generic": self.resources_generic, "unit_movement_decisions": self.unit_movement_decisions,
                "aa_unit_id_counter": self.aa_unit_id_counter, "allowed_aa_units": self.allowed_aa_units}
