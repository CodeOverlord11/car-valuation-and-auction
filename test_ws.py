import websocket
import json

def on_message(ws, message):
    print("Received message:")
    print(json.dumps(json.loads(message), indent=2))
    ws.close()

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"Connection closed. Status code: {close_status_code}, Msg: {close_msg}")

def on_open(ws):
    print("Connection opened!")

if __name__ == "__main__":
    ws = websocket.WebSocketApp(
        "ws://127.0.0.1:8000/ws/auction/demo-1",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever()
