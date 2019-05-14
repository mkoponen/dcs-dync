import networkx as nx
import numpy as np
import euclid3
import random
import logging

logger = logging.getLogger('general')


def decide_move(group, game_map):

    if group.category != "vehicle":
        return None

    if group.name.startswith("staticgroup"):
        return None

    node_id = game_map.find_group_node(group)

    if node_id is None:
        logger.error("The group %s is not on the game map." % str(group))
        return None

    if game_map.red_goal_node is None or game_map.blue_goal_node is None:
        logger.error("Must set goal nodes for both sides until can call decide_move.")
        return None

    if group.coalition == "red":
        correct_goal = game_map.red_goal_node
    else:
        correct_goal = game_map.blue_goal_node

    origin_coords = game_map.get_node_coords(node_id)
    origin_coords = euclid3.Point2(origin_coords[0], origin_coords[1])
    goal_coords = game_map.get_node_coords(correct_goal)
    goal_coords = euclid3.Point2(goal_coords[0], goal_coords[1])

    neighbor_paths = []
    path_pairs = []

    for neighbor in game_map.graph[node_id]:
        if neighbor == correct_goal:
            return int(correct_goal)
        shortest_path_to_goal = game_map.get_shortest_path(neighbor, correct_goal)

        # Ignore paths that return to the node we are in
        if shortest_path_to_goal is not None and node_id not in shortest_path_to_goal:
            neighbor_paths.append(shortest_path_to_goal)

    if len(neighbor_paths) == 0:
        logger.warning("No path to goal found for group %s" % str(group))
        return None

    if len(neighbor_paths) == 1:
        return int(neighbor_paths[0][0])

    # We try to identify the REALLY stupid choices before we randomize our actual choice
    forbidden_nodes = []

    length = len(neighbor_paths)

    # A bit complicated algorithm. Creates a list of all possible pairs of different paths and truncates them to the
    # nearest common node. The i and j -parts of the for loops are the traditional way to compare pairs with least
    # amount of work. (Don't compare item with itself, and don't compare a to b, and then b to a.
    for i in range(length - 1):
        for j in range(i + 1, length):

            # The previous two loops compared paths. The next two loops compare nodes in paths.
            found_intersection = False
            for k in range(0, len(neighbor_paths[i])):
                for l in range(0, len(neighbor_paths[j])):
                    if neighbor_paths[i][k] == neighbor_paths[j][l]:
                        path_pairs.append((neighbor_paths[i][:k+1], neighbor_paths[j][:l+1]))
                        found_intersection = True
                        break
                if found_intersection:
                    break

    # Compares all the pairs, and forbids all nodes where there is such a pair that the divergent part is one third
    # longer for the to-be-forbidden path, than the shorter path. This prevents any dumb detours from happening.
    for pair in path_pairs:

        # This allows us to trivially calculate the path length
        tmpgraph1 = game_map.graph.subgraph(pair[0])
        tmpgraph2 = game_map.graph.subgraph(pair[1])
        size1 = tmpgraph1.size(weight='weight')
        size2 = tmpgraph2.size(weight='weight')

        if size1 >= 1.33 * size2:
            # Found a dumb detour. Forbid.
            if pair[0][0] not in forbidden_nodes:
                forbidden_nodes.append(pair[0][0])
        elif size2 >= 1.33 * size1:
            # ditto
            if pair[1][0] not in forbidden_nodes:
                forbidden_nodes.append(pair[1][0])

    node_is_backtrack = {}
    choices = []
    allow_backtrack = True

    for path in neighbor_paths:
        if path[0] not in forbidden_nodes:
            is_backtrack = False
            dest_coords = game_map.get_node_coords(path[0])
            dest_coords = euclid3.Point2(dest_coords[0], dest_coords[1])

            if dest_coords.distance(goal_coords) > origin_coords.distance(goal_coords):
                # Making this move would mean backtracking
                is_backtrack = True
            else:
                # We found at least one node which doesn't constitute backtracking. Hence we disallow all moves that do
                allow_backtrack = False
            node_is_backtrack[path[0]] = is_backtrack
            choices.append(path[0])

    if allow_backtrack is False:
        choices = [node for node in choices if node_is_backtrack[node] is False]

    decision = np.random.choice(choices)
    extra_info = ""
    if node_is_backtrack[decision] is True:
        extra_info = "(which is backtracking)"

    logger.info("Final decision for %s: move to node %d. %s" % (group.name, decision, extra_info))

    if decision is None:
        return None
    else:
        return int(decision)


def find_aa_target_node(group, game_map):
    logger.info("Deciding target node for aa group %s" % group.name)
    furthest_nodes = game_map.find_furtherst_own_groups_nodes(group.coalition)

    if furthest_nodes is None or len(furthest_nodes) == 0:
        logger.error("Bug: Cannot find nodes furthest away from own base for coalition %s" % group.coalition)
        return None

    random.shuffle(furthest_nodes)

    if group.coalition == "red":
        enemy_coalition = "blue"
    else:
        enemy_coalition = "red"

    max_advantage = -999
    node_with_max_advantage = None

    for node_id in furthest_nodes:
        this_advantage = game_map.get_num_units_in_node(group.coalition, node_id) - \
                         game_map.get_num_units_in_node(enemy_coalition, node_id)

        if max_advantage < this_advantage:
            max_advantage = this_advantage
            node_with_max_advantage = node_id

    if node_with_max_advantage is None:
        return None
    else:
        return int(node_with_max_advantage)


def decide_aa_move(group, game_map):

    if group.category != "vehicle":
        return None

    node_id = game_map.find_group_node(group)
    correct_goal = find_aa_target_node(group, game_map)

    if node_id == correct_goal:
        logger.info("AA unit %s already in goal" % group.name)
        return int(correct_goal)

    if correct_goal is None:
        logger.error("Bug: Could not decide aa move")
        return None

    logger.info("AA unit %s's goal is %d" % (group.name, correct_goal))

    if group.coalition == "red":
        enemy_coalition = "blue"
    else:
        enemy_coalition = "red"

    origin_coords = game_map.get_node_coords(node_id)
    origin_coords = euclid3.Point2(origin_coords[0], origin_coords[1])
    goal_coords = game_map.get_node_coords(correct_goal)
    goal_coords = euclid3.Point2(goal_coords[0], goal_coords[1])

    neighbor_paths = []
    path_pairs = []

    for neighbor in game_map.graph[node_id]:
        if neighbor == correct_goal:
            return int(correct_goal)
        shortest_path_to_goal = game_map.get_shortest_path(neighbor, correct_goal)

        # Ignore paths that return to the node we are in
        if shortest_path_to_goal is not None and node_id not in shortest_path_to_goal:
            neighbor_paths.append(shortest_path_to_goal)

    if len(neighbor_paths) == 0:
        logger.warning("No path to goal found for group %s" % str(group))
        return None

    if len(neighbor_paths) == 1:
        return int(neighbor_paths[0][0])

    # We try to identify the REALLY stupid choices before we randomize our actual choice
    forbidden_nodes = []

    length = len(neighbor_paths)

    # A bit complicated algorithm. Creates a list of all possible pairs of different paths and truncates them to the
    # nearest common node. The i and j -parts of the for loops are the traditional way to compare pairs with least
    # amount of work. (Don't compare item with itself, and don't compare a to b, and then b to a.
    for i in range(length - 1):
        for j in range(i + 1, length):

            # The previous two loops compared paths. The next two loops compare nodes in paths.
            found_intersection = False
            for k in range(0, len(neighbor_paths[i])):
                for l in range(0, len(neighbor_paths[j])):
                    if neighbor_paths[i][k] == neighbor_paths[j][l]:
                        path_pairs.append((neighbor_paths[i][:k+1], neighbor_paths[j][:l+1]))
                        found_intersection = True
                        break
                if found_intersection:
                    break

    # Compares all the pairs, and forbids all nodes where there is such a pair that the divergent part is one third
    # longer for the to-be-forbidden path, than the shorter path. This prevents any dumb detours from happening.
    for pair in path_pairs:

        # This allows us to trivially calculate the path length
        tmpgraph1 = game_map.graph.subgraph(pair[0])
        tmpgraph2 = game_map.graph.subgraph(pair[1])
        size1 = tmpgraph1.size(weight='weight')
        size2 = tmpgraph2.size(weight='weight')

        if size1 >= 1.33 * size2:
            # Found a dumb detour. Forbid.
            if pair[0][0] not in forbidden_nodes:
                forbidden_nodes.append(pair[0][0])
        elif size2 >= 1.33 * size1:
            # ditto
            if pair[1][0] not in forbidden_nodes:
                forbidden_nodes.append(pair[1][0])

    node_is_backtrack = {}
    choices = []
    allow_backtrack = True

    for path in neighbor_paths:
        if path[0] not in forbidden_nodes:
            is_backtrack = False
            dest_coords = game_map.get_node_coords(path[0])
            dest_coords = euclid3.Point2(dest_coords[0], dest_coords[1])

            if dest_coords.distance(goal_coords) > origin_coords.distance(goal_coords):
                # Making this move would mean backtracking
                is_backtrack = True
            else:
                # We found at least one node which doesn't constitute backtracking. Hence we disallow all moves that do
                allow_backtrack = False
            node_is_backtrack[path[0]] = is_backtrack
            choices.append(path[0])

    if allow_backtrack is False:
        choices = [node for node in choices if node_is_backtrack[node] is False]

    max_advantage = -999
    node_with_max_advantage = None

    for choice in choices:
        this_advantage = game_map.get_num_units_in_node(group.coalition, choice) - \
                         game_map.get_num_units_in_node(enemy_coalition, choice)

        if max_advantage < this_advantage:
            max_advantage = this_advantage
            node_with_max_advantage = choice

    decision = node_with_max_advantage
    extra_info = ""
    if node_is_backtrack[decision] is True:
        extra_info = " (which is backtracking)"

    logger.info("Final decision for aa group %s: move to node %d%s. AA unit currently heading towards node %d." %
                (group.name, decision, extra_info, correct_goal))
    if decision is None:
        return None
    else:
        return int(decision)


def decide_support_move(current_node, coalition, game_map, max_infantry_in_node):
    if coalition != "red" and coalition != "blue":
        logger.error("Cannot decide support move: Coalition must be either 'red' or 'blue'; was: '%s'" % coalition)
        return None

    # We prefer to fill nodes that are at the shortest possible distance from base, that still require support and don't
    # have enemy units.

    for distance in range(1, game_map.get_longest_distance(coalition) + 1):
        nodes = game_map.get_nodes_by_distance(coalition, distance)
        if nodes is not None:
            random.shuffle(nodes)
            for node_id in nodes:
                if node_id == current_node:
                    continue

                num_infantry_in_node = 0
                infantry_dict = game_map.get_infantry_in_node(node_id)
                if infantry_dict is not None:
                    # Note that we don't need to check here WHOSE infantry it is - the condition above already will have
                    # rejected the node if it's enemy infantry. Hence, if we get past the condition, it must be ours.
                    num_infantry_in_node = infantry_dict["number"]

                # Target nodes (but not detour nodes) are rejected with extreme prejudice, if they have enemy units or
                # they have less than half the max infantry. For a detour to a worthy target node, we WILL consider
                # nodes that are merely slightly lacking, though we give priority to nodes less than half-full.
                if game_map.is_enemy_activity_in_node(coalition, node_id) is False and \
                   num_infantry_in_node <= max_infantry_in_node / 2.0:

                    # Node: this is the neighbors-dictionary. We check if current node is this node's neighbor.
                    if current_node in game_map.graph[node_id]:
                        # The absolute optimal situation. Target node needs support and is next to us. Choose that.
                        # Note that the original list was shuffled, so we can just take the first instance that we come
                        # across. It's still random.
                        logger.info("Support unit for %s in node %d is able to make optimal move to node %d" %
                                    (coalition, int(current_node), int(node_id)))
                        return int(node_id)

            # Ok, we're here, so we found no optimal choices. What about a detour of exactly one node, such that
            # would take us to our target in two moves? Note: This is a bit special case. If we find even one such
            # target node, we immediately make the decision, only randomizing what detour we take. I mean, how likely
            # is it that there are several legitimate target nodes, exactly at this distance from base, and exactly one
            # node removed from us?
            for node_id in nodes:
                if node_id == current_node:
                    continue
                options = []
                num_infantry_in_node = 0
                infantry_dict = game_map.get_infantry_in_node(node_id)
                if infantry_dict is not None:
                    num_infantry_in_node = infantry_dict["number"]
                if game_map.is_enemy_activity_in_node(coalition, node_id) is False and \
                   num_infantry_in_node <= max_infantry_in_node / 2.0:

                    for neighbor in game_map.graph[current_node]:
                        num_infantry_in_node = 0
                        infantry_dict = game_map.get_infantry_in_node(neighbor)
                        if infantry_dict is not None:
                            # Note that we don't need to check here WHOSE infantry it is - the condition above
                            # already will have rejected the node if it's enemy infantry. Hence, if we get past the
                            # condition, it must be ours.
                            num_infantry_in_node = infantry_dict["number"]

                        if node_id in game_map.graph[neighbor] and \
                           game_map.is_enemy_activity_in_node(coalition, neighbor) is False and \
                           num_infantry_in_node <= max_infantry_in_node / 2.0:
                            options.append(neighbor)
                    if len(options) > 0:
                        # Now we have to actually use the choice function because we are choosing from the neighbors
                        # list, which is not shuffled.

                        node_num = int(np.random.choice(options))

                        logger.info("Support unit for %s in node %d is able to make almost optimal move to node %d; "
                                    "advancing towards goal through support needing detour." %
                                    (coalition, int(current_node), node_num))
                        return node_num

                    # Getting more desperate. Is there any neighbor that needs support AT ALL?

                    for neighbor in game_map.graph[current_node]:

                        num_infantry_in_node = 0
                        infantry_dict = game_map.get_infantry_in_node(neighbor)
                        if infantry_dict is not None:
                            # Note that we don't need to check here WHOSE infantry it is - the condition above
                            # already will have rejected the node if it's enemy infantry. Hence, if we get past the
                            # condition, it must be ours.
                            num_infantry_in_node = infantry_dict["number"]

                        if node_id in game_map.graph[neighbor] and \
                           game_map.is_enemy_activity_in_node(coalition, neighbor) is False and \
                           num_infantry_in_node < max_infantry_in_node:
                            options.append(neighbor)
                    if len(options) > 0:
                        node_num = int(np.random.choice(options))
                        logger.info("Support unit for %s in node %d is able to make almost optimal move to node %d; "
                                    "advancing towards goal through support needing detour." %
                                    (coalition, int(current_node), node_num))
                        return node_num

            # Now we're getting REALLY desperate about this particular distance. Are there any nodes whatsoever at it,
            # such that need support? If so, we choose between the nodes (if more than one) that are at the smallest
            # distance from our current position.
            distance_dict = {}
            for node_id in nodes:
                if node_id == current_node:
                    continue
                num_infantry_in_node = 0
                infantry_dict = game_map.get_infantry_in_node(node_id)
                if infantry_dict is not None:
                    num_infantry_in_node = infantry_dict["number"]
                if game_map.is_enemy_activity_in_node(coalition, node_id) is False and \
                   num_infantry_in_node <= max_infantry_in_node / 2.0:

                    try:
                        path = nx.dijkstra_path(game_map.graph, current_node, node_id)
                    except nx.NetworkXNoPath:
                        continue

                    this_distance = len(path) - 1
                    if this_distance not in distance_dict:
                        distance_dict[this_distance] = []

                    distance_dict[this_distance].append(node_id)

            if bool(distance_dict) is False:
                # Empty dictionary. In other words, we didn't find any nodes at all worth visiting at this distance from
                # base. We skip all the way to the beginning of the outermost loop, in which we try a greater distance
                # from base.
                continue

            # We have finally found a node worth visiting. What are the node(s) at the smallest possible distance from
            # our current position?
            smallest_distance = min(list(distance_dict.keys()))

            # Between those (or if just one, we pick that) we take first node (remember, original list was shuffled, so
            # this is the same as choosing randomly
            target_node = distance_dict[smallest_distance][0]

            try:
                path = nx.dijkstra_path(game_map.graph, current_node, target_node)
            except nx.NetworkXNoPath:
                continue
            if len(path) < 2:
                # Just extreme paranoia - trying to avoid an exception in some pathological circumstance.
                continue

            node_num = int(path[1])

            # In this one case we are completely deterministic and just take the shortest path to our target node.
            # Remember: The randomness was already involved in CHOOSING the target, so this is still unpredictable.
            logger.info("Support unit for %s in node %d needs to make a bad move to node %d: Follow shortest path to "
                        "target" % (coalition, int(current_node), node_num))
            return node_num

        # If here, we try the next greatest distance from base

    # All nodes either occupied, or don't require assistance
    return None


def get_mission_start_teleport():
    pass
