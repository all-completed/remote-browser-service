#!/usr/bin/env python3
"""
WebSocket connection script for remote browser service with Playwright.

This script connects to the remote browser service via WebSocket and uses Playwright
to control the browser through Chrome DevTools Protocol.

Playwright is required by default. Use --no-playwright for WebSocket-only mode.

Usage:
    # Local server (default)
    python websocket_connection.py --server-url http://localhost:8080 --session-id abc123

    # Remote server (set SERVER_URL or --server-url, API token via AC_API_KEY or --api-token)
    python websocket_connection.py --server-url https://<host> --user-id YOUR_USER_ID --session-id abc123

    # Connect with custom session ID
    python websocket_connection.py --session-id abc123

    # Navigate to custom URL
    python websocket_connection.py --session-id abc123 --navigate https://example.com

    # WebSocket-only mode (not recommended)
    python websocket_connection.py --no-playwright --session-id abc123
"""
import os
import sys
import asyncio
import argparse
import json
import time
import websockets
from websockets.exceptions import ConnectionClosed, InvalidURI
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


async def connect_websocket_only(base_url: str, user_id: str, session_id: str, api_token: str = None, short_url: bool = False):
    """
    Connect to remote browser service via WebSocket only (no Playwright).

    Args:
        base_url: Server base URL (e.g., ws://localhost:8080)
        user_id: User ID
        session_id: Session identifier
        api_token: Optional API token for auth
        short_url: Use /ws/{session_id} (token required, user_id from token)
    """
    base_ws = base_url.replace('http://', 'ws://').replace('https://', 'wss://')
    if short_url:
        if not api_token:
            print("✗ Token required for /ws/{session_id} alias (user_id from token)")
            sys.exit(1)
        ws_url = f"{base_ws}/ws/{session_id}"
    else:
        ws_url = f"{base_ws}/users/{user_id}/ws/{session_id}"
    params = ["mode=browser"]
    if api_token:
        params.append(f"access_token={api_token}")
    ws_url += "?" + "&".join(params)
    
    print("=" * 60)
    print("WebSocket Connection to Remote Browser Service")
    print("=" * 60)
    print(f"Connecting to: {ws_url}")
    print()
    
    try:
        # Increase timeout for session creation (up to 2 minutes)
        async with websockets.connect(ws_url, ping_interval=None, ping_timeout=None, close_timeout=10, open_timeout=120) as websocket:
            print("✓ Connected successfully!")
            print("  Waiting for messages...")
            print("  (Press Ctrl+C to disconnect)")
            print()
            
            # Listen for messages
            try:
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        print(f"📨 Received JSON: {json.dumps(data, indent=2)}")
                    except json.JSONDecodeError:
                        print(f"📨 Received: {message[:200]}..." if len(message) > 200 else f"📨 Received: {message}")
            except KeyboardInterrupt:
                print("\n\n⚠️  Disconnecting...")
                await websocket.close()
                print("✓ Disconnected")
                
    except ConnectionClosed:
        print("✗ Connection closed by server")
        sys.exit(1)
    except InvalidURI as e:
        print(f"✗ Invalid WebSocket URL: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error connecting: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def connect_with_playwright(server_url: str, user_id: str, session_id: str, api_token: str = None, navigate_url: str = None, duration: float = None, short_url: bool = False):
    """
    Connect to remote browser service and control it with Playwright.
    
    Args:
        server_url: Server base URL (e.g., http://localhost:8080)
        session_id: Session identifier
        navigate_url: Optional URL to navigate to (default: Google)
    """
    if not PLAYWRIGHT_AVAILABLE:
        print("✗ Playwright is not installed. Install it with: pip install playwright")
        print("  Then run: playwright install chromium")
        sys.exit(1)
    
    print("=" * 60)
    print("Playwright Connection to Remote Browser Service")
    print("=" * 60)
    print(f"Server: {server_url}")
    print(f"User ID: {user_id}")
    print(f"Session ID: {session_id}")
    if api_token:
        print(f"API token: {'*' * 8} (provided)")
    if short_url:
        print("URL: /ws/{session_id} (user_id from token)")
    print()

    base_ws = server_url.replace('http://', 'ws://').replace('https://', 'wss://')
    if short_url:
        if not api_token:
            print("✗ Token required for /ws/{session_id} alias (user_id from token)")
            sys.exit(1)
        ws_url = f"{base_ws}/ws/{session_id}?mode=browser&access_token={api_token}"
    else:
        ws_url = f"{base_ws}/users/{user_id}/ws/{session_id}?mode=browser"
        if api_token:
            ws_url += f"&access_token={api_token}"
    
    # Connect with Playwright (long timeout: server may need to create session first)
    print("\nStep 1: Connecting with Playwright over CDP (through server WS)...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(ws_url, timeout=180_000)
            print(f"✓ Connected to browser via CDP: {ws_url}")
            
            contexts = browser.contexts
            if contexts:
                context = contexts[0]
                print(f"✓ Using existing context")
            else:
                context = browser.new_context()
                print(f"✓ Created new context")
            
            pages = context.pages
            if pages and len(pages) > 0:
                page = pages[0]
                print(f"✓ Using existing page")
            else:
                page = context.new_page()
                print(f"✓ Created new page")
            
            target_url = navigate_url or "https://www.google.com"
            print(f"\nStep 2: Navigating to {target_url}...")
            page.goto(target_url, wait_until="networkidle")
            print(f"✓ Successfully navigated to: {page.url}")
            print(f"  Page title: {page.title()}")
            
            print("\n✓ Browser is ready!")
            if duration:
                print(f"  (Closing in {duration}s to trigger session save)")
            else:
                print("  (Press Ctrl+C to close)")
            print()

            try:
                if duration:
                    time.sleep(duration)
                else:
                    while True:
                        time.sleep(1)
            except KeyboardInterrupt:
                print("\n\n⚠️  Closing browser...")
                page.close()
                browser.close()
                print("✓ Browser closed")
                
    except Exception as e:
        print(f"✗ Error with Playwright: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point."""
    default_server = os.environ.get("SERVER_URL", "http://localhost:8080")
    default_ws = os.environ.get("WS_URL", default_server.replace("http://", "ws://").replace("https://", "wss://") + "/ws")
    
    parser = argparse.ArgumentParser(
        description="Connect to remote browser service via WebSocket with Playwright (default mode)"
    )
    parser.add_argument(
        "--url",
        default=default_ws,
        help="WebSocket URL (default: from SERVER_URL or WS_URL env)"
    )
    parser.add_argument(
        "--server-url",
        default=default_server,
        help="Server base URL (default: http://localhost:8080 or SERVER_URL env)"
    )
    parser.add_argument(
        "--user-id",
        default=os.environ.get("USER_ID") or os.environ.get("AC_USER_ID", "dev-user"),
        help="User ID (default: dev-user or USER_ID env var)"
    )
    parser.add_argument(
        "--session-id",
        default=os.environ.get("SESSION_ID", "test-session"),
        help="Session identifier (default: test-session or SESSION_ID env var)"
    )
    parser.add_argument(
        "--api-token",
        default=os.environ.get("AC_API_KEY") or os.environ.get("API_TOKEN"),
        help="API token or Auth0 access token (or AC_API_KEY / API_TOKEN env var)"
    )
    parser.add_argument(
        "--short-url",
        action="store_true",
        help="Use /ws/{session_id} alias (token required, user_id from token)"
    )
    parser.add_argument(
        "--no-playwright",
        action="store_true",
        help="Use WebSocket only, don't use Playwright (not recommended)"
    )
    parser.add_argument(
        "--navigate",
        default=os.environ.get("NAVIGATE_URL", "https://www.google.com"),
        help="URL to navigate to with Playwright (default: https://www.google.com or NAVIGATE_URL env var)"
    )
    parser.add_argument(
        "--duration",
        type=float,
        metavar="SECONDS",
        help="Auto-close after SECONDS (triggers session save)"
    )
    args = parser.parse_args()
    
    try:
        if args.no_playwright:
            base = args.server_url.replace('http://', 'ws://').replace('https://', 'wss://')
            asyncio.run(connect_websocket_only(base, args.user_id, args.session_id, args.api_token, args.short_url))
        else:
            if not PLAYWRIGHT_AVAILABLE:
                print("✗ Playwright is required but not installed")
                print("  Install Playwright with:")
                print("    pip install playwright")
                print("    playwright install chromium")
                sys.exit(1)
            
            server_url = args.server_url
            if args.url != default_ws and (args.url.startswith("ws://") or args.url.startswith("wss://")):
                base = args.url.replace("ws://", "http://").replace("wss://", "https://").split("/ws")[0]
                if base:
                    server_url = base

            connect_with_playwright(server_url, args.user_id, args.session_id, args.api_token, args.navigate, args.duration, args.short_url)
    except KeyboardInterrupt:
        print("\n\nConnection interrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
