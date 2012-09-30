from __future__ import division, print_function

# add our main folder as include dir
import sys
sys.path.append("../")

import struct
import engine.map
import engine.player
import function, constants
from networking import event_serialize


def Server_Event_Hello(client, networker, game, event):
    # Stop saying hello
    networker.has_connected = True
    # Update the sequence, since from now the server is listening, or the first packet won't get through
    networker.sequence += 1
    # TODO: Some version check using event.version and constants.GAME_VERSION_NUMBER
    # Set all the important values to the game
    game.servername = event.servername
    player_id = event.playerid
    game.maxplayers = event.maxplayers
    game.map = engine.map.Map(game, event.mapname)
    client.start_game(player_id)

def Server_Event_Player_Join(client, networker, game, event):
    newplayer = engine.player.Player(game, game.current_state, event.id)
    newplayer.name = event.name

def Server_Event_Changeclass(client, networker, game, event):
    player = game.current_state.players[event.playerid]
    player.nextclass = function.convert_class(event.newclass)

def Server_Event_Changeteam(client, networker, game, event):
    player = game.current_state.players[event.playerid]
    player.team = event.newteam

def Server_Event_Die(client, networker, game, event):
    player = game.current_state.players[event.playerid]
    character = game.current_state.entities[player.character_id]
    character.die(game, game.current_state)

def Server_Event_Spawn(client, networker, game, event):
    player = game.current_state.players[event.playerid]
    player.spawn(game, game.current_state)

def Server_Snapshot_Update(client, networker, game, event):
    # Copy the current game state, and replace it with everything the server knows
    time = struct.unpack_from(">f", event.bytestr)[0]
    event.bytestr= event.bytestr[4:]

    state = game.current_state

    state.time = time

    for player in state.players.values():
        length = player.deserialize_input(event.bytestr)
        event.bytestr = event.bytestr[length:]

        try:
            character = state.entities[player.character_id]
            length = character.deserialize(state, event.bytestr)
            event.bytestr = event.bytestr[length:]
        except KeyError:
            # Character is dead
            pass

    game.current_state = state


def Server_Full_Update(client, networker, game, event):
    game.current_state.time, numof_players = struct.unpack_from(">IB", event.bytestr)
    event.bytestr = event.bytestr[5:]

    for index in range(numof_players):
        player = engine.player.Player(game, game.current_state, index)

        player.name, player_class, player.team, character_exists = struct.unpack_from(">32pBBB", event.bytestr)
        player.nextclass = function.convert_class(player_class)
        event.bytestr = event.bytestr[35:]

        if character_exists:
            player.spawn(game, game.current_state)

def Server_Event_Disconnect(client, networker, game, event):
    player = game.current_state.players[event.playerid]
    print (player.name +" has disconnected")
    player.destroy(game, game.current_state)

def Server_Event_Fire_Primary(client, networker, game, event):
    #FIXME: After merge, use state instead of game.current_state
    player = game.current_state.players[event.playerid]
    try:
        character = game.current_state.entities[player.character_id]
        weapon = game.current_state.entities[character.weapon]
        weapon.fire_primary(game, game.current_state)
    except KeyError:
        # character is dead or something. Shouldn't happen, so print something
        print("Error: Firing event called for dead or non-existent character!")

def Server_Event_Fire_Secondary(client, networker, game, event):
    #FIXME: After merge, use state instead of game.current_state
    player = game.current_state.players[event.playerid]
    try:
        character = game.current_state.entities[player.character_id]
        weapon = game.current_state.entities[character.weapon]
        weapon.fire_secondary(game, game.current_state)
    except KeyError:
        # character is dead or something. Shouldn't happen, so print something
        print("Error: Firing event called for dead or non-existent character!")

# Gather the functions together to easily be called by the event ID
eventhandlers = {}
eventhandlers[constants.EVENT_HELLO] = Server_Event_Hello
eventhandlers[constants.EVENT_PLAYER_JOIN] = Server_Event_Player_Join
eventhandlers[constants.EVENT_PLAYER_CHANGECLASS] = Server_Event_Changeclass
eventhandlers[constants.EVENT_PLAYER_CHANGETEAM] = Server_Event_Changeteam
eventhandlers[constants.EVENT_PLAYER_DIE] = Server_Event_Die
eventhandlers[constants.EVENT_PLAYER_SPAWN] = Server_Event_Spawn
eventhandlers[constants.SNAPSHOT_UPDATE] = Server_Snapshot_Update
eventhandlers[constants.FULL_UPDATE] = Server_Full_Update
eventhandlers[constants.EVENT_PLAYER_DISCONNECT] = Server_Event_Disconnect
eventhandlers[constants.EVENT_FIRE_PRIMARY] = Server_Event_Fire_Primary
eventhandlers[constants.EVENT_FIRE_SECONDARY] = Server_Event_Fire_Secondary
