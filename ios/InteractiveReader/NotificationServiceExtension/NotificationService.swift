import UserNotifications

/// Notification Service Extension for handling rich push notifications.
/// Downloads cover art images and attaches them to notifications.
class NotificationService: UNNotificationServiceExtension {

    private var contentHandler: ((UNNotificationContent) -> Void)?
    private var bestAttemptContent: UNMutableNotificationContent?

    override func didReceive(
        _ request: UNNotificationRequest,
        withContentHandler contentHandler: @escaping (UNNotificationContent) -> Void
    ) {
        self.contentHandler = contentHandler
        bestAttemptContent = (request.content.mutableCopy() as? UNMutableNotificationContent)

        guard let bestAttemptContent else {
            contentHandler(request.content)
            return
        }

        // Extract metadata from the push payload
        let userInfo = request.content.userInfo

        // Build enhanced notification body with metadata
        enrichNotificationContent(bestAttemptContent, from: userInfo)

        // Try multiple keys for cover image URL
        let imageURLString = userInfo["cover_url"] as? String
            ?? userInfo["image_url"] as? String
            ?? userInfo["thumbnail_url"] as? String
            ?? (userInfo["aps"] as? [String: Any])?["cover_url"] as? String

        guard let imageURLString, let imageURL = URL(string: imageURLString) else {
            // No image URL, deliver notification as-is
            contentHandler(bestAttemptContent)
            return
        }

        // Download the image and attach it
        downloadImage(from: imageURL) { [weak self] fileURL in
            guard let self else {
                contentHandler(bestAttemptContent)
                return
            }

            if let fileURL,
               let attachment = try? UNNotificationAttachment(
                   identifier: "cover",
                   url: fileURL,
                   options: [UNNotificationAttachmentOptionsTypeHintKey: "public.jpeg"]
               ) {
                bestAttemptContent.attachments = [attachment]
            }

            contentHandler(bestAttemptContent)
        }
    }

    override func serviceExtensionTimeWillExpire() {
        // Called just before the extension will be terminated by the system.
        // Use this as an opportunity to deliver your "best attempt" at modified content,
        // otherwise the original push payload will be used.
        if let contentHandler, let bestAttemptContent {
            contentHandler(bestAttemptContent)
        }
    }

    /// Enrich the notification content with metadata from the payload.
    /// Builds a structured body with title, author, languages, and counts.
    private func enrichNotificationContent(
        _ content: UNMutableNotificationContent,
        from userInfo: [AnyHashable: Any]
    ) {
        // Extract metadata fields
        let title = userInfo["title"] as? String
        let subtitle = userInfo["subtitle"] as? String
        let inputLanguage = userInfo["input_language"] as? String
        let targetLanguage = userInfo["target_language"] as? String
        let chapterCount = userInfo["chapter_count"] as? Int
        let sentenceCount = userInfo["sentence_count"] as? Int

        // Build enhanced body with available metadata
        var bodyParts: [String] = []

        // Title is already in the main body, add subtitle (author) if available
        if let subtitle, !subtitle.isEmpty {
            content.subtitle = subtitle
        }

        // Build metadata line: "English → Arabic"
        if let inputLanguage, let targetLanguage {
            bodyParts.append("\(inputLanguage) → \(targetLanguage)")
        } else if let inputLanguage {
            bodyParts.append(inputLanguage)
        } else if let targetLanguage {
            bodyParts.append("→ \(targetLanguage)")
        }

        // Add chapter/sentence counts
        var countParts: [String] = []
        if let chapterCount, chapterCount > 0 {
            countParts.append("\(chapterCount) chapters")
        }
        if let sentenceCount, sentenceCount > 0 {
            countParts.append("\(sentenceCount) sentences")
        }
        if !countParts.isEmpty {
            bodyParts.append(countParts.joined(separator: ", "))
        }

        // If we have metadata, append it to the body
        if !bodyParts.isEmpty {
            let metadataLine = bodyParts.joined(separator: " • ")
            if let existingBody = content.body.isEmpty ? nil : content.body {
                content.body = "\(existingBody)\n\(metadataLine)"
            } else {
                content.body = metadataLine
            }
        }
    }

    private func downloadImage(from url: URL, completion: @escaping (URL?) -> Void) {
        let task = URLSession.shared.downloadTask(with: url) { localURL, response, error in
            guard let localURL, error == nil else {
                completion(nil)
                return
            }

            // Move to a temporary location with proper extension
            let tempURL = FileManager.default.temporaryDirectory
                .appendingPathComponent(UUID().uuidString)
                .appendingPathExtension("jpg")

            do {
                // Remove existing file if any
                try? FileManager.default.removeItem(at: tempURL)
                try FileManager.default.moveItem(at: localURL, to: tempURL)
                completion(tempURL)
            } catch {
                completion(nil)
            }
        }
        task.resume()
    }
}
