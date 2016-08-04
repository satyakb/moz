#!/usr/bin/env python
import pyaudio
import wave
import socket
import signal
import sys
import time

from docopt import docopt


doc = """Moz

Usage:
  client.py <ip> <port> share <wavfile>
  client.py <ip> <port> listen <room>
  client.py (-h | --help)
  client.py (-V | --version)

Options:
  -h --help     Show this screen.
  -V --version  Show version.
"""

TCP_IP = "127.0.0.1"
TCP_PORT = 5005

# length of data to send
BUFFER = 256

sock = None
p = None
stream = None


def share(file, ip, port):
    global sock, p, stream
    # open the file for reading.
    wf = wave.open(file, 'rb')

    # create an audio object
    p = pyaudio.PyAudio()

    sock = socket.socket(socket.AF_INET,  # Internet
                         socket.SOCK_STREAM)  # TCP
    sock.connect((ip, port))
    sock.send('0')  # identifier for sharer

    print 'Room id: %s' % sock.recv(BUFFER)

    # read data (based on the chunk size)
    data = wf.readframes(BUFFER)

    while data != '':
        sock.send(data)
        data = wf.readframes(BUFFER)
        time.sleep(0.001)

    cleanup()


def listen(room, ip, port):
    global BUFFER, sock, p, stream
    BUFFER = BUFFER * 2 * 2
    # create an audio object
    p = pyaudio.PyAudio()

    # open stream based on the wave object which has been input.
    stream = p.open(format=p.get_format_from_width(2),
                    channels=2,
                    rate=44100,
                    output=True)

    sock = socket.socket(socket.AF_INET,  # Internet
                         socket.SOCK_STREAM)  # TCP
    sock.connect((ip, port))

    sock.send('1')  # identifier for listener
    sock.send(room)

    while True:
        data = sock.recv(BUFFER)
        if not data:
            break
        stream.write(data)

    cleanup()


def signal_handler(signal, frame):
    cleanup()
    sys.exit(0)


def cleanup():
    global sock, stream, p
    if sock:
        sock.close()
    if stream:
        stream.close()
    if p:
        p.terminate()


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    args = docopt(doc, version='Moz 1.0')
    try:
        ip = args.get('<ip>')
        port = int(args.get('<port>'))

        if args.get('share'):
            share(args.get('<wavfile>'), ip, port)
        elif args.get('listen'):
            listen(args.get('<room>'), ip, port)
    finally:
        cleanup()


if __name__ == '__main__':
    main()
