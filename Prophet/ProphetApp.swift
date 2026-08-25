import SwiftUI

@main
struct ProphetApp: App {
    @StateObject private var store = ProphetStore()
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(store)
                .preferredColorScheme(.dark)
        }
        .onChange(of: scenePhase) { _, phase in
            // Retour au premier plan : resynchronisation immédiate, cache ignoré.
            if phase == .active {
                Task { await store.refresh(force: true) }
            }
        }
    }
}
