import SwiftUI

@MainActor
extension AppleBookCreateViewModel {
    func loadCreationTemplates(
        using appState: AppState,
        cacheKey: String,
        force: Bool = false
    ) async -> [CreationTemplateEntry] {
        guard let configuration = appState.configuration else {
            return []
        }
        if !force, loadedCreationTemplatesCacheKey == cacheKey {
            return creationTemplates
        }

        isLoadingCreationTemplates = true
        creationTemplatesErrorMessage = nil
        defer { isLoadingCreationTemplates = false }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.fetchCreationTemplates()
            creationTemplates = response.templates
            loadedCreationTemplatesCacheKey = cacheKey
            return response.templates
        } catch APIClientError.httpError(let statusCode, _) where statusCode == 404 {
            creationTemplates = []
            creationTemplatesErrorMessage = "This backend does not expose saved creation templates yet."
            return []
        } catch {
            creationTemplates = []
            creationTemplatesErrorMessage = error.localizedDescription
            return []
        }
    }

    func deleteCreationTemplate(
        templateID: String,
        using appState: AppState
    ) async -> Bool {
        guard let configuration = appState.configuration else {
            creationTemplatesErrorMessage = "Configure a valid API base URL before deleting saved templates."
            return false
        }
        let trimmedID = templateID.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedID.isEmpty else {
            creationTemplatesErrorMessage = "Choose a saved template before deleting it."
            return false
        }

        isDeletingCreationTemplate = true
        creationTemplatesErrorMessage = nil
        creationTemplateMessage = nil
        defer { isDeletingCreationTemplate = false }

        do {
            let client = APIClient(configuration: configuration)
            let response = try await client.deleteCreationTemplate(templateId: trimmedID)
            let deletedID = response.templateId.trimmingCharacters(in: .whitespacesAndNewlines)
            let idsToRemove = Set([trimmedID, deletedID].filter { !$0.isEmpty })
            guard !idsToRemove.isEmpty else {
                creationTemplatesErrorMessage = "Saved template was not deleted."
                return false
            }

            let templateCountBeforeRemoval = creationTemplates.count
            creationTemplates.removeAll { idsToRemove.contains($0.id) }
            let didRemoveLocalTemplate = creationTemplates.count != templateCountBeforeRemoval
            if response.deleted {
                creationTemplateMessage = "Deleted saved template."
                return true
            }
            guard didRemoveLocalTemplate else {
                creationTemplatesErrorMessage = "Saved template was not deleted."
                return false
            }
            creationTemplateMessage = "Removed stale saved template."
            return true
        } catch {
            creationTemplatesErrorMessage = error.localizedDescription
            return false
        }
    }

    func saveCreationTemplate(
        _ request: CreationTemplateSaveRequest,
        using appState: AppState
    ) async -> CreationTemplateEntry? {
        guard let configuration = appState.configuration else {
            creationTemplatesErrorMessage = "Configure a valid API base URL before saving templates."
            return nil
        }
        guard !request.name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            creationTemplatesErrorMessage = "Template name cannot be empty."
            return nil
        }

        isSavingCreationTemplate = true
        creationTemplatesErrorMessage = nil
        creationTemplateMessage = nil
        defer { isSavingCreationTemplate = false }

        do {
            let client = APIClient(configuration: configuration)
            let saved = try await client.saveCreationTemplate(request)
            creationTemplates.removeAll { $0.id == saved.id }
            creationTemplates.insert(saved, at: 0)
            loadedCreationTemplatesCacheKey = nil
            creationTemplateMessage = "Saved template \(saved.displayName)."
            return saved
        } catch {
            creationTemplatesErrorMessage = error.localizedDescription
            return nil
        }
    }
}
