#!/usr/bin/env python
import errno
import pyaudio
import signal
import socket
import sys
import time
import uuid

from Queue import Empty, Queue
from threading import Thread, Lock

TCP_IP = "127.0.0.1"
TCP_PORT = 5005

sock = socket.socket(socket.AF_INET,  # Internet
                     socket.SOCK_STREAM)  # TCP
sock.bind((TCP_IP, TCP_PORT))
sock.listen(5)

BUFFER = 1024 * 2 * 2

audio = {}  # {room: Queue<data>}
listeners = {}  # {room: Set<socket>}
lock = Lock()


def sharer_handler(conn):
    room = str(uuid.uuid4())
    conn.sendall(room)
    while True:
        data = conn.recv(BUFFER)
        if not data:
            break
        with lock:
            if room not in audio:
                audio[room] = Queue()
                listeners[room] = set()
        audio[room].put(data)


def listener_handler(conn):
    room = conn.recv(1024)
    with lock:
        if room not in audio:
            audio[room] = Queue()
            listeners[room] = set()
    listeners[room].add(conn)
    while True:
        time.sleep(1)


def spray():
    while True:
        with lock:
            for room in audio:
                if listeners[room]:
                    try:
                        data = audio[room].get_nowait()
                    except Empty:
                        continue
                    for conn in listeners[room]:
                        try:
                            conn.sendall(data)
                        except IOError, e:
                            if e.errno != errno.EPIPE:
                                raise e


def client_thread(conn):
    data = conn.recv(1)

    try:
        if data == '0':
            sharer_handler(conn)
        else:
            listener_handler(conn)
    finally:
        with lock:
            print 'here'
            for members in listeners.values():
                members.discard(conn)
            conn.close()


def cleanup():
    global sock, stream, p
    if sock:
        sock.close()


def signal_handler(signal, frame):
    cleanup()
    sys.exit(0)

Thread(target=spray).start()

while True:
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    conn, addr = sock.accept()
    print 'Connection address:', addr
    thread = Thread(target=client_thread, args=(conn,))
    thread.start()
