# For players who join an existing server

All the hard work regarding setting up a campaign has already been done by the host. Players don't need to install
anything extra, apart from having the same version of DCS World as the host. The hosting player should have delivered
you an image of the map before the campaign starts, so that you know where the headquarters of the two sides are. The
objective is to get a vehicle to the opposing side's headquarters in such a way that on the next turn, after infantry
kills are calculated, the vehicle is still at the base and there is no living enemy infantry in it. A campaign can also
end in a draw if this is true for both sides on the same turn. One vehicle kills one infantry per turn. So, a group of
six units would kill six infantry.

The objective is to escort your vehicles towards the enemy HQ. In other words, you will be trying to destroy enemy
vehicles and/or airplanes, depending on what type of plane you are flying. Secondarily you can try to kill enemy
infantry and support units (which heal the infantry; in other words, revive dead infantry units in the node that the
support unit is in). This will allow your vehicles to advance faster near the enemy HQ, where otherwise the infantry
will slow them down.

Vehicles move with an algorithm that is designed to be unpredictable, but still find a reasonably fast route to the
target. But you can never predict 100% where the unit will move next. They won't always follow the absolute shortest
path, which is by design. If opposing forces would have moved past each other along the same segment between two nodes
on a turn, they are instead placed in combat positions for the next mission. Casualties will happen during gameplay. In
other words, vehicles are never destroyed in the simulated part of the turn. Destruction happens during the mission. For
this reason, missions should always be allowed to go on for some 10 to 15 minutes even if all human players die almost
immediately. This will cause an appropriate amount of casualties to happen while the game A.I. is driving the vehicles
and flying the remaining planes.

Typically, if a player is not engaged with an enemy plane and is flying a plane that can bomb ground units, the best
strategy is to try to destroy the enemy vehicle that has advanced the furthest. A.I. players employ the same strategy.

The host will receive a pop-up message in the game when the campaign has been fought to its conclusion. The host has the
ability to make the server automatically post the result to a Discord channel, or if Discord is not used then the host
can simply inform the rest of the players by whatever means of communication are used to organize the campaign.