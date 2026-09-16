/**
 * Utility function to select the optimal female English SpeechSynthesisVoice
 * for Samarthan Educational Assistant across different OS and browser environments.
 *
 * Priority order:
 * 1. Indian English female voice (en-IN)
 * 2. High-quality English female voices (en-US, en-GB)
 * 3. Any available English female voice
 * 4. Fallback to best available English voice
 */
export function selectBestFemaleEnglishVoice(): SpeechSynthesisVoice | null {
  if (typeof window === "undefined" || !window.speechSynthesis) {
    return null;
  }

  const voices = window.speechSynthesis.getVoices();
  if (!voices || voices.length === 0) {
    return null;
  }

  // Common female voice name keywords across Windows, macOS, Chrome, Edge, Safari
  const femaleKeywords = [
    "female",
    "zira",       // Windows English Female (Microsoft Zira)
    "heera",      // Windows Indian English Female (Microsoft Heera)
    "neerja",     // Windows Indian English Female (Microsoft Neerja)
    "prabhat",    // Edge / Windows Indian voice
    "veena",      // macOS/iOS Indian English Female
    "sangeeta",   // Android/Google Indian English Female
    "samanta",    // macOS Female
    "karen",      // macOS Australian Female
    "fiona",      // macOS Scottish Female
    "victoria",   // macOS Female
    "moira",      // macOS Irish Female
    "samantha",   // macOS US Female
    "serena",     // macOS UK Female
    "hazel",      // Windows UK Female
    "susan",      // Windows US Female
    "aria",       // Edge Neural Female
    "jenny",      // Edge Neural Female
    "emma",       // Edge Neural Female
    "ava",        // Edge Neural Female
    "sonia",      // Edge UK Female Neural
    "natural",    // Edge Natural voices (frequently female in en-US/en-IN)
    "google",     // Google US/UK/IN English voices
  ];

  // Helper score calculation for voice ranking
  const getScore = (voice: SpeechSynthesisVoice): number => {
    let score = 0;
    const nameLower = voice.name.toLowerCase();
    const langLower = voice.lang.toLowerCase().replace("_", "-");

    // 1. Language Filtering
    const isEnglish = langLower.startsWith("en");
    if (!isEnglish) return -100;

    score += 10; // Base points for English

    const isIndian = langLower.includes("en-in") || nameLower.includes("india") || nameLower.includes("indian");
    const isUS = langLower.includes("en-us");
    const isGB = langLower.includes("en-gb");

    if (isIndian) score += 50;
    else if (isUS || isGB) score += 30;

    // 2. Gender indicator check
    const matchesFemaleKeyword = femaleKeywords.some((kw) => nameLower.includes(kw));
    // Explicitly exclude known male voice identifiers
    const matchesMaleKeyword = ["david", "mark", "george", "ravi", "richard", "james", "male"].some(
      (kw) => nameLower.includes(kw) && !nameLower.includes("female")
    );

    if (matchesFemaleKeyword && !matchesMaleKeyword) score += 100;
    if (matchesMaleKeyword) score -= 80;

    // 3. Prefer local/neural high quality voices
    if (voice.localService) score += 5;
    if (nameLower.includes("neural") || nameLower.includes("natural")) score += 15;

    return score;
  };

  // Rank and sort candidate voices
  const sortedVoices = [...voices]
    .map((voice) => ({ voice, score: getScore(voice) }))
    .filter((item) => item.score > -50)
    .sort((a, b) => b.score - a.score);

  return sortedVoices.length > 0 ? sortedVoices[0].voice : voices[0];
}
