// Editable Word (.docx) export — bonus feature. Mirrors the PDF: branding
// banner, title + state, the full snapshot table, and a clickable Medicare link.

import {
  Document,
  Packer,
  Paragraph,
  Table,
  TableRow,
  TableCell,
  TextRun,
  ExternalHyperlink,
  WidthType,
  AlignmentType,
  HeadingLevel,
  BorderStyle,
} from 'docx';

const PINK = 'E6007E';
const BLUE = '1B3A8B';
const ACCENT = '0071E3';
const LABEL_FILL = 'F5F5F7';

function labelCell(text) {
  return new TableCell({
    width: { size: 45, type: WidthType.PERCENTAGE },
    shading: { fill: LABEL_FILL },
    children: [new Paragraph({ children: [new TextRun({ text, bold: true })] })],
  });
}

function valueCell(text) {
  return new TableCell({
    width: { size: 55, type: WidthType.PERCENTAGE },
    children: [new Paragraph(String(text))],
  });
}

export async function exportDocx(report) {
  const rows = report.tableRows.map(
    ([label, value]) =>
      new TableRow({ children: [labelCell(label), valueCell(value)] })
  );

  const table = new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    rows,
  });

  const doc = new Document({
    sections: [
      {
        children: [
          // Branding banner (static)
          new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({ text: 'INFINITE', bold: true, size: 40, color: PINK }),
              new TextRun({ text: '  Managed by MEDELITE', bold: true, size: 22, color: BLUE }),
            ],
          }),
          new Paragraph({
            alignment: AlignmentType.CENTER,
            heading: HeadingLevel.HEADING_1,
            children: [new TextRun({ text: 'FACILITY ASSESSMENT SNAPSHOT', bold: true })],
          }),
          new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [new TextRun({ text: report.state || '', color: '6E6E73' })],
          }),
          new Paragraph({ text: '' }),
          table,
          new Paragraph({ text: '' }),
          ...(report.qaSummary
            ? [
                new Paragraph({
                  children: [
                    new TextRun({ text: 'QA Summary: ', bold: true }),
                    new TextRun({ text: report.qaSummary }),
                  ],
                }),
                new Paragraph({ text: '' }),
              ]
            : []),
          new Paragraph({
            children: [
              new TextRun({ text: 'Source: ', color: '6E6E73' }),
              new ExternalHyperlink({
                link: report.medicareUrl,
                children: [
                  new TextRun({
                    text: 'View official Medicare Care Compare profile',
                    style: 'Hyperlink',
                    color: ACCENT,
                    underline: {},
                  }),
                ],
              }),
            ],
          }),
        ],
      },
    ],
  });

  const blob = await Packer.toBlob(doc);
  const safeName = (report.name || 'facility').replace(/[^a-z0-9]+/gi, '_').slice(0, 40);
  triggerDownload(blob, `Facility_Assessment_${safeName}_${report.ccn}.docx`);
}

function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
