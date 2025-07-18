# FeedMerge Flutter App

A mobile application for managing social media content across multiple platforms.

## Features

- **Authentication**: Secure login/register with JWT tokens
- **State Management**: Riverpod for reactive state management
- **Navigation**: Go Router with authentication guards
- **OAuth Integration**: Connect to Twitter, Instagram, LinkedIn, and Facebook
- **Media Upload**: Background video/image upload with flutter_uploader
- **Content Calendar**: Create, schedule, and manage posts
- **Secure Storage**: JWT tokens stored securely with flutter_secure_storage

## Architecture

### State Management
- Uses **Riverpod** providers for managing:
  - Authentication state
  - Content calendar data
  - API client configuration

### Navigation
- **Go Router** with route-based navigation
- Authentication guards that redirect based on login state
- Routes: `/login`, `/register`, `/home`, `/settings`, `/new-post`

### API Integration
- **Dio** HTTP client with interceptors for:
  - Automatic JWT token attachment
  - Token refresh on 401 errors
  - Request/response logging

### OAuth Flow
- **flutter_web_auth_2** for secure OAuth flows
- Supports all major social platforms
- In-app browser for seamless user experience

### Media Upload
- **flutter_uploader** for background uploads
- Pre-signed URL workflow with backend
- Progress tracking and notification support

### Secure Storage
- **flutter_secure_storage** for:
  - JWT access/refresh tokens
  - User profile data
  - Platform-specific encryption

## Getting Started

1. **Install Dependencies**
   ```bash
   flutter pub get
   ```

2. **Update Configuration**
   - Update `ApiClient` base URL in `lib/services/api_client.dart`
   - Configure OAuth client IDs in `lib/services/oauth_service.dart`
   - Update redirect URIs for your app

3. **Platform Setup**

   **Android (`android/app/src/main/AndroidManifest.xml`)**:
   ```xml
   <!-- Add intent filters for OAuth redirects -->
   <activity
       android:name="com.linusu.flutter_web_auth_2.CallbackActivity"
       android:exported="true">
       <intent-filter android:autoVerify="true">
           <action android:name="android.intent.action.VIEW" />
           <category android:name="android.intent.category.DEFAULT" />
           <category android:name="android.intent.category.BROWSABLE" />
           <data android:scheme="com.yourapp.feedmerge" />
       </intent-filter>
   </activity>
   ```

   **iOS (`ios/Runner/Info.plist`)**:
   ```xml
   <key>CFBundleURLTypes</key>
   <array>
       <dict>
           <key>CFBundleURLName</key>
           <string>com.yourapp.feedmerge</string>
           <key>CFBundleURLSchemes</key>
           <array>
               <string>com.yourapp.feedmerge</string>
           </array>
       </dict>
   </array>
   ```

4. **Run the App**
   ```bash
   flutter run
   ```

## Project Structure

```
lib/
├── main.dart                 # App entry point with ProviderScope
├── routes.dart              # Go Router configuration
├── models/                  # Data models
│   ├── auth_state.dart     # Authentication state & User model
│   └── content_calendar.dart # Post model & calendar state
├── providers/               # Riverpod providers
│   ├── auth_provider.dart  # Authentication logic
│   └── content_calendar_provider.dart # Content management
├── services/                # External services
│   ├── api_client.dart     # HTTP client with JWT interceptors
│   ├── oauth_service.dart  # Social platform OAuth flows
│   ├── secure_storage_service.dart # Token storage
│   └── upload_service.dart # Background media upload
├── screens/                 # UI screens
│   ├── login_screen.dart
│   ├── register_screen.dart
│   ├── home_screen.dart
│   ├── settings_screen.dart
│   └── new_post_screen.dart
└── widgets/                 # Reusable widgets
    └── post_card.dart      # Post display component
```

## Key Dependencies

- `riverpod` & `flutter_riverpod`: State management
- `go_router`: Navigation with guards
- `dio`: HTTP client with interceptors
- `flutter_secure_storage`: Secure token storage
- `flutter_web_auth_2`: OAuth flows
- `flutter_uploader`: Background uploads
- `image_picker`: Media selection

## OAuth Configuration

Update the following in `oauth_service.dart`:
- Replace `YOUR_TWITTER_CLIENT_ID` with actual Twitter API client ID
- Replace `YOUR_INSTAGRAM_CLIENT_ID` with Instagram client ID
- Replace `YOUR_LINKEDIN_CLIENT_ID` with LinkedIn client ID
- Replace `YOUR_FACEBOOK_CLIENT_ID` with Facebook client ID
- Update redirect URIs to match your app's scheme

## Backend Integration

The app expects these backend endpoints:
- `POST /auth/login` - User authentication
- `POST /auth/register` - User registration
- `POST /auth/refresh` - Token refresh
- `GET /users/me` - Current user data
- `GET /posts` - User's posts
- `POST /posts` - Create new post
- `PUT /posts/{id}` - Update post
- `DELETE /posts/{id}` - Delete post
- `POST /upload/presigned-url` - Get upload URL
- `POST /auth/connect/{platform}` - Connect social account

## Security Features

- JWT tokens stored in secure keychain/keystore
- Automatic token refresh on expiration
- OAuth flows use secure in-app browser
- HTTPS-only API communication
- Platform-specific encryption for sensitive data

## Customization

- Update app colors in `main.dart` theme configuration
- Modify OAuth redirect schemes in platform configs
- Add new social platforms in `oauth_service.dart`
- Extend post model for additional metadata
- Customize UI components in the `widgets/` directory
