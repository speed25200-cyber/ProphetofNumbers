import Combine
import Foundation


enum HubStatus: String {
    case idle, connecting, live, error
}

struct DrawSceneMeta {
    var id: Int?
    var balls: [Int]
    var boost: Double?
    var extra: Int?
    var nextDrawTime: String?
}

struct DrawSceneState {
    var scene: String
    var duration: Int
    var startTime: Int
    var endTime: Int
    var progress: Int
    var meta: DrawSceneMeta
}

enum DrawReveal {
    static let ballMs = 5500

    static func visibleCount(scene: String, startTime: Int, progress: Int, ballCount: Int) -> Int {
        if scene == "DrawScene" || scene == "ExtraScene" {
            let n = (progress - startTime + Int(0.7 * Double(ballMs))) / ballMs
            return max(0, min(20, min(ballCount, n)))
        }
        return ballCount
    }

    static func copy(scene: String) -> (kicker: String, title: String) {
        switch scene {
        case "DrawScene": return ("En direct", "Tirage en cours")
        case "ExtraScene": return ("En direct", "Boule extra")
        case "ReorderScene": return ("Classement", "Les 20 boules")
        case "ResultsScene": return ("Résultat", "Dernier tirage")
        case "CountdownScene": return ("Attente", "Prochain tirage")
        case "BoostScene": return ("Boost", "Multiplicateur")
        case "BangoScene": return ("Cagnottes", "Bango")
        case "NightModeScene": return ("Fermé", "Séance terminée")
        case "AttentionScene": return ("Attention", "Tirage imminent")
        default: return ("Loto Express", "Boucle officielle")
        }
    }
}

@MainActor
final class DrawStream: ObservableObject {
    @Published var status: HubStatus = .idle
    @Published var state: DrawSceneState?
    @Published var progress: Int = 0
    @Published var error: String?

    private var task: URLSessionWebSocketTask?
    private var session: URLSession?
    private var ping: Timer?
    private var clock: Timer?
    private var retry: Timer?
    private var closed = false
    private var invocation = 0
    private var attempt = 0
    private var snappedAt = Date()
    private var baseProgress = 0
    private let rs = "\u{1e}"

    init() {
        clock = Timer.scheduledTimer(withTimeInterval: 0.2, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.tickProgress() }
        }
        Task { await start() }
    }

    func retryNow() {
        retry?.invalidate()
        Task { await start() }
    }

    var revealed: [Int] {
        guard let state else { return [] }
        let n = DrawReveal.visibleCount(
            scene: state.scene,
            startTime: state.startTime,
            progress: progress,
            ballCount: state.meta.balls.count
        )
        return Array(state.meta.balls.prefix(n))
    }

    private func tickProgress() {
        if state != nil {
            progress = baseProgress + Int(Date().timeIntervalSince(snappedAt) * 1000)
        }
    }

    private func start() async {
        guard !closed else { return }
        status = .connecting
        do {
            let step1 = try await post("https://prod.jeux-webretail.loro.ch/api/animation/negotiate?negotiateVersion=1")
            guard let azure = step1["url"] as? String,
                  let token = step1["accessToken"] as? String,
                  let u = URL(string: azure)
            else { throw LoroError.decode }
            var comps = URLComponents(url: u, resolvingAgainstBaseURL: false)!
            let path = comps.path.hasSuffix("/") ? String(comps.path.dropLast()) : comps.path
            comps.path = path + "/negotiate"
            guard let neg2 = comps.url else { throw LoroError.decode }
            let step2 = try await post(neg2.absoluteString, token: token)
            guard let conn = step2["connectionToken"] as? String else { throw LoroError.decode }
            let id = conn.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? conn
            let tok = token.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? token
            var ws = azure.replacingOccurrences(of: "https://", with: "wss://")
            ws += (azure.contains("?") ? "&" : "?") + "id=\(id)&access_token=\(tok)"
            guard let wsURL = URL(string: ws) else { throw LoroError.decode }
            listen(wsURL)
        } catch {
            status = .error
            self.error = error.localizedDescription
            scheduleRetry()
        }
    }

    private func listen(_ url: URL) {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        let session = URLSession(configuration: config)
        self.session = session
        let task = session.webSocketTask(with: url)
        self.task = task
        task.resume()
        sendRaw(#"{"protocol":"json","version":1}"# + rs)
        ping?.invalidate()
        ping = Timer.scheduledTimer(withTimeInterval: 12, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.sendJSON(["type": 6]) }
        }
        receiveLoop()
    }

    private func receiveLoop() {
        task?.receive { [weak self] result in
            Task { @MainActor in
                guard let self, !self.closed else { return }
                switch result {
                case .failure:
                    self.status = .error
                    self.scheduleRetry()
                case .success(let message):
                    let raw: String
                    switch message {
                    case .string(let s): raw = s
                    case .data(let d): raw = String(data: d, encoding: .utf8) ?? ""
                    @unknown default: raw = ""
                    }
                    self.handle(raw)
                    self.receiveLoop()
                }
            }
        }
    }

    private func handle(_ raw: String) {
        let parts = raw.split(separator: "\u{1e}", omittingEmptySubsequences: true)
        for part in parts {
            guard let data = String(part).data(using: .utf8),
                  let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
            else { continue }
            if obj.isEmpty {
                invocation += 1
                sendJSON([
                    "type": 1,
                    "invocationId": "\(invocation)",
                    "target": "ConnectLoop",
                    "arguments": ["ONLINE"],
                ])
                continue
            }
            if let type = obj["type"] as? Int, type == 6 {
                sendJSON(["type": 6])
                continue
            }
            if obj["target"] as? String == "SendCurrentState",
               let args = obj["arguments"] as? [Any],
               let rec = args.first as? [String: Any]
            {
                apply(rec)
            }
        }
    }

    private func apply(_ rec: [String: Any]) {
        let scene = rec["scene"] as? String ?? "Unknown"
        let metaRoot = rec["meta"] as? [String: Any] ?? [:]
        let fr = metaRoot["fr-ch"] as? [String: Any] ?? metaRoot["de-ch"] as? [String: Any] ?? [:]
        let balls = (fr["balls"] as? [Any] ?? []).compactMap { v -> Int? in
            if let n = v as? Int { return n }
            if let n = v as? Double { return Int(n) }
            if let s = v as? String { return Int(s) }
            return nil
        }
        let boost: Double? = {
            if let n = fr["boost"] as? Double { return n }
            if let n = fr["boost"] as? Int { return Double(n) }
            return nil
        }()
        let extra: Int? = {
            if let n = fr["extra"] as? Int { return n }
            if let n = fr["extra"] as? Double { return Int(n) }
            return nil
        }()
        let id: Int? = {
            if let n = fr["id"] as? Int { return n }
            if let n = fr["id"] as? Double { return Int(n) }
            return nil
        }()
        let next = DrawSceneState(
            scene: scene,
            duration: rec["duration"] as? Int ?? 0,
            startTime: rec["startTime"] as? Int ?? 0,
            endTime: rec["endTime"] as? Int ?? 0,
            progress: rec["progress"] as? Int ?? 0,
            meta: DrawSceneMeta(
                id: id,
                balls: balls,
                boost: boost,
                extra: extra,
                nextDrawTime: fr["nextDrawTime"] as? String
            )
        )
        state = next
        baseProgress = next.progress
        snappedAt = Date()
        progress = next.progress
        status = .live
        error = nil
        attempt = 0
    }

    private func sendJSON(_ obj: [String: Any]) {
        guard JSONSerialization.isValidJSONObject(obj),
              let data = try? JSONSerialization.data(withJSONObject: obj),
              let s = String(data: data, encoding: .utf8)
        else { return }
        sendRaw(s + rs)
    }

    private func sendRaw(_ s: String) {
        task?.send(.string(s)) { _ in }
    }

    private func scheduleRetry() {
        guard !closed else { return }
        retry?.invalidate()
        let wait = min(12.0, 0.8 * pow(2.0, Double(min(attempt, 4))))
        attempt += 1
        retry = Timer.scheduledTimer(withTimeInterval: wait, repeats: false) { [weak self] _ in
            Task { await self?.start() }
        }
    }

    private func post(_ url: String, token: String? = nil) async throws -> [String: Any] {
        var req = URLRequest(url: URL(string: url)!)
        req.httpMethod = "POST"
        req.httpBody = Data()
        req.setValue("text/plain;charset=UTF-8", forHTTPHeaderField: "Content-Type")
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        if let token {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, resp) = try await URLSession.shared.data(for: req)
        if let http = resp as? HTTPURLResponse, !(200...299).contains(http.statusCode) {
            throw LoroError.http(http.statusCode)
        }
        guard let obj = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw LoroError.decode
        }
        return obj
    }
}
