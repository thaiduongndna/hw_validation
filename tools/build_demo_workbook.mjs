import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { SpreadsheetFile, Workbook } from '@oai/artifact-tool';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const outputDir = path.join(root, 'outputs', 'demo');
const qaDir = path.join(outputDir, 'qa');
await fs.mkdir(qaDir, { recursive: true });

const workbook = Workbook.create();
const sheet = workbook.worksheets.add('Validation');
sheet.showGridLines = false;
sheet.tabColor = '#1E3A5F';

const headers = ['Test ID', 'Interface', 'Signal', 'Parameter', 'Spec Min', 'Spec Max', 'Unit', 'Measured Min', 'Measured Max', 'Result', 'Note', 'Run ID'];
const records = [
  ['GPIO-01', 'GPIO', 'GPIO1', 'HIGH level', 2.4, null, 'V'],
  ['GPIO-02', 'GPIO', 'GPIO1', 'LOW level', null, 0.4, 'V'],
  ['SPI-01', 'SPI', 'SCLK', 'Clock frequency', 0.9, 1.1, 'MHz'],
  ['SPI-02', 'SPI', 'MOSI', 'Setup time', 10, null, 'ns'],
  ['I2C-01', 'I2C', 'SCL', 'Rise time', null, 300, 'ns'],
  ['I2C-02', 'I2C', 'SCL', 'LOW time', 1300, null, 'ns'],
  ['UART-01', 'UART', 'TX', 'Baud rate', 113000, 117000, 'baud'],
  ['UART-02', 'UART', 'TX', 'Stop bit time', 8, null, 'us'],
];
const values = records.map(row => [...row, null, null, 'NOT RUN', null, null]);
sheet.getRange('A1:L14').format.font = { name: 'Arial', size: 10, color: '#24364B' };
sheet.getRange('A1:L14').format.verticalAlignment = 'center';
sheet.getRange('A1:L14').format.rowHeight = 25;

sheet.getRange('A2').values = [['DEMO — Low-speed interface validation']];
sheet.getRange('A2').format.font = { name: 'Arial', size: 16, bold: true, color: '#17324D' };
sheet.getRange('A2:L2').format.rowHeight = 32;
sheet.getRange('A3').values = [['Synthetic limits for software demonstration only. These are not a component specification.']];
sheet.getRange('A3').format.font = { name: 'Arial', size: 10, color: '#9A5B13' };
sheet.getRange('A4').values = [['Edit the blue specification fields. The demo fills measured values, result and run details. Blank limit = no bound.']];
sheet.getRange('A4').format.font = { name: 'Arial', size: 10, color: '#52657A' };
sheet.getRange('A5').values = [['SPECIFICATION INPUTS']];
sheet.getRange('H5').values = [['MEASUREMENT OUTPUTS']];
sheet.getRange('A5:G5').format.fill = '#DBEAFE';
sheet.getRange('H5:L5').format.fill = '#DCFCE7';
sheet.getRange('A5:L5').format.font = { name: 'Arial', size: 10, bold: true, color: '#17324D' };

sheet.getRange('A6:L6').values = [headers];
sheet.getRange('A6:G6').format.fill = '#24517A';
sheet.getRange('H6:L6').format.fill = '#236445';
sheet.getRange('A6:L6').format.font = { name: 'Arial', size: 10, bold: true, color: '#FFFFFF' };
sheet.getRange('A6:L6').format.horizontalAlignment = 'center';
sheet.getRange('A6:L6').format.rowHeight = 30;
sheet.getRange('A6:L6').format.borders = { insideVertical: { style: 'thin', color: '#FFFFFF' } };

sheet.getRange('A7:L14').values = values;
sheet.getRange('A7:G14').format.fill = '#F4F8FD';
sheet.getRange('E7:F14').format.font = { name: 'Arial', size: 10, color: '#1D4ED8' };
sheet.getRange('H7:L14').format.fill = '#F2FAF5';
sheet.getRange('A7:L14').format.borders = { insideHorizontal: { style: 'thin', color: '#E2E8F0' }, bottom: { style: 'thin', color: '#CBD5E1' } };
sheet.getRange('E7:F14').format.horizontalAlignment = 'right';
sheet.getRange('H7:I14').format.horizontalAlignment = 'right';
sheet.getRange('E7:F9').setNumberFormat('0.0');
sheet.getRange('E10:F14').setNumberFormat('#,##0');
sheet.getRange('H7:I14').setNumberFormat('#,##0.000');
sheet.getRange('G7:G14').format.horizontalAlignment = 'center';
sheet.getRange('J7:J14').format.horizontalAlignment = 'center';
sheet.getRange('J7:J14').format.font = { name: 'Arial', size: 10, color: '#64748B' };

for (const [status, fill, color] of [
  ['PASS', '#DCFCE7', '#166534'],
  ['FAIL', '#FEE2E2', '#991B1B'],
  ['INCONCLUSIVE', '#FEF3C7', '#92400E'],
  ['SPEC ERROR', '#FEF3C7', '#92400E'],
]) {
  sheet.getRange('J7:J14').conditionalFormats.add('cellIs', {
    operator: 'equal', formula: `"${status}"`,
    format: { fill, font: { color, bold: true } },
  });
}

const widths = [105, 86, 85, 150, 95, 95, 65, 115, 115, 130, 265, 210];
widths.forEach((width, index) => {
  const column = String.fromCharCode(65 + index);
  sheet.getRange(`${column}1:${column}14`).format.columnWidthPx = width;
});
sheet.getRange('A1:L1').format.rowHeight = 10;
sheet.freezePanes.freezeRows(6);
sheet.freezePanes.freezeColumns(4);

workbook.recalculate();
const inspect = await workbook.inspect({ kind: 'table', range: 'Validation!A6:L14', include: 'values,formulas', tableMaxRows: 9, tableMaxCols: 12, maxChars: 6000 });
await fs.writeFile(path.join(qaDir, 'workbook-inspect.ndjson'), inspect.ndjson);
const errors = await workbook.inspect({ kind: 'match', searchTerm: '#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!', options: { useRegex: true, maxResults: 20 }, summary: 'formula error scan' });
await fs.writeFile(path.join(qaDir, 'formula-errors.ndjson'), errors.ndjson);
const preview = await workbook.render({ sheetName: 'Validation', range: 'A1:L14', scale: 1.5, format: 'png' });
await fs.writeFile(path.join(qaDir, 'spec_demo.png'), new Uint8Array(await preview.arrayBuffer()));
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(path.join(outputDir, 'spec_demo.xlsx'));
console.log(JSON.stringify({ workbook: path.join(outputDir, 'spec_demo.xlsx'), preview: path.join(qaDir, 'spec_demo.png'), tests: values.length, headers: headers.length }));
