import random
from dataclasses import dataclass
from threading import Lock
from flask import Flask, render_template, session, request, \
    copy_current_request_context
from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)


@dataclass
class User:
    sid: str
    name: str = ""
    role: str | None = ""

    def into(self):
        return {"name": self.name, "role": self.role}


users = {}


@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)


@app.route('/master')
def master():
    return render_template("master.html", async_mode=socketio.async_mode)


@socketio.event
def set_name(message):
    users[request.sid].name = message["name"]
    print(users)


@socketio.event
def add_user(message):
    users[request.sid] = User(request.sid)
    print('User connected', request.sid)


@socketio.event
def assign_roles(message):
    roles = []
    print(message)
    for role in message["roles"]:
        try:
            amount = int(role["amount"])
        except ValueError:
            emit("invalid_amount")
            return
        for i in range(amount):
            roles.append(role["name"])

    if len(roles) > len(users):
        emit("more_roles")
        return

    while len(roles) < len(users):
        roles.append(message["default"])

    random.shuffle(roles)

    assert len(roles) == len(users)

    for user, role in zip(users.values(), roles):
        user.role = role
        emit("role", {"role": role}, room=user.sid)

    emit("users", {"users": [user.into() for user in users.values()]})

@socketio.event
def my_broadcast_event(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']},
         broadcast=True)


@socketio.event
def my_ping():
    emit('my_pong')


@socketio.event
def connect():
    print('Client connected', request.sid)


@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected', request.sid)
    if request.sid in users.keys():
        del users[request.sid]


if __name__ == '__main__':
    socketio.run(app)
