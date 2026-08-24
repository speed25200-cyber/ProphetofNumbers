import SwiftUI

@main
struct ProphetApp: App {
    @StateObject private var store = ProphetStore()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(store)
                .preferredColorScheme(.dark)
        }
    }
}
