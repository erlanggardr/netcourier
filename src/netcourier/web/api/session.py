import threading
from netcourier.client.gateway_connection import GatewayConnection
from netcourier.common.constants import DEFAULT_GATEWAY_HOST, DEFAULT_GATEWAY_CLIENT_PORT

class MockApp:
    def __init__(self, session):
        self.session = session
        self.token = None
        self.active_downloader = None
        
    def run_in_ui(self, callback, *args, **kwargs):
        try:
            callback(*args, **kwargs)
        except Exception as e:
            print(f"Callback error: {e}")

    def on_pm_received(self, payload):
        self.session.push_event({"type": "PM_RECEIVED", "payload": payload})
        
    def on_room_message(self, payload):
        self.session.push_event({"type": "ROOM_MESSAGE", "payload": payload})
        
    def on_room_delete_file(self, payload):
        self.session.push_event({"type": "ROOM_DELETE_FILE_BROADCAST", "payload": payload})
        
    def on_room_reaction(self, payload):
        self.session.push_event({"type": "ROOM_REACTION_BROADCAST", "payload": payload})
        
    def on_room_typing(self, payload):
        self.session.push_event({"type": "ROOM_TYPING_BROADCAST", "payload": payload})
        
    def on_room_member_list_response(self, payload):
        self.session.push_event({"type": "ROOM_MEMBER_LIST", "payload": payload})
        
    def on_room_system_event(self, payload):
        self.session.push_event({"type": "SYSTEM_EVENT", "payload": payload})
        
    def on_gateway_disconnected(self):
        self.session.push_event({"type": "DISCONNECTED", "server": "gateway"})
        
    def on_room_disconnected(self):
        self.session.push_event({"type": "DISCONNECTED", "server": "room"})
        
    def show_error(self, message):
        self.session.push_event({"type": "ERROR", "message": message})


class WebSession:
    def __init__(self, session_id, gateway_host=DEFAULT_GATEWAY_HOST, gateway_port=DEFAULT_GATEWAY_CLIENT_PORT):
        self.session_id = session_id
        self.app = MockApp(self)
        self.gateway_conn = GatewayConnection(gateway_host, gateway_port, self.app)
        self.room_conn = None
        self.events = []
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)
        self.username = None
        
        self.gateway_conn.connect()

    def push_event(self, event):
        with self.cond:
            self.events.append(event)
            self.cond.notify_all()

    def get_events(self, timeout=30):
        with self.cond:
            if not self.events:
                self.cond.wait(timeout)
            events_to_return = self.events[:]
            self.events = []
            return events_to_return
