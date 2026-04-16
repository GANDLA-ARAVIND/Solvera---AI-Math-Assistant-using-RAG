import { jsPDF } from 'jspdf';

/**
 * Strip markdown / LaTeX formatting so the PDF contains readable plain text.
 */
function stripFormatting(text) {
  if (!text) return '';
  return (
    text
      // Remove display math $$...$$
      .replace(/\$\$([\s\S]*?)\$\$/g, (_, m) => m.trim())
      // Remove inline math $...$
      .replace(/\$(.*?)\$/g, (_, m) => m)
      // Remove bold **...**
      .replace(/\*\*(.*?)\*\*/g, '$1')
      // Remove italic *...*
      .replace(/\*(.*?)\*/g, '$1')
      // Remove headings (## ...)
      .replace(/^#{1,6}\s+/gm, '')
      // Remove code fences
      .replace(/```[\s\S]*?```/g, '')
      // Remove inline code
      .replace(/`(.*?)`/g, '$1')
      // Collapse multiple blank lines
      .replace(/\n{3,}/g, '\n\n')
      .trim()
  );
}

/**
 * Generate and download a PDF of the current chat conversation.
 *
 * @param {Array<{role: string, content: string}>} messages
 */
export default function downloadChatPdf(messages) {
  if (!messages || messages.length === 0) return;

  const doc = new jsPDF({ unit: 'pt', format: 'a4' });
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const marginX = 50;
  const maxWidth = pageWidth - marginX * 2;
  let y = 50;

  const ensureSpace = (needed) => {
    if (y + needed > pageHeight - 50) {
      doc.addPage();
      y = 50;
    }
  };

  // ── Title ──────────────────────────────────────────────
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(18);
  doc.setTextColor(30, 64, 175); // blue-800
  const title = 'Solvera \u2013 AI Math Assistant Conversation';
  const titleWidth = doc.getTextWidth(title);
  doc.text(title, (pageWidth - titleWidth) / 2, y);
  y += 10;

  // Decorative line
  doc.setDrawColor(30, 64, 175);
  doc.setLineWidth(1.5);
  doc.line(marginX, y, pageWidth - marginX, y);
  y += 20;

  // Date/time
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(10);
  doc.setTextColor(100, 100, 100);
  const now = new Date();
  const dateStr = `Downloaded on ${now.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })} at ${now.toLocaleTimeString('en-US')}`;
  doc.text(dateStr, marginX, y);
  y += 8;

  doc.setFontSize(10);
  doc.text(`Total messages: ${messages.length}`, marginX, y);
  y += 25;

  // ── Messages ───────────────────────────────────────────
  messages.forEach((msg, idx) => {
    const isUser = msg.role === 'user';
    const label = isUser ? 'User' : 'Solvera Assistant';
    const content = stripFormatting(msg.content);

    // Label
    ensureSpace(40);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(11);
    doc.setTextColor(isUser ? 30 : 16, isUser ? 64 : 185, isUser ? 175 : 129); // blue / emerald
    doc.text(label, marginX, y);
    y += 4;

    // Thin separator under label
    doc.setDrawColor(200, 200, 200);
    doc.setLineWidth(0.5);
    doc.line(marginX, y, marginX + 120, y);
    y += 10;

    // Body text
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(10);
    doc.setTextColor(40, 40, 40);

    const lines = doc.splitTextToSize(content, maxWidth);
    lines.forEach((line) => {
      ensureSpace(14);
      doc.text(line, marginX, y);
      y += 14;
    });

    // Spacing between messages
    y += 12;

    // Full-width light divider between messages (skip after last)
    if (idx < messages.length - 1) {
      ensureSpace(8);
      doc.setDrawColor(220, 220, 220);
      doc.setLineWidth(0.3);
      doc.line(marginX, y, pageWidth - marginX, y);
      y += 16;
    }
  });

  // ── Footer on every page ───────────────────────────────
  const totalPages = doc.internal.getNumberOfPages();
  for (let p = 1; p <= totalPages; p++) {
    doc.setPage(p);
    doc.setFont('helvetica', 'italic');
    doc.setFontSize(8);
    doc.setTextColor(160, 160, 160);
    doc.text(
      `Solvera \u2013 Page ${p} of ${totalPages}`,
      pageWidth / 2,
      pageHeight - 25,
      { align: 'center' },
    );
  }

  doc.save('Solvera_Chat.pdf');
}
