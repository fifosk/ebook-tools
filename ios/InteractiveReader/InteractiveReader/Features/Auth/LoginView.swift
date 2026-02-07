import AuthenticationServices
import SwiftUI

struct LoginView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var viewModel = LoginViewModel()
    @StateObject private var appleSignIn = AppleSignInCoordinator()
    @FocusState private var focusedField: Field?

    private enum Field {
        case username
        case password
    }

    var body: some View {
        NavigationStack {
            ZStack {
                LoginBackgroundView()
                ScrollView {
                    VStack(spacing: 24) {
                        LoginCard {
                            VStack(alignment: .leading, spacing: 20) {
                                LoginHeaderView()
                                LoginServerStatusView(status: viewModel.serverStatus)

                                VStack(alignment: .leading, spacing: 12) {
                                    TextField("Username", text: $viewModel.username)
                                        .textInputAutocapitalization(.never)
                                        .autocorrectionDisabled()
                                        .focused($focusedField, equals: .username)
                                        .loginFieldStyle()
                                        .accessibilityIdentifier("loginUsernameField")

                                    SecureField("Password", text: $viewModel.password)
                                        .focused($focusedField, equals: .password)
                                        .submitLabel(.go)
                                        .onSubmit(signIn)
                                        .loginFieldStyle()
                                        .accessibilityIdentifier("loginPasswordField")

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
                                    .loginPrimaryButtonStyle()
                                    .disabled(viewModel.isLoading)
                                    .accessibilityIdentifier("loginSignInButton")

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
                                    // Use fixedSize to let the button determine its own width
                                    // This avoids constraint conflicts with Apple's internal max-width of 375
                                    .frame(minWidth: 200, maxWidth: 375, minHeight: 44)
                                    .disabled(viewModel.isLoading)
                                    #endif
                                }
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .center)
                    }
                    .padding(.horizontal, 24)
                    .padding(.vertical, 32)
                }
            }
            .toolbar(.hidden, for: .navigationBar)
        }
        .onAppear {
            if viewModel.username.isEmpty {
                viewModel.username = appState.lastUsername
            }
            Task {
                await viewModel.refreshServerStatus(using: appState)
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
