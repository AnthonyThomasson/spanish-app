import { SpeechRecognition as NativeSpeechRecognition } from '@capacitor-community/speech-recognition';

type RequestPermissions = () => Promise<{ speechRecognition: string }>;

/** Asks for microphone access; resolves false (never throws) when denied or unavailable. */
export async function ensureMicrophonePermission(
  request: RequestPermissions = () => NativeSpeechRecognition.requestPermissions(),
): Promise<boolean> {
  try {
    return (await request()).speechRecognition === 'granted';
  } catch {
    return false;
  }
}
