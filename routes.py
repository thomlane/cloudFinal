from google.cloud import datastore
from flask import Flask, request, make_response, Blueprint
import json
from google.oauth2 import id_token
from google.auth.transport import requests

import constants

routes_blueprint = Blueprint('routes',__name__)
client = datastore.Client()

url = constants.url

games_self = url + constants.games + '/'
balls_self = url + constants.balls + '/'

#-- helper functions --#

# Passing in the JWT token returns the user id
def _getUserID(token):
    # Clean up authorization header to get just the user id
    encoded = token[7:]
    req = requests.Request()
    # verify the id
    id_info = id_token.verify_oauth2_token(encoded, req, constants.CLIENT_ID)
    return id_info['sub']



# Check all lanes. If the lane is in use, return True. If the lane is avaliable
##  or doesn't exist, return false
def _laneInUse (lane,game):
    if lane == game['lane']:
        return False
    query = client.query(kind=constants.games)
    results = list(query.fetch())

    for e in results:
        if e["lane"] == lane:
            return True
    return False
def _laneInUses (lane):
    query = client.query(kind=constants.games)
    results = list(query.fetch())

    for e in results:
        if e["lane"] == lane:
            return True
    return False

# Run through all lanes to check the next avaliable
def _nextAvaliable():

    query = client.query(kind=constants.games)
    results = list(query.fetch())
    # run through each lane
    for i in range(1,21):
        # since results is unordered, have to check all each time
        for game in results:
            # if this game's lane is i then this lane isn't avaliable
            if game["lane"] == i:
                break
        # if we went through the full for loop, this lane is avaliable
        else:
            return i
    # if no lanes are avaliable return 0
    return 0

# Removes game from user's game list
def _deleteGameFromUser (user_id, game_id):
    # Locate the user
    query = client.query(kind=constants.users)
    query.add_filter("id","=",user_id)
    results = list (query.fetch())
    query2 = client.query(kind=constants.users)
    users = list (query2.fetch())
    print(results)
    print(users)
    user = results[0]

    # Clear the game from the user
    for game in user['games']:
        if game.key.id == game_id:
            user['games'].remove(game)
            break

    user.update({
        "games":    user['games'],
        "id":       user['id']
    })
    client.put(user)
    return

# Removes game from ball's game attribute
def _removeGameFromBalls (game):
    for ball in game['balls']:
        print(ball)
        ball_key = client.key(constants.balls, int(ball))
        b = client.get(key=ball_key)
        b['game'] = None
        client.put(b)
    return

# removes the ball from the game
def _removeBallFromGame (game,ball):
    for i in range(len(game['balls'])):
        if game['balls'][i] == ball.key.id:
            del game['balls'][i]
            client.put(game)
            break

# Deletes all entities from database
@routes_blueprint.route('/hidden', methods=['DELETE'])
def hidden ():
    query = client.query(kind=constants.users)
    results = list(query.fetch())
    for user in results:
        user_key = client.key(constants.users, int(user.key.id))
        client.delete(user_key)
    query = client.query(kind=constants.games)
    results = list(query.fetch())
    for game in results:
        game_key = client.key(constants.games, int(game.key.id))
        client.delete(game_key)
    query = client.query(kind=constants.balls)
    results = list(query.fetch())
    for ball in results:
        ball_key = client.key(constants.balls, int(ball.key.id))
        client.delete(ball_key)
    return "All done"

@routes_blueprint.route('/users',methods=['GET'])
def users ():
    print ("in USERS")
    if request.method == 'GET':
        print('GET')


        query = client.query(kind=constants.users)
        results = list(query.fetch())

        return json.dumps(results)


@routes_blueprint.route('/games/<g_id>/balls/<b_id>', methods = ['POST','GET', 'PATCH', 'PUT', 'DELETE'])
def gamesIDballsID (g_id,b_id):
    print ("in GAMES id BALLS id")

    # Used to remove a ball from a game
    if request.method == 'DELETE':
        print('DELETE')

        # Game can only be edited by it's user, requiring an authorization
        if (request.headers.get('Authorization') == None):
            er = {"Error": "Must have an Authorization header"}
            print ("Error: Must have an Authorization header")
            return (json.dumps(er), 401)

        user_id = _getUserID(request.headers['Authorization'])

        game_key = client.key(constants.games, int(g_id))
        game = client.get(key=game_key)

        # Check the game exists
        if (game == None):
            er = {"Error": "No game with this game_id exists"}
            print("Error: No game with this game_id exists")
            return (json.dumps(er), 404)

        ball_key = client.key(constants.balls, int(b_id))
        ball = client.get(key=ball_key)

        # Check the ball exists
        if (ball == None):
            er = {"Error": "No ball with this ball_id exists"}
            print("Error: No ball with this ball_id exists")
            return (json.dumps(er), 404)

        # Check if this user is allowed to change this game
        if game['user'] != user_id:
            er = {"Error": "Only This game's user can edit this game"}
            print ("Error: Only This game's user can edit this game")
            return (json.dumps(er), 403)

        _removeBallFromGame(game, ball)
        ball['game'] = None
        client.put(ball)
        return ('',204)

    # Put a ball in game
    elif request.method == 'PATCH':
        print("PATCH")

        # Can only return JSON
        if 'application/json' not in request.accept_mimetypes:
            er = {"Error": "Can only return application/json"}
            print ("Error: Can only return application/json")
            return (json.dumps(er), 406)

        # Game can only be edited by it's user, requiring an authorization
        if (request.headers.get('Authorization') == None):
            er = {"Error": "Must have an Authorization header"}
            print ("Error: Must have an Authorization header")
            return (json.dumps(er), 401)

        user_id = _getUserID(request.headers['Authorization'])

        game_key = client.key(constants.games, int(g_id))
        game = client.get(key=game_key)

        # Check the game exists
        if (game == None):
            er = {"Error": "No game with this game_id exists"}
            print("Error: No game with this game_id exists")
            return (json.dumps(er), 404)

        ball_key = client.key(constants.balls, int(b_id))
        ball = client.get(key=ball_key)

        # Check the ball exists
        if (ball == None):
            er = {"Error": "No ball with this ball_id exists"}
            print("Error: No ball with this ball_id exists")
            return (json.dumps(er), 404)

        # Check if this user is allowed to change this game
        if game['user'] != user_id:
            er = {"Error": "Only This game's user can edit this game"}
            print ("Error: Only This game's user can edit this game")
            return (json.dumps(er), 403)

        if ball['game'] != None:
            er = {"Error": "This ball already has a game"}
            print ("Error: This ball already has a game")
            return (json.dumps(er), 403)

        ball['game'] = game.key.id
        game['balls'].append(ball.key.id)
        client.put(ball)
        client.put(game)
        body = {
            "user":     game["user"],
            "lane":     game['lane'],
            "bumpers":  game['bumpers'],
            "lights":   game['lights'],
            "balls":    game['balls'],
            "id":       g_id,
            "self":     games_self + g_id
        }

        return (json.dumps(body), 200)





    else:
        er = {"Error": str(request.method) + " is not allowed with this route. Try PATCH or DELETE"}
        print ("Error: "+ str(request.method) +  "is not allowed with this route. Try PATCH or DELETE")
        return (json.dumps(er), 405)


@routes_blueprint.route('/balls/<id>', methods=['POST','GET', 'PATCH', 'PUT', 'DELETE'])
def ballsID (id):
    print("in BALLS id")

    if request.method == 'PUT' or request.method == 'PATCH':
        print('in PUT/PATCH')

        # check for proper content and accept headers
        if 'application/json' not in request.content_type:
            er = {"Error": "Can only receive application/json"}
            print ("Error: Can only receive application/json")
            return (json.dumps(er), 415)
        if 'application/json' not in request.accept_mimetypes:
            er = {"Error": "Can only return application/json"}
            print ("Error: Can only return application/json")
            return (json.dumps(er), 406)

        print(id)
        ball_key = client.key(constants.balls, int(id))
        ball = client.get(key=ball_key)

        # Check the ball exists
        if (ball == None):
            er = {"Error": "No ball with this ball_id exists"}
            print("Error: No ball with this ball_id exists")
            return (json.dumps(er), 404)
        print (ball)
        print("ball game id: " + str(ball['game']))
        if (ball['game'] != None):
            # Game can only be deleted by the user, requiring an authorization
            if (request.headers.get('Authorization') == None):
                er = {"Error": "Must have an Authorization header"}
                print ("Error: Must have an Authorization header")
                return (json.dumps(er), 401)
            user_id = _getUserID(request.headers['Authorization'])

            game_key = client.key(constants.games, int(ball['game']))
            game = client.get(key=game_key)
            if game['user'] != user_id:
                er = {"Error": "Only This game's user can edit this game"}
                print ("Error: Only This game's user can edit this game")
                return (json.dumps(er), 403)
        else:
            user_id = None

        content = request.get_json()

        # Error check content
        ## Check if proper types
        if "weight" in content and type(content["weight"]) != int:
            er = {"Error": "weight must be an int"}
            print ("Error: weight must be an int")
            return (json.dumps(er), 400)
        if "color" in content and type(content["color"]) != str:
            er = {"Error": "color must be a string"}
            print ("Error: color must be a string")
            return (json.dumps(er), 400)
        if "inserts" in content and type(content["inserts"]) != bool:
            er = {"Error": "inserts must be a boolean"}
            print ("Error: inserts must be a boolean")
            return (json.dumps(er), 400)

        # PATCH would allow some values to be missing from request body
        if (request.method == 'PATCH'):
            # Set values; if values not in content, replace with values already in ball
            ## Pick the weight
            if "weight" not in content:
                weight = ball["weight"]
            else:
                weight = content["weight"]
            ## Choose color
            if "color" not in content:
                color = ball["color"]
            else:
                color = content["color"]
            ## inserts?
            if "inserts" not in content:
                inserts = ball["inserts"]
            else:
                inserts = content["inserts"]

        # PUT will cause an error if anything is missing from the request body
        elif (request.method == 'PUT'):
            # Check if all parts of the request body exist
            if ("weight" not in content or "color" not in content or "inserts" not in content):
                er = {"Error": "The request object is missing at least one of the required attributes"}
                print("Error: The request object is missing at least one of the required attributes")
                return (json.dumps(er), 400)

            weight = content["weight"]
            color = content["color"]
            inserts = content["inserts"]


        ball.update({
            "weight":   weight,
            "color":    color,
            "inserts":  inserts,
            "game":     ball['game']
        })
        client.put(ball)
        body = {
            "weight":   weight,
            "color":    color,
            "inserts":  inserts,
            "game":     ball['game'],
            "id":       id,
            "self":     balls_self + id
        }
        res = make_response(json.dumps(body),200)
        res.headers.set('Content-Location', games_self + id)
        res.mimetype = 'application/json'
        return res




    elif request.method == 'GET':
        print("GET")

        if 'application/json' not in request.accept_mimetypes:
            er = {"Error": "Can only return application/json"}
            print ("Error: Can only return application/json")
            return (json.dumps(er), 406)

        ball_key = client.key(constants.balls, int(id))
        ball = client.get(key=ball_key)

        # Check the ball exists
        if (ball == None):
            er = {"Error": "No ball with this ball_id exists"}
            print("Error: No ball with this ball_id exists")
            return (json.dumps(er), 404)
        print (ball)

        # form return body
        body = {
            "game":     ball['game'],
            "weight":   ball['weight'],
            "color":    ball['color'],
            "inserts":  ball['inserts'],
            "id":       id,
            "self":     balls_self + id
        }

        return (json.dumps(body),200)




    elif request.method == 'DELETE':
        print("DELETE")

        ball_key = client.key(constants.balls, int(id))
        ball = client.get(key=ball_key)

        # Check the ball exists
        if (ball == None):
            er = {"Error": "No ball with this ball_id exists"}
            print("Error: No ball with this ball_id exists")
            return (json.dumps(er), 404)
        print (ball)

        if ball["game"] != None:
            # ball can only be deleted by the user of the game the ball is in
            if (request.headers.get('Authorization') == None):
                er = {"Error": "This ball belongs to a game. Must have an Authorization header"}
                print ("Error: This ball belongs to a game. Must have an Authorization header")
                return (json.dumps(er), 401)

            user_id = _getUserID(request.headers['Authorization'])
            game_key = client.key(constants.games, int(ball['game']))
            game = client.get(key=game_key)

            print("test here")
            print(user_id)
            print(game['user'])
            # Check if this user is allowed to change this game
            if game['user'] != user_id:
                er = {"Error": "That ball belongs to another user's game"}
                print ("Error: That ball belongs to another user's game")
                return (json.dumps(er), 403)

            _removeBallFromGame(game,ball)


        client.delete(ball_key)
        return ('',204)

    else:
        er = {"Error": str(request.method) + " is not allowed with this route. Try PATCH, PUT, DELETE or GET"}
        print ("Error: "+ str(request.method) +  "is not allowed with this route. Try PATCH, PUT, DELETE or GET")
        return (json.dumps(er), 405)

# Just for getting all balls or creating a new one
@routes_blueprint.route('/balls', methods=['POST','GET', 'PATCH', 'PUT', 'DELETE'])
def balls ():
    print ("in BALLS")
    if request.method == 'GET':
        print("GET")

        if 'application/json' not in request.accept_mimetypes:
            er = {"Error": "Can only return application/json"}
            print ("Error: Can only return application/json")
            return (json.dumps(er), 406)


        query = client.query(kind=constants.balls)
        balls = list(query.fetch())
        body = []
        for ball in balls:
            this = {
                "id": ball.key.id,
                "self": balls_self + str(ball.key.id)
            }
            body.append(this)
        return (json.dumps(body),200)


    # Create a new ball
    elif request.method == 'POST':
        print ("POST")

        # check for proper content and accept headers
        if 'application/json' not in request.content_type:
            er = {"Error": "Can only receive application/json"}
            print ("Error: Can only receive application/json")
            return (json.dumps(er), 415)
        if 'application/json' not in request.accept_mimetypes:
            er = {"Error": "Can only return application/json"}
            print ("Error: Can only return application/json")
            return (json.dumps(er), 406)

        # Get the request body
        content = request.get_json()

        # Error check content

        ## Check everything required is in body
        if "weight" not in content or "color" not in content or "inserts" not in content:
            er = {"Error": "The request object is missing an attribute"}
            print("Error: The request object is missing an attribute")
            return (json.dumps(er), 400)

        ## Check if proper types
        if type(content["weight"]) != int:
            er = {"Error": "weight must be an int"}
            print ("Error: weight must be an int")
            return (json.dumps(er), 400)
        if type(content["color"]) != str:
            er = {"Error": "color must be a string"}
            print ("Error: color must be a string")
            return (json.dumps(er), 400)
        if type(content["inserts"]) != bool:
            er = {"Error": "inserts must be a boolean"}
            print ("Error: inserts must be a boolean")
            return (json.dumps(er), 400)

        # create the new balls data
        new_ball = datastore.entity.Entity(key=client.key(constants.balls))
        new_ball.update ({
            "game":     None,
            "weight":   content['weight'],
            "color":    content['color'],
            "inserts":  content['inserts']
        })

        # Put the new ball in datastore
        client.put(new_ball)
        id = str(new_ball.key.id)

        body = {
            "game":     None,
            "weight":   new_ball['weight'],
            "color":    new_ball['color'],
            "inserts":  new_ball['inserts'],
            "id":       id,
            "self":     balls_self + id
        }

        # set headers
        res = make_response(json.dumps(body),201)
        res.mimetype = 'application/json'
        res.headers.set('Content-Location', balls_self + id)

        return res


    else:
        er = {"Error": str(request.method) + " is not allowed with this route. Try POST or GET"}
        print ("Error: " + str(request.method) +  "is not allowed with this route. Try POST or GET")
        return (json.dumps(er), 405)




@routes_blueprint.route('/games', methods=['POST','GET', 'PATCH', 'PUT', 'DELETE'])
def games ():
    print("in GAMES")
    if request.method == 'POST':
        print("POST")

        # check for proper content and accept headers
        if 'application/json' not in request.content_type:
            er = {"Error": "Can only receive application/json"}
            print ("Error: Can only receive application/json")
            return (json.dumps(er), 415)
        if 'application/json' not in request.accept_mimetypes:
            er = {"Error": "Can only return application/json"}
            print ("Error: Can only return application/json")
            return (json.dumps(er), 406)


        # Game must be made by a user, requiring an authorization
        if (request.headers.get('Authorization') == None):
            er = {"Error": "Must have an Authorization header"}
            print ("Error: Must have an Authorization header")
            return (json.dumps(er), 401)

        user_id = _getUserID(request.headers['Authorization'])

        print("user id: " + str(user_id))

        content = request.get_json()

        # Error check content
        ## Check if proper types
        if "lane" in content and type(content["lane"]) != int:
            er = {"Error": "lane must be an int"}
            print ("Error: lane must be an int")
            return (json.dumps(er), 400)
        if "bumper" in content and type(content["bumper"]) != bool:
            er = {"Error": "bumper must be a boolean"}
            print ("Error: bumper must be a boolean")
            return (json.dumps(er), 400)
        if "lights" in content and type(content["lights"]) != bool:
            er = {"Error": "lights must be a boolean"}
            print ("Error: lights must be a boolean")
            return (json.dumps(er), 400)

        # Set default values
        ## Find a lane
        if "lane" not in content:
            lane = _nextAvaliable()
        else:
            lane = content["lane"]
        ## Set bumpers
        if "bumpers" not in content:
            bumpers = False
        else:
            bumpers = content["bumpers"]
        ## lights?
        if "lights" not in content:
            lights = False
        else:
            lights = content["lights"]


        ## if lane == 0, there were no lanes avaliable
        if lane == 0:
            er = {"Error": "No lanes currently available; try again later"}
            print ("Error: No lanes currently available; try again later")
            return (json.dumps(er), 404)

        ## Check that lane is within the proper bounds
        if lane < 1 or lane > 20:
            er = {"Error": "Lane number must be between 1 and 20, inclusive"}
            print ("Error: Lane number must be between 1 and 20, inclusive")
            return (json.dumps(er), 400)

        ## Check that this is avaliable
        if _laneInUses(lane):
            er = {"Error": "A game is already being played in that lane"}
            print ("Error: A game is already being played in that lane")
            return (json.dumps(er), 403)


        # create the new games data
        new_game = datastore.entity.Entity(key=client.key(constants.games))
        new_game.update ({
            "user":         user_id,
            "lane":         lane,
            "bumpers":      bumpers,
            "lights":       lights,
            "balls":         []
        })

        # Put the new game in datastore
        client.put(new_game)
        id = str(new_game.key.id)

        # form return body
        body = {
            "id":       id,
            "user":     new_game["user"],
            "lane":     new_game["lane"],
            "bumpers":  new_game["bumpers"],
            "lights":   new_game["lights"],
            "balls":    new_game["balls"],
            "self":     games_self + id
        }

        # set headers
        res = make_response(json.dumps(body),201)
        res.mimetype = 'application/json'
        res.headers.set('Content-Location', games_self + id)

        return res

    # List users games
    elif request.method == 'GET':
        print("in GET")


        # Game can only be seen by the user, requiring an authorization
        if (request.headers.get('Authorization') == None):
            er = {"Error": "Must have an Authorization header"}
            print ("Error: Must have an Authorization header")
            return (json.dumps(er), 401)

        # Can only return JSON
        if 'application/json' not in request.accept_mimetypes:
            er = {"Error": "Can only return application/json"}
            print ("Error: Can only return application/json")
            return (json.dumps(er), 406)

        # Games can only be shown to the game's user, requiring an authorization
        user_id = _getUserID(request.headers['Authorization'])

        query = client.query(kind=constants.games)
        results = list(query.fetch())
        games = []
        for game in results:
            id = str(game.key.id)
            # If the request is made by this game's user, give full details
            if (game['user'] == user_id):
                body = {
                    "id":       id,
                    "self":     games_self + id
                }
                games.append(body)
        return (json.dumps(games), 200)


    else:
        er = {"Error": str(request.method) + " is not allowed with this route. Try POST or GET"}
        print ("Error: "+ str(request.method) +  "is not allowed with this route. Try POST or GET")
        return (json.dumps(er), 405)


# Any game endpoint that requires a specific game
@routes_blueprint.route('/games/<id>', methods=['POST','GET', 'PATCH', 'PUT', 'DELETE'])
def gamesID (id):
    print("in GAMES ID")
    if request.method == 'GET':

        # Can only return JSON
        if 'application/json' not in request.accept_mimetypes:
            er = {"Error": "Can only return application/json"}
            print ("Error: Can only return application/json")
            return (json.dumps(er), 406)

        # Game can only be seen by the user, requiring an authorization
        if (request.headers.get('Authorization') == None):
            er = {"Error": "Must have an Authorization header"}
            print ("Error: Must have an Authorization header")
            return (json.dumps(er), 401)

        user_id = _getUserID(request.headers['Authorization'])

        print("user id: " + str(user_id))
        print ("object id: " + str(id))

        game_key = client.key(constants.games, int(id))
        game = client.get(key=game_key)

        # Check the game exists
        if (game == None):
            er = {"Error": "No game with this game_id exists"}
            print("Error: No game with this game_id exists")
            return (json.dumps(er), 404)
        print (game)

        # Check if this user is allowed to change this game
        if game['user'] != user_id:
            er = {"Error": "Only This game's user can view this game"}
            print ("Error: Only This game's user can view this game")
            return (json.dumps(er), 403)

        id = str(game.key.id)
        body = {
            "id":       id,
            "user":     game["user"],
            "lane":     game["lane"],
            "bumpers":  game["bumpers"],
            "lights":   game["lights"],
            "balls":    game["balls"],
            "self":     games_self + id
        }
        return (json.dumps(body),200)


    elif request.method == 'DELETE':
        print('DELETE')

        # Game can only be deleted by the user, requiring an authorization
        if (request.headers.get('Authorization') == None):
            er = {"Error": "Must have an Authorization header"}
            print ("Error: Must have an Authorization header")
            return (json.dumps(er), 401)

        user_id = _getUserID(request.headers['Authorization'])

        print("user id: " + str(user_id))
        print ("object id: " + str(id))

        game_key = client.key(constants.games, int(id))
        game = client.get(key=game_key)

        # Check the game exists
        if (game == None):
            er = {"Error": "No game with this game_id exists"}
            print("Error: No game with this game_id exists")
            return (json.dumps(er), 404)
        print (game)

        # Check if this user is allowed to change this game
        if game['user'] != user_id:
            er = {"Error": "Only This game's user can edit this game"}
            print ("Error: Only This game's user can edit this game")
            return (json.dumps(er), 403)

        # remove the game from the user's lists
        _deleteGameFromUser (user_id, game.key.id)
        _removeGameFromBalls (game)

        # Finally should be able to delete game
        client.delete(game_key)
        return ('',204)


    elif request.method == 'PUT' or request.method == 'PATCH':
        print('in PUT/PATCH')

        # check for proper content and accept headers
        if 'application/json' not in request.content_type:
            er = {"Error": "Can only receive application/json"}
            print ("Error: Can only receive application/json")
            return (json.dumps(er), 415)
        if 'application/json' not in request.accept_mimetypes:
            er = {"Error": "Can only return application/json"}
            print ("Error: Can only return application/json")
            return (json.dumps(er), 406)


        # Game must be edited by the user, requiring an authorization
        if (request.headers.get('Authorization') == None):
            er = {"Error": "Must have an Authorization header"}
            print ("Error: Must have an Authorization header")
            return (json.dumps(er), 401)

        user_id = _getUserID(request.headers['Authorization'])

        print("user id: " + str(user_id))
        print ("object id: " + str(id))

        game_key = client.key(constants.games, int(id))
        game = client.get(key=game_key)

        # Check the game exists
        if (game == None):
            er = {"Error": "No game with this game_id exists"}
            print("Error: No game with this game_id exists")
            return (json.dumps(er), 404)
        print (game)

        if game['user'] != user_id:
            er = {"Error": "Only This game's user can edit this game"}
            print ("Error: Only This game's user can edit this game")
            return (json.dumps(er), 403)


        content = request.get_json()

        # Error check content
        ## Check if proper types
        if "lane" in content and type(content["lane"]) != int:
            er = {"Error": "lane must be an int"}
            print ("Error: lane must be an int")
            return (json.dumps(er), 400)
        if "bumper" in content and type(content["bumper"]) != bool:
            er = {"Error": "bumper must be a boolean"}
            print ("Error: bumper must be a boolean")
            return (json.dumps(er), 400)
        if "lights" in content and type(content["lights"]) != bool:
            er = {"Error": "lights must be a boolean"}
            print ("Error: lights must be a boolean")
            return (json.dumps(er), 400)

        # PATCH would allow some values to be missing from request body
        if (request.method == 'PATCH'):
            # Set values; if values not in content, replace with values already in game
            ## Find a lane
            if "lane" not in content:
                lane = game["lane"]
            else:
                lane = content["lane"]
            ## Set bumpers
            if "bumpers" not in content:
                bumpers = game["bumpers"]
            else:
                bumpers = content["bumpers"]
            ## lights?
            if "lights" not in content:
                lights = game["lights"]
            else:
                lights = content["lights"]

        # PUT will cause an error if anything is missing from the request body
        elif (request.method == 'PUT'):
            # Check if all parts of the request body exist
            if ("lane" not in content or "bumpers" not in content or "lights" not in content):
                er = {"Error": "The request object is missing at least one of the required attributes"}
                print("Error: The request object is missing at least one of the required attributes")
                return (json.dumps(er), 400)
            lane = content['lane']
            bumpers = content['bumpers']
            lights = content['lights']


        ## Check that lane is within the proper bounds
        if lane < 1 or lane > 20:
            er = {"Error": "Lane number must be between 1 and 20, inclusive"}
            print ("Error: Lane number must be between 1 and 20, inclusive")
            return (json.dumps(er), 400)

        ## Check that this is avaliable
        if _laneInUse(lane,game):
            er = {"Error": "A game is already being played in that lane"}
            print ("Error: A game is already being played in that lane")
            return (json.dumps(er), 403)

        game.update({
            "user":     game["user"],
            "lane":     lane,
            "bumpers":   bumpers,
            "lights":   lights,
            "balls":    game['balls']
        })
        client.put(game)
        id = str(game.key.id)
        body = {
            "user":     game["user"],
            "lane":     lane,
            "bumpers":  bumpers,
            "lights":   lights,
            "balls":    game['balls'],
            "id":       id,
            "self":     games_self + id
        }
        res = make_response(json.dumps(body),200)
        res.headers.set('Content-Location', games_self + id)
        res.mimetype = 'application/json'
        return res


    else:
        er = {"Error": str(request.method) + " is not allowed with this route. Try PUT, PATCH, GET, or DELETE"}
        print ("Error: "+ str(request.method) +  "is not allowed with this route. Try PUT, PATCH, GET, or DELETE")
        return (json.dumps(er), 405)
