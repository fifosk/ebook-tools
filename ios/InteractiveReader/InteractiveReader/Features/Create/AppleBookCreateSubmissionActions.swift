import Foundation

extension AppleBookCreateView {
    func submit() {
        switch creationMode {
        case .generatedBook:
            submitGeneratedBook()
        case .narrateEbook:
            submitNarrateEbook()
        case .subtitleJob:
            submitSubtitleJob()
        case .youtubeDub:
            submitYoutubeDub()
        }
    }

    func submitGeneratedBook() {
        let draft = currentGeneratedBookDraft()

        Task {
            let jobId = await viewModel.submitGeneratedBook(draft, using: appState)
            await completeSubmission(jobId)
        }
    }

    func submitSubtitleJob() {
        guard let draft = currentSubtitleJobDraft() else { return }

        Task {
            let jobId = await viewModel.submitSubtitleJob(
                draft,
                localFileURL: selectedSubtitleFileURL,
                localFilename: selectedSubtitleFileName,
                using: appState
            )
            await completeSubmission(jobId)
        }
    }

    func submitYoutubeDub() {
        guard let draft = currentYoutubeDubDraft() else { return }

        Task {
            let jobId = await viewModel.submitYoutubeDub(draft, using: appState)
            await completeSubmission(jobId)
        }
    }

    func submitNarrateEbook() {
        let draft = currentNarrateEbookDraft()

        Task {
            let jobId = await viewModel.submitNarrateEbook(
                draft,
                localFileURL: selectedNarrateFileURL,
                localFilename: selectedNarrateFileName,
                using: appState
            )
            await completeSubmission(jobId)
        }
    }

    func completeSubmission(_ jobId: String?) async {
        guard let jobId else {
            return
        }
        await refreshIntakeStatus(force: true)
        onJobSubmitted(jobId)
    }
}
