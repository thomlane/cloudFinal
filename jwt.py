from google.cloud import datastore
import flask
from flask import Flask, request, render_template, Blueprint
from requests_oauthlib import OAuth2Session
import json
from google.oauth2 import id_token
from google.auth import crypt
from google.auth import jwt
from google.auth.transport import requests

import constants

# This disables the requirement to use HTTPS so that you can test locally.
import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# app = Flask(__name__)
jwt_blueprint = Blueprint('jwt',__name__)
client = datastore.Client()

# These should be copied from an OAuth2 Credential section at
# https://console.cloud.google.com/apis/credentials
client_id = constants.CLIENT_ID
client_secret = constants.CLIENT_SECRET

# This is the page that you will use to decode and collect the info from
# the Google authentication flow
redirect_uri = constants.url + 'jwt/oauth'

# These let us get basic info to identify a user and not much else
# they are part of the Google People API
scope = 'https://www.googleapis.com/auth/userinfo.profile'
oauth = OAuth2Session(client_id, redirect_uri=redirect_uri,
                          scope=scope)

def _unique (id):
    print("in CHECK UNIQUE")
    # check uniqueness
    query = client.query(kind=constants.users)
    users = list(query.fetch())
    for user in users:
        if (id == user["id"]):
            return False
    return True

# Main log in page
@jwt_blueprint.route('/')
def index():
    print("loaded index")
    return flask.send_file ("templates/index.html")

# This link will redirect users to begin the OAuth flow with Google
@jwt_blueprint.route('/start')
def start():
    authorization_url, state = oauth.authorization_url(
        'https://accounts.google.com/o/oauth2/auth',
        # access_type and prompt are Google specific extra
        # parameters.
        access_type="offline", prompt="select_account")
    return flask.redirect(authorization_url)
    # return 'Please go <a href=%s>here</a> and authorize access.' % authorization_url

# This is where users will be redirected back to and where you can collect
# the JWT for use in future requests
@jwt_blueprint.route('/oauth')
def oauthroute():
    token = oauth.fetch_token(
        'https://accounts.google.com/o/oauth2/token',
        authorization_response=request.url,
        client_secret=client_secret)
    req = requests.Request()

    id_info = id_token.verify_oauth2_token(
    token['id_token'], req, client_id)
    print ("Your JWT is: " + token['id_token'])
    print ("Your unique id is " + id_info['sub'])

    jwt = token['id_token']
    id = id_info['sub']

    # if this id is not unique, the user has been here before
    if (not _unique(id)):
        print("LOGGED IN")
        message = "Welcome back user #" + id + "!"

    # else create a new user
    else:
        print("NEW USER")
        new_user = datastore.entity.Entity(key=client.key(constants.users))
        new_user.update({
                            "id": id,
                            "games": []
                        })
        client.put(new_user)
        message = "Welcome new user #" + id + "!"

    return flask.render_template(
      "login.html",
       sub = id,
       jwt = jwt,
       message = message
     )

# This page demonstrates verifying a JWT. id_info['email'] contains
# the user's email address and can be used to identify them
# this is the code that could prefix any API call that needs to be
# tied to a specific user by checking that the email in the verified
# JWT matches the email associated to the resource being accessed.
# @jwt_blueprint.route('/verify-jwt')
# def verify():
#     req = requests.Request()
#
#     id_info = id_token.verify_oauth2_token(
#     request.args['jwt'], req, client_id)
#
#     return repr(id_info) + "<br><br> the user is: " + id_info['email']
#
# if __name__ == '__main__':
#     app.run(host='127.0.0.1', port=8080, debug=True)
