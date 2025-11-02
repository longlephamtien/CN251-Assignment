/**
 * Utility functions for formatting data
 */

/**
 * Format timestamp to human-readable date string
 */
export const formatTimestamp = (timestamp) => {
  return new Date(timestamp * 1000).toLocaleString();
};

/**
 * Format timestamp to show date on first line and time on second
 */
export const formatTimestampMultiLine = (timestamp) => {
  const date = new Date(timestamp * 1000);
  const dateStr = date.toLocaleDateString();
  const timeStr = date.toLocaleTimeString();
  return { date: dateStr, time: timeStr };
};

/**
 * Truncate filename in the middle to preserve extension (like macOS Finder)
 * Shows beginning of filename and end before extension, with ellipsis in the middle
 * Automatically adjusts start/end ratio based on available space (responsive to window size)
 * Example: "HK1_2324_BTL1-Network Application P2P File Sharing.pdf" 
 *       -> Wide: "HK1_2324_BTL1...Application.pdf" (55/45)
 *       -> Medium: "HK1_2324_...Sharing.pdf" (60/40)
 *       -> Narrow: "HK1_23...ng.pdf" (70/30)
 */
export const truncateMiddle = (str, maxLength = 40) => {
  if (!str || str.length <= maxLength) return str;
  
  // Find extension
  const lastDotIndex = str.lastIndexOf('.');
  const hasExtension = lastDotIndex > 0 && lastDotIndex < str.length - 1;
  
  if (!hasExtension) {
    // No extension, just truncate at end
    return str.substring(0, maxLength - 3) + '...';
  }
  
  const extension = str.substring(lastDotIndex); // includes the dot
  const nameWithoutExt = str.substring(0, lastDotIndex);
  
  // Calculate how many characters we can show
  const availableChars = maxLength - extension.length - 3; // 3 for "..."
  
  if (availableChars <= 0) {
    // Extension is too long, just show it
    return '...' + extension;
  }
  
  // Dynamically calculate ratio based on maxLength (which reflects window/column width)
  // As window shrinks (maxLength decreases), we shift ratio to preserve start context
  let startRatio, endRatio;
  
  if (maxLength >= 60) {
    // Very wide: split almost evenly (55/45)
    startRatio = 0.55;
    endRatio = 0.45;
  } else if (maxLength >= 50) {
    // Wide: slight preference to start (58/42)
    startRatio = 0.58;
    endRatio = 0.42;
  } else if (maxLength >= 40) {
    // Medium: more start bias (60/40)
    startRatio = 0.60;
    endRatio = 0.40;
  } else if (maxLength >= 30) {
    // Narrow: strong start bias (65/35)
    startRatio = 0.65;
    endRatio = 0.35;
  } else if (maxLength >= 20) {
    // Very narrow: heavy start bias (70/30)
    startRatio = 0.70;
    endRatio = 0.30;
  } else {
    // Extremely narrow: maximum start bias (75/25)
    startRatio = 0.75;
    endRatio = 0.25;
  }
  
  const startChars = Math.ceil(availableChars * startRatio);
  const endChars = Math.max(1, availableChars - startChars); // At least 1 char at end
  
  // Show beginning + ... + end + extension
  const start = nameWithoutExt.substring(0, startChars);
  const end = nameWithoutExt.substring(nameWithoutExt.length - endChars);
  
  return start + '...' + end + extension;
};

/**
 * Format file size in bytes to human-readable format with auto-unit conversion
 * Format: "abc.d xB" where units auto-convert when >= 1000
 */
export const formatFileSize = (bytes) => {
  if (bytes === 0) return '0.0 B';
  
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = bytes;
  let unitIndex = 0;
  
  // Auto-convert to next unit when >= 1000
  while (size >= 1000 && unitIndex < units.length - 1) {
    size = size / 1024;
    unitIndex++;
  }
  
  // Format as "abc.d xB" (one decimal place)
  return size.toFixed(1) + ' ' + units[unitIndex];
};
