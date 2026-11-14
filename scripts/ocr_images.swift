import AppKit
import Foundation
import Vision

struct Observation: Codable {
    let text: String
    let x: Double
    let y: Double
    let width: Double
    let height: Double
}

struct Result: Codable {
    let path: String
    let width: Int
    let height: Int
    let observations: [Observation]
}

let encoder = JSONEncoder()
encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
var results: [Result] = []

for path in CommandLine.arguments.dropFirst() {
    guard let image = NSImage(contentsOfFile: path),
          let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil)
    else {
        FileHandle.standardError.write("Could not load \(path)\n".data(using: .utf8)!)
        continue
    }

    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["es-ES", "en-US"]
    request.usesLanguageCorrection = true

    let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    do {
        try handler.perform([request])
        let observations = (request.results ?? []).compactMap { observation -> Observation? in
            guard let candidate = observation.topCandidates(1).first else { return nil }
            let box = observation.boundingBox
            return Observation(
                text: candidate.string,
                x: box.origin.x,
                y: box.origin.y,
                width: box.size.width,
                height: box.size.height
            )
        }
        results.append(Result(
            path: path,
            width: cgImage.width,
            height: cgImage.height,
            observations: observations
        ))
    } catch {
        FileHandle.standardError.write("OCR failed for \(path): \(error)\n".data(using: .utf8)!)
    }
}

FileHandle.standardOutput.write(try encoder.encode(results))
