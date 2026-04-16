import { jsPDF } from 'jspdf';

/**
 * Strip markdown / LaTeX formatting so the PDF contains readable plain text.
 */
function stripFormatting(text) {
  if (!text) return '';
  return text
    .replace(/\$\$([\s\S]*?)\$\$/g, (_, m) => m.trim())
    .replace(/\$(.*?)\$/g, (_, m) => m)
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/\*(.*?)\*/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/```[\s\S]*?```/g, '')
    .replace(/`(.*?)`/g, '$1')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

/**
 * Download a single history entry as a PDF.
 *
 * @param {{ query_text: string, solution_text?: string, topic?: string, created_at?: string }} entry
 */
export default function downloadHistoryPdf(entry) {
  if (!entry) return;

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

  // ── Title ──
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(18);
  doc.setTextColor(30, 64, 175);
  const title = 'Solvera \u2013 Solution';
  const titleWidth = doc.getTextWidth(title);
  doc.text(title, (pageWidth - titleWidth) / 2, y);
  y += 10;

  doc.setDrawColor(30, 64, 175);
  doc.setLineWidth(1.5);
  doc.line(marginX, y, pageWidth - marginX, y);
  y += 20;

  // ── Meta info ──
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(10);
  doc.setTextColor(100, 100, 100);

  if (entry.created_at) {
    const date = new Date(entry.created_at).toLocaleDateString('en-US', {
      weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
    });
    doc.text(`Date: ${date}`, marginX, y);
    y += 14;
  }

  if (entry.topic) {
    doc.text(`Topic: ${entry.topic.replace('_', ' ')}`, marginX, y);
    y += 14;
  }
  y += 10;

  // ── Question ──
  ensureSpace(40);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(11);
  doc.setTextColor(30, 64, 175);
  doc.text('Question', marginX, y);
  y += 4;
  doc.setDrawColor(200, 200, 200);
  doc.setLineWidth(0.5);
  doc.line(marginX, y, marginX + 80, y);
  y += 10;

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(10);
  doc.setTextColor(40, 40, 40);
  const questionLines = doc.splitTextToSize(stripFormatting(entry.query_text), maxWidth);
  questionLines.forEach((line) => {
    ensureSpace(14);
    doc.text(line, marginX, y);
    y += 14;
  });
  y += 16;

  // ── Solution ──
  const solutionText = entry.solution_text || entry.solution || '';
  if (solutionText) {
    ensureSpace(40);
    doc.setDrawColor(220, 220, 220);
    doc.setLineWidth(0.3);
    doc.line(marginX, y - 8, pageWidth - marginX, y - 8);

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(11);
    doc.setTextColor(16, 185, 129);
    doc.text('Solution', marginX, y);
    y += 4;
    doc.setDrawColor(200, 200, 200);
    doc.setLineWidth(0.5);
    doc.line(marginX, y, marginX + 80, y);
    y += 10;

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(10);
    doc.setTextColor(40, 40, 40);
    const solutionLines = doc.splitTextToSize(stripFormatting(solutionText), maxWidth);
    solutionLines.forEach((line) => {
      ensureSpace(14);
      doc.text(line, marginX, y);
      y += 14;
    });
  }

  // ── Footer ──
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

  const safeName = (entry.query_text || 'solution').slice(0, 40).replace(/[^a-zA-Z0-9 ]/g, '').trim().replace(/\s+/g, '_');
  doc.save(`Solvera_${safeName}.pdf`);
}
