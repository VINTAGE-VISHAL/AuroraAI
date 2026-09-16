export interface ParsedMessageContent {
  thinking: string | null;
  content: string;
  isThinkingOpen: boolean;
}

/**
 * Parses out <think>...</think> blocks from model output text.
 * Handles both completed blocks and active streaming blocks where <think> is unclosed.
 */
export function parseThinkingContent(text: string): ParsedMessageContent {
  if (!text) {
    return { thinking: null, content: "", isThinkingOpen: false };
  }

  const thinkStartRegex = /<think>/i;
  const thinkEndRegex = /<\/think>/i;

  const startMatch = thinkStartRegex.exec(text);
  if (!startMatch) {
    return { thinking: null, content: text, isThinkingOpen: false };
  }

  const startIndex = startMatch.index;
  const contentAfterStart = text.slice(startIndex + startMatch[0].length);

  const endMatch = thinkEndRegex.exec(contentAfterStart);
  if (endMatch) {
    const thinking = contentAfterStart.slice(0, endMatch.index).trim();
    const restBefore = text.slice(0, startIndex);
    const restAfter = contentAfterStart.slice(endMatch.index + endMatch[0].length);
    const combinedContent = (restBefore + restAfter).trim();
    return { thinking, content: combinedContent, isThinkingOpen: false };
  } else {
    // <think> tag opened, but </think> tag hasn't been emitted yet (streaming active)
    const thinking = contentAfterStart.trim();
    const restBefore = text.slice(0, startIndex).trim();
    return { thinking, content: restBefore, isThinkingOpen: true };
  }
}
