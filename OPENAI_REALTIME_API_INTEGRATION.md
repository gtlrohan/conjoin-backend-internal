# 🎯 OpenAI Realtime API Integration Instructions

## Overview

This document provides complete instructions for integrating OpenAI's Realtime API with the voice therapy system. The current implementation uses WebSocket proxying, but OpenAI Realtime API requires WebRTC for optimal performance.

## 🚨 Current Issues

- Backend is creating custom WebSocket proxy instead of using OpenAI's WebRTC endpoint
- Frontend sends placeholder silence instead of real audio
- Missing ephemeral token security implementation
- Not using OpenAI's native audio format requirements (PCM16, 24kHz, mono)

## 📋 TODO Checklist

- [ ] Replace WebSocket connection with OpenAI Realtime API WebRTC endpoint
- [ ] Implement ephemeral token generation endpoint for secure client access
- [ ] Add proper audio format handling (PCM16, 24kHz, mono) for OpenAI compatibility
- [ ] Integrate therapy-specific instructions and session management
- [ ] Update frontend to use WebRTC instead of WebSocket for audio streaming

---

## 1. 🔧 Backend API Changes Required

### Replace Current Voice Therapist Endpoints

**File to modify**: Your main FastAPI backend file

```python
# REPLACE your current voice-therapist endpoints with these:

import httpx
from fastapi import HTTPException, Depends
from datetime import datetime
from typing import Optional

# 1. ADD Ephemeral Token Generation Endpoint
@app.post("/voice-therapist/session/start")
async def create_realtime_session(request: VoiceSessionRequest, current_user: User = Depends(get_current_user)):
    """
    Create OpenAI Realtime API session and return ephemeral credentials
    """
    try:
        # Call OpenAI's Realtime Sessions API
        async with httpx.AsyncClient() as client:
            openai_response = await client.post(
                "https://api.openai.com/v1/realtime/sessions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-realtime-preview-2024-12-17",
                    "voice": "alloy",
                    "instructions": get_therapy_instructions(request.therapy_type),
                    "input_audio_transcription": {"model": "whisper-1"},
                    "tools": get_therapy_tools(),
                    "tool_choice": "auto",
                    "temperature": 0.8,
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 500
                    }
                }
            )
        
        if openai_response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"OpenAI API error: {openai_response.text}")
            
        session_data = openai_response.json()
        
        # Store session in database for tracking
        db_session = VoiceTherapySession(
            session_id=session_data["id"],
            user_id=current_user.id,
            therapy_type=request.therapy_type,
            openai_session_id=session_data["id"],
            ephemeral_token_expires=datetime.fromtimestamp(session_data["expires_at"]),
            status="created"
        )
        db.add(db_session)
        await db.commit()
        
        return {
            "session_id": session_data["id"],
            "client_secret": session_data["client_secret"],  # This is the ephemeral token
            "expires_at": session_data["expires_at"],
            "therapy_type": request.therapy_type,
            "start_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create OpenAI session: {str(e)}")

def get_therapy_instructions(therapy_type: str) -> str:
    """
    Return specialized therapy instructions for OpenAI
    """
    base_instructions = """You are a compassionate, professional therapist conducting a voice therapy session. 
    
    Your approach should be:
    - Speak in a warm, empathetic tone
    - Ask thoughtful follow-up questions
    - Provide evidence-based therapeutic guidance
    - Maintain appropriate professional boundaries
    - Be supportive and non-judgmental
    - Keep responses concise but meaningful
    - Use active listening techniques
    - Validate the user's emotions
    - Suggest practical coping strategies when appropriate
    
    Remember: This is a real therapy session. The user trusts you with their mental health."""
    
    therapy_specific = {
        "general": """Focus on general mental wellbeing and active listening. 
        Help the user explore their thoughts and feelings in a safe, non-judgmental space.""",
        
        "anxiety": """Specialize in anxiety management techniques including:
        - Deep breathing exercises
        - Cognitive reframing techniques  
        - Grounding exercises (5-4-3-2-1 technique)
        - Progressive muscle relaxation
        - Challenging catastrophic thinking patterns""",
        
        "stress": """Focus on stress reduction techniques including:
        - Mindfulness and present-moment awareness
        - Time management strategies
        - Boundary setting techniques
        - Work-life balance discussions
        - Identifying stress triggers and coping mechanisms"""
    }
    
    return f"{base_instructions}\n\nSpecialization: {therapy_specific.get(therapy_type, therapy_specific['general'])}"

def get_therapy_tools():
    """
    Return therapy-specific tools/functions for the AI
    """
    return [
        {
            "type": "function",
            "name": "end_session_summary",
            "description": "Create a session summary when the user wants to end the therapy session",
            "parameters": {
                "type": "object",
                "properties": {
                    "key_topics": {"type": "string", "description": "Main topics discussed"},
                    "insights": {"type": "string", "description": "Key insights or breakthroughs"},
                    "recommended_actions": {"type": "string", "description": "Suggested next steps or homework"}
                },
                "required": ["key_topics"]
            }
        },
        {
            "type": "function", 
            "name": "breathing_exercise",
            "description": "Guide the user through a breathing exercise",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration": {"type": "integer", "description": "Duration in seconds"},
                    "technique": {"type": "string", "description": "Type of breathing technique"}
                }
            }
        }
    ]

# 2. UPDATE Session End Endpoint
@app.post("/voice-therapist/session/{session_id}/end")
async def end_realtime_session(
    session_id: str, 
    request: EndSessionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    End OpenAI Realtime session and save session data
    """
    try:
        # Find session in database
        session = db.query(VoiceTherapySession).filter(
            VoiceTherapySession.session_id == session_id,
            VoiceTherapySession.user_id == current_user.id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Update session with end data
        session.end_time = datetime.now()
        session.session_summary = request.session_summary
        session.mood_after = request.mood_after
        session.status = "ended"
        
        await db.commit()
        
        return {
            "message": "Session ended successfully",
            "session_id": session_id,
            "duration_minutes": (session.end_time - session.start_time).total_seconds() / 60
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to end session: {str(e)}")

# 3. ADD Request/Response Models
from pydantic import BaseModel

class VoiceSessionRequest(BaseModel):
    therapy_type: str  # "general", "anxiety", "stress"
    mood_before: Optional[str] = None

class EndSessionRequest(BaseModel):
    session_summary: Optional[str] = None
    mood_after: Optional[str] = None
```

---

## 2. 🗄️ Database Schema Updates

**File to modify**: Your SQLAlchemy models file

```python
# UPDATE VoiceTherapySession model:
from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.sql import func

class VoiceTherapySession(Base):
    __tablename__ = "voice_therapy_sessions"
    
    session_id = Column(String, primary_key=True)  # This is now OpenAI's session ID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    therapy_type = Column(String, nullable=False)
    start_time = Column(DateTime, default=func.now())
    end_time = Column(DateTime, nullable=True)
    openai_session_id = Column(String, nullable=False)  # NEW: Store OpenAI's internal session ID
    ephemeral_token_expires = Column(DateTime, nullable=True)  # NEW: Track token expiration
    session_summary = Column(Text, nullable=True)
    mood_before = Column(String, nullable=True)
    mood_after = Column(String, nullable=True)
    status = Column(String, default="created")  # created, active, ended, error
    
    # Relationship
    user = relationship("User", back_populates="therapy_sessions")

# ADD migration file
"""
Revision ID: add_realtime_api_fields
Create Date: 2024-01-XX XX:XX:XX.XXXXXX
"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add new columns for OpenAI Realtime API
    op.add_column('voice_therapy_sessions', sa.Column('openai_session_id', sa.String(), nullable=True))
    op.add_column('voice_therapy_sessions', sa.Column('ephemeral_token_expires', sa.DateTime(), nullable=True))
    
    # Update existing records (if any)
    op.execute("UPDATE voice_therapy_sessions SET openai_session_id = session_id WHERE openai_session_id IS NULL")
    
    # Make openai_session_id non-nullable after update
    op.alter_column('voice_therapy_sessions', 'openai_session_id', nullable=False)

def downgrade():
    op.drop_column('voice_therapy_sessions', 'ephemeral_token_expires')
    op.drop_column('voice_therapy_sessions', 'openai_session_id')
```

---

## 3. 🎤 Frontend WebRTC Implementation

**File to modify**: `lib/src/services/voice_therapy_service.dart`

```dart
import 'dart:async';
import 'dart:convert';
import 'package:flutter_webrtc/flutter_webrtc.dart';
import 'package:conjoin_app/src/models/voice_therapy_session.dart';
import 'package:conjoin_app/src/services/backend_request_service.dart';
import 'package:conjoin_app/src/services/authentication_service.dart';
import 'package:flutter/foundation.dart';

class VoiceTherapyService extends ChangeNotifier {
  static final VoiceTherapyService _instance = VoiceTherapyService._internal();
  factory VoiceTherapyService() => _instance;
  VoiceTherapyService._internal();

  // WebRTC components
  RTCPeerConnection? _peerConnection;
  RTCDataChannel? _dataChannel;
  MediaStream? _localStream;
  
  final BackendRequest _backendRequest = BackendRequest();
  
  VoiceTherapySession? _currentSession;
  VoiceSessionStatus _status = VoiceSessionStatus.idle;
  List<AudioMessage> _audioMessages = [];

  // Getters
  VoiceTherapySession? get currentSession => _currentSession;
  VoiceSessionStatus get status => _status;
  List<AudioMessage> get audioMessages => List.unmodifiable(_audioMessages);

  // Initialize WebRTC
  Future<bool> initialize() async {
    try {
      debugPrint('Initializing WebRTC for voice therapy');
      return true;
    } catch (e) {
      debugPrint('Error initializing VoiceTherapyService: $e');
      return false;
    }
  }

  // Start a new voice therapy session with WebRTC
  Future<VoiceTherapySession?> startSession({
    required int userId,
    required VoiceTherapyType therapyType,
    String? moodBefore,
  }) async {
    try {
      _updateStatus(VoiceSessionStatus.connecting);
      
      debugPrint('🚀 Starting OpenAI Realtime API session...');
      debugPrint('👤 User ID: $userId');
      debugPrint('🎯 Therapy Type: ${therapyType.toString().split('.').last}');

      // Get ephemeral token from backend
      final response = await _backendRequest.post(
        '/voice-therapist/session/start',
        {
          'therapy_type': therapyType.toString().split('.').last,
          'mood_before': moodBefore,
        },
      );
      
      if (response == null) {
        throw Exception('Failed to create session');
      }
      
      final sessionData = response;
      final ephemeralToken = sessionData['client_secret']['value'];
      
      debugPrint('✅ Ephemeral token received');
      debugPrint('🆔 Session ID: ${sessionData['session_id']}');
      
      // Create WebRTC connection
      await _createWebRTCConnection(sessionData['session_id'], ephemeralToken);
      
      _currentSession = VoiceTherapySession(
        sessionId: sessionData['session_id'],
        userId: userId,
        therapyType: therapyType,
        startTime: DateTime.now(),
        moodBefore: moodBefore,
        status: VoiceSessionStatus.connecting,
      );
      
      return _currentSession;
      
    } catch (e) {
      debugPrint('❌ Session creation failed: $e');
      _updateStatus(VoiceSessionStatus.error);
      return null;
    }
  }
  
  // Create WebRTC Connection to OpenAI
  Future<void> _createWebRTCConnection(String sessionId, String ephemeralToken) async {
    try {
      // WebRTC Configuration
      final configuration = {
        'iceServers': [
          {'urls': 'stun:stun.l.google.com:19302'}
        ],
        'iceCandidatePoolSize': 10,
      };
      
      _peerConnection = await createPeerConnection(configuration);
      
      // Set up data channel for OpenAI events
      RTCDataChannelInit dataChannelDict = RTCDataChannelInit()
        ..maxRetransmits = 30;
        
      _dataChannel = await _peerConnection!.createDataChannel('oai-events', dataChannelDict);
      
      _dataChannel!.onMessage = (RTCDataChannelMessage message) {
        debugPrint('📨 Realtime event received: ${message.text.substring(0, 100)}...');
        _handleRealtimeEvent(jsonDecode(message.text));
      };
      
      _dataChannel!.onDataChannelState = (RTCDataChannelState state) {
        debugPrint('📡 Data channel state: $state');
        if (state == RTCDataChannelState.RTCDataChannelOpen) {
          debugPrint('✅ Data channel opened - sending session update');
          _sendSessionUpdate();
        }
      };
      
      // Get microphone access with OpenAI-compatible settings
      final mediaConstraints = {
        'audio': {
          'sampleRate': 24000,  // OpenAI requires 24kHz
          'channelCount': 1,    // Mono audio
          'echoCancellation': true,
          'noiseSuppression': true,
          'autoGainControl': true,
        },
        'video': false,
      };
      
      _localStream = await navigator.mediaDevices.getUserMedia(mediaConstraints);
      
      // Add local audio track to peer connection
      if (_localStream!.getAudioTracks().isNotEmpty) {
        await _peerConnection!.addTrack(_localStream!.getAudioTracks().first, _localStream!);
        debugPrint('🎤 Local audio track added');
      }
      
      // Handle incoming audio from OpenAI
      _peerConnection!.onTrack = (RTCTrackEvent event) {
        debugPrint('🔊 Received audio track from OpenAI');
        if (event.track.kind == 'audio') {
          // Create audio element to play OpenAI's voice
          final audioRenderer = RTCVideoRenderer();
          audioRenderer.initialize();
          audioRenderer.srcObject = event.streams.first;
        }
      };
      
      // Handle connection state changes
      _peerConnection!.onConnectionState = (RTCPeerConnectionState state) {
        debugPrint('🔗 Connection state: $state');
        switch (state) {
          case RTCPeerConnectionState.RTCPeerConnectionStateConnected:
            debugPrint('✅ WebRTC connected to OpenAI');
            _updateStatus(VoiceSessionStatus.connected);
            break;
          case RTCPeerConnectionState.RTCPeerConnectionStateFailed:
            debugPrint('❌ WebRTC connection failed');
            _updateStatus(VoiceSessionStatus.error);
            break;
          case RTCPeerConnectionState.RTCPeerConnectionStateDisconnected:
            debugPrint('⚠️ WebRTC disconnected');
            if (_status != VoiceSessionStatus.ended) {
              _updateStatus(VoiceSessionStatus.error);
            }
            break;
          default:
            break;
        }
      };
      
      // Create and send offer to OpenAI
      RTCSessionDescription offer = await _peerConnection!.createOffer();
      await _peerConnection!.setLocalDescription(offer);
      
      debugPrint('📤 Sending WebRTC offer to OpenAI');
      
      // Send offer to OpenAI Realtime API
      final openAiResponse = await _backendRequest.postRaw(
        'https://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17',
        offer.sdp!,
        headers: {
          'Authorization': 'Bearer $ephemeralToken',
          'Content-Type': 'application/sdp',
        },
      );
      
      if (openAiResponse != null && openAiResponse.isNotEmpty) {
        final answer = RTCSessionDescription(openAiResponse, 'answer');
        await _peerConnection!.setRemoteDescription(answer);
        
        debugPrint('✅ WebRTC connection established with OpenAI Realtime API');
      } else {
        throw Exception('Failed to get SDP answer from OpenAI');
      }
      
    } catch (e) {
      debugPrint('❌ WebRTC connection failed: $e');
      _updateStatus(VoiceSessionStatus.error);
      throw e;
    }
  }
  
  // Send session configuration to OpenAI
  void _sendSessionUpdate() {
    if (_dataChannel?.state != RTCDataChannelState.RTCDataChannelOpen) return;
    
    final sessionUpdate = {
      'type': 'session.update',
      'session': {
        'instructions': _getSessionInstructions(),
        'voice': 'alloy',
        'input_audio_format': 'pcm16',
        'output_audio_format': 'pcm16',
        'input_audio_transcription': {'model': 'whisper-1'},
        'turn_detection': {
          'type': 'server_vad',
          'threshold': 0.5,
          'prefix_padding_ms': 300,
          'silence_duration_ms': 500,
        },
        'tools': _getTherapyTools(),
        'tool_choice': 'auto',
        'temperature': 0.8,
      }
    };
    
    _dataChannel!.send(RTCDataChannelMessage(jsonEncode(sessionUpdate)));
    debugPrint('📤 Session configuration sent to OpenAI');
  }
  
  String _getSessionInstructions() {
    if (_currentSession == null) return '';
    
    final baseInstructions = '''You are a compassionate, professional therapist conducting a voice therapy session.
    
Your approach should be:
- Speak in a warm, empathetic tone
- Ask thoughtful follow-up questions  
- Provide evidence-based therapeutic guidance
- Maintain appropriate professional boundaries
- Be supportive and non-judgmental
- Keep responses concise but meaningful
- Use active listening techniques
- Validate the user's emotions

Remember: This is a real therapy session. The user trusts you with their mental health.''';

    final therapySpecific = {
      VoiceTherapyType.general: 'Focus on general mental wellbeing and active listening.',
      VoiceTherapyType.anxiety: 'Specialize in anxiety management techniques, breathing exercises, and cognitive reframing.',
      VoiceTherapyType.stress: 'Focus on stress reduction techniques, mindfulness, and coping strategies.'
    };

    return '$baseInstructions\n\nSpecialization: ${therapySpecific[_currentSession!.therapyType]}';
  }
  
  List<Map<String, dynamic>> _getTherapyTools() {
    return [
      {
        'type': 'function',
        'name': 'end_session_summary',
        'description': 'Create a session summary when the user wants to end the therapy session',
        'parameters': {
          'type': 'object',
          'properties': {
            'key_topics': {'type': 'string', 'description': 'Main topics discussed'},
            'insights': {'type': 'string', 'description': 'Key insights or breakthroughs'},
            'recommended_actions': {'type': 'string', 'description': 'Suggested next steps'}
          },
          'required': ['key_topics']
        }
      }
    ];
  }
  
  // Handle OpenAI Realtime Events
  void _handleRealtimeEvent(Map<String, dynamic> event) {
    final eventType = event['type'];
    debugPrint('📨 Realtime event: $eventType');
    
    switch (eventType) {
      case 'session.created':
        debugPrint('🎉 OpenAI Realtime session created');
        _addWelcomeMessage();
        break;
        
      case 'session.updated':
        debugPrint('⚙️ Session configuration updated');
        break;
        
      case 'input_audio_buffer.speech_started':
        debugPrint('🎤 User started speaking');
        _updateStatus(VoiceSessionStatus.recording);
        break;
        
      case 'input_audio_buffer.speech_stopped':
        debugPrint('🛑 User stopped speaking');
        _updateStatus(VoiceSessionStatus.processing);
        break;
        
      case 'conversation.item.input_audio_transcription.completed':
        _handleUserTranscription(event);
        break;
        
      case 'response.audio_transcript.delta':
        _handleAITextResponse(event);
        break;
        
      case 'response.audio_transcript.done':
        debugPrint('✅ AI transcript complete');
        break;
        
      case 'response.audio.delta':
        debugPrint('🔊 AI audio chunk received');
        _updateStatus(VoiceSessionStatus.speaking);
        break;
        
      case 'response.done':
        debugPrint('✅ AI response complete');
        _updateStatus(VoiceSessionStatus.connected);
        break;
        
      case 'error':
        debugPrint('❌ OpenAI error: ${event['error']}');
        _updateStatus(VoiceSessionStatus.error);
        break;
        
      default:
        debugPrint('🔄 Unknown event: $eventType');
    }
  }
  
  // Handle user speech transcription
  void _handleUserTranscription(Map<String, dynamic> event) {
    final transcript = event['transcript'] as String?;
    if (transcript == null || transcript.isEmpty) return;
    
    debugPrint('👤 User said: $transcript');
    
    // Add or update user message
    final userMessage = AudioMessage(
      id: 'user_${DateTime.now().millisecondsSinceEpoch}',
      isFromUser: true,
      timestamp: DateTime.now(),
      transcription: transcript,
      audioPath: null,
    );
    
    _audioMessages.add(userMessage);
    notifyListeners();
  }
  
  // Handle AI text response streaming
  void _handleAITextResponse(Map<String, dynamic> event) {
    final delta = event['delta'] as String?;
    if (delta == null || delta.isEmpty) return;
    
    // Update or create AI message
    final lastMessage = _audioMessages.isNotEmpty ? _audioMessages.last : null;
    if (lastMessage != null && !lastMessage.isFromUser && lastMessage.id.startsWith('ai_')) {
      // Update existing message
      final updatedTranscript = (lastMessage.transcription ?? '') + delta;
      final updatedMessage = AudioMessage(
        id: lastMessage.id,
        isFromUser: false,
        timestamp: lastMessage.timestamp,
        transcription: updatedTranscript,
        audioPath: lastMessage.audioPath,
      );
      _audioMessages[_audioMessages.length - 1] = updatedMessage;
    } else {
      // Create new AI message
      final aiMessage = AudioMessage(
        id: 'ai_${DateTime.now().millisecondsSinceEpoch}',
        isFromUser: false,
        timestamp: DateTime.now(),
        transcription: delta,
        audioPath: null,
      );
      _audioMessages.add(aiMessage);
    }
    
    notifyListeners();
  }
  
  void _addWelcomeMessage() {
    final welcomeMessage = AudioMessage(
      id: 'welcome_${DateTime.now().millisecondsSinceEpoch}',
      isFromUser: false,
      transcription: "Hello! I'm your AI therapist. I can see we're successfully connected. Feel free to start speaking whenever you're ready.",
      audioPath: null,
      timestamp: DateTime.now(),
    );

    _audioMessages.add(welcomeMessage);
    notifyListeners();
    
    debugPrint('👋 Welcome message added to chat');
  }

  // End the session
  Future<bool> endSession({String? moodAfter, String? sessionSummary}) async {
    try {
      if (_currentSession == null) {
        debugPrint('❌ No active session to end');
        return false;
      }

      _updateStatus(VoiceSessionStatus.ended);
      
      // Close WebRTC connection
      await _dataChannel?.close();
      await _peerConnection?.close();
      
      // Stop local media stream
      _localStream?.getTracks().forEach((track) {
        track.stop();
      });
      _localStream?.dispose();
      
      _dataChannel = null;
      _peerConnection = null;
      _localStream = null;
      
      // End session on backend
      try {
        await _backendRequest.post(
          '/voice-therapist/session/${_currentSession!.sessionId}/end',
          {
            'session_summary': sessionSummary ?? '',
            'mood_after': moodAfter ?? '',
          },
        );
        debugPrint('✅ Session ended successfully on backend');
      } catch (e) {
        debugPrint('⚠️ Failed to end session on backend: $e');
      }
      
      // Clean up
      _audioMessages.clear();
      _currentSession = null;
      _updateStatus(VoiceSessionStatus.idle);
      
      return true;
    } catch (e) {
      debugPrint('❌ Error ending session: $e');
      return false;
    }
  }

  // Helper methods
  void _updateStatus(VoiceSessionStatus newStatus) {
    if (_status != newStatus) {
      debugPrint('🔄 Status change: $_status -> $newStatus');
      _status = newStatus;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    endSession();
    super.dispose();
  }
}
```

---

## 4. 📱 Required Dependencies

**File to modify**: `pubspec.yaml`

```yaml
dependencies:
  flutter:
    sdk: flutter
  
  # Existing dependencies...
  
  # NEW: Add WebRTC support
  flutter_webrtc: ^0.10.7
  
  # REMOVE these (no longer needed):
  # record: ^5.0.1
  # web_socket_channel: ^2.4.0
  # audioplayers: ^6.0.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^3.0.0
```

**Run after updating pubspec.yaml**:
```bash
flutter pub get
flutter pub deps
```

---

## 5. 🔒 Environment Variables

**File to modify**: Your environment configuration

```env
# ADD to your .env file:
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_REALTIME_MODEL=gpt-4o-realtime-preview-2024-12-17

# Optional: Configure rate limits
OPENAI_MAX_DAILY_SESSIONS=50
OPENAI_MAX_SESSION_DURATION_MINUTES=30
```

**File to modify**: Your settings/config file

```python
# ADD to your settings class:
class Settings(BaseSettings):
    # Existing settings...
    
    # OpenAI Realtime API
    OPENAI_API_KEY: str
    OPENAI_REALTIME_MODEL: str = "gpt-4o-realtime-preview-2024-12-17"
    OPENAI_MAX_DAILY_SESSIONS: int = 50
    OPENAI_MAX_SESSION_DURATION_MINUTES: int = 30
    
    class Config:
        env_file = ".env"
```

---

## 6. 🌐 Backend Request Service Updates

**File to modify**: `lib/src/services/backend_request_service.dart`

```dart
class BackendRequest {
    final authService = AuthenticationService();

    static const String _baseUrl = 'http://127.0.0.1:8000';
    static const Duration _timeout = Duration(seconds: 30); // Increased for WebRTC

    // NEW: Add method for raw HTTP requests (needed for SDP)
    Future<String?> postRaw(String url, String body, {Map<String, String>? headers}) async {
        try {
            final token = await authService.getAuthToken();
            if (token == null || token.isEmpty) {
                throw Exception('No authentication token available');
            }

            final Map<String, String> requestHeaders = {
                'Authorization': 'Bearer $token',
                ...?headers,
            };
            
            final response = await http.post(
                Uri.parse(url),
                headers: requestHeaders,
                body: body,
            ).timeout(_timeout);

            if (response.statusCode == 200) {
                return response.body;
            } else {
                throw Exception('Request failed with status ${response.statusCode}: ${response.body}');
            }
        } catch (e) {
            debugPrint('❌ Raw POST request failed: $e');
            return null;
        }
    }
    
    // Existing methods remain the same...
}
```

---

## 7. 🧪 Testing Instructions

### Phase 1: Backend Testing
1. **Test ephemeral token generation**:
   ```bash
   curl -X POST http://localhost:8000/voice-therapist/session/start \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"therapy_type": "general"}'
   ```

2. **Verify response contains**:
   - `session_id`: OpenAI session ID
   - `client_secret.value`: Ephemeral token
   - `expires_at`: Token expiration timestamp

### Phase 2: Frontend Testing
1. **Test WebRTC connection establishment**
2. **Test microphone access permissions**
3. **Test audio streaming to OpenAI**
4. **Test AI voice responses**
5. **Test session end functionality**

### Phase 3: Integration Testing
1. **Test full therapy session flow**
2. **Test different therapy types (general, anxiety, stress)**
3. **Test error handling and recovery**
4. **Test session timeout handling**

---

## 8. 🚀 Deployment Notes

### Production Considerations

1. **Security**: 
   - Never expose OpenAI API key to client
   - Use HTTPS for all connections
   - Implement rate limiting on ephemeral token generation

2. **Monitoring**:
   - Log WebRTC connection events
   - Monitor OpenAI API usage and costs
   - Track session success/failure rates

3. **Performance**:
   - WebRTC handles network optimization automatically
   - Monitor audio quality and latency
   - Implement connection retry logic

---

## 9. 🐛 Troubleshooting

### Common Issues

1. **"Failed to establish WebRTC connection"**
   - Check ephemeral token is valid and not expired
   - Verify OpenAI API key has Realtime API access
   - Ensure proper STUN server configuration

2. **"No audio from AI"**
   - Check audio permissions in browser/app
   - Verify WebRTC audio track setup
   - Check audio element initialization

3. **"Connection drops frequently"**
   - Implement connection state monitoring
   - Add automatic reconnection logic
   - Check network stability

### Debug Commands

```bash
# Check Flutter WebRTC setup
flutter doctor -v
flutter pub deps

# Test backend endpoints
curl -X GET http://localhost:8000/health
curl -X POST http://localhost:8000/voice-therapist/session/start

# Monitor WebRTC in browser
# Open Developer Tools > Console
# Check for WebRTC connection logs
```

---

## 10. 📋 Final Checklist

- [ ] Backend generates ephemeral tokens correctly
- [ ] Frontend establishes WebRTC connection
- [ ] Microphone audio reaches OpenAI
- [ ] AI voice responses play back properly  
- [ ] Session management works end-to-end
- [ ] Error handling is implemented
- [ ] Database schema is updated
- [ ] Environment variables are configured
- [ ] Testing is completed
- [ ] Documentation is updated

---

## 🎯 Expected Results

After implementing these changes:

1. **Significantly lower latency** (~200-500ms vs 2-3 seconds)
2. **Better audio quality** (native 24kHz vs compressed WebSocket)
3. **More natural conversations** (OpenAI handles turn-taking)
4. **Improved security** (ephemeral tokens vs exposed keys)
5. **Simplified architecture** (direct WebRTC vs WebSocket proxy)

This implementation leverages OpenAI's Realtime API as intended, providing a much better user experience for your voice therapy application. 