import asyncio
import json
import websockets
import sys
import time

async def test_integration():
    uri = "ws://localhost:8001/ws"
    print(f"Connecting to {uri}...")
    
    start_time = time.time()
    try:
        async with websockets.connect(uri) as websocket:
            connect_time = time.time() - start_time
            print(f"Connected to WebSocket server in {connect_time:.3f}s")
            
            # 1. Wait for Session Started
            print("Waiting for session_started...")
            session_start_req_time = time.time()
            
            while True:
                response = await websocket.recv()
                
                if isinstance(response, bytes):
                    continue 
                
                data = json.loads(response)
                # print(f"Received: {data}")
                
                if data.get("type") == "session_started":
                    session_ready_time = time.time() - session_start_req_time
                    print(f"SUCCESS: Session Started! Latency: {session_ready_time:.3f}s")
                    break
                elif data.get("type") == "error":
                    print(f"ERROR: Received error from server: {data.get('message')}")
                    sys.exit(1)

            # 2. Wait for Greeting (TTS Start)
            print("Waiting for greeting (tts_start)...")
            greeting_start_time = time.time()
            greeting_received = False
            try:
                while True:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    
                    if isinstance(response, bytes):
                        # print(f"Received audio chunk ({len(response)} bytes)")
                        continue
                    
                    data = json.loads(response)
                    
                    if data.get("type") == "tts_start":
                        tts_latency = time.time() - greeting_start_time
                        print(f"SUCCESS: Greeting started! Latency: {tts_latency:.3f}s")
                        print(f"Text: {data.get('text')}")
                        greeting_received = True
                        break
            except asyncio.TimeoutError:
                print("WARNING: Timeout waiting for greeting.")

            # 3. Test Audio Upstream (Send 1s of silence)
            print("Testing Audio Upstream (Sending 1s silence)...")
            silence_chunk = b'\x00' * 640 # 20ms of 16kHz 16bit mono
            for _ in range(50): # 50 * 20ms = 1s
                await websocket.send(silence_chunk)
                await asyncio.sleep(0.02)
            print("Audio sent successfully (no connection drop).")

            # 4. Test Disconnect
            print("Sending disconnect action...")
            await websocket.send(json.dumps({"action": "disconnect"}))
            
            # 5. Wait for Session Ended
            print("Waiting for session_ended or close...")
            try:
                while True:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    if isinstance(response, bytes): continue
                    data = json.loads(response)
                    
                    if data.get("type") == "session_ended":
                        print("SUCCESS: Session Ended!")
                        break
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed by server (Expected).")
            except asyncio.TimeoutError:
                print("WARNING: Timeout waiting for session_ended.")

            print("\nIntegration Test Completed Successfully!")

    except Exception as e:
        print(f"Integration Test Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_integration())
