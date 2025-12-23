import SwiftUI

struct JobLoaderView: View {
    @StateObject private var viewModel = InteractivePlayerViewModel()

    @State private var apiBaseURL: String = "http://localhost:8000"
    @State private var storageBaseURL: String = ""
    @State private var jobID: String = ""
    @State private var authToken: String = ""
    @State private var userID: String = ""
    @State private var userRole: String = ""
    @FocusState private var focusedField: Field?

    private enum Field {
        case api, storage, job
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    configurationForm
                    stateContent
                }
                .padding()
            }
            .navigationTitle("Interactive Reader Pilot")
        }
    }

    private var configurationForm: some View {
        PlatformGroupBox(label: { Text("Server configuration") }) {
            VStack(alignment: .leading, spacing: 12) {
                TextField("API base URL", text: $apiBaseURL)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .keyboardType(.URL)
                    .focused($focusedField, equals: .api)

                TextField("Storage base URL (optional)", text: $storageBaseURL)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .keyboardType(.URL)
                    .focused($focusedField, equals: .storage)

                TextField("Auth token (optional)", text: $authToken)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()

                HStack {
                    TextField("User ID (optional)", text: $userID)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    TextField("User role (optional)", text: $userRole)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                }

                TextField("Job ID", text: $jobID)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .focused($focusedField, equals: .job)
                    .submitLabel(.go)
                    .onSubmit(loadJob)

                loadButton
            }
        }
    }

    private var loadButton: some View {
        Button(action: loadJob) {
            HStack {
                if viewModel.loadState == .loading {
                    ProgressView()
                        .progressViewStyle(.circular)
                }
                Text("Load job")
            }
            .frame(maxWidth: .infinity)
        }
        .buttonStyle(.borderedProminent)
        .disabled(!canAttemptLoad)
    }

    @ViewBuilder
    private var stateContent: some View {
        switch viewModel.loadState {
        case .idle:
            Text("Enter a job identifier to load its interactive media.")
                .foregroundStyle(.secondary)
        case .loading:
            Text("Fetching media and timing data…")
                .foregroundStyle(.secondary)
        case let .error(message):
            VStack(alignment: .leading, spacing: 8) {
                Label("Unable to load job", systemImage: "exclamationmark.triangle.fill")
                    .foregroundStyle(.red)
                Text(message)
                    .font(.callout)
            }
        case .loaded:
            if let _ = viewModel.jobContext {
                InteractivePlayerView(viewModel: viewModel, audioCoordinator: viewModel.audioCoordinator)
                    .frame(maxWidth: .infinity)
            } else {
                Text("No interactive content available.")
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var canAttemptLoad: Bool {
        !jobID.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && URL(string: apiBaseURL.trimmingCharacters(in: .whitespacesAndNewlines)) != nil
    }

    private func loadJob() {
        guard canAttemptLoad else { return }
        focusedField = nil
        guard let apiURL = URL(string: apiBaseURL.trimmingCharacters(in: .whitespacesAndNewlines)) else { return }
        let storageURLString = storageBaseURL.trimmingCharacters(in: .whitespacesAndNewlines)
        let storageURL = storageURLString.isEmpty ? nil : URL(string: storageURLString)
        let configuration = APIClientConfiguration(
            apiBaseURL: apiURL,
            storageBaseURL: storageURL,
            authToken: authToken.nonEmptyValue,
            userID: userID.nonEmptyValue,
            userRole: userRole.nonEmptyValue
        )
        Task {
            await viewModel.loadJob(jobId: jobID, configuration: configuration)
        }
    }
}
