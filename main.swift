import Cocoa
import WebKit
import UserNotifications

// ============================================================
// MARK: - Main Entry
// ============================================================

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.activate(ignoringOtherApps: true)
app.run()

// ============================================================
// MARK: - App Delegate
// ============================================================

class AppDelegate: NSObject, NSApplicationDelegate, UNUserNotificationCenterDelegate {
    var window: PomodoroWindow?

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Request notification permission
        UNUserNotificationCenter.current().delegate = self
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound]) { granted, _ in
            print(granted ? "Notifications allowed" : "Notifications denied")
        }

        // Create and show window
        window = PomodoroWindow()
        window?.center()
        window?.makeKeyAndOrderFront(nil)
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows: Bool) -> Bool {
        if !hasVisibleWindows {
            window?.makeKeyAndOrderFront(nil)
        }
        return true
    }

    func applicationWillTerminate(_ notification: Notification) {
        // Cleanup
    }

    // Allow notifications even when app is in foreground
    func userNotificationCenter(_ center: UNUserNotificationCenter,
                                willPresent notification: UNNotification,
                                withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void) {
        completionHandler([.banner, .sound])
    }
}

// ============================================================
// MARK: - Pomodoro Window
// ============================================================

class PomodoroWindow: NSWindow, WKScriptMessageHandler, WKNavigationDelegate {

    private var webView: WKWebView!
    private var alwaysOnTopItem: NSMenuItem?

    init() {
        super.init(
            contentRect: NSRect(x: 0, y: 0, width: 420, height: 580),
            styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView],
            backing: .buffered,
            defer: false
        )

        self.title = "番茄钟"
        self.minSize = NSSize(width: 380, height: 520)
        self.maxSize = NSSize(width: 480, height: 680)

        // Frameless with vibrant background
        self.titlebarAppearsTransparent = true
        self.titleVisibility = .hidden
        self.isMovableByWindowBackground = true
        self.backgroundColor = NSColor(red: 0.102, green: 0.102, blue: 0.180, alpha: 1.0)
        self.level = .floating  // Always on top by default
        self.collectionBehavior = [.canJoinAllSpaces, .stationary]

        // Custom appearance
        self.isOpaque = false
        self.hasShadow = true

        setupWebView()
        setupMenu()
    }

    private func setupWebView() {
        // WKWebView configuration
        let config = WKWebViewConfiguration()

        // Add message handler for JS bridge
        config.userContentController.add(self, name: "pomodoro")
        config.userContentController.add(self, name: "notification")
        config.userContentController.add(self, name: "alwaysOnTop")

        // Allow file access from parent directory
        config.preferences.setValue(true, forKey: "allowFileAccessFromFileURLs")

        webView = WKWebView(frame: self.contentView!.bounds, configuration: config)
        webView.autoresizingMask = [.width, .height]
        webView.navigationDelegate = self
        webView.isInspectable = true

        // Transparent, seamless background
        webView.setValue(false, forKey: "drawsBackground")
        webView.layer?.cornerRadius = 12
        webView.layer?.masksToBounds = true

        self.contentView?.addSubview(webView)
        self.contentView?.wantsLayer = true
        self.contentView?.layer?.cornerRadius = 12
        self.contentView?.layer?.masksToBounds = true

        // Resolve HTML URL: bundle first, then executable-adjacent fallback
        let htmlURL: URL
        let readAccessURL: URL
        if let htmlPath = Bundle.main.path(forResource: "index", ofType: "html") {
            htmlURL = URL(fileURLWithPath: htmlPath)
            readAccessURL = htmlURL.deletingLastPathComponent()
        } else {
            let execURL = Bundle.main.bundleURL.deletingLastPathComponent()
            let fallbackURL = execURL.appendingPathComponent("index.html")
            if FileManager.default.fileExists(atPath: fallbackURL.path) {
                htmlURL = fallbackURL
                readAccessURL = execURL
            } else {
                print("ERROR: Cannot find index.html")
                return
            }
        }
        webView.loadFileURL(htmlURL, allowingReadAccessTo: readAccessURL)
    }

    private func setupMenu() {
        let mainMenu = NSMenu()

        // App menu
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "关于番茄钟", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(withTitle: "退出番茄钟", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        let appMenuItem = NSMenuItem()
        appMenuItem.submenu = appMenu
        mainMenu.addItem(appMenuItem)

        // Window menu
        let windowMenu = NSMenu(title: "窗口")
        alwaysOnTopItem = NSMenuItem(title: "🔝 置顶", action: #selector(toggleAlwaysOnTop), keyEquivalent: "t")
        alwaysOnTopItem?.state = .on
        alwaysOnTopItem?.keyEquivalentModifierMask = [.command, .shift]
        windowMenu.addItem(alwaysOnTopItem!)
        windowMenu.addItem(NSMenuItem.separator())
        windowMenu.addItem(withTitle: "最小化", action: #selector(NSWindow.miniaturize(_:)), keyEquivalent: "m")
        windowMenu.addItem(withTitle: "关闭窗口", action: #selector(NSWindow.performClose(_:)), keyEquivalent: "w")
        let windowMenuItem = NSMenuItem()
        windowMenuItem.submenu = windowMenu
        mainMenu.addItem(windowMenuItem)

        NSApplication.shared.mainMenu = mainMenu
    }

    private func setAlwaysOnTop(_ flag: Bool) {
        self.level = flag ? .floating : .normal
        alwaysOnTopItem?.state = flag ? .on : .off
        webView.evaluateJavaScript("onAlwaysOnTopChanged(\(flag))", completionHandler: nil)
    }

    @objc private func toggleAlwaysOnTop() {
        setAlwaysOnTop(self.level != .floating)
    }

    // ----------------------------------------
    // MARK: WKScriptMessageHandler
    // ----------------------------------------

    func userContentController(_ userContentController: WKUserContentController,
                               didReceive message: WKScriptMessage) {
        switch message.name {
        case "notification":
            if let body = message.body as? [String: Any],
               let title = body["title"] as? String,
               let text = body["body"] as? String {
                sendNotification(title: title, body: text)
            }
        case "alwaysOnTop":
            if let flag = message.body as? Bool {
                setAlwaysOnTop(flag)
            }
        default:
            print("Unknown message: \(message.name)")
        }
    }

    private func sendNotification(title: String, body: String) {
        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        content.sound = .default

        let request = UNNotificationRequest(
            identifier: "pomodoro-\(UUID().uuidString)",
            content: content,
            trigger: nil
        )

        UNUserNotificationCenter.current().add(request) { error in
            if let error = error {
                print("Notification error: \(error)")
            }
        }
    }
}
