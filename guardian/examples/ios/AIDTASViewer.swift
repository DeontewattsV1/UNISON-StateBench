// SPDX-License-Identifier: Apache-2.0
// iOS 17+ source example. NOT COMPILED in the Linux verification environment.
// Read-only HATS evidence importer; no network calls or identity attestation.
import SwiftUI
import Charts
import Observation
import UniformTypeIdentifiers

private struct HatsEvidence: Decodable {
    let schemaVersion: Int
    let product: String
    let component: String
    let evidenceClass: String
    let state: HatsState
}

private struct HatsState: Decodable {
    let runId: String
    let agents: [HatsAgent]
    let events: [HatsEvent]
    let syntheticActions: Int
}

private struct HatsAgent: Decodable, Identifiable {
    let id: String
    let type: String
    let parentId: String?
    let depth: Int
    let revoked: Bool
    let lineageHash: String
}

private struct HatsEvent: Decodable, Identifiable {
    let id: String
    let seq: Int
    let type: String
    let evidence: String
}

@MainActor @Observable
private final class AgentMonitorModel {
    private(set) var evidence: HatsEvidence?
    private(set) var error: String?

    func open(_ url: URL) {
        evidence = nil
        error = nil
        let scoped = url.startAccessingSecurityScopedResource()
        defer { if scoped { url.stopAccessingSecurityScopedResource() } }
        do {
            let handle = try FileHandle(forReadingFrom: url)
            defer { try? handle.close() }
            let maximumBytes = 5 * 1024 * 1024
            let data = try handle.read(upToCount: maximumBytes + 1) ?? Data()
            guard data.count <= maximumBytes else { throw ImportError.tooLarge }
            let decoded = try JSONDecoder().decode(HatsEvidence.self, from: data)
            guard decoded.schemaVersion == 1,
                  decoded.product == "UNISON Guardian",
                  decoded.component == "HATS",
                  decoded.evidenceClass == "SIMULATED",
                  decoded.state.agents.count <= 12,
                  decoded.state.syntheticActions >= 0,
                  decoded.state.events.count <= 200 else { throw ImportError.unsupported }
            let ids = Set(decoded.state.agents.map(\.id))
            guard ids.count == decoded.state.agents.count,
                  decoded.state.agents.allSatisfy({ agent in
                      (0...3).contains(agent.depth) &&
                      (agent.parentId.map { ids.contains($0) } ?? true)
                  }),
                  Set(decoded.state.events.map(\.id)).count == decoded.state.events.count,
                  decoded.state.events.enumerated().allSatisfy({ $0.element.seq == $0.offset + 1 })
            else { throw ImportError.unsupported }
            evidence = decoded
        } catch {
            self.error = "Unable to open this HATS export. Select an unmodified Guardian HATS evidence JSON file (up to 5 MiB)."
        }
    }

    func importFailed() {
        error = "No evidence file was opened."
    }

    private enum ImportError: Error { case tooLarge, unsupported }
}

struct AIDTASViewer: View {
    @State private var model = AgentMonitorModel()
    @State private var importing = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    Text("Evidence-native agent observatory")
                        .font(.title2.bold())
                    Button("Open HATS evidence JSON", systemImage: "doc.badge.plus") {
                        importing = true
                    }
                    .buttonStyle(.borderedProminent)

                    if let evidence = model.evidence {
                        let agents = evidence.state.agents
                        let edges = agents.filter { $0.parentId != nil }.count
                        Text("\(evidence.evidenceClass) · HATS")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        Text("Run \(evidence.state.runId)")
                            .font(.caption.monospaced())
                            .textSelection(.enabled)
                        Chart {
                            BarMark(x: .value("Kind", "Agents"), y: .value("Count", agents.count))
                            BarMark(x: .value("Kind", "Lineage"), y: .value("Count", edges))
                            BarMark(x: .value("Kind", "Events"), y: .value("Count", evidence.state.events.count))
                        }
                        .frame(height: 240)
                        .accessibilityLabel("Imported synthetic evidence counts")
                        Text("Synthetic actions: \(evidence.state.syntheticActions)")
                        ForEach(agents) { agent in
                            VStack(alignment: .leading, spacing: 4) {
                                Text("\(agent.type) · depth \(agent.depth) · \(agent.revoked ? "revoked" : "registered")")
                                    .font(.headline)
                                Text(agent.id).font(.caption.monospaced())
                                Text("Digest: \(agent.lineageHash)").font(.caption.monospaced())
                            }
                            .textSelection(.enabled)
                        }
                    } else {
                        Text("Export evidence from Guardian's HATS lab, then open the downloaded JSON here.")
                    }

                    if let error = model.error {
                        Text(error).foregroundStyle(.red).accessibilityAddTraits(.updatesFrequently)
                    }
                    Text("Read-only imported counts. This observer does not recompute SHA-256 digests, authenticate an origin or authorize actions. Seeded identities are synthetic; a valid-looking export is not independent agent-origin attribution.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
                .padding()
            }
            .navigationTitle("AI-DTAS / HATS")
            .fileImporter(isPresented: $importing, allowedContentTypes: [.json]) { result in
                switch result {
                case .success(let url): model.open(url)
                case .failure: model.importFailed()
                }
            }
        }
    }
}

#Preview { AIDTASViewer() }
