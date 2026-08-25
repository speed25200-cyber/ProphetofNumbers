import Foundation
import UserNotifications

// Notifications locales alignées sur le cadencement officiel (un tirage
// toutes les 5 minutes à partir de nextDrawAt). Sans serveur APNs, le
// résultat lui-même ne peut pas être poussé — chaque notification porte
// donc la fin de tirage et la dernière prédiction Nexus connue.
enum Notifier {
    private static let maxScheduled = 6
    private static let drawCycle: TimeInterval = 300
    private static let publishLag: TimeInterval = 18

    static func requestAuthorization() async -> Bool {
        do {
            return try await UNUserNotificationCenter.current()
                .requestAuthorization(options: [.alert, .sound])
        } catch {
            return false
        }
    }

    static func cancelDrawNotifications() {
        let ids = (0..<maxScheduled).map { "prophet.draw.\($0)" }
        UNUserNotificationCenter.current().removePendingNotificationRequests(withIdentifiers: ids)
    }

    static func scheduleDrawNotifications(
        nextDrawAt: Date,
        nextDrawNumber: Int,
        prediction: [Int],
        stake: Int
    ) {
        cancelDrawNotifications()
        let center = UNUserNotificationCenter.current()
        let now = Date()
        let numbers = prediction.map(String.init).joined(separator: " ")

        for i in 0..<maxScheduled {
            let fire = nextDrawAt.addingTimeInterval(Double(i) * drawCycle + publishLag)
            guard fire > now.addingTimeInterval(5) else { continue }

            let content = UNMutableNotificationContent()
            content.title = "Tirage #\(nextDrawNumber + i) terminé"
            content.body = numbers.isEmpty
                ? "Ouvre Prophet pour le résultat live et la prochaine grille."
                : (i == 0
                    ? "Prédiction Nexus \(stake)/\(stake) : \(numbers) · Ouvre Prophet pour le résultat live."
                    : "Dernière prédiction Nexus \(stake)/\(stake) : \(numbers) · Ouvre Prophet pour la grille à jour.")
            content.sound = .default

            let trigger = UNTimeIntervalNotificationTrigger(
                timeInterval: fire.timeIntervalSince(now),
                repeats: false
            )
            center.add(UNNotificationRequest(
                identifier: "prophet.draw.\(i)",
                content: content,
                trigger: trigger
            ))
        }
    }
}
