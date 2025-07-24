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

## The overall flow:
User Account & Authentication
This section covers how users access and secure their accounts within your app.

Email & Password Registration: A standard sign-up form where a new user can create an account using their email address and a secure password. The process would include an email verification step to ensure the user's email is valid.

Social Login (Google & Facebook): One-click buttons on the sign-up/login screen allowing users to create an account or log in instantly using their existing Google or Facebook profiles. This is the fastest and most convenient way for users to get started.

Standard Login & Logout: A simple login screen for returning users to enter their email and password. The logout function, accessible from a user menu, securely ends the session and returns the user to the login screen.

Password Reset: A "Forgot Password?" link on the login screen that initiates a secure flow where a user can enter their email to receive instructions on how to reset their password.

Social Account & Platform Integration
This is the core of connecting the app to a creator's social media presence.

Connect Social Accounts: A dedicated section in the app (likely under "Settings") where the user sees a list of supported platforms (Instagram, TikTok, YouTube, Facebook). Each platform has a "Connect" button.

Secure OAuth Flow: When the user clicks "Connect," a secure, in-app browser window opens directly to the official login page for that platform (e.g., the standard Instagram login screen). The user enters their credentials there, and the app never sees or stores their password.

Granting Permissions: After logging in, the platform will ask the user to grant your app specific permissions, such as "publish content on your behalf" and "access your analytics."

Manage Connections: A view where the user can see all their currently connected accounts, with the ability to "Reconnect" if a token has expired or "Disconnect" to remove a platform from the app.

Content Creation & Scheduling Workflow
This is the main "doing" part of the app, where creators prepare and schedule their content.

Start New Post: A primary button in the UI (e.g., a "+" icon) that opens the main "composer" screen.

Media Library & Video Upload: The user is first prompted to select a video. They can either upload a new video from their phone/computer or choose one they've previously uploaded to their in-app media library.

AI Video Repurposing (Advanced Feature): An option to upload a longer video (e.g., from YouTube) and have the app's AI automatically suggest several shorter, "viral-ready" clips. The user can then select one of these clips to proceed.

Multi-Platform Customization: The core of the composer. The screen shows the video preview and a series of tabs or sections for each connected platform (Instagram, TikTok, etc.). The user can switch between these tabs to write a unique caption, title, and set of hashtags for each destination.

Platform-Specific Options:

Instagram: A dedicated field for scheduling the "First Comment" and a toggle to "Share to Feed."

TikTok: Toggles for "Allow Duets," "Allow Stitches," and "Allow Comments."

YouTube: Fields for "Video Title" (different from the description), "Visibility" (Public, Private, Unlisted), and "Tags."

Thumbnail/Cover Selection: An intuitive tool that allows the user to either scrub through the video to select a specific frame as the cover image or upload a separate, custom-designed thumbnail.

Scheduling & Publishing Options:

Schedule for Later: The user can pick a specific date and time from a calendar view for the post to go live.

Publish Now: A button to immediately start the publishing process.

Save as Draft: The ability to save the entire configured post as a draft to finish later.

Content Management & Calendar
This section covers how users view and organize their scheduled and published content.

Visual Content Calendar: A full-screen calendar (with month, week, and day views) that visually displays all scheduled, published, and draft posts. Each post is shown as a small card with the video thumbnail, making it easy to see the content plan at a glance.

Drag-and-Drop Rescheduling: The ability to simply click and drag a scheduled post from one day to another on the calendar to instantly reschedule it.

Post Status Indicators: Clear visual cues on each post card (e.g., a colored dot or icon) to indicate its status: 🟡 Scheduled, 🟢 Published, 🔴 Failed, ⚫️ Draft.

Content Filtering & Searching: The ability to filter the calendar view by social platform or post status, as well as a search bar to find specific posts by their caption or title.

Editing Scheduled Posts: Clicking on any scheduled post in the calendar opens the composer view, allowing the user to edit the caption, scheduled time, or any other detail before it goes live.

Analytics & Performance Tracking
This is where creators see the results of their work.

Unified Analytics Dashboard: A main dashboard that gives a high-level overview of performance across all connected accounts. It would feature key metrics like Total Views, Total Likes, Follower Growth, and Engagement Rate over a set period (e.g., last 30 days).

Post-by-Post Analytics: The ability to click on any published post to see a detailed breakdown of its performance, including views, likes, comments, shares, saves, and watch time.

Deep Video Analytics: For supported platforms, this would show an Audience Retention graph, a line chart that visualizes exactly when viewers are dropping off during the video, helping creators understand what parts are boring or engaging.

Platform Comparison: A feature that allows creators to see how the same video performed differently across Instagram, TikTok, and YouTube, helping them understand where their content resonates best.

App Settings & Management
This includes general account and application management features.

Profile Management: A section for the user to update their name, email address, or password.

Plan & Billing: An area where the user can see their current subscription plan, view billing history, and upgrade or change their plan.

Notification Preferences: Toggles allowing the user to control which push notifications they receive (e.g., "when a post is successfully published," "when a post fails," "weekly performance summary").

Help & Support: An integrated help center with FAQs, tutorials, and a way to contact customer support.

## MILESTONE:
🎯 Implementation Priority Suggestions
Phase 1: MVP Foundation
Authentication system
Basic social account connection (using our new APIs)
Simple post composer
Immediate publishing
Phase 2: Core Features
Content calendar
Scheduling system
Basic analytics
Draft management
Phase 3: Advanced Features
AI video repurposing
Deep analytics
Batch operations
Advanced scheduling
🔄 Process Improvements
1. Documentation Updates Needed
Update backend endpoint references
Add error handling documentation
Include testing guidelines
Add deployment instructions
2. Development Workflow
Consider adding CI/CD pipeline setup
Code generation for API models
Automated testing integration