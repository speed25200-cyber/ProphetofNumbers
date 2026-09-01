import SwiftUI

@main
struct ProphetApp: App {
    @StateObject private var store = ProphetStore()
    @StateObject private var draw = DrawStream()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(store)
                .environmentObject(draw)
                .preferredColorScheme(.dark)
        }
    }
}
