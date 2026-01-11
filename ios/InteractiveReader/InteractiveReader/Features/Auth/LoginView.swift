import SwiftUI

struct LoginView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var viewModel = LoginViewModel()
    @FocusState private var focusedField: Field?

    private enum Field {
        case api
        case username
        case password
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    PlatformGroupBox(label: { Text("Server") }) {
                        VStack(alignment: .leading, spacing: 12) {
                            TextField("API base URL", text: $appState.apiBaseURLString)
                                .textInputAutocapitalization(.never)
                                .autocorrectionDisabled()
                                #if os(iOS)
                                .keyboardType(.URL)
                                #endif
                                .focused($focusedField, equals: .api)

                            #if os(tvOS)
                            Text("Example: https://api.langtools.fifosk.synology.me")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            #else
                            Text("Example: https://api.langtools.fifosk.synology.me")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            #endif
                        }
                        .padding(.vertical, 4)
                    }

                    PlatformGroupBox(label: { Text("Sign in") }) {
                        VStack(alignment: .leading, spacing: 12) {
                            TextField("Username", text: $viewModel.username)
                                .textInputAutocapitalization(.never)
                                .autocorrectionDisabled()
                                .focused($focusedField, equals: .username)

                            SecureField("Password", text: $viewModel.password)
                                .focused($focusedField, equals: .password)
                                .submitLabel(.go)
                                .onSubmit(signIn)

                            if let error = viewModel.errorMessage {
                                Label(error, systemImage: "exclamationmark.triangle.fill")
                                    .font(.callout)
                                    .foregroundStyle(.red)
                            }

                            Button(action: signIn) {
                                HStack {
                                    if viewModel.isLoading {
                                        ProgressView()
                                    }
                                    Text("Sign In")
                                }
                                .frame(maxWidth: .infinity)
                            }
                            .buttonStyle(.borderedProminent)
                            .disabled(viewModel.isLoading)
                        }
                        .padding(.vertical, 4)
                    }
                }
                .padding()
            }
            .navigationTitle("ebook-tools")
        }
        .onAppear {
            if viewModel.username.isEmpty {
                viewModel.username = appState.lastUsername
            }
        }
    }

    private func signIn() {
        focusedField = nil
        Task {
            await viewModel.signIn(using: appState)
        }
    }
}
