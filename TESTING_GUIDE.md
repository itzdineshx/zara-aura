# ZARA Home Automation - End-to-End Testing Guide

## Pre-Testing Setup

### Prerequisites
- Node.js 18+ and npm/bun installed
- Python 3.8+ with virtual environment set up
- Backend dependencies installed: `pip install -r backend/requirements.txt`
- Frontend dependencies installed: `npm install` or `bun install`
- OpenRouter API key for cloud LLM (if testing online mode)
- MQTT broker configured (local or cloud)

### Environment Variables

#### Frontend (.env.local or .env)
```bash
VITE_BACKEND_URL=http://localhost:8000
```

#### Backend (.env or environment)
```bash
# AI/LLM Configuration
OPENROUTER_API_KEY=your_key_here
PREFERRED_RESPONSE_MODE=smart

# STT Configuration
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
WHISPER_MODEL_SIZE=base

# MQTT Home Automation
HOME_MQTT_ENABLED=true
HOME_MQTT_HOST=localhost
HOME_MQTT_PORT=1883
HOME_MQTT_USERNAME=user
HOME_MQTT_PASSWORD=pass
HOME_MQTT_CONTROL_TOPIC=zara/home/control
HOME_MQTT_STATUS_TOPIC=zara/home/status

# TTS Configuration
TTS_ENGINE=edge-tts
```

## Step-by-Step Testing

### 1. Start Backend Server

```bash
# Navigate to project root
cd e:\projects\zara-home

# Activate virtual environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Navigate to backend
cd backend

# Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### 2. Start Frontend Development Server

```bash
# In new terminal, from project root
npm run dev
# or
bun run dev
```

**Expected Output:**
```
  VITE v5.4.19  ready in XXX ms
  ➜  Local:   http://localhost:5173/
  ➜  Press q to stop
```

### 3. Open Browser

Navigate to `http://localhost:5173` (or the URL shown by Vite)

**What to verify:**
- Page loads without errors
- ZARA orb displays with smooth animations
- Title and controls visible
- No console errors in DevTools (F12)

### 4. Test Health Check

**Test:** Backend connectivity check
**Expected:** Console should show `Backend health check passed` (check DevTools Console)

### 5. Test Voice Input (Most Important)

#### 5.1 Microphone Permission
- Click the microphone button at bottom center
- Browser should request microphone permission
- **Allow** the permission

#### 5.2 Simple Voice Command
- Say: "Hello"
- Listen for:
  1. Orb changes to **listening** state (animated pulse)
  2. After 4.5 seconds, auto-sends to backend
  3. Orb changes to **thinking** state
  4. Backend responds with text and audio

**Verify in Response Display:**
- **Main text**: AI response visible
- **Subtitle**: Shows "Heard: [your_transcript]" with emotion and language
- **Audio plays**: Should hear TTS response

#### 5.3 Verify API Request/Response
Open DevTools Network tab:
1. Filter for `voice` or `chat` requests
2. Check POST request to `/voice` endpoint
3. Verify request body has audio blob
4. Verify response has:
   ```json
   {
     "text": "...",
     "transcript": "...",
     "language": "...",
     "emotion": "...",
     "audio_features": { "volume": 0.X, "pitch": X }
   }
   ```

### 6. Test Chat Input

**Test:** Text-based AI interaction
**How:**
1. Note: Currently no text input UI, but API is wired
2. Use DevTools Console to test:
   ```javascript
   // In console, within the browser on localhost:5173
   const { sendChat } = await import('./src/lib/zara-api.ts');
   const response = await sendChat("What time is it?", "smart");
   console.log(response);
   ```

**Verify:** Response contains text, emotion, language

### 7. Test Device Control

**Test:** Home automation action execution
**How:**
1. Look for "Home Devices" panel on left side
2. Click the toggle button for "Light"
3. Check DevTools Network tab for `/chat` request
4. Verify MQTT topic publication (if MQTT broker is set up)

**Verify:**
- Button state changes immediately (optimistic update)
- No error in console
- Backend responds with `status: "executed"`
- If MQTT connected: Check MQTT pub/sub for message on `zara/home/control`

**Expected MQTT payload:**
```json
{
  "action": "light_on",
  "source": "zara-backend",
  "ts": "2026-05-06T..."
}
```

### 8. Test Mode Switching

**Test:** Response mode changes (online/smart/offline)
**How:**
1. Look for mode toggle buttons (top right area - SMART/VIRTUAL/LOOP)
2. Click different modes
3. Check DevTools Console for no errors

**Verify:**
- Mode button highlights correctly
- POST request to `/mode` endpoint succeeds
- Backend responds with `{ "mode": "selected_mode" }`
- Voice input still works in each mode

### 9. Test Continuous Loop Mode

**Test:** Loop mode for continuous listening
**How:**
1. Toggle "LOOP" button in top right
2. Speak a short phrase
3. After response completes, should automatically start listening again

**Verify:**
- Listening starts automatically
- Can stop by saying "stop loop" or clicking mic button again
- Subtext shows "Loop mode on"

### 10. Test Error Scenarios

#### 10.1 Backend Offline
1. Stop backend server
2. Click microphone button
3. Try to record and send voice

**Expected:** Error message in runtime hint area

#### 10.2 Invalid API Response
1. Start backend but with STT/TTS disabled
2. Send voice audio

**Expected:** Appropriate error message or graceful fallback

#### 10.3 MQTT Not Connected
1. Disconnect MQTT broker
2. Try to control device

**Expected:** Error message showing "MQTT connection failed"

### 11. Test Settings Panel

**Test:** Settings persistence
**How:**
1. Click settings icon (if present)
2. Change settings:
   - Response Mode
   - Voice Language
   - Microphone Sensitivity
   - Voice Speed
   - Voice Persona (Male/Female)
   - Continuous Loop

**Verify:**
- Settings persist across voice interactions
- Language changes affect response language
- Sensitivity affects audio capture
- Changes sync with backend (`/mode` endpoint)

### 12. Test Multi-Language Support

**Test:** Language detection and response
**How:**
1. Say something in Hindi: "नमस्ते"
2. Say something in Tamil: "வணக்கம்"
3. Say something in English: "Hello"

**Verify:**
- Transcript shows detected language
- Response language matches or intelligently switches
- Subtitle shows correct language code (en, hi, ta, te, ml)

### 13. Test Audio Playback

**Test:** TTS audio generation and playback
**How:**
1. Send voice or chat message
2. Listen for audio response

**Verify:**
- Audio plays through speakers/headphones
- No errors in console
- Network request to `/tts` succeeds
- Audio blob is valid MP3/WAV

### 14. Performance Check

**Test:** Real-time responsiveness
**How:**
1. Send multiple voice messages in succession
2. Watch network waterfall and timing
3. Check CPU/Memory in DevTools

**Verify:**
- Voice processing completes within 5-10 seconds
- No memory leaks (memory stable across multiple interactions)
- Network requests complete successfully
- Smooth UI animations (no jank)

## Debugging Tips

### Enable Verbose Logging
Add to `src/pages/Index.tsx`:
```typescript
useEffect(() => {
  console.log("State changed:", {
    orbState,
    isProcessing,
    runtimeHint,
    lastLanguage,
    lastEmotion,
  });
}, [orbState, isProcessing, runtimeHint, lastLanguage, lastEmotion]);
```

### Check Network Requests
DevTools Network tab filters:
- `voice` - Voice processing endpoint
- `chat` - Chat endpoint
- `tts` - Text-to-speech endpoint
- `health` - Health check
- `home` - Home automation endpoints
- `mode` - Mode setting endpoint

### MQTT Debugging
If using MQTT broker:
```bash
# Subscribe to all topics (using mosquitto_sub)
mosquitto_sub -h localhost -p 1883 -t "zara/home/#"

# Should see messages like:
# zara/home/control - Commands sent from backend
# zara/home/status - Status updates from ESP32
```

### Backend Logs
FastAPI will show:
```
INFO:     POST /voice HTTP/1.1" 200 OK
INFO:     POST /chat HTTP/1.1" 200 OK
INFO:     POST /home-mode HTTP/1.1" 200 OK
```

## Expected Behavior Summary

| Action | Expected Result |
|--------|-----------------|
| Page load | Page loads, health check passes, no errors |
| Click mic | Orb animates to "listening", shows "Listening..." |
| Speak | Audio captured, orb animates to "thinking" |
| 4.5s pass | Auto-sends audio to backend |
| Backend processes | Orb animates to "speaking", response plays |
| Device toggle | MQTT command sent, button state updates |
| Stop recording | Stops audio capture, processes existing chunks |
| Mode change | Backend syncs, POST /mode succeeds |
| Loop enabled | Continuous auto-listening starts |
| Error occurs | Error message shown in subtext area |

## Test Coverage Checklist

- [ ] Backend health check passes
- [ ] Voice input records successfully
- [ ] Backend responds with valid VoiceApiResponse
- [ ] TTS audio plays
- [ ] Device control sends MQTT commands
- [ ] Mode switching syncs with backend
- [ ] Continuous loop mode works
- [ ] Multi-language detection works
- [ ] Error handling displays messages
- [ ] Settings persist
- [ ] No memory leaks after multiple interactions
- [ ] Performance acceptable (< 5-10s per request)
- [ ] No console errors
- [ ] UI animations smooth

## Troubleshooting

### "Unable to reach backend" Error
- Check backend is running on port 8000
- Verify `VITE_BACKEND_URL` env var
- Check CORS configuration in backend
- Try `http://localhost:8000/health` in browser

### No Audio Response
- Check TTS service is running
- Verify speaker volume
- Check DevTools for `/tts` request errors
- Try different TTS engine in settings

### MQTT Commands Not Received
- Verify MQTT broker is running
- Check topic names match: `zara/home/control`, `zara/home/status`
- Verify credentials in backend config
- Monitor MQTT topics: `mosquitto_sub -h localhost -p 1883 -t "zara/home/#"`

### Microphone Not Working
- Grant browser microphone permission
- Check microphone is not in use by another app
- Verify HTTPS (not needed for localhost, but check if deploying)
- Check DevTools for getUserMedia errors

### Responses Very Slow
- Check backend STT model size (use `tiny` for faster testing)
- Verify Ollama is running (if using offline mode)
- Check OpenRouter API is responsive (if using online mode)
- Monitor backend CPU/memory usage
