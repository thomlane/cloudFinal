import json

import flask
import requests

from jwt import jwt_blueprint
from routes import routes_blueprint


app = flask.Flask(__name__)

app.register_blueprint(jwt_blueprint,url_prefix='/jwt')
app.register_blueprint(routes_blueprint)

@app.route('/')
def routing():
    print ("main")
    return flask.redirect(flask.url_for('jwt.index'))


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
