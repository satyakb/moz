#!/usr/bin/env python
import base64
import errno
import json
import pyaudio
import redis
import select
import signal
import socket
import sys
import time
import uuid

from Queue import Empty, Queue
from threading import Thread, Lock

TCP_IP = "127.0.0.1"
TCP_PORT = 5005

r = redis.StrictRedis(host='localhost', port=6379, db=0)

sock = socket.socket(socket.AF_INET,  # Internet
                     socket.SOCK_STREAM)  # TCP
sock.bind((TCP_IP, TCP_PORT))
sock.listen(5)

BUFFER = 256 * 2 * 2

listeners = {}  # {room: Set<socket>}
lock = Lock()


def sharer_handler(conn, room):
    conn.sendall(room)
    while True:
        data = conn.recv(BUFFER)
        if not data:
            break
        need_lock = True
        if need_lock:
            with lock:
                if room not in listeners:
                    listeners[room] = set()
                need_lock = False

        data = json.dumps({'room': room, 'data': base64.b64encode(data)})
        r.rpush("audio:%s" % room, data)
        time.sleep(0.001)


def listener_handler(conn, room):
    with lock:
        if room not in listeners:
            listeners[room] = set()
        listeners[room].add(conn)
        print listeners[room]

    while True:
        try:
            select.select([conn, ], [conn, ], [], 5)
        except IOError:
            break
        time.sleep(1)


def spray(room):
    while True:
        time.sleep(0.001)
        with lock:
            if room in listeners:
                if not listeners[room]:
                    continue
                msg = r.lpop("audio:%s" % room)
                if not msg:
                    continue
                data = json.loads(msg)
                try:
                    data = base64.b64decode(data['data'])
                except Empty:
                    continue
                for conn in set(listeners[room]):
                    try:
                        conn.sendall(data)
                    except IOError, e:
                        if e.errno == errno.EPIPE:
                            conn.close()
                            listeners[room].remove(conn)


def create_room():
    room = str(uuid.uuid4())[:8]
    return room


def client_thread(conn):
    data = conn.recv(1)

    try:
        if data == '0':
            room = create_room()
            Thread(target=spray, args=(room,)).start()
            sharer_handler(conn, room)
        else:
            room = conn.recv(1024)
            listener_handler(conn, room)
    finally:
        conn.close()


def cleanup():
    global sock, stream, p
    if sock:
        sock.close()


def signal_handler(signal, frame):
    cleanup()
    sys.exit(0)


def main():
    if r.keys():
        r.delete(*r.keys())

    while True:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        conn, addr = sock.accept()
        print 'Connection address:', addr
        thread = Thread(target=client_thread, args=(conn,))
        thread.start()


if __name__ == '__main__':
    main()

