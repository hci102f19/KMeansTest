import threading

from pyparrot.Bebop import Bebop

from model.flight.Vector import Vector


class BebopWrapper(threading.Thread):
    def __init__(self, bebop: Bebop):
        super().__init__()

        self.bebop = bebop

        self._running = True
        self.next_command = None

    def smart_sleep(self, timer):
        self.bebop.smart_sleep(timer)

    def stop_video_stream(self):
        self.bebop.stop_video_stream()

    def disconnect(self):
        self._running = False

    def enqueue_vector(self, vector: Vector):
        self.next_command = vector

    def run(self):
        print("self.bebop.safe_takeoff(5)")

        while self._running:
            if self.next_command is None:
                self.bebop.smart_sleep(0.1)
                continue

            print("FLY")
            cmd, self.next_command = self.next_command, None
            self.bebop.fly_direct(**cmd.emit(), duration=0.1)

        print("self.bebop.safe_land(5)")
        self.bebop.disconnect()
