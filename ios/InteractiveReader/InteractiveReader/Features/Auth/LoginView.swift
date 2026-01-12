import AuthenticationServices
import SwiftUI

struct LoginView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var viewModel = LoginViewModel()
    @StateObject private var appleSignIn = AppleSignInCoordinator()
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

                            #if os(tvOS)
                            Button(action: handleAppleButton) {
                                HStack(spacing: 8) {
                                    Image(systemName: "applelogo")
                                    Text("Sign In with Apple")
                                }
                                .frame(maxWidth: .infinity)
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(.black)
                            .foregroundStyle(.white)
                            .frame(minHeight: 44)
                            .disabled(viewModel.isLoading)
                            #else
                            SignInWithAppleButton(.signIn, onRequest: { request in
                                request.requestedScopes = [.fullName, .email]
                            }, onCompletion: handleAppleSignIn)
                            .signInWithAppleButtonStyle(.black)
                            .frame(maxWidth: .infinity, minHeight: 44)
                            .disabled(viewModel.isLoading)
                            #endif
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
            appleSignIn.onCredential = { credential in
                Task {
                    await viewModel.signInWithApple(credential: credential, using: appState)
                }
            }
            appleSignIn.onError = { error in
                viewModel.errorMessage = error.localizedDescription
            }
        }
    }

    private func signIn() {
        focusedField = nil
        Task {
            await viewModel.signIn(using: appState)
        }
    }

    private func handleAppleSignIn(result: Result<ASAuthorization, Error>) {
        focusedField = nil
        switch result {
        case .success(let authorization):
            guard let credential = authorization.credential as? ASAuthorizationAppleIDCredential else {
                viewModel.errorMessage = "Apple sign-in did not return a credential."
                return
            }
            Task {
                await viewModel.signInWithApple(credential: credential, using: appState)
            }
        case .failure(let error):
            viewModel.errorMessage = error.localizedDescription
        }
    }

    private func handleAppleButton() {
        focusedField = nil
        appleSignIn.startSignIn()
    }
}
