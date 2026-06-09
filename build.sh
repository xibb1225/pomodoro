#!/bin/bash
# ============================================================
# Build the Pomodoro.app bundle
# ============================================================

set -e

APP_NAME="Pomodoro"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$PROJECT_DIR/build"
APP_BUNDLE="$BUILD_DIR/$APP_NAME.app"

echo "🍅 Building $APP_NAME..."

# Clean
rm -rf "$BUILD_DIR"
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"

# -------------------------------------------
# Compile Swift
# -------------------------------------------
echo "  → Compiling Swift..."
swiftc \
  -o "$APP_BUNDLE/Contents/MacOS/$APP_NAME" \
  -target arm64-apple-macosx14.0 \
  -framework Cocoa \
  -framework WebKit \
  -framework UserNotifications \
  -O \
  "$PROJECT_DIR/main.swift"

echo "  ✓ Binary compiled"

# -------------------------------------------
# Copy resources
# -------------------------------------------
echo "  → Copying resources..."
cp "$PROJECT_DIR/index.html" "$APP_BUNDLE/Contents/Resources/"
cp "$PROJECT_DIR/style.css" "$APP_BUNDLE/Contents/Resources/"
cp "$PROJECT_DIR/renderer.js" "$APP_BUNDLE/Contents/Resources/"

# -------------------------------------------
# Create Info.plist
# -------------------------------------------
cat > "$APP_BUNDLE/Contents/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>Pomodoro</string>
    <key>CFBundleDisplayName</key>
    <string>番茄钟</string>
    <key>CFBundleIdentifier</key>
    <string>com.pomodoro.timer</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleExecutable</key>
    <string>Pomodoro</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>14.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSUIElement</key>
    <false/>
</dict>
</plist>
PLIST

# -------------------------------------------
# Create icon (simple red circle via sips)
# -------------------------------------------
echo "  → Generating icon..."

ICON_DIR="$APP_BUNDLE/Contents/Resources/AppIcon.iconset"
mkdir -p "$ICON_DIR"

# Generate a simple red-circle PNG using Python (built into macOS)
python3 "$PROJECT_DIR/gen_icon.py" "$ICON_DIR"

# Convert iconset to icns
iconutil -c icns "$ICON_DIR" -o "$APP_BUNDLE/Contents/Resources/AppIcon.icns" 2>/dev/null || true
rm -rf "$ICON_DIR"

# -------------------------------------------
# Done
# -------------------------------------------
echo ""
echo "✅ Build complete!"
echo "   App: $APP_BUNDLE"
echo ""
echo "To run: open \"$APP_BUNDLE\""
echo "Or:     $APP_BUNDLE/Contents/MacOS/$APP_NAME"
echo ""
echo "Tip: Drag Pomodoro.app to your Applications folder or Dock."
