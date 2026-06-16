// Client-side PDF generation with jsPDF + AutoTable.
// Writes REAL vector text and a REAL clickable link annotation (not a
// screenshot), so the text stays crisp and the Medicare link is clickable.

import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';

const BRAND_PINK = [230, 0, 126];
const BRAND_BLUE = [27, 58, 139];
const INK = [29, 29, 31];
const SUBTLE = [110, 110, 115];
const ACCENT = [0, 113, 227];
const LABEL_FILL = [245, 245, 247];

// A safe, descriptive filename for a facility's PDF.
export function pdfFileName(report) {
  const safeName = (report.name || 'facility').replace(/[^a-z0-9]+/gi, '_').slice(0, 40);
  return `Facility_Assessment_${safeName}_${report.ccn}.pdf`;
}

// Build the jsPDF document for a report WITHOUT saving it, so callers can either
// download it (exportPdf) or collect its bytes for a ZIP (batch mode).
export function buildPdfDoc(report) {
  const doc = new jsPDF({ unit: 'pt', format: 'a4' });
  const pageWidth = doc.internal.pageSize.getWidth();
  const center = pageWidth / 2;

  // --- Branding banner (STATIC — never replaced by the facility name) -------
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(22);
  const infinite = 'INFINITE';
  const managed = '  Managed by MEDELITE';
  const wInfinite = doc.getTextWidth(infinite);
  doc.setFontSize(12);
  const wManaged = doc.getTextWidth(managed);
  const startX = center - (wInfinite + wManaged) / 2;

  doc.setFontSize(22);
  doc.setTextColor(...BRAND_PINK);
  doc.text(infinite, startX, 56);
  doc.setFontSize(12);
  doc.setTextColor(...BRAND_BLUE);
  doc.text(managed, startX + wInfinite, 56);

  // --- Title + dynamic state ------------------------------------------------
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(15);
  doc.setTextColor(...INK);
  doc.text('FACILITY ASSESSMENT SNAPSHOT', center, 84, { align: 'center' });

  if (report.state) {
    doc.setFontSize(12);
    doc.setTextColor(...SUBTLE);
    doc.text(report.state, center, 102, { align: 'center' });
  }

  // --- Data table -----------------------------------------------------------
  autoTable(doc, {
    startY: 118,
    margin: { left: 56, right: 56 },
    theme: 'grid',
    styles: {
      font: 'helvetica',
      fontSize: 10,
      cellPadding: 6,
      lineColor: [210, 210, 215],
      lineWidth: 0.5,
      textColor: INK,
    },
    columnStyles: {
      0: { cellWidth: 240, fontStyle: 'bold', fillColor: LABEL_FILL, textColor: [60, 60, 67] },
      1: { cellWidth: 'auto' },
    },
    body: report.tableRows,
  });

  // --- QA Summary (benchmark verdict) ---------------------------------------
  let cursorY = doc.lastAutoTable.finalY + 24;
  if (report.qaSummary) {
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(10);
    doc.setTextColor(...INK);
    doc.text('QA Summary', 56, cursorY);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9.5);
    doc.setTextColor(...SUBTLE);
    doc.text(doc.splitTextToSize(report.qaSummary, pageWidth - 112), 56, cursorY + 14);
    cursorY += 40;
  }

  // --- Clickable Medicare Care Compare source link --------------------------
  const afterTableY = cursorY;
  doc.setFontSize(9);
  doc.setTextColor(...SUBTLE);
  doc.text('Source (click to verify on the official Medicare Care Compare profile):', 56, afterTableY);

  doc.setFontSize(10);
  doc.setTextColor(...ACCENT);
  doc.textWithLink('View official Medicare Care Compare profile →', 56, afterTableY + 16, {
    url: report.medicareUrl,
  });

  doc.setFontSize(7.5);
  doc.setTextColor(...SUBTLE);
  doc.text(report.medicareUrl, 56, afterTableY + 30);

  return doc;
}

// Single-report download (unchanged behavior).
export function exportPdf(report) {
  buildPdfDoc(report).save(pdfFileName(report));
}
