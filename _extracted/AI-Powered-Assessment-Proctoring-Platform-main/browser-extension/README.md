# ExtensionGuard Browser Extension

This Manifest V3 extension is designed to monitor browser activity during an active interview and report suspicious navigation to the FastAPI backend.

## Features
- tracks tab switches
- detects local and loopback URL access
- detects AI/service websites
- sends browser events to the interview event API
- supports safe registration and unregistration of the active interview session

## Installation
1. Open Chrome/Edge and navigate to `chrome://extensions`.
2. Enable Developer mode.
3. Load the `browser-extension` folder as an unpacked extension.
4. Use the UI or a companion script to call:
   - `chrome.runtime.sendMessage({ type: 'registerInterviewSession', interviewId: 1, token: 'JWT' })`
5. When the interview ends, call:
   - `chrome.runtime.sendMessage({ type: 'clearInterviewSession' })`

## Notes
The extension does not collect browsing history outside the active interview window and only submits events during an active interview session.
