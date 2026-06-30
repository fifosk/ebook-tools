import Foundation

extension AppleBookCreateView {
    func refreshCreationTemplatesFromSection() {
        Task { await refreshCreationTemplates(force: true) }
    }

    func saveCurrentCreationTemplate() {
        guard let request = currentCreationTemplateSaveRequest() else {
            return
        }
        Task {
            guard let template = await viewModel.saveCreationTemplate(request, using: appState) else {
                return
            }
            selectedTemplateID = template.id
        }
    }

    func currentCreationTemplateSaveRequest() -> CreationTemplateSaveRequest? {
        switch creationMode {
        case .generatedBook:
            return AppleBookCreateTemplateSavePayloadFactory.makeGeneratedBookRequest(
                from: currentGeneratedBookDraft()
            )
        case .narrateEbook:
            return AppleBookCreateTemplateSavePayloadFactory.makeNarrateEbookRequest(
                from: currentNarrateEbookDraft()
            )
        case .subtitleJob:
            guard let draft = currentSubtitleJobDraft() else { return nil }
            return AppleBookCreateTemplateSavePayloadFactory.makeSubtitleJobRequest(from: draft)
        case .youtubeDub:
            guard let draft = currentYoutubeDubDraft() else { return nil }
            return AppleBookCreateTemplateSavePayloadFactory.makeYoutubeDubRequest(from: draft)
        }
    }

    func refreshCreationTemplates(force: Bool = false) async {
        _ = await viewModel.loadCreationTemplates(
            using: appState,
            cacheKey: creationTemplateLoadKey,
            mode: creationMode.creationTemplateMode,
            force: force
        )
        let resolvedTemplateID = AppleBookCreateTemplateSettings.resolvedTemplateSelection(
            selectedTemplateID,
            from: viewModel.creationTemplates,
            for: creationMode
        )
        guard resolvedTemplateID != selectedTemplateID else {
            return
        }
        selectedTemplateID = resolvedTemplateID
    }

    func applySelectedCreationTemplate() {
        guard let template = compatibleCreationTemplates.first(where: { $0.id == selectedTemplateID }) else {
            viewModel.creationTemplateMessage = nil
            viewModel.errorMessage = "Choose a saved template before applying it."
            return
        }
        applyCreationTemplate(template)
    }

    func requestDeleteSelectedCreationTemplate() {
        guard let template = compatibleCreationTemplates.first(where: { $0.id == selectedTemplateID }) else {
            viewModel.creationTemplateMessage = nil
            viewModel.errorMessage = "Choose a saved template before deleting it."
            return
        }
        creationTemplatePendingDelete = template
    }

    func deleteCreationTemplate(_ template: CreationTemplateEntry) async {
        creationTemplatePendingDelete = nil
        let didDelete = await viewModel.deleteCreationTemplate(
            templateID: template.id,
            using: appState
        )
        guard didDelete else { return }
        if selectedTemplateID == template.id
            || AppleBookCreateTemplateSettings.selectedCompatibleTemplateID(
                selectedTemplateID,
                from: viewModel.creationTemplates,
                for: creationMode
            ) == nil {
            selectedTemplateID = AppleBookCreateTemplateSettings.resolvedTemplateSelection(
                selectedTemplateID,
                from: viewModel.creationTemplates,
                for: creationMode
            )
        }
    }
}
