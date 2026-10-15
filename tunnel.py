"""
Helper script to expose the local Flask server to the internet using pyngrok.
Run:
    python tunnel.py <YOUR_NGROK_AUTHTOKEN>
Or sign up for a free token at https://dashboard.ngrok.com/get-started/your-authtoken
"""
import sys
from pyngrok import ngrok, conf

def start_tunnel():
    if len(sys.argv) > 1:
        token = sys.argv[1].strip()
        ngrok.set_auth_token(token)
        print(f"[OK] ngrok authtoken set.")
    else:
        print("[INFO] If you have an ngrok authtoken, run: python tunnel.py <AUTHTOKEN>")
        print("[INFO] Attempting to connect...")

    try:
        public_url = ngrok.connect(5000)
        print("\n" + "=" * 60)
        print("🎉 YOUR LIVE PUBLIC URL:")
        print(f"👉 {public_url}")
        print("=" * 60)
        print("Keep this terminal open while sharing the link.")
        print("Press Ctrl+C to terminate the tunnel.\n")
        
        # Keep process alive
        import time
        while True:
            time.sleep(1)
    except Exception as e:
        print(f"\n[ERROR] Could not start ngrok tunnel: {e}")
        print("Tip: Sign up for a free account at https://ngrok.com to get your free authtoken.")

if __name__ == "__main__":
    start_tunnel()
