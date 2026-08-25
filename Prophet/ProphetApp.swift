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
            switch phase {
            case .active:
                // Retour au premier plan : resynchronisation immédiate (cache
                // ignoré), et le live remplace les notifications programmées.
                store.disarmBackgroundNotifications()
                Task { await store.refresh(force: true) }
            case .background:
                store.armBackgroundNotifications()
            default:
                break
            }
        }
    }
}
