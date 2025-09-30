# 🚨 **Flutter Voice Therapy Connection Error - Debug Guide**

## ✅ **Backend Status: CONFIRMED WORKING**
- Authentication endpoint: ✅ Working
- Session creation: ✅ Working  
- WebSocket server: ✅ Running on `ws://localhost:8000`

---

## 🔍 **Common Frontend Issues & Solutions**

### **1. WebSocket URL Format**
**Problem:** Incorrect WebSocket URL construction
**Solution:** Ensure the URL is exactly:
```dart
final wsUrl = 'ws://localhost:8000${data['websocket_url']}?token=$_jwtToken';
// Should be: ws://localhost:8000/voice-therapist/session/{session_id}/ws?token={jwt}
```

### **2. CORS/Network Issues**
**Problem:** Flutter can't connect to localhost from browser/mobile
**Solution:** Try different connection URLs:
```dart
// For Flutter Web (development)
final wsUrl = 'ws://localhost:8000/voice-therapist/session/$sessionId/ws?token=$token';

// For Flutter Mobile (emulator)
final wsUrl = 'ws://10.0.2.2:8000/voice-therapist/session/$sessionId/ws?token=$token';

// For Flutter Mobile (physical device - replace with your computer's IP)
final wsUrl = 'ws://192.168.1.XXX:8000/voice-therapist/session/$sessionId/ws?token=$token';
```

### **3. JWT Token Issues**
**Problem:** Token not properly URL-encoded or expired
**Debug Code:**
```dart
void debugToken() {
  print('JWT Token: ${_jwtToken?.substring(0, 50)}...');
  print('Session ID: $_sessionId');
  print('WebSocket URL: $wsUrl');
  
  // Test token validity
  http.get(
    Uri.parse('http://localhost:8000/user/'),
    headers: {'Authorization': 'Bearer $_jwtToken'}
  ).then((response) {
    print('Token validation status: ${response.statusCode}');
  });
}
```

### **4. WebSocket Library Issues**
**Problem:** Wrong WebSocket implementation
**Solution:** Ensure you're using the correct package:
```yaml
dependencies:
  web_socket_channel: ^2.4.0
```

```dart
import 'package:web_socket_channel/io.dart';

// Connect with proper error handling
try {
  _channel = IOWebSocketChannel.connect(
    Uri.parse(wsUrl),
    protocols: null,
  );
  
  _channel!.stream.listen(
    (message) {
      print('WebSocket message received: $message');
      _handleAIMessage(jsonDecode(message));
    },
    onError: (error) {
      print('❌ WebSocket error: $error');
      // Show connection error in UI
    },
    onDone: () {
      print('🔌 WebSocket connection closed');
    },
  );
} catch (e) {
  print('❌ Failed to connect WebSocket: $e');
}
```

---

## 🧪 **Step-by-Step Debug Process**

### **Step 1: Test API Endpoints First**
```dart
Future<void> debugBackendConnection() async {
  try {
    // Test 1: Login
    print('🔑 Testing login...');
    final loginResponse = await http.post(
      Uri.parse('http://localhost:8000/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'email': 'kevinconjoin@gmail.com',
        'password': 'password'
      }),
    );
    print('Login Status: ${loginResponse.statusCode}');
    
    if (loginResponse.statusCode == 200) {
      final loginData = jsonDecode(loginResponse.body);
      final token = loginData['auth_token'];
      print('✅ Login successful, token received');
      
      // Test 2: Session Creation
      print('📞 Testing session creation...');
      final sessionResponse = await http.post(
        Uri.parse('http://localhost:8000/voice-therapist/session/start'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json'
        },
        body: jsonEncode({'therapy_type': 'general'}),
      );
      print('Session Status: ${sessionResponse.statusCode}');
      print('Session Response: ${sessionResponse.body}');
      
      if (sessionResponse.statusCode == 200) {
        final sessionData = jsonDecode(sessionResponse.body);
        final sessionId = sessionData['session_id'];
        final wsUrl = 'ws://localhost:8000${sessionData['websocket_url']}?token=$token';
        print('✅ Session created successfully');
        print('🔗 WebSocket URL: $wsUrl');
        
        // Test 3: WebSocket Connection
        _testWebSocketConnection(wsUrl);
      }
    }
  } catch (e) {
    print('❌ API Test Failed: $e');
  }
}

Future<void> _testWebSocketConnection(String wsUrl) async {
  try {
    print('🌐 Testing WebSocket connection...');
    final channel = IOWebSocketChannel.connect(Uri.parse(wsUrl));
    
    // Set a timeout for connection
    final connectionTimer = Timer(Duration(seconds: 10), () {
      print('❌ WebSocket connection timeout');
      channel.sink.close();
    });
    
    channel.stream.listen(
      (message) {
        connectionTimer.cancel();
        print('✅ WebSocket connected successfully!');
        print('📨 First message: $message');
        channel.sink.close();
      },
      onError: (error) {
        connectionTimer.cancel();
        print('❌ WebSocket error: $error');
      },
      onDone: () {
        connectionTimer.cancel();
        print('🔌 WebSocket connection closed');
      },
    );
    
    // Send a test message
    Timer(Duration(seconds: 2), () {
      channel.sink.add(jsonEncode({
        'type': 'test',
        'message': 'Hello from Flutter'
      }));
    });
    
  } catch (e) {
    print('❌ WebSocket connection failed: $e');
  }
}
```

### **Step 2: Check Network Connectivity**
```dart
Future<void> checkNetworkConnectivity() async {
  try {
    // Test basic HTTP connectivity
    final response = await http.get(Uri.parse('http://localhost:8000/'));
    print('Backend reachable: ${response.statusCode}');
  } catch (e) {
    print('❌ Cannot reach backend: $e');
    print('💡 Try these alternatives:');
    print('   - For Android emulator: http://10.0.2.2:8000');
    print('   - For physical device: http://[YOUR_COMPUTER_IP]:8000');
  }
}
```

### **Step 3: Add Detailed Error Logging**
```dart
void setupDetailedLogging() {
  // Add this to your WebSocket connection code
  _channel!.stream.listen(
    (message) {
      print('📨 Received: ${message.toString()}');
      try {
        final data = jsonDecode(message);
        print('📊 Parsed data: $data');
        _handleAIMessage(data);
      } catch (e) {
        print('❌ JSON parse error: $e');
      }
    },
    onError: (error) {
      print('❌ WebSocket error details: $error');
      print('❌ Error type: ${error.runtimeType}');
      // Update UI to show specific error
      setState(() {
        _connectionError = error.toString();
      });
    },
    onDone: () {
      print('🔌 WebSocket done - Connection closed');
      print('🔍 Close reason: Check backend logs');
    },
  );
}
```

---

## 🎯 **Quick Fix Checklist**

1. **✅ Check URL**: Ensure WebSocket URL format is exactly right
2. **✅ Check Token**: Verify JWT is valid and properly formatted  
3. **✅ Check Network**: Try different IP addresses (localhost, 10.0.2.2, actual IP)
4. **✅ Check Logs**: Add detailed logging to see exactly where it fails
5. **✅ Check Packages**: Ensure correct WebSocket package version
6. **✅ Check CORS**: Backend might need CORS configuration for WebSockets

---

## 💻 **Backend CORS Fix (if needed)**

If the issue is CORS-related, add this to your `main.py`:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 🚀 **Expected Working Flow**

When working properly, you should see:
```
🔑 Testing login... ✅
📞 Testing session creation... ✅ 
🌐 Testing WebSocket connection... ✅
📨 First message: {"type":"session.updated",...}
✅ WebSocket connected successfully!
```

**The backend is confirmed working - this is purely a frontend connection issue!** 🎯 