#!/usr/bin/env python
import base64
import errno
import redis
import signal
import socket
import time
import uuid

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
    need_lock = True
    while True:
        data = conn.recv(BUFFER)
        if not data:
            break
        if need_lock:
            with lock:
                if room not in listeners:
                    listeners[room] = set()
                need_lock = False

        r.rpush("audio:%s" % room, base64.b64encode(data))
        time.sleep(0.001)


def listener_handler(conn, room):
    with lock:
        if room not in listeners:
            listeners[room] = set()
        listeners[room].add(conn)
        print listeners[room]

    # Loop so connection doesn't end
    while True:
        time.sleep(1)


def spray(room):
    while True:
        time.sleep(0.001)  # be nice to cpu
        with lock:
            if room in listeners:
                if not listeners[room]:  # if no listeners in room, continue
                    continue

                # Get data from Redis
                data = r.lpop("audio:%s" % room)
                if not data:  # if nothing to send, continue
                    continue
                data = base64.b64decode(data)

                # Send BUFFER amount of stream to all listeners
                # duplicate so set can be modified while iterating
                for conn in set(listeners[room]):
                    try:
                        conn.sendall(data)
                    except IOError, e:
                        # Close connection and remove listener if socket closed
                        if e.errno == errno.EPIPE:
                            conn.close()
                            listeners[room].remove(conn)


def create_room():
    room = str(uuid.uuid4())[:8]
    return room


def client_thread(conn):
    data = conn.recv(1)

    try:
        if data == '0':  # Sharer
            room = create_room()

            # Create thread that handles sending data to all listeners
            Thread(target=spray, args=(room,)).start()

            # Handle incoming data from sharer
            sharer_handler(conn, room)

        elif data == '1':  # Listener
            room = conn.recv(8)
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
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if r.keys():
        r.delete(*r.keys())

    while True:
        conn, addr = sock.accept()
        print 'Connection address:', addr

        # Create thread to handle each connection
        thread = Thread(target=client_thread, args=(conn,))
        thread.start()


if __name__ == '__main__':
    main()
